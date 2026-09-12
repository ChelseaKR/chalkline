"""The inverse view: which credentials authorize a subject.

``site/index.html`` is organised by authorization, which answers the question a
credential holder asks. An assignment clerk asks the other one: which credentials
authorize teaching Biological Sciences (Specialized)? The 1,014 subject alignments
already carry the answer and the Commission does not publish it in that shape.

These pages present it and infer nothing. A subject appears against an authorization
only where the sort table publishes it on that authorization's own rows, or where a
cross-reference this project can follow supplies it, and where it arrived that way the
page says so and names the credential it came from. The row notes are reproduced as the
Commission published them. Nothing here is composed by this project, and no page states
what a holder "may be assigned": that is a judgement, and quoting rows is not.

Three kinds of page, all self-contained on the same inline stylesheet as the main page:

``subjects/index.html``            every code, its published name or names, and how many
                                   authorizations reach it.
``subjects/<CODE>.html``           one code, and every authorization the graph aligns to it.
``subjects/not-subject-coded.html``the authorizations the Commission publishes ``NONE``
                                   against, kept apart from the ones whose scope was never
                                   published at all.

That last separation is the point of a separate page rather than an empty one. An
authorization the Commission marked ``NONE`` is a published fact about its scope. An
authorization whose scope this project could not read is not modeled at all and is listed,
with its reason, in the exclusions table on the main page. Collapsing the two would publish
a silence as a statement.

A code that carries two published names keeps both. The sort table spells ``Theater`` and
``Introductory Theater`` against ``THTR``, and picking one would be this project choosing
which of the Commission's strings is the real one.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Final

from chalkline.ctdl.export import DISCLAIMER_BODY, DISCLAIMER_LEAD
from chalkline.model import Authorization, Catalog, SubjectScope
from chalkline.site import SITE_URL, STYLE, _e
from chalkline.sources.sort_table import SOURCE_URL as SORT_TABLE_URL

#: The directory these pages are published under, relative to ``site/``.
DIRECTORY: Final = "subjects"

INDEX_FILENAME: Final = f"{DIRECTORY}/index.html"
NOT_SUBJECT_CODED_FILENAME: Final = f"{DIRECTORY}/not-subject-coded.html"

#: The shape a subject code must have before it becomes a filename.
#:
#: A path assembled from source data is a path the Commission decides, and every code it
#: publishes today is short and alphanumeric. Rather than trust that, the shape is asserted
#: and a code outside it stops the build: a code carrying a dot, a slash or a space would
#: otherwise write outside the directory, collide with a sibling, or produce a link no
#: browser resolves. Refusing is the honest failure; sanitising would publish a page under
#: a name the Commission never used.
CODE_SHAPE: Final = re.compile(r"[A-Z0-9]{1,16}")


class UnpublishableCode(ValueError):
    """A subject code that cannot become a filename, named rather than sanitised."""


@dataclass(frozen=True, slots=True)
class Reach:
    """One authorization a subject code reaches, and the row that put it there."""

    authorization: Authorization
    scope: SubjectScope

    @property
    def by_cross_reference(self) -> bool:
        """Whether this alignment arrived through a followed cross-reference."""
        return self.authorization.resolved_from is not None


@dataclass(frozen=True, slots=True)
class Subject:
    """One subject code, every name published for it, and everything it reaches."""

    code: str
    names: tuple[str, ...]
    reaches: tuple[Reach, ...]

    @property
    def filename(self) -> str:
        return f"{DIRECTORY}/{self.code}.html"


def group(catalog: Catalog) -> tuple[Subject, ...]:
    """Every subject code in the catalog, in the order the sort table publishes them.

    Ordering is by code so the published set is stable under a re-fetch that reorders
    rows. Names are kept in first-seen order and never merged; see the module docstring.
    """
    names: OrderedDict[str, list[str]] = OrderedDict()
    reaches: OrderedDict[str, list[Reach]] = OrderedDict()
    for authorization in catalog.authorizations:
        for scope in authorization.subjects:
            seen = names.setdefault(scope.code, [])
            if scope.name not in seen:
                seen.append(scope.name)
            reaches.setdefault(scope.code, []).append(Reach(authorization, scope))
    return tuple(Subject(code, tuple(names[code]), tuple(reaches[code])) for code in sorted(names))


def not_subject_coded(catalog: Catalog) -> tuple[Authorization, ...]:
    """The authorizations the Commission publishes ``NONE`` against."""
    return tuple(a for a in catalog.authorizations if a.declares_no_subject_codes)


def _refuse_unpublishable(subjects: tuple[Subject, ...]) -> None:
    bad = [s.code for s in subjects if not CODE_SHAPE.fullmatch(s.code)]
    if bad:
        raise UnpublishableCode(
            "these subject codes cannot be published as filenames without renaming them, "
            f"which this project will not do: {bad}"
        )


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def _document(title: str, canonical: str, description: str, body: str) -> str:
    """The shared shell. One file, one inline stylesheet, nothing fetched."""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<meta name="description" content="{_e(description)}">
<link rel="canonical" href="{_e(SITE_URL + canonical)}">
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>{_e(title)}</h1>
<p class="notice"><strong>{_e(DISCLAIMER_LEAD)}</strong> {_e(DISCLAIMER_BODY)}</p>
{body}
<footer>
<p>Chalkline is an independent demonstration by Chelsea Kelly-Reif. It is not affiliated
with, endorsed by, or published by the California Commission on Teacher Credentialing or
Credential Engine. Nothing here has been published to the Credential Registry.</p>
</footer>
</main>
</body>
</html>
"""


