"""The dataset descriptor says only what the artifacts say, and says it once.

Three things this module is for.

*The descriptor is measured, not recorded.* Every size and every digest in it is taken from
the bytes of the file it describes, at the moment the file is produced. A test that only
checked the descriptor was well-formed would pass over one whose hashes were copied from a
previous build, which is the state a hand-maintained figure reaches within a week.

*The two vocabularies are one statement.* schema.org and DCAT are carried on the same node
rather than as two documents, so a harvester reading either comes away with the same
subject. The tests below assert that correspondence property by property, because "we
emitted both" is the kind of claim that stays true while the two drift apart.

*Nothing here is a wall clock.* ``dateModified`` is the Commission's retrieval date. A
descriptor that stamped the build time would report a change on every re-run of a
deterministic build, and a catalog would believe it.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

from chalkline import dataset
from chalkline.ctdl.export import (
    COVERAGE_FILENAME,
    DISCLAIMER,
    GRAPH_FILENAME,
    RESOURCE_BASE,
    serialize,
)
from chalkline.site import SITE_URL, TITLE, _dataset_block
from chalkline.sources.leaflets import SOURCE_URL as LEAFLET_INDEX_URL
from chalkline.sources.sort_table import SOURCE_URL as SORT_TABLE_URL

SITE = Path(__file__).resolve().parents[1] / "site"
PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

FIXTURE_ARTIFACTS = {
    GRAPH_FILENAME: '{"@graph": []}\n',
    COVERAGE_FILENAME: '{"entities": {}}\n',
    dataset.EVIDENCE_FILENAME: '{"findings": []}\n',
}


def build(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "site_url": "https://example.invalid/project/",
        "title": "A title",
        "artifacts": dict(FIXTURE_ARTIFACTS),
        "retrieved": "2026-08-07",
    }
    kwargs.update(overrides)
    return dataset.descriptor(**kwargs)


def distributions(document: dict[str, Any]) -> list[dict[str, Any]]:
    return list(document["schema:distribution"])


# --- what the descriptor measures ----------------------------------------------------


def test_every_digest_and_size_is_taken_from_the_bytes_it_describes() -> None:
    document = build()
    by_name = {node["schema:name"]: node for node in distributions(document)}
    for filename, text in FIXTURE_ARTIFACTS.items():
        node = by_name[dataset.ARTIFACT_TITLES[filename]]
        assert node["schema:sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert node["dcat:byteSize"] == len(text.encode("utf-8"))
        assert node["schema:contentSize"] == str(len(text.encode("utf-8")))
        assert node["spdx:checksum"]["spdx:checksumValue"] == node["schema:sha256"]
        assert node["spdx:checksum"]["spdx:algorithm"] == {"@id": dataset.SHA256_ALGORITHM}


def test_a_changed_artifact_changes_its_digest_and_nothing_else() -> None:
    """The control the issue asks for: edit one artifact, the hash test fails.

    Asserted as a *difference*, not merely as "not equal to a constant", so a descriptor
    that had stopped hashing at all, emitting a fixed placeholder for every file, would
    fail here rather than pass.
    """
    before = build()
    edited = dict(FIXTURE_ARTIFACTS)
    edited[COVERAGE_FILENAME] = '{"entities": {"ceterms:License": 1}}\n'
    after = build(artifacts=edited)

    changed = [
        (b["schema:name"], b["schema:sha256"] != a["schema:sha256"])
        for b, a in zip(distributions(before), distributions(after), strict=True)
    ]
    assert changed == [
        (dataset.ARTIFACT_TITLES[GRAPH_FILENAME], False),
        (dataset.ARTIFACT_TITLES[COVERAGE_FILENAME], True),
        (dataset.ARTIFACT_TITLES[dataset.EVIDENCE_FILENAME], False),
    ]


def test_the_modified_date_is_the_retrieval_date_and_carries_no_clock() -> None:
    document = build(retrieved="2026-08-07")
    assert document["schema:dateModified"] == "2026-08-07"
    assert document["dct:modified"] == "2026-08-07"
    # Nothing anywhere in the document may look like a timestamp: a build clock would
    # report a change on every re-run of a build that produced identical bytes.
    text = serialize(document)
    assert re.search(r"\d{4}-\d{2}-\d{2}T", text) is None, "the descriptor carries a timestamp"
    assert text.count("2026-08-07") == 2, "the retrieval date appears only as dateModified"


def test_two_builds_of_the_same_artifacts_are_byte_identical() -> None:
    assert serialize(build()) == serialize(build())


# --- absence must not be published as a smaller dataset -------------------------------


@pytest.mark.parametrize("missing", sorted(FIXTURE_ARTIFACTS))
def test_a_missing_artifact_stops_the_descriptor(missing: str) -> None:
    """Two downloads described where three are published is a smaller dataset asserted.

    It is the failure mode with no symptom: the document is well-formed, the digests it
    does carry are correct, and ``chalkline check`` holds it to a fresh build that also
    describes two.
    """
    partial = {k: v for k, v in FIXTURE_ARTIFACTS.items() if k != missing}
    with pytest.raises(ValueError, match=missing):
        build(artifacts=partial)


def test_an_empty_retrieval_date_stops_the_descriptor() -> None:
    with pytest.raises(ValueError, match="build clock"):
        build(retrieved="")


def test_the_cli_stops_when_the_evidence_report_is_absent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The third artifact is read from disk, so its absence has to stop the build."""
    from chalkline import cli

    monkeypatch.setattr(cli, "SITE_DIR", tmp_path)
    with pytest.raises(FileNotFoundError, match="dataset descriptor"):
        cli._evidence_text()


