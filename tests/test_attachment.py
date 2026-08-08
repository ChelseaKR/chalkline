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
