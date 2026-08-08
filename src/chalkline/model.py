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

Cross-references, and how they are followed
-------------------------------------------

A row in the third case sometimes carries a Commission note that points at another
credential's rows in this same table. Two forms are published:

* ``Subject Codes Same as on <credential>`` defers only the subject list. The deferring row
  publishes its own Authorization Code, so the reference is followed **code by code**: for
  each Authorization Code on the deferring row, the subjects are the ones the named
  credential publishes under that same Authorization Code.
* ``Authorization and Subject Codes Same as on <credential>`` defers both. The deferring row
  publishes no Authorization Code at all, so the reference is followed **credential-wide**:
  the deferring authorization takes the named credential's Authorization Codes and the
  subjects published against them.

Both forms are resolved from this table and nothing else. The named credential is found by
its published Authorization Title, exactly; if the title names nothing in the table, names
rows on more than one document, or names an authorization that is itself deferred, the
reference is not followed and the authorization stays excluded with a reason that says which
of those it was. A code on the deferring row that the named credential does not publish is
the same kind of refusal.

**The referenced rows' Notes do not travel with the subjects.** The Commission's statement is
that the subject *codes* are the same; a note such as "Pursuant to Title 5 80004(c) ..." is a
remark it attached to the row it wrote, and copying it onto a different credential would be
this project asserting something the Commission did not. The subject code and the subject
name cross; nothing else does.

An authorization whose every row falls in the third case and whose reference cannot be
followed is **excluded**, with its reason recorded.

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

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Final

from chalkline.sources.sort_table import SortTableRow

NO_SUBJECT_CODES: Final = "NONE"
"""The Commission's published value for "this authorization is not subject-coded"."""

NOT_A_DOCUMENT_CODE: Final = "Multiple"
"""Published in the Document Title column when several document types carry the
authorization. A statement about the credential, not a code for one."""

SCOPE_ON_DOCUMENT: Final = "Indicated on Document"
"""Published in the Subject column when the scope is written on the issued credential."""

SUBJECTS_DEFERRED_RE: Final = re.compile(r"^Subject Codes Same as on (?P<credential>.+?)\.?$")
"""The Commission's note for "this authorization's subjects are another credential's"."""

ALL_CODES_DEFERRED_RE: Final = re.compile(
    r"^Authorization and Subject Codes Same as on (?P<credential>.+?)\.?$"
)
"""The Commission's note for "this authorization's codes *and* subjects are another's"."""

REASON_ON_DOCUMENT: Final = (
    "the sort table states that the subjects are indicated on the issued document, so the "
    "scope is not published in any machine-readable source this project reads"
)
REASON_UNPUBLISHED: Final = (
    "the sort table publishes no subject code, no subject, and no note describing the "
    "scope for this authorization"
)


def reason_unfollowable(note: str, finding: str) -> str:
    """Why a published cross-reference could not be followed, saying what was found."""
    return (
        f"the sort table defers this authorization's scope with the note {note!r}, and that "
        f"reference cannot be followed within the table: {finding}"
    )


@dataclass(frozen=True, slots=True)
class SubjectScope:
    """One subject an authorization covers, as the Commission coded and named it."""

    code: str
    name: str
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferencedRows:
    """One Authorization Code of a referenced credential, and what it supplied."""

    authorization_code: str
    subjects_supplied: int
    declares_no_subject_codes: bool


