"""CTIDs follow the published grammar, and stability comes from the ledger.

The point of these tests is the deviation this project does *not* take: identifiers are real
UUIDv4s, so two mints of the same key differ, and only the committed ledger makes a re-export
reproduce itself.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chalkline import ctid
from chalkline.ctdl.export import ORGANIZATION_KEY
from chalkline.model import Catalog


def test_minted_ctids_match_the_published_grammar() -> None:
    for _ in range(50):
        value = ctid.mint()
        assert ctid.is_ctid(value)
        assert len(value) == 39
        assert value.startswith("ce-")


def test_grammar_rejects_the_shapes_that_go_wrong_in_practice() -> None:
    assert not ctid.is_ctid("b55f88e3-dfd4-430b-ab47-3e5f9986e1e4")  # bare UUID, no ce-
    assert not ctid.is_ctid("ce-B55F88E3-DFD4-430B-AB47-3E5F9986E1E4")  # upper case
    assert not ctid.is_ctid("ce-b55f88e3-dfd4-530b-ab47-3e5f9986e1e4")  # version 5
    assert not ctid.is_ctid("ce-b55f88e3-dfd4-430b-cb47-3e5f9986e1e4")  # bad variant bits
    assert not ctid.is_ctid("ce-b55f88e3dfd4430bab473e5f9986e1e4")  # no hyphens


def test_minting_is_random_which_is_what_v4_means() -> None:
    assert ctid.mint() != ctid.mint()


def test_ledger_round_trips_and_sorts(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    ctid.save_ledger({"b": ctid.mint(), "a": ctid.mint()}, path)
    document = json.loads(path.read_text(encoding="utf-8"))
    assert list(document["ctids"]) == ["a", "b"]
    assert document["note"] == ctid.LEDGER_NOTE
    assert set(ctid.load_ledger(path)) == {"a", "b"}


def test_missing_ledger_reads_as_empty(tmp_path: Path) -> None:
    assert ctid.load_ledger(tmp_path / "absent.json") == {}


def test_a_malformed_ledger_entry_stops_everything(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps({"ctids": {"a": "not-a-ctid"}}), encoding="utf-8")
    with pytest.raises(ValueError, match="not CTIDs"):
        ctid.load_ledger(path)


def test_a_reused_ctid_stops_everything(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    value = ctid.mint()
    path.write_text(json.dumps({"ctids": {"a": value, "b": value}}), encoding="utf-8")
    with pytest.raises(ValueError, match="same CTID"):
        ctid.load_ledger(path)


def test_mint_missing_never_reassigns_an_existing_key() -> None:
    existing = {"a": ctid.mint()}
    updated, minted = ctid.mint_missing(["a", "b"], existing)
    assert minted == 1
    assert updated["a"] == existing["a"]
    assert ctid.is_ctid(updated["b"])


def test_require_refuses_to_invent_and_names_the_fix() -> None:
    with pytest.raises(KeyError, match="mint-ctids"):
        ctid.require("absent", {})


def test_the_committed_ledger_is_well_formed() -> None:
    ledger = ctid.load_ledger()
    assert ledger, "the committed ledger should not be empty"
    assert all(ctid.is_ctid(value) for value in ledger.values())
    assert len(set(ledger.values())) == len(ledger)


def test_the_committed_ledger_covers_every_modeled_authorization(real_catalog: Catalog) -> None:
    ledger = ctid.load_ledger()
    assert ORGANIZATION_KEY in ledger
    missing = [a.key for a in real_catalog.authorizations if a.key not in ledger]
    assert missing == []
