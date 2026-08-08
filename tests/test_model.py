"""Grouping, and the one thing that causes an exclusion: an unverifiable scope."""

from __future__ import annotations

import pytest

from chalkline import model
from chalkline.model import build_catalog
from chalkline.sources import sort_table
from tests.conftest import row, table


def catalog_from(*rows: str) -> model.Catalog:
    return build_catalog(sort_table.parse(table(*rows)))


def test_rows_sharing_a_triple_become_one_authorization() -> None:
    catalog = catalog_from(
        row(subject_code="ART", subject="Art"),
        row(subject_code="MUS", subject="Music"),
    )
    (authorization,) = catalog.authorizations
    assert [scope.code for scope in authorization.subjects] == ["ART", "MUS"]


def test_the_same_code_on_different_documents_stays_two_credentials() -> None:
    catalog = catalog_from(
        row(document="TC2", title="Multiple Subject Teaching Credential", code="R2M"),
        row(document="TPSL", title="Teaching Permit for Statutory Leave", code="R2M"),
    )
    assert len(catalog.authorizations) == 2
    assert len({a.key for a in catalog.authorizations}) == 2


def test_published_none_is_a_statement_not_a_gap() -> None:
    catalog = catalog_from(row(subject_code="NONE", subject=""))
    (authorization,) = catalog.authorizations
    assert authorization.declares_no_subject_codes is True
    assert authorization.subjects == ()
    assert catalog.exclusions == ()


DEFERS_SUBJECTS = "Subject Codes Same as on Single Subject Teaching Credential"
DEFERS_EVERYTHING = (
    "Authorization and Subject Codes Same as on Education Specialist Instruction Credential"
)


def test_a_deferred_scope_is_resolved_from_the_credential_the_note_names() -> None:
    """The note points at rows in this same table, and those rows supply the subjects."""
    catalog = catalog_from(
        row(subject_code="ART", subject="Art", notes=("Academic Subject",)),
        row(subject_code="MUS", subject="Music"),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            subject_code="",
            subject="",
            notes=(DEFERS_SUBJECTS,),
        ),
    )
    assert catalog.exclusions == ()
    permit = catalog.authorizations[1]
    assert permit.title == "Short-Term Staff Permit"
    assert [(s.code, s.name) for s in permit.subjects] == [("ART", "Art"), ("MUS", "Music")]
    resolution = permit.resolved_from
    assert resolution is not None
    assert resolution.note == DEFERS_SUBJECTS
    assert resolution.credential == "Single Subject Teaching Credential"
    assert resolution.document_title == "TC1"
    assert resolution.defers_authorization_codes is False
    assert resolution.subjects_supplied == 2


def test_the_referenced_rows_notes_do_not_travel_with_the_subjects() -> None:
    """The Commission said the subject codes are the same; its row notes are not that claim."""
    catalog = catalog_from(
        row(subject_code="ART", subject="Art", notes=("Pursuant to Title 5 80004(c)",)),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            subject_code="",
            subject="",
            notes=(DEFERS_SUBJECTS,),
        ),
    )
    source, permit = catalog.authorizations
    assert source.subjects[0].notes == ("Pursuant to Title 5 80004(c)",)
    assert permit.subjects[0].notes == ()


def test_the_cross_reference_note_does_not_become_a_description() -> None:
    catalog = catalog_from(
        row(subject_code="ART", subject="Art"),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            subject_code="",
            subject="",
            notes=(DEFERS_SUBJECTS,),
        ),
    )
    assert catalog.authorizations[1].shared_notes == ()


def test_a_note_deferring_the_codes_too_takes_the_referenced_credentials_codes() -> None:
    catalog = catalog_from(
        row(
            document="TC3S",
            title="Education Specialist Instruction Credential",
            code="R3MN",
            subject_code="MN",
            subject="Mild to Moderate Support Needs",
        ),
        row(
            document="TC3S",
            title="Education Specialist Instruction Credential",
            code="SEEC",
            subject_code="NONE",
            subject="Early Childhood Added Authorization",
        ),
        row(
            document="TLA3",
            title="Special Education Limited Assignment Teaching Permit",
            code="",
            subject_code="",
            subject="",
            notes=(DEFERS_EVERYTHING,),
        ),
    )
    permit = catalog.authorizations[-1]
    assert permit.authorization_code == ""
    assert permit.authorization_codes == ("R3MN", "SEEC")
    assert [s.code for s in permit.subjects] == ["MN"]
    resolution = permit.resolved_from
    assert resolution is not None
    assert resolution.defers_authorization_codes is True
    assert [(s.authorization_code, s.subjects_supplied) for s in resolution.sources] == [
        ("R3MN", 1),
        ("SEEC", 0),
    ]
    assert resolution.sources[1].declares_no_subject_codes is True


