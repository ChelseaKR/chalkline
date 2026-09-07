"""Serialize the committed CTDL graph as RDF, offline, through a processor written elsewhere.

``credentials.jsonld`` is JSON-LD, and JSON-LD is only RDF once a processor has read it against
a context. SPARQL stores, SHACL engines and registry loaders want the RDF, not the JSON. This
module produces it, and in producing it asks an implementation this repository did not write
whether the graph says what the graph is supposed to say -- the same reasoning that brought in
``ctdl-validate``.

Offline, and provably
---------------------

``pyld`` installs a ``requests``-backed document loader at import time. Left alone it would
fetch ``https://credreg.net/ctdl/schema/context/json`` over the network, which would make the
serialization a statement about whatever the Commission's host served that minute rather than
about the context vendored in this repository. So :func:`offline_document_loader` serves the
vendored file for that one URL and raises :class:`NetworkRefused` for every other, and it is
installed globally as well as passed per call, because a default that reaches the network is
the wrong default even for code that never means to use it.
``tests/test_rdf.py`` replaces ``socket.socket.connect`` with a raise and runs the whole
pipeline underneath it, so "offline" is measured rather than asserted.

Determinism
-----------

The N-Quads are the URDNA2015 canonical form, not merely sorted output. 9,153 of the 10,008
quads carry a blank node -- every nested profile in the graph is anonymous -- and sorting does
not make blank-node labels stable, it only makes them stably *ordered*. Canonicalization
assigns each blank node a label derived from its position in the graph, so two runs in two
processes produce identical bytes. Measured: the same SHA-256 under two ``PYTHONHASHSEED``
values.

The Turtle is written here rather than by ``rdflib`` for that same reason. rdflib's Turtle
serializer inlines blank nodes in an order that follows dictionary iteration, and the same
graph under two hash seeds gave the same byte length and two different digests. rdflib is
still used, in the tests, as the independent parser that is asked whether this file's Turtle
denotes the same graph as its N-Triples.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

from chalkline.ctdl.export import CTDL_CONTEXT_URL as CTDL_CONTEXT_URL

NQUADS_FILENAME: Final = "credentials.nq"
TURTLE_FILENAME: Final = "credentials.ttl"
STATEMENT_FILENAME: Final = "rdf.json"

CONTEXT_PATH: Final = Path(__file__).with_name("ctdl-context.json")

ALGORITHM: Final = "URDNA2015"
"""The canonicalization algorithm, named in the committed statement so a reader of
``credentials.nq`` knows why its blank node labels are what they are."""

RDF_TYPE: Final = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
XSD_STRING: Final = "http://www.w3.org/2001/XMLSchema#string"

#: Top-level keys of ``credentials.jsonld`` that carry no triple and are not expected to.
#: ``comment`` is prose addressed to whoever opens the file; the context does not define it,
#: so expansion drops it, and a round-trip gate that did not know this would fail on a
#: correct document. Every entry here is a reviewed decision, printed by
#: :func:`undeclared_terms` callers rather than silently skipped.
UNDECLARED_BY_DESIGN: Final[dict[str, str]] = {
    "comment": (
        "prose addressed to a human reader of the JSON, deliberately outside the context and "
        "therefore outside the RDF; removing it leaves the canonical N-Quads byte-identical"
    ),
}

#: A local name is written after a prefix only when it matches this. Turtle's own PN_LOCAL
#: production allows far more, including escapes and dots, and getting those subtly wrong
#: produces a file that parses as a *different* graph rather than one that fails to parse.
#: Anything outside this is written as a full IRI, which is always correct.
_SAFE_LOCAL_NAME: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


class RDFError(Exception):
    """The graph could not be serialized, or does not survive its own round-trip."""


class NetworkRefused(RDFError):
    """A JSON-LD processor asked for a document over the network. It does not get one."""


def _jsonld() -> Any:
    """Import ``pyld`` at the point of use, and say what to install if it is not there.

    ``pyproject.toml`` keeps ``dependencies`` empty on purpose, and this module is the only
    thing in the package that needs a third-party import. Importing it lazily means
    ``pip install chalkline-ctdl`` still gives a working ``build``, ``check``, ``mint-ctids``
    and ``authorizes``; only ``export`` asks for more.
    """
    try:
        from pyld import jsonld
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised by hand, not in CI
        raise RDFError(
            "chalkline export needs a JSON-LD processor, which is a development dependency "
            "and not part of the runtime install: `uv sync` in a checkout, or "
            "`pip install pyld==3.3.0`"
        ) from exc
    return jsonld


def vendored_context() -> dict[str, Any]:
    """The context as committed, which is the only context this project will resolve."""
    with CONTEXT_PATH.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


def offline_document_loader(
    context: Mapping[str, Any] | None = None,
) -> Callable[..., dict[str, Any]]:
    """A document loader that serves the vendored context and refuses everything else."""
    document = dict(context) if context is not None else vendored_context()

    def loader(url: str, options: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if url == CTDL_CONTEXT_URL:
            return {
                "contentType": "application/ld+json",
                "contextUrl": None,
                "documentUrl": url,
                "document": document,
            }
        raise NetworkRefused(
            f"refused to load {url}: the only document this build resolves is the vendored "
            f"context at {CONTEXT_PATH.name}"
        )

    return loader


@contextmanager
def _surfacing_a_refused_load() -> Iterator[None]:
    """Let :class:`NetworkRefused` out, rather than a processor error that buried it.

    pyld catches whatever a document loader raises and re-raises its own
    ``JsonLdError('Could not convert input to RDF dataset before normalization.')``, which
    says nothing about the network and would be read as a malformed document. The refusal is
    the interesting fact, so it is pulled back out of the cause chain.
    """
    try:
        yield
    except Exception as exc:
        cause: BaseException | None = exc
        while cause is not None:
            if isinstance(cause, NetworkRefused):
                raise cause from exc
            cause = cause.__cause__
        raise


def _options(context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Processor options, with the offline loader installed globally as well as passed.

    Passing it is what makes *these* calls offline. Installing it is what makes a future call
    that forgets to pass it offline too, and pyld's own default is a network loader.
    """
    loader = offline_document_loader(context)
    _jsonld().set_document_loader(loader)
    return {"documentLoader": loader}


