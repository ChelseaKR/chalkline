"""A leaflet page is read only as far as it describes the document it is titled for."""

from __future__ import annotations

from pathlib import Path

import pytest

from chalkline.sources import leaflet_pages, leaflets

FOOTER = '<div class="et_pb_with_border et_pb_section et_pb_section_5" ><p>Get Involved</p></div>'


def page(title: str, body: str, footer: str = FOOTER) -> str:
    return (
        "<html><body><article>"
        f'<h1 class="entry-title">{title}</h1>{body}{footer}'
        "</article></body></html>"
    )


def test_a_page_is_read_into_a_lead_and_classified_sections() -> None:
    parsed = leaflet_pages.parse(
        page(
            "School Nurse Services Credential (CL-380)",
            "<p>What it is.</p>"
            "<h2>Requirements</h2><p>Hold a licence.</p><ul><li>And a degree.</li></ul>"
            "<h2>Term of the Credential</h2><p>Five years.</p>",
        ),
        "cl-380",
        "School Nurse Services Credential",
    )
    assert parsed.page_title == "School Nurse Services Credential"
    assert parsed.lead == ("What it is.",)
    assert [(s.heading, s.kind) for s in parsed.sections] == [
        ("Requirements", leaflet_pages.REQUIREMENTS),
        ("Term of the Credential", leaflet_pages.VALIDITY),
    ]
    assert parsed.sections[0].blocks == ("Hold a licence.", "And a degree.")
    assert parsed.stopped_at is None


def test_reading_stops_where_the_leaflet_moves_on_to_another_document() -> None:
    """CL-380's real shape: a second credential, with its own requirements, further down."""
    parsed = leaflet_pages.parse(
        page(
            "School Nurse Services Credential (CL-380)",
            "<h2>Requirements for the Preliminary Credential</h2><p>Mine.</p>"
            "<h2>Other Health Services Credentials</h2>"
            "<h3>Requirements for the Clear Credential</h3><p>Not mine.</p>",
        ),
        "cl-380",
        "School Nurse Services Credential",
    )
    assert [s.heading for s in parsed.sections] == ["Requirements for the Preliminary Credential"]
    assert parsed.stopped_at == "Other Health Services Credentials"
    assert "Not mine." not in str(parsed.sections)


def test_reading_stops_at_a_repeated_heading() -> None:
    parsed = leaflet_pages.parse(
        page(
            "A Thing (CL-1)",
            "<h2>Requirements</h2><p>First.</p><h2>Requirements</h2><p>Second.</p>",
        ),
        "cl-1",
        "A Thing",
    )
    assert parsed.stopped_at == "Requirements"
    assert parsed.sections[0].blocks == ("First.",)


def test_an_unclassified_heading_that_names_nothing_is_skipped_not_a_stop() -> None:
    parsed = leaflet_pages.parse(
        page(
            "A Thing (CL-1)",
            "<h2>Requirements</h2><p>Mine.</p>"
            "<h3>Commission-Approved Agencies:</h3><p>A list.</p>"
            "<h2>Period of Validity</h2><p>Forever.</p>",
        ),
        "cl-1",
        "A Thing",
    )
    assert parsed.stopped_at is None
    assert parsed.skipped_headings == ("Commission-Approved Agencies:",)
    assert [s.heading for s in parsed.of_kind(leaflet_pages.VALIDITY)] == ["Period of Validity"]


def test_a_page_whose_code_disagrees_with_the_index_is_refused() -> None:
    with pytest.raises(ValueError, match="not the leaflet the index named"):
        leaflet_pages.parse(page("A Thing (CL-2)", "<p>x</p>"), "cl-1", "A Thing")


def test_a_page_whose_title_disagrees_with_the_index_is_refused() -> None:
    """CL-893 really does this: the index and the page name the credential differently."""
    with pytest.raises(ValueError, match="not evidence about the authorization"):
        leaflet_pages.parse(
            page("American Indian Languages-Culture Credential (CL-893)", "<p>x</p>"),
            "cl-893",
            "American Indian Languages Credential",
        )


