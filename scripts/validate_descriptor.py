#!/usr/bin/env python3
"""Validate the published dataset descriptor against the vocabularies it claims to use.

``site/dataset.jsonld`` is a schema.org ``Dataset`` and a DCAT ``dcat:Dataset`` on one node,
and it is embedded verbatim in ``site/index.html`` for harvesters. ``tests/test_dataset.py``
holds it to the build: every size and digest measured, the description the unofficial notice,
the embedded copy the file. None of that says the document is *valid*: a descriptor whose
property names were misspelled, or whose values were the wrong kind for the property, would
pass all of it, and a harvester would drop the part it could not read without telling anyone.

So this reads the published bytes the way a consumer does and checks them against the
published specifications, not against this project's own idea of them (CQ-49):

- **As JSON-LD 1.1**, with ``rdflib``, an independent parser. The ``@context`` must be inline
  prefixes only, so nothing is fetched, and every key and type must expand to an IRI under one
  of them. A JSON-LD processor drops a term it cannot expand *silently*, so the statements in
  the JSON are also counted against the triples the parser produced, and a shortfall fails.
- **Against the vocabularies**, vendored under ``data/vocab/`` with their provenance: schema.org
  release 30.1, DCAT 3, DCMI Metadata Terms and SPDX 2.3. Every class, property and
  vocabulary IRI used must be defined in its vocabulary.
- **schema.org domains and ranges.** Each schema.org property's ``schema:domainIncludes`` must
  admit a schema.org type its subject carries (or a supertype of one), and each value must fit
  its ``schema:rangeIncludes``: a node of an admitted type, an IRI where ``URL`` is admitted, or
  a literal of an admitted data type, dates checked for their lexical form.
- **DCAT domains, and DCAT/DCMI/SPDX range kinds.** A ``dcat:`` property's ``rdfs:domain``
  must be a type the subject carries (or a supertype); a property whose ``rdfs:range`` is a
  class must not be given a literal, and one whose range is a literal must not be given a
  resource. Domains are not enforced for DCMI and SPDX terms: DCMI's are absent or generic, and
  DCAT 3 itself reuses ``spdx:checksum`` on a distribution, which RDFS reads as an inference
  about the subject rather than an error.

    python scripts/validate_descriptor.py     # validate site/dataset.jsonld and its embed

``make validate-dataset`` runs it and ``make verify`` includes that target, so CI runs it on
every push. ``tests/test_descriptor_validates.py`` runs it too, and holds every rule above to a
negative control: a mutation of the real descriptor that the rule must catch.

No network: the context is refused unless it is inline, and the vocabularies are read from disk.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Final

from rdflib import OWL, RDF, RDFS, BNode, Graph, Literal, URIRef
from rdflib.term import Node

REPO_ROOT: Final = Path(__file__).resolve().parents[1]
DESCRIPTOR_PATH: Final = REPO_ROOT / "site" / "dataset.jsonld"
PAGE_PATH: Final = REPO_ROOT / "site" / "index.html"
VOCAB_DIR: Final = REPO_ROOT / "data" / "vocab"

SCHEMA: Final = "https://schema.org/"
DCAT: Final = "http://www.w3.org/ns/dcat#"
DCT: Final = "http://purl.org/dc/terms/"
SPDX: Final = "http://spdx.org/rdf/terms#"
XSD: Final = "http://www.w3.org/2001/XMLSchema#"

#: Each vocabulary the descriptor may use: its namespace, the vendored file that defines it,
#: the rdflib format of that file, and the name a finding uses for it.
VOCABULARIES: Final = (
    (SCHEMA, "schemaorg-current-https.ttl", "turtle", "schema.org 30.1"),
    (DCAT, "dcat3.ttl", "turtle", "DCAT 3"),
    (DCT, "dublin_core_terms.ttl", "turtle", "DCMI Metadata Terms"),
    (SPDX, "spdx-terms.xml", "xml", "SPDX 2.3"),
)

CLASS_TYPES: Final = frozenset({RDFS.Class, OWL.Class})
PROPERTY_TYPES: Final = frozenset(
    {
        RDF.Property,
        OWL.ObjectProperty,
        OWL.DatatypeProperty,
        OWL.AnnotationProperty,
        OWL.FunctionalProperty,
    }
)

EMBED_RE: Final = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL)
DATE_RE: Final = re.compile(r"\d{4}-\d{2}-\d{2}")
DATETIME_RE: Final = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})?"
)


@dataclass(frozen=True)
class Vocabulary:
    """One vendored vocabulary, read once."""

    namespace: str
    name: str
    graph: Graph

    def defines(self, term: Node) -> bool:
        return (term, None, None) in self.graph

    def is_class(self, term: Node) -> bool:
        return any(kind in CLASS_TYPES for kind in self.graph.objects(term, RDF.type))

    def is_property(self, term: Node) -> bool:
        return any(kind in PROPERTY_TYPES for kind in self.graph.objects(term, RDF.type))

    def supertypes(self, term: Node) -> set[Node]:
        """*term* and every class it is a subclass of, transitively, within this vocabulary."""
        found = self.graph.transitive_objects(term, RDFS.subClassOf)
        return {node for node in found if node is not None}

    def subtypes(self, term: Node) -> set[Node]:
        """*term* and every class that is a subclass of it, transitively."""
        found = self.graph.transitive_subjects(RDFS.subClassOf, term)
        return {node for node in found if node is not None}


@cache
def vocabularies() -> tuple[Vocabulary, ...]:
    """The four vendored vocabularies, parsed from disk. Cached: schema.org is 1 MB of Turtle."""
    loaded: list[Vocabulary] = []
    for namespace, filename, file_format, name in VOCABULARIES:
        graph = Graph()
        graph.parse(VOCAB_DIR / filename, format=file_format)
        loaded.append(Vocabulary(namespace, name, graph))
    return tuple(loaded)


def vocabulary_for(term: Node) -> Vocabulary | None:
    return next((v for v in vocabularies() if str(term).startswith(v.namespace)), None)


def _schema() -> Vocabulary:
    return next(v for v in vocabularies() if v.namespace == SCHEMA)


def _dcat() -> Vocabulary:
    return next(v for v in vocabularies() if v.namespace == DCAT)


def _short(term: Node) -> str:
    text = str(term)
    for prefix, namespace in (
        ("schema", SCHEMA),
        ("dcat", DCAT),
        ("dct", DCT),
        ("spdx", SPDX),
        ("rdfs", str(RDFS)),
        ("xsd", XSD),
    ):
        if text.startswith(namespace):
            return f"{prefix}:{text[len(namespace) :]}"
    return text


# --- JSON-LD ----------------------------------------------------------------------------


def _context(document: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """The inline prefix map, or findings saying why there is not one."""
    context = document.get("@context")
    if not isinstance(context, dict) or not all(
        isinstance(key, str) and isinstance(value, str) and value.startswith("http")
        for key, value in context.items()
    ):
        return {}, [
            "@context is not an inline map of prefixes to namespace IRIs; a remote or "
            "structured context would have to be fetched or interpreted before validation"
        ]
    return dict(context), []


def _expands(term: str, prefixes: dict[str, str]) -> bool:
    """Whether a key or type expands to an IRI under this document's prefix-only context.

    A compact IRI whose prefix is declared, or an absolute IRI. Anything else, a bare word
    or an undeclared prefix, is a term JSON-LD cannot expand and drops.
    """
    if term.startswith(("https://", "http://")):
        return True
    prefix, colon, _ = term.partition(":")
    return bool(colon) and prefix in prefixes


def _walk(node: Any, prefixes: dict[str, str], where: str) -> Iterator[tuple[int, str | None]]:
    """(statements, finding) for every node object below *node*.

    One statement per value of every property, and one per ``@type``, which is what a
    JSON-LD processor turns into triples. A node reference (an object holding only ``@id``)
    is a value, not a node, so it adds nothing of its own.
    """
    if isinstance(node, list):
        for index, item in enumerate(node):
            yield from _walk(item, prefixes, f"{where}[{index}]")
        return
    if not isinstance(node, dict):
        return
    types = node.get("@type", [])
    for kind in types if isinstance(types, list) else [types]:
        yield 1, None if _expands(kind, prefixes) else f"{where}: @type {kind!r} expands to no IRI"
    for key, value in node.items():
        if key.startswith("@"):
            continue
        if not _expands(key, prefixes):
            yield 0, f"{where}: {key!r} expands to no IRI, so a JSON-LD processor drops it"
        items = value if isinstance(value, list) else [value]
        yield len(items), None
        for index, item in enumerate(items):
            yield from _walk(item, prefixes, f"{where}.{key}[{index}]")


def parse(text: str) -> tuple[Graph, list[str]]:
    """The descriptor as a consumer reads it, and every way that reading lost something."""
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        return Graph(), [f"not JSON: {error}"]
    if not isinstance(document, dict):
        return Graph(), ["the document is not a JSON object"]
    prefixes, findings = _context(document)
    if findings:
        return Graph(), findings
    body = {key: value for key, value in document.items() if key != "@context"}
    counted = 0
    for statements, finding in _walk(body, prefixes, "$"):
        counted += statements
        if finding:
            findings.append(finding)
    graph = Graph()
    with warnings.catch_warnings():
        # rdflib's own JSON-LD parser builds a ConjunctiveGraph internally and warns about
        # it. That is rdflib's deprecation, not a finding about this document.
        warnings.filterwarnings("ignore", "ConjunctiveGraph is deprecated", DeprecationWarning)
        graph.parse(data=text, format="json-ld")
    if len(graph) != counted:
        findings.append(
            f"the JSON states {counted} statements and a JSON-LD processor read {len(graph)}: "
            "an undefined term is dropped silently, and a repeated value collapses"
        )
    return graph, findings


# --- the vocabularies -------------------------------------------------------------------


def _types(graph: Graph, node: Node) -> set[Node]:
    return set(graph.objects(node, RDF.type))


def undefined_terms(graph: Graph) -> list[str]:
    """Every class, property or vocabulary IRI the descriptor uses that no vocabulary defines."""
    findings: list[str] = []
    for _subject, predicate, value in sorted(graph):
        if predicate == RDF.type:
            vocabulary = vocabulary_for(value) if isinstance(value, URIRef) else None
            if vocabulary is None:
                findings.append(f"type {value} is in none of the vendored vocabularies")
            elif not vocabulary.is_class(value):
                findings.append(f"{_short(value)} is not a class in {vocabulary.name}")
            continue
        vocabulary = vocabulary_for(predicate)
        if vocabulary is None:
            findings.append(f"property {predicate} is in none of the vendored vocabularies")
        elif not vocabulary.is_property(predicate):
            findings.append(f"{_short(predicate)} is not a property in {vocabulary.name}")
        defining = vocabulary_for(value) if isinstance(value, URIRef) else None
        if defining is not None and not defining.defines(value):
            findings.append(f"{_short(value)} is not defined in {defining.name}")
    return sorted(set(findings))


def _schema_types(graph: Graph, node: Node) -> set[Node]:
    schema = _schema()
    found: set[Node] = set()
    for kind in _types(graph, node):
        if str(kind).startswith(SCHEMA):
            found |= schema.supertypes(kind)
    return found


def _literal_fits(value: Literal, admitted: set[Node]) -> bool:
    """Whether a literal is a value of one of the admitted schema.org data types."""
    schema = _schema()
    text = str(value)
    datatype = value.datatype
    text_like = schema.subtypes(URIRef(SCHEMA + "Text"))
    if admitted & text_like and datatype in (None, URIRef(XSD + "string")):
        return True
    if URIRef(SCHEMA + "Date") in admitted and DATE_RE.fullmatch(text):
        return True
    if URIRef(SCHEMA + "DateTime") in admitted and DATETIME_RE.fullmatch(text):
        return True
    numeric = {URIRef(SCHEMA + name) for name in ("Number", "Integer", "Float")}
    if admitted & numeric and isinstance(value.toPython(), int | float):
        return True
    return URIRef(SCHEMA + "Boolean") in admitted and isinstance(value.toPython(), bool)


def schema_domains_and_ranges(graph: Graph) -> list[str]:
    """schema.org's own validation contract: domainIncludes and rangeIncludes."""
    schema = _schema()
    findings: list[str] = []
    for subject, predicate, value in sorted(graph):
        if not str(predicate).startswith(SCHEMA) or not schema.is_property(predicate):
            continue
        where = f"{_short(predicate)} on {subject}"
        domains = set(schema.graph.objects(predicate, URIRef(SCHEMA + "domainIncludes")))
        carried = _schema_types(graph, subject)
        if not carried:
            findings.append(f"{where}: the subject carries no schema.org type")
        elif not domains & carried:
            findings.append(
                f"{where}: the subject's types are not in its domain "
                f"({', '.join(sorted(_short(d) for d in domains))})"
            )
        ranges = set(schema.graph.objects(predicate, URIRef(SCHEMA + "rangeIncludes")))
        admitted: set[Node] = set()
        for kind in ranges:
            admitted |= schema.subtypes(kind)
        if isinstance(value, Literal):
            fits = _literal_fits(value, admitted)
        else:
            fits = bool(_schema_types(graph, value) & admitted) or (
                isinstance(value, URIRef) and URIRef(SCHEMA + "URL") in admitted
            )
        if not fits:
            findings.append(
                f"{where}: {value!s} is not in its range "
                f"({', '.join(sorted(_short(r) for r in ranges))})"
            )
    return findings


