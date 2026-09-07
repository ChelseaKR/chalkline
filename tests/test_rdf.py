"""The RDF serializations, and the things that would make them a lie.

Three claims are under test, and each is measured rather than asserted:

* **Offline.** ``pyld`` installs a network document loader at import. Every test that touches
  the processor runs with ``socket.socket.connect`` replaced by a raise, so a build that
  reached ``credreg.net`` would fail here rather than quietly serialize whatever that host
  served.
* **Deterministic.** The N-Quads are the URDNA2015 canonical form. 9,153 of the 10,008 quads
  carry a blank node, so sorting alone would not make them stable.
* **Complete.** Nothing the document says is missing from the RDF, and nothing in the RDF was
  invented. The controls below inject the two shapes of undeclared term and assert the gate
  fails on each -- including the shape expansion cannot see.

Where the real graph is checked, and why not here
-------------------------------------------------

Every test that runs the processor runs it over a six-triple fixture, not over the published
890 KB graph. That is a measurement, not a preference: canonicalizing the real graph takes
about 25 seconds, and under ``coverage``'s tracer -- which fires on every call in every
module, pyld's included -- one export took over two minutes. A handful of those would have
turned a 52-second merge gate into a several-minute one.

So the split is deliberate. **This file proves the logic**, on a graph small enough to count
by hand. **`make rdf` proves the bytes**, by running `chalkline export --check` over the real
graph outside coverage, and `make verify` runs it. The tests below that touch the real graph
read the committed files rather than regenerating them, and
:func:`test_the_gate_that_holds_the_committed_bytes_is_still_in_verify` fails if that target
ever leaves the gate -- because from in here, a dropped gate and a passing one look the same.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from chalkline.ctdl import rdf

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
GRAPH = SITE / "credentials.jsonld"

#: Hand-counted, from the fixture below, by reading the six statements it makes:
#: the licence's type, its CTID, its name, its link to one subject; and that subject's type
#: and its name. Six triples, two subjects, one of them anonymous.
FIXTURE_TRIPLES = 6


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test in this file runs with the network removed from underneath it.

    Two things about how this is written, both deliberate.

    ``connect`` rather than the ``socket`` class: pyld's import of its own loaders pulls in
    ``ssl``, which subclasses ``socket.socket`` at import time, so replacing the class breaks
    the import instead of the connection and the test would pass for the wrong reason.

    The targets are strings rather than an ``import socket`` at the top of this file.
    ``tests/test_provenance.py`` scans every ``.py`` in this repository and fails when a file
    imports a networking module without being one of the three named in README.md and
    PROVENANCE.md as opening a socket. This file does the opposite of opening one, and adding
    it to that list would make both documents say something untrue about it. Keeping the
    reference out of the import graph keeps the scan's rule simple -- "imports a networking
    module" really does mean "can reach the network" -- and keeps that list short and honest.
    """

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("this code reached the network")

    monkeypatch.setattr("socket.socket.connect", refuse)
    monkeypatch.setattr("socket.create_connection", refuse)
    monkeypatch.setattr("socket.getaddrinfo", refuse)


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    with GRAPH.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = json.load(handle)
    return loaded


@pytest.fixture
def fixture_graph() -> dict[str, Any]:
    return {
        "@context": rdf.CTDL_CONTEXT_URL,
        "@graph": [
            {
                "@id": "https://example.org/a",
                "@type": "ceterms:License",
                "ceterms:ctid": "ce-1",
                "ceterms:name": {"en-US": "A"},
                "ceterms:subject": [
                    {
                        "@type": "ceterms:CredentialAlignmentObject",
                        "ceterms:targetNodeName": {"en-US": "S"},
                    }
                ],
            }
        ],
    }


@pytest.fixture(scope="module")
def committed() -> Iterator[dict[str, str]]:
    yield {
        name: (SITE / name).read_text(encoding="utf-8")
        for name in (rdf.NQUADS_FILENAME, rdf.TURTLE_FILENAME, rdf.STATEMENT_FILENAME)
    }


# ------------------------------------------------------------------------------------------
# Offline.
# ------------------------------------------------------------------------------------------


def test_the_whole_pipeline_runs_with_the_network_removed(fixture_graph: dict[str, Any]) -> None:
    """The autouse fixture is the assertion: reaching the network raises."""
    assert rdf.nquads(fixture_graph).count("\n") == FIXTURE_TRIPLES


