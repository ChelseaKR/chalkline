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

The ``<h1>`` reads ``"<title> (<CODE>)"``. This module requires both halves to agree with
the leaflet the index named: the code must be the code, and the title must equal the index
title under the same normalization the matcher uses. That check is not decorative. CL-893 is
listed in the Commission's index as "American Indian Languages Credential" and titles itself
"American Indian Languages-Culture Credential", and a page whose own title is not the title
under which it was matched is not evidence about the authorization it was matched to.

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

    skipped_headings: tuple[str, ...]
    """In-scope headings this module could not classify, and therefore did not read."""

    def of_kind(self, *kinds: str) -> tuple[Section, ...]:
        return tuple(section for section in self.sections if section.kind in kinds)


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


def parse(markup: str, code: str, index_title: str) -> LeafletPage:
    """One leaflet page, read as far as it describes the document it is titled for.

    ``code`` and ``index_title`` are what the Commission's leaflet index says about this
    document. Both must agree with the page's own ``<h1>`` or this raises: the page is then
    not evidence about the authorization the index matched it to.
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
    if normalize_title(page_title) != normalize_title(index_title):
        raise ValueError(
            f"{code}: the index lists this leaflet as {index_title!r} and the page titles "
            f"itself {page_title!r}; a page whose own title is not the title it was matched "
            "under is not evidence about the authorization it was matched to"
        )

    lead, sections, stopped_at, skipped = _sections(body[found.end() :])
    return LeafletPage(
        code=code,
        page_title=page_title,
        lead=lead,
        sections=sections,
        stopped_at=stopped_at,
        skipped_headings=skipped,
    )


def _sections(
    markup: str,
) -> tuple[tuple[str, ...], tuple[Section, ...], str | None, tuple[str, ...]]:
    """Walk the page's blocks into a lead and a list of sections, stopping where it must."""
    lead: list[str] = []
    sections: list[Section] = []
    seen: set[str] = set()
    heading: str | None = None
    level = 0
    blocks: list[str] = []
    stopped_at: str | None = None

    def close() -> None:
        if heading is not None:
            sections.append(
                Section(heading=heading, level=level, kind=classify(heading), blocks=tuple(blocks))
            )

    for block in _BLOCK_RE.finditer(markup):
        if block.group("heading") is not None:
            text = _text(block.group("heading"))
            if not text:
                continue
            key = _normalize_heading(text)
            kind = classify(text)
            if key in seen or (kind == UNCLASSIFIED and _names_a_document(text)):
                stopped_at = text
                break
            close()
            seen.add(key)
            heading, level, blocks = text, int(block.group("h")[1]), []
            continue
        text = _text(
            block.group("para") if block.group("para") is not None else block.group("item")
        )
        if not text:
            continue
        (blocks if heading is not None else lead).append(text)
    else:
        close()
    if stopped_at is not None:
        close()

    return (
        tuple(lead),
        tuple(sections),
        stopped_at,
        tuple(section.heading for section in sections if section.kind == UNCLASSIFIED),
    )


def load(code: str, index_title: str, directory: Path | None = None) -> LeafletPage:
    """Parse the vendored snapshot of one leaflet page."""
    path = (directory or SOURCE_DIR) / f"{code}.html"
    return parse(path.read_text(encoding="utf-8"), code, index_title)


def available(directory: Path | None = None) -> tuple[str, ...]:
    """Every leaflet code this repository holds a snapshot for, in code order."""
    root = directory or SOURCE_DIR
    if not root.exists():
        return ()
    return tuple(sorted(path.stem for path in root.glob("*.html")))
