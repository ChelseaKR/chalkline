"""Shared fixtures. Everything here is local; no test opens a socket."""

from __future__ import annotations

import pytest

from chalkline.attachment import Attachment, attach
from chalkline.model import Catalog, build_catalog
from chalkline.sources import leaflet_pages, leaflets, sort_table

HEADER_ROW = (
    "<tr><th>Document Title</th><th>Authorization Title</th><th>Authorization Code</th>"
    "<th>Subject Code</th><th>Subject</th><th>Notes</th></tr>"
)


def table(*rows: str) -> str:
    """A sort-table page holding exactly the given data rows."""
    return f"<html><body><table>{HEADER_ROW}{''.join(rows)}</table></body></html>"


def row(
    document: str = "TC1",
    title: str = "Single Subject Teaching Credential",
    code: str = "R1S",
    subject_code: str = "ART",
    subject: str = "Art",
    notes: tuple[str, ...] = (),
) -> str:
    """One data row, notes rendered as the ``<ul>`` the Commission publishes."""
    body = "".join(f"<li>{note}</li>" for note in notes)
    cell = f"<ul>{body}</ul>" if notes else ""
    return (
        f"<tr><td>{document}</td><td>{title}</td><td>{code}</td>"
        f"<td>{subject_code}</td><td>{subject}</td><td>{cell}</td></tr>"
    )


@pytest.fixture(scope="session")
def real_rows() -> tuple[sort_table.SortTableRow, ...]:
    """The vendored Commission artifact, parsed once."""
    return sort_table.load()


@pytest.fixture(scope="session")
def real_catalog(real_rows: tuple[sort_table.SortTableRow, ...]) -> Catalog:
    return build_catalog(real_rows)


@pytest.fixture(scope="session")
def real_index() -> leaflets.Index:
    """The vendored leaflet index: titled leaflets, and the rows that only redirect."""
    return leaflets.load_index()


@pytest.fixture(scope="session")
def real_leaflets(real_index: leaflets.Index) -> tuple[leaflets.Leaflet, ...]:
    return real_index.leaflets


@pytest.fixture(scope="session")
def leaflet_index(
    real_leaflets: tuple[leaflets.Leaflet, ...],
) -> dict[str, leaflets.Leaflet]:
    return leaflets.index_by_title(real_leaflets)


@pytest.fixture(scope="session")
def vendored_pages() -> tuple[str, ...]:
    """Every leaflet page this repository holds a snapshot for."""
    return leaflet_pages.available()


@pytest.fixture(scope="session")
def real_attachments(
    real_catalog: Catalog,
    leaflet_index: dict[str, leaflets.Leaflet],
    real_leaflets: tuple[leaflets.Leaflet, ...],
) -> dict[str, Attachment]:
    """Every leaflet this project attaches to the vendored catalog, read once."""
    return attach(real_catalog, leaflet_index, published=real_leaflets)
