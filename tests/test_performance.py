"""The published page carries its own weight, and fetches nothing to render.

Two claims this repository has been making in prose and checking nowhere.

``chalkline.site``'s module docstring: "No external stylesheet, script, font, or image: the
page is one file and works offline, which is the same discipline the rest of this project
applies to its data." The README's Performance row: "the published output is three static
files served from GitHub Pages, with no client-side data fetch and no runtime. **Not yet
enforced:** no performance budget is measured and none is gated."

Self-containment is the load-bearing half. It is what makes the page work from a file://
URL, and what makes every script on the page one that somebody decided to put there. One
``<script src>`` or one webfont ``<link>`` would end both at once, and until now nothing would
have noticed.

The page does run one script, and it is the second exception this gate makes, also by name:
the Google Analytics 4 loader from :mod:`chalkline.analytics` (owner decision 2026-09-17).
It is matched by its whole text, so an inline script that differs from it by one byte is
refused like any other. It fetches nothing to render: off the production host it returns
without doing anything, and on it, unless the browser sends Global Privacy Control or Do Not
Track or the visitor opted out, it appends Google's gtag.js as an async script after the page
is already there. That fetch is the one this gate knowingly allows, and
``tests/test_analytics.py`` holds exactly when it happens.

The page does carry one ``<link>``, the ``rel="canonical"`` added with the head metadata,
and it is the single exception this gate makes. It is an exception by name rather than by
element: :data:`METADATA_LINK_RELS` lists the relations that leave the browser nothing to
fetch, a ``<link>`` whose ``rel`` is not on that list is a subresource, and a separate test
asserts that the canonical link is the only ``<link>`` the page has. Exempting the element
instead would have let a stylesheet in behind the exemption.

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

from chalkline import analytics
from chalkline import ctid as ctid_module
from chalkline import subjects as subjects_module
from chalkline.attachment import Attachment
from chalkline.model import Catalog
from chalkline.site import SITE_URL, STYLE, render

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
attribute that names what. Two elements are qualified and the rest are refused outright:
``link`` by :data:`METADATA_LINK_RELS`, and ``script`` in exactly two shapes, an inline data
block whose ``type`` is on :data:`DATA_BLOCK_SCRIPT_TYPES` and the GA4 loader, matched by its
whole text against :data:`GA4_LOADER`."""

GA4_LOADER: Final = (
    analytics.head_snippet(analytics.GA4_MEASUREMENT_ID)
    .removeprefix("<script>")
    .removesuffix("</script>\n")
)
"""The body of the one inline script the page may run, exactly as the build writes it."""

DATA_BLOCK_SCRIPT_TYPES: Final = frozenset({"application/ld+json"})
"""The only ``type`` values that make a ``<script>`` on this page inert data.

Deny by default, with one name on the list, exactly as :data:`METADATA_LINK_RELS` works.

HTML defines a ``script`` element whose ``type`` is not a JavaScript MIME type as a **data
block**, which the parser hands to the document as inert text and never evaluates.
``application/ld+json`` is that case, and it is how a page carries structured data for a
harvester that will not execute anything. It is how the dataset descriptor is embedded.

So the exemption is by ``type``, and it is narrow in three ways that matter. A ``<script>``
with **no** ``type`` is JavaScript by default, and the only such script admitted is the GA4
loader, byte for byte. A ``<script>`` with a ``src`` is refused whatever its ``type``,
because a data block that arrives over the network is still a fetch and self-containment is
the other half of this gate. And a ``type`` this list does not name is refused rather than
guessed at: ``module``, ``text/javascript`` and an empty string all run code.

Adding a second name here is a decision that a second type is inert, and it belongs in a
diff with the reasoning next to it rather than in a wildcard."""

