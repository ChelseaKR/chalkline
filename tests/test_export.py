"""The projection says what the source says, and the coverage statement counts the result."""

from __future__ import annotations

import pytest

from chalkline import ctid as ctid_module
from chalkline.attachment import Attachment
from chalkline.ctdl import export, validate
from chalkline.model import Catalog, build_catalog
from chalkline.sources import leaflet_pages, sort_table
from chalkline.sources import leaflets as leaflets_module
from tests.conftest import row, table

CTIDS = ctid_module.load_ledger()
LEAFLETS_PUBLISHED = len(leaflets_module.load())


@pytest.fixture(scope="module")
def document(real_catalog: Catalog, real_attachments: dict[str, Attachment]) -> dict[str, object]:
    return export.project_graph(real_catalog, CTIDS, real_attachments)


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
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", None)
    assert entity["ceterms:description"] == {export.LANG: "Academic Subject"}

    quiet = build_catalog(sort_table.parse(table(row(subject_code="ART", subject="Art"))))
    bare = export.project_license(quiet.authorizations[0], "ce-x", "urn:org", None)
    assert "ceterms:description" not in bare


def test_no_subject_property_when_the_commission_published_none() -> None:
    catalog = build_catalog(sort_table.parse(table(row(subject_code="NONE", subject=""))))
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", None)
    assert "ceterms:subject" not in entity


