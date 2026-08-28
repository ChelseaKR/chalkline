"""Which leaflet describes which authorization, and what may be read from it."""

from __future__ import annotations

from pathlib import Path

from chalkline.attachment import NO_SNAPSHOT, Attachment, attach
from chalkline.model import Catalog, build_catalog
from chalkline.sources import leaflet_pages, leaflets, sort_table
from tests.conftest import row, table


def catalog_of(*titles: str) -> Catalog:
    return build_catalog(
        sort_table.parse(
            table(*(row(title=title, subject_code="NONE", subject="") for title in titles))
        )
    )


def index_of(*pairs: tuple[str, str]) -> dict[str, leaflets.Leaflet]:
    return leaflets.index_by_title(
        tuple(
            leaflets.Leaflet(code=code, title=title, url=f"https://example.gov/{code}/")
            for code, title in pairs
        )
    )


def test_an_exact_title_matches_and_names_its_rule() -> None:
    index = index_of(("cl-380", "School Nurse Services Credential"))
    match = leaflets.match_title("School Nurse Services Credential", index)
    assert match is not None
    assert match.rule == leaflets.MATCH_EXACT_TITLE
    assert match.qualifier is None


def test_a_parenthesised_qualifier_matches_the_family_leaflet() -> None:
    index = index_of(("cl-858", "Short-Term Staff Permit"))
    match = leaflets.match_title("Short-Term Staff Permit (Special Education)", index)
    assert match is not None
    assert match.rule == leaflets.MATCH_NAMED_FAMILY
    assert match.qualifier == "Special Education"


def test_the_family_rule_is_an_equality_not_a_prefix() -> None:
    """The rule this project rejected: a leaflet whose title merely starts with the title."""
    index = index_of(
        ("cl-808", "Education Specialist Instruction Credential Requirements for Teachers")
    )
    assert leaflets.match_title("Education Specialist Instruction Credential", index) is None


def test_a_title_with_no_trailing_parenthetical_does_not_reach_the_family_rule() -> None:
    index = index_of(("cl-889", "Special Education Limited Assignment Permit"))
    assert (
        leaflets.match_title("Special Education Limited Assignment Teaching Permit", index) is None
    )


def test_a_parenthetical_that_is_not_trailing_does_not_match() -> None:
    index = index_of(("cl-610", "Clinical or Rehabilitative Services Credential"))
    assert (
        leaflets.match_title("Clinical or Rehabilitative Services (CRS) Credential", index) is None
    )


def test_the_exact_rule_wins_over_the_family_rule() -> None:
    index = index_of(
        ("cl-1", "Short-Term Staff Permit"),
        ("cl-2", "Short-Term Staff Permit (Single Subject)"),
    )
    match = leaflets.match_title("Short-Term Staff Permit (Single Subject)", index)
    assert match is not None
    assert match.leaflet.code == "cl-2"
    assert match.rule == leaflets.MATCH_EXACT_TITLE


def test_a_missing_snapshot_is_recorded_rather_than_raised(tmp_path: Path) -> None:
    catalog = catalog_of("School Nurse Services Credential")
    index = index_of(("cl-380", "School Nurse Services Credential"))
    (attachment,) = attach(catalog, index, tmp_path).values()
    assert attachment.page is None
    assert attachment.refusal == NO_SNAPSHOT
    assert attachment.description == ()
    assert attachment.requirements == ()
    assert attachment.renewal == ()
    assert attachment.leaflet.code == "cl-380"


def test_an_unmatched_authorization_gets_no_attachment(tmp_path: Path) -> None:
    catalog = catalog_of("Something Else Entirely")
    index = index_of(("cl-380", "School Nurse Services Credential"))
    assert attach(catalog, index, tmp_path) == {}


def test_description_is_the_lead_then_the_authorization_section() -> None:
    page = leaflet_pages.LeafletPage(
        code="cl-1",
        page_title="A Thing",
        lead=("Opening prose.",),
        sections=(
            leaflet_pages.Section(
                heading="Authorization",
                level=2,
                kind=leaflet_pages.AUTHORIZATION,
                blocks=("What it lets you do.",),
            ),
            leaflet_pages.Section(
                heading="Requirements",
                level=2,
                kind=leaflet_pages.REQUIREMENTS,
                blocks=("Hold a degree.",),
            ),
            leaflet_pages.Section(
                heading="Renewal",
                level=2,
                kind=leaflet_pages.RENEWAL,
                blocks=("Every five years.",),
            ),
        ),
        stopped_at=None,
        classified_beyond_the_stop=(),
        skipped_headings=(),
    )
    leaflet = leaflets.Leaflet(code="cl-1", title="A Thing", url="https://example.gov/1/")
    attachment = Attachment(
        match=leaflets.Match(leaflet=leaflet, rule=leaflets.MATCH_EXACT_TITLE),
        page=page,
        refusal=None,
    )
    assert attachment.description == ("Opening prose.", "What it lets you do.")
    assert [s.heading for s in attachment.requirements] == ["Requirements"]
    assert [s.heading for s in attachment.renewal] == ["Renewal"]


def test_one_leaflet_page_is_read_once_however_many_authorizations_share_it(
    real_catalog: Catalog, real_attachments: dict[str, Attachment]
) -> None:
    by_code: dict[str, set[int]] = {}
    for attachment in real_attachments.values():
        by_code.setdefault(attachment.leaflet.code, set()).add(id(attachment.page))
    assert all(len(pages) == 1 for pages in by_code.values())
    assert len(real_attachments) > len(by_code), "some leaflet should serve several titles"


