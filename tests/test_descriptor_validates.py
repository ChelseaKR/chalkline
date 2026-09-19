"""The dataset descriptor is valid against the specifications it names, and the check can fail.

``scripts/validate_descriptor.py`` reads ``site/dataset.jsonld`` and the copy embedded in
``site/index.html`` as a JSON-LD consumer does, with ``rdflib``, and checks them against the
vendored schema.org, DCAT 3, DCMI Metadata Terms and SPDX 2.3 vocabularies (CQ-49: generated
output validated against its published spec, not against this project's own tests of it).

A validator that has never been seen to fail cannot be told apart from one that returns an
empty list, so every rule it enforces has a negative control below: a single mutation of the
real descriptor, asserted to have landed, that the rule has to report by name.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "validate_descriptor.py"
MAKEFILE = REPO_ROOT / "Makefile"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("chalkline_validate_descriptor", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before it runs: a dataclass resolves its annotations through sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load()


@pytest.fixture(scope="module")
def published() -> str:
    return str(validator.DESCRIPTOR_PATH.read_text(encoding="utf-8"))


def test_the_published_descriptor_is_valid(published: str) -> None:
    assert validator.validate(published) == []


def test_the_copy_a_harvester_reads_from_the_page_is_valid() -> None:
    page = validator.PAGE_PATH.read_text(encoding="utf-8")
    blocks = validator.embedded(page)
    assert len(blocks) == 1, "the page should carry exactly one data block"
    assert validator.validate(blocks[0]) == []


def test_the_script_passes_and_says_what_it_checked(capsys: pytest.CaptureFixture[str]) -> None:
    assert validator.main() == 0
    out = capsys.readouterr().out
    assert "0 findings" in out
    for name in ("schema.org 30.1", "DCAT 3", "DCMI Metadata Terms", "SPDX 2.3"):
        assert name in out


def test_the_vocabularies_are_the_whole_published_ones() -> None:
    """A truncated or emptied vendored file would make every term look undefined, or none.

    The floors are at or under today's counts (schema.org 30.1 defines 946 classes and 1,538
    properties; DCAT 3 defines nine classes of its own) and far above anything a partial
    file would hold.
    """
    counts = {}
    for vocabulary in validator.vocabularies():
        subjects = set(vocabulary.graph.subjects())
        in_namespace = [s for s in subjects if str(s).startswith(vocabulary.namespace)]
        counts[vocabulary.name] = (
            sum(vocabulary.is_class(s) for s in in_namespace),
            sum(vocabulary.is_property(s) for s in in_namespace),
        )
    assert counts["schema.org 30.1"][0] > 800 and counts["schema.org 30.1"][1] > 1_400
    assert counts["DCAT 3"][0] >= 9 and counts["DCAT 3"][1] >= 30
    assert counts["DCMI Metadata Terms"][1] >= 50
    assert counts["SPDX 2.3"][0] >= 20 and counts["SPDX 2.3"][1] >= 50


def test_make_verify_runs_the_validator() -> None:
    """CI runs `make verify` byte for byte, so this is what puts the validator in CI."""
    text = MAKEFILE.read_text(encoding="utf-8")
    verify = re.search(r"^verify:(.*)$", text, re.MULTILINE)
    assert verify is not None and "validate-dataset" in verify.group(1).split()
    assert "scripts/validate_descriptor.py" in text


# --- negative controls -------------------------------------------------------------------

Mutation = Callable[[dict[str, Any]], None]


def _first_distribution(document: dict[str, Any]) -> dict[str, Any]:
    node: dict[str, Any] = document["schema:distribution"][0]
    return node


def _rename(node: dict[str, Any], old: str, new: str) -> None:
    node[new] = node.pop(old)


CONTROLS: list[tuple[str, Mutation, str]] = [
    (
        "a misspelled schema.org property",
        lambda d: _rename(d, "schema:name", "schema:nmae"),
        "schema:nmae is not a property in schema.org 30.1",
    ),
    (
        "a misspelled DCAT property",
        lambda d: _rename(_first_distribution(d), "dcat:downloadURL", "dcat:downloadUrl"),
        "dcat:downloadUrl is not a property in DCAT 3",
    ),
    (
        "a misspelled schema.org class",
        lambda d: d.__setitem__("@type", ["schema:DataSet", "dcat:Dataset"]),
        "schema:DataSet is not a class in schema.org 30.1",
    ),
    (
        "a term with an undeclared prefix, which JSON-LD drops silently",
        lambda d: d.__setitem__("foaf:page", "https://example.org/"),
        "'foaf:page' expands to no IRI",
    ),
    (
        "a bare word, which JSON-LD drops silently",
        lambda d: d.__setitem__("name", "Chalkline"),
        "'name' expands to no IRI",
    ),
    (
        "an absolute IRI from no vendored vocabulary",
        lambda d: d.__setitem__("https://example.org/ns#rating", "5"),
        "is in none of the vendored vocabularies",
    ),
    (
        "a schema.org property outside its domain",
        lambda d: d.__setitem__("schema:contentUrl", "https://example.org/x"),
        "schema:contentUrl on https://chelseakr.github.io/chalkline/#dataset: the subject's "
        "types are not in its domain",
    ),
    (
        "a schema.org date that is not a date",
        lambda d: d.__setitem__("schema:dateModified", "last week"),
        "last week is not in its range",
    ),
    (
        "a schema.org property given text where only a node is admitted",
        lambda d: d.__setitem__("schema:distribution", ["the graph"]),
        "the graph is not in its range (schema:DataDownload)",
    ),
    (
        "a DCAT class-valued property given a literal",
        lambda d: _first_distribution(d).__setitem__("dcat:mediaType", "application/ld+json"),
        "its range is dct:MediaType, a class, and application/ld+json is a literal",
    ),
    (
        "a literal-valued property given a resource",
        lambda d: d.__setitem__("dct:title", {"@id": "https://example.org/title"}),
        "its range is rdfs:Literal, a literal, not https://example.org/title",
    ),
    (
        "a DCAT property on the wrong kind of node",
        lambda d: d.__setitem__("dcat:byteSize", 1),
        "the subject is not a dcat:Distribution",
    ),
    (
        "an SPDX individual that does not exist",
        lambda d: _first_distribution(d)["spdx:checksum"].__setitem__(
            "spdx:algorithm", {"@id": "spdx:checksumAlgorithm_sha257"}
        ),
        "spdx:checksumAlgorithm_sha257 is not defined in SPDX 2.3",
    ),
    (
        "a remote context, which would have to be fetched",
        lambda d: d.__setitem__("@context", "https://schema.org/"),
        "@context is not an inline map",
    ),
    (
        "a dataset node with no identifier",
        lambda d: d.pop("@id"),
        "expected one identified schema:Dataset node",
    ),
]


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [(mutation, expected) for _, mutation, expected in CONTROLS],
    ids=[name for name, _, _ in CONTROLS],
)
def test_each_rule_catches_its_breakage(published: str, mutation: Mutation, expected: str) -> None:
    document = json.loads(published)
    broken = copy.deepcopy(document)
    mutation(broken)
    assert broken != document, "the mutation did not land, so this control checks nothing"
    findings = validator.validate(json.dumps(broken, indent=2))
    assert any(expected in finding for finding in findings), (
        f"expected a finding containing {expected!r}, got {findings}"
    )


def test_the_statement_count_catches_what_a_processor_drops(published: str) -> None:
    """The backstop under the per-term check: JSON-LD drops a term it cannot expand silently.

    Asserted directly, because the per-term check also fires on the same mutation and would
    otherwise hide whether this one can.
    """
    document = json.loads(published)
    document["name"] = "Chalkline"
    findings = validator.validate(json.dumps(document))
    assert any("a JSON-LD processor read" in finding for finding in findings), findings


def test_the_script_fails_on_a_broken_descriptor(
    published: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exit code, not only the list: `make verify` reads the process status."""
    document = json.loads(published)
    _rename(document, "schema:name", "schema:nmae")
    broken = tmp_path / "dataset.jsonld"
    broken.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(validator, "DESCRIPTOR_PATH", broken)
    assert validator.main() == 1