def quads(
    document: Mapping[str, Any], context: Mapping[str, Any] | None = None
) -> list[dict[str, Any]]:
    """The graph as a canonical list of RDF triples, in URDNA2015 order.

    Returned as pyld's structured terms rather than as text, so the serializers below never
    parse N-Triples back out of a string. A parser is a place for an escaping bug to live, and
    there is no reason to have one here.
    """
    with _surfacing_a_refused_load():
        dataset = _jsonld().normalize(document, {**_options(context), "algorithm": ALGORITHM})
    if not isinstance(dataset, dict):  # pragma: no cover - pyld returns a dataset without format
        raise RDFError("the processor did not return a dataset")
    graphs = sorted(dataset)
    if graphs not in ([], ["@default"]):
        raise RDFError(
            "the graph normalized into named graphs, which this project does not publish: "
            + ", ".join(graphs)
        )
    return list(dataset.get("@default", []))


def _escape_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return escaped.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _term(node: Mapping[str, Any]) -> str:
    """One RDF term in N-Triples syntax, which is also valid Turtle."""
    kind = node["type"]
    value = node["value"]
    if kind == "IRI":
        return f"<{value}>"
    if kind == "blank node":
        return str(value)
    text = f'"{_escape_literal(value)}"'
    language = node.get("language")
    if language:
        return f"{text}@{language}"
    datatype = node.get("datatype")
    if datatype and datatype != XSD_STRING:
        return f"{text}^^<{datatype}>"
    return text


