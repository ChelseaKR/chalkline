"""The published page, reviewed against a named list of accessibility checks.

The README's Standards Conformance table carried this row as an open obligation: "Applies
-- the published page is human-facing, so it is in scope. **Not met:** there is no automated
accessibility gate in CI, and no manual review of the generated page has been performed."
This module is the gate, and the review that produced it found three real defects in the
page `chalkline build` was publishing:

* the exclusions table's four ``<th>`` cells carried no ``scope``, so nothing said whether
  they head a column or a row (technique H63, for WCAG 1.3.1 Info and Relationships);
* ``.counts`` and ``.subjects`` are styled ``list-style: none``, and Safari removes list
  semantics from a list whose markers are removed, so 134 list items stopped being announced
  as lists at all. ``role="list"`` restores what the styling took away;
* ``.wrap`` is a horizontally scrolling region with no way into it from a keyboard. A region
  that scrolls only under a pointer is content a keyboard-only reader cannot reach (WCAG
  2.1.1 Keyboard), and the exclusions table is the only place this page puts content in one.

What this gate is, exactly
--------------------------

It checks the rendered page against the list in :data:`CHECKS` and nothing else. It is not
an audit: no assistive technology is driven, no browser lays the page out, reading order and
comprehension are not assessed, and a page can satisfy every check here and still be hard to
use. What it can do is fail, on this page, for a reason a reader can name, and every check
below is exercised against a deliberately broken copy of the real page so that a green run
is a statement about the page rather than about the check.

The counts each check examined are asserted too. A check that ran over nothing reports the
same empty problem list as a check that ran over everything and found nothing wrong, and the
difference between those two is the whole point of running it.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Final

import pytest

import chalkline.site
from chalkline import ctid as ctid_module
from chalkline.attachment import Attachment
from chalkline.model import Catalog
from chalkline.site import render


def stylesheet() -> str:
    """The stylesheet the page embeds, read through the module so a test can replace it."""
    return chalkline.site.STYLE


TEXT_CONTRAST: Final = 4.5
"""WCAG 1.4.3 Contrast (Minimum), level AA, for text below 18.66px bold or 24px regular.
Every colour pair this page makes is small text, so the large-text allowance never applies."""


@dataclass(frozen=True, slots=True)
class Element:
    """One start tag of the rendered page, with its attributes."""

    tag: str
    attrs: dict[str, str]


class _Elements(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[Element] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.found.append(Element(tag, {name: value or "" for name, value in attrs}))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def elements(page: str) -> list[Element]:
    parser = _Elements()
    parser.feed(page)
    return parser.found


@dataclass
class Report:
    """What one run of the checks found, and how much each one looked at."""

    problems: list[str] = field(default_factory=list)
    examined: dict[str, int] = field(default_factory=dict)

    def fault(self, code: str, message: str) -> None:
        self.problems.append(f"{code}: {message}")

    def looked_at(self, code: str, count: int) -> None:
        self.examined[code] = count


# --- the checks ---------------------------------------------------------------------------


def check_language(page: str, report: Report) -> None:
    """WCAG 3.1.1 Language of Page. Without it a screen reader guesses the voice."""
    roots = [e for e in elements(page) if e.tag == "html"]
    report.looked_at("lang", len(roots))
    for root in roots:
        if not root.attrs.get("lang", "").strip():
            report.fault("lang", "the <html> element declares no lang")


def check_title(page: str, report: Report) -> None:
    """WCAG 2.4.2 Page Titled."""
    titles = re.findall(r"<title>(.*?)</title>", page, re.DOTALL)
    report.looked_at("title", len(titles))
    if len(titles) != 1 or not titles[0].strip():
        report.fault("title", f"the page publishes {len(titles)} non-empty <title> elements")


def check_heading_order(page: str, report: Report) -> None:
    """WCAG 1.3.1. One h1, and no level skipped on the way down: h2 never follows h4."""
    levels = [int(tag[1]) for tag in re.findall(r"<(h[1-6])[^>]*>", page)]
    report.looked_at("heading-order", len(levels))
    if levels.count(1) != 1:
        report.fault("heading-order", f"the page has {levels.count(1)} <h1> elements, not one")
    for before, after in itertools.pairwise(levels):
        if after > before + 1:
            report.fault("heading-order", f"an h{after} follows an h{before}, skipping a level")


def check_table_headers(page: str, report: Report) -> None:
    """Technique H63: a th says whether it heads a column or a row, so cells can be read."""
    headers = [e for e in elements(page) if e.tag == "th"]
    report.looked_at("th-scope", len(headers))
    for header in headers:
        if header.attrs.get("scope") not in {"col", "row", "colgroup", "rowgroup"}:
            report.fault("th-scope", f"a <th> carries scope={header.attrs.get('scope')!r}")


def unmarkered_classes(style: str) -> set[str]:
    """Every class the stylesheet strips list markers from."""
    return {
        match.group(1)
        for match in re.finditer(r"\.([\w-]+)\s*\{[^}]*list-style:\s*none", style, re.DOTALL)
    }


def check_list_semantics(page: str, report: Report) -> None:
    """A list whose markers CSS removes is no longer announced as a list in Safari.

    This is browser behaviour rather than a WCAG success criterion in its own right: WebKit
    treats ``list-style: none`` as a signal that the author did not mean a list, and drops
    the role. ``role="list"`` says otherwise. The effect it prevents is the one 1.3.1 is
    about, a relationship visible in the markup that does not reach the reader.
    """
    stripped = unmarkered_classes(stylesheet())
    assert stripped, "the stylesheet strips markers from no class; this check has no subject"
    lists = [
        e
        for e in elements(page)
        if e.tag in {"ul", "ol"} and set(e.attrs.get("class", "").split()) & stripped
    ]
    report.looked_at("list-semantics", len(lists))
    for found in lists:
        if found.attrs.get("role") != "list":
            report.fault(
                "list-semantics",
                f"<{found.tag} class={found.attrs.get('class')!r}> has its markers removed "
                'by the stylesheet and carries no role="list"',
            )


def scrolling_classes(style: str) -> set[str]:
    """Every class the stylesheet makes a horizontally scrolling region."""
    return {
        match.group(1)
        for match in re.finditer(r"\.([\w-]+)\s*\{[^}]*overflow-x:\s*auto", style, re.DOTALL)
    }


def check_scrollable_regions(page: str, report: Report) -> None:
    """WCAG 2.1.1 Keyboard. A region that scrolls only under a pointer excludes a keyboard."""
    scrolls = scrolling_classes(stylesheet())
    assert scrolls, "the stylesheet declares no scrolling region; this check has no subject"
    regions = [e for e in elements(page) if set(e.attrs.get("class", "").split()) & scrolls]
    report.looked_at("scroll-focusable", len(regions))
    for region in regions:
        if region.attrs.get("tabindex") != "0":
            report.fault(
                "scroll-focusable",
                f"<{region.tag} class={region.attrs.get('class')!r}> scrolls horizontally "
                "and cannot be focused, so a keyboard cannot scroll it",
            )
        elif not (region.attrs.get("aria-label") or region.attrs.get("aria-labelledby")):
            report.fault(
                "scroll-focusable",
                f"<{region.tag} class={region.attrs.get('class')!r}> takes focus and has no "
                "accessible name, so nothing says what the reader has landed on",
            )


def check_image_alternatives(page: str, report: Report) -> None:
    """WCAG 1.1.1 Non-text Content.

    The page renders no images today and the examined count says so out loud, because a
    check whose subject is absent and a check whose subject is clean look identical from
    outside. It stays because the page is generated, and the day one is added is exactly
    the day nobody thinks about this.
    """
    images = [e for e in elements(page) if e.tag == "img"]
    report.looked_at("img-alt", len(images))
    for image in images:
        if "alt" not in image.attrs:
            report.fault("img-alt", f"<img src={image.attrs.get('src')!r}> carries no alt")


def check_zoom_is_allowed(page: str, report: Report) -> None:
    """WCAG 1.4.4 Resize Text. A viewport that pins the scale locks out magnification."""
    viewports = [e for e in elements(page) if e.tag == "meta" and e.attrs.get("name") == "viewport"]
    report.looked_at("zoom", len(viewports))
    for viewport in viewports:
        content = viewport.attrs.get("content", "").replace(" ", "").lower()
        if "user-scalable=no" in content:
            report.fault("zoom", "the viewport sets user-scalable=no")
        maximum = re.search(r"maximum-scale=([\d.]+)", content)
        if maximum is not None and float(maximum.group(1)) < 2:
            report.fault("zoom", f"the viewport caps zoom at {maximum.group(1)}")


# --- contrast -------------------------------------------------------------------------------

PALETTES: Final = (
    ("light", r":root\s*\{(.*?)\}"),
    ("dark", r"prefers-color-scheme:\s*dark\s*\)\s*\{\s*:root\s*\{(.*?)\}"),
)
"""Where each palette's tokens are declared in the stylesheet."""

