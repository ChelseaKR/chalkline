"""Read CTC's credential leaflet index, and match leaflets to authorizations conservatively.

A leaflet is attached to an authorization on equalities between strings the Commission
published. Nothing else. No prefix matching, no keyword overlap, no similarity score, and no
inference from one name to another.

Two of those equalities are between titles:

1. **Exact title.** A published title of the leaflet and the authorization's published title
   are the same string after case folding and punctuation normalization.
2. **Named family.** The authorization's published title is a leaflet title followed by a
   parenthesised qualifier, and the part before the qualifier equals that leaflet's title
   under the same normalization. ``Short-Term Staff Permit (Single Subject)`` and
   ``Short-Term Staff Permit (Special Education)`` are two of the Commission's variants of
   one named permit, and the Commission publishes exactly one leaflet titled
   ``Short-Term Staff Permit``.

Rule 2 is an equality too: the qualifier is removed as a whole parenthesised unit and the
remainder must match character for character after normalization. It is not a prefix rule.
``Education Specialist Instruction Credential Requirements for Teachers Prepared Outside of
California`` still matches nothing, because dropping a trailing parenthetical is not what
separates it from ``Education Specialist Instruction Credential``.

A leaflet has up to two published titles
----------------------------------------

The index gives each leaflet a title, and the leaflet's own page gives itself another in its
``<h1>``. Usually they are the same string. Where they differ, both are still the Commission's
published name for that document, and both are tried: ``CL-902`` is listed in the index as
"The Teaching Permit for Statutory Leave (TPSL)" and titles itself "Teaching Permit for
Statutory Leave", which is exactly rule 2's base for the two authorizations the sort table
publishes as ``Teaching Permit for Statutory Leave (Multiple Subject)`` and ``(Single
Subject)``. Reading the page's own title is not a widening of the rule; it is applying the
same equality to the other name the Commission published for the same document.

Which title matched decides whether the page may be read. See
:mod:`chalkline.attachment`, which is where that decision lives.

The third equality is a code, not a name
----------------------------------------

Some leaflet titles carry the Commission's own document code in parentheses. Where that code
is, character for character, a whole Document Title cell in the sort table, the Commission
has said which document the leaflet is for in its own key, which is a stronger statement than
a name. ``Mathematics Instructional Leadership Specialist Credential (MILS) and Mathematics
Instructional Added Authorization (MIAA)`` names document ``MILS``, and the sort table
publishes ``MILS`` as the Document Title of exactly one credential.

The code must be a whole Document Title cell. A cell reading ``TC1, TC2`` lists two documents
and a leaflet naming one of them says nothing about a row that carries both.

All three are deliberately strict, and they leave most authorizations without a leaflet. That
is the intended outcome: a leaflet link asserts "this Commission document describes this
authorization", and a near-miss title is not evidence for that claim. The counts of matched
and unmatched authorizations, and of which rule matched, are derived from the data at build
time and recorded in the coverage statement, so the strictness is visible rather than hidden.
"""

from __future__ import annotations

import html
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SOURCE_PATH: Final = (
    Path(__file__).resolve().parents[3] / "data" / "source" / "credential-leaflets.html"
)

SOURCE_URL: Final = "https://www.ctc.ca.gov/credentials/leaflets/"
SITE_ROOT: Final = "https://www.ctc.ca.gov"

_ROW_RE: Final = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_CELL_RE: Final = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
_LINK_RE: Final = re.compile(
    r'<a[^>]+href="(/credentials/leaflets/[^"#?]+)"[^>]*>(.*?)</a>', re.DOTALL
)
_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")
_NON_ALNUM_RE: Final = re.compile(r"[^a-z0-9]+")
_QUALIFIED_RE: Final = re.compile(r"^(?P<base>.+?)\s*\((?P<qualifier>[^()]+)\)$")
"""An authorization title ending in one parenthesised qualifier, and the title without it."""

_PARENTHESISED_RE: Final = re.compile(r"\(([^()]+)\)")
"""Every parenthesised run in a title. Used to look for a document code, not to strip."""

MATCH_EXACT_TITLE: Final = "exact title"
MATCH_NAMED_FAMILY: Final = "named family, qualifier in parentheses"
MATCH_DOCUMENT_CODE: Final = "document code published in the leaflet's own title"

FROM_INDEX: Final = "the Commission's leaflet index"
FROM_PAGE: Final = "the leaflet page's own title"
FROM_DOCUMENT_CODE: Final = "the Commission's document code, not a title"
"""Where the string that produced a match was published. Counted in the coverage statement,
because "which of the Commission's own words said so" is the whole basis of an attachment."""


@dataclass(frozen=True, slots=True)
class Leaflet:
    """One leaflet as the index publishes it."""

    code: str
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class Match:
    """A leaflet attached to an authorization, and the rule that attached it."""

    leaflet: Leaflet
    rule: str
    qualifier: str | None = None
    """The parenthesised text rule 2 set aside, kept so the match can be re-read later."""

    published_by: str = FROM_INDEX
    """Which of the Commission's published strings the equality was against.

    Load-bearing rather than decorative: a leaflet page may be read for prose only where the
    page's own title is one of the strings that produced the match, and this is what says
    whether it was.
    """

    matched_title: str = ""
    """The exact published string the authorization's title was compared against."""


