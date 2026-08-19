"""Leaflets attach on an equality with something the Commission published, and nothing else."""

from __future__ import annotations

from pathlib import Path

import pytest

from chalkline.sources import leaflets


def row(code: str, title: str, published_code: str | None = None, category: str = "") -> str:
    """One index row: the linked title, the Commission's code column, and a category.

    ``published_code`` defaults to the code in the link path, which is the ordinary case: a
    leaflet's own row names its own code. Passing a different one builds the other kind of
    row the index carries, a redirection from a retired document.
    """
    shown = code if published_code is None else published_code
    return (
        f'<tr><td class="column-1"><a href="/credentials/leaflets/{code}/">{title}</a></td>'
        f'<td class="column-2">{shown}</td><td class="column-3">{category}</td></tr>'
    )


def page(*links: tuple[str, str]) -> str:
    body = "".join(row(code, label) for code, label in links)
    return f"<html><body><table>{body}</table></body></html>"


def test_parses_code_title_and_url() -> None:
    (leaflet,) = leaflets.parse(page(("cl-380", "School Nurse Services Credential")))
    assert leaflet.code == "cl-380"
    assert leaflet.title == "School Nurse Services Credential"
    assert leaflet.url == "https://www.ctc.ca.gov/credentials/leaflets/cl-380/"


def test_an_empty_repeat_link_does_not_erase_a_title() -> None:
    parsed = leaflets.parse(page(("cl-380", ""), ("cl-380", "School Nurse Services Credential")))
    assert [x.title for x in parsed] == ["School Nurse Services Credential"]


def test_the_index_link_to_itself_is_skipped() -> None:
    """The index links back to itself, with and without a trailing segment."""
    for path in (
        "/credentials/leaflets/",
        "/credentials/leaflets//",
        "/credentials/leaflets/leaflets/",
    ):
        markup = f'<table><tr><td><a href="{path}">Leaflets</a></td><td>CL-1</td></tr></table>'
        assert leaflets.parse(markup) == ()


def test_results_are_sorted_by_code() -> None:
    parsed = leaflets.parse(page(("cl-562", "B"), ("cl-380", "A")))
    assert [x.code for x in parsed] == ["cl-380", "cl-562"]


def test_normalization_folds_case_and_punctuation_only() -> None:
    assert leaflets.normalize_title("Credential (CTE)") == leaflets.normalize_title(
        "credential  cte"
    )
    assert leaflets.normalize_title("A - B") == leaflets.normalize_title("A \u2013 B")
    assert leaflets.normalize_title("Art Credential") != leaflets.normalize_title("Art")


def test_code_normalization_drops_separators_and_nothing_else() -> None:
    """The index writes one code two ways across its own two columns."""
    assert leaflets.normalize_code("CL-533O CLAD-BL") == leaflets.normalize_code("cl-533o-clad-bl")
    assert leaflets.normalize_code("CL-760GE") == leaflets.normalize_code("cl-760ge")
    assert leaflets.normalize_code("CL-533o") != leaflets.normalize_code("cl-533o-clad-bl")


def test_an_ambiguous_title_matches_nothing() -> None:
    parsed = leaflets.parse(page(("cl-1", "Same Title"), ("cl-2", "Same Title")))
    assert leaflets.index_by_title(parsed) == {}


def test_an_unambiguous_title_is_indexed() -> None:
    parsed = leaflets.parse(page(("cl-1", "Only One")))
    assert set(leaflets.index_by_title(parsed)) == {"only one"}


def test_the_vendored_index_parses(real_leaflets: tuple[leaflets.Leaflet, ...]) -> None:
    assert len(real_leaflets) > 0
    assert all(x.title and x.code and x.url.startswith("https://") for x in real_leaflets)


def test_load_reads_the_vendored_path_by_default() -> None:
    assert leaflets.load() == leaflets.parse(leaflets.SOURCE_PATH.read_text(encoding="utf-8"))


def test_a_link_with_no_code_segment_is_skipped() -> None:
    markup = (
        '<table><tr><td><a href="/credentials/leaflets/#top">Anchor</a></td><td>x</td></tr></table>'
    )
    assert leaflets.parse(markup) == ()


def test_a_row_without_a_code_column_is_not_read() -> None:
    """A one-cell row cannot say which leaflet its title belongs to, so it says nothing."""
    markup = '<table><tr><td><a href="/credentials/leaflets/cl-380/">Nurse</a></td></tr></table>'
    assert leaflets.parse(markup) == ()


def test_a_redirection_row_does_not_title_the_leaflet_it_points_at() -> None:
    """The index prints the redirection above the leaflet's own row, and it is not a title.

    Six leaflets carry one. Taking the first non-empty link text published all six under a
    sentence about a document that no longer exists, and hid the real title entirely.
    """
    markup = (
        "<table>"
        + row("cl-828", "CL-740 has been replaced by CL-828.", published_code="CL-740")
        + row("cl-828", "General Education Limited Assignment Teaching Permit")
        + "</table>"
    )
    (leaflet,) = leaflets.parse(markup)
    assert leaflet.title == "General Education Limited Assignment Teaching Permit"


