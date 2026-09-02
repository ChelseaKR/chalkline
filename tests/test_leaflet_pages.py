"""A leaflet page is read only as far as it describes the document it is titled for."""

from __future__ import annotations

from pathlib import Path

import pytest

from chalkline.sources import leaflet_pages, leaflets

FOOTER = '<div class="et_pb_with_border et_pb_section et_pb_section_5" ><p>Get Involved</p></div>'

EN_DASH = "\u2013"
"""The Commission separates a requirements heading from its qualifier with an en dash.

Written as an escape because ruff refuses the literal character in a string (RUF001, the
ambiguous-character rule) and because a reader of this file cannot otherwise tell it from a
hyphen. `leaflets.normalize_title` folds all three dashes together for comparison; these
assertions are against the heading verbatim, so the exact character matters here.
"""


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
        # A page that yields nothing has to say why it yielded nothing. CL-628b and CL-898
        # open with a heading the Commission gave an outline to, which is where reading
        # stops, so they contribute no prose at all: an empty read with a recorded stop, not
        # an empty read full stop. CL-537 was in that position until issue #36 was fixed,
        # because its first heading repeats its own title and used to end the page.
        assert parsed.lead or parsed.sections or parsed.stopped_at
        read += 1
    assert read == 19, f"only {read} snapshots parsed, so the assertions above ran {read} times"


def test_available_is_empty_when_there_is_no_snapshot_directory(tmp_path: Path) -> None:
    assert leaflet_pages.available(tmp_path / "nowhere") == ()


def test_a_document_heading_with_no_outline_under_it_is_set_aside_not_a_stop() -> None:
    """Issue #36, in the shape CL-879 has it.

    "Special Class Authorization" is unclassified and names a document, and it used to end
    the page. It is one paragraph about an add-on, sitting between this credential's own
    "Authorization" section and its own requirements, and the Commission gave it no
    sub-headings. So it is set aside, its prose unread because this module cannot say whose
    it is, and the requirements after it are read, which is what the published graph was
    missing.
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
    assert parsed.stopped_at is None
    assert parsed.classified_beyond_the_stop == ()
    assert parsed.set_aside == ("Special Class Authorization",)
    assert [section.heading for section in parsed.sections] == [
        "Authorization",
        "Requirements for the Clear Credential",
        "Terms and Definitions",
    ]
    assert "An add-on." not in str(parsed.sections), (
        "the prose under a set-aside heading was read into a section, which is what must "
        "not happen: this module does not know whose statement it is"
    )
    assert parsed.of_kind(leaflet_pages.REQUIREMENTS)[0].blocks == ("Hold a master's degree.",)


def test_a_document_heading_with_an_outline_under_it_still_ends_the_page() -> None:
    """The other half, in the shape CL-380 has it. Narrowing the rule must not widen it.

    The Commission gave this heading a requirements section of its own, which is what
    starting a second document looks like, so nothing after it is read: those requirements
    belong to the Special Teaching Authorization in Health rather than to the School Nurse
    Services Credential, and so does the term the page closes on.
    """
    parsed = leaflet_pages.parse(
        page(
            "School Nurse Services Credential (CL-1)",
            "<h2>Requirements for the Clear Credential</h2><p>Mine.</p>"
            "<h2>Special Teaching Authorization in Health</h2><p>Another document.</p>"
            "<h3>Requirements for the Special Teaching Authorization in Health</h3>"
            "<p>Not mine.</p>"
            "<h2>Term of the Credential</h2><p>Not mine either.</p>",
        ),
        "cl-1",
    )
    assert parsed.stopped_at == "Special Teaching Authorization in Health"
    assert parsed.set_aside == ()
    assert parsed.classified_beyond_the_stop == (
        "Requirements for the Special Teaching Authorization in Health",
        "Term of the Credential",
    )
    assert [section.heading for section in parsed.sections] == [
        "Requirements for the Clear Credential"
    ]
    assert "Not mine" not in str(parsed.sections)


def test_a_repeated_unclassified_heading_does_not_end_the_page() -> None:
    """CL-529's shape: one heading reused under each of three specializations.

    The repeat rule reads a heading it has seen before as the page having looped into a
    structure it has been through. That is true of a classified heading, because the
    Commission does not head two statements of one document's requirements with one string,
    and false of an unclassified sub-heading, which leaflets reuse on purpose. Applying it to
    both ended CL-529 one heading before its "Period Of Validity".
    """
    parsed = leaflet_pages.parse(
        page(
            "Specialist Instruction Credentials (CL-1)",
            "<h2>Agriculture</h2><p>One.</p>"
            "<h2>Out-of-State Applicants</h2><p>First.</p>"
            "<h2>Gifted Education</h2><p>Two.</p>"
            "<h2>Out-of-State Applicants</h2><p>Second.</p>"
            "<h2>Period Of Validity</h2><p>Five years.</p>",
        ),
        "cl-1",
    )
    assert parsed.stopped_at is None
    assert [s.heading for s in parsed.of_kind(leaflet_pages.VALIDITY)] == ["Period Of Validity"]


def test_the_three_leaflets_issue_36_names_now_read_past_the_aside() -> None:
    """The three vendored pages the issue names, each asserted against the vendored bytes.

    Every one of them stopped at an unclassified heading naming a document that the
    Commission had given no sub-headings, and every one of them had classified content for
    its own subject behind that heading.

    CL-562 is the one that still stops. Its "National Board for Professional Teaching
    Standards Certification" is an alternate route to the same Teacher Librarian Services
    Credential and is now read past; what stops the page is the "Special Class Authorization"
    after it, which the Commission did give an outline of its own (an authorization, its
    requirements, its period of validity and its terms), and which is a different document.
    The stop moved to the right heading rather than going away.
    """
    speech = leaflet_pages.load("cl-879")
    assert speech.stopped_at != "Special Class Authorization"
    assert "Special Class Authorization" in speech.set_aside
    assert [s.heading for s in speech.of_kind(leaflet_pages.REQUIREMENTS)] == [
        f"Requirements for the Two-Year Preliminary Credential {EN_DASH} For Individuals "
        "Prepared in California",
        f"Requirements for the Clear Credential {EN_DASH} For Individuals Prepared in California",
        f"Requirements for the Two-Year Preliminary Credential {EN_DASH} For Individuals "
        "Prepared Out-of-State",
        f"Requirements for the Clear Credential {EN_DASH} For Individuals Prepared Out-of-State",
    ], "CL-879 publishes no requirements, which is the defect issue #36 opens with"

    tpsl = leaflet_pages.load("cl-902")
    assert tpsl.stopped_at is None
    assert tpsl.set_aside == ("TPSL Authorizations",)
    assert [s.heading for s in tpsl.of_kind(leaflet_pages.VALIDITY)] == ["Period of Validity"]

    librarian = leaflet_pages.load("cl-562")
    assert librarian.set_aside == (
        "National Board for Professional Teaching Standards Certification",
    )
    assert librarian.stopped_at == "Special Class Authorization"
    assert [s.heading for s in librarian.sections] == [
        "Authorization",
        "Requirements for the Clear Credential",
    ]


def _snapshot(code: str) -> str:
    """One vendored leaflet's bytes, for a test that needs the outline and not the parse."""
    return (leaflet_pages.SOURCE_DIR / f"{code}.html").read_text(encoding="utf-8")