METADATA_LINK_RELS: Final = frozenset({"canonical"})
"""The only ``rel`` values a ``<link>`` on this page may carry.

Deny by default, with one name on the list. A ``<link>`` is how a stylesheet, a webfont, a
favicon, a preload and a prefetch all arrive, so the element is refused unless its ``rel``
is one this project has looked at and found to fetch nothing: ``rel="canonical"`` states
where the page lives and the browser retrieves nothing for it.

The list is one entry because the page carries one ``<link>``. Adding a second name here is
a decision that a second relation fetches nothing, and it belongs in a diff with the
reasoning next to it rather than in a wildcard. ``alternate`` in particular is not on the
list and must not be added without qualification: ``rel="alternate stylesheet"`` is a
stylesheet.
"""

FIXED_OVERHEAD_BUDGET: Final = 21_900
"""Bytes the page may spend on everything that is not a credential: the stylesheet, the
head, the disclaimer, the counts, the prose, the exclusions table, the footer. It was 8,690
against a budget of 12,000 (1.38x headroom). The stylesheet is 2,797 of it, the head metadata
added with the canonical link is 890, the share-card tags (`og:image` and its type,
dimensions and alt text, plus `twitter:image`) are 588, and the accessibility fixes (`scope`,
`role`, `tabindex`, the region label and its focus ring) are 206.

Google Analytics 4 (owner decision 2026-09-17) took the overhead from 8,920 to 12,525: the
inline loader is 3,097 bytes, the footer's privacy line and opt-out control 365, and the
opt-out button's style the rest. The budget was raised by 3,600 for that and not by a byte
more, so the headroom left for everything else is what it was before (3,075 bytes, against
3,080). A heavier page for analytics was decided on purpose, here, in the diff.

The subject pages (#87) added one sentence linking them from the page, taking it to 12,660:
2,940 bytes of headroom, 1.23x.

The dataset descriptor (#88) is embedded in the head as an inline
``<script type="application/ld+json">`` data block carrying ``site/dataset.jsonld`` verbatim:
6,282 bytes with its tags. The budget was raised by 6,300 for it and not by a byte more, the
same discipline the GA4 raise followed, so the page's overhead is 18,942 and the headroom
left for everything else is 2,958 bytes (1.16x), as it was before. It is fixed overhead by
definition: it describes the three downloads and does not grow when the Commission
publishes more rows. Embedding it is what makes it harvestable: dataset search engines read
structured data from a page's head, and a descriptor in a file nothing links from the page
is one those harvesters never see."""

PER_AUTHORIZATION_BUDGET: Final = 2_200
"""Bytes the page may spend per modeled authorization. The mean is 1,868 today and the
largest single block is 13,189 (an authorization with a long subject list), so the budget is
on the total rather than on any one block: 1.18x headroom on the average, which is enough
for another property or two per credential and not enough to absorb a doubling.

The mean was 1,711 until the leaflet stop rule was fixed (issue #36), which added
requirements and renewal terms to six authorizations that had been publishing none. The
budget was deliberately not raised for it: the whole point of expressing this as a formula
was that a page carrying more of what the Commission published is the project working, and
1.18x is still headroom rather than a number chosen after the fact to fit."""


@dataclass(frozen=True, slots=True)
class Reference:
    """One thing the page points at, and whether the browser fetches it to render."""

    tag: str
    target: str
    subresource: bool

    rel: str = ""
    """The ``rel`` of a ``<link>``, as the page writes it. Empty for every other element."""

    body: str = ""
    """The text of an inline ``<script>``. Empty for every other element."""

    data_block: bool = False
    """Whether an inline ``<script>`` is an inert data block by its ``type``."""


def _script_is_a_data_block(script_type: str | None) -> bool:
    """Whether an inline ``<script>`` of this ``type`` is inert data rather than code.

    Only ever asked of a ``<script>`` with no ``src``: one with a ``src`` is a fetch whatever
    its type, and the parser refuses it before this is reached. A ``type`` this project has
    not cleared, including none at all, is treated as code, which is what the HTML default
    already makes it.
    """
    return script_type is not None and script_type.strip().lower() in DATA_BLOCK_SCRIPT_TYPES