def _sort_table_link() -> str:
    return f'<a href="{_e(SORT_TABLE_URL)}">Authorization Sort Table</a>'


def _notes_block(scope: SubjectScope) -> str:
    """The Notes column for this row, as published, or a statement that it is empty."""
    if not scope.notes:
        return (
            '<p class="from">The Commission publishes no note against this subject on this '
            "authorization's rows.</p>"
        )
    items = "".join(f"<li>{_e(note)}</li>" for note in scope.notes)
    return f'<ul class="conditions">{items}</ul>'


def _reached_by(reach: Reach) -> str:
    """Where this alignment came from, when it did not come from the rows themselves."""
    resolution = reach.authorization.resolved_from
    if resolution is None:
        return '<p class="from">Published on this authorization\'s own rows in the sort table.</p>'
    return (
        '<p class="from">Reached by following a cross-reference. The Commission publishes no '
        "subjects on this authorization's own rows; its note reads &ldquo;"
        f"{_e(resolution.note)}&rdquo;, and this subject is one the table publishes for "
        f"<b>{_e(resolution.credential)}</b> on document "
        f"<code>{_e(resolution.document_title)}</code>.</p>"
    )


def _reach_block(reach: Reach) -> str:
    authorization = reach.authorization
    meta = [f"document <code>{_e(authorization.document_title)}</code>"]
    if authorization.authorization_code:
        meta.append(f"authorization <code>{_e(authorization.authorization_code)}</code>")
    return (
        '<article class="cred">'
        f"<h3>{_e(authorization.title)}</h3>"
        f'<p class="meta">{" &middot; ".join(meta)}</p>'
        f"{_reached_by(reach)}"
        f"{_notes_block(reach.scope)}"
        f'<p class="meta">{_sort_table_link()}</p>'
        "</article>"
    )


def _names_sentence(subject: Subject) -> str:
    if len(subject.names) == 1:
        return ""
    spellings = ", ".join(f"&ldquo;{_e(name)}&rdquo;" for name in subject.names)
    return (
        f'<p class="from">The sort table publishes {len(subject.names)} names against this '
        f"code: {spellings}. Both are kept; choosing between them would be this project "
        "deciding which of the Commission's strings is the real one.</p>"
    )


def render_subject(subject: Subject) -> str:
    """One code, and every modeled authorization the graph aligns to it."""
    count = len(subject.reaches)
    noun, verb = ("authorization", "authorizes") if count == 1 else ("authorizations", "authorize")
    resolved = sum(1 for reach in subject.reaches if reach.by_cross_reference)
    crossed = (
        f" {resolved} of them reached the subject through a followed cross-reference "
        "rather than through its own rows, and each one says so and names the credential "
        "the rows belong to."
        if resolved
        else ""
    )
    body = (
        f"<p>Every modeled authorization below carries subject code <code>{_e(subject.code)}"
        "</code> in the Commission's published "
        f"{_sort_table_link()}, retrieved 2026-08-07.{crossed} Nothing on this page is "
        "inferred: an authorization appears only where a published row, or a cross-reference "
        "this project can follow, puts the code on it. Which assignments a credential "
        "permits is a judgement, and this project makes none: it quotes rows.</p>"
        f"{_names_sentence(subject)}"
        f'<p class="meta"><a href="index.html">All subject codes</a> &middot; '
        '<a href="../index.html">Modeled credentials</a></p>'
        f"<h2>{count} {noun} {verb} this subject</h2>"
        + "".join(_reach_block(reach) for reach in subject.reaches)
    )
    return _document(
        title=f"Subject code {subject.code}: {' / '.join(subject.names)}",
        canonical=subject.filename,
        description=(
            f"The California educator credential authorizations that carry subject code "
            f"{subject.code} in the Commission's published Authorization Sort Table."
        ),
        body=body,
    )


