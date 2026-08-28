"""Decide, for each authorization, which leaflet describes it and what may be read from it.

This is the policy layer between the two leaflet sources and the export. It answers four
questions in order, and records the answer to each so the counts in the coverage statement
are derived rather than declared:

1. **Which leaflet, if any?** An equality against one of the Commission's own published
   strings: the title the leaflet index gives the leaflet, the title the leaflet page gives
   itself, or a document code the leaflet's title names. Tried in that order, and nothing
   else is tried at all.
2. **Is the snapshot the leaflet that was asked for?**
   :func:`chalkline.sources.leaflet_pages.parse` refuses a page whose ``<h1>`` carries some
   other document's code.
3. **Is the page's own title one of the strings that produced the match?** This is the check
   that used to live inside the parser. A page may be read only where the Commission's own
   name for it is a name that identified the authorization. Matching on the index's title
   therefore requires the page to agree with the index; matching on the page's title is
   self-satisfying; matching on a document code is not a title match at all and never
   permits a read.
4. **What does the page state about the document it is titled for?** The classified sections
   in the readable range, which stops where the leaflet moves on to another document, plus
   the variant section the Commission's own sub-heading names.

An authorization that fails step 2 or step 3, or whose leaflet has no vendored snapshot,
still gets its Commission link: the Commission's own index or key made that association, not
this project. What it does not get is prose, because prose attributed to the wrong document
is worse than no prose.

Why step 3 is not simply "the page agrees with the index"
---------------------------------------------------------

Two leaflets disagree with the index about their own name, and they are opposite cases.

``cl-893`` is indexed as "American Indian Languages Credential", which is exactly the title
of the two authorizations that match it, and titles itself "American Indian
Languages-Culture Credential". The sort table publishes *both* ``AIL`` and ``AILC`` as
document codes, so the page's own name may well be the other document's. Prose refused.

``cl-902`` is indexed as "The Teaching Permit for Statutory Leave (TPSL)", which matches no
authorization, and titles itself "Teaching Permit for Statutory Leave", which is precisely
the family base of ``Teaching Permit for Statutory Leave (Multiple Subject)`` and ``(Single
Subject)``. The disagreement is not a doubt here; it is the identification. Prose read.

The rule that separates them is not "do the two titles agree" but "did the title the page
publishes identify this authorization".

Variant sections
----------------

A leaflet matched by the named-family rule was matched by dropping a parenthesised qualifier
the Commission wrote in the authorization's title. Where the leaflet's own requirements
contain a sub-section headed with that same qualifier, that sub-section states the
requirements for that variant, and the equality is the same normalized one the matcher uses.

``Short-Term Staff Permit (Single Subject)`` takes the requirements under ``Single Subject:``.
``Short-Term Staff Permit (Special Education)`` takes nothing, because the leaflet heads that
breakdown ``Education Specialist:`` and deciding those two phrases mean the same thing would
be this project writing the Commission's key for it. That is a real gap and it is counted, in
``variant_qualifiers_no_heading_states`` in the coverage statement, rather than smoothed over.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from chalkline.model import Authorization, Catalog
from chalkline.sources import leaflet_pages, leaflets

NO_SNAPSHOT: Final = (
    "this repository holds no vendored snapshot of the leaflet page, so nothing was read "
    "from it; run `python scripts/fetch_sources.py leaflets <code>` to retrieve one"
)


def title_refusal(code: str, index_title: str, page_title: str) -> str:
    """Why a page matched through the index's title may not be read.

    The wording is the Commission's two names for the document and the reason the pair is not
    evidence, because a refusal that does not say what was found cannot be checked.
    """
    return (
        f"{code}: the index lists this leaflet as {index_title!r} and the page titles itself "
        f"{page_title!r}; a page whose own title is not the title it was matched under is not "
        "evidence about the authorization it was matched to"
    )


def code_refusal(code: str, page_title: str) -> str:
    """Why a page matched on a document code alone may not be read."""
    return (
        f"{code}: this leaflet was identified by the document code its title names, not by a "
        f"title, and the page titles itself {page_title!r}, which is not the authorization's "
        "published title; a code says which document the leaflet is for and not which of its "
        "words describe that document"
    )


DESCRIPTION_SECTIONS: Final = (leaflet_pages.AUTHORIZATION,)
"""Section kinds whose text joins the leaflet's lead to form ``ceterms:description``.

