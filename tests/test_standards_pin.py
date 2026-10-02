"""The portfolio standards pin, checked the same way `chalkline check` checks everything else.

DOCUMENTATION-STANDARD.md §1.1 (DOC-01): "The workflow `ref:` (CI-fetch) or
`.standards-version` (vendored) names a released tag, never a branch." This project vendors
rather than CI-fetches (its own gates are already offline by design; adding a private deploy
key to a *public* repository's CI to fetch another private repository is a real supply-chain
surface this project would rather not open for a pin that a plain text file already states).

DOC-01's own "measured by" column reads "CI asserts the recorded ref matches a
`vMAJOR.MINOR.PATCH` tag and is not `main`/a `heads/` ref". This test is that assertion: it
is a shape check against the committed file, on purpose. Confirming the tag is *real* --
that `v3.0.1` actually exists in ChelseaKR/portfolio-standards -- would mean a network call,
which is the one thing this project has held every other check to not needing. That
confirmation is done by hand each time the pin moves: for `v3.0.1`, on 2026-10-02, the tag
was confirmed as a signed annotated tag with an immutable GitHub Release whose archive matches
its `SHA256SUMS` entry. DOC-02 (staying current) is a portfolio-wide job, not this
repository's own gate.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = REPO_ROOT / ".standards-version"

RELEASED_TAG = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+$")


def test_standards_pin_file_exists() -> None:
    assert PIN_PATH.exists(), f"{PIN_PATH} is missing; DOC-01 requires a vendored pin"


def test_standards_pin_names_a_released_tag_not_a_branch() -> None:
    pin = PIN_PATH.read_text(encoding="utf-8").strip()
    assert RELEASED_TAG.match(pin), (
        f".standards-version holds {pin!r}, which is not a `vMAJOR.MINOR.PATCH` tag. "
        "DOC-01 requires a released tag, never `main` or a `heads/` ref."
    )
    assert pin not in {"main", "master"}
    assert not pin.startswith("heads/")