def test_a_reference_to_a_credential_the_table_does_not_publish_stays_excluded() -> None:
    catalog = catalog_from(
        row(subject_code="ART", subject="Art"),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            subject_code="",
            subject="",
            notes=("Subject Codes Same as on Nonexistent Credential",),
        ),
    )
    (exclusion,) = catalog.exclusions
    assert "no row in the table publishes the Authorization Title" in exclusion.reason
    assert "Subject Codes Same as on Nonexistent Credential" in exclusion.reason


def test_a_reference_that_lands_on_two_documents_stays_excluded() -> None:
    catalog = catalog_from(
        row(document="TC1", subject_code="ART", subject="Art"),
        row(document="TC2", subject_code="MUS", subject="Music"),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            subject_code="",
            subject="",
            notes=(DEFERS_SUBJECTS,),
        ),
    )
    (exclusion,) = catalog.exclusions
    assert "more than one document" in exclusion.reason


def test_a_reference_to_a_code_the_named_credential_does_not_carry_stays_excluded() -> None:
    catalog = catalog_from(
        row(code="R1S", subject_code="ART", subject="Art"),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            code="R1F",
            subject_code="",
            subject="",
            notes=(DEFERS_SUBJECTS,),
        ),
    )
    (exclusion,) = catalog.exclusions
    assert "publishes no rows under the Authorization Code(s) R1F" in exclusion.reason


def test_a_circular_reference_stays_excluded() -> None:
    """A credential that defers its own scope is not an end point for somebody else's."""
    catalog = catalog_from(
        row(subject_code="", subject="", notes=("Subject Codes Same as on Another Credential",)),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            subject_code="",
            subject="",
            notes=(DEFERS_SUBJECTS,),
        ),
    )
    reasons = [e.reason for e in catalog.exclusions]
    assert any("does not end at published subjects" in reason for reason in reasons)


def test_a_reference_to_rows_that_publish_only_none_stays_excluded() -> None:
    catalog = catalog_from(
        row(subject_code="NONE", subject=""),
        row(
            document="TC13",
            title="Short-Term Staff Permit",
            subject_code="",
            subject="",
            notes=(DEFERS_SUBJECTS,),
        ),
    )
    (exclusion,) = catalog.exclusions
    assert "publishes no subject codes under the referenced rows" in exclusion.reason


def test_an_unrecognised_note_is_not_treated_as_a_cross_reference() -> None:
    catalog = catalog_from(
        row(subject_code="", subject="", notes=("See the Special Education Assignment Chart",))
    )
    (exclusion,) = catalog.exclusions
    assert exclusion.reason == model.REASON_UNPUBLISHED


def test_scope_on_the_issued_document_is_excluded() -> None:
    catalog = catalog_from(row(subject_code="", subject="Indicated on Document"))
    (exclusion,) = catalog.exclusions
    assert exclusion.reason == model.REASON_ON_DOCUMENT


def test_scope_published_nowhere_is_excluded() -> None:
    catalog = catalog_from(row(subject_code="", subject=""))
    (exclusion,) = catalog.exclusions
    assert exclusion.reason == model.REASON_UNPUBLISHED
    assert exclusion.key.endswith("|R1S")


def test_a_name_is_never_the_reason_for_an_exclusion(real_catalog: model.Catalog) -> None:
    assert all(exclusion.title for exclusion in real_catalog.exclusions)


def test_contradictory_scope_stops_the_build() -> None:
    with pytest.raises(ValueError, match="contradict"):
        catalog_from(
            row(subject_code="ART", subject="Art"),
            row(subject_code="NONE", subject=""),
        )


def test_shared_notes_only_where_every_row_agrees() -> None:
    agreeing = catalog_from(
        row(subject_code="ART", subject="Art", notes=("Academic Subject",)),
        row(subject_code="MUS", subject="Music", notes=("Academic Subject",)),
    )
    assert agreeing.authorizations[0].shared_notes == ("Academic Subject",)

    differing = catalog_from(
        row(subject_code="ART", subject="Art", notes=("Academic Subject",)),
        row(subject_code="MUS", subject="Music", notes=("Something else",)),
    )
    assert differing.authorizations[0].shared_notes == ()


def test_comma_cells_split_and_multiple_is_not_a_code() -> None:
    assert model.split_cell("R1S, R1F, R1GS") == ("R1S", "R1F", "R1GS")
    assert model.split_cell("  ") == ()
    assert model.document_codes("TC1, TC2") == ("TC1", "TC2")
    assert model.document_codes("Multiple") == ()


def test_catalog_accounts_for_every_published_authorization(
    real_catalog: model.Catalog,
) -> None:
    """Modeled plus excluded equals what the table published. Nothing is silently dropped."""
    grouped = {
        (r.document_title, r.authorization_title, r.authorization_code) for r in sort_table.load()
    }
    assert len(real_catalog.authorizations) + len(real_catalog.exclusions) == len(grouped)
    assert real_catalog.source_rows == len(sort_table.load())


def test_every_modeled_authorization_has_a_resolvable_scope(
    real_catalog: model.Catalog,
) -> None:
    assert all(bool(a.subjects) != a.declares_no_subject_codes for a in real_catalog.authorizations)