def _link_is_metadata(rel: str) -> bool:
    """Whether a ``<link>`` carrying this ``rel`` leaves the browser nothing to fetch.

    ``rel`` is a space-separated token list, so every token has to be one this project has
    cleared. A bare ``<link>`` with no ``rel`` at all is not metadata: it is an element whose
    relation nobody declared, and the answer to what it fetches is unknown rather than none.
    """
    tokens = rel.lower().split()
    return bool(tokens) and all(token in METADATA_LINK_RELS for token in tokens)


class _References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[Reference] = []
        self.elements = 0
        self._inline: list[str] | None = None
        self._inline_type: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements += 1
        values = {name: value or "" for name, value in attrs}
        if tag == "script" and "src" not in values:
            # Decided at the end tag, once the whole body has been read.
            self._inline = []
            self._inline_type = values.get("type")
        elif tag in SUBRESOURCE_TAGS:
            # A <script> reaching here has a src, which is a fetch whatever its type.
            rel = values.get("rel", "") if tag == "link" else ""
            fetches = not (tag == "link" and _link_is_metadata(rel))
            self.found.append(Reference(tag, values.get(SUBRESOURCE_TAGS[tag], ""), fetches, rel))
        elif "href" in values:
            self.found.append(Reference(tag, values["href"], False))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._inline is not None:
            self._inline.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._inline is not None:
            body = "".join(self._inline)
            inert = _script_is_a_data_block(self._inline_type)
            self._inline, self._inline_type = None, None
            runs_uncleared_code = not inert and body != GA4_LOADER
            self.found.append(
                Reference("script", "", runs_uncleared_code, body=body, data_block=inert)
            )


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
def page(built_artifacts: dict[str, str]) -> str:
    """The page as `chalkline build` writes it, from the vendored sources.

    Taken from the build rather than re-rendered, so the dataset descriptor the build embeds
    is inside the page this budget measures and this gate walks.
    """
    return built_artifacts["index.html"]


def test_the_page_fetches_nothing_to_render_and_runs_only_the_ga4_loader(page: str) -> None:
    """No stylesheet, font, image or frame, and no code but the GA4 loader.

    The one other ``<script>`` is the dataset descriptor, an inert data block.

    The element count is asserted too. A parser that read nothing would report no
    subresources just as convincingly as a page that has none.
    """
    found, elements = references(page)
    assert elements > 1_000, f"the reference scan walked {elements} elements, so it saw a page"
    subresources = [f"<{r.tag}> fetches {r.target!r}" for r in found if r.subresource]
    assert subresources == [], f"the page is not self-contained: {subresources}"
    assert stylesheet_fetches(STYLE) == [], "the inline stylesheet fetches something"


def test_the_only_link_element_is_the_one_that_fetches_nothing(page: str) -> None:
    """The ``<link>`` exemption is named, not assumed.

    :data:`METADATA_LINK_RELS` is the one place this gate lets an element through, so the
    element it lets through is asserted rather than left to the pass above. Without this, a
    page that had lost its ``<link rel="canonical">`` and a page that had gained a
    ``<link rel="stylesheet">`` the scanner failed to see would both read as self-contained.
    """
    found, _ = references(page)
    links = [reference for reference in found if reference.tag == "link"]
    assert [(link.rel, link.target) for link in links] == [("canonical", SITE_URL)], (
        f"the page's <link> elements are not the one metadata link this gate allows: {links}"
    )


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


def test_the_only_scripts_are_the_descriptor_and_the_ga4_loader(
    page: str, built_artifacts: dict[str, str]
) -> None:
    """Both script exemptions are named, not assumed, the same way the ``<link>`` one is.

    The data block is held to the descriptor the build writes, byte for byte, and the code
    to the GA4 loader, byte for byte.
    """
    found, _ = references(page)
    scripts = [reference for reference in found if reference.tag == "script"]
    assert [(s.target, s.body, s.data_block, s.subresource) for s in scripts] == [
        ("", built_artifacts["dataset.jsonld"], True, False),
        ("", GA4_LOADER, False, False),
    ]
    assert "googletagmanager.com/gtag/js?id=" + analytics.GA4_MEASUREMENT_ID in GA4_LOADER


