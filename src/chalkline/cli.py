"""Command line entry point.

Three verbs, and none of them touches the network:

``chalkline build``       parse the vendored sources, validate, write ``site/``.
``chalkline mint-ctids``  assign a spec-conformant CTID to any authorization lacking one.
``chalkline check``       build in memory and compare against the committed ``site/``.
``chalkline authorizes``  answer one assignment question from the graph, with its rows.

``check`` is what CI runs. It fails when the committed artifacts are not byte-for-byte what
the current code produces from the current sources, which makes the output in the repository
a verified statement rather than a stale one. It also enumerates ``site/`` rather than only
looking for the files it produces, because comparing what the build writes cannot notice a
file the build has stopped writing, and ``.github/workflows/pages.yml`` uploads the whole
directory: an orphan there is not merely stale in the repository, it is served.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from chalkline import authorizes as authorizes_module
from chalkline import ctid as ctid_module
from chalkline import dataset as dataset_module
from chalkline.attachment import attach
from chalkline.ctdl import export as export_module
from chalkline.ctdl import validate as validate_module
from chalkline.model import Catalog, build_catalog
from chalkline.site import SITE_URL, TITLE, render
from chalkline.sources import leaflet_pages, sort_table
from chalkline.sources import leaflets as leaflets_module

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "site"
PAGE_FILENAME = "index.html"

#: Files published from ``site/`` that ``build`` does not write, each with the gate that
#: does hold it to a fresh run. ``check`` enumerates the directory and fails on anything
#: else, because it used to look only for the files it produced: a file committed under
#: ``site/`` that the build had stopped writing sat there unmentioned, and
#: ``.github/workflows/pages.yml`` uploads the whole directory, so an orphan is not merely
#: stale in the repository, it is served. An exclusion a reader cannot see is the silence
#: this check exists to remove, so every reason here is printed on every run.
PUBLISHED_BY_ANOTHER_GATE: dict[str, str] = {
    "ctdl-validate.json": (
        "written by scripts/validate_evidence.py and held byte-for-byte to a fresh "
        "ctdl-validate run by `make validate` and tests/test_ctdl_validate_evidence.py"
    ),
    "og-card.png": (
        "the share image named by the page's og:image, committed rather than derived "
        "from any source; tests/test_site.py holds it to being a PNG of exactly the "
        "dimensions the head declares, and to being the file the head names"
    ),
}


def _catalog() -> Catalog:
    return build_catalog(sort_table.load())


def _evidence_text() -> str:
    """The committed ``ctdl-validate`` report, read rather than reproduced.

    It is written by ``scripts/validate_evidence.py`` and held byte-for-byte to a fresh
    ``ctdl-validate`` run by ``make validate`` and ``tests/test_ctdl_validate_evidence.py``,
    which is why it sits in :data:`PUBLISHED_BY_ANOTHER_GATE` rather than being built here.
    The dataset descriptor still has to state its size and digest, so it is read from the
    committed copy, always from ``site/`` and not from a caller's ``--output-dir``, because
    the committed file is the one that gate holds.

    A missing report stops the build. A descriptor that quietly described two downloads
    where the site publishes three would be well-formed, would carry correct digests for
    the two it did describe, and would pass ``chalkline check`` against a fresh build that
    also described two.
    """
    path = SITE_DIR / dataset_module.EVIDENCE_FILENAME
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} is missing; it is one of the three artifacts the dataset descriptor "
            "describes, and a descriptor naming fewer downloads than the site publishes "
            "would assert a smaller dataset than the one that exists. Run `make validate`."
        )
    return path.read_text(encoding="utf-8")


def _artifacts(catalog: Catalog) -> dict[str, str]:
    """The four published files, as text, without writing anything."""
    index = leaflets_module.load_index()
    attachments = attach(
        catalog, leaflets_module.index_by_title(index.leaflets), published=index.leaflets
    )
    vendored = leaflet_pages.available()
    ctids = ctid_module.load_ledger()
    document = export_module.project_graph(catalog, ctids, attachments)
    validate_module.check(document)
    statement = export_module.coverage(document, catalog, attachments, index, vendored)
    export_module.check_coverage(statement, document, catalog, attachments, index, vendored)
    graph_text = export_module.serialize(document)
    coverage_text = export_module.serialize(statement)
    # The descriptor measures the artifacts, so it is built after them and before the page
    # that embeds it. It describes the three downloads and never itself or index.html:
    # index.html is the landing page a reader arrives at, not a distribution, and a
    # descriptor that hashed the page embedding it could not be written at all.
    descriptor = dataset_module.descriptor(
        site_url=SITE_URL,
        title=TITLE,
        artifacts={
            export_module.GRAPH_FILENAME: graph_text,
            export_module.COVERAGE_FILENAME: coverage_text,
            dataset_module.EVIDENCE_FILENAME: _evidence_text(),
        },
        retrieved=statement["source"]["retrieved"],
    )
    dataset_text = export_module.serialize(descriptor)
    return {
        export_module.GRAPH_FILENAME: graph_text,
        export_module.COVERAGE_FILENAME: coverage_text,
        dataset_module.DATASET_FILENAME: dataset_text,
        PAGE_FILENAME: render(catalog, ctids, attachments, dataset_jsonld=dataset_text),
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


def _published_files(output_dir: Path) -> list[str]:
    """Every file actually sitting in ``output_dir``, which is what Pages uploads."""
    return sorted(
        str(path.relative_to(output_dir))
        for path in output_dir.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


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

    # Comparing only the files the build produces cannot see a file it has stopped
    # producing. Enumerate the directory instead: anything here that no gate accounts
    # for is published to Pages and checked by nothing.
    for name in _published_files(output_dir):
        if name in artifacts or name in PUBLISHED_BY_ANOTHER_GATE:
            continue
        stale.append(
            f"{name}: committed under {output_dir.name}/ and produced by nothing. It is "
            "published as-is and no gate holds it to any code. Remove it, or record the "
            "gate that does, in PUBLISHED_BY_ANOTHER_GATE."
        )

    if stale:
        print("committed output is not what the code produces:", file=sys.stderr)
        for line in stale:
            print(f"  {line}", file=sys.stderr)
        print("run `chalkline build` and commit the result", file=sys.stderr)
        return 1
    for name, reason in sorted(PUBLISHED_BY_ANOTHER_GATE.items()):
        if (output_dir / name).is_file():
            print(f"  skip  {name}\n          not built here: {reason}")
    print(
        f"committed output matches a fresh build ({len(artifacts)} files); "
        f"no file under {output_dir.name}/ is unaccounted for"
    )
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


def authorizes(args: argparse.Namespace) -> int:
    """``authorizes`` end to end.

    A source that cannot be read exits 2 with the reason on stderr, never 0 with an empty
    answer: "no rows found" from a file that was never opened is the reading this verb
    exists to keep apart from a real absence.

    A question that cannot be asked exits 2 for the same reason. `ask` refuses an empty
    ``--code`` rather than searching for it, and that refusal used to leave this function
    as an uncaught ValueError. Python exits 1 on an uncaught exception, and 1 is
    ``DOES_NOT_AUTHORIZE``, the one code in :data:`authorizes.EXIT` that means the
    Commission published a denial. `chalkline authorizes --code "$CODE" --subject BSS`
    with ``CODE`` unset printed a traceback and exited 1, so a caller testing the exit
    status read its own empty variable as a denial of the credential. Both refusals now
    take the same path: the reason on stderr, nothing on stdout, exit 2.
    """
    try:
        source = (
            authorizes_module.source_from_catalog(_catalog())
            if args.from_sources
            else authorizes_module.source_from_graph(args.graph)
        )
    except authorizes_module.SourceUnreadable as exc:
        print(f"chalkline authorizes: {exc}", file=sys.stderr)
        return authorizes_module.EXIT[authorizes_module.Answer.UNKNOWN_AUTHORIZATION]

    try:
        result = authorizes_module.ask(
            source,
            code=args.code,
            subject_code=args.subject,
            subject_name=args.subject_name,
            document=args.document,
            title=args.title,
        )
    except ValueError as exc:
        print(f"chalkline authorizes: {exc}", file=sys.stderr)
        return authorizes_module.EXIT[authorizes_module.Answer.UNKNOWN_AUTHORIZATION]

    print(
        authorizes_module.render_json(result)
        if args.json
        else authorizes_module.render_text(result),
        end="" if not args.json else "\n",
    )
    return result.exit_code


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

    asks = sub.add_parser(
        "authorizes",
        help="does one authorization carry one subject, per the published record",
        description=authorizes_module.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    asks.add_argument("--code", required=True, help="a CTC Authorization Code, e.g. R1S")
    asks.add_argument(
        "--document",
        default=None,
        help=(
            "narrow by Document Title code, exactly, e.g. TC1 or TPSL. This is the "
            "Document Title column, which the table publishes as codes"
        ),
    )
    asks.add_argument(
        "--title",
        default=None,
        help=(
            "narrow by Authorization Title, e.g. 'Single Subject Teaching Credential'. "
            "A different column from --document, and matched separately"
        ),
    )
    subject = asks.add_mutually_exclusive_group(required=True)
    subject.add_argument("--subject", default=None, help="a subject code, e.g. BSS")
    subject.add_argument(
        "--subject-name", default=None, help="the subject name as the Commission prints it"
    )
    asks.add_argument(
        "--from-sources",
        action="store_true",
        help=(
            "answer from the vendored Commission table instead of the published graph. "
            "Only this source records the exclusions and the cross-reference chain."
        ),
    )
    asks.add_argument("--json", action="store_true", help="emit the answer as JSON")
    asks.add_argument("--graph", type=Path, default=SITE_DIR / "credentials.jsonld")

    args = parser.parse_args(argv)
    if args.command == "build":
        return build(args.output_dir)
    if args.command == "check":
        return check(args.output_dir)
    if args.command == "authorizes":
        return authorizes(args)
    return mint_ctids(args.ledger)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