def normalize_title(title: str) -> str:
    """The comparison key: lower case, dashes unified, punctuation reduced to spaces.

    Case and punctuation differ between the two pages for the same document ("CTE)" versus
    "CTE )", en dash versus hyphen), and that variation carries no meaning. Word order and
    word content are untouched, so two different documents cannot normalize together.
    """
    # The dashes are deliberate: CTC uses all three across the two pages for one document.
    lowered = title.lower().replace("\u2013", "-").replace("\u2014", "-")
    return " ".join(_NON_ALNUM_RE.sub(" ", lowered).split())


def normalize_code(code: str) -> str:
    """The comparison key for a document code: lower case, separators dropped.

    The Commission writes one code two ways across the index's own two columns. ``CL-533o``
    in the code cell is ``cl-533o`` in the link path, and ``CL-533O CLAD-BL`` is
    ``cl-533o-clad-bl``: a space in one place is a hyphen in the other. Dropping every
    separator compares the code and not the punctuation between its parts. Letters and
    digits are untouched and their order is untouched, so two different codes cannot
    normalize together.
    """
    return _NON_ALNUM_RE.sub("", code.lower())


def _text(fragment: str) -> str:
    stripped = _TAG_RE.sub(" ", fragment)
    return _SPACE_RE.sub(" ", html.unescape(stripped).replace("\xa0", " ")).strip()


@dataclass(frozen=True, slots=True)
class Superseded:
    """An index row that points at a leaflet under some *other* document's code.

    The Commission keeps a row for each retired document, linking it to the leaflet that
    replaced it. The row's link text is a sentence about that replacement --- "CL-740 has
    been replaced by CL-828." --- and its code cell holds the retired code, not the code of
    the leaflet it links to. It is a redirection, and it publishes no title for anything.
    """

    code: str
    """The retired document's code, as the index's own code column publishes it."""

    replaced_by: str
    """The leaflet the row links to."""

    notice: str
    """The sentence the index prints in place of a title."""


def _rows(markup: str) -> list[tuple[str, str, str]]:
    """Every index row that links a leaflet, as (link path code, code cell, link text).

    The index is a three-column table: the linked title, the Commission's document code, and
    a category. Only the first two are read. A row's cells are taken from the row itself, so
    a code can never be read off a neighbour.
    """
    found: list[tuple[str, str, str]] = []
    for row in _ROW_RE.findall(markup):
        cells = _CELL_RE.findall(row)
        if len(cells) < 2:
            continue
        link = _LINK_RE.search(row)
        if link is None:
            continue
        path = link.group(1).strip("/").rsplit("/", 1)[-1]
        if not path or path == "leaflets":
            continue
        found.append((path, _text(cells[1]), _text(cells[0])))
    return found


def parse(markup: str) -> tuple[Leaflet, ...]:
    """Every leaflet the index gives a title, ordered by leaflet code.

    A leaflet's own row is the one whose code cell holds the code its link path names. That
    is the row that publishes the leaflet's title, and it is the only row that does.

    The index also carries a redirection row for each retired document, linking it to the
    leaflet that replaced it, with the retired code in the code column and a sentence where a
    title would go. Six leaflets have one, and for all six the Commission prints the
    redirection above the leaflet's own row. This function used to take the first non-empty
    link text for a path, so all six were published under a sentence about a document that no
    longer exists: ``cl-828`` came out titled "CL-740 has been replaced by CL-828." and its
    real title, "General Education Multiple and Single Subject Limited Assignment Teaching
    Permits", was never read. A row that publishes no title is not a title.

    Order is not relied on. A leaflet is identified by the agreement between its two
    published codes, so the same leaflets come back whichever way round the Commission
    prints the rows.
    """
    found: dict[str, str] = {}
    for path, code, title in _rows(markup):
        if title and normalize_code(code) == normalize_code(path) and not found.get(path):
            found[path] = title
    return tuple(
        Leaflet(code=code, title=found[code], url=f"{SITE_ROOT}/credentials/leaflets/{code}/")
        for code in sorted(found)
    )


def superseded(markup: str) -> tuple[Superseded, ...]:
    """Every redirection row: a retired document code, and the leaflet that replaced it.

    Counted rather than discarded. These rows are the reason the naive parse was wrong, and a
    coverage statement that simply stopped mentioning them would be hiding the correction
    rather than publishing it.
    """
    return tuple(
        Superseded(code=code, replaced_by=path, notice=title)
        for path, code, title in _rows(markup)
        if title and normalize_code(code) != normalize_code(path)
    )


@dataclass(frozen=True, slots=True)
class Index:
    """The leaflet index as a whole: what it titles, and what it only redirects."""

    leaflets: tuple[Leaflet, ...]
    superseded: tuple[Superseded, ...]


def load_index(path: Path | None = None) -> Index:
    """The vendored leaflet index, titled leaflets and redirection rows alike."""
    markup = (path or SOURCE_PATH).read_text(encoding="utf-8")
    return Index(leaflets=load(path), superseded=superseded(markup))


