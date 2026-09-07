"""Provenance is checked, not asserted.

Every vendored artifact carries a sidecar naming its URL, retrieval date, and sha256. If a
snapshot is refreshed without updating its sidecar, or edited by hand, these tests fail.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Final

import pytest

from chalkline.ctdl import export
from chalkline.sources import leaflets, sort_table

REPO_ROOT = Path(__file__).resolve().parents[1]

LEAFLET_SNAPSHOTS = tuple(sorted((REPO_ROOT / "data" / "source" / "leaflets").glob("*.html")))

SORT_TABLE = REPO_ROOT / "data" / "source" / "authorization-sort-table.html"
LEAFLET_INDEX = REPO_ROOT / "data" / "source" / "credential-leaflets.html"
CTDL_CONTEXT = REPO_ROOT / "src" / "chalkline" / "ctdl" / "ctdl-context.json"
CTDL_SCHEMA = REPO_ROOT / "src" / "chalkline" / "ctdl" / "ctdl-schema.json"

SIDECAR_SUFFIX = ".source.json"

#: Every directory that holds a vendored third-party artifact. `VENDORED` used to be a
#: literal tuple naming four files plus a glob over the leaflet snapshots, which meant a
#: new capture dropped anywhere but `leaflets/` was bound by nothing: not the hash test,
#: not the size test, not the requirement that PROVENANCE.md publish a row for it. Adding
#: `data/source/new-capture.html` and running this module passed, 89 tests green. So the
#: set is discovered from the tree instead, in both directions -- a sidecar whose artifact
#: is missing fails, and an artifact with no sidecar fails -- and the four named constants
#: above are asserted to still be in what discovery finds, so discovery going vacuous or
#: silently narrowing is itself a failure.
#: `(directory, suffixes)`. `suffixes` is `None` where every file in the directory is a
#: vendored artifact, and a tuple where the directory holds this project's own code too:
#: `src/chalkline/ctdl/` is a Python package whose vendored content is the two JSON
#: specification documents, so a `.py` there is authored, not captured. Stating it as data
#: keeps the judgement reviewable instead of buried in a filename test.
VENDORED_ROOTS: tuple[tuple[Path, tuple[str, ...] | None], ...] = (
    (REPO_ROOT / "data" / "source", None),
    (REPO_ROOT / "src" / "chalkline" / "ctdl", (".json",)),
)


def _discovered() -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """`(artifacts, orphans)`: every file under a vendored root, split by sidecar."""
    artifacts: list[Path] = []
    orphans: list[Path] = []
    for root, suffixes in VENDORED_ROOTS:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name.endswith(SIDECAR_SUFFIX):
                continue
            if suffixes is not None and path.suffix not in suffixes:
                continue
            if path.with_suffix(SIDECAR_SUFFIX).is_file():
                artifacts.append(path)
            else:
                orphans.append(path)
    return tuple(artifacts), tuple(orphans)


VENDORED, UNSIDECARED = _discovered()


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


def test_every_vendored_artifact_is_discovered_not_listed() -> None:
    """The denominator has to come off the tree, or a new capture is bound by nothing.

    Adding `data/source/new-capture.html` to the previous version of this module changed
    nothing: 89 tests passed with an unhashed, unsourced, unpublished third-party capture
    sitting in the repository. Every check below reads `VENDORED`, so `VENDORED` is the
    one thing that must not be a hand-maintained list.
    """
    assert VENDORED, "no vendored artifact was discovered; every check below would be empty"
    for named in (SORT_TABLE, LEAFLET_INDEX, CTDL_CONTEXT, CTDL_SCHEMA):
        assert named in VENDORED, f"discovery no longer finds {named.name}"
    for snapshot in LEAFLET_SNAPSHOTS:
        assert snapshot in VENDORED, f"discovery no longer finds {snapshot.name}"


def test_no_vendored_file_is_here_without_a_sidecar() -> None:
    """A capture with no sidecar has no recorded URL, date, size or hash to check."""
    assert UNSIDECARED == (), (
        "these files sit under a vendored root with no "
        f"{SIDECAR_SUFFIX} beside them, so nothing records where they came from: "
        + ", ".join(str(path.relative_to(REPO_ROOT)) for path in UNSIDECARED)
    )


def test_no_sidecar_describes_a_file_that_is_not_there() -> None:
    """The other direction: a sidecar whose artifact is gone is provenance for nothing."""
    found = 0
    for root, _ in VENDORED_ROOTS:
        for meta_path in sorted(root.rglob(f"*{SIDECAR_SUFFIX}")):
            named = str(json.loads(meta_path.read_text(encoding="utf-8"))["file"])
            artifact = meta_path.parent / named
            assert artifact.is_file(), f"{meta_path.name} names {named}, which is not here"
            assert artifact in VENDORED, f"{named} is described but not checked"
            found += 1
    assert found == len(VENDORED), (
        f"{found} sidecars describe {len(VENDORED)} discovered artifacts; the two sets "
        "have to be the same or one side is unchecked"
    )


PROVENANCE = REPO_ROOT / "PROVENANCE.md"

_PROVENANCE_ROW_RE = re.compile(
    r"^\|\s*`(?P<name>[^`]+)`\s*\|.*?\|\s*(?P<bytes>[\d,]+)\s*\|\s*"
    r"`(?P<prefix>[0-9a-f]{8})…(?P<suffix>[0-9a-f]+)`\s*\|\s*$",
    re.MULTILINE,
)
"""A row of either sources table: the artifact, its byte count, and its abbreviated sha256."""


def _vendored_named(name: str) -> Path:
    """The artifact a PROVENANCE row names, by path or by leaflet code."""
    if name.endswith((".html", ".json")):
        return REPO_ROOT / name
    return REPO_ROOT / "data" / "source" / "leaflets" / f"{name}.html"


def provenance_rows() -> dict[Path, tuple[int, str, str]]:
    """Every artifact PROVENANCE.md tabulates, with the size and hash it publishes."""
    text = PROVENANCE.read_text(encoding="utf-8")
    return {
        _vendored_named(m.group("name")): (
            int(m.group("bytes").replace(",", "")),
            m.group("prefix"),
            m.group("suffix"),
        )
        for m in _PROVENANCE_ROW_RE.finditer(text)
    }


def test_provenance_tabulates_every_vendored_artifact_and_nothing_else() -> None:
    """The denominator, named. A table that stopped listing files would otherwise pass below."""
    assert set(provenance_rows()) == set(VENDORED)


@pytest.mark.parametrize("path", VENDORED, ids=lambda p: p.name)
def test_the_hash_provenance_publishes_is_the_hash_on_disk(path: Path) -> None:
    """PROVENANCE.md transcribes the sidecars by hand, so the transcription is checked too.

    The sidecars were already bound to the bytes. The document a reader actually opens was
    not, and four of its ten leaflet hashes had the wrong tail: correct eight-character
    prefix, correct byte count, and a suffix that belonged to no file in the repository.
    An abbreviation nothing recomputes is a citation, not a checksum.
    """
    rows = provenance_rows()
    assert path in rows, f"PROVENANCE.md publishes no row for {path.name}"
    published_bytes, prefix, suffix = rows[path]
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    assert published_bytes == len(payload)
    assert digest.startswith(prefix), f"{path.name}: PROVENANCE says {prefix}…, file is {digest}"
    assert digest.endswith(suffix), f"{path.name}: PROVENANCE says …{suffix}, file is {digest}"


def test_the_parsers_point_at_the_urls_the_sidecars_record() -> None:
    assert sidecar(SORT_TABLE)["final_url"] == sort_table.SOURCE_URL
    assert sidecar(LEAFLET_INDEX)["final_url"] == leaflets.SOURCE_URL


def test_the_commission_address_is_printed_in_the_vendored_artifact() -> None:
    """The organization address is transcribed from the page footer, so the page must say it."""
    page = SORT_TABLE.read_text(encoding="utf-8")
    assert export.ORGANIZATION_ADDRESS["street"] in page
    assert export.ORGANIZATION_ADDRESS["locality"] in page
    assert export.ORGANIZATION_ADDRESS["postal_code"] in page
    assert export.ORGANIZATION_NAME in page


def test_the_published_scope_statement_is_still_on_the_page() -> None:
    """The Commission's own statement of what the table covers, quoted in the sidecar.

    The length guard is the check. ``"" in anything`` is True, and the sidecars are the one
    artifact class not covered by the hash test above (it hashes the payload, not the file
    beside it), so blanking this field would have satisfied the containment test in silence.
    """
    page = SORT_TABLE.read_text(encoding="utf-8")
    quoted = str(sidecar(SORT_TABLE)["scope_statement_published_on_page"])
    assert len(quoted) > 40, f"the recorded scope statement is {len(quoted)} characters"
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


def test_every_leaflet_snapshot_is_either_attached_or_a_recorded_non_match(
    real_catalog: object, leaflet_index: object, real_leaflets: object
) -> None:
    """Every snapshot is here for a reason, and the reason is written down.

    This used to require every snapshot to be attached, which was true only because a
    leaflet's page could not be read until after its index title had already matched. A
    leaflet's own page title is now evidence too, and evidence has to be retrieved before it
    can be weighed: several of these pages were fetched to see what the Commission calls the
    document, and the answer was that it calls it something the authorization is not called.

    A snapshot that matched nothing is kept, because a finding nobody can re-read is not a
    finding. What it must not be is unexplained, so its sidecar has to say which it is.
    """
    from chalkline.attachment import attach
    from chalkline.model import Catalog

    assert isinstance(real_catalog, Catalog)
    attachments = attach(real_catalog, leaflet_index, published=real_leaflets)  # type: ignore[arg-type]
    attached = {attachment.leaflet.code for attachment in attachments.values()}
    assert attached <= {path.stem for path in LEAFLET_SNAPSHOTS}, (
        "an attached leaflet has no vendored snapshot, so its prose was never read"
    )
    unattached = {path.stem for path in LEAFLET_SNAPSHOTS} - attached
    for path in LEAFLET_SNAPSHOTS:
        purpose = sidecar(path)["purpose"]
        assert isinstance(purpose, str)
        expected = "Retrieved and not attached" if path.stem in unattached else "Attached"
        assert purpose.startswith(expected), (
            f"{path.stem}: its sidecar opens {purpose[:40]!r}, and it is "
            f"{'not ' if path.stem in unattached else ''}attached"
        )
    assert unattached, "the non-match branch above asserted nothing"


NETWORKING = (
    "urllib",
    "urllib3",
    "http",
    "socket",
    "socketserver",
    "ssl",
    "ftplib",
    "poplib",
    "imaplib",
    "smtplib",
    "telnetlib",
    "xmlrpc",
    "webbrowser",
    "asyncio",
    "subprocess",
    "requests",
    "httpx",
    "aiohttp",
)
"""Top-level modules that can open a socket, or that exist to, or that can hand the job off.

