"""Render the modeled credentials as one self-contained, browsable HTML page.

No external stylesheet, script, font, or image: the page is one file and works offline,
which is the same discipline the rest of this project applies to its data. Every number on
the page is counted from the catalog at render time rather than written into the template,
so the page cannot claim a total the data does not support.

The page states, above everything else, that it is unofficial and models publicly published
Commission information for demonstration. That statement is part of the artifact, not a
footnote to it.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from typing import Final

from chalkline.attachment import Attachment
from chalkline.ctdl.export import DISCLAIMER_BODY, DISCLAIMER_LEAD, description_of
from chalkline.model import Authorization, Catalog
from chalkline.sources.sort_table import SOURCE_URL as SORT_TABLE_URL

TITLE: Final = "Chalkline: California educator credential authorizations as CTDL"

# Where this page is served from, in full, including the project path.
#
# GitHub Pages serves this repository at a path under chelseakr.github.io,
# which five sibling projects also publish under, and
# https://chelseakr.github.io/ is itself a 404. A canonical or an og:url naming
# the bare origin would therefore not be a shorter spelling of the same
# address: it would tell a crawler that six unrelated projects are one page,
# and a root-relative href would land on another project or on nothing.
# tests/test_site.py holds this to the project path.
SITE_URL: Final = "https://chelseakr.github.io/chalkline/"

# What the page is, said the way the page says it. Every clause is on the page
# already: the h1 names the modeling, the paragraph under it names the sort
# table and the leaflets as the only sources, and the notice above both says
# the project is unofficial.
#
# No count. The page prints its own tallies, counted from the catalog at build
# time by _counts_block, and tests/test_documented_counts.py holds the prose
# figures to the same data. A number repeated here would be a third copy that
# nothing derives and nothing checks.
DESCRIPTION: Final = (
    "An unofficial model of California educator credential authorizations as CTDL "
    "JSON-LD, built only from the Commission on Teacher Credentialing's published "
    "Authorization Sort Table and its credential leaflets."
)

# The share image. Absolute, and carrying the project path, for the same reason
# SITE_URL is: a preview fetcher retrieves it from its own machine with no page
# context, so a relative name resolves against whatever it takes the base to be
# and a root-relative one lands on a sibling project's site.
#
# It is not written by `chalkline build`, being committed art rather than
# derived data, so it is registered in cli.PUBLISHED_BY_ANOTHER_GATE with the
# test that holds it. That registry exists precisely so a file published from
# site/ cannot sit there unaccounted for.
#
# The card repeats the disclaimer. The page leads with "Unofficial" and the
# whole project turns on not being mistaken for the Commission's own; a link
# preview is the one surface where that notice is dropped by default, and it is
# also the surface a stranger sees first.
CARD_FILENAME: Final = "og-card.png"
CARD_URL: Final = SITE_URL + CARD_FILENAME
CARD_WIDTH: Final = 1200
CARD_HEIGHT: Final = 630
CARD_ALT: Final = (
    "Chalkline, marked unofficial: California educator credential authorizations as CTDL."
)

STYLE: Final = """
:root { color-scheme: light dark; --ink: #1a1c1e; --bg: #fbfaf7; --muted: #5a5f66;
  --rule: #d9d5cc; --accent: #7a3b12; --panel: #f3f0e9; }
@media (prefers-color-scheme: dark) { :root { --ink: #e8e6e1; --bg: #16181a;
  --muted: #a2a8b0; --rule: #32363b; --accent: #e0a678; --panel: #1e2124; } }
* { box-sizing: border-box; }
body { margin: 0; padding: 0 1.25rem 4rem; background: var(--bg); color: var(--ink);
  font: 16px/1.6 ui-serif, Georgia, "Times New Roman", serif; }
main { max-width: 62rem; margin: 0 auto; }
h1 { font-size: 1.9rem; line-height: 1.2; margin: 2.5rem 0 0.5rem; }
h2 { font-size: 1.25rem; margin: 3rem 0 0.75rem; border-bottom: 1px solid var(--rule);
  padding-bottom: 0.3rem; }
p, li { max-width: 48rem; }
a { color: var(--accent); }
.notice { background: var(--panel); border-left: 3px solid var(--accent);
  padding: 0.9rem 1.1rem; margin: 1.5rem 0; font-size: 0.95rem; }
.counts { display: flex; flex-wrap: wrap; gap: 1.5rem; padding: 0; list-style: none;
  margin: 1.5rem 0; }
.counts li { border-left: 2px solid var(--rule); padding-left: 0.8rem; }
.counts b { display: block; font-size: 1.5rem; font-family: ui-sans-serif, system-ui, sans-serif; }
.counts span { font-size: 0.85rem; color: var(--muted); }
.cred { border-top: 1px solid var(--rule); padding: 1.1rem 0; }
.cred h3 { margin: 0 0 0.35rem; font-size: 1.05rem; }
.meta { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.8rem;
  color: var(--muted); margin: 0 0 0.5rem; }
.meta code { background: var(--panel); padding: 0.1rem 0.35rem; border-radius: 3px; }
.note { font-size: 0.92rem; margin: 0.4rem 0; white-space: pre-line; }
.from { color: var(--muted); font-size: 0.82rem; margin: 0.35rem 0; }
details { margin-top: 0.5rem; font-size: 0.9rem; }
summary { cursor: pointer; color: var(--muted); }
.subjects { margin: 0.6rem 0 0; padding: 0; list-style: none;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr)); gap: 0.3rem; }
.subjects li { border-left: 2px solid var(--rule); padding-left: 0.6rem; font-size: 0.88rem; }
.subjects code { color: var(--muted); }
.conditions { margin: 0.6rem 0 0; padding-left: 1.1rem; }
.conditions li { margin-bottom: 0.3rem; }
.wrap { overflow-x: auto; }
.wrap:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem; margin-top: 0.5rem; }
th, td { text-align: left; padding: 0.45rem 0.7rem; border-bottom: 1px solid var(--rule);
  vertical-align: top; }