PAIRS: Final = (
    ("ink", "bg", "body sets color: var(--ink) on background: var(--bg)"),
    ("ink", "panel", ".notice sets background: var(--panel) and inherits the body's ink"),
    ("muted", "bg", ".from, .meta, .counts span, summary and th all set color: var(--muted)"),
    ("muted", "panel", ".meta code sets background: var(--panel) inside .meta's muted text"),
    ("accent", "bg", "a sets color: var(--accent)"),
    ("accent", "panel", "a inside .notice, which sets background: var(--panel)"),
)
"""Every foreground/background pairing the stylesheet actually makes, with the rule that
makes it. Hand-kept, and guarded below: a colour token that appears in no pairing and is not
recorded as decorative fails, so a new token cannot be added without being placed."""

DECORATIVE: Final = {
    "rule": (
        "a hairline separator between rows and blocks. It carries no text and identifies no "
        "control, so neither 1.4.3 (text) nor 1.4.11 (user interface components and "
        "graphical objects) applies to it. It is named here rather than skipped silently."
    )
}


def palette(name: str, pattern: str, style: str) -> dict[str, str]:
    block = re.search(pattern, style, re.DOTALL)
    assert block is not None, f"the stylesheet declares no {name} palette"
    found = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block.group(1)))
    assert found, f"the {name} palette declares no colour tokens"
    return found


