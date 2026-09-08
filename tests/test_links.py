"""Link verdicts, and the three things about them that are load-bearing.

1. No verdict file must never render as "0 unreachable". Not checked and nothing
   wrong are different statements and only the first one is true of this repository
   today.
2. ``credentials.jsonld`` is byte-identical with and without a verdict file. A
   redirect is annotated, never followed into the graph.
3. Every sentence this produces is an observation about one run. "We could not
   reach it" is supportable from one request; "the Commission's page is gone" is not.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from chalkline import links
from chalkline.attachment import attach
from chalkline.ctdl import export as export_module
from chalkline.model import build_catalog
from chalkline.site import render
from chalkline.sources import leaflet_pages, sort_table
from chalkline.sources import leaflets as leaflets_module

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = REPO_ROOT / "site" / "credentials.jsonld"


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    return loaded


def _verdicts(document: dict[str, Any], **overrides: str) -> links.Verdicts:
    """A verdict file covering every URL the committed graph publishes."""
    urls = links.commission_urls(document)
    return links.Verdicts(
        checked="2026-09-06",
        entries=tuple(
            links.Verdict(
                url=url,
                verdict=overrides.get(url, links.ALIVE),
                checked="2026-09-06",
                status=200,
                final_url=url,
                title="Commission on Teacher Credentialing",
            )
            for url in urls
        ),
    )


# --- what the graph publishes ---------------------------------------------


def test_the_urls_checked_are_the_distinct_commission_urls(document: dict[str, Any]) -> None:
    urls = links.commission_urls(document)
    assert urls == sorted(set(urls))
    assert urls, "the graph publishes Commission URLs and this found none"
    assert all(url.startswith("https://www.ctc.ca.gov/") for url in urls)


def test_distinct_urls_and_published_references_are_reported_as_different_numbers(
    document: dict[str, Any],
) -> None:
    """Most of the 133 subjectWebpage values are the same address.

    Publishing only the occurrence count would say a run made far more requests
    than it made; publishing only the distinct count would understate how much of
    the graph one dead URL takes down.
    """
    block = links.summary(document, None)
    assert block["references_published"] > block["urls_published"]
    assert block["urls_published"] == len(links.commission_urls(document))


def test_a_url_added_anywhere_in_the_graph_is_found(document: dict[str, Any]) -> None:
    """The collector walks every string, not a hand-kept list of URL-bearing keys."""
    before = set(links.commission_urls(document))
    extended = json.loads(json.dumps(document))
    extended["@graph"].append(
        {"@type": "ceterms:License", "ceterms:someNewProperty": "https://www.ctc.ca.gov/new/"}
    )
    assert set(links.commission_urls(extended)) - before == {"https://www.ctc.ca.gov/new/"}


def test_a_non_commission_url_is_not_checked(document: dict[str, Any]) -> None:
    extended = json.loads(json.dumps(document))
    extended["@graph"].append({"@id": "https://example.invalid/page"})
    assert links.commission_urls(extended) == links.commission_urls(document)


# --- the absence rule -----------------------------------------------------


def test_no_verdict_file_publishes_every_link_as_filed_and_says_so(
    document: dict[str, Any],
) -> None:
    block = links.summary(document, None)
    assert block["state"] == "not_checked"
    assert block["note"] == links.NOT_CHECKED_NOTE
    # The whole point: no count of unreachable exists, so nothing can read as zero.
    assert "verdicts" not in block
    assert "unreachable" not in json.dumps(block)


def test_the_committed_coverage_says_no_link_check_has_been_run() -> None:
    """The published statement, not a reconstruction of it."""
    coverage = json.loads((REPO_ROOT / "site" / "coverage.json").read_text(encoding="utf-8"))
    assert coverage["link_verdicts"]["state"] == "not_checked"
    assert "not the same statement as every link working" in coverage["link_verdicts"]["note"]


def test_a_missing_verdict_file_is_none_and_not_an_empty_run(tmp_path: Path) -> None:
    assert links.load(tmp_path / "absent.json") is None


def test_a_url_the_run_never_reached_is_counted_apart(document: dict[str, Any]) -> None:
    """Not rolled into `alive`, and not into `indeterminate` either."""
    verdicts = _verdicts(document)
    short = links.Verdicts(checked=verdicts.checked, entries=verdicts.entries[1:])
    block = links.summary(document, short)
    assert block["urls_without_a_verdict"] == 1
    assert block["urls_with_a_verdict"] == block["urls_published"] - 1


def test_a_verdict_for_a_url_the_graph_no_longer_publishes_is_reported(
    document: dict[str, Any],
) -> None:
    verdicts = _verdicts(document)
    stale = links.Verdicts(
        checked=verdicts.checked,
        entries=(
            *verdicts.entries,
            links.Verdict(
                url="https://www.ctc.ca.gov/gone/",
                verdict=links.ALIVE,
                checked="2026-09-06",
                status=200,
                final_url=None,
                title=None,
            ),
        ),
    )
    assert links.summary(document, stale)["verdicts_for_urls_no_longer_published"] == 1


# --- a recorded run -------------------------------------------------------


def test_one_unreachable_is_rendered_on_the_page_and_counted(
    document: dict[str, Any],
) -> None:
    url = links.commission_urls(document)[0]
    verdicts = _verdicts(document, **{url: links.UNREACHABLE})
    block = links.summary(document, verdicts)
    assert block["state"] == "recorded"
    assert block["checked"] == "2026-09-06"
    assert block["verdicts"][links.UNREACHABLE] == 1
    note = links.page_note(document, verdicts)
    assert "1 that it could not reach" in note
    assert "2026-09-06" in note


def test_every_sentence_is_about_the_run_and_not_about_the_commission(
    document: dict[str, Any],
) -> None:
    url = links.commission_urls(document)[0]
    for verdicts in (None, _verdicts(document, **{url: links.UNREACHABLE})):
        note = links.page_note(document, verdicts)
        lowered = note.lower()
        for forbidden in (
            "the page is gone",
            "no longer exists",
            "the commission removed",
            "broken link",
            "dead link",
            "404",
        ):
            assert forbidden not in lowered, f"{forbidden!r} is a claim about the Commission"
        assert "this project" in lowered or "run" in lowered


def test_a_redirect_is_annotated_and_never_rewritten(document: dict[str, Any]) -> None:
    url = links.commission_urls(document)[0]
    verdicts = _verdicts(document, **{url: links.REDIRECTED_OFF_SITE})
    assert links.summary(document, verdicts)["verdicts"][links.REDIRECTED_OFF_SITE] == 1
    assert url in links.commission_urls(document)


# --- the note is about what was observed, not about the file it is written in --
#
# `Verdicts.checked` is the date the file was written. `scripts/check_links.py`
# writes it on every run and carries forward every verdict younger than
# EXPIRY_DAYS, so a second quarterly run inside the expiry requests nothing and
# restamps the file with the day it ran. Reading the note off that stamp turned a
# run that made zero requests into "A link check run on <today> requested each
# distinct Commission URL once. It observed 14 reachable." Both halves of that
# sentence are pinned below.


def _carried_forward(document: dict[str, Any], observed: str, written: str) -> links.Verdicts:
    """A file written on ``written`` whose every row was observed on ``observed``."""
    return links.Verdicts(
        checked=written,
        entries=tuple(
            links.Verdict(
                url=url,
                verdict=links.ALIVE,
                checked=observed,
                status=200,
                final_url=url,
                title=None,
            )
            for url in links.commission_urls(document)
        ),
    )


def test_the_note_dates_the_observations_and_not_the_file_they_were_written_in(
    document: dict[str, Any],
) -> None:
    """The re-run that requests nothing. It must not read as a check made today."""
    verdicts = _carried_forward(document, observed="2026-07-01", written="2026-09-08")
    note = links.page_note(document, verdicts)
    assert "2026-07-01" in note
    assert "2026-09-08" not in note, (
        "the note dated fourteen observations to the day the file was rewritten, on a "
        f"run that requested nothing: {note}"
    )


def test_the_observation_window_is_read_from_the_rows_rather_than_the_stamp(
    document: dict[str, Any],
) -> None:
    """The window is a fact about the rows, and the stamp is not one of them."""
    verdicts = _carried_forward(document, observed="2026-07-01", written="2026-09-08")
    covered = links.coverage_of(document, verdicts)
    assert (covered.first, covered.last) == ("2026-07-01", "2026-07-01")
    assert covered.one_day is True
    assert covered.covered == covered.published == len(links.commission_urls(document))
    assert covered.uncovered == 0


def test_observations_spread_over_several_days_are_reported_as_a_window(
    document: dict[str, Any],
) -> None:
    """The ordinary state of a carried-forward file: some rows old, some new."""
    fresh = _carried_forward(document, observed="2026-09-08", written="2026-09-08")
    mixed = links.Verdicts(
        checked="2026-09-08",
        entries=(
            links.Verdict(
                url=fresh.entries[0].url,
                verdict=links.ALIVE,
                checked="2026-06-20",
                status=200,
                final_url=fresh.entries[0].url,
                title=None,
            ),
            *fresh.entries[1:],
        ),
    )
    covered = links.coverage_of(document, mixed)
    assert (covered.first, covered.last) == ("2026-06-20", "2026-09-08")
    assert covered.one_day is False
    note = links.page_note(document, mixed)
    assert "between 2026-06-20 and 2026-09-08" in note
    assert "not the date the file was written" in note


def test_the_single_day_form_survives_when_every_observation_shares_a_date(
    document: dict[str, Any],
) -> None:
    """Positive control: the window form must not be unconditional.

    Without this, a note that always said "between X and X" would satisfy every
    assertion above while being worse prose than what it replaced.
    """
    note = links.page_note(document, _verdicts(document))
    assert note.startswith("A link check run on 2026-09-06 requested")
    assert "between" not in note


def test_a_published_url_no_observation_covers_is_named_in_the_note(
    document: dict[str, Any],
) -> None:
    """`summary` has counted this since the module was written. The note did not.

    A URL the graph gained after the last check has no verdict, so it contributes
    to none of the five counts. Leaving it out of the sentence published thirteen
    observations under a claim that each of fourteen URLs had been requested.
    """
    full = _verdicts(document)
    short = links.Verdicts(checked=full.checked, entries=full.entries[1:])
    published = len(links.commission_urls(document))
    note = links.page_note(document, short)
    assert f"requested {published - 1} of the {published}" in note
    assert f"1 of the {published}" in note
    assert "have not been requested by this project" in note
    assert links.summary(document, short)["urls_without_a_verdict"] == 1


def test_a_complete_run_says_nothing_about_urls_it_did_not_request(
    document: dict[str, Any],
) -> None:
    """The other side of it: the clause is conditional, not decoration."""
    assert "have not been requested by this project" not in links.page_note(
        document, _verdicts(document)
    )


def test_a_verdict_file_about_urls_this_graph_no_longer_publishes_covers_nothing(
    document: dict[str, Any],
) -> None:
    """Zero covered rows must not render as a run that found nothing wrong.

    This is the module's own no-file rule one level down: counts of zero across
    five verdicts read as a clean bill of health, and the true statement is that
    nothing here is about the addresses the graph publishes now.
    """
    orphaned = links.Verdicts(
        checked="2026-09-06",
        entries=(
            links.Verdict(
                url="https://www.ctc.ca.gov/gone/",
                verdict=links.ALIVE,
                checked="2026-09-06",
                status=200,
                final_url=None,
                title=None,
            ),
        ),
    )
    covered = links.coverage_of(document, orphaned)
    assert covered.covered == 0 and covered.first is None and covered.one_day is False
    note = links.page_note(document, orphaned)
    assert "none of it is about" in note
    assert "not the same statement as every link working" in note
    assert "reachable" not in note, f"a run covering nothing counted something: {note}"


def test_the_coverage_window_reaches_coverage_json(document: dict[str, Any]) -> None:
    """A reader of the artifact gets the observation dates, not only the stamp."""
    block = links.summary(document, _carried_forward(document, "2026-07-01", "2026-09-08"))
    assert block["checked"] == "2026-09-08"
    assert block["observed_first"] == "2026-07-01"
    assert block["observed_last"] == "2026-07-01"


def test_every_note_shape_is_about_the_run_and_not_about_the_commission(
    document: dict[str, Any],
) -> None:
    """The rule at the top of this file, applied to the branches added since.

    `test_every_sentence_is_about_the_run_and_not_about_the_commission` covers the
    no-file and one-day shapes. A new shape that quietly made a claim about the
    Commission would pass it by never being rendered.
    """
    url = links.commission_urls(document)[0]
    full = _verdicts(document, **{url: links.UNREACHABLE})
    shapes = (
        _carried_forward(document, "2026-07-01", "2026-09-08"),
        links.Verdicts(checked=full.checked, entries=full.entries[1:]),
        links.Verdicts(
            checked="2026-09-06",
            entries=(
                links.Verdict(
                    url="https://www.ctc.ca.gov/gone/",
                    verdict=links.UNREACHABLE,
                    checked="2026-09-06",
                    status=404,
                    final_url=None,
                    title=None,
                ),
            ),
        ),
    )
    for verdicts in shapes:
        note = links.page_note(document, verdicts)
        lowered = note.lower()
        for forbidden in (
            "the page is gone",
            "no longer exists",
            "the commission removed",
            "broken link",
            "dead link",
            "404",
        ):
            assert forbidden not in lowered, f"{forbidden!r} is a claim about the Commission"
        assert "this project" in lowered or "run" in lowered


# --- the graph does not move -----------------------------------------------


def _built(link_verdicts: links.Verdicts | None) -> tuple[str, str, str]:
    catalog = build_catalog(sort_table.load())
    index = leaflets_module.load_index()
    attachments = attach(
        catalog, leaflets_module.index_by_title(index.leaflets), published=index.leaflets
    )
    vendored = leaflet_pages.available()
    ctids = _ledger()
    graph = export_module.project_graph(catalog, ctids, attachments)
    statement = export_module.coverage(graph, catalog, attachments, index, vendored, link_verdicts)
    export_module.check_coverage(
        statement, graph, catalog, attachments, index, vendored, link_verdicts
    )
    return (
        export_module.serialize(graph),
        export_module.serialize(statement),
        render(catalog, ctids, attachments, links.page_note(graph, link_verdicts)),
    )


def _ledger() -> dict[str, str]:
    from chalkline import ctid as ctid_module

    return ctid_module.load_ledger()


def test_credentials_jsonld_is_byte_identical_with_and_without_a_verdict_file(
    document: dict[str, Any],
) -> None:
    """A verdict annotates. It cannot change what the graph asserts."""
    without_graph, without_coverage, without_page = _built(None)
    with_graph, with_coverage, with_page = _built(_verdicts(document))
    assert without_graph == with_graph
    assert without_coverage != with_coverage
    assert without_page != with_page


def test_a_recorded_run_changes_only_the_link_block(document: dict[str, Any]) -> None:
    _, without, _ = _built(None)
    _, recorded, _ = _built(_verdicts(document))
    before = json.loads(without)
    after = json.loads(recorded)
    differing = {key for key in before | after if before.get(key) != after.get(key)}
    assert differing == {"link_verdicts"}


# --- reading a verdict file -------------------------------------------------


def _document(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "checked": "2026-09-06",
        "verdicts": [
            {
                "url": "https://www.ctc.ca.gov/",
                "verdict": links.ALIVE,
                "checked": "2026-09-06",
                "status": 200,
                "final_url": "https://www.ctc.ca.gov/",
                "title": "Commission on Teacher Credentialing",
            }
        ],
    }
    return base | overrides


def test_a_well_formed_verdict_file_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "link-verdicts.json"
    parsed = links.parse(_document())
    path.write_text(links.serialize(parsed), encoding="utf-8")
    assert links.load(path) == parsed


@pytest.mark.parametrize(
    "overrides",
    [
        {"checked": "not a date"},
        {"checked": 20260906},
        {"verdicts": []},
        {"verdicts": "alive"},
        {"verdicts": [{"url": "https://www.ctc.ca.gov/", "verdict": "probably alive"}]},
        {"verdicts": [{"url": "https://example.invalid/", "verdict": links.ALIVE}]},
        {
            "verdicts": [
                {"url": "https://www.ctc.ca.gov/", "verdict": links.ALIVE, "checked": "soon"}
            ]
        },
        {
            "verdicts": [
                {
                    "url": "https://www.ctc.ca.gov/",
                    "verdict": links.ALIVE,
                    "checked": "2026-09-06",
                    "status": "200",
                }
            ]
        },
    ],
)
def test_an_unreadable_verdict_file_is_refused_rather_than_partly_believed(
    overrides: dict[str, Any],
) -> None:
    with pytest.raises(links.VerdictError):
        links.parse(_document(**overrides))


def test_two_verdicts_for_one_url_are_refused() -> None:
    row = {
        "url": "https://www.ctc.ca.gov/",
        "verdict": links.ALIVE,
        "checked": "2026-09-06",
    }
    with pytest.raises(links.VerdictError):
        links.parse(_document(verdicts=[row, dict(row, verdict=links.UNREACHABLE)]))


def test_the_verdict_vocabulary_is_the_five_the_issue_names() -> None:
    """Pinned as literals: a sixth verdict is a change to what this publishes."""
    assert links.VERDICTS == (
        "alive",
        "redirected on-site",
        "redirected off-site",
        "unreachable",
        "indeterminate",
    )


def test_the_reader_opens_no_socket_and_the_checker_does() -> None:
    """Pointed at both halves, using the repository's own scanner rather than a substring.

    `chalkline.links` is inside the package, so it is already covered by
    `test_no_module_in_the_package_opens_a_socket`. This says the split is real in
    both directions: the checker would fail that scan if it were in the package,
    which is why it is not.
    """
    from tests.test_provenance import connection_imports, networking_imports

    reader = (REPO_ROOT / "src" / "chalkline" / "links.py").read_text(encoding="utf-8")
    checker = (REPO_ROOT / "scripts" / "check_links.py").read_text(encoding="utf-8")
    assert networking_imports(reader) == []
    assert connection_imports(checker) != []
