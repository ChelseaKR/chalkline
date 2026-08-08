"""Group the sort table's rows into authorizations, and decide which ones can be modeled.

One authorization is one (Document Title, Authorization Title, Authorization Code) triple.
All three are load-bearing: ``R2M`` names six different credentials depending on the
document that carries it, ``R3MN`` appears on both the Education Specialist Instruction
Credential and its District Intern counterpart, and ``SMAB`` appears under two different
authorization titles. Keying on the code alone would merge credentials the Commission keeps
apart, so the key is the whole triple.

Scope, and the only reason anything is excluded
-----------------------------------------------

The Subject Code column says one of three things, and this module reads all three literally:

* **A subject code** (``BSS``, ``AGRI``). The authorization covers that subject. This is a
  resolvable scope and it becomes a subject alignment in the export.
* **``NONE``.** The Commission published the string ``NONE``, which is a statement, not a
  gap: this authorization is not subject-coded. That is also a resolvable scope, expressed
  as the absence of subject alignments plus a recorded flag, never as a missing value.
* **Nothing at all.** The scope lives somewhere this table does not reproduce, either in a
  cross-reference ("Subject Codes Same as on Single Subject Teaching Credential") or on the
  issued document itself ("Indicated on Document").

An authorization whose every row falls in the third case is **excluded**, with its reason
recorded, because its scope cannot be verified from the source this project reads. Resolving
those cross-references would mean asserting an equivalence between two credentials' subject
lists that the Commission states in prose and this project has not checked row by row. That
is a defensible next step, not something to guess at now.

Names are never the reason for an exclusion: every row in the vendored artifact carries an
Authorization Title, so every excluded authorization is excluded on scope alone.

Cell values that are lists
--------------------------

Two columns sometimes hold a comma-separated list: Document Title (``TC1, TC2``) and
Authorization Code (``R1S, R1F, R1GS, R1WL``). Splitting on the comma is the one structural
normalization this module performs, and the verbatim cell is kept alongside the split. The
Document Title value ``Multiple`` is not a document code; it is the Commission's way of
saying more than one document type carries the authorization, without naming them. It is
kept verbatim and never emitted as an identifier.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Final

from chalkline.sources.sort_table import SortTableRow

NO_SUBJECT_CODES: Final = "NONE"
"""The Commission's published value for "this authorization is not subject-coded"."""

NOT_A_DOCUMENT_CODE: Final = "Multiple"
"""Published in the Document Title column when several document types carry the
authorization. A statement about the credential, not a code for one."""

SCOPE_ON_DOCUMENT: Final = "Indicated on Document"
"""Published in the Subject column when the scope is written on the issued credential."""

REASON_DEFERRED: Final = (
    "the sort table does not enumerate this authorization's subjects; it refers the reader "
    "to another credential's subject list, and this project has not verified that the two "
    "lists match row by row"
)
REASON_ON_DOCUMENT: Final = (
    "the sort table states that the subjects are indicated on the issued document, so the "
    "scope is not published in any machine-readable source this project reads"
)
REASON_UNPUBLISHED: Final = (
    "the sort table publishes no subject code, no subject, and no note describing the "
    "scope for this authorization"
)


@dataclass(frozen=True, slots=True)
class SubjectScope:
    """One subject an authorization covers, as the Commission coded and named it."""

    code: str
    name: str
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Authorization:
    """One credential authorization the Commission currently issues."""

    document_title: str
    title: str
    authorization_code: str
    document_codes: tuple[str, ...]
    authorization_codes: tuple[str, ...]
    subjects: tuple[SubjectScope, ...]
    declares_no_subject_codes: bool
    shared_notes: tuple[str, ...]

    @property
    def key(self) -> str:
        """Stable identity across runs: the published triple, joined.

        This is the key the CTID ledger is written against, so it must never be derived
        from anything that can drift, such as row order or a count.
        """
        return f"{self.document_title}|{self.title}|{self.authorization_code}"


@dataclass(frozen=True, slots=True)
class Exclusion:
    """One authorization this project declines to model, and why."""

    document_title: str
    title: str
    authorization_code: str
    reason: str
    published_notes: tuple[str, ...]

    @property
    def key(self) -> str:
        return f"{self.document_title}|{self.title}|{self.authorization_code}"


@dataclass(frozen=True, slots=True)
class Catalog:
    """Everything the sort table yielded: what is modeled, and what is not."""

    authorizations: tuple[Authorization, ...]
    exclusions: tuple[Exclusion, ...]
    source_rows: int


def split_cell(value: str) -> tuple[str, ...]:
    """A possibly comma-separated cell as its tokens, in published order."""
    return tuple(token.strip() for token in value.split(",") if token.strip())


def document_codes(value: str) -> tuple[str, ...]:
    """The document codes in a Document Title cell, minus the non-code ``Multiple``."""
    return tuple(token for token in split_cell(value) if token != NOT_A_DOCUMENT_CODE)


def _exclusion_reason(rows: list[SortTableRow]) -> str:
    """Why an authorization with no resolvable scope has none, from what CTC published."""
    if any(row.subject == SCOPE_ON_DOCUMENT for row in rows):
        return REASON_ON_DOCUMENT
    if any("same as on" in note.lower() for row in rows for note in row.notes):
        return REASON_DEFERRED
    return REASON_UNPUBLISHED


def _shared_notes(rows: list[SortTableRow]) -> tuple[str, ...]:
    """Notes that describe the authorization rather than one of its subjects.

    A note qualifies only when every row of the authorization carries exactly the same note
    list. When notes vary by subject they are statements about those subjects, and they
    stay on the subject where the Commission put them.
    """
    first = rows[0].notes
    return first if all(row.notes == first for row in rows) else ()


def build_catalog(rows: tuple[SortTableRow, ...]) -> Catalog:
    """Every authorization in the table, sorted into modeled and excluded.

    Row order within an authorization is the Commission's publication order and is kept;
    the authorizations themselves are returned in first-appearance order, so the output is
    a function of the source artifact alone.
    """
    grouped: OrderedDict[tuple[str, str, str], list[SortTableRow]] = OrderedDict()
    for row in rows:
        grouped.setdefault(
            (row.document_title, row.authorization_title, row.authorization_code), []
        ).append(row)

    authorizations: list[Authorization] = []
    exclusions: list[Exclusion] = []
    for (document_title, title, code), group in grouped.items():
        subjects = tuple(
            SubjectScope(code=row.subject_code, name=row.subject, notes=row.notes)
            for row in group
            if row.subject_code and row.subject_code != NO_SUBJECT_CODES and row.subject
        )
        declares_none = any(row.subject_code == NO_SUBJECT_CODES for row in group)
        if not subjects and not declares_none:
            exclusions.append(
                Exclusion(
                    document_title=document_title,
                    title=title,
                    authorization_code=code,
                    reason=_exclusion_reason(group),
                    published_notes=tuple(note for row in group for note in row.notes),
                )
            )
            continue
        if subjects and declares_none:
            raise ValueError(
                f"{document_title}|{title}|{code}: the table gives this authorization both "
                f"subject codes and the literal {NO_SUBJECT_CODES!r}; the two statements "
                "contradict each other and this project will not choose between them"
            )
        authorizations.append(
            Authorization(
                document_title=document_title,
                title=title,
                authorization_code=code,
                document_codes=document_codes(document_title),
                authorization_codes=split_cell(code),
                subjects=subjects,
                declares_no_subject_codes=declares_none,
                shared_notes=_shared_notes(group),
            )
        )
    return Catalog(
        authorizations=tuple(authorizations),
        exclusions=tuple(exclusions),
        source_rows=len(rows),
    )