def test_the_loader_refuses_every_url_but_the_vendored_context() -> None:
    loader = rdf.offline_document_loader()
    served = loader(rdf.CTDL_CONTEXT_URL)
    assert served["documentUrl"] == rdf.CTDL_CONTEXT_URL
    assert "@context" in served["document"]
    with pytest.raises(rdf.NetworkRefused, match="refused to load"):
        loader("https://credreg.net/ctdl/schema/context/json/../elsewhere")


def test_a_remote_context_is_refused_rather_than_fetched() -> None:
    """A document naming a context this repository has not vendored does not get one."""
    with pytest.raises(rdf.NetworkRefused, match="example.com"):
        rdf.nquads({"@context": "https://example.com/context.jsonld", "@graph": []})


def test_the_offline_loader_is_installed_globally_and_not_only_passed(
    fixture_graph: dict[str, Any],
) -> None:
    """pyld's default loader reaches the network. A call that forgot to pass options would
    use it, so the module installs the offline loader as the default too."""
    from pyld import jsonld

    rdf.nquads(fixture_graph)
    installed = jsonld.get_document_loader()
    with pytest.raises(rdf.NetworkRefused):
        installed("https://example.com/anything")


# ------------------------------------------------------------------------------------------
# Determinism.
# ------------------------------------------------------------------------------------------


def test_the_nquads_are_byte_identical_across_runs(fixture_graph: dict[str, Any]) -> None:
    assert rdf.nquads(fixture_graph) == rdf.nquads(fixture_graph)


def test_the_turtle_is_byte_identical_across_runs(fixture_graph: dict[str, Any]) -> None:
    assert rdf.turtle(fixture_graph) == rdf.turtle(fixture_graph)


def test_canonical_labels_are_what_makes_the_output_stable_not_sorting(
    document: dict[str, Any], committed: dict[str, str]
) -> None:
    """Sorted is not stable. Most of this graph's triples name an anonymous node, and a
    label assigned by insertion order would sort consistently within one run and differ
    between two. The labels here come out of URDNA2015 instead."""
    lines = committed[rdf.NQUADS_FILENAME].splitlines()
    blank = [line for line in lines if "_:" in line]
    assert len(blank) > len(lines) // 2
    assert all(label.startswith("_:c14n") for line in blank for label in _labels(line))


def _labels(line: str) -> list[str]:
    return [token for token in line.split(" ") if token.startswith("_:")]


# ------------------------------------------------------------------------------------------
# Completeness: the two shapes of undeclared term.
# ------------------------------------------------------------------------------------------


def test_an_undeclared_bare_term_is_reported(fixture_graph: dict[str, Any]) -> None:
    """Control. A bare key the context does not define is dropped on expansion in silence."""
    before = rdf.nquads(fixture_graph)
    sabotaged = copy.deepcopy(fixture_graph)
    sabotaged["@graph"][0]["notARealTerm"] = "x"

    assert rdf.nquads(sabotaged) == before, "expansion should have dropped it, silently"
    assert rdf.undeclared_terms(sabotaged) == ["notARealTerm"]
    with pytest.raises(rdf.RDFError, match="notARealTerm"):
        rdf.artifacts(sabotaged)


def test_an_undeclared_prefixed_term_is_reported_though_expansion_keeps_it(
    fixture_graph: dict[str, Any],
) -> None:
    """Control, and the more dangerous shape.

    ``ceterms:notARealTerm`` is *not* dropped: the context declares ``ceterms`` as a prefix,
    so the processor resolves the compact IRI whether or not that term exists, and the triple
    count goes **up**. A round-trip gate alone would pass this. Measured on the real graph
    while writing this: adding one such key left the quad count higher, not equal.
    """
    before = rdf.nquads(fixture_graph)
    sabotaged = copy.deepcopy(fixture_graph)
    sabotaged["@graph"][0]["ceterms:notARealTerm"] = "x"

    after = rdf.nquads(sabotaged)
    assert after != before
    assert after.count("\n") == before.count("\n") + 1, "expansion kept it; only the check sees it"
    assert rdf.round_trip_difference(sabotaged) is None, "and the round-trip is still clean"

    assert rdf.undeclared_terms(sabotaged) == ["ceterms:notARealTerm"]
    with pytest.raises(rdf.RDFError, match="ceterms:notARealTerm"):
        rdf.artifacts(sabotaged)


