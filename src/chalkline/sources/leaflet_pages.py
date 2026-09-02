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

An unclassified heading that names a credential, permit, certificate, certification or
authorization is where that happens, and **the Commission's own outline is what says whether
it has happened.** Where such a heading has sub-headings under it, the leaflet has started a
second document and given it a structure of its own, and the page ends there: nothing after
it is read. Where it has none, it is one stretch of prose inside the outline of the document
being described, so that heading and its prose are set aside and reading resumes with the
next heading.

That distinction is the whole of the fix for issue #36, and the leaflets are what argue for
it. Naming a document was the entire test until 2026-08-29, so reading ended at CL-879's
"Special Class Authorization" -- one paragraph about an add-on, sitting between the Speech
Language Pathology Services Credential's "Authorization" section and its own four
"Requirements for ..." sections, none of which were ever reached. Fourteen of the nineteen
vendored pages stopped early, twelve of them before something this module classifies, and
CL-537 stopped at its first heading and published nothing at all. Five stop now, each at a
document the Commission gave its own outline to.

Reading also ends where a classified heading repeats one already read, because the
Commission does not head two statements of one document's requirements with one string. That
test applies to classified headings only: leaflets repeat unclassified sub-headings on
purpose, and applying it to those ended CL-529 one heading before its "Period Of Validity"
and CL-879 in the middle of its requirements.

