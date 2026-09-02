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
INDEX = leaflets_module.load_index()
VENDORED = leaflet_pages.available()


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
    statement = export.coverage(document, real_catalog, real_attachments, INDEX, VENDORED)
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


def test_the_census_counts_every_property_the_export_emits(
    document: dict[str, object],
) -> None:
    """No property lands on a License without the coverage statement counting it."""
    assert export.census_problems(document) == []
    emitted = {term for e in licenses(document) for term in e if not term.startswith("@")}
    assert emitted, "the export should put properties on a License"
    assert emitted <= set(export.LICENSE_PROPERTIES)


def test_a_property_the_census_does_not_count_is_refused(
    document: dict[str, object],
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
) -> None:
    """The check the tautological one could not make: the statement's shape has gone stale.

    A statement counted from the same inputs always agrees with itself, so a property added
    to the export and not to :data:`export.LICENSE_PROPERTIES` would ship uncounted. This is
    what makes that a build failure.
    """
    graph: list[dict[str, object]] = document["@graph"]  # type: ignore[assignment]
    extended = dict(document)
    first, *rest = graph
    extended["@graph"] = [{**first, "ceterms:availableOnlineAt": "https://example.gov/"}, *rest]

    problems = export.census_problems(extended)
    assert problems == []  # the organization is not a License, so its properties are not counted

    licensed = next(e for e in graph if e.get("@type") == "ceterms:License")
    extended["@graph"] = [
        {**e, "ceterms:availableOnlineAt": "https://example.gov/"} if e is licensed else e
        for e in graph
    ]
    assert export.census_problems(extended) == [
        "license_properties does not count ceterms:availableOnlineAt, "
        "which the export emits on a License"
    ]
    statement = export.coverage(extended, real_catalog, real_attachments, INDEX, VENDORED)
    with pytest.raises(ValueError, match="ceterms:availableOnlineAt"):
        export.check_coverage(statement, extended, real_catalog, real_attachments, INDEX, VENDORED)


def test_requirements_and_renewal_are_counted_as_a_union_not_a_sum(
    document: dict[str, object],
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
) -> None:
    """An authorization carrying both is one authorization, not two."""
    statement = export.coverage(document, real_catalog, real_attachments, INDEX, VENDORED)
    counted = statement["authorizations"]["with_requirements_or_renewal_terms"]
    both = [e for e in licenses(document) if "ceterms:requires" in e and "ceterms:renewal" in e]
    assert both, "the fixture should hold an authorization carrying both"
    assert counted == len(
        [e for e in licenses(document) if "ceterms:requires" in e or "ceterms:renewal" in e]
    )
    properties = statement["license_properties"]
    assert counted < properties["ceterms:requires"] + properties["ceterms:renewal"]


def test_a_coverage_statement_the_export_contradicts_is_refused(
    document: dict[str, object],
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
) -> None:
    statement = export.coverage(document, real_catalog, real_attachments, INDEX, VENDORED)
    statement["entities"] = {"ceterms:License": 1}
    problems = export.coverage_problems(
        statement, document, real_catalog, real_attachments, INDEX, VENDORED
    )
    assert problems
    with pytest.raises(ValueError, match="does not describe the export"):
        export.check_coverage(statement, document, real_catalog, real_attachments, INDEX, VENDORED)


def test_projection_is_byte_for_byte_deterministic(
    real_catalog: Catalog, real_attachments: dict[str, Attachment]
) -> None:
    first = export.serialize(export.project_graph(real_catalog, CTIDS, real_attachments))
    second = export.serialize(export.project_graph(real_catalog, CTIDS, real_attachments))
    assert first == second


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
        classified_beyond_the_stop=(),
        set_aside=(),
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


def test_a_leaflet_read_stopped_partway_is_counted_not_silent(
    real_catalog: Catalog,
) -> None:
    """A stop looks, in every other property count, exactly like a page read to its end.

    Before `Attachment.stopped_at` existed, `LeafletPage.stopped_at` was computed by the
    parser and read by nothing downstream: a license whose leaflet stopped partway published
    the same zero `ceterms:requires`/`ceterms:renewal` as one read whole with nothing further
    to state, with no coverage figure telling the two apart (issue #36).
    """
    stopped = attachment_with()
    object.__setattr__(stopped.page, "stopped_at", "Some Other Credential")
    whole = attachment_with()
    attachments = {
        real_catalog.authorizations[0].key: stopped,
        real_catalog.authorizations[1].key: whole,
    }
    statement = export.coverage({"@graph": []}, real_catalog, attachments, INDEX, VENDORED)
    leaflets_counted = statement["leaflets"]
    assert leaflets_counted["authorizations_with_a_leaflet_reading_stopped_before_the_end"] == 1
    assert leaflets_counted["reading_stopped_at_heading"] == {"Some Other Credential": 1}


