"""Project California credential authorizations into CTDL JSON-LD.

Nothing in this module is published to, drawn from, or claimed about any registry. It writes
files to disk. Class and property choices are justified in ``docs/MODELING.md`` and enforced
by :mod:`chalkline.ctdl.validate` against the vendored schema, so the justification and the
behaviour cannot drift apart.

The graph
---------

* One ``ceterms:CredentialOrganization`` for the Commission on Teacher Credentialing.
* One ``ceterms:License`` per modeled authorization. ``ceterms:License`` is the class whose
  published definition matches what these documents are: "Credential awarded by a government
  agency or other authorized organization that constitutes legal authority to do a specific
  job ... and are time-limited and must be renewed periodically." Every entry in the sort
  table, including the permits, is state-conferred legal authority to serve in a California
  public school position. ``ceterms:Certification`` was considered and rejected: CTDL
  separates it from License as a credential "awarded by an authoritative body for
  demonstrating the knowledge, skills, and abilities to perform specific tasks", which
  describes the assessments behind these documents rather than the documents themselves.
* Nested profiles carry the detail: ``ceterms:CredentialAlignmentObject`` for each subject,
  ``ceterms:JurisdictionProfile`` and ``ceterms:Place`` for California,
  ``ceterms:ConditionProfile`` for the requirements and renewal terms a matched leaflet
  states, ``ceterms:IdentifierValue`` for the Commission's own codes. None of these is a
  published resource in its own right, so none carries a CTID; the schema agrees, listing
  ``ctid`` in none of their domains.

Absence is meaningful throughout. A property appears only where a source supports it: no
description where neither a leaflet nor the Notes column published prose, no subject
alignments where the Commission published ``NONE``, no requirements where no leaflet was read
or where the leaflet states them under a heading this project does not classify, no
occupation or grade-level alignment at all (see ``docs/MODELING.md`` for why those two would
require inventing a mapping the Commission never wrote).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

from chalkline import ctid as ctid_module
from chalkline.attachment import Attachment
from chalkline.model import Authorization, Catalog
from chalkline.sources.leaflet_pages import Section
from chalkline.sources.sort_table import SOURCE_URL as SORT_TABLE_URL

CTDL_CONTEXT_URL: Final = "https://credreg.net/ctdl/schema/context/json"

RESOURCE_BASE: Final = "https://chalkline.chelseakr.com/ctdl/resources/"
"""Where ``@id`` URIs live: this project's own namespace.

Deliberately not ``credentialengineregistry.org``. A registry-shaped URI would imply these
records exist in the Credential Registry, and they do not.
"""

LANG: Final = "en-US"
"""Key for CTDL language maps. The context types ``ceterms:name`` and its relatives as
``@container: @language``, so a language tag is structurally required to say anything."""

ORGANIZATION_KEY: Final = "organization|Commission on Teacher Credentialing"
ORGANIZATION_NAME: Final = "Commission on Teacher Credentialing"
ORGANIZATION_WEBPAGE: Final = "https://www.ctc.ca.gov/"

ORGANIZATION_ADDRESS: Final = {
    "street": "651 Bannon Street",
    "locality": "Sacramento",
    "region": "California",
    "postal_code": "95811",
    "country": "United States",
}
"""The Commission's address as printed in the footer of the vendored sort table page.