def test_a_page_without_an_id_runs_nothing(
    real_catalog: Catalog, real_attachments: dict[str, Attachment]
) -> None:
    """With the ID unset the page is back to running no code at all."""
    bare = render(real_catalog, ctid_module.load_ledger(), real_attachments, ga4_id="")
    found, _ = references(bare)
    assert [r for r in found if r.tag == "script"] == []
    assert [r for r in found if r.subresource] == []


BREAKAGES: Final = (
    ("<style>", '<script src="https://example.com/a.js"></script><style>'),
    ("<style>", "<script>fetch('https://example.com/')</script><style>"),
    ("allow_google_signals: false", "allow_google_signals: true"),
    ("<style>", '<link rel="stylesheet" href="https://fonts.example/x.css"><style>'),
    ("<style>", '<link rel="preload" as="font" href="https://fonts.example/i.woff2"><style>'),
    ("<style>", '<link rel="icon" href="favicon.ico"><style>'),
    ("<style>", '<link rel="alternate stylesheet" href="https://fonts.example/x.css"><style>'),
    ("<style>", '<link href="https://fonts.example/x.css"><style>'),
    ("<main>", '<main><img src="seal.png" alt="">'),
    ("<main>", '<main><iframe src="https://example.com/"></iframe>'),
)
"""Ten ways to make the page fetch or run something, applied to the real page.

Two of them are scripts: a second inline script, and the GA4 loader itself with Google
signals switched on. The loader is matched by its whole text, so an edit to it is a script
this gate has not cleared rather than the one it has.

Five of them are ``<link>`` elements, because ``<link>`` is the one element
:data:`METADATA_LINK_RELS` lets through at all and an allowlist is worth exactly what the
cases it still refuses are worth. A stylesheet, a preloaded webfont and a favicon are the
three relations most likely to arrive by accident; ``alternate stylesheet`` is the reason
``rel`` is read as a token list rather than a string, since it would pass a check that only
asked whether ``alternate`` was cleared; and a ``<link>`` with no ``rel`` at all is refused
because an undeclared relation is unknown, not harmless.
"""


@pytest.mark.parametrize(("original", "broken"), BREAKAGES, ids=lambda v: str(v)[:34])
def test_a_page_that_fetches_something_is_caught(page: str, original: str, broken: str) -> None:
    assert original in page
    broken_page = page.replace(original, broken, 1)
    assert broken_page != page, "the breakage did not land, so this would check the real page"
    found, _ = references(broken_page)
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


README = Path(__file__).resolve().parents[1] / "README.md"

_DOCUMENTED_BUDGET = re.compile(
    r"weight budget is a formula, ([\d,]+) bytes of fixed overhead plus ([\d,]+) per "
    r"modeled authorization"
)
_DOCUMENTED_SPEND = re.compile(r"Today the page spends ([\d,]+) and ([\d,]+)")
"""The README's Performance row, in the two halves it makes a number of.

The first is the budget, which is a decision; the second is what the page actually weighs,
which is a measurement. Both were typed into prose by hand, and the second had already
drifted: the row said 7,006 when the head metadata added with the canonical link had taken
the page to 7,896. ``tests/test_documented_counts.py`` binds the README's prose figures to
the coverage statement, but only where a figure stands beside one of its counted nouns, and
"bytes" is not one of them, so these two were outside every check the repository had.
"""


def _figure(pattern: re.Pattern[str], text: str) -> tuple[int, ...]:
    """The figures one README sentence publishes, or a failure if the sentence has moved.

    A pattern that stops matching is a check that has stopped checking, so a miss fails here
    rather than quietly returning nothing for the assertions below to agree with.
    """
    found = pattern.search(text)
    assert found is not None, (
        f"README.md no longer contains the sentence {pattern.pattern!r}, so the figures in "
        "it are unbound. Reword the test with the row, or the row can drift again."
    )
    return tuple(int(group.replace(",", "")) for group in found.groups())


