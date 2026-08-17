"""Check an emitted document against the CTDL schema Credential Engine publishes.

This is the mechanical form of "do not model from memory". Every claim the export makes
about CTDL is re-checked here against the vendored schema encoding
(``ctdl-schema.json``, provenance in the ``.source.json`` beside it), so a term that does
not exist, or a property used on a class the schema does not admit, fails the build instead
of shipping and failing in somebody else's validator later.

Four checks, in the order a reader would ask them:

1. **Class exists.** Every ``@type`` is an ``rdfs:Class`` in the schema.
2. **Property exists.** Every property key is an ``rdf:Property`` in the schema, and is
   also declared in the vendored JSON-LD context, so the emitted document is resolvable
   against the context it references.
3. **Domain admits the pairing.** The enclosing node's ``@type`` appears in the property's
   ``schema:domainIncludes``. This is the check that catches the plausible-looking mistake:
   ``ceterms:codedNotation`` reads like it belongs on a licence, and the schema does not put
   it there.
4. **Range admits the value.** A property whose range is CTDL classes takes either a nested
   node of one of those classes or a string IRI referencing one. A property whose range is a
   literal type takes a value of the matching JSON shape, with ``rdf:langString`` written as
   the language map the context declares. A language tag may carry one string or a list of
   strings; both are JSON-LD's ``@container: @language``, and the list form is what a
   property defined as a *single* condition needs in order to state several of them.

Findings are returned, not raised, so a caller can report all of them at once. The export
raises on any finding.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

SCHEMA_PATH: Final = Path(__file__).parent / "ctdl-schema.json"
CONTEXT_PATH: Final = Path(__file__).parent / "ctdl-context.json"

NODE_REFERENCE_RE: Final = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|_:)")
"""What a string standing in for a node has to look like: an absolute IRI, or a blank node.

A property whose range is CTDL classes may carry a string instead of a nested node, and that
string is a reference to such a node. Accepting *any* string there means a bare label sails
through in place of a reference nothing can follow, which is the same class of mistake this
module exists to catch on the other three checks. RFC 3986 makes the scheme the part that
tells an absolute IRI from a label, and JSON-LD adds ``_:`` for blank nodes."""

_LITERAL_SHAPES: Final = {
    "xsd:string": (str,),
    "xsd:anyURI": (str,),
    "xsd:language": (str,),
    "xsd:boolean": (bool,),
    "xsd:integer": (int,),
    "xsd:float": (float, int),
    "xsd:dateTime": (str,),
    "xsd:date": (str,),
    "xsd:duration": (str,),
}
"""JSON shapes the literal ranges this project emits are allowed to take."""


def load_schema(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """The vendored CTDL schema, keyed by term IRI."""
    document = json.loads((path or SCHEMA_PATH).read_text(encoding="utf-8"))
    return {term["@id"]: term for term in document["@graph"]}


def load_context(path: Path | None = None) -> dict[str, Any]:
    """The ``@context`` mapping from the vendored CTDL context."""
    document = json.loads((path or CONTEXT_PATH).read_text(encoding="utf-8"))
    context: dict[str, Any] = document["@context"]
    return context


def is_language_map(term: str, context: Mapping[str, Any]) -> bool:
    """Whether the context declares this term's values as a language map."""
    entry = context.get(term)
    return isinstance(entry, Mapping) and entry.get("@container") == "@language"


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else [value]


