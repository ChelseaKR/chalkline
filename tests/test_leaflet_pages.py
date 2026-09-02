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
    )
    assert parsed.stopped_at is None
    assert parsed.skipped_headings == ("Commission-Approved Agencies:",)
    assert [s.heading for s in parsed.of_kind(leaflet_pages.VALIDITY)] == ["Period of Validity"]


def test_a_page_whose_code_disagrees_with_the_index_is_refused() -> None:
    with pytest.raises(ValueError, match="not the leaflet the index named"):
        leaflet_pages.parse(page("A Thing (CL-2)", "<p>x</p>"), "cl-1")


def test_a_page_whose_title_disagrees_with_the_index_is_reported_not_refused() -> None:
    """CL-893 and CL-902 both do this, and they are opposite cases.

    The parser cannot tell them apart, because which one is a doubt and which one is an
    identification depends on the authorization being matched. So it reports the page's own
    title and :mod:`chalkline.attachment` decides. This used to raise here, which is the
    reason CL-902 could not be read at all.
    """
    parsed = leaflet_pages.parse(
        page("American Indian Languages-Culture Credential (CL-893)", "<p>x</p>"), "cl-893"
    )
    assert parsed.page_title == "American Indian Languages-Culture Credential"


def test_a_page_with_no_coded_title_is_refused() -> None:
    with pytest.raises(ValueError, match="does not read"):
        leaflet_pages.parse(page("A Thing", "<p>x</p>"), "cl-1")


def test_a_page_with_no_title_is_refused() -> None:
    with pytest.raises(ValueError, match="publishes no"):
        leaflet_pages.parse(
            "<html><body><article><p>x</p>" + FOOTER + "</article></body></html>",
            "cl-1",
        )


def test_a_page_with_no_footer_boundary_is_refused() -> None:
    with pytest.raises(ValueError, match="where the Commission's content ends"):
        leaflet_pages.parse(page("A Thing (CL-1)", "<p>x</p>", footer=""), "cl-1")


def test_a_page_without_exactly_one_article_is_refused() -> None:
    with pytest.raises(ValueError, match="exactly one <article>"):
        leaflet_pages.parse("<html><body>no article</body></html>", "cl-1")