def render_index(subjects: tuple[Subject, ...], uncoded: int) -> str:
    """Every code, with its published name or names and how many authorizations reach it."""
    rows = "".join(
        "<tr>"
        f'<td><a href="{_e(subject.code)}.html"><code>{_e(subject.code)}</code></a></td>'
        f"<td>{_e(' / '.join(subject.names))}</td>"
        f"<td>{len(subject.reaches)}</td>"
        "</tr>"
        for subject in subjects
    )
    alignments = sum(len(subject.reaches) for subject in subjects)
    counts = "".join(
        f"<li><b>{value}</b><span>{_e(label)}</span></li>"
        for value, label in (
            (len(subjects), "distinct subject codes"),
            (alignments, "subject alignments across them"),
            (uncoded, "authorizations published as not subject-coded"),
        )
    )
    body = (
        "<p>The main page is organised by credential. This is the inverse: for each subject "
        "code the Commission publishes in its "
        f"{_sort_table_link()}, the credentials that authorize it. Every figure here is "
        "counted from the same catalog the graph is built from.</p>"
        f'<p class="meta"><a href="../index.html">Modeled credentials</a> &middot; '
        f'<a href="{_e(NOT_SUBJECT_CODED_FILENAME.split("/")[-1])}">Not subject-coded</a>'
        "</p>"
        f'<ul class="counts" role="list">{counts}</ul>'
        f"<h2>{len(subjects)} subject codes</h2>"
        '<div class="wrap" role="region" aria-label="Subject codes" tabindex="0">'
        "<table><thead><tr>"
        '<th scope="col">Code</th><th scope="col">Name as published</th>'
        '<th scope="col">Authorizations</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )
    return _document(
        title="Subjects, and which California credentials authorize them",
        canonical=INDEX_FILENAME,
        description=(
            "Every subject code in the Commission's published Authorization Sort Table, "
            "with the modeled educator credential authorizations that carry it."
        ),
        body=body,
    )


def render_not_subject_coded(uncoded: tuple[Authorization, ...]) -> str:
    """The authorizations the Commission publishes ``NONE`` against, on their own page."""
    rows = "".join(
        "<tr>"
        f"<td>{_e(authorization.title)}</td>"
        f"<td><code>{_e(authorization.document_title)}</code></td>"
        f"<td><code>{_e(authorization.authorization_code) or '&mdash;'}</code></td>"
        "</tr>"
        for authorization in uncoded
    )
    body = (
        "<p>The Commission publishes <code>NONE</code> in the Subject Code column for each "
        "authorization below. That is a published statement about scope, and it is why "
        "these are on a page of their own rather than folded in with an empty result.</p>"
        "<p>They are not the same as an authorization whose scope the Commission did not "
        "publish in a form this project can read. Those are not modeled at all, and each is "
        'listed with its reason in the exclusions table on the <a href="../index.html">main '
        "page</a>.</p>"
        f'<p class="meta"><a href="index.html">All subject codes</a> &middot; '
        f"{_sort_table_link()}</p>"
        f"<h2>{len(uncoded)} authorizations</h2>"
        '<div class="wrap" role="region" aria-label="Authorizations published as not '
        'subject-coded" tabindex="0">'
        "<table><thead><tr>"
        '<th scope="col">Authorization</th><th scope="col">Document</th>'
        '<th scope="col">Code</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )
    return _document(
        title="California credential authorizations published as not subject-coded",
        canonical=NOT_SUBJECT_CODED_FILENAME,
        description=(
            "The modeled California educator credential authorizations for which the "
            "Commission publishes NONE in the Subject Code column."
        ),
        body=body,
    )


def pages(catalog: Catalog) -> dict[str, str]:
    """Every subject page, keyed by its path under ``site/``."""
    subjects = group(catalog)
    _refuse_unpublishable(subjects)
    uncoded = not_subject_coded(catalog)
    written = {subject.filename: render_subject(subject) for subject in subjects}
    written[INDEX_FILENAME] = render_index(subjects, len(uncoded))
    written[NOT_SUBJECT_CODED_FILENAME] = render_not_subject_coded(uncoded)
    return written


def census(catalog: Catalog) -> dict[str, int]:
    """The counted statement about these pages, for ``coverage.json``."""
    subjects = group(catalog)
    return {
        "distinct_codes": len(subjects),
        "alignments": sum(len(subject.reaches) for subject in subjects),
        "codes_with_more_than_one_published_name": sum(
            1 for subject in subjects if len(subject.names) > 1
        ),
        "alignments_reached_by_cross_reference": sum(
            1 for subject in subjects for reach in subject.reaches if reach.by_cross_reference
        ),
        "authorizations_published_as_not_subject_coded": len(not_subject_coded(catalog)),
        "pages_published": len(subjects) + 2,
    }