def _is_literal_range(kind: Node) -> bool:
    return kind == RDFS.Literal or str(kind).startswith(XSD) or kind == RDF.langString


def _range_kind(where: str, vocabulary: Vocabulary, predicate: Node, value: Node) -> list[str]:
    """A literal where the range is a class, or a resource where the range is a literal."""
    findings: list[str] = []
    for kind in vocabulary.graph.objects(predicate, RDFS.range):
        if kind == RDFS.Resource:
            continue
        if _is_literal_range(kind) and not isinstance(value, Literal):
            findings.append(f"{where}: its range is {_short(kind)}, a literal, not {value}")
        elif not _is_literal_range(kind) and isinstance(value, Literal):
            findings.append(
                f"{where}: its range is {_short(kind)}, a class, and {value!s} is a literal"
            )
    return findings


def _dcat_domain(where: str, graph: Graph, subject: Node, predicate: Node) -> list[str]:
    """A DCAT property on a subject that is not of its rdfs:domain, or a subclass of it."""
    dcat = _dcat()
    carried: set[Node] = set()
    for kind in _types(graph, subject):
        carried |= dcat.supertypes(kind)
    return [
        f"{where}: the subject is not a {_short(domain)}"
        for domain in dcat.graph.objects(predicate, RDFS.domain)
        if domain not in carried
    ]


