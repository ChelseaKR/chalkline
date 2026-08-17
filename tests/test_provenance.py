"""Provenance is checked, not asserted.

Every vendored artifact carries a sidecar naming its URL, retrieval date, and sha256. If a
snapshot is refreshed without updating its sidecar, or edited by hand, these tests fail.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from chalkline.ctdl import export
from chalkline.sources import leaflets, sort_table

REPO_ROOT = Path(__file__).resolve().parents[1]

LEAFLET_SNAPSHOTS = tuple(sorted((REPO_ROOT / "data" / "source" / "leaflets").glob("*.html")))

VENDORED = (
    REPO_ROOT / "data" / "source" / "authorization-sort-table.html",
    REPO_ROOT / "data" / "source" / "credential-leaflets.html",
    REPO_ROOT / "src" / "chalkline" / "ctdl" / "ctdl-context.json",
    REPO_ROOT / "src" / "chalkline" / "ctdl" / "ctdl-schema.json",
    *LEAFLET_SNAPSHOTS,
)


def sidecar(path: Path) -> dict[str, object]:
    loaded: dict[str, object] = json.loads(
        path.with_suffix(".source.json").read_text(encoding="utf-8")
    )
    return loaded


@pytest.mark.parametrize("path", VENDORED, ids=lambda p: p.name)
def test_each_artifact_matches_its_recorded_hash_and_size(path: Path) -> None:
    payload = path.read_bytes()
    meta = sidecar(path)
    assert hashlib.sha256(payload).hexdigest() == meta["sha256"]
    assert len(payload) == meta["bytes"]


@pytest.mark.parametrize("path", VENDORED, ids=lambda p: p.name)
def test_each_artifact_records_a_source_and_a_date(path: Path) -> None:
    meta = sidecar(path)
    url = meta.get("final_url") or meta.get("source_url")
    assert isinstance(url, str) and url.startswith("https://")
    assert isinstance(meta["retrieved"], str) and len(meta["retrieved"]) == 10


def test_the_parsers_point_at_the_urls_the_sidecars_record() -> None:
    table_meta = sidecar(VENDORED[0])
    assert table_meta["final_url"] == sort_table.SOURCE_URL
    leaflet_meta = sidecar(VENDORED[1])
    assert leaflet_meta["final_url"] == leaflets.SOURCE_URL


def test_the_commission_address_is_printed_in_the_vendored_artifact() -> None:
    """The organization address is transcribed from the page footer, so the page must say it."""
    page = VENDORED[0].read_text(encoding="utf-8")
    assert export.ORGANIZATION_ADDRESS["street"] in page
    assert export.ORGANIZATION_ADDRESS["locality"] in page
    assert export.ORGANIZATION_ADDRESS["postal_code"] in page
    assert export.ORGANIZATION_NAME in page


def test_the_published_scope_statement_is_still_on_the_page() -> None:
    """The Commission's own statement of what the table covers, quoted in the sidecar."""
    page = VENDORED[0].read_text(encoding="utf-8")
    quoted = str(sidecar(VENDORED[0])["scope_statement_published_on_page"])
    assert quoted in " ".join(page.split())


def test_every_leaflet_snapshot_is_one_the_commission_index_links() -> None:
    """No snapshot is here that the Commission's own index does not publish."""
    published = {leaflet.code: leaflet for leaflet in leaflets.load()}
    assert LEAFLET_SNAPSHOTS, "the repository should hold leaflet snapshots"
    for path in LEAFLET_SNAPSHOTS:
        meta = sidecar(path)
        assert path.stem in published, f"{path.stem} is not in the Commission's leaflet index"
        assert meta["final_url"] == published[path.stem].url
        assert meta["index_title"] == published[path.stem].title


def test_every_leaflet_snapshot_is_one_an_authorization_matched(
    real_catalog: object, leaflet_index: object
) -> None:
    """Nothing was retrieved speculatively: each snapshot serves a modeled authorization."""
    from chalkline.attachment import attach
    from chalkline.model import Catalog

    assert isinstance(real_catalog, Catalog)
    attachments = attach(real_catalog, leaflet_index)  # type: ignore[arg-type]
    needed = {attachment.leaflet.code for attachment in attachments.values()}
    assert {path.stem for path in LEAFLET_SNAPSHOTS} == needed


NETWORKING = ("urllib", "http", "socket", "ssl", "ftplib", "requests", "httpx", "aiohttp")
"""Top-level modules that can open a socket, or that exist to."""


def networking_imports(source: str) -> list[str]:
    """Every networking module a source file imports, however the import is written.

    Parsed rather than pattern-matched. A regex anchored on ``import <name>`` reads
    ``import json, socket`` as an import of ``json`` and says nothing about the second name,
    which is the one that matters; the syntax tree has both. Nothing here is a claim about
    dynamic imports, which no module in this package uses and which this cannot see.
    """
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module)
    return sorted(name for name in found if name.split(".")[0] in NETWORKING or name in NETWORKING)


@pytest.mark.parametrize(
    "source",
    [
        "import socket",
        "import json, socket",
        "import urllib.request",
        "import urllib.request as fetch",
        "from urllib import request",
        "from http.client import HTTPSConnection",
        "import requests",
        "def f():\n    import httpx\n",
    ],
)
def test_the_networking_scan_sees_every_shape_of_import(source: str) -> None:
    """The scan is only worth running if it catches the import forms a module could use."""
    assert networking_imports(source) != []


@pytest.mark.parametrize(
    "source",
    ["import json", "from pathlib import Path", "from chalkline.sources import leaflets", ""],
)
def test_the_networking_scan_passes_ordinary_imports(source: str) -> None:
    assert networking_imports(source) == []


def test_no_module_in_the_package_opens_a_socket() -> None:
    """Only scripts/fetch_sources.py may reach the network, and it is not importable code."""
    package = REPO_ROOT / "src" / "chalkline"
    modules = sorted(package.rglob("*.py"))
    # An empty scan produces the same empty list as a clean one. Say how many files were
    # read, so a moved package cannot pass this by giving the check nothing to look at.
    assert len(modules) >= 10, f"scanned {len(modules)} modules under {package}"
    offenders = {
        str(path.relative_to(REPO_ROOT)): imported
        for path in modules
        if (imported := networking_imports(path.read_text(encoding="utf-8")))
    }
    assert offenders == {}


def test_the_one_module_allowed_to_reach_the_network_does() -> None:
    """The scan is pointed at code that would fail it if it were in the package."""
    fetcher = REPO_ROOT / "scripts" / "fetch_sources.py"
    assert networking_imports(fetcher.read_text(encoding="utf-8")) != []
