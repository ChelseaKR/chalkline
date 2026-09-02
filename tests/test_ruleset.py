"""The committed ruleset must not be a lockout waiting to be re-applied.

`.github/rulesets/main.json` is committed under CI-CD-STANDARD §5 so the posture on `main`
is reviewable in a diff, and `.github/rulesets/README.md` documents applying it with
`gh api repos/ChelseaKR/chalkline/rulesets -X POST --input .github/rulesets/main.json`. The
file carried `"bypass_actors": []` from the day it was written, so following this
repository's own instructions was enough to strip the owner's bypass from the live ruleset
and lock her out of her own repository. GitHub returns 201 for that apply exactly as it does
for any other, so nothing would have warned. It is not hypothetical: an agent applied a
no-bypass ruleset elsewhere in this portfolio and restoring access took a sweep across
eighteen repositories.

Correcting the file once is not the fix, because the file can regress and nothing in `src/`
or `tests/` read it. This module is the fix: the empty list is now a test failure.

Every check here is written to fail closed, which is the same discipline `chalkline check`
holds the built site to. The predicates are pure functions of a parsed document, run against
documents they must reject as well as against the committed one, and `load_ruleset` refuses
a missing or unparseable file rather than returning something empty that the assertions
below would then read as "nothing wrong". A guard that passes when its subject is absent is
the defect it exists to catch. The parse is load-bearing for a second reason: a malformed
file still contains the literal string `bypass_actors`, so a grep would vouch for a document
GitHub could not read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RULESET = REPO_ROOT / ".github" / "rulesets" / "main.json"
RULESET_DOC = REPO_ROOT / ".github" / "rulesets" / "README.md"

OWNER_BYPASS = {
    "actor_id": 5,
    "actor_type": "RepositoryRole",
    "bypass_mode": "always",
}
"""The repository owner's standing bypass, and the only entry this file may carry.

`RepositoryRole` 5 is the admin role. It is what live ruleset `21156701` on this repository
reports for `bypass_actors`, read back on 2026-08-29. `bypass_mode` is `always` rather than
the `pull_request` CI-CD-STANDARD asks for at CICD-15, because a bypass that only works
inside a pull request is no use when the thing that is wedged is the pull request.
"""


def load_ruleset() -> dict[str, Any]:
    """The committed ruleset, or a failure. Never a silent empty document.

    The two ways a check like this passes vacuously are a missing file and an unparseable
    one, so both are failures here rather than defaults.
    """
    if not RULESET.is_file():
        pytest.fail(f"{RULESET} is missing; the committed ruleset is what this checks")
    try:
        loaded = json.loads(RULESET.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        pytest.fail(f"{RULESET} is not parseable JSON, so nothing can vouch for it: {exc}")
    if not isinstance(loaded, dict):
        pytest.fail(f"{RULESET} is not a JSON object")
    return loaded


def lockout_risk(ruleset: dict[str, Any]) -> str | None:
    """Why applying this ruleset would lock the owner out, or ``None`` if it would not.

    A pure function of a parsed document, so it can be run against the documents it has to
    reject as well as against the one on disk.
    """
    if "bypass_actors" not in ruleset:
        return "no bypass_actors key at all, which GitHub reads as an empty list"
    actors = ruleset["bypass_actors"]
    if not isinstance(actors, list):
        return f"bypass_actors is {type(actors).__name__}, not a list"
    if not actors:
        return (
            "bypass_actors is empty, so applying this leaves no break-glass path and the "
            "owner cannot merge, push or delete the ruleset that is blocking them"
        )
    if OWNER_BYPASS not in actors:
        return (
            f"bypass_actors does not carry the owner's standing bypass {OWNER_BYPASS}; "
            f"it carries {actors}"
        )
    return None


def test_applying_the_committed_ruleset_would_not_lock_the_owner_out() -> None:
    """The whole point. This is the assertion the empty list has to fail."""
    risk = lockout_risk(load_ruleset())
    assert risk is None, (
        "applying .github/rulesets/main.json as committed would lock the repository owner "
        f"out: {risk}. See .github/rulesets/README.md, 'bypass_actors: the repository "
        "owner, and nobody else'."
    )


def test_the_owner_is_the_only_bypass_actor() -> None:
    """One actor. A second entry is a real finding; this one is not."""
    actors = load_ruleset()["bypass_actors"]
    assert actors == [OWNER_BYPASS], (
        "the owner's standing bypass is the only entry this file may carry, and a second "
        f"one is a widening of who can skip every rule: {actors}"
    )


@pytest.mark.parametrize(
    ("document", "expected"),
    [
        ({"bypass_actors": []}, "empty"),
        ({}, "no bypass_actors key"),
        ({"bypass_actors": {}}, "not a list"),
        (
            {
                "bypass_actors": [
                    {"actor_id": 1, "actor_type": "Integration", "bypass_mode": "always"}
                ]
            },
            "does not carry the owner",
        ),
        (
            {"bypass_actors": [dict(OWNER_BYPASS, bypass_mode="pull_request")]},
            "does not carry the owner",
        ),
    ],
    ids=["empty", "absent", "wrong-type", "wrong-actor", "wrong-mode"],
)
def test_the_lockout_check_rejects_the_documents_it_must_reject(
    document: dict[str, Any], expected: str
) -> None:
    """Five ways to lose the bypass, each of which GitHub answers with 201 like any other apply.

    The empty list is the one that was committed here. The rest are the shapes an edit to
    fix it could plausibly land in, `pull_request` included: it is what CICD-15 suggests and
    it is still a lockout on the day a required check is what wedged the pull request.
    """
    risk = lockout_risk(document)
    assert risk is not None, f"{document} should be refused"
    assert expected in risk


def test_the_lockout_check_accepts_the_shape_it_should() -> None:
    """A positive control, so the check above is not passing because it refuses everything."""
    assert lockout_risk({"bypass_actors": [OWNER_BYPASS]}) is None


def test_the_documentation_names_the_bypass_the_file_carries() -> None:
    """The README talks a reader through checking this before posting. It must name the same actor.

    The apply procedure is prose and prose drifts. If the file and the instructions for
    reading it disagree, the instructions are the ones a person follows.
    """
    doc = RULESET_DOC.read_text(encoding="utf-8")
    for fragment in ('"actor_id": 5', "RepositoryRole", "always"):
        assert fragment in doc, f"{RULESET_DOC} does not name {fragment!r}"