def relative_luminance(colour: str) -> float:
    """WCAG's relative luminance of an sRGB colour."""
    channels = [int(colour[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    """WCAG's contrast ratio between two sRGB colours."""
    luminances = sorted((relative_luminance(foreground), relative_luminance(background)))
    return (luminances[1] + 0.05) / (luminances[0] + 0.05)


def check_contrast(page: str, report: Report) -> None:
    """WCAG 1.4.3 Contrast (Minimum), over both palettes the page ships."""
    del page  # the palettes are the stylesheet's, and the page embeds it verbatim
    examined = 0
    for name, pattern in PALETTES:
        tokens = palette(name, pattern, stylesheet())
        placed = {token for pair in PAIRS for token in pair[:2]} | set(DECORATIVE)
        unplaced = sorted(set(tokens) - placed)
        if unplaced:
            report.fault(
                "contrast",
                f"the {name} palette declares {unplaced}, which no pairing uses and "
                "DECORATIVE does not name; nothing checks their contrast",
            )
        for foreground, background, rule in PAIRS:
            if foreground not in tokens or background not in tokens:
                report.fault("contrast", f"the {name} palette is missing {foreground}/{background}")
                continue
            examined += 1
            ratio = contrast(tokens[foreground], tokens[background])
            if ratio < TEXT_CONTRAST:
                report.fault(
                    "contrast",
                    f"{name}: {foreground} on {background} is {ratio:.2f}:1, below "
                    f"{TEXT_CONTRAST}:1 ({rule})",
                )
    report.looked_at("contrast", examined)


@dataclass(frozen=True, slots=True)
class Check:
    """One check, and the code every problem it reports is prefixed with."""

    code: str
    run: Callable[[str, Report], None]


CHECKS: Final[tuple[Check, ...]] = (
    Check("lang", check_language),
    Check("title", check_title),
    Check("heading-order", check_heading_order),
    Check("th-scope", check_table_headers),
    Check("list-semantics", check_list_semantics),
    Check("scroll-focusable", check_scrollable_regions),
    Check("img-alt", check_image_alternatives),
    Check("zoom", check_zoom_is_allowed),
    Check("contrast", check_contrast),
)
"""Everything this gate checks. The list is the gate's scope, and it is short on purpose."""


def review(page: str) -> Report:
    report = Report()
    for check in CHECKS:
        check.run(page, report)
    return report


@pytest.fixture(scope="module")
def page(real_catalog: Catalog, real_attachments: dict[str, Attachment]) -> str:
    """The page as `chalkline build` writes it, from the vendored sources."""
    return render(real_catalog, ctid_module.load_ledger(), real_attachments)


def test_the_published_page_passes_every_check(page: str) -> None:
    assert review(page).problems == []


EXPECTED_SUBJECTS: Final = {
    "lang": 1,
    "title": 1,
    "img-alt": 0,
    "zoom": 1,
    "contrast": 12,
}
"""How much each check must find to look at, where the number is fixed by the page's shape.

``img-alt`` is 0 and stated: the page renders no images, so that check passes today by
having nothing to judge, and saying so is the difference between a clean result and an
empty one. ``contrast`` is 12: six pairings in each of two palettes.
"""


def test_every_check_looked_at_something(page: str) -> None:
    """The denominator. A check that examined nothing reports the same clean result."""
    examined = review(page).examined
    assert set(examined) == {
        "lang",
        "title",
        "heading-order",
        "th-scope",
        "list-semantics",
        "scroll-focusable",
        "img-alt",
        "zoom",
        "contrast",
    }, "a check ran without recording what it examined"
    for code, count in EXPECTED_SUBJECTS.items():
        assert examined[code] == count, f"{code} examined {examined[code]}, expected {count}"
    for code in ("heading-order", "th-scope", "list-semantics", "scroll-focusable"):
        assert examined[code] > 0, f"{code} found nothing on the page to check"


BREAKAGES: Final = (
    ("lang", '<html lang="en">', "<html>"),
    ("title", "<title>Chalkline", "<title></title><s>Chalkline"),
    ("heading-order", "modeled onto CTDL</h1>", "modeled onto CTDL</h1><h4>Skipped</h4>"),
    ("th-scope", '<th scope="col">Authorization</th>', "<th>Authorization</th>"),
    ("list-semantics", '<ul class="counts" role="list">', '<ul class="counts">'),
    ("scroll-focusable", ' tabindex="0"><table>', "><table>"),
    ("scroll-focusable", ' aria-label="Authorizations not modeled"', ""),
    ("img-alt", "<main>", '<main><img src="seal.png">'),
    ("zoom", "initial-scale=1", "initial-scale=1, user-scalable=no"),
)
"""One deliberate break per check, applied to the real page. The point of the list is that
every check in :data:`CHECKS` appears in it: a check nothing can break is a check that
cannot fail, which is the failure mode this whole module exists to avoid."""


@pytest.mark.parametrize(("code", "original", "broken"), BREAKAGES, ids=lambda v: str(v)[:28])
def test_each_check_rejects_a_page_that_breaks_it(
    page: str, code: str, original: str, broken: str
) -> None:
    assert original in page, f"the page no longer contains {original!r}, so nothing was broken"
    found = review(page.replace(original, broken, 1)).problems
    assert any(problem.startswith(f"{code}: ") for problem in found), (
        f"replacing {original!r} with {broken!r} produced {found}, none of them from {code}"
    )


@pytest.mark.parametrize(
    ("original", "broken", "expected"),
    [
        ("--muted: #5a5f66", "--muted: #c9ccd0", "a light-palette token washed out to 1.86:1"),
        ("--accent: #e0a678", "--accent: #2b2f33", "a dark-palette token darkened to 1.35:1"),
        ("--panel: #f3f0e9", "--panel: #6d6a63", "a background nobody rechecked after an edit"),
        ("--rule: #d9d5cc;", "--hairline: #d9d5cc;", "a renamed token that no pairing places"),
    ],
    ids=lambda value: str(value)[:34],
)
def test_the_contrast_check_rejects_a_palette_it_should(
    page: str,
    monkeypatch: pytest.MonkeyPatch,
    original: str,
    broken: str,
    expected: str,
) -> None:
    """The contrast check reads the stylesheet, so it is broken there rather than in the page.

    The last case is the denominator working: renaming a token leaves the palette declaring
    a colour that no pairing in PAIRS and no entry in DECORATIVE accounts for, and a check
    that quietly ignored it would be checking less than it says it does.
    """
    assert original in stylesheet(), f"the stylesheet no longer declares {original!r}"
    monkeypatch.setattr(chalkline.site, "STYLE", stylesheet().replace(original, broken))
    problems = review(page).problems
    assert any(problem.startswith("contrast: ") for problem in problems), (
        f"{expected} produced {problems}"
    )


def test_every_check_is_covered_by_a_breakage() -> None:
    """No check may sit in CHECKS without something above proving it can fail.

    This is the check on the checks. A gate is easy to grow by adding a function that reads
    the page and never disagrees with it; the cost of adding one here is that it has to come
    with the edit that makes it fail.
    """
    codes = [check.code for check in CHECKS]
    assert len(set(codes)) == len(codes), f"two checks share a code: {codes}"
    proven = {code for code, _, _ in BREAKAGES} | {"contrast"}
    assert sorted(set(codes) - proven) == [], (
        f"these checks have no breakage proving they can fail: {sorted(set(codes) - proven)}"
    )
    assert sorted(proven - set(codes)) == [], (
        f"these breakages name no check: {sorted(proven - set(codes))}"
    )
