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
  ``ceterms:IdentifierValue`` for the Commission's own codes. None of these is a published
  resource in its own right, so none carries a CTID; the schema agrees, listing ``ctid`` in
  none of their domains.

Absence is meaningful throughout. A property appears only where the sort table supports it:
no description where the Commission published no prose, no subject alignments where it
published ``NONE``, no occupation or grade-level alignment at all (see ``docs/MODELING.md``
for why those two would require inventing a mapping the Commission never wrote).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from chalkline import ctid as ctid_module
from chalkline.model import Authorization, Catalog
from chalkline.sources import leaflets as leaflets_module
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


def project_license(
    authorization: Authorization,
    ctid: str,
    organization_iri: str,
    webpage: str,
) -> dict[str, Any]:
    """One authorization as one ``ceterms:License``.

    ``ceterms:ownedBy`` names the Commission: "Agent with an enforceable claim or legal
    title to the resource" is what a state licensing body has over the credentials it
    confers. ``ceterms:description`` appears only where every row of the authorization
    carries the same note list, meaning the Commission wrote prose about the authorization
    rather than about one of its subjects; the sort table publishes no free-text description
    of a credential, and this project does not compose one.
    """
    entity: dict[str, Any] = {
        "@type": "ceterms:License",
        "@id": _iri(ctid),
        "ceterms:ctid": ctid,
        "ceterms:name": _lang(authorization.title),
    }
    if authorization.shared_notes:
        entity["ceterms:description"] = _lang("\n".join(authorization.shared_notes))
    entity["ceterms:inLanguage"] = [LANG]
    entity["ceterms:subjectWebpage"] = webpage
    entity["ceterms:ownedBy"] = [organization_iri]
    entity["ceterms:regulatedIn"] = [california_jurisdiction()]
    identifiers = _identifiers(authorization)
    if identifiers:
        entity["ceterms:identifier"] = identifiers
    subjects = _subjects(authorization)
    if subjects:
        entity["ceterms:subject"] = subjects
    return entity


def webpage_for(
    authorization: Authorization, leaflet_index: Mapping[str, leaflets_module.Leaflet]
) -> tuple[str, leaflets_module.Leaflet | None]:
    """The authoritative page for an authorization, and the leaflet behind it if there is one.

    A leaflet is used only on an exact normalized title match (see
    :mod:`chalkline.sources.leaflets`). Otherwise the subject webpage is the sort table,
    which is the page that does describe the authorization, alongside the others.
    """
    leaflet = leaflet_index.get(leaflets_module.normalize_title(authorization.title))
    return (leaflet.url if leaflet else SORT_TABLE_URL), leaflet


def project_graph(
    catalog: Catalog,
    ctids: Mapping[str, str],
    leaflet_index: Mapping[str, leaflets_module.Leaflet],
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
        webpage, _ = webpage_for(authorization, leaflet_index)
        graph.append(
            project_license(
                authorization,
                ctid_module.require(authorization.key, ctids),
                organization_iri,
                webpage,
            )
        )
    return {"@context": CTDL_CONTEXT_URL, "comment": DISCLAIMER, "@graph": graph}


LICENSE_PROPERTIES: Final = (
    "ceterms:name",
    "ceterms:description",
    "ceterms:inLanguage",
    "ceterms:subjectWebpage",
    "ceterms:ownedBy",
    "ceterms:regulatedIn",
    "ceterms:identifier",
    "ceterms:subject",
)
"""License properties the coverage statement counts, in emission order."""


def coverage(
    document: Mapping[str, Any],
    catalog: Catalog,
    leaflet_index: Mapping[str, leaflets_module.Leaflet],
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
    matched = [
        a
        for a in catalog.authorizations
        if leaflets_module.normalize_title(a.title) in leaflet_index
    ]
    reasons: dict[str, int] = {}
    for exclusion in catalog.exclusions:
        reasons[exclusion.reason] = reasons.get(exclusion.reason, 0) + 1
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
        },
        "authorizations": {
            "published_in_source": len(catalog.authorizations) + len(catalog.exclusions),
            "modeled": len(catalog.authorizations),
            "excluded": len(catalog.exclusions),
            "with_subject_codes": sum(1 for a in catalog.authorizations if a.subjects),
            "published_as_not_subject_coded": sum(
                1 for a in catalog.authorizations if a.declares_no_subject_codes
            ),
        },
        "license_properties": {
            term: sum(1 for e in licenses if term in e) for term in LICENSE_PROPERTIES
        },
        "leaflets": {
            "rule": (
                "a leaflet is attached only where its published title equals the "
                "authorization's published title after case and punctuation normalization"
            ),
            "authorizations_with_a_leaflet": len(matched),
            "authorizations_without_a_leaflet": len(catalog.authorizations) - len(matched),
        },
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
        },
    }


def coverage_problems(
    statement: Mapping[str, Any],
    document: Mapping[str, Any],
    catalog: Catalog,
    leaflet_index: Mapping[str, leaflets_module.Leaflet],
) -> list[str]:
    """Every figure in a coverage statement that the export beside it contradicts."""
    expected = coverage(document, catalog, leaflet_index)
    return [
        f"{key}: says {statement.get(key)!r}, the export gives {expected[key]!r}"
        for key in expected
        if statement.get(key) != expected[key]
    ]


def check_coverage(
    statement: Mapping[str, Any],
    document: Mapping[str, Any],
    catalog: Catalog,
    leaflet_index: Mapping[str, leaflets_module.Leaflet],
) -> None:
    """Refuse to publish a coverage statement the export contradicts."""
    problems = coverage_problems(statement, document, catalog, leaflet_index)
    if problems:
        raise ValueError(
            "coverage statement does not describe the export beside it: " + "; ".join(problems)
        )


def serialize(document: Mapping[str, Any]) -> str:
    """One canonical serialization, so determinism is a property rather than a habit."""
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


@dataclass(frozen=True, slots=True)
class ExportReport:
    """What one export run produced, for the CLI to say out loud."""

    licenses: int
    excluded: int
    alignments: int
    document_path: Path
    coverage_path: Path


def write(
    catalog: Catalog,
    ctids: Mapping[str, str],
    leaflets: Sequence[leaflets_module.Leaflet],
    output_dir: Path,
) -> ExportReport:
    """Project ``catalog`` into ``output_dir``, checking everything before writing anything.

    A failed check leaves no partial output to mistake for a good one.
    """
    from chalkline.ctdl import validate as validate_module

    leaflet_index = leaflets_module.index_by_title(tuple(leaflets))
    document = project_graph(catalog, ctids, leaflet_index)
    validate_module.check(document)
    statement = coverage(document, catalog, leaflet_index)
    check_coverage(statement, document, catalog, leaflet_index)

    output_dir.mkdir(parents=True, exist_ok=True)
    document_path = output_dir / GRAPH_FILENAME
    coverage_path = output_dir / COVERAGE_FILENAME
    document_path.write_text(serialize(document), encoding="utf-8")
    coverage_path.write_text(serialize(statement), encoding="utf-8")
    entities: dict[str, int] = statement["entities"]
    return ExportReport(
        licenses=entities["ceterms:License"],
        excluded=len(catalog.exclusions),
        alignments=entities["ceterms:CredentialAlignmentObject"],
        document_path=document_path,
        coverage_path=coverage_path,
    )
