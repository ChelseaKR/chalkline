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
"""

from __future__ import annotations

import hashlib
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

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


def main() -> int:
    if not all(url.startswith("https://") for url, _ in TARGETS):  # pragma: no cover
        raise ValueError("every source must be fetched over https")
    return max(fetch(url, destination) for url, destination in TARGETS)


if __name__ == "__main__":
    raise SystemExit(main())