def test_every_vendored_stop_is_a_heading_the_commission_gave_an_outline_to() -> None:
    """The rule holds over the corpus, not only over the pages the issue named.

    Both halves are asserted, because either one alone is satisfiable by a rule that has
    stopped working: a stop must be a heading with sub-headings under it or a repeat, and a
    set-aside heading must have none. The counts are asserted too, so a parser that stopped
    finding either case would fail rather than pass over an empty set.
    """
    stops = 0
    asides = 0
    for code in leaflet_pages.available():
        parsed = leaflet_pages.load(code)
        blocks = leaflet_pages._walk(leaflet_pages._body(_snapshot(code)))
        headings = {b.text: i for i, b in enumerate(blocks) if b.heading}
        for heading in parsed.set_aside:
            asides += 1
            assert not leaflet_pages._has_sub_headings(blocks, headings[heading]), (
                f"{code}: {heading!r} was set aside although the Commission gave it an "
                "outline of its own, which is a stop rather than an aside"
            )
        if parsed.stopped_at is None:
            continue
        stops += 1
        assert leaflet_pages.classify(parsed.stopped_at) != leaflet_pages.UNCLASSIFIED or (
            leaflet_pages._has_sub_headings(blocks, headings[parsed.stopped_at])
        ), f"{code}: reading stopped at {parsed.stopped_at!r}, which has nothing under it"
    assert (stops, asides) == (6, 14), f"{stops} stops and {asides} set-aside headings"


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

    Six of the nineteen snapshots stop, and every one of them has something classified behind
    the stop: a stop is the leaflet starting a second Commission document with an outline of
    its own, and that document states its own requirements. What is behind CL-380's stop is
    the Special Teaching Authorization in Health's requirements, the Other Health Services
    Credentials' requirements, and the term of a Health Services Credential. Not reading
    those is the point; counting them is how a reader can tell that from a leaflet that was
    read whole and simply said nothing more.

    This is where the fix for issue #36 shows up as a number. Fourteen pages stopped before
    it, twelve of them before something classified, and what sat behind most of those stops
    was the leaflet's own later requirements rather than another document's.
    """
    stopped = {
        code: leaflet_pages.load(code).classified_beyond_the_stop
        for code in leaflet_pages.available()
        if leaflet_pages.load(code).stopped_at is not None
    }
    assert len(stopped) == 6, f"{len(stopped)} vendored pages stop, not 6"
    assert sum(1 for beyond in stopped.values() if beyond) == 6, (
        "a stop with nothing classified behind it would mean the page ended at a heading "
        "the Commission gave an outline to but no statements under"
    )
    assert "cl-812" not in stopped, (
        "CL-812 stopped at its last heading, an aside with nothing after it, and reading "
        "past that heading is part of the fix rather than a regression"
    )
    assert stopped["cl-380"] == (
        "Requirements for the Special Teaching Authorization in Health",
        "Requirements for the Clear Credential",
        "Term of the Credential",
    ), "CL-380 is the page the stop rule exists for and its stop must not have moved"
    assert stopped["cl-879"] == ("Terms and Definitions:",), (
        "CL-879's four 'Requirements for ...' headings are read now; only the definitions "
        "list behind its upgrade section is left, and that section has an outline of its own"
    )