# --- one statement, two vocabularies --------------------------------------------------


def test_the_dataset_node_carries_both_vocabularies_for_every_claim() -> None:
    document = build()
    assert document["@type"] == ["schema:Dataset", "dcat:Dataset"]
    for schema_term, dcat_term in [
        ("schema:name", "dct:title"),
        ("schema:description", "dct:description"),
        ("schema:dateModified", "dct:modified"),
        ("schema:inLanguage", "dct:language"),
        ("schema:license", "dct:license"),
        ("schema:isBasedOn", "dct:source"),
        ("schema:keywords", "dcat:keyword"),
    ]:
        assert document[schema_term] == document[dcat_term], (
            f"{schema_term} and {dcat_term} describe the same dataset and have drifted"
        )


def test_both_distribution_properties_name_the_same_three_nodes() -> None:
    """DCAT reaches the distributions by reference, so there is one copy, not two."""
    document = build()
    inlined = [node["@id"] for node in document["schema:distribution"]]
    referenced = [node["@id"] for node in document["dcat:distribution"]]
    assert inlined == referenced
    assert all(set(node) == {"@id"} for node in document["dcat:distribution"]), (
        "a DCAT distribution is a reference to the node above it, not a second copy"
    )


def test_every_distribution_is_typed_for_both_vocabularies() -> None:
    for node in distributions(build()):
        assert node["@type"] == ["schema:DataDownload", "dcat:Distribution"]
        assert node["schema:contentUrl"] == node["@id"]
        assert node["dcat:downloadURL"] == {"@id": node["@id"]}
        assert node["schema:encodingFormat"] == node["dcat:mediaType"]


# --- what the descriptor may and may not claim ----------------------------------------


def test_the_description_is_the_unofficial_notice_in_full() -> None:
    """A catalog card is where a stranger meets this project with no page around it."""
    document = build()
    assert document["schema:description"] == DISCLAIMER
    assert "not published by, affiliated with, or endorsed by" in document["schema:description"]
    assert "Nothing here has been published to the Credential Registry" in DISCLAIMER


def test_the_descriptor_never_names_the_ctdl_resource_namespace() -> None:
    """ADR 0004's `@id` decision is untouched by describing where a file downloads from.

    The identifiers here are the served page and the files beside it, which `index.html`
    already publishes as `canonical` and `og:url`.
    """
    text = serialize(build(site_url=SITE_URL))
    assert RESOURCE_BASE not in text
    assert "credentialengineregistry.org" not in text


def test_the_declared_licence_is_the_licence_the_repository_carries() -> None:
    declared = PYPROJECT.read_text(encoding="utf-8")
    assert 'license = "Apache-2.0"' in declared
    assert dataset.LICENSE_URL == "https://www.apache.org/licenses/LICENSE-2.0"
    assert build()["schema:license"] == {"@id": dataset.LICENSE_URL}