def test_empty_headings_and_blocks_contribute_nothing() -> None:
    parsed = leaflet_pages.parse(
        page("A Thing (CL-1)", "<p>&nbsp;</p><h2> </h2><h2>Requirements</h2><p></p><p>Real.</p>"),
        "cl-1",
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


def test_a_nested_heading_records_the_section_it_sits_inside() -> None:
    """Reading the Commission's outline, which is what makes a variant section attributable."""
    parsed = leaflet_pages.parse(
        page(
            "Short-Term Staff Permit (CL-858)",
            "<h2>How to Apply</h2><p>Ask.</p>"
            "<h2>Requirements for Issuance</h2><p>Common.</p>"
            "<h3>Single Subject:</h3><p>Theirs.</p>"
            "<h2>Period of Validity</h2><p>A year.</p>"
            "<h3>Renewing:</h3><p>Not requirements.</p>",
        ),
        "cl-858",
    )
    within = {s.heading: s.within for s in parsed.sections}
    assert within["How to Apply"] == leaflet_pages.UNCLASSIFIED
    assert within["Single Subject:"] == leaflet_pages.REQUIREMENTS
    assert within["Requirements for Issuance"] == leaflet_pages.UNCLASSIFIED
    # "Period of Validity" is at the same level as the requirements heading, so it closes it.
    # Anything nested under it is inside validity, not inside requirements that came earlier.
    assert within["Renewing:"] == leaflet_pages.UNCLASSIFIED
    assert [s.heading for s in parsed.variants_within(leaflet_pages.REQUIREMENTS)] == [
        "Single Subject:"
    ]


def test_a_variant_heading_with_no_text_under_it_is_not_offered() -> None:
    parsed = leaflet_pages.parse(
        page(
            "A Thing (CL-1)",
            "<h2>Requirements</h2><p>Common.</p><h3>Single Subject:</h3><h3>Multiple Subject:</h3>"
            "<p>Theirs.</p>",
        ),
        "cl-1",
    )
    assert [s.heading for s in parsed.variants_within(leaflet_pages.REQUIREMENTS)] == [
        "Multiple Subject:"
    ]


def test_the_real_family_leaflets_break_requirements_out_by_variant() -> None:
    """The shape the variant rule reads, asserted against the vendored bytes."""
    for code, expected in (
        ("cl-858", ["Single Subject:", "Multiple Subject:", "Education Specialist:"]),
        ("cl-856", ["Single Subject:", "Multiple Subject:", "Education Specialist:"]),
        ("cl-902", ["Single Subject", "Multiple Subject", "Special Education"]),
    ):
        parsed = leaflet_pages.load(code)
        headings = [s.heading for s in parsed.variants_within(leaflet_pages.REQUIREMENTS)]
        assert headings == expected, f"{code}: {headings}"


def test_every_vendored_leaflet_either_parses_or_says_why(
    real_leaflets: tuple[leaflets.Leaflet, ...],
) -> None:
    """No vendored snapshot fails in a way this project has not accounted for.

    The refusal branch ends in ``continue``, so every assertion after it is skippable. With
    no count of how many snapshots actually reached them, a parser that refused all of them
    would go green exactly like one that read all of them, so the number that parsed is
    asserted. The parser now refuses only on the code, which no vendored snapshot fails:
    every one of them is the document its filename names.
    """
    index = {leaflet.code: leaflet for leaflet in real_leaflets}
    assert leaflet_pages.available(), "the repository should hold leaflet snapshots"
    read = 0
    for code in leaflet_pages.available():
        assert code in index, f"{code} is not a leaflet the Commission's index publishes"
        try:
            parsed = leaflet_pages.load(code)
        except ValueError as refusal:
            assert code in str(refusal)
            continue
        assert parsed.code == code
        # A page that yields nothing has to say why it yielded nothing. CL-537 opens with a
        # heading repeating its own title, which is where reading stops, so it contributes no
        # prose at all: an empty read with a recorded stop, not an empty read full stop.
        assert parsed.lead or parsed.sections or parsed.stopped_at
        read += 1
    assert read == 19, f"only {read} snapshots parsed, so the assertions above ran {read} times"


def test_available_is_empty_when_there_is_no_snapshot_directory(tmp_path: Path) -> None:
    assert leaflet_pages.available(tmp_path / "nowhere") == ()


def test_a_stop_records_the_classified_headings_it_left_unread() -> None:
    """How much a stop costs, which the stop heading alone does not say.

    "Special Class Authorization" is unclassified and names a document, so reading stops
    there. What sits behind it is this leaflet's own requirements, under headings
    ``classify`` recognises. Nothing reads them, and until they were counted a leaflet that
    stopped one heading short of the end and one that stopped before five looked the same.
    """
    parsed = leaflet_pages.parse(
        page(
            "Speech-Language Pathology Services Credential (CL-1)",
            "<h2>Authorization</h2><p>What it lets you do.</p>"
            "<h3>Special Class Authorization</h3><p>An add-on.</p>"
            "<h3>Requirements for the Clear Credential</h3><p>Hold a master's degree.</p>"
            "<h3>Terms and Definitions</h3><p>Words.</p>",
        ),
        "cl-1",
    )
    assert parsed.stopped_at == "Special Class Authorization"
    assert parsed.classified_beyond_the_stop == (
        "Requirements for the Clear Credential",
        "Terms and Definitions",
    )
    assert [section.heading for section in parsed.sections] == ["Authorization"]
    assert all("master" not in block for section in parsed.sections for block in section.blocks), (
        "text beyond the stop was read into a section, which is exactly what must not happen"
    )


def test_a_stop_with_nothing_classified_behind_it_records_nothing() -> None:
    """The distinction the count exists to make, from the other side."""
    parsed = leaflet_pages.parse(
        page(
            "A Credential (CL-1)",
            "<h2>Requirements</h2><p>Hold a degree.</p>"
            "<h2>Some Other Certificate</h2><p>Not this document.</p>"
            "<h3>A subsection with no kind</h3><p>More.</p>",
        ),
        "cl-1",
    )
    assert parsed.stopped_at == "Some Other Certificate"
    assert parsed.classified_beyond_the_stop == ()


def test_a_page_read_to_the_end_records_no_headings_beyond_a_stop() -> None:
    parsed = leaflet_pages.parse(
        page("A Credential (CL-1)", "<h2>Requirements</h2><p>Hold a degree.</p>"),
        "cl-1",
    )
    assert parsed.stopped_at is None
    assert parsed.classified_beyond_the_stop == ()


def test_the_vendored_leaflets_stop_before_content_this_project_classifies() -> None:
    """Asserted against the vendored bytes, because the figure is the point of the count.

    Twelve of the nineteen snapshots stop before at least one heading ``classify`` would
    have recognised. CL-879 is the case issue #36 opens with: reading stops at "Special
    Class Authorization", an aside about an add-on, and four "Requirements for ..." headings
    for the credential the leaflet is actually titled for are never reached.
    """
    stopped = {
        code: leaflet_pages.load(code).classified_beyond_the_stop
        for code in leaflet_pages.available()
        if leaflet_pages.load(code).stopped_at is not None
    }
    assert len(stopped) == 14, f"{len(stopped)} vendored pages stop, not 14"
    assert sum(1 for beyond in stopped.values() if beyond) == 12
    assert stopped["cl-812"] == (), "cl-812 stops at the last thing on the page"
    assert [heading[:36] for heading in stopped["cl-879"]] == [
        "Requirements for the Two-Year Prelim",
        "Requirements for the Clear Credentia",
        "Requirements for the Two-Year Prelim",
        "Requirements for the Clear Credentia",
        "Terms and Definitions:",
    ]