th { font-family: ui-sans-serif, system-ui, sans-serif; font-size: 0.78rem;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
footer { margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--rule);
  font-size: 0.85rem; color: var(--muted); }
"""


def _e(text: str) -> str:
    return html.escape(text, quote=True)


def _counts_block(catalog: Catalog, tallies: Mapping[str, int]) -> str:
    published = len(catalog.authorizations) + len(catalog.exclusions)
    items = [
        (catalog.source_rows, "rows published in the sort table"),
        (published, "authorizations in those rows"),
        (len(catalog.authorizations), "modeled as ceterms:License"),
        (len(catalog.exclusions), "excluded, with reasons below"),
        (tallies["alignments"], "subject alignments emitted"),
        (tallies["resolved"], "scopes resolved by following a cross-reference"),
        (tallies["leaflets"], "linked to a CTC leaflet"),
        (tallies["descriptions"], "carrying a description"),
        (tallies["conditions"], "carrying requirements or renewal terms"),
    ]
    cells = "".join(f"<li><b>{value}</b><span>{_e(label)}</span></li>" for value, label in items)
    return f'<ul class="counts" role="list">{cells}</ul>'


def _resolution_block(authorization: Authorization) -> str:
    """Where a resolved authorization's subjects came from, row by row."""
    resolution = authorization.resolved_from
    if resolution is None:
        return ""
    rows = ", ".join(
        f"<code>{_e(source.authorization_code)}</code> ({source.subjects_supplied})"
        for source in resolution.sources
    )
    return (
        '<p class="from">The Commission publishes no subjects on this authorization\'s own '
        f"rows. Its note reads &ldquo;{_e(resolution.note)}&rdquo;, and the subjects below "
        f"are the ones the table publishes for <b>{_e(resolution.credential)}</b> on document "
        f"<code>{_e(resolution.document_title)}</code>, under these authorization codes "
        f"(subjects supplied in brackets): {rows}.</p>"
    )


def _conditions_block(attachment: Attachment | None) -> str:
    """Requirements and renewal terms, quoted from the leaflet that states them."""
    if attachment is None:
        return ""
    parts: list[str] = []
    for label, sections in (
        ("Requirements", attachment.requirements),
        ("Renewal and validity", attachment.renewal),
    ):
        for section in sections:
            if not section.blocks:
                continue
            items = "".join(f"<li>{_e(block)}</li>" for block in section.blocks)
            parts.append(
                f"<details><summary>{_e(label)}: {_e(section.heading)}</summary>"
                f'<ul class="conditions">{items}</ul></details>'
            )
    unstated = attachment.variant_unstated
    if unstated is not None:
        parts.append(
            '<p class="from">This leaflet breaks its requirements out by variant and states '
            f"none under &ldquo;{_e(unstated)}&rdquo;, the qualifier the Commission publishes "
            "in this authorization's own title. Only the requirements it states for the "
            "permit as a whole are shown; matching this variant to a differently worded "
            "heading would be this project's judgement rather than the Commission's.</p>"
        )
    return "".join(parts)


