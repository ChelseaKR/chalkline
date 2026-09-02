"""Read one CTC credential leaflet, as the Commission publishes it on the web.

The Commission's leaflets are web pages, not only PDFs: every leaflet the index links under
``/credentials/leaflets/<code>/`` serves its full text as HTML. That is the artifact this
module reads, from the vendored snapshots in ``data/source/leaflets/`` (provenance in the
``.source.json`` beside each). Nothing here opens a socket.

What a leaflet page is
----------------------

One ``<article>``, holding a page-builder tree of sections. The Commission's own content
runs from the ``<h1 class="entry-title">`` down to the site's footer block, which the theme
marks with ``et_pb_with_border``. Inside that range the text is ordinary ``<h2>``-``<h6>``
headings with ``<p>`` paragraphs and ``<ul>``/``<ol>`` items under them.

Identity is checked, not assumed
--------------------------------

The ``<h1>`` reads ``"<title> (<CODE>)"``. **The code must be the code the index named.** A
snapshot whose page calls itself something other than the document that was asked for is the
wrong file, and this module refuses it outright: no policy can rescue reading the wrong
document.

The title is a different question, and this module reports it rather than deciding it. The
page's title and the index's title are both names the Commission published for the same
leaflet, and they do not always agree: CL-893 is listed in the index as "American Indian
Languages Credential" and titles itself "American Indian Languages-Culture Credential", while
CL-902 is listed as "The Teaching Permit for Statutory Leave (TPSL)" and titles itself
"Teaching Permit for Statutory Leave". One of those disagreements is a reason to refuse the
page and the other is what identifies it, and which is which depends on the authorization
being matched, which this module knows nothing about. So :class:`LeafletPage` carries the
page's own title and :mod:`chalkline.attachment` decides. That decision used to live here as
a ``raise``, which is why "The Teaching Permit for Statutory Leave" could not be read at all.

Variant sections
----------------

Several leaflets state one set of requirements for a named permit and then break them out by
variant: CL-858 heads "Requirements for Issuance" and then "Single Subject:", "Multiple
Subject:" and "Education Specialist:". Those sub-headings are not section kinds, so this
module does not classify them; it records which classified section each one sits inside, and
the policy layer matches a variant heading against the parenthesised qualifier the
Commission put in the authorization's own title.

What is in scope, and where reading stops
-----------------------------------------

Several leaflets describe more than one document. CL-380 is titled for the School Nurse
Services Credential and then goes on to the Special Teaching Authorization in Health and the
Other Health Services Credentials, each with its own requirements. Attributing those to the
School Nurse credential would be a wrong statement, not a rough one.

So reading stops at the first heading that both fails to classify and names a credential,
permit, certificate, certification, or authorization, and at the first heading that repeats
one already seen. Everything before that point belongs to the document the leaflet is titled
for; everything after it is another document's and is never read. Within the range, only
sections whose heading classifies contribute anything, and the headings that were skipped
are recorded so the omission is counted rather than silent.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from chalkline.sources.leaflets import normalize_title

SOURCE_DIR: Final = Path(__file__).resolve().parents[3] / "data" / "source" / "leaflets"

_ARTICLE_RE: Final = re.compile(r"<article[^>]*>.*?</article>", re.DOTALL)
_FOOTER_SECTION_RE: Final = re.compile(
    r'<div class="[^"]*et_pb_with_border[^"]*et_pb_section[^"]*"\s*>'
)
_TITLE_RE: Final = re.compile(r'<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>(.*?)</h1>', re.DOTALL)
_BLOCK_RE: Final = re.compile(
    r"<(?P<h>h[2-6])[^>]*>(?P<heading>.*?)</(?P=h)>|<p[^>]*>(?P<para>.*?)</p>|<li[^>]*>(?P<item>.*?)</li>",
    re.DOTALL,
)
_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")
_CODED_TITLE_RE: Final = re.compile(r"^(?P<title>.+?)\s*\((?P<code>[A-Za-z]+-[0-9A-Za-z-]+)\)$")

REQUIREMENTS: Final = "requirements"
RENEWAL: Final = "renewal"
VALIDITY: Final = "validity"
AUTHORIZATION: Final = "authorization"
DEFINITIONS: Final = "definitions"
INTRODUCTION: Final = "introduction"
UNCLASSIFIED: Final = ""

CONDITION_KINDS: Final = (REQUIREMENTS, RENEWAL, VALIDITY)
"""The section kinds that become CTDL condition profiles."""

VALIDITY_HEADINGS: Final = ("period of validity", "term of the credential", "term of validity")
"""Headings under which the Commission states how long a document lasts."""

CREDENTIAL_NOUNS: Final = (
    "credential",
    "permit",
    "certificate",
    "certification",
    "authorization",
)
"""Words that make an unclassified heading a claim about some document. A section headed
with one of these that this module cannot classify is where reading stops, because the
leaflet has moved on to a document other than the one it is titled for."""


@dataclass(frozen=True, slots=True)
class Section:
    """One heading of a leaflet and the Commission's text under it."""

    heading: str
    level: int
    kind: str
    blocks: tuple[str, ...]

    within: str = UNCLASSIFIED
    """The kind of the nearest classified section this one sits under, by heading level.

    The Commission's leaflets nest: "Single Subject:" at ``h3`` under "Requirements for
    Issuance" at ``h2`` is part of those requirements, and the same words under a validity
    heading would not be. Reading the outline is reading the document; guessing from the
    words alone would not be.
    """