def test_the_sources_are_the_two_commission_pages_this_project_reads() -> None:
    document = build()
    assert document["schema:isBasedOn"] == [
        {"@id": SORT_TABLE_URL},
        {"@id": LEAFLET_INDEX_URL},
    ]


def test_the_descriptor_states_no_count() -> None:
    """Counts live in `coverage.json`, counted from the graph, and nowhere else.

    A third copy that nothing derives is a figure that goes stale silently, which is the
    reasoning `site.DESCRIPTION` already records for the page's own prose.
    """
    numeric: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")
        elif isinstance(node, bool | int | float):
            numeric.append(path)

    walk(build(), "")
    assert numeric == [
        ".schema:distribution[0].dcat:byteSize",
        ".schema:distribution[1].dcat:byteSize",
        ".schema:distribution[2].dcat:byteSize",
    ], f"the descriptor carries a number that is not a byte size: {numeric}"


def test_the_context_is_declared_in_full_and_fetches_nothing() -> None:
    document = build()
    assert document["@context"] == dataset.CONTEXT
    assert all(isinstance(value, str) for value in document["@context"].values())
    for prefix in ("schema", "dcat", "dct", "spdx"):
        assert prefix in document["@context"]


# --- the committed artifacts ----------------------------------------------------------


def test_the_committed_descriptor_describes_the_committed_artifacts() -> None:
    document = json.loads((SITE / dataset.DATASET_FILENAME).read_text(encoding="utf-8"))
    for node in document["schema:distribution"]:
        filename = node["@id"].removeprefix(SITE_URL)
        published = (SITE / filename).read_bytes()
        assert node["schema:sha256"] == hashlib.sha256(published).hexdigest(), (
            f"the descriptor's digest for {filename} is not the committed file's"
        )
        assert node["dcat:byteSize"] == len(published)


def test_the_committed_descriptor_covers_every_download_the_site_publishes() -> None:
    """The denominator, so a descriptor that lost a distribution is visible."""
    document = json.loads((SITE / dataset.DATASET_FILENAME).read_text(encoding="utf-8"))
    described = {node["@id"].removeprefix(SITE_URL) for node in document["schema:distribution"]}
    assert described == set(dataset.DESCRIBED_ARTIFACTS)
    assert len(document["schema:distribution"]) == 3


def test_the_committed_descriptor_dates_from_the_coverage_statement() -> None:
    document = json.loads((SITE / dataset.DATASET_FILENAME).read_text(encoding="utf-8"))
    statement = json.loads((SITE / COVERAGE_FILENAME).read_text(encoding="utf-8"))
    assert document["schema:dateModified"] == statement["source"]["retrieved"]


def test_the_committed_page_embeds_the_committed_descriptor_verbatim() -> None:
    """One statement. The page a harvester reads and the file a catalog fetches are one file."""
    descriptor_text = (SITE / dataset.DATASET_FILENAME).read_text(encoding="utf-8")
    page = (SITE / "index.html").read_text(encoding="utf-8")
    assert _dataset_block(descriptor_text) in page, (
        "site/index.html does not carry site/dataset.jsonld byte for byte"
    )


def test_the_committed_descriptor_names_this_project_and_this_site() -> None:
    document = json.loads((SITE / dataset.DATASET_FILENAME).read_text(encoding="utf-8"))
    assert document["schema:name"] == TITLE
    assert document["schema:url"] == SITE_URL
    assert document["@id"] == f"{SITE_URL}#dataset"


# --- the embed cannot be broken by its own content ------------------------------------


def test_a_descriptor_containing_a_left_angle_bracket_is_refused() -> None:
    """`</script` ends a data block and no escaping inside one can prevent it.

    So the guard is on the character, not on the sequence: a `<` in the descriptor means
    something arrived that this reasoning has not been re-checked against.
    """
    with pytest.raises(ValueError, match="cannot be escaped"):
        _dataset_block('{"a": "</script>"}')
    with pytest.raises(ValueError, match="cannot be escaped"):
        _dataset_block('{"a": "1 < 2"}')


def test_the_real_descriptor_contains_no_left_angle_bracket() -> None:
    assert "<" not in serialize(build(site_url=SITE_URL))