def test_subject_alignments_carry_the_code_name_and_row_notes() -> None:
    catalog = build_catalog(
        sort_table.parse(table(row(subject_code="ART", subject="Art", notes=("Academic",))))
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", None)
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
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", None)
    codes = [v["ceterms:identifierValueCode"] for v in entity["ceterms:identifier"]]
    assert codes == ["BASP"]


def test_comma_separated_codes_become_separate_identifiers() -> None:
    catalog = build_catalog(
        sort_table.parse(
            table(row(document="TC1, TC2", code="R1S, R1F", subject_code="NONE", subject=""))
        )
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", None)
    codes = [v["ceterms:identifierValueCode"] for v in entity["ceterms:identifier"]]
    assert codes == ["TC1", "TC2", "R1S", "R1F"]


def test_the_subject_webpage_is_the_leaflet_where_there_is_one() -> None:
    leaflet = leaflets_module.Leaflet(
        code="cl-380", title="School Nurse Services Credential", url="https://example.gov/380"
    )
    attachment = Attachment(
        match=leaflets_module.Match(leaflet=leaflet, rule=leaflets_module.MATCH_EXACT_TITLE),
        page=None,
        refusal="not read, for this test",
    )
    assert export.webpage_for(attachment) == leaflet.url
    assert export.webpage_for(None) == sort_table.SOURCE_URL


def test_export_refuses_to_mint_a_missing_ctid(real_catalog: Catalog) -> None:
    with pytest.raises(KeyError, match="mint-ctids"):
        export.project_graph(real_catalog, {}, {})


def test_coverage_is_counted_from_the_graph(
    document: dict[str, object],
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
) -> None:
    statement = export.coverage(document, real_catalog, real_attachments, LEAFLETS_PUBLISHED)
    assert statement["entities"]["ceterms:License"] == len(licenses(document))
    assert statement["authorizations"]["modeled"] == len(real_catalog.authorizations)
    assert statement["authorizations"]["excluded"] == len(real_catalog.exclusions)
    assert statement["authorizations"]["published_in_source"] == len(
        real_catalog.authorizations
    ) + len(real_catalog.exclusions)
    assert sum(statement["excluded_by_reason"].values()) == len(real_catalog.exclusions)
    assert statement["authorizations"]["scope_resolved_by_cross_reference"] == sum(
        1 for a in real_catalog.authorizations if a.resolved_from is not None
    )
    leaflets_counted = statement["leaflets"]
    assert leaflets_counted["authorizations_with_a_leaflet"] + leaflets_counted[
        "authorizations_without_a_leaflet"
    ] == len(real_catalog.authorizations)
    assert sum(leaflets_counted["matched_by_rule"].values()) == len(real_attachments)


def test_a_coverage_statement_the_export_contradicts_is_refused(
    document: dict[str, object],
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
) -> None:
    statement = export.coverage(document, real_catalog, real_attachments, LEAFLETS_PUBLISHED)
    statement["entities"] = {"ceterms:License": 1}
    problems = export.coverage_problems(
        statement, document, real_catalog, real_attachments, LEAFLETS_PUBLISHED
    )
    assert problems
    with pytest.raises(ValueError, match="does not describe the export"):
        export.check_coverage(
            statement, document, real_catalog, real_attachments, LEAFLETS_PUBLISHED
        )


def test_projection_is_byte_for_byte_deterministic(
    real_catalog: Catalog, real_attachments: dict[str, Attachment]
) -> None:
    first = export.serialize(export.project_graph(real_catalog, CTIDS, real_attachments))
    second = export.serialize(export.project_graph(real_catalog, CTIDS, real_attachments))
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


def attachment_with(*sections: leaflet_pages.Section) -> Attachment:
    leaflet = leaflets_module.Leaflet(
        code="cl-1", title="A Thing", url="https://www.ctc.ca.gov/credentials/leaflets/cl-1/"
    )
    page = leaflet_pages.LeafletPage(
        code="cl-1",
        page_title="A Thing",
        lead=("Leaflet prose.",),
        sections=sections,
        stopped_at=None,
        skipped_headings=(),
    )
    return Attachment(
        match=leaflets_module.Match(leaflet=leaflet, rule=leaflets_module.MATCH_EXACT_TITLE),
        page=page,
        refusal=None,
    )


def test_leaflet_prose_becomes_the_description_and_outranks_the_notes_column() -> None:
    catalog = build_catalog(
        sort_table.parse(table(row(subject_code="ART", subject="Art", notes=("Academic",))))
    )
    attachment = attachment_with(
        leaflet_pages.Section(
            heading="Requirements",
            level=2,
            kind=leaflet_pages.REQUIREMENTS,
            blocks=("Hold a degree.", "Pass an exam."),
        ),
        leaflet_pages.Section(
            heading="Period of Validity",
            level=2,
            kind=leaflet_pages.VALIDITY,
            blocks=("Five years.",),
        ),
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", attachment)
    assert entity["ceterms:description"] == {export.LANG: "Leaflet prose."}
    (requires,) = entity["ceterms:requires"]
    assert requires["@type"] == "ceterms:ConditionProfile"
    assert requires["ceterms:name"] == {export.LANG: "Requirements"}
    assert requires["ceterms:condition"] == {export.LANG: ["Hold a degree.", "Pass an exam."]}
    assert requires["ceterms:subjectWebpage"] == attachment.leaflet.url
    (renewal,) = entity["ceterms:renewal"]
    assert renewal["ceterms:condition"] == {export.LANG: ["Five years."]}
    assert entity["ceterms:subjectWebpage"] == attachment.leaflet.url


def test_a_leaflet_that_states_nothing_leaves_the_notes_column_standing() -> None:
    catalog = build_catalog(
        sort_table.parse(table(row(subject_code="ART", subject="Art", notes=("Academic",))))
    )
    attachment = attachment_with()
    object.__setattr__(attachment.page, "lead", ())
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", attachment)
    assert entity["ceterms:description"] == {export.LANG: "Academic"}
    assert "ceterms:requires" not in entity
    assert "ceterms:renewal" not in entity


def test_a_section_with_no_text_produces_no_condition_profile() -> None:
    catalog = build_catalog(sort_table.parse(table(row(subject_code="ART", subject="Art"))))
    attachment = attachment_with(
        leaflet_pages.Section(
            heading="Requirements", level=2, kind=leaflet_pages.REQUIREMENTS, blocks=()
        )
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", attachment)
    assert "ceterms:requires" not in entity


def test_every_emitted_condition_profile_is_in_the_range_of_its_property(
    document: dict[str, object],
) -> None:
    seen = 0
    for entity in licenses(document):
        for term in ("ceterms:requires", "ceterms:renewal"):
            profiles: list[dict[str, object]] = entity.get(term, [])  # type: ignore[assignment]
            for profile in profiles:
                assert profile["@type"] == "ceterms:ConditionProfile"
                assert profile["ceterms:condition"][export.LANG]  # type: ignore[index]
                seen += 1
    assert seen, "the vendored leaflets should yield at least one condition profile"


def test_an_authorization_with_no_codes_at_all_emits_no_identifier() -> None:
    """Nothing is fabricated to fill the property: no code published, no identifier."""
    catalog = build_catalog(
        sort_table.parse(table(row(document="Multiple", code="", subject_code="NONE", subject="")))
    )
    entity = export.project_license(catalog.authorizations[0], "ce-x", "urn:org", None)
    assert "ceterms:identifier" not in entity
