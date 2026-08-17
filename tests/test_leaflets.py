"""Leaflets attach on an exact title match, and on nothing else."""

from __future__ import annotations

from pathlib import Path

import pytest

from chalkline.sources import leaflets


def page(*links: tuple[str, str]) -> str:
    body = "".join(f'<a href="/credentials/leaflets/{code}/">{label}</a>' for code, label in links)
    return f"<html><body>{body}</body></html>"


def test_parses_code_title_and_url() -> None:
    (leaflet,) = leaflets.parse(page(("cl-380", "School Nurse Services Credential")))
    assert leaflet.code == "cl-380"
    assert leaflet.title == "School Nurse Services Credential"
    assert leaflet.url == "https://www.ctc.ca.gov/credentials/leaflets/cl-380/"


def test_an_empty_repeat_link_does_not_erase_a_title() -> None:
    parsed = leaflets.parse(page(("cl-380", ""), ("cl-380", "School Nurse Services Credential")))
    assert [x.title for x in parsed] == ["School Nurse Services Credential"]


def test_the_index_link_to_itself_is_skipped() -> None:
    """The index links back to itself, with and without a trailing segment."""
    assert leaflets.parse('<a href="/credentials/leaflets/">Leaflets</a>') == ()
    assert leaflets.parse('<a href="/credentials/leaflets//">Leaflets</a>') == ()
    assert leaflets.parse('<a href="/credentials/leaflets/leaflets/">Leaflets</a>') == ()


def test_results_are_sorted_by_code() -> None:
    parsed = leaflets.parse(page(("cl-562", "B"), ("cl-380", "A")))
    assert [x.code for x in parsed] == ["cl-380", "cl-562"]


def test_normalization_folds_case_and_punctuation_only() -> None:
    assert leaflets.normalize_title("Credential (CTE)") == leaflets.normalize_title(
        "credential  cte"
    )
    assert leaflets.normalize_title("A - B") == leaflets.normalize_title("A \u2013 B")
    assert leaflets.normalize_title("Art Credential") != leaflets.normalize_title("Art")


def test_an_ambiguous_title_matches_nothing() -> None:
    parsed = leaflets.parse(page(("cl-1", "Same Title"), ("cl-2", "Same Title")))
    assert leaflets.index_by_title(parsed) == {}


def test_an_unambiguous_title_is_indexed() -> None:
    parsed = leaflets.parse(page(("cl-1", "Only One")))
    assert set(leaflets.index_by_title(parsed)) == {"only one"}


def test_the_vendored_index_parses(real_leaflets: tuple[leaflets.Leaflet, ...]) -> None:
    assert len(real_leaflets) > 0
    assert all(x.title and x.code and x.url.startswith("https://") for x in real_leaflets)


def test_load_reads_the_vendored_path_by_default() -> None:
    assert leaflets.load() == leaflets.parse(leaflets.SOURCE_PATH.read_text(encoding="utf-8"))


def test_a_link_with_no_code_segment_is_skipped() -> None:
    assert leaflets.parse('<a href="/credentials/leaflets/#top">Anchor</a>') == ()


def test_an_index_artifact_linking_no_leaflets_is_refused(tmp_path: Path) -> None:
    """An unreadable index must not be reported as an index of nothing.

    `_LINK_RE` matches a path-relative href, so the Commission switching to absolute URLs is
    an ordinary CMS change. It used to yield zero leaflets, zero attachments, a graph with
    the descriptions and conditions silently gone, and a coverage statement publishing the
    smaller counts as fact, with every gate still green.
    """
    index = tmp_path / "credential-leaflets.html"
    index.write_text(
        '<a href="https://www.ctc.ca.gov/credentials/leaflets/cl-380/">School Nurse</a>',
        encoding="utf-8",
    )
    assert leaflets.parse(index.read_text(encoding="utf-8")) == ()
    with pytest.raises(ValueError, match="links no leaflet pages"):
        leaflets.load(index)
