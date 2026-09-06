"""The `authorizes` verb: the three real answers, and the four ways there is no answer.

The whole point of this verb is that "no" is rare and expensive. A credential that
publishes no subject codes has not denied anything; an authorization this project excluded
has not stopped existing; a code the table never published is unknown. Each of those is a
separate answer here, and each is tested, because collapsing any of them into "no" would
publish a gap in this project as a fact about the Commission.

The two sources are held to each other: for every authorization the graph carries and
every subject any of them publishes, the graph and the re-derived catalog must reach the
same answer. Where they cannot agree, the difference is asserted rather than smoothed:
only the catalog records the exclusions and the cross-reference chain, and the graph's
answers say so in words.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chalkline import authorizes as module
from chalkline.authorizes import (
    Answer,
    AuthorizationView,
    Source,
    SourceUnreadable,
    SubjectView,
    ask,
    render_json,
    render_text,
    source_from_catalog,
    source_from_graph,
)
from chalkline.cli import main
from chalkline.model import build_catalog
from chalkline.sources import sort_table

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH = REPO_ROOT / "site" / "credentials.jsonld"


@pytest.fixture(scope="module")
def graph_source() -> Source:
    return source_from_graph(GRAPH)


@pytest.fixture(scope="module")
def catalog_source() -> Source:
    return source_from_catalog(build_catalog(sort_table.load()))


def view(
    *,
    title: str = "A Credential",
    document_codes: tuple[str, ...] = ("TC1",),
    codes: tuple[str, ...] = ("R1E",),
    subjects: tuple[SubjectView, ...] = (),
    resolution: str | None = None,
) -> AuthorizationView:
    return AuthorizationView(
        title=title,
        document_codes=document_codes,
        codes=codes,
        subjects=subjects,
        resolution=resolution,
    )


def source(*views: AuthorizationView, exclusions: tuple[module.ExcludedView, ...] = ()) -> Source:
    return Source(
        name="a synthetic source",
        authorizations=views,
        exclusions=exclusions,
        records_exclusions=bool(exclusions),
        records_reference_chain=False,
    )


BSS = SubjectView(code="BSS", name="Biological Sciences (Specialized)", notes=())
MATH = SubjectView(code="MATH", name="Mathematics", notes=())


# --- the two answers that answer the question ----------------------------------


def test_a_published_subject_answers_yes_with_the_row(graph_source: Source) -> None:
    result = ask(graph_source, code="R1E", subject_code="BSS", document="TC1")
    assert result.answer is Answer.AUTHORIZES
    assert result.exit_code == 0
    assert any("BSS" in line for line in result.evidence)


def test_a_subject_the_row_does_not_carry_answers_no(graph_source: Source) -> None:
    result = ask(graph_source, code="R1S", subject_code="BSS", document="TC1")
    assert result.answer is Answer.DOES_NOT_AUTHORIZE
    assert result.exit_code == 1
    assert any("subject codes published" in line for line in result.evidence)


def test_a_subject_can_be_asked_for_by_name(graph_source: Source) -> None:
    by_code = ask(graph_source, code="R1E", subject_code="BSS", document="TC1")
    by_name = ask(
        graph_source,
        code="R1E",
        subject_name="Biological Sciences (Specialized)",
        document="TC1",
    )
    assert by_name.answer is by_code.answer is Answer.AUTHORIZES


# --- the four answers that are not answers -------------------------------------


def test_an_authorization_with_no_subject_codes_is_not_a_denial() -> None:
    """The 66 NONE rows. "Not subject-coded", never "no"."""
    result = ask(source(view(subjects=())), code="R1E", subject_code="BSS")
    assert result.answer is Answer.NOT_SUBJECT_CODED
    assert result.exit_code == 2
    assert "not a denial" in result.detail


def test_every_authorization_the_graph_publishes_without_subjects_answers_that_way(
    graph_source: Source,
) -> None:
    """Over the real graph, not only the synthetic row."""
    bare = [v for v in graph_source.authorizations if not v.subjects and len(v.codes) == 1]
    assert bare, "the graph carries no subject-less authorization, so this proves nothing"
    for candidate in bare[:5]:
        result = ask(
            graph_source,
            code=candidate.codes[0],
            subject_code="BSS",
            document=candidate.document_codes[0] if candidate.document_codes else None,
        )
        assert result.answer in {Answer.NOT_SUBJECT_CODED, Answer.AMBIGUOUS}
        assert result.exit_code != 1, "a row with no subject codes must never exit 'no'"


def test_an_excluded_authorization_carries_its_recorded_reason(
    catalog_source: Source,
) -> None:
    """The issue's acceptance criterion: exit 2, with the reason."""
    assert catalog_source.exclusions, "the catalog records no exclusions to test"
    excluded = catalog_source.exclusions[0]
    result = ask(catalog_source, code=excluded.codes[0], subject_code="BSS")
    assert result.answer is Answer.NOT_MODELED
    assert result.exit_code == 2
    assert excluded.reason in " ".join(result.evidence)
    assert "gap in this project" in result.detail