def test_the_documented_weight_is_the_weight_the_page_spends(
    page: str, real_catalog: Catalog
) -> None:
    """The Performance row's four numbers are the budgets and the measurement, not prose."""
    text = " ".join(README.read_text(encoding="utf-8").split())
    assert _figure(_DOCUMENTED_BUDGET, text) == (
        FIXED_OVERHEAD_BUDGET,
        PER_AUTHORIZATION_BUDGET,
    ), "README.md publishes a budget this module does not hold the page to"

    blocks = re.findall(r'<article class="cred"[^>]*>.*?</article>', page, re.DOTALL)
    spent_on_blocks = sum(len(block.encode("utf-8")) for block in blocks)
    overhead = len(page.encode("utf-8")) - spent_on_blocks
    per_authorization = round(spent_on_blocks / len(real_catalog.authorizations))

    assert _figure(_DOCUMENTED_SPEND, text) == (overhead, per_authorization), (
        "README.md says the page spends something other than what it spends. The measured "
        f"figures are {overhead:,} and {per_authorization:,}."
    )


# --- the <script> exemption is narrow, and these are the shapes it must still refuse ---


@pytest.mark.parametrize(
    ("markup", "why"),
    [
        ("<script>alert(1)</script>", "no type at all is JavaScript by HTML's own default"),
        ('<script type="">x</script>', "an empty type is JavaScript by the same default"),
        ('<script type="text/javascript">x</script>', "an explicit JavaScript type"),
        ('<script type="module">x</script>', "a module is code"),
        ('<script src="/a.js"></script>', "a src is a fetch whatever the type"),
        (
            '<script type="application/ld+json" src="/d.jsonld"></script>',
            "a data block served from elsewhere is still a subresource",
        ),
        ('<script type="APPLICATION/JAVASCRIPT">x</script>', "case does not launder a type"),
        (
            '<script type="application/ld+json; charset=utf-8">{}</script>',
            "a parameterized type is not the cleared one",
        ),
    ],
)
def test_the_script_exemption_refuses_everything_but_an_inline_data_block(
    markup: str, why: str
) -> None:
    """Widening a deny-by-default gate is only safe if the denial still works.

    ``script`` was admitted only as the GA4 loader, byte for byte, until the dataset
    descriptor needed an inline ``application/ld+json`` data block, which HTML never
    evaluates. Each row here is a shape
    the widened gate must still catch, asserted directly rather than inferred from the real
    page carrying none of them.
    """
    found, _ = references(f"<html><head>{markup}</head><body><p>x</p></body></html>")
    scripts = [reference for reference in found if reference.tag == "script"]
    assert [reference.subresource for reference in scripts] == [True], why


def test_an_inline_ld_json_data_block_is_the_one_shape_admitted() -> None:
    found, _ = references(
        '<html><head><script type="application/ld+json">{"a":1}</script></head>'
        "<body><p>x</p></body></html>"
    )
    scripts = [reference for reference in found if reference.tag == "script"]
    assert [reference.subresource for reference in scripts] == [False]


def test_the_page_script_tags_are_the_descriptor_and_the_ga4_loader(page: str) -> None:
    """The exemption is asserted against the real page's markup, not left to the scanner.

    Without this, a page that had lost its descriptor and a page that had gained a
    ``<script>`` the scanner mis-read would both read as self-contained.
    """
    scripts = re.findall(r"<script\b[^>]*>", page)
    assert scripts == ['<script type="application/ld+json">', "<script>"], (
        f"the page's <script> elements are not the two this gate allows: {scripts}"
    )


# --- the subject pages, which are their own page class --------------------------------------

SUBJECT_OVERHEAD_BUDGET: Final = 7_500
"""Bytes a page under ``site/subjects/`` may spend on everything that is not a listed row.

The stylesheet, the head, the disclaimer, the intro prose, the navigation and the footer.
The heaviest is 5,493 today, so this is 1.37x headroom; the shared stylesheet's opt-out
button style (GA4, #100) accounts for 141 of it, though these pages carry no button. It is
the same number for all three kinds of page under that directory, because they share the
shell that accounts for most of it.
"""