The lead is the Commission's prose directly under the leaflet's own title, and an
``Authorization`` section is its prose about what the document lets its holder do. Both are
a "statement, characterization or account of the entity", which is what CTDL's description
says it is. Sections of every other kind are conditions or definitions and are not
descriptions, so they never land here.
"""


@dataclass(frozen=True, slots=True)
class Attachment:
    """One authorization's leaflet: how it was matched, and what could be read from it."""

    match: leaflets.Match
    page: leaflet_pages.LeafletPage | None
    refusal: str | None

    @property
    def leaflet(self) -> leaflets.Leaflet:
        return self.match.leaflet

    @property
    def description(self) -> tuple[str, ...]:
        """The Commission's prose about this document, in the order the leaflet prints it."""
        if self.page is None:
            return ()
        blocks = list(self.page.lead)
        for section in self.page.of_kind(*DESCRIPTION_SECTIONS):
            blocks.extend(section.blocks)
        return tuple(blocks)

    @property
    def variant_sections(self) -> tuple[leaflet_pages.Section, ...]:
        """The requirements the leaflet states for this authorization's own variant.

        Empty unless the leaflet was matched by the named-family rule, which is the only rule
        that leaves a qualifier the Commission wrote. The comparison is the same normalized
        title equality the matcher uses, against the Commission's own sub-heading.
        """
        if self.page is None or self.match.qualifier is None:
            return ()
        wanted = leaflets.normalize_title(self.match.qualifier)
        return tuple(
            section
            for section in self.page.variants_within(leaflet_pages.REQUIREMENTS)
            if leaflets.normalize_title(section.heading) == wanted
        )

    @property
    def variant_unstated(self) -> str | None:
        """This authorization's qualifier, where the leaflet breaks out variants but not this.

        ``None`` where there is nothing to say: no qualifier, no page, or a leaflet that does
        not break its requirements out by variant at all. A qualifier reported here is a
        statement the Commission published for its other variants and not for this one.
        """
        if self.page is None or self.match.qualifier is None or self.variant_sections:
            return None
        if not self.page.variants_within(leaflet_pages.REQUIREMENTS):
            return None
        return self.match.qualifier

    @property
    def requirements(self) -> tuple[leaflet_pages.Section, ...]:
        """The leaflet's requirements for this authorization: the common ones, then its own.

        Order is the leaflet's own: a variant section is printed under the requirements
        section it sits inside, and it is emitted after it for the same reason.
        """
        if self.page is None:
            return ()
        return self.page.of_kind(leaflet_pages.REQUIREMENTS) + self.variant_sections

    @property
    def renewal(self) -> tuple[leaflet_pages.Section, ...]:
        if self.page is None:
            return ()
        return self.page.of_kind(leaflet_pages.RENEWAL, leaflet_pages.VALIDITY)

    @property
    def unread_headings(self) -> tuple[str, ...]:
        """In-scope headings that contributed nothing *to this authorization*.

        The page's own list of unclassified headings is the wrong answer here. "Single
        Subject:" is unclassified on the page and is read for the authorization whose title
        carries that qualifier, so publishing the page's list would count a heading as passed
        over for the very authorization that used it.
        """
        if self.page is None:
            return ()
        read = {section.heading for section in self.variant_sections}
        return tuple(h for h in self.page.skipped_headings if h not in read)

    @property
    def stopped_at(self) -> str | None:
        """The heading, if any, where this leaflet stopped being read, page-title-verified.

        ``None`` means the page was read to its end, or that there is no page at all (no
        snapshot, or one refused for identity -- see :func:`readable_for`). A leaflet that
        stopped partway may state more about this authorization after that heading (see
        :mod:`chalkline.sources.leaflet_pages` for why reading stops there), and this project
        does not know whether it does or guess at it. What it does do is count this rather
        than let a truncated read look identical, in the coverage statement, to a leaflet
        that was read whole and simply states nothing further: see
        ``authorizations_with_a_leaflet_reading_stopped_before_the_end`` in
        :func:`chalkline.ctdl.export.coverage`.
        """
        return None if self.page is None else self.page.stopped_at

    @property
    def classified_beyond_the_stop(self) -> tuple[str, ...]:
        """Headings this project's own classifier recognises that the stop left unread.

        The size of the omission :attr:`stopped_at` discloses. An empty tuple means the stop
        cost this authorization nothing a heading would have offered, which is a different
        answer from "reading stopped" and, until this was counted, indistinguishable from it.
        Of the sixteen attached authorizations whose read stopped, exactly one is in that
        position: the Reading and Literacy Added Authorization, whose CL-812 stops at a
        heading with nothing classified after it. The other fifteen lose between one and five
        headings each, the worst being the three Speech-Language Pathology Services Credential
        entries, whose CL-879 stops before four "Requirements for ..." headings and a
        "Terms and Definitions:".

        Not a claim of loss. Where the stop was right, as at CL-380's move to the Special
        Teaching Authorization in Health, these belong to another Commission document and not
        reading them is the point. Telling that case from CL-879's, where the same rule fires
        on a subsection of the leaflet's own subject, is issue #36 and is not decided here.
        """
        return () if self.page is None else self.page.classified_beyond_the_stop

    @property
    def stated_conditions(self) -> tuple[leaflet_pages.Section, ...]:
        """The requirement and renewal sections the Commission put text under.

        A heading with nothing beneath it is a heading. The export emits a condition profile
        only for a section with blocks, and the page prints one only for a section with
        blocks, so anything counting conditions has to apply the same rule or it will publish
        a total that neither the graph nor the page can show.
        """
        return tuple(section for section in self.requirements + self.renewal if section.blocks)


