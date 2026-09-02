"""The page states what it is, escapes what it renders, and counts what it shows."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from chalkline import ctid as ctid_module
from chalkline.attachment import Attachment
from chalkline.model import Authorization, Catalog, build_catalog
from chalkline.site import render
from chalkline.sources import leaflet_pages, sort_table
from chalkline.sources import leaflets as leaflets_module
from tests.conftest import row, table

VOID = {"meta", "br", "hr", "img", "input", "link", "source", "area", "col"}


class _Balance(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.unbalanced: list[str] = []

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            self.unbalanced.append(tag)
        else:
            self.stack.pop()


def rendered(catalog: Catalog) -> str:
    ctids = {a.key: ctid_module.mint() for a in catalog.authorizations}
    return render(catalog, ctids, {})


def test_the_page_is_balanced_html(
    real_catalog: Catalog, real_attachments: dict[str, Attachment]
) -> None:
    ctids = ctid_module.load_ledger()
    parser = _Balance()
    parser.feed(render(real_catalog, ctids, real_attachments))
    assert parser.unbalanced == []
    assert parser.stack == []


def test_the_page_says_it_is_unofficial(real_catalog: Catalog) -> None:
    page = render(real_catalog, ctid_module.load_ledger(), {})
    assert "Unofficial demonstration" in page
    assert "not affiliated" in page.lower()
    assert "Credential Engine" in page


# ---------------------------------------------------------------------------
# The head, and the shared origin it has to survive
#
# The page is served at a path under chelseakr.github.io, which five sibling
# projects also publish under, and https://chelseakr.github.io/ is itself a
# 404. A canonical naming the bare origin, or a root-relative href, is invisible
# in a browser and wrong to everything that reads a head. So it is checked here.
#
# The expected address is written out rather than imported from
# chalkline.site.SITE_URL. A check that builds its expectation out of the
# constant it is checking moves with the mistake and stays green, which is the
# shape of check that cannot fail.
# ---------------------------------------------------------------------------

PUBLISHED_AT = "https://chelseakr.github.io/chalkline/"


def head_of(page: str) -> str:
    return page.split("</head>", 1)[0]


def test_the_page_carries_a_self_referencing_canonical(real_catalog: Catalog) -> None:
    head = head_of(render(real_catalog, ctid_module.load_ledger(), {}))
    assert f'<link rel="canonical" href="{PUBLISHED_AT}">' in head
    assert f'<meta property="og:url" content="{PUBLISHED_AT}">' in head


def test_the_constant_the_page_is_built_from_is_the_published_path() -> None:
    from chalkline.site import SITE_URL

    assert SITE_URL == PUBLISHED_AT


def test_the_page_describes_itself(real_catalog: Catalog) -> None:
    # The page had a title and no description at all, so anything that reads a
    # head had nothing to read but the title.
    head = head_of(render(real_catalog, ctid_module.load_ledger(), {}))
    described = re.search(r'<meta name="description" content="([^"]+)"', head)
    assert described is not None
    assert described.group(1).strip()
    # The card and the page are two statements about one thing, so they are
    # held equal rather than each checked for being non-empty.
    assert f'<meta property="og:description" content="{described.group(1)}">' in head
    titled = re.search(r"<title>([^<]+)</title>", head)
    assert titled is not None
    assert f'<meta property="og:title" content="{titled.group(1)}">' in head
    assert '<meta property="og:type" content="website">' in head
    assert '<meta property="og:site_name" content="Chalkline">' in head
    assert '<meta name="twitter:card" content="summary">' in head


def test_the_description_claims_nothing_the_page_does_not(real_catalog: Catalog) -> None:
    # This project is unofficial and says so on its face. A description that
    # dropped the word, or that quoted a figure, would be a claim made in a
    # place no reader of the page can see and no other test reads.
    head = head_of(render(real_catalog, ctid_module.load_ledger(), {}))
    described = re.search(r'<meta name="description" content="([^"]+)"', head)
    assert described is not None
    description = described.group(1)
    assert "unofficial" in description.lower()
    assert re.search(r"\b[0-9]+\b", description) is None, (
        f"the description states a figure nothing derives: {description!r}"
    )


def test_the_page_makes_no_root_relative_reference(
    real_catalog: Catalog, real_attachments: dict[str, Attachment]
) -> None:
    # `href="/x"` resolves against chelseakr.github.io, not against
    # /chalkline/, so it lands on another project or on nothing. Protocol-
    # relative `//host/x` is a different thing and is excluded deliberately.
    page = render(real_catalog, ctid_module.load_ledger(), real_attachments)
    rooted = re.findall(r'(?:href|src|content)="(/(?!/)[^"]*)"', page)
    assert rooted == [], f"root-relative references escape /chalkline/: {rooted}"


def test_counts_come_from_the_catalog(real_catalog: Catalog) -> None:
    page = render(real_catalog, ctid_module.load_ledger(), {})
    assert f"<b>{len(real_catalog.authorizations)}</b>" in page
    assert f"<b>{len(real_catalog.exclusions)}</b>" in page


def test_every_exclusion_and_its_reason_are_shown(real_catalog: Catalog) -> None:
    page = render(real_catalog, ctid_module.load_ledger(), {})
    for exclusion in real_catalog.exclusions:
        assert html.escape(exclusion.reason, quote=True) in page
        assert html.escape(exclusion.title, quote=True) in page


def test_markup_in_source_text_is_escaped() -> None:
    """A cell whose *text* is angle brackets, written as entities the way HTML requires."""
    catalog = build_catalog(
        sort_table.parse(
            table(row(title="Cred &lt;script&gt;alert(1)&lt;/script&gt;", subject="A &amp; B"))
        )
    )
    parsed = catalog.authorizations[0]
    assert parsed.title == "Cred <script>alert(1)</script>"
    page = rendered(catalog)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "A &amp; B" in page


def test_a_not_subject_coded_credential_says_so() -> None:
    catalog = build_catalog(sort_table.parse(table(row(subject_code="NONE", subject=""))))
    assert "not subject-coded" in rendered(catalog)


def test_the_none_claim_is_read_off_the_flag_and_not_off_an_empty_list() -> None:
    """The page quotes the Commission's ``NONE`` only where the Commission published it.

    `declares_no_subject_codes` is the field that records that the Commission published
    ``NONE``; an empty subject tuple only records that this authorization has no subjects.
    The page used to print the ``NONE`` sentence from the empty tuple, which is a statement
    about the source made from something that is not evidence of it.
    """
    silent = Authorization(
        document_title="TC1",
        title="Silent Credential",
        authorization_code="ZZZ",
        document_codes=("TC1",),
        authorization_codes=("ZZZ",),
        subjects=(),
        declares_no_subject_codes=False,
        shared_notes=(),
    )
    page = rendered(Catalog(authorizations=(silent,), exclusions=(), source_rows=1))
    assert "not subject-coded" not in page
    assert "did not publish <code>NONE</code>" in page


def test_every_modeled_authorization_has_subjects_or_declares_none(
    real_catalog: Catalog,
) -> None:
    """The invariant that made the old branch true, stated instead of relied upon.

    `build_catalog` excludes an authorization whose subjects are neither published nor
    reachable through a cross-reference, so a modeled one always lands in exactly one of the
    two states the page renders. That held by construction across three separate code paths
    and nothing asserted it, which is why printing the ``NONE`` sentence from the wrong
    variable stayed invisible.
    """
    for authorization in real_catalog.authorizations:
        assert bool(authorization.subjects) != authorization.declares_no_subject_codes, (
            f"{authorization.key} carries neither subjects nor the Commission's NONE"
        )


def attached(
    catalog: Catalog, page: leaflet_pages.LeafletPage | None, refusal: str | None
) -> dict[str, Attachment]:
    leaflet = leaflets_module.Leaflet(
        code="cl-380", title="School Nurse Services Credential", url="https://example.gov/380"
    )
    match = leaflets_module.Match(leaflet=leaflet, rule=leaflets_module.MATCH_EXACT_TITLE)
    return {
        a.key: Attachment(match=match, page=page, refusal=refusal) for a in catalog.authorizations
    }


def test_a_leaflet_link_appears_when_one_matched() -> None:
    catalog = build_catalog(sort_table.parse(table(row(title="School Nurse Services Credential"))))
    ctids = {a.key: ctid_module.mint() for a in catalog.authorizations}
    page = render(catalog, ctids, attached(catalog, None, "not read, for this test"))
    assert "https://example.gov/380" in page
    assert "Leaflet CL-380" in page
    assert "not read, for this test" in page


def test_leaflet_prose_and_conditions_are_shown() -> None:
    catalog = build_catalog(sort_table.parse(table(row(title="School Nurse Services Credential"))))
    ctids = {a.key: ctid_module.mint() for a in catalog.authorizations}
    leaflet_page = leaflet_pages.LeafletPage(
        code="cl-380",
        page_title="School Nurse Services Credential",
        lead=("What this credential is.",),
        sections=(
            leaflet_pages.Section(
                heading="Requirements",
                level=2,
                kind=leaflet_pages.REQUIREMENTS,
                blocks=("Hold a licence.",),
            ),
            leaflet_pages.Section(
                heading="Term of the Credential",
                level=2,
                kind=leaflet_pages.VALIDITY,
                blocks=("Five years.",),
            ),
        ),
        stopped_at=None,
        skipped_headings=(),
    )
    rendered_page = render(catalog, ctids, attached(catalog, leaflet_page, None))
    assert "What this credential is." in rendered_page
    assert "Description from leaflet CL-380." in rendered_page
    assert "Requirements: Requirements" in rendered_page
    assert "Renewal and validity: Term of the Credential" in rendered_page
    assert "Five years." in rendered_page


def test_a_section_with_no_text_renders_nothing() -> None:
    """The same rule the export applies: an empty section is not a requirement."""
    catalog = build_catalog(sort_table.parse(table(row(title="School Nurse Services Credential"))))
    ctids = {a.key: ctid_module.mint() for a in catalog.authorizations}
    empty = leaflet_pages.LeafletPage(
        code="cl-380",
        page_title="School Nurse Services Credential",
        lead=(),
        sections=(
            leaflet_pages.Section(
                heading="Requirements", level=2, kind=leaflet_pages.REQUIREMENTS, blocks=()
            ),
        ),
        stopped_at=None,
        skipped_headings=(),
    )
    page = render(catalog, ctids, attached(catalog, empty, None))
    assert "No requirements or renewal terms" in page
    assert "Requirements: Requirements" not in page
    # And the headline count says the same thing the credential below it says. A heading the
    # Commission put no text under is a heading, not a requirement, and counting it here
    # would have the page contradict itself in two places at once.
    assert "<b>0</b><span>carrying requirements or renewal terms</span>" in page
    assert "<b>1</b><span>carrying requirements or renewal terms</span>" not in page


def test_absence_is_stated_rather_than_hidden() -> None:
    catalog = build_catalog(sort_table.parse(table(row(subject_code="ART", subject="Art"))))
    page = rendered(catalog)
    assert "No description." in page
    assert "No requirements or renewal terms" in page


def test_a_resolved_scope_names_the_rows_it_came_from() -> None:
    catalog = build_catalog(
        sort_table.parse(
            table(
                row(subject_code="ART", subject="Art"),
                row(
                    document="TC13",
                    title="Short-Term Staff Permit",
                    subject_code="",
                    subject="",
                    notes=("Subject Codes Same as on Single Subject Teaching Credential",),
                ),
            )
        )
    )
    page = rendered(catalog)
    assert "Subject Codes Same as on Single Subject Teaching Credential" in page
    assert "Single Subject Teaching Credential" in page
    assert "<b>1</b><span>scopes resolved by following a cross-reference</span>" in page


def test_singular_and_plural_subject_counts() -> None:
    one = build_catalog(sort_table.parse(table(row(subject_code="ART", subject="Art"))))
    assert "1 authorized subject<" in rendered(one)
    two = build_catalog(
        sort_table.parse(
            table(row(subject_code="ART", subject="Art"), row(subject_code="MUS", subject="Music"))
        )
    )
    assert "2 authorized subjects<" in rendered(two)


def test_a_credential_without_an_authorization_code_still_renders() -> None:
    catalog = build_catalog(sort_table.parse(table(row(code="", subject_code="NONE", subject=""))))
    page = rendered(catalog)
    assert "authorization <code>" not in page
    assert re.search(r"document <code>TC1</code>", page)