SUBJECT_PER_AUTHORIZATION_BUDGET: Final = 900
"""Bytes a subject page may spend per authorization it lists. The heaviest is 742, which is
1.21x headroom: enough for another sentence of provenance per authorization and not enough
to absorb a doubling."""

SUBJECT_ROW_BUDGET: Final = 140
"""Bytes a table row may cost on the subject index and the not-subject-coded page. The
heaviest is 108."""


def _spent(page: str, pattern: str) -> tuple[int, int, int]:
    """(total bytes, bytes in the repeating unit, count of units)."""
    units = re.findall(pattern, page, re.DOTALL)
    return len(page.encode("utf-8")), sum(len(u.encode("utf-8")) for u in units), len(units)


@pytest.fixture(scope="module")
def subject_pages(real_catalog: Catalog) -> dict[str, str]:
    return subjects_module.pages(real_catalog)


def test_the_subject_pages_fetch_nothing_to_render(subject_pages: dict[str, str]) -> None:
    """One file each, on the same inline stylesheet. Same rule as the main page.

    A second page class is the easiest way to publish a stylesheet link that the gate on
    the first page class would have refused.
    """
    assert len(subject_pages) > 100, "the subject pages did not render, so this checks nothing"
    for name, page in subject_pages.items():
        found, elements = references(page)
        assert elements > 10, f"{name}: the scan walked {elements} elements"
        fetches = [f"<{r.tag}> fetches {r.target!r}" for r in found if r.subresource]
        assert fetches == [], f"{name} is not self-contained: {fetches}"


def test_every_subject_page_stays_within_its_weight_budget(
    subject_pages: dict[str, str], real_catalog: Catalog
) -> None:
    """Held against the heaviest page, not the mean.

    Averaged over 323 pages, one page that had grown by ten kilobytes would move the figure
    by thirty bytes and pass. The budget is about markup per unit, and the unit is a page.
    """
    reaches = {
        subject.code: len(subject.reaches) for subject in subjects_module.group(real_catalog)
    }
    checked = 0
    for name, page in subject_pages.items():
        if name in (subjects_module.INDEX_FILENAME, subjects_module.NOT_SUBJECT_CODED_FILENAME):
            continue
        code = name.split("/")[1].removesuffix(".html")
        total, in_blocks, blocks = _spent(page, r'<article class="cred">.*?</article>')
        assert blocks == reaches[code], (
            f"{name} renders {blocks} blocks for {reaches[code]} authorizations, so the "
            "split this budget assumes is not the page's shape"
        )
        overhead = total - in_blocks
        assert overhead <= SUBJECT_OVERHEAD_BUDGET, (
            f"{name} spends {overhead:,} bytes outside its listed authorizations, over "
            f"the {SUBJECT_OVERHEAD_BUDGET:,} budget"
        )
        assert in_blocks / blocks <= SUBJECT_PER_AUTHORIZATION_BUDGET, (
            f"{name} spends {in_blocks / blocks:,.0f} bytes per authorization it lists, "
            f"over the {SUBJECT_PER_AUTHORIZATION_BUDGET:,} budget"
        )
        checked += 1
    assert checked == len(reaches), "a subject page went unmeasured"


@pytest.mark.parametrize(
    "name", [subjects_module.INDEX_FILENAME, subjects_module.NOT_SUBJECT_CODED_FILENAME]
)
def test_the_two_table_pages_stay_within_their_row_budget(
    subject_pages: dict[str, str], name: str
) -> None:
    page = subject_pages[name]
    total, in_rows, rows = _spent(page, r"<tr>.*?</tr>")
    assert rows > 1, f"{name} renders no data rows"
    body = rows - 1  # the header row is overhead, not a row of data
    overhead = total - in_rows
    assert overhead <= SUBJECT_OVERHEAD_BUDGET, (
        f"{name} spends {overhead:,} bytes outside its rows, over {SUBJECT_OVERHEAD_BUDGET:,}"
    )
    assert in_rows / rows <= SUBJECT_ROW_BUDGET, (
        f"{name} spends {in_rows / rows:,.0f} bytes per row across {body} rows, over "
        f"the {SUBJECT_ROW_BUDGET:,} budget"
    )