def test_the_vendored_leaflets_include_at_least_one_stopped_read(
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
) -> None:
    """Pins a real stop so the count cannot quietly go stale.

    ``cl-562`` ("Teacher Librarian Services Credential") stops at "Special Class
    Authorization", which is a different Commission document and which the Commission gave an
    outline of its own: an authorization, its requirements, its period of validity and its
    terms. Everything before it belongs to the Teacher Librarian Services Credential and is
    read; nothing after it does.

    That heading used to be reached only after the page had already ended at "National Board
    for Professional Teaching Standards Certification", which is an alternate route to the
    same credential and is now read past (issue #36).
    """
    statement = export.coverage({"@graph": []}, real_catalog, real_attachments, INDEX, VENDORED)
    leaflets_counted = statement["leaflets"]
    directly_counted = sum(1 for a in real_attachments.values() if a.stopped_at is not None)
    assert directly_counted > 0
    assert (
        leaflets_counted["authorizations_with_a_leaflet_reading_stopped_before_the_end"]
        == directly_counted
    )
    assert "Special Class Authorization" in leaflets_counted["reading_stopped_at_heading"]


def test_the_coverage_statement_sizes_what_a_stopped_read_left_behind(
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
    real_index: leaflets_module.Index,
    vendored_pages: tuple[str, ...],
) -> None:
    """A stop is disclosed; this is how large it is.

    Both figures fell hard when issue #36 was fixed: sixteen attached authorizations had a
    stopped read and fifteen of those lost a classified heading, against six and six now. The
    difference is not that less is disclosed, it is that less is dropped. What is behind a
    stop today is another Commission document's own statements, which is what the rule was
    always meant to exclude.
    """
    document = export.project_graph(real_catalog, ctid_module.load_ledger(), real_attachments)
    leaflets = export.coverage(
        document, real_catalog, real_attachments, real_index, vendored_pages
    )["leaflets"]

    stopped = leaflets["authorizations_with_a_leaflet_reading_stopped_before_the_end"]
    lost = leaflets["authorizations_whose_stop_left_a_classified_heading_unread"]
    headings = leaflets["headings_left_unread_beyond_the_stop"]

    assert stopped == 6
    assert lost == 6, "every stop today is a document the Commission gave its own statements"
    assert sum(headings.values()) == sum(
        len(attachment.classified_beyond_the_stop) for attachment in real_attachments.values()
    ), "the tally and the attachments disagree about how many headings were left unread"
    assert headings["Requirements for the Special Teaching Authorization in Health"] == 1, (
        "CL-380's stop is the one the rule exists for, and what it leaves unread is the "
        "Special Teaching Authorization in Health's own requirements"
    )
    assert all(count > 0 for count in headings.values())


def test_the_coverage_statement_names_what_was_set_aside_rather_than_read(
    real_catalog: Catalog,
    real_attachments: dict[str, Attachment],
    real_index: leaflets_module.Index,
    vendored_pages: tuple[str, ...],
) -> None:
    """The weaker judgement is published in full, because it is the weaker judgement.

    A heading naming a document that the Commission gave no sub-headings is read past rather
    than read: its prose is not attributed to this authorization, and the page after it is.
    Every such heading is listed with a count rather than summarised, so a reader can check
    the call on each one. "TPSL Authorizations" is the case to check: it is an overview of
    what the Teaching Permit for Statutory Leave's own variants authorize, on that permit's
    own leaflet, and reading it as another document is what used to cost both TPSL entries
    their period of validity.
    """
    document = export.project_graph(real_catalog, ctid_module.load_ledger(), real_attachments)
    leaflets = export.coverage(
        document, real_catalog, real_attachments, real_index, vendored_pages
    )["leaflets"]

    set_aside = leaflets["authorizations_whose_leaflet_set_a_subject_aside"]
    headings = leaflets["headings_set_aside_as_another_subject"]

    assert set_aside == sum(1 for a in real_attachments.values() if a.set_aside)
    assert set_aside > 0, "nothing was set aside, so this check is checking nothing"
    assert sum(headings.values()) == sum(
        len(attachment.set_aside) for attachment in real_attachments.values()
    ), "the tally and the attachments disagree about how many headings were set aside"
    assert headings["TPSL Authorizations"] == 2
    assert "TPSL Authorizations" not in leaflets["reading_stopped_at_heading"], (
        "the heading issue #36 names is set aside now, not the end of the page"
    )
    assert all(count > 0 for count in headings.values())


def test_an_attachment_whose_page_was_refused_reports_no_headings_beyond_a_stop(
    real_attachments: dict[str, Attachment],
) -> None:
    """No page means no measurement, and an empty tuple is the honest answer, not a zero.

    The four authorizations whose leaflet page this project refuses on identity have no read
    to have stopped. They must not appear in the tally above as if their leaflet had been
    read to the end.
    """
    refused = [a for a in real_attachments.values() if a.refusal is not None]
    assert len(refused) == 4, f"{len(refused)} refused attachments, expected 4"
    for attachment in refused:
        assert attachment.page is None
        assert attachment.stopped_at is None
        assert attachment.classified_beyond_the_stop == ()
