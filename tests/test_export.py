"""The projection says what the source says, and the coverage statement counts the result."""

from __future__ import annotations

import pytest

from chalkline import ctid as ctid_module
from chalkline.ctdl import export, validate
from chalkline.model import Catalog, build_catalog
from chalkline.sources import leaflets as leaflets_module
from chalkline.sources import sort_table
from tests.conftest import row, table

CTIDS = ctid_module.load_ledger()


@pytest.fixture(scope="module")
def document(real_catalog: Catalog) -> dict[str, object]:
    index = leaflets_module.index_by_title(leaflets_module.load())
    return export.project_graph(real_catalog, CTIDS, index)


def licenses(document: dict[str, object]) -> list[dict[str, object]]:
    graph: list[dict[str, object]] = document["@graph"]  # type: ignore[assignment]
    return [e for e in graph if e.get("@type") == "ceterms:License"]


def test_the_real_export_validates_against_the_published_schema(
    document: dict[str, object],
) -> None:
    assert validate.validate(document) == []


def test_one_license_per_modeled_authorization(
    document: dict[str, object], real_catalog: Catalog
) -> None:
    assert len(licenses(document)) == len(real_catalog.authorizations)


def test_excluded_authorizations_are_absent_from_the_graph(
    document: dict[str, object], real_catalog: Catalog
) -> None:
    names = {e["ceterms:name"][export.LANG] for e in licenses(document)}  # type: ignore[index]
    modeled = {a.title for a in real_catalog.authorizations}
    for exclusion in real_catalog.exclusions:
        if exclusion.title not in modeled:
            assert exclusion.title not in names


def test_the_organization_appears_once_and_is_referenced_by_every_license(
    document: dict[str, object],
) -> None:
    graph: list[dict[str, object]] = document["@graph"]  # type: ignore[assignment]
    organizations = [e for e in graph if e.get("@type") == "ceterms:CredentialOrganization"]
    assert len(organizations) == 1
    iri = organizations[0]["@id"]
    assert all(entity["ceterms:ownedBy"] == [iri] for entity in licenses(document))


def test_every_license_carries_a_ledger_ctid(document: dict[str, object]) -> None:
    minted = set(CTIDS.values())
    for entity in licenses(document):
        value = entity["ceterms:ctid"]
        assert ctid_module.is_ctid(str(value))
        assert value in minted
        assert entity["@id"] == export.RESOURCE_BASE + str(value)


def test_ids_do_not_pretend_to_live_in_the_registry(document: dict[str, object]) -> None:
    graph: list[dict[str, object]] = document["@graph"]  # type: ignore[assignment]
    assert all("credentialengineregistry.org" not in str(e.get("@id", "")) for e in graph)


def test_the_document_carries_the_unofficial_statement(document: dict[str, object]) -> None:
    assert "not published by, affiliated with, or endorsed by" in str(document["comment"])
    assert str(document["comment"]).startswith(export.DISCLAIMER_LEAD)
    assert document["@context"] == export.CTDL_CONTEXT_URL