def load(path: Path | None = None) -> tuple[Leaflet, ...]:
    """Parse the vendored leaflet index (or another copy, for tests).

    An index that yields nothing is refused here rather than returned. `parse` is allowed to
    find no leaflets, because markup holding only the index's own self-link genuinely lists
    none; a whole index artifact holding none is a page this parser can no longer read.
    `sort_table.load` has always refused its artifact on the same grounds, and the leaflet
    side did not: it returned `()`, and the entire pipeline succeeded on that. Nothing
    attached, descriptions and conditions dropped out of the graph, the coverage statement
    published the smaller figures as fact, and every gate stayed green. `_LINK_RE` needs a
    path-relative href, so a CMS switching to absolute URLs is all it would take.

    This docstring used to say `sort_table.load` "has always refused its artifact on the same
    grounds". That was true of every way the sort-table page could stop *parsing* and false
    of the one way it could stop having rows: a table keeping the Commission's six headers
    and losing every row under them satisfied all four of that parser's structural checks and
    returned `()`. `sort_table.load` now carries this same refusal, so the sentence holds.
    """
    leaflets = parse((path or SOURCE_PATH).read_text(encoding="utf-8"))
    if not leaflets:
        raise ValueError(
            f"the leaflet index at {path or SOURCE_PATH} links no leaflet pages; the page "
            "structure changed and an unreadable index is not an empty one"
        )
    return leaflets


def index_by_title(leaflets: tuple[Leaflet, ...]) -> dict[str, Leaflet]:
    """Normalized title to leaflet, dropping any title two leaflets share.

    An ambiguous title is not a match: if two leaflets normalize alike this code cannot tell
    which one describes the authorization, so it offers neither.
    """
    counts: dict[str, int] = {}
    for leaflet in leaflets:
        key = normalize_title(leaflet.title)
        counts[key] = counts.get(key, 0) + 1
    return {
        normalize_title(leaflet.title): leaflet
        for leaflet in leaflets
        if counts[normalize_title(leaflet.title)] == 1
    }


def index_by_document_code(
    leaflets: tuple[Leaflet, ...], published_codes: Collection[str]
) -> dict[str, Leaflet]:
    """Document code to the one leaflet whose published title names it in parentheses.

    ``published_codes`` is the set of Document Title cells the sort table actually publishes.
    A parenthesised run that is not one of them is not a code and is ignored, which is what
    keeps "(Single Subjects)", "(Audiology, Orientation and Mobility)" and "(Formerly:
    Development Center Permits)" out: the rule is an equality against the Commission's own
    key, so anything that is not in that key simply fails it.

    A code two leaflets name is dropped, for the same reason an ambiguous title is dropped:
    this code cannot tell which of them describes the document, so it offers neither.
    """
    counts: dict[str, int] = {}
    for leaflet in leaflets:
        for code in _PARENTHESISED_RE.findall(leaflet.title):
            if code.strip() in published_codes:
                counts[code.strip()] = counts.get(code.strip(), 0) + 1
    return {
        code.strip(): leaflet
        for leaflet in leaflets
        for code in _PARENTHESISED_RE.findall(leaflet.title)
        if code.strip() in published_codes and counts[code.strip()] == 1
    }


def match_title(
    title: str, index: Mapping[str, Leaflet], published_by: str = FROM_INDEX
) -> Match | None:
    """The leaflet an authorization title identifies, and which rule identified it.

    Rule 1 is tried first and rule 2 only where rule 1 finds nothing, so an authorization
    that has a leaflet of its own is never attributed to the family leaflet above it.

    ``published_by`` names where the titles in ``index`` were published, so a match carries
    the provenance of the string that produced it rather than only the fact of it.
    """
    exact = index.get(normalize_title(title))
    if exact is not None:
        return Match(
            leaflet=exact,
            rule=MATCH_EXACT_TITLE,
            published_by=published_by,
            matched_title=title.strip(),
        )
    qualified = _QUALIFIED_RE.fullmatch(title.strip())
    if qualified is None:
        return None
    base = qualified.group("base").strip()
    family = index.get(normalize_title(base))
    if family is None:
        return None
    return Match(
        leaflet=family,
        rule=MATCH_NAMED_FAMILY,
        qualifier=qualified.group("qualifier").strip(),
        published_by=published_by,
        matched_title=base,
    )


def match_document_code(document_title: str, index: Mapping[str, Leaflet]) -> Match | None:
    """The leaflet whose published title names this whole Document Title cell as a code.

    The cell must match whole. ``TC1, TC2`` names two documents, and a leaflet titled for one
    of them is not titled for the row that carries both, so the lookup is on the cell as the
    Commission wrote it and never on a token split out of it.
    """
    leaflet = index.get(document_title.strip())
    if leaflet is None:
        return None
    return Match(
        leaflet=leaflet,
        rule=MATCH_DOCUMENT_CODE,
        published_by=FROM_DOCUMENT_CODE,
        matched_title=document_title.strip(),
    )
