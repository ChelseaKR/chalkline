"""The numbers in the prose are the numbers the build produces.

Everything the build writes is counted: ``site/coverage.json`` is derived from the emitted
graph, ``site/index.html`` counts the catalog at render time, and ``chalkline check`` holds
both byte-for-byte against a fresh build. The two documents a reader meets first, README.md
and PROVENANCE.md, retype those figures into markdown tables by hand, and nothing used to
check them. PROVENANCE.md even introduces its table with "Recomputed from the emitted graph
at build time", which was a description of where the numbers came from originally rather
than of anything that keeps them true.

One of them had already drifted: the README published 20 authorizations carrying
requirements or renewal terms, which is the two property counts added together with the
authorizations carrying both counted twice, where the graph and the page both say 13.

So every numeric row of both tables is bound to a freshly counted coverage statement here.
The binding is exhaustive in both directions: a row this module does not know about fails,
and a figure this module names that the table has stopped publishing fails too. Without that
pair, a row could be added to a table, or quietly deleted from one, and this file would go on
passing while checking less than it claims to.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from chalkline import ctid as ctid_module
from chalkline.attachment import Attachment
from chalkline.ctdl import export
from chalkline.model import Catalog
from chalkline.sources import leaflets as leaflets_module

REPO_ROOT = Path(__file__).resolve().parents[1]

_ROW_RE = re.compile(r"^\|\s*(?P<label>.+?)\s*\|\s*(?P<count>[\d,]+)\s*\|\s*$", re.MULTILINE)


def documented(path: Path, heading: str) -> dict[str, int]:
    """Every ``| label | number |`` row of the table under one heading."""
    text = path.read_text(encoding="utf-8")
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    section = text[start : end if end != -1 else len(text)]
    return {
        match.group("label"): int(match.group("count").replace(",", ""))
        for match in _ROW_RE.finditer(section)
    }


def figures(statement: dict[str, Any]) -> dict[str, int]:
    """Every figure the two tables are allowed to quote, keyed by how they label it."""
    authorizations = statement["authorizations"]
    entities = statement["entities"]
    properties = statement["license_properties"]
    leaflets = statement["leaflets"]
    return {
        "Rows published in the sort table": statement["source"]["rows_published"],
        "Authorizations in those rows": authorizations["published_in_source"],
        "Modeled as `ceterms:License`": entities["ceterms:License"],
        "Excluded, each with a recorded reason": authorizations["excluded"],
        "Excluded, with reasons below": authorizations["excluded"],
        "Subject alignments emitted": entities["ceterms:CredentialAlignmentObject"],
        "`ceterms:CredentialAlignmentObject` subject alignments emitted": entities[
            "ceterms:CredentialAlignmentObject"
        ],
        "Of those, supplied by following a published cross-reference": authorizations[
            "subject_alignments_from_a_cross_reference"
        ],
        "Authorizations whose scope was resolved by cross-reference": authorizations[
            "scope_resolved_by_cross_reference"
        ],
        "Authorizations with subject codes": authorizations["with_subject_codes"],
        "Authorizations the Commission publishes as `NONE` (not subject-coded)": authorizations[
            "published_as_not_subject_coded"
        ],
        "Authorizations carrying `ceterms:description`": properties["ceterms:description"],
        "Of those, described in a Commission leaflet": leaflets[
            "authorizations_with_leaflet_prose"
        ],
        "Authorizations carrying `ceterms:requires`": properties["ceterms:requires"],
        "Authorizations carrying `ceterms:renewal`": properties["ceterms:renewal"],
        "Authorizations carrying requirements or renewal terms": authorizations[
            "with_requirements_or_renewal_terms"
        ],
        "`ceterms:ConditionProfile` nodes emitted": entities["ceterms:ConditionProfile"],
        "Authorizations linked to a CTC leaflet": leaflets["authorizations_with_a_leaflet"],
        "Leaflet pages read": leaflets["leaflet_pages_read"],
        "Leaflet pages refused on identity": leaflets["leaflet_pages_refused"],
        "Leaflets in the Commission's index": leaflets["leaflets_in_the_commission_index"],
        "CTIDs in the ledger (133 licenses plus the Commission)": len(ctid_module.load_ledger()),
    }


TABLES = (
    (REPO_ROOT / "README.md", "## What this is"),
    (REPO_ROOT / "PROVENANCE.md", "## What is counted"),
)


@pytest.fixture(scope="module")
def statement(real_catalog: Catalog, real_attachments: dict[str, Attachment]) -> dict[str, object]:
    published = len(leaflets_module.load())
    document = export.project_graph(real_catalog, ctid_module.load_ledger(), real_attachments)
    return export.coverage(document, real_catalog, real_attachments, published)


def _id(value: Path | str) -> str:
    return value.name if isinstance(value, Path) else value.removeprefix("## ")


@pytest.mark.parametrize(("path", "heading"), TABLES, ids=_id)
def test_every_documented_count_is_the_count_the_build_produces(
    path: Path, heading: str, statement: dict[str, Any]
) -> None:
    known = figures(statement)
    rows = documented(path, heading)
    assert rows, f"{path.name} publishes no counted table under {heading!r}"
    unknown = sorted(set(rows) - set(known))
    assert unknown == [], (
        f"{path.name} publishes figures nothing checks: {unknown}. Add each one to "
        "figures() with the coverage-statement value it quotes, or it can drift."
    )
    wrong = {label: (count, known[label]) for label, count in rows.items() if count != known[label]}
    assert wrong == {}, f"{path.name} says (documented, built): {wrong}"


def test_every_figure_this_module_binds_is_still_published(statement: dict[str, Any]) -> None:
    """A label that has left both tables is a check that has stopped checking anything."""
    published = {label for path, heading in TABLES for label in documented(path, heading)}
    orphaned = sorted(set(figures(statement)) - published)
    assert orphaned == [], (
        f"figures() names rows no table publishes any more: {orphaned}. Drop them, or the "
        "count of things checked here is smaller than it looks."
    )