def test_an_unknown_code_is_unknown_and_never_no(graph_source: Source) -> None:
    result = ask(graph_source, code="NOSUCHCODE", subject_code="BSS")
    assert result.answer is Answer.UNKNOWN_AUTHORIZATION
    assert result.exit_code == 2, "an unknown code must not share the 'no' exit code"
    assert "no authorization with Authorization Code" in result.detail


def test_the_graph_says_it_cannot_tell_excluded_from_never_published(
    graph_source: Source, catalog_source: Source
) -> None:
    """The one thing the published artifact genuinely cannot answer, said out loud."""
    excluded = catalog_source.exclusions[0]
    from_graph = ask(graph_source, code=excluded.codes[0], subject_code="BSS")
    assert from_graph.answer is Answer.UNKNOWN_AUTHORIZATION
    assert "--from-sources" in from_graph.detail
    assert not graph_source.records_exclusions

    from_catalog = ask(catalog_source, code=excluded.codes[0], subject_code="BSS")
    assert from_catalog.answer is Answer.NOT_MODELED


def test_a_subject_nobody_publishes_is_unknown_not_a_denial() -> None:
    result = ask(source(view(subjects=(MATH,))), code="R1E", subject_code="NOSUCH")
    assert result.answer is Answer.UNKNOWN_SUBJECT
    assert result.exit_code == 2


def test_a_code_on_several_rows_refuses_rather_than_choosing(graph_source: Source) -> None:
    result = ask(graph_source, code="R1S", subject_code="BSS")
    assert result.answer is Answer.AMBIGUOUS
    assert result.exit_code == 2
    assert len(result.matched) > 1
    assert "--document" in result.detail and "--title" in result.detail


# --- the two narrowing flags are two columns -----------------------------------


def test_document_matches_the_document_title_code_and_not_the_title() -> None:
    only = source(view(title="Single Subject Teaching Credential", document_codes=("TC1",)))
    assert ask(only, code="R1E", subject_code="BSS", document="TC1").answer is not (
        Answer.UNKNOWN_AUTHORIZATION
    )
    missed = ask(
        only,
        code="R1E",
        subject_code="BSS",
        document="Single Subject Teaching Credential",
    )
    assert missed.answer is Answer.UNKNOWN_AUTHORIZATION, (
        "--document must not silently match the Authorization Title; they are two "
        "columns and --title is the one that reads the other"
    )


def test_title_matches_the_authorization_title_as_a_substring() -> None:
    only = source(view(title="Single Subject Teaching Credential", subjects=(MATH,)))
    assert ask(only, code="R1E", subject_code="MATH", title="single subject").answer is (
        Answer.AUTHORIZES
    )


# --- the two sources agree -----------------------------------------------------


def test_the_graph_and_the_catalog_reach_the_same_answer_everywhere(
    graph_source: Source, catalog_source: Source
) -> None:
    """The issue's acceptance criterion, over every unambiguous row and a real subject set.

    Answers only. The evidence differs by design, because the graph does not publish the
    cross-reference chain, and that difference is asserted separately below.
    """
    by_identity = {v.identity: v for v in catalog_source.authorizations}
    compared = 0
    for view_from_graph in graph_source.authorizations:
        twin = by_identity.get(view_from_graph.identity)
        if twin is None:
            continue
        code = view_from_graph.codes[0] if view_from_graph.codes else None
        if code is None:
            continue
        document = view_from_graph.document_codes[0] if view_from_graph.document_codes else None
        for subject_code in ("BSS", "MATH", "NOSUCH"):
            left = ask(graph_source, code=code, subject_code=subject_code, document=document)
            right = ask(catalog_source, code=code, subject_code=subject_code, document=document)
            assert left.answer is right.answer, (
                f"{view_from_graph.label()} / {subject_code}: graph says "
                f"{left.answer} and the catalog says {right.answer}"
            )
            compared += 1
    assert compared > 200, f"only {compared} comparisons ran, which proves little"


