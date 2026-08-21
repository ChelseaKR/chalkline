"""Throwaway: deliberately fails `make verify` to test that the `protect-main` ruleset
(issue #22) actually blocks a merge with a red required check. Deleted before this branch
is closed without merging.
"""


def test_deliberately_fails() -> None:
    assert False, "deliberate failure to verify branch protection actually blocks a merge"  # noqa: B011,S101