``subprocess`` earns its place the hard way: the scan is the whole mechanism behind "nothing
in this package reaches the network", and a list that stopped at the obvious HTTP clients let
``subprocess.run(["curl", ...])`` through without a word. Reaching the network by asking
another program to do it is still reaching the network. ``asyncio`` and ``webbrowser`` are
here for the same reason."""


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
    """No module under ``src/chalkline/`` reaches the network, however it might try to.

    This is a claim about the package and nothing wider. Two files outside it do open sockets,
    and the scan below is the check that holds the repository-wide claim the documents make.
    Until 2026-09-06 this docstring restated that wider claim, which it has never tested.
    """
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


def test_the_one_module_allowed_to_reach_the_commission_does() -> None:
    """The scan is pointed at code that would fail it if it were in the package."""
    fetcher = REPO_ROOT / "scripts" / "fetch_sources.py"
    assert networking_imports(fetcher.read_text(encoding="utf-8")) != []


# --- The repository-wide claim, which is the one the documents actually make ----------------
#
# `test_no_module_in_the_package_opens_a_socket` above proves a claim about `src/chalkline/`.
# README.md and PROVENANCE.md made a claim about the repository: that `fetch_sources.py` was
# "the only code in this repository that opens a socket", run by hand, and that "Tests and CI
# are hermetic". `scripts/verify_live_site.py` had opened HTTPS connections since cf3c7f5
# (2026-08-29), unattended, on the daily cron in `.github/workflows/live-integrity.yml`, and
# `make audit` had been reaching the PyPI advisory API from inside the merge gate since
# 2026-08-21. The prose cited the package test as its evidence, and the package test proves
# something narrower than the prose said.
#
# So the repository-wide claim gets a repository-wide check, and the documents that make it
# get read.

HANDS_OFF_ONLY: Final = frozenset({"subprocess", "asyncio", "webbrowser", "urllib.parse"})
"""Networking imports that do not themselves open a connection.

