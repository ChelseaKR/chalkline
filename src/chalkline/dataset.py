"""One statement about what this project publishes, in the two vocabularies catalogs read.

The three artifacts under ``site/`` are findable today only by reading the README. Dataset
search engines and open-data catalogs do not read READMEs; they harvest schema.org from a
page's head and DCAT from a descriptor. This module writes both, and embeds the result in
the published page, so the artifacts can be found by the machinery that exists for finding
datasets.

**One node, two vocabularies, rather than two documents.** The obvious shape is a
schema.org ``Dataset`` and a parallel DCAT ``Dataset`` saying the same thing. Two
descriptions of one dataset are two things that can disagree, and nothing would notice
which one a harvester believed. So each node here is typed as *both* and carries both
vocabularies' properties side by side: ``schema:name`` and ``dct:title`` on the same node,
``schema:distribution`` and ``dcat:distribution`` pointing at the same three nodes. A DCAT
harvester and a schema.org harvester read the same subject and cannot come away with
different statements, because there is only one.

**Nothing here is a wall clock.** ``dateModified`` is the Commission's retrieval date,
copied from ``coverage.json``, because the dataset is as current as its sources are, not as
current as the last build. A build clock in a descriptor is a claim that the data changed,
and re-running a deterministic build changes nothing.

**No counts.** ``coverage.json`` counts the graph from the graph, and
``export.check_coverage`` refuses a statement the export contradicts. Copying those figures
here would make a third place that nothing derives and nothing checks, which is the
reasoning :data:`chalkline.site.DESCRIPTION` already records for the page's own prose. The
descriptor points at the coverage statement instead.

**The description is the notice.** A harvester's card is the one surface where a stranger
meets this project with no page around it, so ``schema:description`` is
:data:`chalkline.ctdl.export.DISCLAIMER` in full. A catalog entry that read as an official
California credential dataset would be the single worst outcome this project can produce,
and the notice is what stops it.

**The ``@id`` namespace is untouched.** The identifiers here name the served page and the
files beside it, the addresses ``site/index.html`` already publishes as ``canonical`` and
``og:url``, and never :data:`chalkline.ctdl.export.RESOURCE_BASE`. Describing where a file
is downloaded from is not the resolvable-``@id`` decision ADR 0004 reserved, and
``tests/test_dataset.py`` holds the descriptor to carrying no CTDL resource URI at all.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Final

from chalkline.ctdl.export import (
    COVERAGE_FILENAME,
    DISCLAIMER,
    GRAPH_FILENAME,
    LANG,
)
from chalkline.sources.leaflets import SOURCE_URL as LEAFLET_INDEX_URL
from chalkline.sources.sort_table import SOURCE_URL as SORT_TABLE_URL

DATASET_FILENAME: Final = "dataset.jsonld"

EVIDENCE_FILENAME: Final = "ctdl-validate.json"
"""The third described artifact. Written by ``scripts/validate_evidence.py`` rather than by
``chalkline build``, and registered in ``cli.PUBLISHED_BY_ANOTHER_GATE`` for that reason, so
:func:`descriptor` is handed its bytes rather than reproducing them."""

LICENSE_URL: Final = "https://www.apache.org/licenses/LICENSE-2.0"
"""Apache-2.0, matching ``pyproject.toml``'s ``license`` field and the committed ``LICENSE``.

``tests/test_dataset.py`` holds this to the declared license rather than letting the
descriptor state a licence the repository does not carry."""

CONTEXT: Final = {
    "schema": "https://schema.org/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "dct": "http://purl.org/dc/terms/",
    "spdx": "http://spdx.org/rdf/terms#",
}
"""The four vocabularies the descriptor uses, declared in full rather than by remote context.