def test_class_names_are_not_reported_because_the_context_declares_no_classes(
    document: dict[str, Any],
) -> None:
    """``ceterms:License`` is not a key in the vendored context; no class is. Checking
    ``@type`` values against it would report every class in a correct document, which is why
    :mod:`chalkline.ctdl.validate` checks classes against the vendored *schema* instead."""
    declarations = rdf._declarations(rdf.vendored_context())
    assert "ceterms:name" in declarations
    assert "ceterms:License" not in declarations
    assert rdf.undeclared_terms(document) == []


def test_language_map_keys_are_values_and_not_terms(fixture_graph: dict[str, Any]) -> None:
    """``{"ceterms:name": {"en-US": "A"}}`` uses one term, not two. Reading the tag as a term
    reported 3,492 undeclared terms on the real graph before this was fixed."""
    assert "ceterms:name" in rdf._language_map_terms(rdf._declarations(rdf.vendored_context()))
    assert rdf.undeclared_terms(fixture_graph) == []


def test_the_allowlist_is_justified_by_the_graph_being_unchanged_without_it(
    document: dict[str, Any], fixture_graph: dict[str, Any]
) -> None:
    """``comment`` is allowed to be undeclared. The justification is that removing it leaves
    the canonical N-Quads byte-identical, so it carries no triple and hides nothing."""
    assert set(rdf.UNDECLARED_BY_DESIGN) == {"comment"}
    assert "comment" in document
    assert rdf.undeclared_terms(document) == []

    with_comment = dict(fixture_graph, comment="prose for a human reader")
    assert rdf.nquads(with_comment) == rdf.nquads(fixture_graph)
    assert rdf.undeclared_terms(with_comment) == []


# ------------------------------------------------------------------------------------------
# The round-trip, and why it is not a text comparison.
# ------------------------------------------------------------------------------------------


def test_the_round_trip_denotes_the_same_graph(fixture_graph: dict[str, Any]) -> None:
    assert rdf.round_trip_difference(fixture_graph) is None


def test_the_round_trip_is_compared_as_quads_because_the_json_text_always_differs(
    fixture_graph: dict[str, Any],
) -> None:
    """The measurement behind the design.

    Compacting the expansion of the real document differs textually from the document on all
    134 entities and always will: expansion lowercases ``en-US`` to ``en-us`` as the JSON-LD
    API requires, and compaction collapses single-element arrays. A gate that compared the
    JSON would have been red on a correct document from its first run.
    """
    from pyld import jsonld

    options = rdf._options(rdf.vendored_context())
    compacted = jsonld.compact(
        jsonld.expand(fixture_graph, options), fixture_graph["@context"], options
    )
    assert compacted != fixture_graph
    assert rdf.nquads(compacted) == rdf.nquads(fixture_graph)


A = "<https://example.org/a> <https://example.org/p> \"1\" .\n"
B = "<https://example.org/b> <https://example.org/p> \"2\" .\n"


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        (A, A, None),
        (A + B, A, "1 triple(s) lost, first: " + B.strip()),
        (A, A + B, "1 triple(s) gained, first: " + B.strip()),
        (A, B, "1 triple(s) lost, first: " + A.strip() + "; 1 triple(s) gained, first: " + B.strip()),
        (A + A + B, A + B + B, "the quad sets differ in multiplicity only"),
    ],
)
def test_the_difference_report_names_what_moved(
    before: str, after: str, expected: str | None
) -> None:
    """The reporter, driven with graphs that really do differ.

    The round trip over this project's graph does not differ, so without this the reporting
    branch would be code nobody had ever seen run -- and the first time it ran would be the
    day something was already wrong.
    """
    assert rdf.describe_difference(before, after) == expected


