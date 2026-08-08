"""Decide, for each authorization, which leaflet describes it and what may be read from it.

This is the policy layer between the two leaflet sources and the export. It answers three
questions in order, and records the answer to each so the counts in the coverage statement
are derived rather than declared:

1. **Which leaflet, if any?** :func:`chalkline.sources.leaflets.match_title`, which is title
   equality and nothing else.
2. **Does the leaflet page confirm its own identity?** :func:`chalkline.sources.leaflet_pages.parse`
   refuses a page whose ``<h1>`` does not carry the code and the title the index gave it.
3. **What does the page state about the document it is titled for?** The classified sections
   in the readable range, which stops where the leaflet moves on to another document.

A leaflet that fails step 2, or whose snapshot is not vendored, still gives the authorization
its Commission link: the index made that association, not this project. What it does not give
is prose, because prose attributed to the wrong document is worse than no prose.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from chalkline.model import Catalog
from chalkline.sources import leaflet_pages, leaflets

NO_SNAPSHOT: Final = (
    "this repository holds no vendored snapshot of the leaflet page, so nothing was read "
    "from it; run `python scripts/fetch_sources.py leaflets <code>` to retrieve one"
)

DESCRIPTION_SECTIONS: Final = (leaflet_pages.AUTHORIZATION,)
"""Section kinds whose text joins the leaflet's lead to form ``ceterms:description``.

The lead is the Commission's prose directly under the leaflet's own title, and an
``Authorization`` section is its prose about what the document lets its holder do. Both are
a "statement, characterization or account of the entity", which is what CTDL's description
says it is. Sections of every other kind are conditions or definitions and are not
descriptions, so they never land here.
"""


@dataclass(frozen=True, slots=True)
class Attachment:
    """One authorization's leaflet: how it was matched, and what could be read from it."""

    match: leaflets.Match
    page: leaflet_pages.LeafletPage | None
    refusal: str | None

    @property
    def leaflet(self) -> leaflets.Leaflet:
        return self.match.leaflet

    @property
    def description(self) -> tuple[str, ...]:
        """The Commission's prose about this document, in the order the leaflet prints it."""
        if self.page is None:
            return ()
        blocks = list(self.page.lead)
        for section in self.page.of_kind(*DESCRIPTION_SECTIONS):
            blocks.extend(section.blocks)
        return tuple(blocks)

    @property
    def requirements(self) -> tuple[leaflet_pages.Section, ...]:
        return () if self.page is None else self.page.of_kind(leaflet_pages.REQUIREMENTS)

    @property
    def renewal(self) -> tuple[leaflet_pages.Section, ...]:
        if self.page is None:
            return ()
        return self.page.of_kind(leaflet_pages.RENEWAL, leaflet_pages.VALIDITY)


def read_leaflet(
    leaflet: leaflets.Leaflet, directory: Path | None = None
) -> tuple[leaflet_pages.LeafletPage | None, str | None]:
    """One leaflet page, or the reason it was not read. Never both, never neither."""
    try:
        return leaflet_pages.load(leaflet.code, leaflet.title, directory), None
    except FileNotFoundError:
        return None, NO_SNAPSHOT
    except ValueError as refusal:
        return None, str(refusal)


def attach(
    catalog: Catalog,
    index: Mapping[str, leaflets.Leaflet],
    directory: Path | None = None,
) -> dict[str, Attachment]:
    """Every authorization that has a leaflet, keyed by the authorization's published triple.

    Each leaflet page is read once however many authorizations it serves, so the six
    Short-Term Staff Permit and Provisional Internship Permit entries share one parse and
    one refusal decision rather than reaching different conclusions about the same file.
    """
    pages: dict[str, tuple[leaflet_pages.LeafletPage | None, str | None]] = {}
    attachments: dict[str, Attachment] = {}
    for authorization in catalog.authorizations:
        match = leaflets.match_title(authorization.title, index)
        if match is None:
            continue
        if match.leaflet.code not in pages:
            pages[match.leaflet.code] = read_leaflet(match.leaflet, directory)
        page, refusal = pages[match.leaflet.code]
        attachments[authorization.key] = Attachment(match=match, page=page, refusal=refusal)
    return attachments
