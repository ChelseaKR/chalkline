"""The live sentinel's verdict must survive the step that reports it.

`scripts/verify_live_site.py` returns three things: 0 (the live surface is what
this checkout publishes), 1 (`EXIT_DIFFERS`) and 4 (`EXIT_CANNOT_RUN`). The step
in `.github/workflows/live-integrity.yml` decides what the run's own exit code
is, and it also carries one excuse: a deploy for a newer commit may have landed
while the check ran, in which case a difference from *this* commit is the deploy
working.

Two things about that step were wrong, and neither is visible by reading it.

**It runs under `bash -e`.** The step declares no `shell:`, so GitHub's default
for a `run` block on Linux applies: `bash -e {0}`. `set -uo pipefail` cannot turn
errexit off (that needs `set +e`). So the bare line

    python3 scripts/verify_live_site.py
    verify_rc="$?"

ended the step the instant the sentinel reported a difference, and `verify_rc`
was never assigned. **The deploy-race excuse was unreachable in exactly the case
it was written for** -- five lines of comment and three of code that could only
run when there was nothing to excuse.

**The two shells disagree on every row.** Under plain `bash` -- which is what a
test that shells out naively would use -- the same body swallows the verdict
whenever `git ls-remote` fails: `remote_sha` is empty, `"" != expected_sha`
holds, and the step exits 0 over a live surface the sentinel said had drifted.
That is a real hazard for anyone who adds `shell: bash` to the step, and it is
why this module pins the shell as part of the fixture rather than trusting it.

So this test extracts the shipped step body from the YAML and RUNS it, under the
shell that ships, with `python3` and `git` stubbed, across every combination that
decides the outcome. A string assertion would have accepted the old body: the
words were all correct.
"""

from __future__ import annotations

import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "live-integrity.yml"

#: What GitHub runs a `run:` block with on Linux when the step declares no
#: `shell:`. Pinned here because it is the difference between a body that swallows
#: the sentinel's verdict and one that does not.
GITHUB_DEFAULT_SHELL = ("bash", "-e")

STEP_NAME = "Compare the live surface with what this checkout publishes"