@dataclass(frozen=True, slots=True)
class LeafletPage:
    """One leaflet page, read down to the point where it stops describing its own subject."""

    code: str
    page_title: str
    lead: tuple[str, ...]
    """The Commission's prose between the title and the first heading."""

    sections: tuple[Section, ...]
    """The sections in scope, classified. Out-of-scope sections are not here at all."""

    stopped_at: str | None
    """The heading that ended the readable range, if one did."""

    classified_beyond_the_stop: tuple[str, ...]
    """Headings after :attr:`stopped_at` that :func:`classify` recognises, in page order.

    The size of what a stop leaves behind, and nothing more. It is an upper bound on what a
    corrected stop rule could recover, not a claim that any of it was wrongly dropped: where
    the stop was right, as at CL-380's move to the Special Teaching Authorization in Health,
    these headings belong to a different Commission document and not reading them is the
    point. Where the stop was wrong, as at CL-879's "Special Class Authorization", they are
    this leaflet's own later requirements. This module cannot tell those two apart (issue
    #36), so it publishes the number and leaves the judgement to a reader.

    Twelve of the nineteen vendored pages stop before something classified. CL-797 is the
    largest, stopping before nine headings that include the requirements for every level of
    the Child Development Permit; no authorization is attached to it, so that one costs the
    published graph nothing today and would cost it a great deal the day one is.

    Empty when reading was not stopped, which is a different fact from an unread page.
    """

    skipped_headings: tuple[str, ...]
    """In-scope headings this module could not classify, and therefore did not read."""

    def of_kind(self, *kinds: str) -> tuple[Section, ...]:
        return tuple(section for section in self.sections if section.kind in kinds)

    def variants_within(self, kind: str) -> tuple[Section, ...]:
        """Unclassified sections nested inside a section of ``kind``, with text under them.

        These are the Commission's own breakdown of one statement by variant. They are
        offered, not attributed: only a caller holding a published qualifier to compare
        against a heading can say which variant a given section belongs to.
        """
        return tuple(
            section
            for section in self.sections
            if section.kind == UNCLASSIFIED and section.within == kind and section.blocks
        )


def _text(fragment: str) -> str:
    stripped = _TAG_RE.sub(" ", fragment)
    return _SPACE_RE.sub(" ", html.unescape(stripped).replace("\xa0", " ")).strip()


def _normalize_heading(heading: str) -> str:
    """A heading reduced for comparison: lower case, no punctuation, single spaces."""
    return normalize_title(heading)


def classify(heading: str) -> str:
    """Which kind of statement a heading introduces, or :data:`UNCLASSIFIED`.

    The vocabulary is small on purpose. A heading this function does not recognise is never
    read, so widening it is the only way to publish more, and each widening is a claim that
    the wording means what the CTDL property says.
    """
    text = _normalize_heading(heading)
    if not text:
        return UNCLASSIFIED
    if "renew" in text:
        return RENEWAL
    if text.startswith("requirements"):
        return REQUIREMENTS
    if text in VALIDITY_HEADINGS:
        return VALIDITY
    if text == AUTHORIZATION:
        return AUTHORIZATION
    if text.startswith("terms and definitions") or text.startswith("definition"):
        return DEFINITIONS
    if text == INTRODUCTION:
        return INTRODUCTION
    return UNCLASSIFIED


def _names_a_document(heading: str) -> bool:
    return any(noun in _normalize_heading(heading) for noun in CREDENTIAL_NOUNS)


def _stops_reading(heading: str, key: str, seen: set[str]) -> bool:
    """Whether this heading ends the range the leaflet describes its own subject in.

    Two conditions, and the module docstring argues both: a heading already seen means the
    page has looped back into a structure it has been through, and an unclassified heading
    naming a document means it has moved on to one. Named here rather than written inline so
    that :func:`_sections` reads as a walk and the rule issue #36 is about has one place to
    live.
    """
    return key in seen or (classify(heading) == UNCLASSIFIED and _names_a_document(heading))


def _prose(block: re.Match[str]) -> str:
    """The text of a paragraph or list item block."""
    return _text(block.group("para") if block.group("para") is not None else block.group("item"))


def _body(markup: str) -> str:
    """The Commission's own content of a leaflet page, footer chrome removed.

    Raises rather than guessing when the page is not the shape this parser was written
    against: a redesigned page should stop the build, not quietly yield a shorter leaflet.
    """
    articles: list[str] = _ARTICLE_RE.findall(markup)
    if len(articles) != 1:
        raise ValueError(
            f"expected exactly one <article> on the leaflet page, found {len(articles)}"
        )
    article = articles[0]
    footer = _FOOTER_SECTION_RE.search(article)
    if footer is None:
        raise ValueError(
            "no footer section found on the leaflet page; the parser cannot tell where the "
            "Commission's content ends and the site's chrome begins"
        )
    return article[: footer.start()]


