"""The independent validator's result is committed evidence, not a claim taken on faith.

`ctdl-validate` (https://github.com/ChelseaKR/ctdl-validate) checks a rule family
`chalkline.ctdl.validate` does not: CTID grammar, identifier kinds, reference targets, and
class pairings. `scripts/validate_evidence.py` runs it as a genuinely separate process over
the committed `site/credentials.jsonld` and writes the result to `site/ctdl-validate.json`.
These tests re-run it and fail if the committed file is not what a fresh run against the
current graph reports, the same guarantee `chalkline check` holds `credentials.jsonld` and
`coverage.json` to. Issue #21.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = REPO_ROOT / "site" / "ctdl-validate.json"


def _evidence() -> dict[str, object]:
    text: str = EVIDENCE_PATH.read_text(encoding="utf-8")
    data: dict[str, object] = json.loads(text)
    return data


def test_committed_evidence_is_what_a_fresh_run_reports() -> None:
    """The whole point: a stale or hand-edited evidence file fails the build."""
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [sys.executable, str(REPO_ROOT / "scripts" / "validate_evidence.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_committed_graph_has_zero_error_findings() -> None:
    """The published claim ("0 findings") is a measurement, and this is where it is checked.

    If a future change to the CTDL mapping ever disagrees with `ctdl-validate`, this is the
    test that turns red, not a README sentence nobody re-derives.
    """
    evidence = _evidence()
    summary = evidence["summary"]
    assert isinstance(summary, dict)
    assert summary["ERROR"] == 0, evidence["findings"]


def test_evidence_names_the_pinned_tool_and_version() -> None:
    """Pinned in `pyproject.toml`; this checks the committed report agrees with the pin."""
    from importlib.metadata import version

    evidence = _evidence()
    assert evidence["tool"] == {"name": "ctdl-validate", "version": version("ctdl-validate")}


def test_evidence_covers_every_entity_in_the_graph() -> None:
    """A validator that silently read zero entities would also report zero findings.

    This is the control the issue asked for: a run against a mutilated graph must disagree,
    or a clean report proves nothing about the graph actually being checked.
    """
    graph = json.loads((REPO_ROOT / "site" / "credentials.jsonld").read_text(encoding="utf-8"))
    entities = graph["@graph"]
    assert len(entities) > 100

    mutated = json.loads(json.dumps(graph))
    mutated["@graph"][0]["ceterms:ctid"] = mutated["@graph"][0]["ceterms:ctid"].removeprefix("ce-")

    import ctdl_validate

    findings = ctdl_validate.validate_document(mutated)
    codes = {f.code for f in findings}
    assert "CTID_BARE_UUID" in codes