def test_artifacts_refuses_to_write_when_the_round_trip_moved(
    fixture_graph: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A serialization that lost a triple is exactly what this verb exists to catch, and
    GitHub Pages uploads the whole directory, so noting the problem beside the file would
    publish it anyway."""
    monkeypatch.setattr(rdf, "round_trip_difference", lambda *a, **k: "1 triple(s) lost")
    with pytest.raises(rdf.RDFError, match="does not denote the same graph"):
        rdf.artifacts(fixture_graph)


def test_a_processor_error_that_is_not_a_refusal_is_left_alone() -> None:
    """The refusal is unwrapped from pyld's own error; everything else keeps its own type."""
    with pytest.raises(ValueError, match="not a refusal"), rdf._surfacing_a_refused_load():
        raise ValueError("not a refusal")


def test_named_graphs_are_refused_rather_than_flattened() -> None:
    """This project publishes one graph. A quad in a second one would be dropped by a
    serializer that only wrote the default graph, which is absence rendered as completeness."""
    monkeypatched = {"@default": [], "https://example.org/g": []}

    class _Fake:
        @staticmethod
        def normalize(_doc: object, _options: object) -> dict[str, list[object]]:
            return monkeypatched

        @staticmethod
        def set_document_loader(_loader: object) -> None:
            return None

    original = rdf._jsonld
    rdf._jsonld = lambda: _Fake()  # type: ignore[assignment]
    try:
        with pytest.raises(rdf.RDFError, match="named graphs"):
            rdf.quads({})
    finally:
        rdf._jsonld = original  # type: ignore[assignment]


# ------------------------------------------------------------------------------------------
# Counts, and the statement beside the files.
# ------------------------------------------------------------------------------------------


def test_the_fixture_graph_has_exactly_the_triples_counted_by_hand(
    fixture_graph: dict[str, Any],
) -> None:
    assert len(rdf.quads(fixture_graph)) == FIXTURE_TRIPLES


def test_the_statement_records_that_each_check_ran_not_only_that_none_failed(
    committed: dict[str, str],
) -> None:
    """A check that never ran cannot fail. Both checks record their own having happened, so
    an empty ``found`` list cannot be mistaken for an unasked question."""
    statement = json.loads(committed[rdf.STATEMENT_FILENAME])
    assert statement["round_trip"]["checked"] is True
    assert statement["undeclared_terms"]["checked"] is True
    assert statement["round_trip"]["equivalent"] is True
    assert statement["undeclared_terms"]["found"] == []
    assert set(statement["undeclared_terms"]["allowed_by_review"]) == set(rdf.UNDECLARED_BY_DESIGN)


def test_the_statement_counts_agree_with_the_files_beside_it(committed: dict[str, str]) -> None:
    statement = json.loads(committed[rdf.STATEMENT_FILENAME])
    assert statement["triples"] == len(committed[rdf.NQUADS_FILENAME].splitlines())
    assert sum(statement["predicates"].values()) == statement["triples"]
    assert 0 < statement["triples_naming_a_blank_node"] < statement["triples"]
    for name in (rdf.NQUADS_FILENAME, rdf.TURTLE_FILENAME):
        recorded = statement["files"][name]
        assert recorded["bytes"] == len(committed[name].encode("utf-8"))


def test_the_gate_that_holds_the_committed_bytes_is_still_in_verify() -> None:
    """The committed serializations are held to a fresh export by `make rdf`, not from here.

    Regenerating the real graph inside this suite would cost the merge gate minutes under
    coverage, so the byte comparison lives in a target that runs without it. That makes this
    file dependent on a gate it cannot run -- and a gate silently dropped from `verify` looks
    exactly like a gate that passed. So the dependency is asserted rather than assumed, and
    `chalkline check` is asserted to name the same gate in the exemption it prints.
    """
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    verify = next(line for line in makefile.splitlines() if line.startswith("verify:"))
    assert " rdf " in f" {verify.split(':', 1)[1].strip()} "
    assert "\nrdf:\n\t$(UVRUN) chalkline export --check\n" in makefile

    from chalkline.cli import PUBLISHED_BY_ANOTHER_GATE

    for name in (rdf.NQUADS_FILENAME, rdf.TURTLE_FILENAME, rdf.STATEMENT_FILENAME):
        assert "make rdf" in PUBLISHED_BY_ANOTHER_GATE[name]


# ------------------------------------------------------------------------------------------
# Turtle, checked by a parser this project did not write.
# ------------------------------------------------------------------------------------------


def test_rdflib_reads_the_turtle_as_the_same_graph_as_the_ntriples(
    fixture_graph: dict[str, Any],
) -> None:
    """The independent opinion. rdflib parses both serializations and is asked whether they
    are the same graph -- isomorphism, not set equality, because rdflib mints its own blank
    node labels on parse and the two parses cannot share them."""
    import rdflib
    from rdflib.compare import isomorphic

    from_nt = rdflib.Graph()
    from_nt.parse(data=rdf.nquads(fixture_graph), format="nt")
    from_ttl = rdflib.Graph()
    from_ttl.parse(data=rdf.turtle(fixture_graph), format="turtle")

    assert len(from_nt) == FIXTURE_TRIPLES
    assert isomorphic(from_nt, from_ttl)


@pytest.mark.slow
def test_rdflib_reads_the_published_turtle_and_ntriples_as_the_same_statements(
    committed: dict[str, str],
) -> None:
    """The same question against the real graph, with a cheaper answer.

    Full isomorphism over 10,008 triples and ~1,600 blank nodes takes minutes, so this
    compares what does not depend on blank node labelling: every fully-grounded triple, and
    the multiset of statements each blank node participates in. A lost triple, a mangled
    literal or a mis-shortened IRI fails this; only a relabelling survives it.
    """
    import rdflib

    from_nt = rdflib.Graph()
    from_nt.parse(data=committed[rdf.NQUADS_FILENAME], format="nt")
    from_ttl = rdflib.Graph()
    from_ttl.parse(data=committed[rdf.TURTLE_FILENAME], format="turtle")

    assert len(from_nt) == len(from_ttl) == len(committed[rdf.NQUADS_FILENAME].splitlines())
    assert _grounded(from_nt) == _grounded(from_ttl)
    assert _shapes(from_nt) == _shapes(from_ttl)


def _grounded(graph: Any) -> set[tuple[str, str, str]]:
    import rdflib

    return {
        (str(s), str(p), str(o))
        for s, p, o in graph
        if not isinstance(s, rdflib.BNode) and not isinstance(o, rdflib.BNode)
    }


def _shapes(graph: Any) -> dict[tuple[str, str], int]:
    """How often each (predicate, object-or-anonymous) pair occurs, blank nodes anonymised."""
    import rdflib

    counts: dict[tuple[str, str], int] = {}
    for _, predicate, obj in graph:
        key = (str(predicate), "_:" if isinstance(obj, rdflib.BNode) else str(obj))
        counts[key] = counts.get(key, 0) + 1
    return counts


# ------------------------------------------------------------------------------------------
# Turtle mechanics.
# ------------------------------------------------------------------------------------------


def test_only_the_prefixes_the_body_uses_are_declared(fixture_graph: dict[str, Any]) -> None:
    turtle = rdf.turtle(fixture_graph)
    declared = {line.split()[1].rstrip(":") for line in turtle.splitlines() if line.startswith("@")}
    assert declared == {"ceterms"}


def test_a_prefix_shaped_string_inside_a_literal_does_not_forge_a_declaration() -> None:
    """The prefixes are read off the terms, never scraped back out of the rendered text."""
    document = {
        "@context": rdf.CTDL_CONTEXT_URL,
        "@graph": [
            {
                "@id": "https://example.org/a",
                "@type": "ceterms:License",
                "ceterms:ctid": "skos: dct: not a prefix",
            }
        ],
    }
    turtle = rdf.turtle(document)
    declared = {line.split()[1].rstrip(":") for line in turtle.splitlines() if line.startswith("@")}
    assert declared == {"ceterms"}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('a "quoted" word', 'a \\"quoted\\" word'),
        ("back\\slash", "back\\\\slash"),
        ("two\nlines", "two\\nlines"),
        ("a\ttab", "a\\ttab"),
    ],
)
def test_literals_are_escaped_rather_than_emitted_raw(value: str, expected: str) -> None:
    """A raw newline or quote inside a literal produces a file that parses as a *different*
    graph, or as none at all, which is worse than failing to write one."""
    assert rdf._escape_literal(value) == expected


def test_an_iri_whose_local_name_is_unsafe_is_written_in_full() -> None:
    """Turtle's PN_LOCAL production allows escapes and dots; getting those subtly wrong makes
    a file that parses as a different graph. Anything outside a conservative name is written
    as a full IRI, which is always correct."""
    prefixes = {"ex": "https://example.org/"}
    assert rdf._shorten("https://example.org/name", prefixes) == ("ex:name", "ex")
    assert rdf._shorten("https://example.org/has.dot", prefixes) == (
        "<https://example.org/has.dot>",
        None,
    )
    assert rdf._shorten("https://elsewhere.test/x", prefixes) == (
        "<https://elsewhere.test/x>",
        None,
    )


def test_the_longest_namespace_wins_and_a_tie_is_broken_by_name() -> None:
    prefixes = {"a": "https://example.org/", "b": "https://example.org/deep/", "c": "https://example.org/"}
    assert rdf._shorten("https://example.org/deep/x", prefixes) == ("b:x", "b")
    assert rdf._shorten("https://example.org/x", prefixes) == ("a:x", "a")
