"""Answer an assignment question from the committed graph, with the rows that support it.

The question this data exists to answer is "which credentials authorize teaching this
subject", and until now answering it meant reading a 553-row table or the JSON-LD by hand.
``chalkline authorizes`` answers it for one authorization and one subject, offline and
deterministically, and prints the evidence.

The answer is not two-valued, and that is the whole design.

**The absence of a row is not a denial.** The Commission publishes subject codes for some
authorizations and, for about half of them, none at all. "This credential does not
authorize Biological Sciences" would be a claim about assignment law that this project has
no basis for, so those answer ``not_subject_coded``. The counts live in
``site/coverage.json`` and in the README table that a test binds to it; they are not
repeated here, where nothing would notice them going stale.

**An authorization this project declined to model is not an authorization that does not
exist.** Three rows are excluded with a recorded reason. Reading their absence from the
graph as "no" would publish the project's own gap as a fact about the Commission.

**An unknown code is unknown.** A code the source does not publish answers "no such
authorization published", never "no".

So there are three exit codes and six answers, and only ``AUTHORIZES`` and
``DOES_NOT_AUTHORIZE`` are answers to the question as asked; the rest say why the published
record does not answer it.

Two sources, deliberately
-------------------------

The default source is ``site/credentials.jsonld``, the artifact this project publishes,
because an answer a reader cannot reproduce from the published artifact is not much of an
answer. ``--from-sources`` re-derives the catalog from the vendored Commission table
instead.

They agree on every authorization the graph carries, and a test holds them to it. They
cannot agree on two things, and the tool says so rather than papering over it: the graph
records neither the exclusions nor the cross-reference chain that resolved a deferred
scope, so from the graph alone an excluded authorization is indistinguishable from one that
was never published. When the graph answers ``unknown``, the printed answer names
``--from-sources`` as the way to tell those apart. That is the difference being reported,
not hidden.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from chalkline.ctdl.export import AUTHORIZATION_CODE_SCHEME, DOCUMENT_CODE_SCHEME
from chalkline.model import Authorization, Catalog


class Answer(StrEnum):
    """What the published record says about the question asked."""

    AUTHORIZES = "authorizes"
    DOES_NOT_AUTHORIZE = "does_not_authorize"
    NOT_SUBJECT_CODED = "not_subject_coded"
    NOT_MODELED = "not_modeled"
    UNKNOWN_AUTHORIZATION = "unknown_authorization"
    UNKNOWN_SUBJECT = "unknown_subject"
    AMBIGUOUS = "ambiguous"


#: Exit codes. Only the first two answer the question; every other answer means the
#: published record does not, and they share a code so that a script cannot mistake one of
#: them for a denial. Which one it was is in the printed answer and in ``--json``.
EXIT = {
    Answer.AUTHORIZES: 0,
    Answer.DOES_NOT_AUTHORIZE: 1,
    Answer.NOT_SUBJECT_CODED: 2,
    Answer.NOT_MODELED: 2,
    Answer.UNKNOWN_AUTHORIZATION: 2,
    Answer.UNKNOWN_SUBJECT: 2,
    Answer.AMBIGUOUS: 2,
}


class SourceUnreadable(Exception):
    """The source could not be read, so nothing is answered from it."""


@dataclass(frozen=True)
class SubjectView:
    code: str
    name: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class AuthorizationView:
    """One authorization, in the shape both sources can produce.

    ``title`` is the Authorization Title, the prose name ("Single Subject Teaching
    Credential"). ``document_codes`` is the Document Title cell, which this table
    publishes as codes ("TC1", "TPSL"), sometimes several. They are two columns and this
    module keeps them two: ``--title`` narrows by one and ``--document`` by the other.
    Matching one flag against both fields would be the quiet conflation the rest of this
    repository is built to avoid.

    ``resolution`` is ``None`` from the graph, which does not publish the cross-reference
    chain. It is absent there, not empty, and the rendering says which.
    """

    title: str
    document_codes: tuple[str, ...]
    codes: tuple[str, ...]
    subjects: tuple[SubjectView, ...]
    resolution: str | None

    @property
    def declares_no_subject_codes(self) -> bool:
        return not self.subjects

    @property
    def identity(self) -> tuple[str, tuple[str, ...]]:
        """What makes two views of the same authorization the same authorization."""
        return (self.title, tuple(sorted(self.codes)))

    def label(self) -> str:
        document = (
            ", ".join(self.document_codes) if self.document_codes else "no Document Title code"
        )
        codes = ", ".join(self.codes) if self.codes else "no Authorization Code"
        return f"{self.title} [{document}; {codes}]"


@dataclass(frozen=True)
class ExcludedView:
    title: str
    document_title: str
    codes: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class Source:
    """Everything a query reads, and an honest account of what this source cannot say."""

    name: str
    authorizations: tuple[AuthorizationView, ...]
    exclusions: tuple[ExcludedView, ...]
    records_exclusions: bool
    records_reference_chain: bool


@dataclass(frozen=True)
class Result:
    answer: Answer
    detail: str
    matched: tuple[AuthorizationView, ...]
    evidence: tuple[str, ...]

    @property
    def exit_code(self) -> int:
        return EXIT[self.answer]

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer.value,
            "detail": self.detail,
            "exit_code": self.exit_code,
            "matched": [
                {
                    "title": view.title,
                    "document_codes": list(view.document_codes),
                    "authorization_codes": list(view.codes),
                    "subject_codes_published": len(view.subjects),
                }
                for view in self.matched
            ],
            "evidence": list(self.evidence),
        }


# --- reading the two sources ---------------------------------------------------


def _english(value: Any) -> str:
    """A CTDL language map's en-US string, or the empty string when there is none."""
    if isinstance(value, dict):
        text = value.get("en-US")
        return text if isinstance(text, str) else ""
    return value if isinstance(value, str) else ""


def _identifier_values(node: dict[str, Any], scheme: str) -> tuple[str, ...]:
    values: list[str] = []
    for identifier in node.get("ceterms:identifier", []):
        if not isinstance(identifier, dict):
            continue
        if _english(identifier.get("ceterms:identifierTypeName")) != scheme:
            continue
        code = identifier.get("ceterms:identifierValueCode")
        if isinstance(code, str) and code.strip():
            values.append(code.strip())
    return tuple(values)


def source_from_graph(path: Path) -> Source:
    """Read ``site/credentials.jsonld``. Refuses a file it cannot read as that graph."""
    if not path.is_file():
        raise SourceUnreadable(f"{path}: no such file. Run `chalkline build` first.")
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        raise SourceUnreadable(f"{path}: the file is empty, so it publishes nothing")
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SourceUnreadable(f"{path}: not parseable JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("@graph"), list):
        raise SourceUnreadable(f"{path}: no @graph array, so this is not the graph")

    views: list[AuthorizationView] = []
    for node in document["@graph"]:
        if not isinstance(node, dict) or node.get("@type") != "ceterms:License":
            continue
        subjects = tuple(
            SubjectView(
                code=str(alignment.get("ceterms:codedNotation") or ""),
                name=_english(alignment.get("ceterms:targetNodeName")),
                notes=tuple(
                    line
                    for line in _english(alignment.get("ceterms:targetNodeDescription")).split("\n")
                    if line.strip()
                ),
            )
            for alignment in node.get("ceterms:subject", [])
            if isinstance(alignment, dict)
        )
        views.append(
            AuthorizationView(
                title=_english(node.get("ceterms:name")),
                document_codes=_identifier_values(node, DOCUMENT_CODE_SCHEME),
                codes=_identifier_values(node, AUTHORIZATION_CODE_SCHEME),
                subjects=subjects,
                resolution=None,
            )
        )
    if not views:
        raise SourceUnreadable(
            f"{path}: the graph carries no ceterms:License node. Answering from it would "
            "report every query as unknown, which is not the same as an empty answer."
        )
    return Source(
        name=str(path),
        authorizations=tuple(views),
        exclusions=(),
        records_exclusions=False,
        records_reference_chain=False,
    )


def _codes_of(authorization: Authorization) -> tuple[str, ...]:
    codes = list(authorization.authorization_codes)
    primary = authorization.authorization_code.strip()
    if primary and primary not in codes:
        codes.insert(0, primary)
    return tuple(codes)


def source_from_catalog(catalog: Catalog) -> Source:
    """The same shape, re-derived from the vendored Commission table."""
    views = tuple(
        AuthorizationView(
            title=authorization.title,
            document_codes=authorization.document_codes,
            codes=_codes_of(authorization),
            subjects=tuple(
                SubjectView(code=scope.code, name=scope.name, notes=scope.notes)
                for scope in authorization.subjects
            ),
            resolution=(
                None
                if authorization.resolved_from is None
                else (
                    f"the Commission's note {authorization.resolved_from.note!r} defers "
                    f"this scope to {authorization.resolved_from.credential!r} on "
                    f"{authorization.resolved_from.document_title!r}, whose rows "
                    f"{', '.join(s.authorization_code for s in authorization.resolved_from.sources)} "
                    f"supplied {authorization.resolved_from.subjects_supplied} subjects"
                )
            ),
        )
        for authorization in catalog.authorizations
    )
    exclusions = tuple(
        ExcludedView(
            title=excluded.title,
            document_title=excluded.document_title,
            codes=(excluded.authorization_code,),
            reason=excluded.reason,
        )
        for excluded in catalog.exclusions
    )
    return Source(
        name="the vendored Commission sort table",
        authorizations=views,
        exclusions=exclusions,
        records_exclusions=True,
        records_reference_chain=True,
    )


# --- the query -----------------------------------------------------------------


def _matches_document(view: AuthorizationView, wanted: str) -> bool:
    """Exact, case-insensitive, against the Document Title codes. Never against the title."""
    needle = wanted.casefold().strip()
    return any(needle == code.casefold() for code in view.document_codes)


def _matches_title(view: AuthorizationView, wanted: str) -> bool:
    """Substring, case-insensitive, against the Authorization Title."""
    return wanted.casefold().strip() in view.title.casefold()


def _find_subject(
    view: AuthorizationView, *, code: str | None, name: str | None
) -> SubjectView | None:
    for subject in view.subjects:
        if code is not None and subject.code.casefold() == code.casefold().strip():
            return subject
        if name is not None and subject.name.casefold() == name.casefold().strip():
            return subject
    return None


def _subject_is_published_anywhere(source: Source, *, code: str | None, name: str | None) -> bool:
    for view in source.authorizations:
        if _find_subject(view, code=code, name=name) is not None:
            return True
    return False


def _evidence(view: AuthorizationView, subject: SubjectView) -> tuple[str, ...]:
    lines = [
        f"row: {view.label()}",
        f"subject: {subject.code} {subject.name}",
    ]
    lines.extend(f"note: {note}" for note in subject.notes)
    if view.resolution:
        lines.append(f"resolved by cross-reference: {view.resolution}")
    return tuple(lines)


def ask(
    source: Source,
    *,
    code: str,
    subject_code: str | None = None,
    subject_name: str | None = None,
    document: str | None = None,
    title: str | None = None,
) -> Result:
    """Does this authorization carry this subject, according to this source?

    A pure function of a parsed source, so the tests can run it over sources it must
    report on rather than only over the committed pair.
    """
    if (subject_code is None) == (subject_name is None):
        raise ValueError("ask() needs exactly one of subject_code or subject_name")
    wanted = subject_code if subject_code is not None else subject_name
    if not code.strip():
        raise ValueError("ask() needs an authorization code to look for")

    matched = tuple(
        view
        for view in source.authorizations
        if any(existing.casefold() == code.casefold().strip() for existing in view.codes)
        and (document is None or _matches_document(view, document))
        and (title is None or _matches_title(view, title))
    )

    if not matched:
        excluded = [
            entry
            for entry in source.exclusions
            if any(c.casefold() == code.casefold().strip() for c in entry.codes)
            and (document is None or document.casefold().strip() == entry.document_title.casefold())
            and (title is None or title.casefold().strip() in entry.title.casefold())
        ]
        if excluded:
            entry = excluded[0]
            return Result(
                answer=Answer.NOT_MODELED,
                detail=(
                    f"{entry.title} [{entry.document_title}; {', '.join(entry.codes)}] "
                    "is published by the Commission and this project does not model it, "
                    "so the graph says nothing about it. That is a gap in this project, "
                    "not a fact about the Commission."
                ),
                matched=(),
                evidence=(f"recorded exclusion reason: {entry.reason}",),
            )
        narrowed = ", ".join(
            part
            for part in (
                f"Document Title code {document!r}" if document else "",
                f"Authorization Title containing {title!r}" if title else "",
            )
            if part
        )
        unknown = (
            f"no authorization with Authorization Code {code!r} is published in "
            f"{source.name}" + (f", narrowed to {narrowed}" if narrowed else "")
        )
        if not source.records_exclusions:
            unknown += (
                ". This source records no exclusions, so a row the Commission publishes "
                "and this project declined to model is indistinguishable here from one "
                "that does not exist. Re-run with --from-sources to tell them apart."
            )
        return Result(
            answer=Answer.UNKNOWN_AUTHORIZATION,
            detail=unknown,
            matched=(),
            evidence=(),
        )

    if len(matched) > 1:
        return Result(
            answer=Answer.AMBIGUOUS,
            detail=(
                f"{code!r} matches {len(matched)} authorizations. Narrow it with "
                "--document (the Document Title code, such as TC1) or --title (the "
                "Authorization Title); answering for one of them would be answering "
                "for the wrong one."
            ),
            matched=matched,
            evidence=tuple(view.label() for view in matched),
        )

    view = matched[0]
    found = _find_subject(view, code=subject_code, name=subject_name)
    if found is not None:
        return Result(
            answer=Answer.AUTHORIZES,
            detail=(
                f"{view.label()} carries the subject {found.code} {found.name}, as the "
                "Commission published it"
            ),
            matched=matched,
            evidence=_evidence(view, found),
        )

    if view.declares_no_subject_codes:
        return Result(
            answer=Answer.NOT_SUBJECT_CODED,
            detail=(
                f"{view.label()} publishes no subject codes at all, so the record does "
                f"not say whether it covers {wanted!r}. This is not a denial: the "
                "Commission codes subjects for some authorizations and not others."
            ),
            matched=matched,
            evidence=(f"row: {view.label()}", "subject codes published: none"),
        )

    if not _subject_is_published_anywhere(source, code=subject_code, name=subject_name):
        return Result(
            answer=Answer.UNKNOWN_SUBJECT,
            detail=(
                f"no subject {wanted!r} is published anywhere in {source.name}, so this "
                "is not a subject any authorization here could carry"
            ),
            matched=matched,
            evidence=(f"row: {view.label()}",),
        )

    published = ", ".join(sorted(subject.code for subject in view.subjects))
    return Result(
        answer=Answer.DOES_NOT_AUTHORIZE,
        detail=(
            f"{view.label()} publishes {len(view.subjects)} subject codes and "
            f"{wanted!r} is not among them"
        ),
        matched=matched,
        evidence=(f"row: {view.label()}", f"subject codes published: {published}"),
    )


def render_text(result: Result) -> str:
    lines = [f"{result.answer.value}: {result.detail}"]
    lines.extend(f"  {line}" for line in result.evidence)
    return "\n".join(lines) + "\n"


def render_json(result: Result) -> str:
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
