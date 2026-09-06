"""The subject pages say what the graph says, and nothing more.

These pages publish the inverse of the main page: for each subject code, the credentials
that authorize it. The whole claim is that nothing on them is composed by this project, so
what has to be checked is not that the pages look right but that each one lists exactly
what the graph aligns to its code, says where each alignment came from, and reproduces the
Commission's own notes rather than a paraphrase.

The last test in each group is a control. A page that lists every authorization would pass
a test that only asked whether the right ones were present, and a page rendered from a
stale copy of the catalog would pass every count. So an alignment is removed and the
affected page has to change while the others do not.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from chalkline import cli
from chalkline import subjects as subjects_module
from chalkline.model import Authorization, Catalog
from chalkline.subjects import (
    CODE_SHAPE,
    INDEX_FILENAME,
    NOT_SUBJECT_CODED_FILENAME,
    Subject,
    UnpublishableCode,
    census,
    group,
    not_subject_coded,
    pages,
    render_index,
    render_not_subject_coded,
    render_subject,
)

SITE: Final = Path(__file__).resolve().parents[1] / "site"


@pytest.fixture(scope="module")
def grouped(real_catalog: Catalog) -> tuple[Subject, ...]:
    return group(real_catalog)


@pytest.fixture(scope="module")
def rendered(real_catalog: Catalog) -> dict[str, str]:
    return pages(real_catalog)


class TestTheGroupingIsTheGraph:
    def test_there_are_subjects_to_check(self, grouped: tuple[Subject, ...]) -> None:
        """The denominator. Every test below iterates this."""
        assert len(grouped) > 100

    def test_every_alignment_reaches_exactly_one_page(
        self, grouped: tuple[Subject, ...], real_catalog: Catalog
    ) -> None:
        """Nothing is dropped and nothing is counted twice."""
        emitted = sum(len(a.subjects) for a in real_catalog.authorizations)
        assert sum(len(subject.reaches) for subject in grouped) == emitted

    def test_every_page_lists_exactly_what_the_graph_aligns_to_its_code(
        self, grouped: tuple[Subject, ...], real_catalog: Catalog
    ) -> None:
        wanted: dict[str, Counter[str]] = {}
        for authorization in real_catalog.authorizations:
            for scope in authorization.subjects:
                wanted.setdefault(scope.code, Counter())[authorization.key] += 1
        for subject in grouped:
            got: Counter[str] = Counter(reach.authorization.key for reach in subject.reaches)
            assert got == wanted[subject.code], subject.code

    def test_a_code_carrying_two_published_names_keeps_both(
        self, grouped: tuple[Subject, ...]
    ) -> None:
        """Merging them would be this project choosing between the Commission's strings.

        Asserted with a case that exists in the vendored source rather than a constructed
        one, and the count is asserted too so that a change which silently merged them
        would fail here rather than reduce this to a test of nothing.
        """
        multiple = [subject for subject in grouped if len(subject.names) > 1]
        assert multiple, "no code in the source publishes two names, so this checks nothing"
        theater = next(subject for subject in grouped if subject.code == "THTR")
        assert sorted(theater.names) == ["Introductory Theater", "Theater"]

    def test_the_codes_are_ordered_and_not_repeated(self, grouped: tuple[Subject, ...]) -> None:
        codes = [subject.code for subject in grouped]
        assert codes == sorted(set(codes))

    def test_not_subject_coded_is_read_off_the_published_flag(self, real_catalog: Catalog) -> None:
        """The Commission's NONE, not an empty subject list.

        On the real catalog the two coincide: ``build_catalog`` excludes an authorization
        whose subjects are neither published nor reachable by cross-reference, so every
        modeled one either carries subjects or carries the flag. That is why this assertion
        is worth almost nothing on its own, and why the constructed case below is the test.
        """
        uncoded = not_subject_coded(real_catalog)
        assert uncoded
        assert all(a.declares_no_subject_codes for a in uncoded)
        assert all(not a.subjects for a in uncoded)

    def test_an_authorization_with_no_subjects_and_no_flag_is_not_on_that_page(
        self, real_catalog: Catalog
    ) -> None:
        """The one case that tells the flag apart from the emptiness.

        Measured: replacing ``a.declares_no_subject_codes`` with ``not a.subjects`` in the
        source changes nothing at all on the vendored catalog, so a control applied to the
        real data lands in the file and still reads as a pass while the implementation now
        says something else entirely. An authorization whose scope the Commission did not
        publish is not an authorization the Commission published ``NONE`` against, and the
        page states the second. The case is constructed because the source cannot produce
        it, and the distinction is still the whole of what the page claims.
        """
        subjectless = replace(
            real_catalog.authorizations[0], subjects=(), declares_no_subject_codes=False
        )
        catalog = replace(
            real_catalog, authorizations=(subjectless, *real_catalog.authorizations[1:])
        )
        assert subjectless not in not_subject_coded(catalog)
        assert subjectless.title not in pages(catalog)[NOT_SUBJECT_CODED_FILENAME]


class TestThePagesAreWhatTheyClaim:
    def test_one_page_per_code_plus_the_index_and_the_uncoded_page(
        self, rendered: dict[str, str], grouped: tuple[Subject, ...]
    ) -> None:
        assert set(rendered) == (
            {subject.filename for subject in grouped} | {INDEX_FILENAME, NOT_SUBJECT_CODED_FILENAME}
        )

    def test_each_page_names_every_authorization_the_graph_gives_its_code(
        self, rendered: dict[str, str], grouped: tuple[Subject, ...]
    ) -> None:
        for subject in grouped:
            page = rendered[subject.filename]
            titles = re.findall(r"<h3>(.*?)</h3>", page)
            assert len(titles) == len(subject.reaches), subject.code

    def test_a_page_says_when_an_alignment_came_through_a_cross_reference(
        self, rendered: dict[str, str], grouped: tuple[Subject, ...]
    ) -> None:
        """And names the credential the rows belong to, which the issue asks for."""
        resolved = [
            (subject, reach)
            for subject in grouped
            for reach in subject.reaches
            if reach.by_cross_reference
        ]
        assert resolved, "no alignment in the source arrived by cross-reference"
        subject, reach = resolved[0]
        page = rendered[subject.filename]
        assert "Reached by following a cross-reference" in page
        resolution = reach.authorization.resolved_from
        assert resolution is not None
        assert resolution.credential in page

    def test_a_page_reproduces_the_row_notes_the_commission_published(
        self, rendered: dict[str, str], grouped: tuple[Subject, ...]
    ) -> None:
        import html as html_module

        noted = [
            (subject, reach)
            for subject in grouped
            for reach in subject.reaches
            if reach.scope.notes
        ]
        assert noted, "no subject row in the source carries a note"
        subject, reach = noted[0]
        page = html_module.unescape(rendered[subject.filename])
        for note in reach.scope.notes:
            assert note in page

    def test_a_row_with_no_note_says_so_rather_than_rendering_nothing(
        self, rendered: dict[str, str], grouped: tuple[Subject, ...]
    ) -> None:
        """An empty notes list and a note the Commission did not publish look the same."""
        blank = [
            subject
            for subject in grouped
            if any(not reach.scope.notes for reach in subject.reaches)
        ]
        assert blank, "every row in the source carries a note, so this checks nothing"
        assert "publishes no note against this subject" in rendered[blank[0].filename]

    def test_the_index_links_every_code_and_the_uncoded_page(
        self, rendered: dict[str, str], grouped: tuple[Subject, ...]
    ) -> None:
        index = rendered[INDEX_FILENAME]
        for subject in grouped:
            assert f'href="{subject.code}.html"' in index, subject.code
        assert 'href="not-subject-coded.html"' in index

    def test_the_uncoded_page_lists_the_published_none_authorizations(
        self, rendered: dict[str, str], real_catalog: Catalog
    ) -> None:
        page = rendered[NOT_SUBJECT_CODED_FILENAME]
        uncoded = not_subject_coded(real_catalog)
        assert f"<h2>{len(uncoded)} authorizations</h2>" in page
        assert page.count("<tr>") == len(uncoded) + 1  # the header row

    def test_the_uncoded_page_keeps_the_two_kinds_of_silence_apart(
        self, rendered: dict[str, str]
    ) -> None:
        """A published NONE is a statement; an unreadable scope is not.

        The page has to say which it is showing, because a reader who takes the second for
        the first has been told the Commission said something it did not.
        """
        page = rendered[NOT_SUBJECT_CODED_FILENAME]
        assert "not the same as an authorization whose scope the Commission did not" in page

    def test_every_page_makes_the_same_disclaimer_the_main_page_makes(
        self, rendered: dict[str, str]
    ) -> None:
        from chalkline.ctdl.export import DISCLAIMER_LEAD

        for name, page in rendered.items():
            assert DISCLAIMER_LEAD in page, name

    def test_no_page_composes_an_assignment_judgement(self, rendered: dict[str, str]) -> None:
        """MODELING.md refuses grade-level interpretation and assignment advice.

        These pages are the surface where "which credentials authorize this?" is one
        sentence away from "who may be assigned to teach this?", which is the sentence
        this project does not write.
        """
        banned = re.compile(
            r"\b(may be assigned|qualified to teach|eligible to teach|is authorized to "
            r"teach any)\b",
            re.IGNORECASE,
        )
        for name, page in rendered.items():
            hit = banned.search(page)
            assert hit is None, f"{name} says {hit.group(0)!r}"


class TestEveryPageIsSelfContained:
    """One file, one inline stylesheet, nothing fetched. Same rule as the main page."""

    def test_no_page_fetches_a_subresource(self, rendered: dict[str, str]) -> None:
        from tests.test_performance import references

        for name, page in rendered.items():
            found, elements = references(page)
            assert elements > 10, name
            fetches = [f"<{r.tag}> fetches {r.target!r}" for r in found if r.subresource]
            assert fetches == [], f"{name}: {fetches}"

    def test_every_relative_link_resolves_from_the_page_that_makes_it(
        self, rendered: dict[str, str]
    ) -> None:
        """Resolved against the page's own directory, which is where a browser resolves it.

        The main page's version of this test joins targets onto ``site/`` because every
        artifact sits there. These pages sit one level down and link upward, so the same
        arithmetic would report ``../index.html`` as missing while a browser found it.
        """
        from tests.test_performance import references

        for name, page in rendered.items():
            directory = (SITE / name).parent
            found, _ = references(page)
            relative = sorted(
                {
                    r.target
                    for r in found
                    if r.target and not r.target.startswith(("https://", "http://", "#", "mailto:"))
                }
            )
            assert relative, f"{name} makes no relative link"
            missing = [t for t in relative if not (directory / t).exists()]
            assert missing == [], f"{name} links {missing}, which is not committed"

    def test_a_page_that_fetched_something_would_be_caught(self, rendered: dict[str, str]) -> None:
        """The control. Without it the scan passing proves only that it ran."""
        from tests.test_performance import references

        page = rendered[INDEX_FILENAME]
        assert "<style>" in page
        broken = page.replace("<style>", '<script src="https://example.com/a.js"></script>', 1)
        found, _ = references(broken)
        assert [r for r in found if r.subresource]

    def test_a_link_that_stopped_resolving_would_be_caught(self, rendered: dict[str, str]) -> None:
        from tests.test_performance import references

        page = rendered[NOT_SUBJECT_CODED_FILENAME]
        broken = page.replace('href="../index.html"', 'href="../index-v2.html"', 1)
        assert broken != page
        found, _ = references(broken)
        directory = (SITE / NOT_SUBJECT_CODED_FILENAME).parent
        relative = {
            r.target
            for r in found
            if r.target and not r.target.startswith(("https://", "http://", "#", "mailto:"))
        }
        assert [t for t in relative if not (directory / t).exists()] == ["../index-v2.html"]


class TestTheCensusIsTheData:
    def test_every_figure_is_counted_from_the_catalog(
        self, real_catalog: Catalog, grouped: tuple[Subject, ...]
    ) -> None:
        counted = census(real_catalog)
        assert counted["distinct_codes"] == len(grouped)
        assert counted["alignments"] == sum(len(s.reaches) for s in grouped)
        assert counted["pages_published"] == len(grouped) + 2
        assert counted["authorizations_published_as_not_subject_coded"] == len(
            not_subject_coded(real_catalog)
        )

    def test_the_census_agrees_with_the_coverage_statement_beside_it(self) -> None:
        """The committed statement, not one computed here.

        ``chalkline check`` already holds ``site/`` to a fresh build. This asserts the
        published figures independently, so a census that had drifted from the pages could
        not pass while a different one is what is served.
        """
        import json

        statement = json.loads((SITE / "coverage.json").read_text(encoding="utf-8"))
        published = sorted(p.name for p in (SITE / "subjects").iterdir())
        assert statement["subjects"]["pages_published"] == len(published)
        assert statement["subjects"]["distinct_codes"] == len(published) - 2
        assert (
            statement["subjects"]["alignments"]
            == statement["entities"]["ceterms:CredentialAlignmentObject"]
        )
        assert (
            statement["subjects"]["alignments_reached_by_cross_reference"]
            == statement["authorizations"]["subject_alignments_from_a_cross_reference"]
        )


class TestACodeThatCannotBeAFilenameIsRefused:
    """Sanitising would publish a page under a name the Commission never used."""

    @pytest.mark.parametrize("code", ["A/B", "..", "a b", "", "x" * 17, "Mixed"])
    def test_a_code_outside_the_shape_stops_the_build(
        self, real_catalog: Catalog, code: str
    ) -> None:
        assert not CODE_SHAPE.fullmatch(code)
        first = real_catalog.authorizations[0]
        assert first.subjects, "the first authorization carries no subject to rewrite"
        bad_scope = replace(first.subjects[0], code=code)
        bad = replace(first, subjects=(bad_scope,))
        catalog = replace(real_catalog, authorizations=(bad, *real_catalog.authorizations[1:]))
        with pytest.raises(UnpublishableCode, match=re.escape(code) if code else "cannot"):
            pages(catalog)

    def test_every_code_the_commission_publishes_today_passes(
        self, grouped: tuple[Subject, ...]
    ) -> None:
        """The denominator for the refusal above."""
        assert all(CODE_SHAPE.fullmatch(subject.code) for subject in grouped)


class TestTheControl:
    """Remove one alignment and exactly the affected page changes.

    Every test above compares the pages against the catalog they were rendered from, so
    all of them would pass over a renderer that had frozen. This is the one that would not.
    """

    @staticmethod
    def _drop(catalog: Catalog, *, shared: bool) -> tuple[Catalog, str, Authorization]:
        """Remove one alignment, choosing a code other pages do or do not also carry.

        ``shared`` picks a code more than one authorization reaches, so its page survives
        the removal and has to change. Without it the page would simply vanish, which a
        renderer that had frozen would also produce and which is therefore a weaker fact.
        """
        reach_count = Counter(scope.code for a in catalog.authorizations for scope in a.subjects)
        for authorization in catalog.authorizations:
            if authorization.resolved_from is not None or len(authorization.subjects) < 2:
                continue
            for scope in authorization.subjects:
                if (reach_count[scope.code] > 1) is not shared:
                    continue
                kept = tuple(s for s in authorization.subjects if s.code != scope.code)
                thinner = replace(authorization, subjects=kept)
                rest = tuple(a for a in catalog.authorizations if a.key != authorization.key)
                return (
                    replace(catalog, authorizations=(thinner, *rest)),
                    scope.code,
                    authorization,
                )
        raise AssertionError(f"the source carries no droppable code with shared={shared}")

    def test_dropping_an_alignment_changes_that_page_and_no_other(
        self, real_catalog: Catalog, rendered: dict[str, str]
    ) -> None:
        catalog, dropped, target = self._drop(real_catalog, shared=True)
        after = pages(catalog)
        name = f"{subjects_module.DIRECTORY}/{dropped}.html"
        assert after[name] != rendered[name], (
            f"dropping {target.title!r} from {dropped} left its page unchanged"
        )
        # The heading list, not a substring of the whole page. An authorization whose scope
        # was resolved by cross-reference quotes the credential it borrowed rows from by
        # name, so the dropped title can legitimately still appear in someone else's
        # provenance sentence while no longer being listed itself.
        before_headings = re.findall(r"<h3>(.*?)</h3>", rendered[name])
        after_headings = re.findall(r"<h3>(.*?)</h3>", after[name])
        assert Counter(before_headings) - Counter(after_headings) == Counter([target.title])
        assert Counter(after_headings) - Counter(before_headings) == Counter()

        moved = {
            page
            for page in set(after) & set(rendered)
            if after[page] != rendered[page] and page != name
        }
        assert moved == {INDEX_FILENAME}, (
            f"dropping one alignment moved pages other than its own and the index: {sorted(moved)}"
        )

    def test_dropping_the_last_alignment_for_a_code_takes_its_page_away(
        self, real_catalog: Catalog, rendered: dict[str, str]
    ) -> None:
        """A code nothing reaches has no page, rather than an empty one.

        An empty page would publish "no credential authorizes this subject", which is a
        claim about the Commission's table that an absent code does not support.
        """
        catalog, dropped, _target = self._drop(real_catalog, shared=False)
        name = f"{subjects_module.DIRECTORY}/{dropped}.html"
        assert name in rendered
        assert name not in pages(catalog)

    def test_dropping_an_alignment_moves_the_census(self, real_catalog: Catalog) -> None:
        catalog, _dropped, _target = self._drop(real_catalog, shared=True)
        assert census(catalog)["alignments"] == census(real_catalog)["alignments"] - 1


class TestTheBuildPublishesThem:
    def test_the_committed_directory_is_what_the_code_produces(
        self, rendered: dict[str, str]
    ) -> None:
        for name, text in rendered.items():
            path = SITE / name
            assert path.is_file(), f"{name} is not committed"
            assert path.read_text(encoding="utf-8") == text, f"{name} differs from a fresh build"

    def test_the_committed_directory_holds_nothing_else(self, rendered: dict[str, str]) -> None:
        """`chalkline check` enumerates site/ and would catch an orphan too.

        Asserted here as well because this is the directory that just gained 325 files, and
        the failure it guards against is one stale file among them, which is the shape
        nobody notices.
        """
        committed = {
            str(p.relative_to(SITE)) for p in (SITE / "subjects").rglob("*") if p.is_file()
        }
        assert committed == set(rendered)

    def test_check_fails_when_a_subject_page_is_stale(self, tmp_path: Path) -> None:
        cli.build(tmp_path)
        (tmp_path / INDEX_FILENAME).write_text("<!doctype html>", encoding="utf-8")
        assert cli.check(tmp_path) == 1

    def test_check_fails_on_an_orphan_under_the_subjects_directory(self, tmp_path: Path) -> None:
        cli.build(tmp_path)
        (tmp_path / subjects_module.DIRECTORY / "ZZZZ.html").write_text("<p>", encoding="utf-8")
        assert cli.check(tmp_path) == 1


class TestTheRenderersRefuseNothingQuietly:
    def test_an_index_over_no_subjects_still_says_zero_rather_than_nothing(self) -> None:
        """Not a state the source produces, and the renderer still must not go blank."""
        page = render_index((), 0)
        assert "<h2>0 subject codes</h2>" in page

    def test_an_uncoded_page_over_none_still_renders_its_explanation(self) -> None:
        page = render_not_subject_coded(())
        assert "<h2>0 authorizations</h2>" in page
        assert "publishes <code>NONE</code>" in page

    def test_a_subject_reached_once_uses_the_singular(self, grouped: tuple[Subject, ...]) -> None:
        single = [subject for subject in grouped if len(subject.reaches) == 1]
        assert single, "no code in the source is reached exactly once"
        page = render_subject(single[0])
        assert "<h2>1 authorization authorizes this subject</h2>" in page
        assert "authorizations" not in page.split("<h2>")[1].split("</h2>")[0]