def parse(markup: str, code: str) -> LeafletPage:
    """One leaflet page, read as far as it describes the document it is titled for.

    ``code`` is the leaflet the caller asked for. The page's ``<h1>`` must name that same
    code or this raises: a snapshot that calls itself another document is the wrong file.

    The page's own title is returned, not judged. Whether it is close enough to the title an
    authorization was matched under is a question about that authorization, and it is settled
    in :mod:`chalkline.attachment`.
    """
    body = _body(markup)
    found = _TITLE_RE.search(body)
    if found is None:
        raise ValueError(f'{code}: the leaflet page publishes no <h1 class="entry-title">')
    printed = _text(found.group(1))
    parsed = _CODED_TITLE_RE.fullmatch(printed)
    if parsed is None:
        raise ValueError(f"{code}: the page title {printed!r} does not read '<title> (<CODE>)'")
    if parsed.group("code").lower() != code.lower():
        raise ValueError(
            f"{code}: the page titles itself {parsed.group('code')!r}, so the snapshot is "
            "not the leaflet the index named"
        )
    page_title = parsed.group("title")

    lead, sections, stopped_at, beyond, skipped = _sections(body[found.end() :])
    return LeafletPage(
        code=code,
        page_title=page_title,
        lead=lead,
        sections=sections,
        stopped_at=stopped_at,
        classified_beyond_the_stop=beyond,
        skipped_headings=skipped,
    )


def _closed(
    heading: str,
    level: int,
    blocks: list[str],
    enclosing: tuple[int, str] | None,
) -> tuple[Section, tuple[int, str] | None]:
    """One finished section, and the classified scope that is open after it.

    ``enclosing`` is the innermost classified section still open, as (heading level, kind). A
    heading at or above that level closes it, which is what "sits inside" means in an outline.
    Only an unclassified section records a scope: a classified one states its own kind, and
    that kind is the answer to what it is.
    """
    kind = classify(heading)
    if enclosing is not None and level <= enclosing[0]:
        enclosing = None
    section = Section(
        heading=heading,
        level=level,
        kind=kind,
        blocks=tuple(blocks),
        within=enclosing[1] if enclosing is not None and kind == UNCLASSIFIED else UNCLASSIFIED,
    )
    return section, (enclosing if kind == UNCLASSIFIED else (level, kind))


def _close(
    sections: list[Section],
    heading: str | None,
    level: int,
    blocks: list[str],
    enclosing: tuple[int, str] | None,
) -> tuple[int, str] | None:
    """Append the open section, if one is open, and give back the scope open after it."""
    if heading is None:
        return enclosing
    section, enclosing = _closed(heading, level, blocks, enclosing)
    sections.append(section)
    return enclosing


def _sections(
    markup: str,
) -> tuple[tuple[str, ...], tuple[Section, ...], str | None, tuple[str, ...], tuple[str, ...]]:
    """Walk the page's blocks into a lead and a list of sections, stopping where it must.

    Past the stop nothing is read: no section, no block, no text. The walk continues anyway,
    over headings alone, because how much of the page a stop leaves behind is the size of
    the omission, and an omission this project cannot close is one it can at least measure.
    """
    lead: list[str] = []
    sections: list[Section] = []
    seen: set[str] = set()
    heading: str | None = None
    level = 0
    blocks: list[str] = []
    stopped_at: str | None = None
    beyond: list[str] = []
    # The innermost classified section still open, as (heading level, kind). A heading at or
    # above that level closes it, which is what "sits inside" means in an outline.
    enclosing: tuple[int, str] | None = None

    for block in _BLOCK_RE.finditer(markup):
        if block.group("heading") is None:
            text = _prose(block)
            if text and stopped_at is None:
                (blocks if heading is not None else lead).append(text)
            continue
        text = _text(block.group("heading"))
        if not text:
            continue
        if stopped_at is not None:
            if classify(text) != UNCLASSIFIED:
                beyond.append(text)
            continue
        key = _normalize_heading(text)
        enclosing = _close(sections, heading, level, blocks, enclosing)
        if _stops_reading(text, key, seen):
            stopped_at = text
            heading = None
            continue
        seen.add(key)
        heading, level, blocks = text, int(block.group("h")[1]), []
    if stopped_at is None:
        enclosing = _close(sections, heading, level, blocks, enclosing)

    return (
        tuple(lead),
        tuple(sections),
        stopped_at,
        tuple(beyond),
        tuple(section.heading for section in sections if section.kind == UNCLASSIFIED),
    )


def load(code: str, directory: Path | None = None) -> LeafletPage:
    """Parse the vendored snapshot of one leaflet page."""
    path = (directory or SOURCE_DIR) / f"{code}.html"
    return parse(path.read_text(encoding="utf-8"), code)


def available(directory: Path | None = None) -> tuple[str, ...]:
    """Every leaflet code this repository holds a snapshot for, in code order."""
    root = directory or SOURCE_DIR
    if not root.exists():
        return ()
    return tuple(sorted(path.stem for path in root.glob("*.html")))
