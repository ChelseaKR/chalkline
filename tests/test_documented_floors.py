"""The tool floors the prose publishes are the floors ``pyproject.toml`` pins.

``tests/test_documented_counts.py`` binds every figure the README quotes about the graph, and
its ``_FIGURE_TOKEN`` docstring records that the lookarounds deliberately drop version strings,
dates and leaflet codes: none of those is a count of anything the build emits, and a regex over
counts has no business reading them. That exclusion is correct and is not touched here. What it
left behind is that tool floors became the one class of figure in the README that nothing
checked at all.

They had already drifted. The Code Quality row said "ruff >= 0.16.2, mypy >= 2.3.0" while
``pyproject.toml`` pinned ``ruff>=0.16.4`` and ``mypy>=2.3.1``. That is a drift with a motor
behind it rather than a one-off typo: Dependabot raises the floor in ``pyproject.toml``, the
merged PR touches no prose, and the sentence describing the pins falls one release further
behind every time a bump lands. Nothing in this module reads a count, so nothing in it loosens
that regex. The floors are read out of ``pyproject.toml`` and compared to the words.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

_REQUIREMENT = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)\s*(?P<floor>[<>=!~]=.*)$")

FLOORS_SENTENCE = re.compile(
    r"Floors are pinned in `pyproject\.toml`: "
    r"Python (>=\s*[0-9][0-9.]*), "
    r"ruff (>=\s*[0-9][0-9.]*), "
    r"mypy (>=\s*[0-9][0-9.]*), "
    r"complexity (<=\s*[0-9]+)\."
)
"""The one sentence in README.md that names the pinned floors, in the order it names them."""


def collapsed(name: str) -> str:
    """A document with its line breaks removed, so a wrapped sentence still reads as one."""
    return " ".join((REPO_ROOT / name).read_text(encoding="utf-8").split())


def pinned() -> tuple[str, ...]:
    """Python, ruff, mypy and complexity as ``pyproject.toml`` pins them, in that order."""
    config: dict[str, Any] = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    dev: dict[str, str] = {}
    for requirement in config["dependency-groups"]["dev"]:
        parsed = _REQUIREMENT.match(requirement)
        assert parsed is not None, f"cannot read a floor out of {requirement!r}"
        dev[parsed.group("name")] = parsed.group("floor")
    complexity = config["tool"]["ruff"]["lint"]["mccabe"]["max-complexity"]
    return (
        config["project"]["requires-python"],
        dev["ruff"],
        dev["mypy"],
        f"<={complexity}",
    )


def as_written(text: str) -> tuple[str, ...]:
    """The same four floors as that text states them, spaced the way ``pyproject.toml`` is."""
    stated = FLOORS_SENTENCE.search(text)
    assert stated is not None, (
        "README.md no longer states the pinned tool floors in the shape this check reads. "
        "The sentence is 'Floors are pinned in `pyproject.toml`: Python >= X, ruff >= Y, "
        "mypy >= Z, complexity <= N.' If it has been reworded, reword this pattern with it "
        "rather than deleting the claim."
    )
    return tuple(group.replace(" ", "") for group in stated.groups())


def test_the_code_quality_row_states_the_floors_pyproject_pins() -> None:
    assert as_written(collapsed("README.md")) == pinned(), (
        "README.md's Code Quality row publishes tool floors that pyproject.toml does not pin. "
        "A Dependabot bump raises the pin and leaves the prose alone, so this is what that "
        "looks like a release later."
    )


def test_the_coverage_floor_is_the_one_pyproject_enforces() -> None:
    """Every document that quotes the coverage floor quotes ``fail_under``.

    Three sentences state it: two rows of README.md's standards table and one line of
    CONTRIBUTING.md. The floor moved from 90 to 97 on 2026-08-28 and all three were edited by
    hand at the time; nothing would have caught the one that was missed.
    """
    config: dict[str, Any] = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    fail_under = config["tool"]["coverage"]["report"]["fail_under"]
    for name in ("README.md", "CONTRIBUTING.md"):
        stated = re.findall(r"([0-9]+)% coverage floor", collapsed(name))
        assert stated, f"{name} no longer states the coverage floor"
        assert {int(figure) for figure in stated} == {fail_under}, (
            f"{name} states a coverage floor of {sorted(set(stated))}; "
            f"pyproject.toml enforces fail_under = {fail_under}."
        )


@pytest.mark.parametrize(
    ("original", "doctored"),
    [
        ("ruff >= 0.16.4", "ruff >= 0.16.2"),
        ("mypy >= 2.3.1", "mypy >= 2.3.0"),
        ("Python >= 3.12", "Python >= 3.11"),
        ("complexity <= 10", "complexity <= 12"),
    ],
)
def test_a_doctored_floor_is_caught(original: str, doctored: str) -> None:
    """The control, in the shape ``test_documented_counts.py`` already uses for its figures.

    Each edit here is one the check above has to reject. The README on disk is not touched:
    the comparison is run over a doctored copy of its text, which is the only way to show that
    a passing run above is a statement about the floors and not about the check being unable
    to fail. The first two are exactly the values the row published before this was written.
    """
    text = collapsed("README.md")
    assert original in text, f"README.md no longer says {original!r}"
    assert as_written(text.replace(original, doctored)) != pinned(), (
        f"changing {original!r} to {doctored!r} left the floor check satisfied"
    )