def test_the_leaflets_own_row_wins_wherever_the_index_prints_it() -> None:
    """Identity is the agreement between two codes, so row order decides nothing."""
    own = row("cl-828", "General Education Limited Assignment Teaching Permit")
    notice = row("cl-828", "CL-740 has been replaced by CL-828.", published_code="CL-740")
    assert leaflets.parse(f"<table>{own}{notice}</table>") == leaflets.parse(
        f"<table>{notice}{own}</table>"
    )


def test_redirection_rows_are_reported_rather_than_dropped() -> None:
    markup = (
        "<table>"
        + row("cl-828", "CL-740 has been replaced by CL-828.", published_code="CL-740")
        + row("cl-828", "General Education Limited Assignment Teaching Permit")
        + "</table>"
    )
    (retired,) = leaflets.superseded(markup)
    assert retired.code == "CL-740"
    assert retired.replaced_by == "cl-828"
    assert retired.notice == "CL-740 has been replaced by CL-828."


def test_the_vendored_index_carries_the_redirection_rows_that_motivated_this() -> None:
    index = leaflets.load_index()
    assert len(index.leaflets) == 81
    assert len(index.superseded) == 8
    titles = {x.code: x.title for x in index.leaflets}
    assert titles["cl-828"] == "General Education Limited Assignment Teaching Permit"
    assert "replaced by" not in " ".join(titles.values())


def test_a_document_code_in_a_leaflet_title_indexes_only_a_published_code() -> None:
    """The equality is against the sort table's own key, so a non-code cannot match."""
    parsed = leaflets.parse(
        page(
            ("cl-898", "Mathematics Instructional Leadership Specialist Credential (MILS)"),
            ("cl-603", "Supplementary Authorizations (Single Subjects)"),
        )
    )
    index = leaflets.index_by_document_code(parsed, {"MILS", "TC1"})
    assert set(index) == {"MILS"}
    assert index["MILS"].code == "cl-898"


def test_a_document_code_two_leaflets_name_is_dropped() -> None:
    parsed = leaflets.parse(page(("cl-1", "One (MILS)"), ("cl-2", "Two (MILS)")))
    assert leaflets.index_by_document_code(parsed, {"MILS"}) == {}


def test_a_document_code_match_is_on_the_whole_cell() -> None:
    parsed = leaflets.parse(page(("cl-898", "Something (MILS)")))
    index = leaflets.index_by_document_code(parsed, {"MILS"})
    assert leaflets.match_document_code("MILS", index) is not None
    # A cell listing two documents is not the document this leaflet is titled for.
    assert leaflets.match_document_code("MILS, TC1", index) is None


def test_a_document_code_match_records_that_it_was_not_a_title() -> None:
    parsed = leaflets.parse(page(("cl-898", "Something (MILS)")))
    match = leaflets.match_document_code("MILS", leaflets.index_by_document_code(parsed, {"MILS"}))
    assert match is not None
    assert match.rule == leaflets.MATCH_DOCUMENT_CODE
    assert match.published_by == leaflets.FROM_DOCUMENT_CODE
    assert match.qualifier is None


def test_a_title_match_records_where_the_title_was_published() -> None:
    index = leaflets.index_by_title(leaflets.parse(page(("cl-1", "Short-Term Staff Permit"))))
    exact = leaflets.match_title("Short-Term Staff Permit", index, leaflets.FROM_PAGE)
    assert exact is not None
    assert exact.published_by == leaflets.FROM_PAGE
    assert exact.matched_title == "Short-Term Staff Permit"

    family = leaflets.match_title("Short-Term Staff Permit (Single Subject)", index)
    assert family is not None
    assert family.rule == leaflets.MATCH_NAMED_FAMILY
    assert family.published_by == leaflets.FROM_INDEX
    assert family.qualifier == "Single Subject"
    assert family.matched_title == "Short-Term Staff Permit"


def test_an_index_artifact_linking_no_leaflets_is_refused(tmp_path: Path) -> None:
    """An unreadable index must not be reported as an index of nothing.

    `_LINK_RE` matches a path-relative href, so the Commission switching to absolute URLs is
    an ordinary CMS change. It used to yield zero leaflets, zero attachments, a graph with
    the descriptions and conditions silently gone, and a coverage statement publishing the
    smaller counts as fact, with every gate still green.
    """
    index = tmp_path / "credential-leaflets.html"
    index.write_text(
        '<table><tr><td><a href="https://www.ctc.ca.gov/credentials/leaflets/cl-380/">'
        "School Nurse</a></td><td>CL-380</td></tr></table>",
        encoding="utf-8",
    )
    assert leaflets.parse(index.read_text(encoding="utf-8")) == ()
    with pytest.raises(ValueError, match="links no leaflet pages"):
        leaflets.load(index)