No ``@context`` URL, for the same reason the page fetches nothing: a consumer that cannot
reach schema.org must still be able to read this document. Every term below is prefixed
from this map.
"""

SHA256_ALGORITHM: Final = "spdx:checksumAlgorithm_sha256"

#: What each described artifact is, in words a catalog entry can show. Fixed strings rather
#: than derived ones: these say what the file *is*, which is a property of the format and
#: not of the data, so nothing here can drift when the Commission publishes more rows.
ARTIFACT_TITLES: Final = {
    GRAPH_FILENAME: "The credential graph, as CTDL JSON-LD",
    COVERAGE_FILENAME: "The coverage statement, counted from the graph at build time",
    EVIDENCE_FILENAME: "An independent ctdl-validate report over the graph",
}

MEDIA_TYPES: Final = {
    GRAPH_FILENAME: "application/ld+json",
    COVERAGE_FILENAME: "application/json",
    EVIDENCE_FILENAME: "application/json",
}

#: Ordered, because a descriptor whose distributions reordered between builds would fail
#: ``chalkline check`` for a difference that means nothing. This is also the order the
#: README lists them in.
DESCRIBED_ARTIFACTS: Final = (GRAPH_FILENAME, COVERAGE_FILENAME, EVIDENCE_FILENAME)

#: Subject terms for harvesters that index on them. Every one of these appears verbatim in
#: the project's own title, in the name of a modeled source, or in the CTDL class this
#: project emits. None of them is a claim about the data that the data does not already
#: make. A term describing scope, quality or completeness would be, and none is here.
KEYWORDS: Final = (
    "California",
    "educator credentials",
    "teaching credentials",
    "credential authorizations",
    "CTDL",
    "Commission on Teacher Credentialing",
)


def sha256_of(text: str) -> str:
    """The hex digest of *text* as it is published, which is UTF-8 on disk."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _distribution(site_url: str, filename: str, text: str) -> dict[str, Any]:
    """One artifact, described once for both vocabularies.

    ``schema:contentSize`` is text and ``dcat:byteSize`` is a number, which is what each
    vocabulary specifies; both are the same measurement of the same bytes. The checksum is
    given twice for the same reason the node is typed twice: ``schema:sha256`` is what a
    schema.org consumer looks for, ``spdx:checksum`` is what DCAT specifies, and a consumer
    should not have to guess which one this project meant.
    """
    url = site_url + filename
    size = len(text.encode("utf-8"))
    digest = sha256_of(text)
    return {
        "@id": url,
        "@type": ["schema:DataDownload", "dcat:Distribution"],
        "schema:name": ARTIFACT_TITLES[filename],
        "dct:title": ARTIFACT_TITLES[filename],
        "schema:contentUrl": url,
        "dcat:downloadURL": {"@id": url},
        "schema:encodingFormat": MEDIA_TYPES[filename],
        "dcat:mediaType": MEDIA_TYPES[filename],
        "schema:contentSize": str(size),
        "dcat:byteSize": size,
        "schema:sha256": digest,
        "spdx:checksum": {
            "@type": "spdx:Checksum",
            "spdx:algorithm": {"@id": SHA256_ALGORITHM},
            "spdx:checksumValue": digest,
        },
    }


def descriptor(
    *,
    site_url: str,
    title: str,
    artifacts: Mapping[str, str],
    retrieved: str,
) -> dict[str, Any]:
    """Describe the published artifacts, from the artifacts.

    *artifacts* maps each filename in :data:`DESCRIBED_ARTIFACTS` to the exact text
    published under it, so every size and every digest in the result is measured from the
    bytes rather than recorded beside them. *retrieved* is ``coverage.json``'s
    ``source.retrieved``; passing it rather than reading a clock is what keeps the
    descriptor's ``dateModified`` a statement about the Commission's publication.

    Raises ``ValueError`` when an artifact is missing, because a descriptor that silently
    described two files instead of three would publish a smaller dataset than the one that
    exists and nothing downstream would object: the document would be well-formed, the
    hashes it did carry would be correct, and ``chalkline check`` would hold it to a fresh
    build that also described two. An absent artifact is not a dataset with fewer
    distributions.
    """
    missing = [name for name in DESCRIBED_ARTIFACTS if name not in artifacts]
    if missing:
        raise ValueError(
            "cannot describe artifacts that were not supplied: "
            + ", ".join(missing)
            + "; a descriptor naming fewer downloads than the site publishes would be a "
            "smaller dataset asserted as the whole one"
        )
    if not retrieved:
        raise ValueError(
            "the descriptor's dateModified is the source retrieval date and it is empty; "
            "an absent date must not be filled in from a build clock"
        )
    distributions = [_distribution(site_url, name, artifacts[name]) for name in DESCRIBED_ARTIFACTS]
    sources = [SORT_TABLE_URL, LEAFLET_INDEX_URL]
    return {
        "@context": dict(CONTEXT),
        "@id": f"{site_url}#dataset",
        "@type": ["schema:Dataset", "dcat:Dataset"],
        "schema:name": title,
        "dct:title": title,
        "schema:description": DISCLAIMER,
        "dct:description": DISCLAIMER,
        "schema:url": site_url,
        "dcat:landingPage": {"@id": site_url},
        "schema:license": {"@id": LICENSE_URL},
        "dct:license": {"@id": LICENSE_URL},
        "schema:inLanguage": LANG,
        "dct:language": LANG,
        "schema:dateModified": retrieved,
        "dct:modified": retrieved,
        "schema:isBasedOn": [{"@id": url} for url in sources],
        "dct:source": [{"@id": url} for url in sources],
        "schema:keywords": list(KEYWORDS),
        "dcat:keyword": list(KEYWORDS),
        "schema:distribution": distributions,
        # The same three nodes, by reference rather than repeated. Each distribution
        # carries an ``@id``, so a node reference here expands to the identical subject a
        # schema.org consumer reads above: one description, reachable through either
        # vocabulary's property. Inlining them twice would double the document and create
        # two copies that a hand edit could pull apart.
        "dcat:distribution": [{"@id": node["@id"]} for node in distributions],
    }