def test_the_vendored_attachments_are_all_accounted_for(
    real_attachments: dict[str, Attachment],
) -> None:
    """Every attachment either read its page or says, in one string, why it did not."""
    for attachment in real_attachments.values():
        assert (attachment.page is None) == (attachment.refusal is not None)


def leaflet_page(
    *sections: leaflet_pages.Section, title: str = "A Thing"
) -> leaflet_pages.LeafletPage:
    return leaflet_pages.LeafletPage(
        code="cl-1",
        page_title=title,
        lead=(),
        sections=sections,
        stopped_at=None,
        classified_beyond_the_stop=(),
        skipped_headings=tuple(s.heading for s in sections if s.kind == leaflet_pages.UNCLASSIFIED),
    )


def family_attachment(page: leaflet_pages.LeafletPage, qualifier: str) -> Attachment:
    leaflet = leaflets.Leaflet(code="cl-1", title="A Thing", url="https://example.gov/1/")
    return Attachment(
        match=leaflets.Match(
            leaflet=leaflet, rule=leaflets.MATCH_NAMED_FAMILY, qualifier=qualifier
        ),
        page=page,
        refusal=None,
    )


REQUIREMENTS_SECTION = leaflet_pages.Section(
    heading="Requirements for Issuance",
    level=2,
    kind=leaflet_pages.REQUIREMENTS,
    blocks=("Common to all.",),
)
SINGLE_SUBJECT = leaflet_pages.Section(
    heading="Single Subject:",
    level=3,
    kind=leaflet_pages.UNCLASSIFIED,
    blocks=("Theirs alone.",),
    within=leaflet_pages.REQUIREMENTS,
)


def test_a_variant_section_the_qualifier_names_is_read_for_that_variant() -> None:
    attachment = family_attachment(
        leaflet_page(REQUIREMENTS_SECTION, SINGLE_SUBJECT), "Single Subject"
    )
    assert [s.heading for s in attachment.variant_sections] == ["Single Subject:"]
    assert [s.heading for s in attachment.requirements] == [
        "Requirements for Issuance",
        "Single Subject:",
    ]
    assert attachment.variant_unstated is None
    # The heading was read for this authorization, so it is not also passed over by it.
    assert attachment.unread_headings == ()


def test_a_qualifier_no_heading_states_is_recorded_rather_than_approximated() -> None:
    """CL-858 heads its third breakdown "Education Specialist:" for "(Special Education)"."""
    attachment = family_attachment(
        leaflet_page(REQUIREMENTS_SECTION, SINGLE_SUBJECT), "Special Education"
    )
    assert attachment.variant_sections == ()
    assert [s.heading for s in attachment.requirements] == ["Requirements for Issuance"]
    assert attachment.variant_unstated == "Special Education"
    assert attachment.unread_headings == ("Single Subject:",)


def test_a_leaflet_that_states_no_variants_at_all_reports_nothing_missing() -> None:
    """Absence of a breakdown is not a gap in one. Most family leaflets have no variants."""
    attachment = family_attachment(leaflet_page(REQUIREMENTS_SECTION), "Special Education")
    assert attachment.variant_sections == ()
    assert attachment.variant_unstated is None


def test_stopped_at_is_none_without_a_page() -> None:
    """Nothing was read, so there is nothing to say reading stopped partway through."""
    leaflet = leaflets.Leaflet(code="cl-1", title="A Thing", url="https://example.gov/1/")
    attachment = Attachment(
        match=leaflets.Match(leaflet=leaflet, rule=leaflets.MATCH_EXACT_TITLE),
        page=None,
        refusal=NO_SNAPSHOT,
    )
    assert attachment.stopped_at is None


def test_stopped_at_carries_the_page_s_own_stop_heading() -> None:
    """The parser's `LeafletPage.stopped_at` reaches the coverage statement through here.

    It used to stop here: `LeafletPage.stopped_at` was computed and tested at the parser
    level and then read by nothing downstream, so a leaflet read that stopped partway
    published exactly the same zero requirements/renewal as one read whole with nothing
    further to state (issue #36).
    """
    page = leaflet_page(title="A Thing")
    object.__setattr__(page, "stopped_at", "Some Other Credential")
    attachment = family_attachment(page, "Special Education")
    assert attachment.stopped_at == "Some Other Credential"


def test_a_snapshot_that_is_another_document_is_recorded_rather_than_raised(
    tmp_path: Path,
) -> None:
    """The one refusal the parser still makes: the page's <h1> names a different leaflet."""
    (tmp_path / "cl-380.html").write_text(
        '<html><body><article><h1 class="entry-title">Something Else (CL-999)</h1>'
        '<div class="et_pb_with_border et_pb_section" ><p>x</p></div></article></body></html>',
        encoding="utf-8",
    )
    catalog = catalog_of("School Nurse Services Credential")
    index = index_of(("cl-380", "School Nurse Services Credential"))
    (attachment,) = attach(catalog, index, tmp_path).values()
    assert attachment.page is None
    assert attachment.refusal is not None
    assert "not the leaflet the index named" in attachment.refusal
    assert attachment.description == ()