def read_leaflet(
    leaflet: leaflets.Leaflet, directory: Path | None = None
) -> tuple[leaflet_pages.LeafletPage | None, str | None]:
    """One leaflet page, or the reason the snapshot could not be parsed at all.

    This is the file question only: is there a snapshot, and is it the document that was
    asked for. Whether the page may be *used* for a given authorization is
    :func:`readable_for`, because that answer differs between two authorizations matched to
    the same page.
    """
    try:
        return leaflet_pages.load(leaflet.code, directory), None
    except FileNotFoundError:
        return None, NO_SNAPSHOT
    except ValueError as refusal:
        return None, str(refusal)


def readable_for(match: leaflets.Match, page: leaflet_pages.LeafletPage) -> str | None:
    """``None`` where this page's own title is a title that identified this authorization.

    A match made against the page's own title satisfies this by construction. A match made
    against the index's title needs the page to agree with the index. A match made against a
    document code was never a title match, so it never permits a read.
    """
    if match.published_by == leaflets.FROM_PAGE:
        return None
    if match.published_by == leaflets.FROM_DOCUMENT_CODE:
        return code_refusal(match.leaflet.code, page.page_title)
    if leaflets.normalize_title(page.page_title) == leaflets.normalize_title(match.leaflet.title):
        return None
    return title_refusal(match.leaflet.code, match.leaflet.title, page.page_title)


def match_for(
    authorization: Authorization,
    by_index_title: Mapping[str, leaflets.Leaflet],
    by_page_title: Mapping[str, leaflets.Leaflet],
    by_document_code: Mapping[str, leaflets.Leaflet],
) -> leaflets.Match | None:
    """The one leaflet this authorization is attached to, by the first rule that fires.

    The order is strongest-name-first: a leaflet the Commission's index names for this
    authorization beats one that names it only on its own page, and a title of any kind beats
    a bare code. Every rule is an equality, so the order decides which evidence is cited and
    never whether there is any.
    """
    return (
        leaflets.match_title(authorization.title, by_index_title, leaflets.FROM_INDEX)
        or leaflets.match_title(authorization.title, by_page_title, leaflets.FROM_PAGE)
        or leaflets.match_document_code(authorization.document_title, by_document_code)
    )


def page_titles(
    published: Sequence[leaflets.Leaflet], directory: Path | None = None
) -> tuple[
    dict[str, leaflets.Leaflet], dict[str, tuple[leaflet_pages.LeafletPage | None, str | None]]
]:
    """Each vendored leaflet's own title, as a second index, plus every page read.

    Only leaflets this repository holds a snapshot for can contribute a page title, which is
    the honest limit of the rule: the Commission's own name for a document is evidence this
    project has only where it has retrieved the document.

    A title two pages share is dropped, exactly as an ambiguous index title is.
    """
    pages: dict[str, tuple[leaflet_pages.LeafletPage | None, str | None]] = {}
    titles: dict[str, list[leaflets.Leaflet]] = {}
    for leaflet in published:
        page, refusal = read_leaflet(leaflet, directory)
        pages[leaflet.code] = (page, refusal)
        if page is not None:
            titles.setdefault(leaflets.normalize_title(page.page_title), []).append(leaflet)
    return {key: found[0] for key, found in titles.items() if len(found) == 1}, pages


def attach(
    catalog: Catalog,
    index: Mapping[str, leaflets.Leaflet],
    directory: Path | None = None,
    published: Sequence[leaflets.Leaflet] = (),
) -> dict[str, Attachment]:
    """Every authorization that has a leaflet, keyed by the authorization's published triple.

    Each leaflet page is read once however many authorizations it serves, so the six
    Short-Term Staff Permit and Provisional Internship Permit entries share one parse rather
    than reaching different conclusions about the same file. The refusal, unlike the parse,
    is per authorization: the same page can be evidence about one and not about another.

    ``published`` is the full leaflet list, needed to read page titles and document codes.
    It defaults to the values of ``index``, which is every leaflet with an unambiguous index
    title --- enough for the title rules, and all a caller that has only an index can give.
    """
    leaflet_list = tuple(published) or tuple(dict.fromkeys(index.values()))
    by_page_title, pages = page_titles(leaflet_list, directory)
    by_document_code = leaflets.index_by_document_code(
        leaflet_list, {a.document_title for a in catalog.authorizations}
    )
    attachments: dict[str, Attachment] = {}
    for authorization in catalog.authorizations:
        match = match_for(authorization, index, by_page_title, by_document_code)
        if match is None:
            continue
        page, refusal = pages.get(match.leaflet.code, (None, NO_SNAPSHOT))
        if page is not None:
            refusal = readable_for(match, page)
            page = None if refusal is not None else page
        attachments[authorization.key] = Attachment(match=match, page=page, refusal=refusal)
    return attachments