def test_only_the_catalog_prints_the_chain_that_supplied_a_subject(
    graph_source: Source, catalog_source: Source
) -> None:
    """The issue's first acceptance criterion, and the honest half of the two-source split."""
    resolved = [v for v in catalog_source.authorizations if v.resolution]
    assert resolved, "no authorization was resolved by cross-reference"
    candidate = next(v for v in resolved if v.subjects and len(v.codes) >= 1)
    document = candidate.document_codes[0] if candidate.document_codes else None

    from_catalog = ask(
        catalog_source,
        code=candidate.codes[0],
        subject_code=candidate.subjects[0].code,
        document=document,
    )
    assert from_catalog.answer is Answer.AUTHORIZES
    chain = [line for line in from_catalog.evidence if "cross-reference" in line]
    assert chain, "the resolving credential is not named"
    assert "defers this scope to" in chain[0]

    from_graph = ask(
        graph_source,
        code=candidate.codes[0],
        subject_code=candidate.subjects[0].code,
        document=document,
    )
    assert from_graph.answer is Answer.AUTHORIZES
    assert not any("cross-reference" in line for line in from_graph.evidence), (
        "the graph does not publish the chain, and inventing one here would be the "
        "thing this test exists to prevent"
    )


# --- sources it must refuse ----------------------------------------------------


def test_a_missing_graph_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SourceUnreadable, match="no such file"):
        source_from_graph(tmp_path / "absent.jsonld")


def test_an_empty_graph_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "nothing-here.jsonld"
    path.write_text("", encoding="utf-8")
    with pytest.raises(SourceUnreadable, match="the file is empty"):
        source_from_graph(path)


def test_an_unparseable_graph_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "broken.jsonld"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(SourceUnreadable, match="not parseable"):
        source_from_graph(path)


def test_a_document_without_a_graph_array_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "other.jsonld"
    path.write_text(json.dumps({"@context": {}}), encoding="utf-8")
    with pytest.raises(SourceUnreadable, match="no @graph array"):
        source_from_graph(path)


def test_a_graph_with_no_licenses_is_refused_rather_than_answering_unknown(
    tmp_path: Path,
) -> None:
    """Every query against it would answer "unknown", which is not an empty answer."""
    path = tmp_path / "empty-graph.jsonld"
    path.write_text(json.dumps({"@graph": [{"@type": "ceterms:CredentialOrganization"}]}))
    with pytest.raises(SourceUnreadable, match="no ceterms:License node"):
        source_from_graph(path)


def test_asking_without_a_subject_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="exactly one of"):
        ask(source(view()), code="R1E")
    with pytest.raises(ValueError, match="exactly one of"):
        ask(source(view()), code="R1E", subject_code="BSS", subject_name="x")


def test_asking_without_a_code_is_a_programming_error() -> None:
    with pytest.raises(ValueError, match="authorization code"):
        ask(source(view()), code="  ", subject_code="BSS")


# --- renderings and exit codes through the command line -------------------------


def test_the_text_rendering_leads_with_the_answer() -> None:
    result = ask(source(view(subjects=(BSS,))), code="R1E", subject_code="BSS")
    assert render_text(result).startswith("authorizes: ")


def test_the_json_rendering_carries_the_answer_and_the_exit_code() -> None:
    result = ask(source(view(subjects=(BSS,))), code="R1E", subject_code="BSS")
    document = json.loads(render_json(result))
    assert document["answer"] == "authorizes"
    assert document["exit_code"] == 0
    assert document["matched"][0]["subject_codes_published"] == 1


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["--code", "R1E", "--document", "TC1", "--subject", "BSS"], 0),
        (["--code", "R1S", "--document", "TC1", "--subject", "BSS"], 1),
        (["--code", "R1S", "--subject", "BSS"], 2),
        (["--code", "NOSUCHCODE", "--subject", "BSS"], 2),
    ],
    ids=["yes", "no", "ambiguous", "unknown"],
)
def test_the_command_line_exit_codes(
    argv: list[str], expected: int, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["authorizes", *argv]) == expected
    assert capsys.readouterr().out.strip(), "an exit code with no printed answer"


def test_the_command_line_can_answer_from_the_sources(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["authorizes", "--code", "R3SE", "--subject", "BSS", "--from-sources"]) == 2
    out = capsys.readouterr().out
    assert "not_modeled" in out


def test_an_unreadable_source_exits_two_with_nothing_on_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["authorizes", "--code", "R1E", "--subject", "BSS", "--graph", str(tmp_path / "no.json")]
    )
    assert code == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no such file" in captured.err


def test_json_output_parses_from_the_command_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(["authorizes", "--code", "R1E", "--document", "TC1", "--subject", "BSS", "--json"])
        == 0
    )
    assert json.loads(capsys.readouterr().out)["answer"] == "authorizes"
