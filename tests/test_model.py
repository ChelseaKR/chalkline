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


def test_scope_deferred_to_another_credential_is_excluded() -> None:
    catalog = catalog_from(
        row(
            subject_code="",
            subject="",
            notes=("Subject Codes Same as on Single Subject Teaching Credential",),
        )
    )
    assert catalog.authorizations == ()
    (exclusion,) = catalog.exclusions
    assert exclusion.reason == model.REASON_DEFERRED
    assert exclusion.published_notes == (
        "Subject Codes Same as on Single Subject Teaching Credential",
    )


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