def test_description_only_where_the_commission_wrote_prose() -> None:
    catalog = build_catalog(
        sort_table.parse(
            table(
                row(subject_code="ART", subject="Art", notes=("Academic Subject",)),
                row(subject_code="MUS", subject="Music", notes=("Academic Subject",)),
            )
        )
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", "https://e/")
    assert entity["ceterms:description"] == {export.LANG: "Academic Subject"}

    quiet = build_catalog(sort_table.parse(table(row(subject_code="ART", subject="Art"))))
    bare = export.project_license(quiet.authorizations[0], "ce-x", "urn:org", "https://e/")
    assert "ceterms:description" not in bare


def test_no_subject_property_when_the_commission_published_none() -> None:
    catalog = build_catalog(sort_table.parse(table(row(subject_code="NONE", subject=""))))
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", "https://e/")
    assert "ceterms:subject" not in entity


def test_subject_alignments_carry_the_code_name_and_row_notes() -> None:
    catalog = build_catalog(
        sort_table.parse(table(row(subject_code="ART", subject="Art", notes=("Academic",))))
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", "https://e/")
    (alignment,) = entity["ceterms:subject"]
    assert alignment["ceterms:codedNotation"] == "ART"
    assert alignment["ceterms:targetNodeName"] == {export.LANG: "Art"}
    assert alignment["ceterms:targetNodeDescription"] == {export.LANG: "Academic"}
    assert alignment["ceterms:framework"] == sort_table.SOURCE_URL


def test_multiple_is_not_emitted_as_a_document_code() -> None:
    catalog = build_catalog(
        sort_table.parse(
            table(row(document="Multiple", code="BASP", subject_code="NONE", subject=""))
        )
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", "https://e/")
    codes = [v["ceterms:identifierValueCode"] for v in entity["ceterms:identifier"]]
    assert codes == ["BASP"]


def test_comma_separated_codes_become_separate_identifiers() -> None:
    catalog = build_catalog(
        sort_table.parse(
            table(row(document="TC1, TC2", code="R1S, R1F", subject_code="NONE", subject=""))
        )
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", "https://e/")
    codes = [v["ceterms:identifierValueCode"] for v in entity["ceterms:identifier"]]
    assert codes == ["TC1", "TC2", "R1S", "R1F"]


def test_a_leaflet_is_used_only_on_an_exact_title_match(real_catalog: Catalog) -> None:
    leaflet = leaflets_module.Leaflet(
        code="cl-380", title="School Nurse Services Credential", url="https://example.gov/380"
    )
    index = {leaflets_module.normalize_title(leaflet.title): leaflet}
    matched = [
        a for a in real_catalog.authorizations if a.title == "School Nurse Services Credential"
    ]
    assert matched, "the vendored table should hold this authorization"
    webpage, used = export.webpage_for(matched[0], index)
    assert webpage == leaflet.url
    assert used == leaflet

    other = next(a for a in real_catalog.authorizations if a.title != leaflet.title)
    fallback, none_used = export.webpage_for(other, index)
    assert fallback == sort_table.SOURCE_URL
    assert none_used is None


def test_export_refuses_to_mint_a_missing_ctid(real_catalog: Catalog) -> None:
    with pytest.raises(KeyError, match="mint-ctids"):
        export.project_graph(real_catalog, {}, {})


def test_coverage_is_counted_from_the_graph(
    document: dict[str, object], real_catalog: Catalog, leaflet_index: dict[str, object]
) -> None:
    statement = export.coverage(document, real_catalog, leaflet_index)  # type: ignore[arg-type]
    assert statement["entities"]["ceterms:License"] == len(licenses(document))
    assert statement["authorizations"]["modeled"] == len(real_catalog.authorizations)
    assert statement["authorizations"]["excluded"] == len(real_catalog.exclusions)
    assert statement["authorizations"]["published_in_source"] == len(
        real_catalog.authorizations
    ) + len(real_catalog.exclusions)
    assert sum(statement["excluded_by_reason"].values()) == len(real_catalog.exclusions)


def test_a_coverage_statement_the_export_contradicts_is_refused(
    document: dict[str, object], real_catalog: Catalog, leaflet_index: dict[str, object]
) -> None:
    statement = export.coverage(document, real_catalog, leaflet_index)  # type: ignore[arg-type]
    statement["entities"] = {"ceterms:License": 1}
    problems = export.coverage_problems(statement, document, real_catalog, leaflet_index)  # type: ignore[arg-type]
    assert problems
    with pytest.raises(ValueError, match="does not describe the export"):
        export.check_coverage(statement, document, real_catalog, leaflet_index)  # type: ignore[arg-type]


def test_projection_is_byte_for_byte_deterministic(real_catalog: Catalog) -> None:
    index = leaflets_module.index_by_title(leaflets_module.load())
    first = export.serialize(export.project_graph(real_catalog, CTIDS, index))
    second = export.serialize(export.project_graph(real_catalog, CTIDS, index))
    assert first == second


def test_write_produces_both_files(real_catalog: Catalog, tmp_path: object) -> None:
    from pathlib import Path

    assert isinstance(tmp_path, Path)
    report = export.write(real_catalog, CTIDS, leaflets_module.load(), tmp_path)
    assert report.document_path.exists()
    assert report.coverage_path.exists()
    assert report.licenses == len(real_catalog.authorizations)
    assert report.excluded == len(real_catalog.exclusions)
    assert report.alignments == sum(len(a.subjects) for a in real_catalog.authorizations)


def test_an_authorization_with_no_codes_at_all_emits_no_identifier() -> None:
    """Nothing is fabricated to fill the property: no code published, no identifier."""
    catalog = build_catalog(
        sort_table.parse(table(row(document="Multiple", code="", subject_code="NONE", subject="")))
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", "https://e/")
    assert "ceterms:identifier" not in entity