@dataclass(frozen=True, slots=True)
class Resolution:
    """How a deferred scope was resolved, in enough detail to audit it row by row."""

    note: str
    """The Commission's cross-reference note, verbatim."""

    credential: str
    """The Authorization Title the note names."""

    document_title: str
    """The Document Title the referenced rows sit on."""

    defers_authorization_codes: bool
    """Whether the note deferred the Authorization Codes as well as the subjects."""

    sources: tuple[ReferencedRows, ...]
    """Every referenced Authorization Code, in the order the table publishes it."""

    @property
    def subjects_supplied(self) -> int:
        return sum(source.subjects_supplied for source in self.sources)


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
    resolved_from: Resolution | None = field(default=None)
    """Set only where the subjects came from another credential's rows by cross-reference."""

    @property
    def key(self) -> str:
        """Stable identity across runs: the published triple, joined.

        This is the key the CTID ledger is written against, so it must never be derived
        from anything that can drift, such as row order or a count. A resolved
        cross-reference does not change it: the triple is still the one the table publishes.
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
    return REASON_UNPUBLISHED


def cross_reference(rows: list[SortTableRow]) -> tuple[str, str, bool] | None:
    """The note, the credential it names, and whether it defers the codes too.

    ``None`` when the Commission published no cross-reference on any of these rows. Only
    the two published forms are recognised; a note this project has not seen before is not
    guessed at, so a new wording upstream leaves the authorization excluded rather than
    resolved against the wrong rows.
    """
    for note in (note for row in rows for note in row.notes):
        both = ALL_CODES_DEFERRED_RE.fullmatch(note)
        if both:
            return note, both.group("credential"), True
        subjects_only = SUBJECTS_DEFERRED_RE.fullmatch(note)
        if subjects_only:
            return note, subjects_only.group("credential"), False
    return None


def _subjects_of(rows: list[SortTableRow]) -> tuple[SubjectScope, ...]:
    """The subject rows of a group, as scopes. Row notes stay on the row that carries them."""
    return tuple(
        SubjectScope(code=row.subject_code, name=row.subject, notes=row.notes)
        for row in rows
        if row.subject_code and row.subject_code != NO_SUBJECT_CODES and row.subject
    )


def _referenced_groups(
    credential: str, grouped: OrderedDict[tuple[str, str, str], list[SortTableRow]]
) -> tuple[list[tuple[str, str, list[SortTableRow]]], str | None]:
    """Every group the named Authorization Title identifies, or why it identifies none.

    The title must land on exactly one Document Title. A title that appears on two documents
    names two different credentials in the Commission's own key, and this project will not
    choose between them.
    """
    found = [
        (document, code, rows)
        for (document, title, code), rows in grouped.items()
        if title == credential
    ]
    if not found:
        return [], f"no row in the table publishes the Authorization Title {credential!r}"
    documents = sorted({document for document, _, _ in found})
    if len(documents) > 1:
        return [], (
            f"the Authorization Title {credential!r} is published on more than one document "
            f"({', '.join(documents)}), so the reference does not identify one credential"
        )
    return found, None


def _resolve(
    note: str,
    credential: str,
    defers_codes: bool,
    own_codes: tuple[str, ...],
    grouped: OrderedDict[tuple[str, str, str], list[SortTableRow]],
) -> tuple[Resolution, tuple[SubjectScope, ...], tuple[str, ...]] | str:
    """Follow one cross-reference, or say in one sentence why it cannot be followed."""
    found, problem = _referenced_groups(credential, grouped)
    if problem is not None:
        return problem

    if defers_codes:
        selected = [(code, rows) for _, code, rows in found]
    else:
        by_code = {code: rows for _, code, rows in found}
        missing = [code for code in own_codes if code not in by_code]
        if missing:
            return (
                f"{credential!r} publishes no rows under the Authorization Code(s) "
                f"{', '.join(missing)} that this authorization carries"
            )
        selected = [(code, by_code[code]) for code in own_codes]

    circular = [code for code, rows in selected if cross_reference(rows) is not None]
    if circular:
        return (
            f"{credential!r} defers its own scope under the Authorization Code(s) "
            f"{', '.join(circular)}, so the reference does not end at published subjects"
        )

    subjects: list[SubjectScope] = []
    sources: list[ReferencedRows] = []
    for code, rows in selected:
        supplied = _subjects_of(rows)
        subjects.extend(
            # The Commission's statement is that the subject codes are the same. Its notes
            # on the referenced rows are remarks about those rows and do not travel.
            SubjectScope(code=scope.code, name=scope.name, notes=())
            for scope in supplied
        )
        sources.append(
            ReferencedRows(
                authorization_code=code,
                subjects_supplied=len(supplied),
                declares_no_subject_codes=any(row.subject_code == NO_SUBJECT_CODES for row in rows),
            )
        )
    if not subjects:
        return f"{credential!r} publishes no subject codes under the referenced rows"

    resolution = Resolution(
        note=note,
        credential=credential,
        document_title=found[0][0],
        defers_authorization_codes=defers_codes,
        sources=tuple(sources),
    )
    codes = tuple(source.authorization_code for source in sources) if defers_codes else own_codes
    return resolution, tuple(subjects), codes


def _scope_by_reference(
    rows: list[SortTableRow],
    own_codes: tuple[str, ...],
    grouped: OrderedDict[tuple[str, str, str], list[SortTableRow]],
) -> tuple[Resolution, tuple[SubjectScope, ...], tuple[str, ...]] | str:
    """The scope a cross-reference leads to, or the reason this authorization is excluded."""
    reference = cross_reference(rows)
    if reference is None:
        return _exclusion_reason(rows)
    followed = _resolve(*reference, own_codes, grouped)
    if isinstance(followed, str):
        return reason_unfollowable(reference[0], followed)
    return followed


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

    Grouping happens before anything is decided, because a cross-reference is followed
    against the whole table and a row that defers its scope may sit above the rows it
    defers to.
    """
    grouped: OrderedDict[tuple[str, str, str], list[SortTableRow]] = OrderedDict()
    for row in rows:
        grouped.setdefault(
            (row.document_title, row.authorization_title, row.authorization_code), []
        ).append(row)

    authorizations: list[Authorization] = []
    exclusions: list[Exclusion] = []
    for (document_title, title, code), group in grouped.items():
        subjects = _subjects_of(group)
        declares_none = any(row.subject_code == NO_SUBJECT_CODES for row in group)
        if subjects and declares_none:
            raise ValueError(
                f"{document_title}|{title}|{code}: the table gives this authorization both "
                f"subject codes and the literal {NO_SUBJECT_CODES!r}; the two statements "
                "contradict each other and this project will not choose between them"
            )
        codes = split_cell(code)
        shared = _shared_notes(group)
        resolution: Resolution | None = None
        if not subjects and not declares_none:
            followed = _scope_by_reference(group, codes, grouped)
            if isinstance(followed, str):
                exclusions.append(
                    Exclusion(
                        document_title=document_title,
                        title=title,
                        authorization_code=code,
                        reason=followed,
                        published_notes=tuple(note for row in group for note in row.notes),
                    )
                )
                continue
            resolution, subjects, codes = followed
            # The cross-reference is a route to the subjects, not prose about the
            # credential. Once followed it is recorded on the resolution, so keeping it as
            # a shared note would publish a table instruction as a description.
            shared = tuple(note for note in shared if note != resolution.note)
        authorizations.append(
            Authorization(
                document_title=document_title,
                title=title,
                authorization_code=code,
                document_codes=document_codes(document_title),
                authorization_codes=codes,
                subjects=subjects,
                declares_no_subject_codes=declares_none,
                shared_notes=shared,
                resolved_from=resolution,
            )
        )
    return Catalog(
        authorizations=tuple(authorizations),
        exclusions=tuple(exclusions),
        source_rows=len(rows),
    )