``NETWORKING`` is deliberately wide: inside `src/chalkline/` even ``subprocess`` is a finding,
because ``subprocess.run(["curl", ...])`` reaches the network by asking another program to. A
repository-wide scan cannot use that width, because ``scripts/validate_evidence.py`` and
``tests/test_ctdl_validate_evidence.py`` both run ``ctdl-validate`` as a subprocess and neither
goes near a socket, and ``verify_live_site.py`` parses a URL with ``urllib.parse``. Excluding
them by name here keeps the wide scan wide where it belongs and makes this one a statement
about connections. The exclusions are listed rather than pattern-matched so that adding one is
a reviewable line.
"""

SCANNED_DIRECTORIES: Final = ("src", "tests", "scripts")

OPENS_A_SOCKET: Final = (
    "scripts/check_links.py",
    "scripts/fetch_sources.py",
    "scripts/verify_live_site.py",
)
"""Every file in this repository that opens a socket, which is the set the documents name."""


def connection_imports(source: str) -> list[str]:
    """The networking imports that open a connection rather than being able to delegate one."""
    return [name for name in networking_imports(source) if name not in HANDS_OFF_ONLY]


def test_the_files_that_open_a_socket_are_the_two_the_documents_name() -> None:
    """The repository-wide version of the claim the repository-wide prose makes."""
    scanned = sorted(
        path for directory in SCANNED_DIRECTORIES for path in (REPO_ROOT / directory).rglob("*.py")
    )
    assert len(scanned) >= 30, f"scanned {len(scanned)} files, which is too few to mean anything"
    opens = sorted(
        str(path.relative_to(REPO_ROOT))
        for path in scanned
        if connection_imports(path.read_text(encoding="utf-8"))
    )
    assert opens == sorted(OPENS_A_SOCKET), (
        f"the files that open a socket are {opens}, and README.md and PROVENANCE.md say they "
        f"are {sorted(OPENS_A_SOCKET)}. Update both documents and this list together: the "
        "last time a third one appeared, the documents went on naming one for eight days."
    )


@pytest.mark.parametrize("name", OPENS_A_SOCKET)
@pytest.mark.parametrize("document", ["README.md", "PROVENANCE.md"])
def test_both_of_them_are_named_where_the_network_posture_is_described(
    document: str, name: str
) -> None:
    """A reader auditing the network posture meets both names, or this fails.

    This is the check that was missing. The defect was never that the sentinel was hidden in
    the code; it is reasoned about at length in its own workflow file. It was that the two
    documents a reader consults about outbound requests did not mention it, and nothing
    noticed, because nothing read those documents for this.
    """
    text = (REPO_ROOT / document).read_text(encoding="utf-8")
    assert name in text, (
        f"{document} does not name {name}, which opens a socket. Both documents describe this "
        "repository's network posture, so both have to name everything that reaches the network."
    )


@pytest.mark.parametrize(
    ("source", "opens"),
    [
        ("import subprocess", False),
        ("from urllib.parse import urlsplit", False),
        ("import json", False),
        ("import ssl", True),
        ("from http.client import HTTPSConnection", True),
        ("import urllib.request", True),
    ],
)
def test_the_connection_scan_separates_opening_from_delegating(source: str, opens: bool) -> None:
    """The control. A narrowed scan that narrowed to nothing would pass the test above."""
    assert bool(connection_imports(source)) is opens
