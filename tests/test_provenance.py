"""Provenance is checked, not asserted.

Every vendored artifact carries a sidecar naming its URL, retrieval date, and sha256. If a
snapshot is refreshed without updating its sidecar, or edited by hand, these tests fail.
"""

from __future__ import annotations

import hashlib
import json
import re
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


def test_no_module_in_the_package_opens_a_socket() -> None:
    """Only scripts/fetch_sources.py may reach the network, and it is not importable code."""
    package = REPO_ROOT / "src" / "chalkline"
    networking = re.compile(
        r"^\s*(?:import|from)\s+(urllib|http|socket|ssl|ftplib|requests|httpx|aiohttp)\b",
        re.MULTILINE,
    )
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in sorted(package.rglob("*.py"))
        if networking.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