def test_a_page_with_no_coded_title_is_refused() -> None:
    with pytest.raises(ValueError, match="does not read"):
        leaflet_pages.parse(page("A Thing", "<p>x</p>"), "cl-1", "A Thing")


def test_a_page_with_no_title_is_refused() -> None:
    with pytest.raises(ValueError, match="publishes no"):
        leaflet_pages.parse(
            "<html><body><article><p>x</p>" + FOOTER + "</article></body></html>",
            "cl-1",
            "A Thing",
        )


def test_a_page_with_no_footer_boundary_is_refused() -> None:
    with pytest.raises(ValueError, match="where the Commission's content ends"):
        leaflet_pages.parse(page("A Thing (CL-1)", "<p>x</p>", footer=""), "cl-1", "A Thing")


def test_a_page_without_exactly_one_article_is_refused() -> None:
    with pytest.raises(ValueError, match="exactly one <article>"):
        leaflet_pages.parse("<html><body>no article</body></html>", "cl-1", "A Thing")


def test_empty_headings_and_blocks_contribute_nothing() -> None:
    parsed = leaflet_pages.parse(
        page("A Thing (CL-1)", "<p>&nbsp;</p><h2> </h2><h2>Requirements</h2><p></p><p>Real.</p>"),
        "cl-1",
        "A Thing",
    )
    assert parsed.lead == ()
    assert parsed.sections[0].blocks == ("Real.",)


@pytest.mark.parametrize(
    ("heading", "kind"),
    [
        ("Requirements for Issuance", leaflet_pages.REQUIREMENTS),
        ("Requirements for One Time Renewal", leaflet_pages.RENEWAL),
        ("One-Time Renewal:", leaflet_pages.RENEWAL),
        ("Period of Validity", leaflet_pages.VALIDITY),
        ("Term of the Credential", leaflet_pages.VALIDITY),
        ("Authorization", leaflet_pages.AUTHORIZATION),
        ("Authorization:", leaflet_pages.AUTHORIZATION),
        ("Terms and Definitions", leaflet_pages.DEFINITIONS),
        ("Definition of Experience Requirement", leaflet_pages.DEFINITIONS),
        ("Introduction", leaflet_pages.INTRODUCTION),
        ("Bilingual Authorizations", leaflet_pages.UNCLASSIFIED),
        ("Single Subject:", leaflet_pages.UNCLASSIFIED),
        ("", leaflet_pages.UNCLASSIFIED),
    ],
)
def test_the_classification_vocabulary_is_the_published_one(heading: str, kind: str) -> None:
    assert leaflet_pages.classify(heading) == kind


def test_every_vendored_leaflet_either_parses_or_says_why(
    real_leaflets: tuple[leaflets.Leaflet, ...],
) -> None:
    """No vendored snapshot fails in a way this project has not accounted for.

    The refusal branch ends in ``continue``, so every assertion after it is skippable. With
    no count of how many snapshots actually reached them, a parser that refused all ten
    would go green exactly like one that read all ten. The Commission's index refuses
    exactly one page (cl-893, on a title mismatch), so nine is the number that has to parse.
    """
    index = {leaflet.code: leaflet for leaflet in real_leaflets}
    assert leaflet_pages.available(), "the repository should hold leaflet snapshots"
    read = 0
    for code in leaflet_pages.available():
        assert code in index, f"{code} is not a leaflet the Commission's index publishes"
        try:
            parsed = leaflet_pages.load(code, index[code].title)
        except ValueError as refusal:
            assert code in str(refusal)
            continue
        assert parsed.code == code
        assert parsed.lead or parsed.sections
        read += 1
    assert read == 9, f"only {read} snapshots parsed, so the assertions above ran {read} times"


def test_available_is_empty_when_there_is_no_snapshot_directory(tmp_path: Path) -> None:
    assert leaflet_pages.available(tmp_path / "nowhere") == ()