Every value here is verbatim from that artifact except ``region`` and ``country``, which
expand the printed "CA" and the page's own "Official website of the State of California"
banner. ``tests/test_provenance.py`` asserts the printed strings are present in the vendored
file, so this constant cannot drift away from its source unnoticed.
"""

FRAMEWORK_NAME: Final = "California Commission on Teacher Credentialing Authorization Sort Table"

DOCUMENT_CODE_SCHEME: Final = "CTC Document Title code"
AUTHORIZATION_CODE_SCHEME: Final = "CTC Authorization Code"

DISCLAIMER_LEAD: Final = "Unofficial demonstration."
DISCLAIMER_BODY: Final = (
    "Chalkline is not published by, affiliated with, or endorsed by the California "
    "Commission on Teacher Credentialing or by Credential Engine. It models information the "
    "Commission publishes on its public Authorization Sort Table, to show what a "
    "machine-readable representation of California educator credentials could look like. "
    "Nothing here has been published to the Credential Registry, and these CTIDs are not "
    "Registry-assigned."
)
DISCLAIMER: Final = f"{DISCLAIMER_LEAD} {DISCLAIMER_BODY}"
"""Carried whole in the JSON-LD and the coverage statement; the page renders the lead in
bold and the body after it, so the statement is never doubled up."""

JURISDICTION_DESCRIPTION: Final = (
    "The Commission on Teacher Credentialing issues and regulates these credentials for "
    "service in California public schools."
)

GRAPH_FILENAME: Final = "credentials.jsonld"
COVERAGE_FILENAME: Final = "coverage.json"


def _lang(text: str) -> dict[str, str]:
    return {LANG: text}


def _iri(ctid: str) -> str:
    return RESOURCE_BASE + ctid


def california_jurisdiction() -> dict[str, Any]:
    """The ``ceterms:regulatedIn`` value: California, as a jurisdiction profile.

    ``ceterms:regulatedIn`` is "Region or political jurisdiction such as a state, province
    or locale in which the credential ... is regulated", which is precisely the Commission's
    relationship to these documents. ``ceterms:recognizedIn`` would say something weaker and
    different (publicly recommended or endorsed), and the broader ``ceterms:jurisdiction``
    would drop the regulatory fact the source establishes.
    """
    return {
        "@type": "ceterms:JurisdictionProfile",
        "ceterms:description": _lang(JURISDICTION_DESCRIPTION),
        "ceterms:mainJurisdiction": {
            "@type": "ceterms:Place",
            "ceterms:name": _lang("California"),
            "ceterms:addressRegion": _lang("California"),
            "ceterms:addressCountry": _lang("United States"),
        },
    }


def project_organization(ctid: str) -> dict[str, Any]:
    """The Commission as a ``ceterms:CredentialOrganization``.

    The class is "Organization that plays one or more key roles in the lifecycle of a
    credential", which is the role the source establishes: the Commission issues and
    regulates every document in the table. The Commission is also a quality assurance body
    for educator preparation programs, and ``ceterms:QACredentialOrganization`` would be the
    class for that role, but this export models no preparation programs and so asserts no
    quality assurance relationship.
    """
    return {
        "@type": "ceterms:CredentialOrganization",
        "@id": _iri(ctid),
        "ceterms:ctid": ctid,
        "ceterms:name": _lang(ORGANIZATION_NAME),
        "ceterms:subjectWebpage": ORGANIZATION_WEBPAGE,
        "ceterms:address": [
            {
                "@type": "ceterms:Place",
                "ceterms:streetAddress": _lang(ORGANIZATION_ADDRESS["street"]),
                "ceterms:addressLocality": _lang(ORGANIZATION_ADDRESS["locality"]),
                "ceterms:addressRegion": _lang(ORGANIZATION_ADDRESS["region"]),
                # Not a language map: the schema gives postalCode range xsd:string, unlike
                # the address lines around it. The validator caught this one.
                "ceterms:postalCode": ORGANIZATION_ADDRESS["postal_code"],
                "ceterms:addressCountry": _lang(ORGANIZATION_ADDRESS["country"]),
            }
        ],
    }


def _identifiers(authorization: Authorization) -> list[dict[str, Any]]:
    """The Commission's own codes, as ``ceterms:IdentifierValue`` nodes.

    The obvious-looking home for a code like ``R1E`` is ``ceterms:codedNotation``, and the
    schema does not allow it: that property's domain does not include ``ceterms:License``.
    ``ceterms:identifier`` does, and its ``IdentifierValue`` range carries both the code and
    the name of the scheme it belongs to, which is more information rather than less.
    """
    values: list[dict[str, Any]] = []
    for code in authorization.document_codes:
        values.append(
            {
                "@type": "ceterms:IdentifierValue",
                "ceterms:identifierTypeName": _lang(DOCUMENT_CODE_SCHEME),
                "ceterms:identifierValueCode": code,
            }
        )
    for code in authorization.authorization_codes:
        values.append(
            {
                "@type": "ceterms:IdentifierValue",
                "ceterms:identifierTypeName": _lang(AUTHORIZATION_CODE_SCHEME),
                "ceterms:identifierValueCode": code,
            }
        )
    return values


def _subjects(authorization: Authorization) -> list[dict[str, Any]]:
    """Each authorized subject as a ``ceterms:CredentialAlignmentObject``.

    The alignment names the framework it points into (the sort table itself), the
    Commission's subject code, and the Commission's subject name. Row-level notes ride
    ``ceterms:targetNodeDescription``, which is defined as the "textual description of an
    individual entry in a formally defined framework that is the target of an alignment" and
    is exactly what those notes are. Notes are a bulleted list on the source page, and they
    are joined with newlines here rather than run together into a sentence.
    """
    alignments: list[dict[str, Any]] = []
    for scope in authorization.subjects:
        alignment: dict[str, Any] = {
            "@type": "ceterms:CredentialAlignmentObject",
            "ceterms:framework": SORT_TABLE_URL,
            "ceterms:frameworkName": _lang(FRAMEWORK_NAME),
            "ceterms:codedNotation": scope.code,
            "ceterms:targetNodeName": _lang(scope.name),
        }
        if scope.notes:
            alignment["ceterms:targetNodeDescription"] = _lang("\n".join(scope.notes))
        alignments.append(alignment)
    return alignments


def _conditions(sections: Sequence[Section], webpage: str) -> list[dict[str, Any]]:
    """A leaflet's classified sections as ``ceterms:ConditionProfile`` nodes.

    ``ceterms:condition`` is "Single constraint, prerequisite, entry condition, requirement,
    or cost", singular, so one of the Commission's paragraphs or bullets is one condition
    rather than the whole section being one blob. The profile keeps the Commission's own
    heading as its name and carries the leaflet URL, because the leaflet states more about
    these conditions than this project reads from it.
    """
    return [
        {
            "@type": "ceterms:ConditionProfile",
            "ceterms:name": _lang(section.heading),
            "ceterms:condition": {LANG: list(section.blocks)},
            "ceterms:subjectWebpage": webpage,
        }
        for section in sections
        if section.blocks
    ]


def description_of(authorization: Authorization, attachment: Attachment | None) -> tuple[str, ...]:
    """The prose this export publishes as ``ceterms:description``, and where it came from.

    A matched leaflet's own prose is preferred over the sort table's Notes column, because
    the leaflet describes the credential and the Notes describe rows of a table. Where the
    leaflet yields nothing the Notes stand, and where neither yields anything the property
    is absent: this project composes no description of its own.
    """
    if attachment is not None and attachment.description:
        return attachment.description
    return authorization.shared_notes


def project_license(
    authorization: Authorization,
    ctid: str,
    organization_iri: str,
    attachment: Attachment | None,
) -> dict[str, Any]:
    """One authorization as one ``ceterms:License``.

    ``ceterms:ownedBy`` names the Commission: "Agent with an enforceable claim or legal
    title to the resource" is what a state licensing body has over the credentials it
    confers.

    ``ceterms:requires`` and ``ceterms:renewal`` appear only where a matched leaflet heads a
    section this project can classify. Both are in the domain of ``ceterms:License`` and
    both take a ``ceterms:ConditionProfile``; ``ceterms:renewal`` is defined as the
    conditions "necessary to maintenance and renewal of an awarded credential", which is
    what the Commission's Period of Validity, Term of the Credential, and Renewal sections
    state. Nothing is emitted from a section this project did not classify.
    """
    entity: dict[str, Any] = {
        "@type": "ceterms:License",
        "@id": _iri(ctid),
        "ceterms:ctid": ctid,
        "ceterms:name": _lang(authorization.title),
    }
    description = description_of(authorization, attachment)
    if description:
        entity["ceterms:description"] = _lang("\n".join(description))
    entity["ceterms:inLanguage"] = [LANG]
    entity["ceterms:subjectWebpage"] = webpage_for(attachment)
    entity["ceterms:ownedBy"] = [organization_iri]
    entity["ceterms:regulatedIn"] = [california_jurisdiction()]
    identifiers = _identifiers(authorization)
    if identifiers:
        entity["ceterms:identifier"] = identifiers
    if attachment is not None:
        requires = _conditions(attachment.requirements, attachment.leaflet.url)
        if requires:
            entity["ceterms:requires"] = requires
        renewal = _conditions(attachment.renewal, attachment.leaflet.url)
        if renewal:
            entity["ceterms:renewal"] = renewal
    subjects = _subjects(authorization)
    if subjects:
        entity["ceterms:subject"] = subjects
    return entity


def webpage_for(attachment: Attachment | None) -> str:
    """The authoritative page for an authorization.

    The matched leaflet where the Commission's index named one, and otherwise the sort
    table, which is the page that does describe the authorization alongside the others. A
    leaflet whose page could not be read still supplies this link: the index made that
    association and this project is only declining to read the page's prose.
    """
    return SORT_TABLE_URL if attachment is None else attachment.leaflet.url


def project_graph(
    catalog: Catalog,
    ctids: Mapping[str, str],
    attachments: Mapping[str, Attachment],
) -> dict[str, Any]:
    """The whole export as one JSON-LD graph document.

    Entity order is the Commission's own publication order, with the organization first, so
    the same source artifact always serializes to the same bytes.

    The top-level ``comment`` key is not a CTDL term and a JSON-LD processor will drop it.
    That is the point: it carries the unofficial-demonstration statement for a human who
    opens the file on its own, without asserting anything into the graph.
    """
    organization_ctid = ctid_module.require(ORGANIZATION_KEY, ctids)
    organization_iri = _iri(organization_ctid)
    graph: list[dict[str, Any]] = [project_organization(organization_ctid)]
    for authorization in catalog.authorizations:
        graph.append(
            project_license(
                authorization,
                ctid_module.require(authorization.key, ctids),
                organization_iri,
                attachments.get(authorization.key),
            )
        )
    return {"@context": CTDL_CONTEXT_URL, "comment": DISCLAIMER, "@graph": graph}


LICENSE_PROPERTIES: Final = (
    "ceterms:ctid",
    "ceterms:name",
    "ceterms:description",
    "ceterms:inLanguage",
    "ceterms:subjectWebpage",
    "ceterms:ownedBy",
    "ceterms:regulatedIn",
    "ceterms:identifier",
    "ceterms:requires",
    "ceterms:renewal",
    "ceterms:subject",
)
"""License properties the coverage statement counts, in emission order.

