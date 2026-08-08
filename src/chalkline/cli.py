"""Command line entry point.

Three verbs, and none of them touches the network:

``chalkline build``       parse the vendored sources, validate, write ``site/``.
``chalkline mint-ctids``  assign a spec-conformant CTID to any authorization lacking one.
``chalkline check``       build in memory and compare against the committed ``site/``.

``check`` is what CI runs. It fails when the committed artifacts are not byte-for-byte what
the current code produces from the current sources, which makes the output in the repository
a verified statement rather than a stale one.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from chalkline import ctid as ctid_module
from chalkline.ctdl import export as export_module
from chalkline.ctdl import validate as validate_module
from chalkline.model import Catalog, build_catalog
from chalkline.site import render
from chalkline.sources import leaflets as leaflets_module
from chalkline.sources import sort_table

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "site"
PAGE_FILENAME = "index.html"


def _catalog() -> Catalog:
    return build_catalog(sort_table.load())


def _artifacts(catalog: Catalog) -> dict[str, str]:
    """The three published files, as text, without writing anything."""
    leaflet_index = leaflets_module.index_by_title(leaflets_module.load())
    ctids = ctid_module.load_ledger()
    document = export_module.project_graph(catalog, ctids, leaflet_index)
    validate_module.check(document)
    statement = export_module.coverage(document, catalog, leaflet_index)
    export_module.check_coverage(statement, document, catalog, leaflet_index)
    return {
        export_module.GRAPH_FILENAME: export_module.serialize(document),
        export_module.COVERAGE_FILENAME: export_module.serialize(statement),
        PAGE_FILENAME: render(catalog, ctids, leaflet_index),
    }


def build(output_dir: Path) -> int:
    catalog = _catalog()
    artifacts = _artifacts(catalog)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, text in artifacts.items():
        (output_dir / name).write_text(text, encoding="utf-8")
    licenses = len(catalog.authorizations)
    print(
        f"wrote {len(artifacts)} files to {output_dir}: "
        f"{licenses} authorizations modeled, {len(catalog.exclusions)} excluded"
    )
    return 0


def check(output_dir: Path) -> int:
    catalog = _catalog()
    artifacts = _artifacts(catalog)
    stale: list[str] = []
    for name, text in artifacts.items():
        path = output_dir / name
        if not path.exists():
            stale.append(f"{name}: missing")
        elif path.read_text(encoding="utf-8") != text:
            stale.append(f"{name}: differs from a fresh build")
    if stale:
        print("committed output is not what the code produces:", file=sys.stderr)
        for line in stale:
            print(f"  {line}", file=sys.stderr)
        print("run `chalkline build` and commit the result", file=sys.stderr)
        return 1
    print(f"committed output matches a fresh build ({len(artifacts)} files)")
    return 0


def mint_ctids(ledger_path: Path | None) -> int:
    catalog = _catalog()
    keys = [export_module.ORGANIZATION_KEY] + [a.key for a in catalog.authorizations]
    existing = ctid_module.load_ledger(ledger_path)
    updated, minted = ctid_module.mint_missing(keys, existing)
    if minted:
        ctid_module.save_ledger(updated, ledger_path)
    print(f"ledger holds {len(updated)} CTIDs; minted {minted} this run")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chalkline", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, helptext in (
        ("build", "write the JSON-LD, coverage statement, and page into site/"),
        ("check", "verify the committed site/ matches a fresh build"),
    ):
        command = sub.add_parser(name, help=helptext)
        command.add_argument("--output-dir", type=Path, default=SITE_DIR)
    minter = sub.add_parser("mint-ctids", help="assign CTIDs to authorizations lacking one")
    minter.add_argument("--ledger", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.command == "build":
        return build(args.output_dir)
    if args.command == "check":
        return check(args.output_dir)
    return mint_ctids(args.ledger)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
