"""The parser reads what the Commission published, and refuses to guess when it changes."""

from __future__ import annotations

from pathlib import Path

import pytest

from chalkline.sources import sort_table
from tests.conftest import HEADER_ROW, row, table


def test_reads_every_cell_verbatim() -> None:
    (parsed,) = sort_table.parse(
        table(row(subject_code="BSS", subject="Biological Sciences (Specialized)"))
    )
    assert parsed.document_title == "TC1"
    assert parsed.authorization_title == "Single Subject Teaching Credential"
    assert parsed.authorization_code == "R1S"
    assert parsed.subject_code == "BSS"
    assert parsed.subject == "Biological Sciences (Specialized)"
    assert parsed.notes == ()


def test_notes_keep_the_commissions_bullet_structure() -> None:
    (parsed,) = sort_table.parse(
        table(row(notes=("Limited to Specific Subject Area Only", "Discontinued in 2020")))
    )
    assert parsed.notes == (
        "Limited to Specific Subject Area Only",
        "Discontinued in 2020",
    )


def test_notes_cell_without_a_list_is_still_read() -> None:
    markup = table(row()).replace("<td></td></tr>", "<td>A bare note</td></tr>")
    (parsed,) = sort_table.parse(markup)
    assert parsed.notes == ("A bare note",)


def test_empty_list_items_are_dropped_not_emitted_as_blank_notes() -> None:
    (parsed,) = sort_table.parse(table(row(notes=("", "Real note"))))
    assert parsed.notes == ("Real note",)


def test_entities_and_nbsp_are_resolved() -> None:
    (parsed,) = sort_table.parse(table(row(subject="Art&nbsp;&amp; Design")))
    assert parsed.subject == "Art & Design"


def test_none_stays_the_literal_string() -> None:
    (parsed,) = sort_table.parse(table(row(subject_code="NONE", subject="")))
    assert parsed.subject_code == "NONE"
    assert parsed.subject == ""


def test_rejects_a_page_without_exactly_one_table() -> None:
    with pytest.raises(ValueError, match="exactly one <table>"):
        sort_table.parse("<html><body><p>no table</p></body></html>")
    with pytest.raises(ValueError, match="exactly one <table>"):
        sort_table.parse(table() + table())


def test_rejects_renamed_or_reordered_columns() -> None:
    swapped = HEADER_ROW.replace("Document Title", "Doc")
    with pytest.raises(ValueError, match="headers are"):
        sort_table.parse(f"<table>{swapped}{row()}</table>")


def test_rejects_a_table_with_no_rows() -> None:
    with pytest.raises(ValueError, match="no rows"):
        sort_table.parse("<table></table>")


def test_load_rejects_an_artifact_that_kept_its_headers_and_lost_its_rows(
    tmp_path: Path,
) -> None:
    """The one shape of a broken page that every structural check lets through.

    `parse` refuses a page with no `<table>`, no `<tr>`, renamed columns, or a short row. A
    page holding the Commission's six headers and nothing under them satisfies all four, so
    `parse` returns `()` (correctly: it read no rows). Read as an artifact that is what a
    catalog of nothing looks like, and the whole pipeline publishes it: zero licences, a
    coverage statement counting zero of everything as measured fact, a page of nine zeroed
    tiles, and `chalkline build` exiting 0.
    """
    path = tmp_path / "authorization-sort-table.html"
    path.write_text(table(), encoding="utf-8")
    assert sort_table.parse(path.read_text(encoding="utf-8")) == ()
    with pytest.raises(ValueError, match="header row and no data rows"):
        sort_table.load(path)


def test_load_accepts_an_artifact_with_a_single_row(tmp_path: Path) -> None:
    """The refusal is about none, not about few: one row is a readable table."""
    path = tmp_path / "authorization-sort-table.html"
    path.write_text(table(row()), encoding="utf-8")
    assert len(sort_table.load(path)) == 1


def test_rejects_a_short_row() -> None:
    with pytest.raises(ValueError, match="has 2 cells"):
        sort_table.parse(f"<table>{HEADER_ROW}<tr><td>TC1</td><td>x</td></tr></table>")


def test_vendored_artifact_parses(real_rows: tuple[sort_table.SortTableRow, ...]) -> None:
    """The real page, counted rather than asserted: whatever it holds, every row is complete."""
    assert len(real_rows) > 0
    assert all(parsed.document_title for parsed in real_rows)
    assert all(parsed.authorization_title for parsed in real_rows)


def test_load_reads_the_vendored_path_by_default() -> None:
    assert sort_table.load() == sort_table.parse(sort_table.SOURCE_PATH.read_text(encoding="utf-8"))
