"""Read CTC's credential leaflet index, and match leaflets to authorizations conservatively.

A leaflet is attached to an authorization on two rules, both of them equalities between
published titles. Nothing else. No prefix matching, no keyword overlap, no reasoning from a
document code to a leaflet number, and no similarity score.

1. **Exact title.** The leaflet's published title and the authorization's published title
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

Both rules are deliberately strict, and they leave most authorizations without a leaflet.
That is the intended outcome: a leaflet link asserts "this Commission document describes this
authorization", and a near-miss title is not evidence for that claim. The counts of matched
and unmatched authorizations, and of which rule matched, are derived from the data at build
time and recorded in the coverage statement, so the strictness is visible rather than hidden.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SOURCE_PATH: Final = (
    Path(__file__).resolve().parents[3] / "data" / "source" / "credential-leaflets.html"
)

SOURCE_URL: Final = "https://www.ctc.ca.gov/credentials/leaflets/"
SITE_ROOT: Final = "https://www.ctc.ca.gov"

_LINK_RE: Final = re.compile(
    r'<a[^>]+href="(/credentials/leaflets/[^"#?]+)"[^>]*>(.*?)</a>', re.DOTALL
)
_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")
_NON_ALNUM_RE: Final = re.compile(r"[^a-z0-9]+")
_QUALIFIED_RE: Final = re.compile(r"^(?P<base>.+?)\s*\((?P<qualifier>[^()]+)\)$")
"""An authorization title ending in one parenthesised qualifier, and the title without it."""

MATCH_EXACT_TITLE: Final = "exact title"
MATCH_NAMED_FAMILY: Final = "named family, qualifier in parentheses"


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


def normalize_title(title: str) -> str:
    """The comparison key: lower case, dashes unified, punctuation reduced to spaces.

    Case and punctuation differ between the two pages for the same document ("CTE)" versus
    "CTE )", en dash versus hyphen), and that variation carries no meaning. Word order and
    word content are untouched, so two different documents cannot normalize together.
    """
    # The dashes are deliberate: CTC uses all three across the two pages for one document.
    lowered = title.lower().replace("\u2013", "-").replace("\u2014", "-")
    return " ".join(_NON_ALNUM_RE.sub(" ", lowered).split())


def _text(fragment: str) -> str:
    stripped = _TAG_RE.sub(" ", fragment)
    return _SPACE_RE.sub(" ", html.unescape(stripped).replace("\xa0", " ")).strip()


def parse(markup: str) -> tuple[Leaflet, ...]:
    """Every leaflet the index links, ordered by leaflet code.

    A link whose text is empty (the index repeats each leaflet as an image link beside its
    text link) contributes nothing and is skipped; the first non-empty title for a given
    path wins, so the parse is independent of markup duplication.
    """
    found: dict[str, str] = {}
    for path, label in _LINK_RE.findall(markup):
        code = path.strip("/").rsplit("/", 1)[-1]
        if not code or code == "leaflets":
            continue
        title = _text(label)
        if title and not found.get(code):
            found[code] = title
    return tuple(
        Leaflet(code=code, title=found[code], url=f"{SITE_ROOT}/credentials/leaflets/{code}/")
        for code in sorted(found)
    )


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


def match_title(title: str, index: Mapping[str, Leaflet]) -> Match | None:
    """The leaflet an authorization title identifies, and which rule identified it.

    Rule 1 is tried first and rule 2 only where rule 1 finds nothing, so an authorization
    that has a leaflet of its own is never attributed to the family leaflet above it.
    """
    exact = index.get(normalize_title(title))
    if exact is not None:
        return Match(leaflet=exact, rule=MATCH_EXACT_TITLE)
    qualified = _QUALIFIED_RE.fullmatch(title.strip())
    if qualified is None:
        return None
    family = index.get(normalize_title(qualified.group("base")))
    if family is None:
        return None
    return Match(
        leaflet=family,
        rule=MATCH_NAMED_FAMILY,
        qualifier=qualified.group("qualifier").strip(),
    )
