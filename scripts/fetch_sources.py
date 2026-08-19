#!/usr/bin/env python3
"""Refresh the vendored source snapshots. The only code in this repository that opens a socket.

Run by hand, never by CI, never by the test suite, never by `make build`. Everything else in
this project reads the committed snapshots under ``data/source/``, which is what makes the
build deterministic and the tests hermetic.

Each fetch is a single unauthenticated GET with an honest, identifying User-Agent. The
Commission's robots.txt (https://www.ctc.ca.gov/robots.txt) disallows only ``/wp-admin/``,
so both paths below are permitted. If a request is refused, this script reports the status
and stops. It does not retry behind a different identity, rotate headers, or otherwise work
around a refusal: a site that declines automated access has said something, and the answer
is to transcribe by hand and label the result, not to ask again in a costume.

After a successful fetch, update the ``retrieved``, ``bytes``, and ``sha256`` fields in the
``.source.json`` beside each file (this script prints them), then rebuild and review the diff.

Two modes::

    python scripts/fetch_sources.py                       # the four base artifacts
    python scripts/fetch_sources.py leaflets cl-858 ...   # one leaflet landing page each

The leaflet mode takes explicit leaflet codes rather than walking the whole index, which
keeps the request count equal to the number of documents someone actually decided to look at.

Which codes are worth naming has one wrinkle. A leaflet has two published titles, the index's
and the page's own, and the second is evidence that has to be retrieved before it can be
weighed: the Commission's index calls CL-902 "The Teaching Permit for Statutory Leave (TPSL)"
and the page calls it "Teaching Permit for Statutory Leave", and only the second identifies
an authorization this project models. So a leaflet whose index title is close to an
authorization's may be retrieved to read what the Commission itself calls the document. The
answer is often that it does not match, and that is a finding: the snapshot stays vendored,
and its sidecar records which it was. What is *not* worth retrieving is a leaflet whose
answer could not change the graph either way --- one whose only plausible authorization is
excluded for want of a published scope.

Requests in one run are spaced by ``PAUSE_SECONDS``.
"""

from __future__ import annotations

import hashlib
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PAUSE_SECONDS = 2.0
"""Held between consecutive requests in one run.

A run that names several leaflets is still several requests to one small state agency's
CMS, and issuing them as fast as the interpreter can is not the same thing as issuing them
politely. This is not rate-limit avoidance: nothing here has ever been rate-limited. It is
that the only cost of waiting is this script's own wall clock.
"""

USER_AGENT = (
    "chalkline/0.1 (+https://github.com/ChelseaKR/chalkline) "
    "one-off source snapshot for an unofficial CTDL modeling demonstration"
)

TARGETS: tuple[tuple[str, Path], ...] = (
    (
        "https://www.ctc.ca.gov/credentials/assignment-resources/authorization-sort-table",
        REPO_ROOT / "data" / "source" / "authorization-sort-table.html",
    ),
    (
        "https://www.ctc.ca.gov/credentials/leaflets",
        REPO_ROOT / "data" / "source" / "credential-leaflets.html",
    ),
    (
        "https://credreg.net/ctdl/schema/context/json",
        REPO_ROOT / "src" / "chalkline" / "ctdl" / "ctdl-context.json",
    ),
    (
        "https://credreg.net/ctdl/schema/encoding/json",
        REPO_ROOT / "src" / "chalkline" / "ctdl" / "ctdl-schema.json",
    ),
)


def fetch(url: str, destination: Path) -> int:
    """Retrieve one source and report what to write into its provenance sidecar.

    The scheme is re-checked here, immediately before the request, rather than relying on
    the check in :func:`main`. ``urllib`` honours ``file://``, so a URL that reached this
    function by some other path could otherwise read a local file and write it into
    ``data/source/`` as though a public site had served it.
    """
    if not url.startswith("https://"):
        raise ValueError(f"refusing to fetch {url!r}: only https sources are retrieved")
    # nosemgrep: dynamic-urllib-use-detected - scheme is pinned to https on the line above
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        # nosemgrep: dynamic-urllib-use-detected - scheme is pinned to https above
        with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
            final_url = response.geturl()
            payload = response.read()
    except urllib.error.HTTPError as error:
        print(f"{url}: refused with HTTP {error.code}. Stopping.", file=sys.stderr)
        print(
            "  Do not retry with different headers. Transcribe the page by hand instead, "
            "and label the result as hand-transcribed in PROVENANCE.md.",
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError as error:  # pragma: no cover - network failure path
        print(f"{url}: {error.reason}", file=sys.stderr)
        return 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    print(f"{destination.relative_to(REPO_ROOT)}")
    print(f"  final_url: {final_url}")
    print(f"  retrieved: {date.today().isoformat()}")
    print(f"  bytes:     {len(payload)}")
    print(f"  sha256:    {hashlib.sha256(payload).hexdigest()}")
    return 0


LEAFLET_DIR = REPO_ROOT / "data" / "source" / "leaflets"

LEAFLET_BASE = "https://www.ctc.ca.gov/credentials/leaflets/"


def leaflet_targets(codes: list[str]) -> list[tuple[str, Path]]:
    """The landing page for each named leaflet, and where its snapshot belongs.

    The code is taken straight from the vendored index's own link path, so this cannot
    fabricate a URL for a leaflet the Commission does not publish.
    """
    return [(f"{LEAFLET_BASE}{code}/", LEAFLET_DIR / f"{code}.html") for code in codes]


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments and arguments[0] == "leaflets":
        codes = arguments[1:]
        if not codes:  # pragma: no cover - operator error path
            print("usage: fetch_sources.py leaflets CODE [CODE ...]", file=sys.stderr)
            return 2
        targets = leaflet_targets(codes)
    else:
        targets = list(TARGETS)
    if not all(url.startswith("https://") for url, _ in targets):  # pragma: no cover
        raise ValueError("every source must be fetched over https")
    results = []
    for index, (url, destination) in enumerate(targets):
        if index:
            time.sleep(PAUSE_SECONDS)
        results.append(fetch(url, destination))
    return max(results)


if __name__ == "__main__":
    raise SystemExit(main())
