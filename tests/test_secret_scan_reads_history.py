"""The `secret-scan` check must read every commit, not the commit it was handed.

`secret-scan` is a required status check on `main`. Until 2026-09-13 it was
`gitleaks/gitleaks-action`, which chooses its range from the triggering event:

    push        gitleaks detect --log-opts=--no-merges --first-parent BASE^..HEAD
    push (1)    gitleaks detect --log-opts=-1          <- exactly one commit
    pull_request the pull request's own commits

Every squash merge into `main` is a one-commit push, so the required check read
1 of `main`'s 94 commits, and `ci.yml` has no `schedule`, so no other lane ever
read more. A credential added in one commit and deleted in the next was
invisible to it.

`fetch-depth: 0` did not prevent that and cannot: it decides how much history
`actions/checkout` puts on disk, not how much of it the scanner is asked to
read. A checkout deep enough to scan and an invocation that declines to is
precisely the state this repository was in. So the assertions below are about
the *invocation*, and the `fetch-depth: 0` assertion is kept only as the
necessary precondition it actually is.

Measured on a throwaway clone of this repository with the fix in hand: a
random, real-shaped AWS key planted in one commit and removed in the next left
`gitleaks git . --log-opts=-1` exiting 0, while `gitleaks git .` exited 1.
"""

from __future__ import annotations

import re
from pathlib import Path

CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"

# Four conformance checks elsewhere in this portfolio passed because they matched
# a tool name inside a COMMENT. The comment above the scan step names both the
# action that was removed and the flag that must not return, so every assertion
# below reads the file with its comments stripped and would not notice them.
_COMMENT = re.compile(r"(?m)^\s*#.*$|\s+#.*$")


def _ci_code() -> str:
    return _COMMENT.sub("", CI.read_text(encoding="utf-8"))


def test_the_scanner_is_not_handed_a_range() -> None:
    text = _ci_code()
    assert "gitleaks git . --no-banner --redact --exit-code 1" in text, (
        "the secret scan no longer runs `gitleaks git .`. Whatever replaces it must "
        "still walk every commit reachable from HEAD on every event."
    )
    assert "--log-opts" not in text, (
        "`--log-opts` scopes gitleaks to a commit range. A range chosen from the "
        "triggering event is how this check came to read 1 of 94 commits."
    )


def test_the_event_driven_action_does_not_come_back() -> None:
    assert "gitleaks/gitleaks-action" not in _ci_code(), (
        "gitleaks/gitleaks-action picks its range from the event and degrades to "
        "`--log-opts=-1` on a single-commit push, which is every squash merge here."
    )


def test_checkout_still_fetches_the_history_the_scan_walks() -> None:
    """Necessary, not sufficient: without it there is nothing on disk to walk."""
    text = _ci_code()
    assert re.search(r"^\s*fetch-depth:\s*0\s*(?:#.*)?$", text, flags=re.MULTILINE), (
        "`fetch-depth: 0` is gone from the secret-scan checkout, so `gitleaks git .` "
        "would walk the single commit actions/checkout fetched. This is the "
        "precondition for a history scan; the invocation above is what makes it one."
    )


def test_the_pinned_binary_is_checksum_verified() -> None:
    text = _ci_code()
    assert "gitleaks_checksums.txt" in text and "sha256sum --check --strict" in text, (
        "the gitleaks binary is downloaded without verifying the published checksum"
    )