def rdfs_ranges_and_dcat_domains(graph: Graph) -> list[str]:
    """DCAT, DCMI and SPDX: literal against resource by rdfs:range, and DCAT's rdfs:domain."""
    findings: list[str] = []
    for subject, predicate, value in sorted(graph):
        vocabulary = vocabulary_for(predicate)
        if predicate == RDF.type or vocabulary is None or vocabulary.namespace == SCHEMA:
            continue
        where = f"{_short(predicate)} on {subject}"
        findings += _range_kind(where, vocabulary, predicate, value)
        if vocabulary.namespace == DCAT:
            findings += _dcat_domain(where, graph, subject, predicate)
    return findings


def _is_blank(node: Node) -> bool:
    return isinstance(node, BNode)


def validate(text: str) -> list[str]:
    """Every finding against *text*, the descriptor as published. Empty means valid."""
    graph, findings = parse(text)
    if not len(graph):
        return findings or ["the descriptor parsed to an empty graph"]
    datasets = list(graph.subjects(RDF.type, URIRef(SCHEMA + "Dataset")))
    if len(datasets) != 1 or _is_blank(datasets[0]):
        findings.append(f"expected one identified schema:Dataset node, found {len(datasets)}")
    findings += undefined_terms(graph)
    findings += schema_domains_and_ranges(graph)
    findings += rdfs_ranges_and_dcat_domains(graph)
    return findings


def embedded(page: str) -> list[str]:
    """The data blocks a page carries, as a harvester extracts them."""
    return [match.group(1) for match in EMBED_RE.finditer(page)]


def _report(label: str, findings: Iterable[str]) -> int:
    found = list(findings)
    for finding in found:
        print(f"{label}: {finding}", file=sys.stderr)
    return len(found)


def main() -> int:
    text = DESCRIPTOR_PATH.read_text(encoding="utf-8")
    blocks = embedded(PAGE_PATH.read_text(encoding="utf-8"))
    failures = _report("site/dataset.jsonld", validate(text))
    if len(blocks) != 1:
        failures += _report("site/index.html", [f"expected one data block, found {len(blocks)}"])
    for block in blocks:
        failures += _report("site/index.html (embedded)", validate(block))
    if failures:
        print(f"validate-dataset: {failures} finding(s)", file=sys.stderr)
        return 1
    graph, _ = parse(text)
    names = ", ".join(vocabulary.name for vocabulary in vocabularies())
    print(
        f"validate-dataset: {len(graph)} statements in site/dataset.jsonld and its embedded "
        f"copy, valid JSON-LD against {names}: 0 findings"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
