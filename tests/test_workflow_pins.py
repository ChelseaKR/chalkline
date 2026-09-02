"""One action, one pin, across every workflow file.

SECURITY-AND-SUPPLY-CHAIN-STANDARD §6 asks for actions pinned to a full 40-character commit
SHA, and `.github/workflows/ci.yml`'s header records that they are, with the tag kept beside
each pin as a comment so a reader can see the version. Nothing checked that two workflows
pinning the same action agreed.

They did not. Dependabot's PR #34 raised `astral-sh/setup-uv` from v9.0.0 to v10.0.1 across
`ci.yml` and `pages.yml`; `live-integrity.yml` was written after that PR was opened and so
was created against v9.0.0, and merging #34 left the repository running two majors of the
same action. That is a real hazard for this repository in particular: the sentinel exists to
say whether the served site disagrees with the build, and an answer produced by a different
uv setup than CI used is worth less than it looks.

The check is a pure function of the parsed workflow text, run against inputs it must reject
as well as against the tree, and it fails on a missing or empty workflow directory rather
than reporting nothing wrong about a set it never read.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Final

import pytest

WORKFLOWS: Final = Path(__file__).resolve().parents[1] / ".github" / "workflows"

_USES: Final = re.compile(
    r"^\s*(?:-\s+)?uses:\s*(?P<action>[^@\s]+)@(?P<pin>[0-9a-f]{40})\s*(?:#\s*(?P<tag>\S+))?\s*$",
    re.MULTILINE,
)
"""One SHA-pinned ``uses:`` line, and the tag comment beside it.

Only full 40-character SHAs match. A `uses:` line pinned to a tag or a branch is not a
different pin of the same action, it is an unpinned action, and
:func:`test_every_action_is_pinned_to_a_sha` is what fails on it.
"""

_ANY_USES: Final = re.compile(r"^\s*(?:-\s+)?uses:\s*(?P<ref>\S+)", re.MULTILINE)


def pins(documents: dict[str, str]) -> dict[str, dict[str, set[str]]]:
    """Every SHA-pinned action, mapped to each pin it carries and the files carrying it."""
    found: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for name, text in documents.items():
        for use in _USES.finditer(text):
            found[use.group("action")][f"{use.group('pin')} ({use.group('tag')})"].add(name)
    return {action: dict(by_pin) for action, by_pin in found.items()}


def disagreements(documents: dict[str, str]) -> dict[str, dict[str, set[str]]]:
    """The actions pinned two different ways, or ``{}`` if every action agrees with itself."""
    return {action: by_pin for action, by_pin in pins(documents).items() if len(by_pin) > 1}


def workflows() -> dict[str, str]:
    """Every workflow file's text, or a failure. Never a silent empty set."""
    if not WORKFLOWS.is_dir():
        pytest.fail(f"{WORKFLOWS} is missing; the workflows are what this checks")
    documents = {path.name: path.read_text(encoding="utf-8") for path in WORKFLOWS.glob("*.yml")}
    if not documents:
        pytest.fail(f"{WORKFLOWS} holds no workflow files, so this check read nothing")
    return documents


def test_no_action_is_pinned_two_different_ways() -> None:
    """The assertion the two setup-uv majors had to fail."""
    found = disagreements(workflows())
    assert found == {}, (
        "these actions are pinned to more than one commit across the workflow files, so two "
        f"jobs in this repository run different versions of the same step: {found}"
    )


def test_the_check_reads_more_than_one_workflow_and_more_than_one_action() -> None:
    """A denominator, so a pass is about the workflows rather than about an empty scan."""
    documents = workflows()
    found = pins(documents)
    assert len(documents) >= 4, f"only {len(documents)} workflow files were read"
    assert len(found) >= 4, f"only {len(found)} pinned actions were found"
    shared = [action for action, by_pin in found.items() if len(next(iter(by_pin.values()))) > 1]
    assert shared, (
        "no action appears in two workflow files, so the check above cannot have anything to "
        "disagree about and is passing vacuously"
    )


def test_every_action_is_pinned_to_a_sha() -> None:
    """A tag-pinned action would be invisible to the check above, so it fails here instead."""
    unpinned = {
        f"{name}: {use.group('ref')}"
        for name, text in workflows().items()
        for use in _ANY_USES.finditer(text)
        if not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", use.group("ref"))
    }
    assert unpinned == set(), (
        f"these actions are not pinned to a full commit SHA: {sorted(unpinned)}. "
        "SECURITY-AND-SUPPLY-CHAIN-STANDARD §6."
    )


DISAGREEING: dict[str, str] = {
    "a.yml": "jobs:\n  x:\n    steps:\n      - uses: acme/setup@" + "a" * 40 + " # v9.0.0\n",
    "b.yml": "jobs:\n  y:\n    steps:\n      - uses: acme/setup@" + "b" * 40 + " # v10.0.1\n",
}
"""The shape the repository was in between #34 and this file: one action, two majors."""

AGREEING: dict[str, str] = {
    "a.yml": "jobs:\n  x:\n    steps:\n      - uses: acme/setup@" + "a" * 40 + " # v9.0.0\n",
    "b.yml": "jobs:\n  y:\n    steps:\n      - uses: acme/setup@" + "a" * 40 + " # v9.0.0\n",
}


def test_the_disagreement_check_rejects_the_document_it_must_reject() -> None:
    found = disagreements(DISAGREEING)
    assert list(found) == ["acme/setup"]
    assert len(found["acme/setup"]) == 2


def test_the_disagreement_check_accepts_agreeing_pins() -> None:
    """A positive control, so the check is not passing because it refuses everything."""
    assert disagreements(AGREEING) == {}
    assert list(pins(AGREEING)) == ["acme/setup"]