def step_body() -> str:
    """The `run:` block of the comparison step, dedented, from the shipped YAML.

    Read as text rather than through a YAML loader so this test has no
    dependency the workflow itself does not have.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = f"- name: {STEP_NAME}\n"
    assert marker in text, f"{WORKFLOW} no longer has a step named {STEP_NAME!r}"
    after = text.split(marker, 1)[1]
    run_at = after.index("run: |\n") + len("run: |\n")
    lines = after[run_at:].splitlines()
    indent = len(lines[0]) - len(lines[0].lstrip())
    body = []
    for line in lines:
        if line.strip() and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line[indent:] if line.strip() else "")
    return "\n".join(body) + "\n"


def test_the_step_body_is_still_extractable() -> None:
    """The floor. Every case below runs this text; an empty read would pass them all."""
    body = step_body()
    assert "verify_live_site.py" in body, body
    assert "git ls-remote" in body, body
    assert len(body.splitlines()) > 10, body


def test_the_step_declares_no_shell_so_the_fixture_below_is_the_real_one() -> None:
    """If the step ever declares `shell:`, this fixture stops being what ships."""
    text = WORKFLOW.read_text(encoding="utf-8")
    after = text.split(f"- name: {STEP_NAME}\n", 1)[1]
    step = after.split("run: |", 1)[0]
    assert "shell:" not in step, (
        "the step now names a shell; update GITHUB_DEFAULT_SHELL to match it, "
        "because these cases are measured under the shell that ships"
    )


def _stub(path: Path, script: str) -> None:
    path.write_text(f"#!/bin/sh\n{script}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def run_step(tmp_path: Path, *, verify_rc: int, remote: str) -> subprocess.CompletedProcess[str]:
    """Run the shipped step body with `python3` and `git` stubbed.

    ``remote`` is one of: ``"same"`` (ls-remote names this commit), ``"moved"``
    (it names another), ``"fails"`` (the read itself fails, as a network blip or
    a rate limit would), ``"empty"`` (it succeeds and names nothing).
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _stub(bin_dir / "python3", f"exit {verify_rc}")
    if remote == "fails":
        git_body = (
            'if [ "$1" = "rev-parse" ]; then echo aaaaaaa; exit 0; fi\n'
            'echo "fatal: unable to access" >&2; exit 128'
        )
    elif remote == "empty":
        git_body = 'if [ "$1" = "rev-parse" ]; then echo aaaaaaa; exit 0; fi\nexit 0'
    else:
        sha = "aaaaaaa" if remote == "same" else "bbbbbbb"
        git_body = (
            'if [ "$1" = "rev-parse" ]; then echo aaaaaaa; exit 0; fi\n'
            f'printf "{sha}\\trefs/heads/main\\n"'
        )
    _stub(bin_dir / "git", git_body)

    script = tmp_path / "step.sh"
    script.write_text(step_body(), encoding="utf-8")
    real_sh = shutil.which("sh") or "/bin/sh"
    env = {
        "PATH": f"{bin_dir}:{Path(real_sh).parent}:/usr/bin:/bin",
        "HOME": str(tmp_path),
    }
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [*GITHUB_DEFAULT_SHELL, str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("remote", ["same", "moved", "fails", "empty"])
def test_a_clean_sentinel_run_passes_whatever_the_remote_read_does(
    tmp_path: Path, remote: str
) -> None:
    """The remote read is only a decision input when there is a difference.

    Under the old body a `git ls-remote` blip on a run whose verdict was already
    green failed the step with git's own 128.
    """
    result = run_step(tmp_path, verify_rc=0, remote=remote)
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)


@pytest.mark.parametrize("verify_rc", [1, 4])
def test_a_difference_is_reported_when_the_remote_has_not_moved(
    tmp_path: Path, verify_rc: int
) -> None:
    """`EXIT_DIFFERS` (1) and `EXIT_CANNOT_RUN` (4) both reach the run's exit code."""
    result = run_step(tmp_path, verify_rc=verify_rc, remote="same")
    assert result.returncode == verify_rc, (result.returncode, result.stdout, result.stderr)


@pytest.mark.parametrize("verify_rc", [1, 4])
@pytest.mark.parametrize("remote", ["fails", "empty"])
def test_an_unreadable_remote_cannot_excuse_a_difference(
    tmp_path: Path, verify_rc: int, remote: str
) -> None:
    """ "main moved" and "I could not ask" are different answers.

    This is the case the whole module exists for: an unestablishable excuse must
    not become an excuse.
    """
    result = run_step(tmp_path, verify_rc=verify_rc, remote=remote)
    assert result.returncode == verify_rc, (result.returncode, result.stdout, result.stderr)
    assert "::error::" in result.stdout, result.stdout


def test_a_real_deploy_race_is_still_excused(tmp_path: Path) -> None:
    """The excuse is the point of the step; it must be reachable and it must work.

    Under the shipped body before this test existed it was reachable only when
    `verify_rc` was 0, i.e. never when it mattered.
    """
    result = run_step(tmp_path, verify_rc=1, remote="moved")
    assert result.returncode == 0, (result.returncode, result.stdout, result.stderr)
    assert "::warning::" in result.stdout, result.stdout
    assert "bbbbbbb" in result.stdout, result.stdout


def test_the_deploy_race_warning_names_both_commits(tmp_path: Path) -> None:
    """A warning reading "moved to  while this ran" is what an empty sha looked like."""
    result = run_step(tmp_path, verify_rc=1, remote="moved")
    warning = next(line for line in result.stdout.splitlines() if line.startswith("::warning::"))
    assert re.search(r"from \S+ to \S+", warning), warning
