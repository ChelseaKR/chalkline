"""The CLI builds, checks, and mints, and check is what keeps the committed output honest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chalkline import cli
from chalkline import ctid as ctid_module


def test_build_writes_three_files(tmp_path: Path) -> None:
    assert cli.build(tmp_path) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "coverage.json",
        "credentials.jsonld",
        "index.html",
    ]


def test_the_committed_site_matches_a_fresh_build(capsys: pytest.CaptureFixture[str]) -> None:
    """The repository's published artifacts are what this code produces, right now."""
    assert cli.check(cli.SITE_DIR) == 0
    assert "matches a fresh build" in capsys.readouterr().out


def test_check_fails_when_output_is_missing(tmp_path: Path) -> None:
    assert cli.check(tmp_path) == 1


def test_check_fails_when_output_is_stale(tmp_path: Path) -> None:
    cli.build(tmp_path)
    (tmp_path / "coverage.json").write_text("{}", encoding="utf-8")
    assert cli.check(tmp_path) == 1


def test_mint_is_a_no_op_once_the_ledger_is_complete(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Against a copy, because a minting test must never write to the committed ledger.

    This used to pass ``None``, which resolves to ``data/ctid-ledger.json`` and saves in
    place. It was a no-op only while the ledger was already complete: with one key missing,
    running pytest minted a fresh UUIDv4 into a tracked artifact and left it modified in the
    working tree, which is precisely what ``chalkline.ctid`` says can never happen as a side
    effect. The assertion is the same; it just no longer has the repository as its subject.
    """
    committed = ctid_module.LEDGER_PATH.read_text(encoding="utf-8")
    ledger = tmp_path / "ledger.json"
    ledger.write_text(committed, encoding="utf-8")

    assert cli.mint_ctids(ledger) == 0
    assert "minted 0 this run" in capsys.readouterr().out
    assert ledger.read_text(encoding="utf-8") == committed


def test_the_committed_ledger_covers_every_key_the_export_requires() -> None:
    """What the test above was really asserting, said directly and without writing anything."""
    from chalkline.ctdl.export import ORGANIZATION_KEY

    catalog = cli._catalog()
    required = {ORGANIZATION_KEY, *(a.key for a in catalog.authorizations)}
    assert required, "the catalog should require at least one CTID"
    assert required - set(ctid_module.load_ledger()) == set()


def test_mint_fills_an_empty_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    assert cli.mint_ctids(ledger) == 0
    minted = json.loads(ledger.read_text(encoding="utf-8"))["ctids"]
    assert len(minted) > 1
    assert ctid_module.load_ledger(ledger) == minted


def test_main_dispatches_each_verb(tmp_path: Path) -> None:
    assert cli.main(["build", "--output-dir", str(tmp_path)]) == 0
    assert cli.main(["check", "--output-dir", str(tmp_path)]) == 0
    assert cli.main(["mint-ctids", "--ledger", str(tmp_path / "l.json")]) == 0


def test_main_requires_a_verb() -> None:
    with pytest.raises(SystemExit):
        cli.main([])