def _description_block(authorization: Authorization, attachment: Attachment | None) -> str:
    """The prose, or a plain statement that the Commission published none."""
    description = description_of(authorization, attachment)
    if description:
        source = (
            f"leaflet {attachment.leaflet.code.upper()}"
            if attachment is not None and attachment.description
            else "the sort table's Notes column"
        )
        return (
            f'<p class="note">{_e(chr(10).join(description))}</p>'
            f'<p class="from">Description from {_e(source)}.</p>'
        )
    if attachment is not None and attachment.refusal is not None:
        return (
            '<p class="from">No description. The Commission\'s leaflet index links '
            f"{_e(attachment.leaflet.code.upper())} to this title, and this project did not "
            f"read that page: {_e(attachment.refusal)}</p>"
        )
    return (
        '<p class="from">No description. The Commission published no prose that applies to '
        "this authorization as a whole, and this project does not compose one.</p>"
    )


def _credential_block(
    authorization: Authorization,
    attachment: Attachment | None,
    ctid: str,
) -> str:
    parts: list[str] = ['<article class="cred">']
    parts.append(f"<h3>{_e(authorization.title)}</h3>")

    meta = [f"document <code>{_e(authorization.document_title)}</code>"]
    if authorization.authorization_code:
        meta.append(f"authorization <code>{_e(authorization.authorization_code)}</code>")
    meta.append(f"CTID <code>{_e(ctid)}</code>")
    parts.append(f'<p class="meta">{" &middot; ".join(meta)}</p>')

    parts.append(_description_block(authorization, attachment))
    parts.append(_resolution_block(authorization))

    if authorization.subjects:
        rows = "".join(
            f"<li><code>{_e(scope.code)}</code> {_e(scope.name)}</li>"
            for scope in authorization.subjects
        )
        count = len(authorization.subjects)
        noun = "subject" if count == 1 else "subjects"
        parts.append(
            f"<details><summary>{count} authorized {noun}</summary>"
            f'<ul class="subjects" role="list">{rows}</ul></details>'
        )
    elif authorization.declares_no_subject_codes:
        parts.append(
            '<p class="from">The Commission publishes <code>NONE</code> in the Subject Code '
            "column for this authorization: it is not subject-coded.</p>"
        )
    else:
        # Quoting the Commission's NONE is a claim about the source, and an empty subject
        # list is not evidence for it. Today the two coincide: `build_catalog` excludes an
        # authorization whose subjects are neither published nor reachable by
        # cross-reference, so every modeled authorization either carries subjects or carries
        # the flag, and `test_site.py` pins that. The claim was being read off the empty
        # list rather than off the flag, which meant the one branch that had to hold for the
        # sentence to be true was the one branch nothing checked.
        parts.append(
            '<p class="from">No subjects are published for this authorization, and the '
            "Commission did not publish <code>NONE</code> against it either.</p>"
        )

    conditions = _conditions_block(attachment)
    parts.append(
        conditions
        or '<p class="from">No requirements or renewal terms: none were read from a '
        "Commission leaflet for this authorization.</p>"
    )

    links = [f'<a href="{_e(SORT_TABLE_URL)}">Authorization Sort Table</a>']
    if attachment is not None:
        leaflet = attachment.leaflet
        links.append(
            f'<a href="{_e(leaflet.url)}">Leaflet {_e(leaflet.code.upper())}</a> '
            f"({_e(attachment.match.rule)}, matched against {_e(attachment.match.published_by)})"
        )
    parts.append(f'<p class="meta">{" &middot; ".join(links)}</p>')
    parts.append("</article>")
    return "".join(parts)