def _class_ranges(
    definition: Mapping[str, Any], schema: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """The CTDL classes a property's range admits, if any."""
    return [
        term
        for term in _as_list(definition.get("schema:rangeIncludes", []))
        if schema.get(term, {}).get("@type") == "rdfs:Class"
    ]


def _language_map_texts_ok(entry: Any) -> bool:
    """One language tag's value: a string, or a list of strings.

    JSON-LD's ``@container: @language`` admits both, and CTDL needs the list form for a
    property like ``ceterms:condition``, whose definition is a *single* constraint and which
    is therefore written once per constraint under the same language tag.
    """
    if isinstance(entry, str):
        return True
    return isinstance(entry, list) and bool(entry) and all(isinstance(x, str) for x in entry)


def _check_language_map(term: str, value: Any, path: str, findings: list[str]) -> None:
    """A language-mapped term takes ``{language tag: text or texts}`` and nothing else."""
    if not isinstance(value, Mapping):
        findings.append(
            f"{path}: {term} is a language map in the context, got {type(value).__name__}"
        )
    elif not value:
        # ``all()`` over no language tags is True, so without this an empty map is the one
        # shape of this property the check cannot see. A name nobody can read in any
        # language is not a name.
        findings.append(f"{path}: {term} is a language map with no language tags")
    elif not all(_language_map_texts_ok(entry) for entry in value.values()):
        findings.append(
            f"{path}: {term} language map holds something other than a string or a "
            "non-empty list of strings"
        )


def _check_item(
    term: str,
    item: Any,
    ranges: list[str],
    class_ranges: list[str],
    where: str,
    findings: list[str],
) -> None:
    """One value of a property, against the range the schema declares for it."""
    if isinstance(item, Mapping):
        if not class_ranges:
            findings.append(f"{where}: {term} has an object value but no class in its range")
        elif item.get("@type") not in class_ranges:
            findings.append(
                f"{where}: {term} holds a {item.get('@type')!r}, "
                f"its range is {sorted(class_ranges)}"
            )
        return
    if class_ranges and isinstance(item, str):
        # A string where a class is expected is an IRI reference to such a node, so it has
        # to be one. A bare label here is a reference that resolves to nothing.
        if not NODE_REFERENCE_RE.match(item):
            findings.append(
                f"{where}: {term} holds {item!r}, which is not an absolute IRI or a blank "
                f"node; a string standing in for a {sorted(class_ranges)} node has to "
                "reference one"
            )
        return
    allowed = tuple(shape for literal in ranges for shape in _LITERAL_SHAPES.get(literal, ()))
    if allowed and not isinstance(item, allowed):
        findings.append(f"{where}: {term} is {type(item).__name__}, its range is {sorted(ranges)}")


def _check_range(
    term: str,
    definition: Mapping[str, Any],
    value: Any,
    path: str,
    schema: Mapping[str, Mapping[str, Any]],
    context: Mapping[str, Any],
    findings: list[str],
) -> None:
    """Whether a property's value has a shape its declared range allows."""
    ranges = _as_list(definition.get("schema:rangeIncludes", []))
    if not ranges:
        return
    if is_language_map(term, context):
        _check_language_map(term, value, path, findings)
        return
    class_ranges = _class_ranges(definition, schema)
    for index, item in enumerate(_as_list(value)):
        where = f"{path}[{index}]" if isinstance(value, list) else path
        _check_item(term, item, ranges, class_ranges, where, findings)


def _check_node(
    node: Mapping[str, Any],
    path: str,
    schema: Mapping[str, Mapping[str, Any]],
    context: Mapping[str, Any],
    findings: list[str],
) -> None:
    declared = node.get("@type")
    if declared is None:
        findings.append(f"{path}: node has no @type")
        return
    if not isinstance(declared, str):
        findings.append(f"{path}: @type {declared!r} is not a single class name")
        return
    if schema.get(declared, {}).get("@type") != "rdfs:Class":
        findings.append(f"{path}: @type {declared!r} is not an rdfs:Class in the CTDL schema")
        return

    for term, value in node.items():
        if not term.startswith("@"):
            _check_property(declared, term, value, path, schema, context, findings)


def _check_property(
    declared: str,
    term: str,
    value: Any,
    path: str,
    schema: Mapping[str, Mapping[str, Any]],
    context: Mapping[str, Any],
    findings: list[str],
) -> None:
    """One property of one node: that it exists, belongs here, and holds an allowed value."""
    definition = schema.get(term)
    if definition is None:
        findings.append(f"{path}: {term} is not a term in the CTDL schema")
        return
    if definition.get("@type") != "rdf:Property":
        findings.append(f"{path}: {term} is not an rdf:Property")
        return
    if term not in context:
        findings.append(f"{path}: {term} is not declared in the CTDL JSON-LD context")
    domain = _as_list(definition.get("schema:domainIncludes", []))
    if domain and declared not in domain:
        findings.append(
            f"{path}: {term} is not in the domain of {declared} "
            f"(schema:domainIncludes has {len(domain)} classes, none of them this one)"
        )
    if isinstance(value, list) and not value:
        # Every check below walks the values, and walking none of them says nothing while
        # reporting no finding. A property present with an empty list asserts less than the
        # same property left out, which is the shape this export never means to emit.
        findings.append(f"{path}: {term} is an empty list, which asserts nothing")
        return
    _check_range(term, definition, value, f"{path}.{term}", schema, context, findings)

    # Recurse only where the range actually admits a nested node. A language map or any
    # other literal-ranged value is a leaf, and walking into it would report its language
    # tags as untyped nodes on top of the range finding already made.
    if not _class_ranges(definition, schema):
        return
    for index, item in enumerate(_as_list(value)):
        if isinstance(item, Mapping):
            where = f"{path}.{term}[{index}]" if isinstance(value, list) else f"{path}.{term}"
            _check_node(item, where, schema, context, findings)


def validate(
    document: Mapping[str, Any],
    schema: Mapping[str, Mapping[str, Any]] | None = None,
    context: Mapping[str, Any] | None = None,
) -> list[str]:
    """Every way an emitted document departs from the published CTDL schema."""
    schema = schema if schema is not None else load_schema()
    context = context if context is not None else load_context()
    findings: list[str] = []
    graph: Sequence[Any] = document.get("@graph", [])
    if not graph:
        findings.append("document has an empty @graph")
    for index, entity in enumerate(graph):
        if not isinstance(entity, Mapping):
            findings.append(f"@graph[{index}]: not an object")
            continue
        _check_node(entity, f"@graph[{index}]", schema, context, findings)
    return findings


def check(
    document: Mapping[str, Any],
    schema: Mapping[str, Mapping[str, Any]] | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Refuse to let a document through if the schema does not admit it."""
    findings = validate(document, schema, context)
    if findings:
        shown = findings[:10]
        more = f" (and {len(findings) - len(shown)} more)" if len(findings) > len(shown) else ""
        raise ValueError("document does not validate against CTDL: " + "; ".join(shown) + more)
