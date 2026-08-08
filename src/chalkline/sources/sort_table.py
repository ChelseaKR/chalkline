"""Read the CTC Authorization Sort Table exactly as the Commission published it.

The input is the vendored copy of the page at ``data/source/authorization-sort-table.html``
(retrieval provenance in the ``.source.json`` beside it), not the live site: the parser is
deterministic over a fixed artifact, and nothing in this package opens a socket. Refreshing
the artifact is a deliberate act, ``scripts/fetch_sources.py``, run by hand.

The table has six columns, named by the Commission in its own header row: Document Title,
Authorization Title, Authorization Code, Subject Code, Subject, Notes. One row is one
(authorization, subject) pair, so an authorization that covers ninety-five subjects occupies
ninety-five rows.

Normalization is deliberately shallow, and this list is exhaustive:

* HTML entities are unescaped and tags removed.
* Non-breaking spaces become ordinary spaces; runs of whitespace collapse to one space.
* The Notes cell is a ``<ul>`` of ``<li>`` items, so notes are read as a *tuple* of note
  strings rather than flattened into one blob. The bullet structure is the Commission's.
* Cell text is stripped at both ends.

Nothing is renamed, re-cased, expanded, split on meaning, or filled in. ``NONE`` in the
Subject Code column stays the literal string ``NONE``, because that is what the Commission
published and it means something (see :mod:`chalkline.model`).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SOURCE_PATH: Final = (
    Path(__file__).resolve().parents[3] / "data" / "source" / "authorization-sort-table.html"
)

SOURCE_URL: Final = (
    "https://www.ctc.ca.gov/employers/assignment-resources/resources/authorization-sort-table/"
)
"""Where the vendored copy came from, after the redirect from the ``/credentials/`` path."""

EXPECTED_HEADERS: Final = (
    "Document Title",
    "Authorization Title",
    "Authorization Code",
    "Subject Code",
    "Subject",
    "Notes",
)
"""The Commission's own header row. Checked on every parse: if CTC restructures the table,
this package stops rather than silently reading columns in the wrong order."""

_TABLE_RE: Final = re.compile(r"<table.*?</table>", re.DOTALL)
_ROW_RE: Final = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_CELL_RE: Final = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL)
_ITEM_RE: Final = re.compile(r"<li[^>]*>(.*?)</li>", re.DOTALL)
_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class SortTableRow:
    """One published (authorization, subject) pair, verbatim."""

    document_title: str
    authorization_title: str
    authorization_code: str
    subject_code: str
    subject: str
    notes: tuple[str, ...]


def _text(fragment: str) -> str:
    """One cell's visible text: tags out, entities in, whitespace collapsed."""
    stripped = _TAG_RE.sub(" ", fragment)
    return _SPACE_RE.sub(" ", html.unescape(stripped).replace("\xa0", " ")).strip()


def _notes(fragment: str) -> tuple[str, ...]:
    """The Notes cell as the Commission's own list of note items.

    The cell is a ``<ul>``; each ``<li>`` is one note. A cell with no list but with text
    (none exist in the vendored artifact, but the shape is legal HTML) reads as a single
    note, so the function cannot silently drop content.
    """
    items = [_text(item) for item in _ITEM_RE.findall(fragment)]
    if items:
        return tuple(item for item in items if item)
    single = _text(fragment)
    return (single,) if single else ()


def parse(markup: str) -> tuple[SortTableRow, ...]:
    """Every data row of the sort table in the order the Commission published them.

    Raises if the document does not hold exactly the table this parser was written
    against, or if its header row is not :data:`EXPECTED_HEADERS`. Both are refusals to
    guess: a changed page should stop the build, not quietly produce a different dataset.
    """
    tables = _TABLE_RE.findall(markup)
    if len(tables) != 1:
        raise ValueError(
            f"expected exactly one <table> in the sort table page, found {len(tables)}; "
            "the page structure changed and the parser will not guess which one to read"
        )
    rows = _ROW_RE.findall(tables[0])
    if not rows:
        raise ValueError("the sort table holds no rows")

    header = tuple(_text(cell) for cell in _CELL_RE.findall(rows[0]))
    if header != EXPECTED_HEADERS:
        raise ValueError(
            f"sort table headers are {header!r}, expected {EXPECTED_HEADERS!r}; "
            "columns may have been reordered or renamed upstream"
        )

    parsed: list[SortTableRow] = []
    for number, row in enumerate(rows[1:], start=2):
        cells = _CELL_RE.findall(row)
        if len(cells) != len(EXPECTED_HEADERS):
            raise ValueError(
                f"row {number} has {len(cells)} cells, expected {len(EXPECTED_HEADERS)}"
            )
        parsed.append(
            SortTableRow(
                document_title=_text(cells[0]),
                authorization_title=_text(cells[1]),
                authorization_code=_text(cells[2]),
                subject_code=_text(cells[3]),
                subject=_text(cells[4]),
                notes=_notes(cells[5]),
            )
        )
    return tuple(parsed)


def load(path: Path | None = None) -> tuple[SortTableRow, ...]:
    """Parse the vendored sort table (or another copy, for tests)."""
    return parse((path or SOURCE_PATH).read_text(encoding="utf-8"))
