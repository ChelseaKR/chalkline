"""Read CTC's credential leaflet index, and match leaflets to authorizations conservatively.

A leaflet is attached to an authorization on one rule and one rule only: the leaflet's
published title and the authorization's published title are the same string after case
folding and punctuation normalization. Nothing else. No prefix matching, no keyword overlap,
no reasoning from a document code to a leaflet number.

The rule is deliberately strict, and it leaves most authorizations without a leaflet. That
is the intended outcome: a leaflet link asserts "this Commission document describes this
authorization", and a near-miss title is not evidence for that claim. The count of matched
and unmatched authorizations is derived from the data at build time and recorded in the
coverage statement, so the strictness is visible rather than hidden.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SOURCE_PATH: Final = (
    Path(__file__).resolve().parents[3] / "data" / "source" / "credential-leaflets.html"
)

SOURCE_URL: Final = "https://www.ctc.ca.gov/credentials/leaflets/"
SITE_ROOT: Final = "https://www.ctc.ca.gov"

_LINK_RE: Final = re.compile(
    r'<a[^>]+href="(/credentials/leaflets/[^"#?]+)"[^>]*>(.*?)</a>', re.DOTALL
)
_TAG_RE: Final = re.compile(r"<[^>]+>")
_SPACE_RE: Final = re.compile(r"\s+")
_NON_ALNUM_RE: Final = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class Leaflet:
    """One leaflet as the index publishes it."""

    code: str
    title: str
    url: str


def normalize_title(title: str) -> str:
    """The comparison key: lower case, dashes unified, punctuation reduced to spaces.

    Case and punctuation differ between the two pages for the same document ("CTE)" versus
    "CTE )", en dash versus hyphen), and that variation carries no meaning. Word order and
    word content are untouched, so two different documents cannot normalize together.
    """
    # The dashes are deliberate: CTC uses all three across the two pages for one document.
    lowered = title.lower().replace("\u2013", "-").replace("\u2014", "-")
    return " ".join(_NON_ALNUM_RE.sub(" ", lowered).split())


def _text(fragment: str) -> str:
    stripped = _TAG_RE.sub(" ", fragment)
    return _SPACE_RE.sub(" ", html.unescape(stripped).replace("\xa0", " ")).strip()


def parse(markup: str) -> tuple[Leaflet, ...]:
    """Every leaflet the index links, ordered by leaflet code.

    A link whose text is empty (the index repeats each leaflet as an image link beside its
    text link) contributes nothing and is skipped; the first non-empty title for a given
    path wins, so the parse is independent of markup duplication.
    """
    found: dict[str, str] = {}
    for path, label in _LINK_RE.findall(markup):
        code = path.strip("/").rsplit("/", 1)[-1]
        if not code or code == "leaflets":
            continue
        title = _text(label)
        if title and not found.get(code):
            found[code] = title
    return tuple(
        Leaflet(code=code, title=found[code], url=f"{SITE_ROOT}/credentials/leaflets/{code}/")
        for code in sorted(found)
    )


def load(path: Path | None = None) -> tuple[Leaflet, ...]:
    """Parse the vendored leaflet index (or another copy, for tests)."""
    return parse((path or SOURCE_PATH).read_text(encoding="utf-8"))


def index_by_title(leaflets: tuple[Leaflet, ...]) -> dict[str, Leaflet]:
    """Normalized title to leaflet, dropping any title two leaflets share.

    An ambiguous title is not a match: if two leaflets normalize alike this code cannot tell
    which one describes the authorization, so it offers neither.
    """
    counts: dict[str, int] = {}
    for leaflet in leaflets:
        key = normalize_title(leaflet.title)
        counts[key] = counts.get(key, 0) + 1
    return {
        normalize_title(leaflet.title): leaflet
        for leaflet in leaflets
        if counts[normalize_title(leaflet.title)] == 1
    }
