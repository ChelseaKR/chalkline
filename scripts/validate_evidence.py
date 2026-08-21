#!/usr/bin/env python3
"""Run the independent CTDL validator over the committed graph and write or check its report.

``chalkline.ctdl.validate`` checks one rule family against the vendored CTDL schema encoding:
class existence, property existence, ``schema:domainIncludes`` pairing, range shape. It caught
``ceterms:codedNotation`` on a ``ceterms:License``. `ctdl-validate`
(https://github.com/ChelseaKR/ctdl-validate) is a second, independently written
implementation of the same specification, checking a rule family this project's own validator
does not: CTID grammar, identifier kinds, reference targets, class pairings. Neither subsumes
the other, so both run over the same published graph, and the interesting outcome is a
disagreement between the two, not a pass. See issue #21.

This script invokes the installed ``ctdl-validate`` CLI as a genuinely separate process,
never as a library import, because the point of a second opinion is that this project's own
code cannot shape it:

    python scripts/validate_evidence.py            # run it, write site/ctdl-validate.json
    python scripts/validate_evidence.py --check     # run it, fail if the committed file differs

``make validate`` runs the ``--check`` form. ``tests/test_ctdl_validate_evidence.py`` runs the
same form again from the test suite, so a stale or hand-edited ``site/ctdl-validate.json``
fails the build whether it is caught by ``make verify`` or by ``pytest`` alone.

No network calls: ``ctdl-validate``'s own README states plainly that only its ``extract``
subcommand opens a connection, and this script never invokes that subcommand.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = REPO_ROOT / "site" / "credentials.jsonld"
EVIDENCE_PATH = REPO_ROOT / "site" / "ctdl-validate.json"


def run_validator() -> tuple[int, str]:
    """Invoke the installed ``ctdl-validate`` CLI against the committed graph.

    Returns the process's exit code (0: no ERROR finding, 1: at least one, 2: the input could
    not be read) and its stdout. A resolved absolute path, never a bare command name, so ruff's
    S607 (starting a process with a partial executable path) has nothing to flag.
    """
    executable = shutil.which("ctdl-validate")
    if executable is None:
        raise SystemExit(
            "ctdl-validate is not on PATH. It is a pinned dev dependency: run `uv sync` "
            "(or `make install`) first."
        )
    result = subprocess.run(  # noqa: S603 -- fixed argv below, no shell, no untrusted input
        [executable, str(GRAPH_PATH), "--format", "json"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 2:
        print(result.stderr, file=sys.stderr, end="")
        raise SystemExit(f"ctdl-validate could not read {GRAPH_PATH}")
    return result.returncode, result.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed evidence file is not what a fresh run reports",
    )
    args = parser.parse_args(argv)

    exit_code, output = run_validator()
    if not output.endswith("\n"):
        output += "\n"

    if args.check:
        if not EVIDENCE_PATH.exists():
            print(
                f"{EVIDENCE_PATH} does not exist: run `python scripts/validate_evidence.py` "
                "without --check to write it",
                file=sys.stderr,
            )
            return 1
        committed = EVIDENCE_PATH.read_text(encoding="utf-8")
        if committed != output:
            print(
                f"{EVIDENCE_PATH} is not what a fresh ctdl-validate run reports against the "
                "committed graph; run `python scripts/validate_evidence.py` and commit the "
                "result",
                file=sys.stderr,
            )
            return 1
        print(f"{EVIDENCE_PATH} matches a fresh ctdl-validate run")
    else:
        EVIDENCE_PATH.write_text(output, encoding="utf-8")
        print(f"wrote {EVIDENCE_PATH}")

    if exit_code != 0:
        print(
            f"ctdl-validate reported at least one ERROR finding against {GRAPH_PATH} "
            f"(exit {exit_code})",
            file=sys.stderr,
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