def nquads(
    document: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
    triples: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Canonical N-Quads. One triple per line, newline-terminated, no trailing blank line."""
    rows = list(triples) if triples is not None else quads(document, context)
    return "".join(
        f"{_term(q['subject'])} {_term(q['predicate'])} {_term(q['object'])} .\n" for q in rows
    )


def _prefixes(context: Mapping[str, Any]) -> dict[str, str]:
    """Namespace prefixes the context itself declares, plus the two RDF always needs."""
    declarations = context.get("@context", context)
    found: dict[str, str] = {"rdf": RDF_TYPE.rsplit("#", 1)[0] + "#", "xsd": XSD_STRING[:-6]}
    if isinstance(declarations, Mapping):
        for name, target in declarations.items():
            if ":" in name or name.startswith("@") or not isinstance(target, str):
                continue
            if target.endswith(("/", "#")):
                found.setdefault(name, target)
    return found


def _shorten(iri: str, prefixes: Mapping[str, str]) -> tuple[str, str | None]:
    """``ceterms:name`` where that is unambiguous and safe, and ``<...>`` where it is not.

    Longest matching namespace wins, and an exact tie is broken by the prefix name, so the
    choice is a fact about the context rather than about the order a dictionary was built.
    Returns the rendering and the prefix it used, so the header declares exactly the prefixes
    the body contains -- read off the terms, never scraped back out of the rendered text,
    where a prefix-shaped substring inside a string literal would forge a declaration.
    """
    candidates = [
        (len(namespace), name, iri[len(namespace) :])
        for name, namespace in prefixes.items()
        if iri.startswith(namespace) and _SAFE_LOCAL_NAME.match(iri[len(namespace) :])
    ]
    if not candidates:
        return f"<{iri}>", None
    longest = max(length for length, _, _ in candidates)
    _, name, local = min(c for c in candidates if c[0] == longest)
    return f"{name}:{local}", name


def _grouped(triples: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """Triples keyed by subject then predicate, in N-Triples term text so ordering is total."""
    grouped: dict[str, dict[str, list[str]]] = {}
    for triple in triples:
        subject = _term(triple["subject"])
        predicate = _term(triple["predicate"])
        grouped.setdefault(subject, {}).setdefault(predicate, []).append(_term(triple["object"]))
    return grouped


def _subject_order(subject: str) -> tuple[int, str]:
    """IRIs first, then blank nodes, each block sorted. Blank node labels are canonical, so
    this is an ordering of the graph and not of one process's memory."""
    return (1, subject) if subject.startswith("_:") else (0, subject)


def turtle(
    document: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
    triples: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Turtle, grouped by subject, with only the prefixes the graph actually uses.

    Blank nodes are written as labelled nodes (``_:c14n7``) rather than inlined in ``[ ]``.
    Inlining reads better and is what rdflib does; it is also what makes rdflib's output
    depend on dictionary order. A label that came out of URDNA2015 is stable, so this keeps
    the labels and stays byte-identical between runs.
    """
    resolved = dict(context) if context is not None else vendored_context()
    rows = list(triples) if triples is not None else quads(document, resolved)
    prefixes = _prefixes(resolved)
    grouped = _grouped(rows)
    used: set[str] = set()
    rendering: dict[str, str] = {}

    def render(term_text: str) -> str:
        """Turtle for one N-Triples term. Cached: the graph reuses ~1,200 distinct terms
        across 30,024 positions, and matching each against 600 namespaces every time made a
        thirty-second job out of a one-second one."""
        if term_text not in rendering:
            if term_text.startswith("<") and term_text.endswith(">"):
                short, prefix = _shorten(term_text[1:-1], prefixes)
                if prefix is not None:
                    used.add(prefix)
                rendering[term_text] = short
            else:
                rendering[term_text] = term_text
        return rendering[term_text]

    body: list[str] = []
    for subject in sorted(grouped, key=_subject_order):
        clauses: list[str] = []
        for predicate in sorted(grouped[subject], key=lambda p: (p != f"<{RDF_TYPE}>", p)):
            short = "a" if predicate == f"<{RDF_TYPE}>" else render(predicate)
            objects = [render(o) for o in sorted(grouped[subject][predicate])]
            clauses.append(f"    {short} " + ",\n        ".join(objects))
        body.append(f"{render(subject)}\n" + " ;\n".join(clauses) + " .\n")

    header = [f"@prefix {name}: <{prefixes[name]}> .\n" for name in sorted(used)]
    return "".join(header) + "\n" + "\n".join(body)


def _declarations(context: Mapping[str, Any]) -> dict[str, Any]:
    inner = context.get("@context", context)
    return dict(inner) if isinstance(inner, Mapping) else {}


def _language_map_terms(declarations: Mapping[str, Any]) -> set[str]:
    """Terms whose values are language maps, whose *keys* are BCP 47 tags, not terms.

    Without this the walk below reads ``{"ceterms:name": {"en-US": "..."}}`` as a document
    using a term called ``en-US`` and reports 3,492 undeclared terms on a correct graph.
    """
    return {
        term
        for term, definition in declarations.items()
        if isinstance(definition, Mapping) and definition.get("@container") == "@language"
    }


def undeclared_terms(
    document: Mapping[str, Any], context: Mapping[str, Any] | None = None
) -> list[str]:
    """Every property key in the document the context does not define, minus the allowlist.

    Two failure shapes, and only one of them is visible to expansion:

    * A **bare** key the context does not define is dropped on expansion, silently. Nothing
      downstream can tell it apart from a key that was never written.
    * A **prefixed** key -- ``ceterms:notARealProperty`` -- is *not* dropped, because the
      context declares ``ceterms`` as a prefix and the processor resolves the compact IRI
      whether or not that specific term exists. Measured against this graph: adding
      ``ceterms:definitelyNotARealTerm`` raised the quad count rather than leaving it equal.
      Expansion cannot catch this one, so membership in the context is checked directly.

    The issue that asked for this gate described only the first shape. Both are checked here.

    Property keys only. The vendored context declares 609 properties and **no classes at all**
    -- ``ceterms:License`` is not a key in it, and resolves through the ``ceterms`` prefix like
    any other compact IRI -- so checking ``@type`` values against the context would report
    every class in a correct document. Classes are checked, against the vendored *schema*,
    by :mod:`chalkline.ctdl.validate`, which requires every ``@type`` to be an ``rdfs:Class``
    there. Splitting the two checks across the two vendored files is not a gap; it is each
    file being asked the question it can answer.
    """
    resolved = dict(context) if context is not None else vendored_context()
    declarations = _declarations(resolved)
    seen: set[str] = set()
    _collect_keys(document, seen, _language_map_terms(declarations))
    return sorted(
        key for key in seen if key not in declarations and key not in UNDECLARED_BY_DESIGN
    )


#: JSON-LD keywords whose values hold no property keys: an IRI, a class name, or the context
#: itself. Walking into them would report class names and the context's own 668 terms as
#: undeclared. Every other keyword -- ``@graph`` above all -- is walked into but not counted.
_OPAQUE_KEYWORDS: Final = frozenset({"@context", "@id", "@type", "@value", "@language"})


def _collect_keys(node: Any, into: set[str], language_maps: frozenset[str] | set[str]) -> None:
    if isinstance(node, Mapping):
        for key, value in node.items():
            if key in _OPAQUE_KEYWORDS:
                continue
            if not key.startswith("@"):
                into.add(key)
                if key in language_maps:
                    continue
            _collect_keys(value, into, language_maps)
    elif isinstance(node, list):
        for item in node:
            _collect_keys(item, into, language_maps)


def round_trip_difference(
    document: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
    triples: Sequence[Mapping[str, Any]] | None = None,
) -> str | None:
    """``None`` when compacting the expansion denotes the same graph, else what differs.

    Compared as canonical quad sets, not as text. Compacting the expansion of this document
    and diffing the JSON reports a difference on all 134 entities and always will: expansion
    lowercases ``en-US`` to ``en-us`` per the JSON-LD API, and compaction collapses
    single-element arrays. Both are the processor being correct. A textual gate here would
    have failed on a correct document from its first run, which is a gate that teaches its
    reader to ignore it.
    """
    resolved = dict(context) if context is not None else vendored_context()
    processor = _jsonld()
    options = _options(resolved)
    with _surfacing_a_refused_load():
        expanded = processor.expand(document, options)
        compacted = processor.compact(expanded, document.get("@context", CTDL_CONTEXT_URL), options)
    return describe_difference(nquads(document, resolved, triples), nquads(compacted, resolved))


def describe_difference(before: str, after: str) -> str | None:
    """``None`` when two N-Quads documents are the same graph, else what moved and by how much.

    Split out from the round-trip so it can be driven with two graphs that really do differ.
    The round trip over this project's own graph does not differ, and a reporter reached only
    by a failure that never happens is a reporter nobody has ever seen work.
    """
    if before == after:
        return None
    lost = sorted(set(before.splitlines()) - set(after.splitlines()))
    gained = sorted(set(after.splitlines()) - set(before.splitlines()))
    parts = []
    if lost:
        parts.append(f"{len(lost)} triple(s) lost, first: {lost[0]}")
    if gained:
        parts.append(f"{len(gained)} triple(s) gained, first: {gained[0]}")
    return "; ".join(parts) or "the quad sets differ in multiplicity only"


def _digest(text: str) -> dict[str, Any]:
    encoded = text.encode("utf-8")
    return {"bytes": len(encoded), "sha256": hashlib.sha256(encoded).hexdigest()}


def statement(
    document: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
    triples: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """What the serializations contain, and what was checked to produce them.

    Every check records whether it *ran*, not only whether it failed. A count of zero
    undeclared terms and a count that was never taken are different facts, and this file is
    read by people deciding whether to trust the triples.
    """
    resolved = dict(context) if context is not None else vendored_context()
    triples = list(triples) if triples is not None else quads(document, resolved)
    nq = nquads(document, resolved, triples)
    ttl = turtle(document, resolved, triples)
    difference = round_trip_difference(document, resolved, triples)
    undeclared = undeclared_terms(document, resolved)
    predicates: dict[str, int] = {}
    for triple in triples:
        name = str(triple["predicate"]["value"])
        predicates[name] = predicates.get(name, 0) + 1
    blank = sum(
        1
        for t in triples
        if any(t[role]["type"] == "blank node" for role in ("subject", "predicate", "object"))
    )
    return {
        "algorithm": ALGORITHM,
        "context": CTDL_CONTEXT_URL,
        "triples": len(triples),
        "triples_naming_a_blank_node": blank,
        "distinct_subjects": len({_term(t["subject"]) for t in triples}),
        "predicates": dict(sorted(predicates.items())),
        "round_trip": {
            "checked": True,
            "basis": f"{ALGORITHM} quad sets, not JSON text",
            "equivalent": difference is None,
            "difference": difference,
        },
        "undeclared_terms": {
            "checked": True,
            "found": undeclared,
            "allowed_by_review": dict(sorted(UNDECLARED_BY_DESIGN.items())),
        },
        "files": {
            NQUADS_FILENAME: _digest(nq),
            TURTLE_FILENAME: _digest(ttl),
        },
    }


def artifacts(
    document: Mapping[str, Any], context: Mapping[str, Any] | None = None
) -> dict[str, str]:
    """The three files ``chalkline export`` writes, refusing to write any of them on a fault.

    A serialization that lost a triple, or that carries a term the context never defined, is
    exactly the artifact this verb exists to catch. Writing it and noting the problem beside
    it would publish it; Pages uploads the whole directory.
    """
    resolved = dict(context) if context is not None else vendored_context()
    triples = quads(document, resolved)
    record = statement(document, resolved, triples)
    if record["undeclared_terms"]["found"]:
        raise RDFError(
            "the document uses terms the context does not define, which either vanish from the "
            "RDF or resolve through a prefix to an IRI nothing declares: "
            + ", ".join(record["undeclared_terms"]["found"])
        )
    if not record["round_trip"]["equivalent"]:
        raise RDFError(
            "expanding and re-compacting the document does not denote the same graph: "
            + str(record["round_trip"]["difference"])
        )
    return {
        NQUADS_FILENAME: nquads(document, resolved, triples),
        TURTLE_FILENAME: turtle(document, resolved, triples),
        STATEMENT_FILENAME: json.dumps(record, ensure_ascii=False, indent=2) + "\n",
    }