def test_a_heavier_subject_page_is_caught(subject_pages: dict[str, str]) -> None:
    """The control, in both directions, as the main page's budget has.

    Growth in the markup per authorization must fail; the Commission aligning more
    authorizations to one subject at today's weight each must not, or the budget becomes a
    cap on how much of the table this project may publish.
    """
    fixed = (subjects_module.INDEX_FILENAME, subjects_module.NOT_SUBJECT_CODED_FILENAME)
    name, page = max(
        ((n, p) for n, p in subject_pages.items() if n not in fixed),
        key=lambda pair: len(pair[1]),
    )
    _total, in_blocks, blocks = _spent(page, r'<article class="cred">.*?</article>')
    assert blocks > 1, f"{name} lists one authorization, so doubling it proves less"
    assert in_blocks * 2 / blocks > SUBJECT_PER_AUTHORIZATION_BUDGET, (
        "doubling the markup per listed authorization would pass"
    )
    assert in_blocks * 2 / (blocks * 2) <= SUBJECT_PER_AUTHORIZATION_BUDGET, (
        "twice as many authorizations at today's weight each would fail, which would make "
        "this a cap on the Commission's table rather than on this project's markup"
    )


def test_the_committed_subject_pages_are_the_pages_this_budget_measured(
    subject_pages: dict[str, str],
) -> None:
    """The budget is about the files that are served, so it is checked against them too."""
    for name in subject_pages:
        committed = SITE / name
        assert committed.is_file(), f"{name} is not committed under site/"
        assert len(committed.read_bytes()) <= (
            SUBJECT_OVERHEAD_BUDGET
            + SUBJECT_PER_AUTHORIZATION_BUDGET * len(re.findall(r"<h3>", subject_pages[name]))
            + SUBJECT_ROW_BUDGET * len(re.findall(r"<tr>", subject_pages[name]))
        ), f"{name} is over its budget as committed"


_DOCUMENTED_SUBJECT_BUDGET = re.compile(
    r"a subject page's budget is ([\d,]+) bytes of fixed overhead plus ([\d,]+) per "
    r"authorization it lists, and the two table pages get ([\d,]+) plus ([\d,]+) per row"
)
_DOCUMENTED_SUBJECT_SPEND = re.compile(
    r"Today the heaviest subject page spends ([\d,]+) and ([\d,]+)"
)


def test_the_documented_subject_budget_is_the_one_held(subject_pages: dict[str, str]) -> None:
    """The README's subject-page figures, bound the same way the main page's are."""
    text = " ".join(README.read_text(encoding="utf-8").split())
    assert _figure(_DOCUMENTED_SUBJECT_BUDGET, text) == (
        SUBJECT_OVERHEAD_BUDGET,
        SUBJECT_PER_AUTHORIZATION_BUDGET,
        SUBJECT_OVERHEAD_BUDGET,
        SUBJECT_ROW_BUDGET,
    ), "README.md publishes a subject-page budget this module does not hold the pages to"

    worst_overhead = 0
    worst_per = 0
    for name, page in subject_pages.items():
        if name in (subjects_module.INDEX_FILENAME, subjects_module.NOT_SUBJECT_CODED_FILENAME):
            continue
        total, in_blocks, blocks = _spent(page, r'<article class="cred">.*?</article>')
        worst_overhead = max(worst_overhead, total - in_blocks)
        worst_per = max(worst_per, round(in_blocks / blocks))
    assert _figure(_DOCUMENTED_SUBJECT_SPEND, text) == (worst_overhead, worst_per), (
        "README.md says the heaviest subject page spends something other than what it "
        f"spends. The measured figures are {worst_overhead:,} and {worst_per:,}."
    )