Hand-kept, and therefore checked: :func:`census_problems` fails the build if the export
emits a property on a licence that this tuple does not name, because a census that quietly
stops counting a property is worse than no census.
"""

LEAFLET_RULE: Final = (
    "a leaflet is attached only where its published title equals the authorization's "
    "published title after case and punctuation normalization, or equals that title with "
    "one trailing parenthesised qualifier removed; and its prose is read only where the "
    "leaflet page's own heading states the code and the title the index gave it"
)


def _leaflet_coverage(catalog: Catalog, attachments: Mapping[str, Attachment]) -> dict[str, Any]:
    """What the leaflets gave and did not give, counted from the attachments themselves."""
    attached = [attachments[a.key] for a in catalog.authorizations if a.key in attachments]
    by_rule: dict[str, int] = {}
    for attachment in attached:
        by_rule[attachment.match.rule] = by_rule.get(attachment.match.rule, 0) + 1
    refusals: dict[str, int] = {}
    for attachment in attached:
        if attachment.refusal is not None:
            refusals[attachment.refusal] = refusals.get(attachment.refusal, 0) + 1
    skipped: dict[str, int] = {}
    for attachment in attached:
        for heading in attachment.page.skipped_headings if attachment.page else ():
            skipped[heading] = skipped.get(heading, 0) + 1
    return {
        "rule": LEAFLET_RULE,
        "leaflets_in_the_commission_index": None,
        "authorizations_with_a_leaflet": len(attached),
        "authorizations_without_a_leaflet": len(catalog.authorizations) - len(attached),
        "matched_by_rule": dict(sorted(by_rule.items())),
        "leaflet_pages_read": len({a.leaflet.code for a in attached if a.page is not None}),
        "leaflet_pages_refused": len({a.leaflet.code for a in attached if a.page is None}),
        "authorizations_with_leaflet_prose": sum(1 for a in attached if a.description),
        "refused_by_reason": dict(sorted(refusals.items())),
        "headings_read_past_but_not_classified": dict(sorted(skipped.items())),
    }


def coverage(
    document: Mapping[str, Any],
    catalog: Catalog,
    attachments: Mapping[str, Attachment],
    leaflets_published: int,
) -> dict[str, Any]:
    """The coverage statement published beside the export, counted from the export itself.

    Every figure is derived from the artifact it describes at the moment of writing, and
    :func:`coverage_problems` recomputes the lot before anything is written, so a number the
    export contradicts cannot ship. ``not_modeled`` names what the source carries that this
    export deliberately does not, with reasons.
    """
    graph: list[Mapping[str, Any]] = list(document.get("@graph", []))
    licenses = [e for e in graph if e.get("@type") == "ceterms:License"]
    organizations = [e for e in graph if e.get("@type") == "ceterms:CredentialOrganization"]
    alignments = [a for e in licenses for a in e.get("ceterms:subject", [])]
    conditions = [
        c
        for e in licenses
        for term in ("ceterms:requires", "ceterms:renewal")
        for c in e.get(term, [])
    ]
    resolved = [a for a in catalog.authorizations if a.resolved_from is not None]
    reasons: dict[str, int] = {}
    for exclusion in catalog.exclusions:
        reasons[exclusion.reason] = reasons.get(exclusion.reason, 0) + 1
    leaflet_counts = _leaflet_coverage(catalog, attachments)
    leaflet_counts["leaflets_in_the_commission_index"] = leaflets_published
    return {
        "note": DISCLAIMER,
        "source": {
            "authorization_sort_table": SORT_TABLE_URL,
            "retrieved": "2026-08-07",
            "rows_published": catalog.source_rows,
        },
        "entities": {
            "ceterms:CredentialOrganization": len(organizations),
            "ceterms:License": len(licenses),
            "ceterms:CredentialAlignmentObject": len(alignments),
            "ceterms:ConditionProfile": len(conditions),
        },
        "authorizations": {
            "published_in_source": len(catalog.authorizations) + len(catalog.exclusions),
            "modeled": len(catalog.authorizations),
            "excluded": len(catalog.exclusions),
            "with_subject_codes": sum(1 for a in catalog.authorizations if a.subjects),
            # The union, not the sum. Some authorizations carry both, so adding the two
            # property counts together counts those twice, and this is the figure the page
            # prints under "carrying requirements or renewal terms".
            "with_requirements_or_renewal_terms": sum(
                1 for e in licenses if "ceterms:requires" in e or "ceterms:renewal" in e
            ),
            "published_as_not_subject_coded": sum(
                1 for a in catalog.authorizations if a.declares_no_subject_codes
            ),
            "scope_resolved_by_cross_reference": len(resolved),
            "subject_alignments_from_a_cross_reference": sum(len(a.subjects) for a in resolved),
        },
        "license_properties": {
            term: sum(1 for e in licenses if term in e) for term in LICENSE_PROPERTIES
        },
        "leaflets": leaflet_counts,
        "excluded_by_reason": dict(sorted(reasons.items())),
        "not_modeled": {
            "ceterms:occupationType": (
                "the sort table publishes no occupation codes, and aligning a credential to "
                "an SOC occupation would be this project's judgement rather than the "
                "Commission's statement"
            ),
            "ceterms:audienceLevelType": (
                "grade ranges appear as prose in the Notes column; mapping that prose onto "
                "CTDL's audience level concept scheme would be an interpretation the "
                "Commission has not published"
            ),
            "competency_framework": (
                "the sort table publishes subject names, not competency statements, and "
                "CTDL's targetCompetency is not in the domain of ceterms:License; modeling "
                "subjects as competencies would require writing skill statements the "
                "Commission never wrote"
            ),
            "leaflet_sections_this_project_cannot_classify": (
                "a leaflet section whose heading is not one of the kinds this project "
                "recognises is never read, and reading stops entirely at the first heading "
                "that names another document, so a leaflet describing several credentials "
                "contributes only the part it is titled for"
            ),
        },
    }


def census_problems(document: Mapping[str, Any]) -> list[str]:
    """Every property the export puts on a License that the census does not count.

    :data:`LICENSE_PROPERTIES` is the one hand-kept list left in the coverage statement, and
    a hand-kept list of what the code emits is exactly the thing that goes quietly out of
    date. Adding a property to :func:`project_license` without adding it here would leave
    the published census silently short by one, so this makes that a build failure.
    """
    graph: Sequence[Any] = document.get("@graph", [])
    emitted = {
        term
        for entity in graph
        if isinstance(entity, Mapping) and entity.get("@type") == "ceterms:License"
        for term in entity
        if not term.startswith("@")
    }
    return [
        f"license_properties does not count {term}, which the export emits on a License"
        for term in sorted(emitted - set(LICENSE_PROPERTIES))
    ]


def coverage_problems(
    statement: Mapping[str, Any],
    document: Mapping[str, Any],
    catalog: Catalog,
    attachments: Mapping[str, Attachment],
    leaflets_published: int,
) -> list[str]:
    """Every way a coverage statement fails to describe the export beside it.

    Two different questions, and only the census has teeth at build time.
    :func:`census_problems` asks whether the statement's shape still covers what the export
    emits, which does not depend on where the statement came from. The figure-by-figure
    comparison that follows it asks whether a statement written elsewhere agrees with a
    freshly counted one, which catches a stale committed statement but is a tautology when
    the caller has just produced the statement from these same inputs.
    """
    expected = coverage(document, catalog, attachments, leaflets_published)
    return census_problems(document) + [
        f"{key}: says {statement.get(key)!r}, the export gives {expected[key]!r}"
        for key in expected
        if statement.get(key) != expected[key]
    ]


def check_coverage(
    statement: Mapping[str, Any],
    document: Mapping[str, Any],
    catalog: Catalog,
    attachments: Mapping[str, Attachment],
    leaflets_published: int,
) -> None:
    """Refuse to publish a coverage statement the export contradicts."""
    problems = coverage_problems(statement, document, catalog, attachments, leaflets_published)
    if problems:
        raise ValueError(
            "coverage statement does not describe the export beside it: " + "; ".join(problems)
        )


def serialize(document: Mapping[str, Any]) -> str:
    """One canonical serialization, so determinism is a property rather than a habit."""
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"