def _exclusions_table(catalog: Catalog) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{_e(exclusion.title)}</td>"
        f"<td><code>{_e(exclusion.document_title)}</code></td>"
        f"<td><code>{_e(exclusion.authorization_code) or '&mdash;'}</code></td>"
        f"<td>{_e(exclusion.reason)}</td>"
        "</tr>"
        for exclusion in catalog.exclusions
    )
    return (
        # tabindex makes the scroll container reachable from the keyboard: a region that
        # scrolls only under a pointer is content a keyboard-only reader cannot get to
        # (WCAG 2.1.1 Keyboard). A focusable region needs a role and a name to be worth
        # landing on, so it carries both.
        '<div class="wrap" role="region" aria-label="Authorizations not modeled" tabindex="0">'
        "<table><thead><tr>"
        '<th scope="col">Authorization</th><th scope="col">Document</th>'
        '<th scope="col">Code</th><th scope="col">Why it is not modeled</th>'
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def render(
    catalog: Catalog,
    ctids: Mapping[str, str],
    attachments: Mapping[str, Attachment],
) -> str:
    """The whole page, as one HTML document."""
    blocks: list[str] = []
    tallies = dict.fromkeys(("alignments", "leaflets", "descriptions", "conditions", "resolved"), 0)
    for authorization in catalog.authorizations:
        attachment = attachments.get(authorization.key)
        tallies["alignments"] += len(authorization.subjects)
        tallies["leaflets"] += attachment is not None
        tallies["descriptions"] += bool(description_of(authorization, attachment))
        tallies["conditions"] += bool(attachment is not None and attachment.stated_conditions)
        tallies["resolved"] += authorization.resolved_from is not None
        blocks.append(_credential_block(authorization, attachment, ctids[authorization.key]))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(TITLE)}</title>
<meta name="description" content="{_e(DESCRIPTION)}">
<link rel="canonical" href="{_e(SITE_URL)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Chalkline">
<meta property="og:url" content="{_e(SITE_URL)}">
<meta property="og:title" content="{_e(TITLE)}">
<meta property="og:description" content="{_e(DESCRIPTION)}">
<meta property="og:image" content="{_e(CARD_URL)}">
<meta property="og:image:type" content="image/png">
<meta property="og:image:width" content="{CARD_WIDTH}">
<meta property="og:image:height" content="{CARD_HEIGHT}">
<meta property="og:image:alt" content="{_e(CARD_ALT)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{_e(CARD_URL)}">
<meta name="twitter:image:alt" content="{_e(CARD_ALT)}">
<style>{STYLE}</style>
</head>
<body>
<main>
<h1>California educator credential authorizations, modeled onto CTDL</h1>
<p class="notice"><strong>{_e(DISCLAIMER_LEAD)}</strong> {_e(DISCLAIMER_BODY)}</p>
<p>Every credential below is drawn from the Commission on Teacher Credentialing's public
<a href="{_e(SORT_TABLE_URL)}">Authorization Sort Table</a>, retrieved 2026-08-07, and
projected into <a href="https://credreg.net/ctdl/handbook">CTDL</a> as a
<code>ceterms:License</code> with its authorized subjects as
<code>ceterms:CredentialAlignmentObject</code> alignments. Descriptions, requirements, and
renewal terms come from the Commission's own
<a href="https://www.ctc.ca.gov/credentials/leaflets/">credential leaflets</a>, retrieved
2026-08-07, where a leaflet's published title identifies the authorization and the leaflet
page states the code and title the index gave it. The machine-readable output is
<a href="credentials.jsonld">credentials.jsonld</a>, and the counted coverage statement is
<a href="coverage.json">coverage.json</a>.</p>
<p>Where a credential below says it has no description, no requirements, or no subject
codes, that is the state of the published source and not an omission being smoothed over.
Nothing on this page is composed by this project.</p>
{_counts_block(catalog, tallies)}
<h2>Modeled credentials</h2>
{"".join(blocks)}
<h2>Not modeled, and why</h2>
<p>An authorization is modeled only where the sort table lets its scope be read from the
table itself: as subject codes, as the Commission's published <code>NONE</code>, or through
a cross-reference that this project can follow to another credential's published rows.
These are the ones left. Their names are published and unambiguous; it is the scope that
this project cannot read, so they are recorded here rather than guessed at.</p>
{_exclusions_table(catalog)}
<footer>
<p>Chalkline is an independent demonstration by Chelsea Kelly-Reif. It is not affiliated
with, endorsed by, or published by the California Commission on Teacher Credentialing or
Credential Engine. Nothing here has been published to the Credential Registry.</p>
</footer>
</main>
</body>
</html>
"""
