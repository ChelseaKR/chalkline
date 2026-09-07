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

from chalkline.model import Catalog
from chalkline.site import SITE_URL, STYLE

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
``link`` by :data:`METADATA_LINK_RELS`, and ``script`` by :data:`DATA_BLOCK_SCRIPT_TYPES`."""

DATA_BLOCK_SCRIPT_TYPES: Final = frozenset({"application/ld+json"})
"""The only ``type`` values a ``<script>`` on this page may carry.

Deny by default, with one name on the list, exactly as :data:`METADATA_LINK_RELS` works.

``script`` used to be refused without qualification, on the reasoning that an inline
``<script>`` fetches nothing but still means the page runs code. That reasoning is right
about JavaScript and wrong about one case: HTML defines a ``script`` element whose ``type``
is not a JavaScript MIME type as a **data block**, which the parser hands to the document as
inert text and never evaluates. ``application/ld+json`` is that case, and it is how a page
carries structured data for a harvester that will not execute anything.

So the exemption is by ``type``, and it is narrow in three ways that matter. A ``<script>``
with **no** ``type`` is JavaScript by default and is refused. A ``<script>`` with a
``src`` is refused whatever its ``type``, because a data block that arrives over the network
is still a fetch and self-containment is the other half of this gate. And a ``type`` this
list does not name is refused rather than guessed at: ``module``, ``text/javascript`` and an
empty string all run code.

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

FIXED_OVERHEAD_BUDGET: Final = 20_000
"""Bytes the page may spend on everything that is not a credential: the stylesheet, the
head, the disclaimer, the counts, the prose, the exclusions table, the footer. It is 14,762
today, so this is 1.35x headroom. The stylesheet is 2,797 of it, the head metadata added with
the canonical link is 890, the share-card tags (`og:image` and its type, dimensions and alt
text, plus `twitter:image`) are 588, the accessibility fixes (`scope`, `role`, `tabindex`,
the region label and its focus ring) are 206, and the embedded dataset descriptor is 6,072.

**Raised from 12,000 for that descriptor, on purpose, and this is the reasoning.** The
budget's whole argument is that a flat cap "eventually gets raised to whatever the page
happens to weigh, which is a budget in name only", so a raise has to answer why this is not
that.

*What was added.* One `<script type="application/ld+json">` carrying `site/dataset.jsonld`
verbatim: a schema.org `Dataset` and DCAT `dcat:Dataset` on one node, with a
`schema:DataDownload`/`dcat:Distribution` for each of the three published artifacts, each
with its byte size and sha256. 6,072 bytes measured, which is 2.3% of the 263,272-byte page
and would not move a page-load budget; it is fixed overhead by definition, because it does
not grow when the Commission publishes more rows.

*Why it is worth the bytes.* The artifacts were findable only by reading the README. Dataset
search engines and open-data catalogs harvest schema.org from a page's head, and a
descriptor written to a file that nothing links from the page is a descriptor those
harvesters never see. The alternative, embedding a schema.org summary and keeping the DCAT
and the checksums in the file, is two descriptions of one dataset that can disagree, with
nothing to say which one a harvester believed.

*Why the multiplier, not the number, is what was preserved.* 1.38x headroom was the
discipline the original budget chose; 20,000 against 14,762 is 1.35x, which is the same
discipline against a page that deliberately carries one more thing. A raise to 15,000 would
have left 1.02x and made the next honest addition fail for no reason; a raise to whatever
the page now weighs would have been the failure this docstring warns about."""

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


def _script_is_a_data_block(values: dict[str, str]) -> bool:
    """Whether this ``<script>`` fetches nothing and runs nothing.

    Both halves are required. ``src`` is checked first because a data block served from
    somewhere else is still a subresource, and a ``type`` this project has not cleared is
    treated as code, which is what the HTML default already makes it.
    """
    if values.get("src"):
        return False
    return values.get("type", "").strip().lower() in DATA_BLOCK_SCRIPT_TYPES


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

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.elements += 1
        values = {name: value or "" for name, value in attrs}
        if tag in SUBRESOURCE_TAGS:
            rel = values.get("rel", "") if tag == "link" else ""
            fetches = not (
                (tag == "link" and _link_is_metadata(rel))
                or (tag == "script" and _script_is_a_data_block(values))
            )
            self.found.append(Reference(tag, values.get(SUBRESOURCE_TAGS[tag], ""), fetches, rel))
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
def page(built_artifacts: dict[str, str]) -> str:
    """The page as `chalkline build` writes it, from the vendored sources.

    Taken from the build rather than re-rendered, so the dataset descriptor the build embeds
    is inside the page this budget measures and this gate walks.
    """
    return built_artifacts["index.html"]


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


BREAKAGES: Final = (
    ("<style>", '<script src="https://example.com/a.js"></script><style>'),
    ("<style>", '<link rel="stylesheet" href="https://fonts.example/x.css"><style>'),
    ("<style>", '<link rel="preload" as="font" href="https://fonts.example/i.woff2"><style>'),
    ("<style>", '<link rel="icon" href="favicon.ico"><style>'),
    ("<style>", '<link rel="alternate stylesheet" href="https://fonts.example/x.css"><style>'),
    ("<style>", '<link href="https://fonts.example/x.css"><style>'),
    ("<main>", '<main><img src="seal.png" alt="">'),
    ("<main>", '<main><iframe src="https://example.com/"></iframe>'),
)
"""Eight ways to make the page fetch something, applied to the real page.

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
            "a parameterised type is not the cleared one",
        ),
    ],
)
def test_the_script_exemption_refuses_everything_but_an_inline_data_block(
    markup: str, why: str
) -> None:
    """Widening a deny-by-default gate is only safe if the denial still works.

    ``script`` was refused outright until the dataset descriptor needed an inline
    ``application/ld+json`` data block, which HTML never evaluates. Each row here is a shape
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


def test_the_only_script_on_the_page_is_the_dataset_descriptor(page: str) -> None:
    """The exemption is asserted against the real page, not left to the pass above.

    Without this, a page that had lost its descriptor and a page that had gained a
    ``<script>`` the scanner mis-read would both read as self-contained.
    """
    scripts = re.findall(r"<script\b[^>]*>", page)
    assert scripts == ['<script type="application/ld+json">'], (
        f"the page's <script> elements are not the one data block this gate allows: {scripts}"
    )