Within the range, only sections whose heading classifies contribute anything, and the
headings that were skipped are recorded so the omission is counted rather than silent. So are
the stop, what a stop left unread, and what was set aside.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
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
"""Words that make an unclassified heading a claim about some document.

A heading carrying one of these that this module cannot classify is a heading about a
document, and the question is whether it is *this* document. These five words cannot answer
that, and treating them as though they could is what issue #36 is about: "TPSL
Authorizations" on the Teaching Permit for Statutory Leave's own leaflet carries one of them
and is about that same permit. :func:`_has_sub_headings` is what answers it, and this tuple
is only what raises the question."""


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
    """The heading at which the leaflet moved on to another document, if it did.

    Nothing after this heading is read. It is set where the page began describing a second
    Commission document and gave that document sub-headings of its own, and where a
    classified heading repeated one already read. See :func:`_read_heading`.
    """

    classified_beyond_the_stop: tuple[str, ...]
    """Headings after :attr:`stopped_at` that :func:`classify` recognises, in page order.

    The size of what a stop leaves behind, and nothing more. It is not a claim that any of it
    was wrongly dropped: past a stop the page is describing another Commission document, and
    these are that document's own statements. CL-380 stops at the Special Teaching
    Authorization in Health, and the "Requirements for the Clear Credential" and "Term of the
    Credential" behind that stop belong to the Other Health Services Credentials rather than
    to the School Nurse Services Credential the leaflet is titled for. Reading them would be
    a wrong statement, and the count is here so that not reading them is a visible one.

    Until 2026-08-29 this measured something much larger and much less defensible. The stop
    rule fired on any unclassified heading naming a document, so it fired on asides inside
    the leaflet's own outline, and what sat behind those stops was the leaflet's own later
    requirements (issue #36). Five of the vendored pages stop today where fourteen did.

    Empty when reading was not stopped, which is a different fact from an unread page.
    """

    set_aside: tuple[str, ...]
    """Headings whose subject is not the leaflet's own, read past rather than read.

    The other half of the correction to issue #36. An unclassified heading that names a
    document but has no sub-headings under it is an aside inside the outline of the document
    being described -- CL-902's "TPSL Authorizations", CL-879's "Special Class
    Authorization", the "Bilingual Authorizations" paragraph three permits carry. Its own
    prose is never read, because this module cannot say whose statement it is; the page after
    it is, because the outline says the Commission has gone back to the subject it was
    describing.

    Listed rather than counted so that a reader can see what was set aside and disagree. The
    judgement is this module's and it is the weakest one it makes: unlike a stop it does not
    end the page, so a wrong call here reads one paragraph less rather than a page less.
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


def _prose(block: re.Match[str]) -> str:
    """The text of a paragraph or list item block."""
    return _text(block.group("para") if block.group("para") is not None else block.group("item"))


@dataclass(frozen=True, slots=True)
class _Block:
    """One heading or one paragraph of the page, in the order the Commission wrote it."""

    heading: bool
    text: str
    level: int


def _walk(markup: str) -> list[_Block]:
    """The page as a list rather than an iterator, because the rule needs to look ahead.

    Whether a heading has sub-headings under it cannot be answered from the heading itself,
    and it is the question :func:`_has_sub_headings` asks. Reading the blocks into a list
    first is what makes that answerable without a second pass over the markup.
    """
    blocks: list[_Block] = []
    for block in _BLOCK_RE.finditer(markup):
        if block.group("heading") is not None:
            text = _text(block.group("heading"))
            if text:
                blocks.append(_Block(True, text, int(block.group("h")[1])))
            continue
        text = _prose(block)
        if text:
            blocks.append(_Block(False, text, 0))
    return blocks


def _has_sub_headings(blocks: list[_Block], index: int) -> bool:
    """Whether the Commission gave the heading at ``index`` a structure of its own.

    The next heading on the page is the whole of the answer. A deeper one is this heading's
    child, so the heading is a section with an outline under it; a heading at the same level
    or shallower ends it, so the heading is a single stretch of prose with nothing beneath.

    This is the distinction the stop rule turns on, and the leaflets are what argue for it.
    CL-380's "Special Teaching Authorization in Health" is followed by "Requirements for the
    Special Teaching Authorization in Health" one level down: the Commission has started
    describing a second document and given it its own requirements, and the tail of that page
    really does belong to other documents (its closing "Term of the Credential" reads
    "Qualified applicants will receive a Clear Health Services Credential issued for five
    calendar years", which is not the School Nurse Services Credential this leaflet is titled
    for). CL-902's "TPSL Authorizations" is followed by "Period of Validity" at the same
    level: it is one paragraph about what this same permit's own variants authorize, and the
    page goes straight back to the permit afterwards.
    """
    level = blocks[index].level
    for block in blocks[index + 1 :]:
        if block.heading:
            return block.level > level
    return False


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

    lead, sections, stopped_at, beyond, set_aside, skipped = _sections(body[found.end() :])
    return LeafletPage(
        code=code,
        page_title=page_title,
        lead=lead,
        sections=sections,
        stopped_at=stopped_at,
        classified_beyond_the_stop=beyond,
        set_aside=set_aside,
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


@dataclass(slots=True)
class _Reading:
    """The state of one walk down a leaflet page.

    A class rather than a stack of locals so that the rule in :func:`_read_heading` reads as
    the three things a heading can be -- a section to open, a subject to set aside, or the
    end of the page -- instead of as bookkeeping.
    """

    lead: list[str] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    """Normalized headings of the classified sections already read. See :func:`_read_heading`
    for why unclassified headings are not recorded here."""

    open_heading: str | None = None
    open_level: int = 0
    open_blocks: list[str] = field(default_factory=list)
    enclosing: tuple[int, str] | None = None
    """The innermost classified section still open, as (heading level, kind). A heading at or
    above that level closes it, which is what "sits inside" means in an outline."""

    stopped_at: str | None = None
    beyond: list[str] = field(default_factory=list)
    set_aside: list[str] = field(default_factory=list)
    within_set_aside: bool = False

    def close(self) -> None:
        """Finish the open section, if one is open."""
        self.enclosing = _close(
            self.sections, self.open_heading, self.open_level, self.open_blocks, self.enclosing
        )
        self.open_heading = None

    def prose(self, text: str) -> None:
        """File one paragraph under the open section, the lead, or nothing at all."""
        if self.stopped_at is not None or self.within_set_aside:
            return
        (self.open_blocks if self.open_heading is not None else self.lead).append(text)

    def begin(self, block: _Block, kind: str, key: str) -> None:
        """Open a section for a heading that belongs to the document the leaflet is titled for."""
        if kind != UNCLASSIFIED:
            self.seen.add(key)
        self.open_heading, self.open_level, self.open_blocks = block.text, block.level, []
        self.within_set_aside = False

    def stop(self, heading: str) -> None:
        """End the page here. Nothing after this is read."""
        self.stopped_at = heading
        self.within_set_aside = False

    def aside(self, heading: str) -> None:
        """Set this heading and its prose aside, and go on reading after it."""
        self.set_aside.append(heading)
        self.within_set_aside = True


def _read_heading(reading: _Reading, blocks: list[_Block], index: int) -> None:
    """Open a section at this heading, set it aside, or stop the page here.

    The whole of the scope rule, in the order it decides.

    A **classified heading whose words a classified heading already used** ends the page. The
    Commission does not head two statements of one document's requirements with one string,
    so a repeat is the page having looped into a structure it has been through. The
    restriction to classified headings is the correction: the rule used to apply to every
    heading, and leaflets repeat unclassified sub-headings on purpose. CL-529 heads the
    out-of-state paragraph under each of its three specializations "Out-of-State Applicants",
    and the second one used to end the page one heading before "Period Of Validity"; CL-879
    heads the alternatives under each of its four requirement sections "Option 1" and
    "Option 2". Neither is a second document.

    An **unclassified heading naming a document** is the case issue #36 is about, and it is
    two cases. Where the Commission gave it sub-headings, the leaflet has moved on to another
    document and given that document its own structure, so the page ends there: CL-380's
    "Special Teaching Authorization in Health" is followed by that authorization's own
    requirements, and everything past it belongs to documents other than the School Nurse
    Services Credential the leaflet is titled for. Where it has no sub-headings, it is an
    aside inside the outline of the document being described, so it is set aside -- its own
    prose is never read, because this module cannot say whose it is -- and reading resumes at
    the next heading. CL-879's "Special Class Authorization", CL-902's "TPSL Authorizations"
    and CL-562's "National Board for Professional Teaching Standards Certification" are all
    that shape, and treating them as the end of the page dropped four "Requirements for ..."
    sections, a "Period of Validity" and a "Terms and Definitions:" that this project's own
    classifier recognises and that plainly belong to the leaflet's own subject.

    Everything else opens a section.
    """
    block = blocks[index]
    kind = classify(block.text)
    key = _normalize_heading(block.text)
    reading.close()
    if kind != UNCLASSIFIED:
        if key in reading.seen:
            reading.stop(block.text)
        else:
            reading.begin(block, kind, key)
        return
    if not _names_a_document(block.text):
        reading.begin(block, kind, key)
        return
    if _has_sub_headings(blocks, index):
        reading.stop(block.text)
    else:
        reading.aside(block.text)


def _sections(
    markup: str,
) -> tuple[
    tuple[str, ...],
    tuple[Section, ...],
    str | None,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    """Walk the page's blocks into a lead and a list of sections, stopping where it must.

    Past the stop nothing is read: no section, no block, no text. The walk continues anyway,
    over headings alone, because how much of the page a stop leaves behind is the size of
    the omission, and an omission this project cannot close is one it can at least measure.
    """
    blocks = _walk(markup)
    reading = _Reading()
    for index, block in enumerate(blocks):
        if not block.heading:
            reading.prose(block.text)
            continue
        if reading.stopped_at is not None:
            if classify(block.text) != UNCLASSIFIED:
                reading.beyond.append(block.text)
            continue
        _read_heading(reading, blocks, index)
    if reading.stopped_at is None:
        reading.close()

    return (
        tuple(reading.lead),
        tuple(reading.sections),
        reading.stopped_at,
        tuple(reading.beyond),
        tuple(reading.set_aside),
        tuple(s.heading for s in reading.sections if s.kind == UNCLASSIFIED),
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
