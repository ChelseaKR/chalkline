"""The published page carries its own weight, and fetches nothing to render.

Two claims this repository has been making in prose and checking nowhere.

``chalkline.site``'s module docstring: "No external stylesheet, script, font, or image: the
page is one file and works offline, which is the same discipline the rest of this project
applies to its data." The README's Performance row: "the published output is three static
files served from GitHub Pages, with no client-side data fetch and no runtime. **Not yet
enforced:** no performance budget is measured and none is gated."

Self-containment is the load-bearing half. It is what makes the page work from a file://
URL, what keeps a reader's visit off any third party's logs, and what makes "no analytics on
the published page, by design" in the Observability row a checkable statement rather than an
intention. One ``<script src>`` or one webfont ``<link>`` would end all three at once, and
until now nothing would have noticed.

The weight budget is the other half, and it is deliberately expressed as a formula rather
than a number of bytes. The page grows when the Commission publishes more authorizations,
which is the project working, and it grows when the markup per authorization grows, which is
the thing worth catching. A flat cap conflates them and eventually gets raised to whatever
the page happens to weigh, which is a budget in name only.

What is not budgeted, and why: ``credentials.jsonld`` and ``coverage.json`` are downloads a
reader chooses to fetch, not page-load cost. They are as large as the data is, and a cap on
them would be a cap on how much of the Commission's table this project may model. The check
that matters for those two is that the page does not fetch them to render, which is the
first test below, and that its links to them resolve, which is the second.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Final

import pytest

from chalkline import ctid as ctid_module
from chalkline.attachment import Attachment
from chalkline.model import Catalog
from chalkline.site import STYLE, render

SITE = Path(__file__).resolve().parents[1] / "site"

SUBRESOURCE_TAGS: Final = {
    "script": "src",
    "link": "href",
    "img": "src",
    "iframe": "src",
    "object": "data",
    "embed": "src",
    "video": "src",
    "audio": "src",
    "source": "src",
    "track": "src",
    "input": "src",
}
"""Every element that makes the browser fetch something while rendering the page, and the
attribute that names what. ``script`` and ``link`` are listed without qualification: an
inline ``<script>`` fetches nothing but still means the page runs code, and the page's claim
is that it does not."""

FIXED_OVERHEAD_BUDGET: Final = 12_000
"""Bytes the page may spend on everything that is not a credential: the stylesheet, the
head, the disclaimer, the counts, the prose, the exclusions table, the footer. It is 7,006
today, so this is 1.7x headroom. The stylesheet is 2,718 of it."""

PER_AUTHORIZATION_BUDGET: Final = 2_200
"""Bytes the page may spend per modeled authorization. The mean is 1,711 today and the
largest single block is 12,932 (an authorization with a long subject list), so the budget is
on the total rather than on any one block: 1.29x headroom on the average, which is enough
for another property or two per credential and not enough to absorb a doubling."""


@dataclass(frozen=True, slots=True)
class Reference:
    """One thing the page points at, and whether the browser fetches it to render."""

    tag: str
    target: str
    subresource: bool


class _References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[Reference] = []
        self.elements = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements += 1
        values = {name: value or "" for name, value in attrs}
        if tag in SUBRESOURCE_TAGS:
            self.found.append(Reference(tag, values.get(SUBRESOURCE_TAGS[tag], ""), True))
        elif "href" in values:
            self.found.append(Reference(tag, values["href"], False))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def stylesheet_fetches(style: str) -> list[str]:
    """Every way the inline stylesheet would reach for another file.

    The page's own ``<style>`` is not an element the reference scan can see into, so it is
    read as text. ``@import`` pulls a second stylesheet; ``url()`` is how a font, an image or
    a cursor gets fetched. Neither has ever appeared here, which is exactly why nothing was
    watching for them.
    """
    found = ["@import"] if "@import" in style else []
    return found + [
        f"url({match.group(1).strip()})" for match in re.finditer(r"url\(([^)]*)\)", style)
    ]


def references(page: str) -> tuple[list[Reference], int]:
    parser = _References()
    parser.feed(page)
    return parser.found, parser.elements


@pytest.fixture(scope="module")
def page(real_catalog: Catalog, real_attachments: dict[str, Attachment]) -> str:
    """The page as `chalkline build` writes it, from the vendored sources."""
    return render(real_catalog, ctid_module.load_ledger(), real_attachments)


def test_the_page_fetches_nothing_and_runs_nothing_to_render(page: str) -> None:
    """No script, stylesheet, font, image or frame. The page is one file.

    The element count is asserted too. A parser that read nothing would report no
    subresources just as convincingly as a page that has none.
    """
    found, elements = references(page)
    assert elements > 1_000, f"the reference scan walked {elements} elements, so it saw a page"
    subresources = [f"<{r.tag}> fetches {r.target!r}" for r in found if r.subresource]
    assert subresources == [], f"the page is not self-contained: {subresources}"
    assert stylesheet_fetches(STYLE) == [], "the inline stylesheet fetches something"


def test_every_link_the_page_makes_resolves(page: str) -> None:
    """A relative link names a file committed beside the page; nothing else is relative."""
    found, _ = references(page)
    relative = sorted(
        {
            reference.target
            for reference in found
            if reference.target
            and not reference.target.startswith(("https://", "http://", "#", "mailto:"))
        }
    )
    assert relative, "the page makes no relative link, so this test is checking nothing"
    missing = [target for target in relative if not (SITE / target).exists()]
    assert missing == [], f"the page links {missing}, which is not committed under site/"


def test_the_page_stays_within_its_weight_budget(page: str, real_catalog: Catalog) -> None:
    """Weight per authorization, not weight. See the module docstring for why."""
    blocks = re.findall(r'<article class="cred"[^>]*>.*?</article>', page, re.DOTALL)
    modeled = len(real_catalog.authorizations)
    assert len(blocks) == modeled, (
        f"the page renders {len(blocks)} credential blocks for {modeled} authorizations, so "
        "the split between fixed overhead and per-authorization weight is not what this "
        "budget assumes"
    )
    total = len(page.encode("utf-8"))
    spent_on_blocks = sum(len(block.encode("utf-8")) for block in blocks)
    overhead = total - spent_on_blocks
    per_authorization = spent_on_blocks / modeled

    assert overhead <= FIXED_OVERHEAD_BUDGET, (
        f"the page spends {overhead:,} bytes on everything that is not a credential, over "
        f"the {FIXED_OVERHEAD_BUDGET:,} budget"
    )
    assert per_authorization <= PER_AUTHORIZATION_BUDGET, (
        f"the page spends {per_authorization:,.0f} bytes per authorization, over the "
        f"{PER_AUTHORIZATION_BUDGET:,} budget. The page is {total:,} bytes for {modeled} "
        "authorizations. Raising the budget is a decision to publish a heavier page; make it "
        "on purpose, in the diff."
    )


def test_the_committed_page_is_the_page_this_budget_measured(real_catalog: Catalog) -> None:
    """The budget is about the file that is served, so it is checked against that file too.

    ``chalkline check`` already holds the committed page to a fresh build byte-for-byte. This
    asserts the same bytes independently, so a budget test that only ever saw a page rendered
    in memory cannot pass while a larger one is what GitHub Pages serves.
    """
    committed = (SITE / "index.html").read_bytes()
    budget = FIXED_OVERHEAD_BUDGET + PER_AUTHORIZATION_BUDGET * len(real_catalog.authorizations)
    assert len(committed) <= budget, f"site/index.html is {len(committed):,} bytes, over {budget:,}"


BREAKAGES: Final = (
    ("<style>", '<script src="https://example.com/a.js"></script><style>'),
    ("<style>", '<link rel="stylesheet" href="https://fonts.example/x.css"><style>'),
    ("<main>", '<main><img src="seal.png" alt="">'),
    ("<main>", '<main><iframe src="https://example.com/"></iframe>'),
)
"""Four ways to make the page fetch something, applied to the real page."""


@pytest.mark.parametrize(("original", "broken"), BREAKAGES, ids=lambda v: str(v)[:34])
def test_a_page_that_fetches_something_is_caught(page: str, original: str, broken: str) -> None:
    assert original in page
    found, _ = references(page.replace(original, broken, 1))
    assert [r for r in found if r.subresource], f"{broken!r} was not seen as a subresource"


@pytest.mark.parametrize(
    ("declaration", "expected"),
    [
        ('@import "https://fonts.example/x.css";', "@import"),
        ("body { background: url(paper.png); }", "url(paper.png)"),
        ("@font-face { src: url(inter.woff2); }", "url(inter.woff2)"),
    ],
    ids=lambda value: str(value)[:30],
)
def test_a_stylesheet_that_fetches_something_is_caught(declaration: str, expected: str) -> None:
    """The stylesheet is inline, so it is read as text rather than walked as elements."""
    assert stylesheet_fetches(STYLE + declaration) == [expected]


def test_a_broken_relative_link_is_caught(page: str) -> None:
    doctored = page.replace('href="coverage.json"', 'href="coverage-v2.json"', 1)
    assert doctored != page
    found, _ = references(doctored)
    relative = {
        r.target
        for r in found
        if r.target and not r.target.startswith(("https://", "http://", "#", "mailto:"))
    }
    assert [t for t in relative if not (SITE / t).exists()] == ["coverage-v2.json"]


def test_a_heavier_page_is_caught(page: str, real_catalog: Catalog) -> None:
    """The budget rejects markup growth, and tolerates the Commission publishing more.

    Both halves are the point. A budget that failed when the source grew would be raised
    every time the project succeeded, and would then be a record of the last page anyone
    measured rather than a limit.
    """
    modeled = len(real_catalog.authorizations)
    blocks = re.findall(r'<article class="cred"[^>]*>.*?</article>', page, re.DOTALL)
    spent = sum(len(block.encode("utf-8")) for block in blocks)

    doubled = spent * 2 / modeled
    assert doubled > PER_AUTHORIZATION_BUDGET, "doubling the markup per credential would pass"

    twice_the_credentials = spent * 2 / (modeled * 2)
    assert twice_the_credentials <= PER_AUTHORIZATION_BUDGET, (
        "twice as many authorizations at today's weight each would fail, which would make "
        "this a cap on the Commission's table rather than on this project's markup"
    )
