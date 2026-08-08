"""The page states what it is, escapes what it renders, and counts what it shows."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser

from chalkline import ctid as ctid_module
from chalkline.model import Catalog, build_catalog
from chalkline.site import render
from chalkline.sources import leaflets as leaflets_module
from chalkline.sources import sort_table
from tests.conftest import row, table

VOID = {"meta", "br", "hr", "img", "input", "link", "source", "area", "col"}


class _Balance(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.unbalanced: list[str] = []

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag:
            self.unbalanced.append(tag)
        else:
            self.stack.pop()


def rendered(catalog: Catalog) -> str:
    ctids = {a.key: ctid_module.mint() for a in catalog.authorizations}
    return render(catalog, ctids, {})


def test_the_page_is_balanced_html(
    real_catalog: Catalog, leaflet_index: dict[str, leaflets_module.Leaflet]
) -> None:
    ctids = ctid_module.load_ledger()
    parser = _Balance()
    parser.feed(render(real_catalog, ctids, leaflet_index))
    assert parser.unbalanced == []
    assert parser.stack == []


def test_the_page_says_it_is_unofficial(real_catalog: Catalog) -> None:
    page = render(real_catalog, ctid_module.load_ledger(), {})
    assert "Unofficial demonstration" in page
    assert "not affiliated" in page.lower()
    assert "Credential Engine" in page


def test_counts_come_from_the_catalog(real_catalog: Catalog) -> None:
    page = render(real_catalog, ctid_module.load_ledger(), {})
    assert f"<b>{len(real_catalog.authorizations)}</b>" in page
    assert f"<b>{len(real_catalog.exclusions)}</b>" in page


def test_every_exclusion_and_its_reason_are_shown(real_catalog: Catalog) -> None:
    page = render(real_catalog, ctid_module.load_ledger(), {})
    for exclusion in real_catalog.exclusions:
        assert html.escape(exclusion.reason, quote=True) in page
        assert html.escape(exclusion.title, quote=True) in page


def test_markup_in_source_text_is_escaped() -> None:
    """A cell whose *text* is angle brackets, written as entities the way HTML requires."""
    catalog = build_catalog(
        sort_table.parse(
            table(row(title="Cred &lt;script&gt;alert(1)&lt;/script&gt;", subject="A &amp; B"))
        )
    )
    parsed = catalog.authorizations[0]
    assert parsed.title == "Cred <script>alert(1)</script>"
    page = rendered(catalog)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "A &amp; B" in page


def test_a_not_subject_coded_credential_says_so() -> None:
    catalog = build_catalog(sort_table.parse(table(row(subject_code="NONE", subject=""))))
    assert "not subject-coded" in rendered(catalog)


def test_a_leaflet_link_appears_when_one_matched() -> None:
    catalog = build_catalog(sort_table.parse(table(row(title="School Nurse Services Credential"))))
    leaflet = leaflets_module.Leaflet(
        code="cl-380", title="School Nurse Services Credential", url="https://example.gov/380"
    )
    ctids = {a.key: ctid_module.mint() for a in catalog.authorizations}
    page = render(catalog, ctids, {leaflets_module.normalize_title(leaflet.title): leaflet})
    assert "https://example.gov/380" in page
    assert "Leaflet CL-380" in page


def test_singular_and_plural_subject_counts() -> None:
    one = build_catalog(sort_table.parse(table(row(subject_code="ART", subject="Art"))))
    assert "1 authorized subject<" in rendered(one)
    two = build_catalog(
        sort_table.parse(
            table(row(subject_code="ART", subject="Art"), row(subject_code="MUS", subject="Music"))
        )
    )
    assert "2 authorized subjects<" in rendered(two)


def test_a_credential_without_an_authorization_code_still_renders() -> None:
    catalog = build_catalog(sort_table.parse(table(row(code="", subject_code="NONE", subject=""))))
    page = rendered(catalog)
    assert "authorization <code>" not in page
    assert re.search(r"document <code>TC1</code>", page)
