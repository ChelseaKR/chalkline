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

from chalkline.ctdl.export import DISCLAIMER_BODY, DISCLAIMER_LEAD
from chalkline.model import Authorization, Catalog
from chalkline.sources import leaflets as leaflets_module
from chalkline.sources.sort_table import SOURCE_URL as SORT_TABLE_URL

TITLE: Final = "Chalkline: California educator credential authorizations as CTDL"

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
.note { color: var(--muted); font-size: 0.9rem; margin: 0.4rem 0; white-space: pre-line; }
details { margin-top: 0.5rem; font-size: 0.9rem; }
summary { cursor: pointer; color: var(--muted); }
.subjects { margin: 0.6rem 0 0; padding: 0; list-style: none;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr)); gap: 0.3rem; }
.subjects li { border-left: 2px solid var(--rule); padding-left: 0.6rem; font-size: 0.88rem; }
.subjects code { color: var(--muted); }
.wrap { overflow-x: auto; }
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


def _counts_block(catalog: Catalog, alignments: int, with_leaflet: int) -> str:
    published = len(catalog.authorizations) + len(catalog.exclusions)
    items = [
        (catalog.source_rows, "rows published in the sort table"),
        (published, "authorizations in those rows"),
        (len(catalog.authorizations), "modeled as ceterms:License"),
        (len(catalog.exclusions), "excluded, with reasons below"),
        (alignments, "subject alignments emitted"),
        (with_leaflet, "linked to a CTC leaflet"),
    ]
    cells = "".join(f"<li><b>{value}</b><span>{_e(label)}</span></li>" for value, label in items)
    return f'<ul class="counts">{cells}</ul>'


def _credential_block(
    authorization: Authorization,
    leaflet: leaflets_module.Leaflet | None,
    ctid: str,
) -> str:
    parts: list[str] = ['<article class="cred">']
    parts.append(f"<h3>{_e(authorization.title)}</h3>")

    meta = [f"document <code>{_e(authorization.document_title)}</code>"]
    if authorization.authorization_code:
        meta.append(f"authorization <code>{_e(authorization.authorization_code)}</code>")
    meta.append(f"CTID <code>{_e(ctid)}</code>")
    parts.append(f'<p class="meta">{" &middot; ".join(meta)}</p>')

    if authorization.shared_notes:
        parts.append(f'<p class="note">{_e(chr(10).join(authorization.shared_notes))}</p>')

    if authorization.subjects:
        rows = "".join(
            f"<li><code>{_e(scope.code)}</code> {_e(scope.name)}</li>"
            for scope in authorization.subjects
        )
        count = len(authorization.subjects)
        noun = "subject" if count == 1 else "subjects"
        parts.append(
            f"<details><summary>{count} authorized {noun}</summary>"
            f'<ul class="subjects">{rows}</ul></details>'
        )
    else:
        parts.append(
            '<p class="note">The Commission publishes <code>NONE</code> in the Subject Code '
            "column for this authorization: it is not subject-coded.</p>"
        )

    links = [f'<a href="{_e(SORT_TABLE_URL)}">Authorization Sort Table</a>']
    if leaflet is not None:
        links.append(f'<a href="{_e(leaflet.url)}">Leaflet {_e(leaflet.code.upper())}</a>')
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
        '<div class="wrap"><table><thead><tr><th>Authorization</th><th>Document</th>'
        "<th>Code</th><th>Why it is not modeled</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def render(
    catalog: Catalog,
    ctids: Mapping[str, str],
    leaflet_index: Mapping[str, leaflets_module.Leaflet],
) -> str:
    """The whole page, as one HTML document."""
    blocks: list[str] = []
    alignments = 0
    with_leaflet = 0
    for authorization in catalog.authorizations:
        leaflet = leaflet_index.get(leaflets_module.normalize_title(authorization.title))
        alignments += len(authorization.subjects)
        with_leaflet += 1 if leaflet is not None else 0
        blocks.append(_credential_block(authorization, leaflet, ctids[authorization.key]))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(TITLE)}</title>
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
<code>ceterms:CredentialAlignmentObject</code> alignments. The machine-readable output is
<a href="credentials.jsonld">credentials.jsonld</a>, and the counted coverage statement is
<a href="coverage.json">coverage.json</a>.</p>
{_counts_block(catalog, alignments, with_leaflet)}
<h2>Modeled credentials</h2>
{"".join(blocks)}
<h2>Not modeled, and why</h2>
<p>An authorization is modeled only where the sort table lets its scope be read from the
table itself, either as subject codes or as the Commission's published
<code>NONE</code>. These are the authorizations whose scope the table points to somewhere
else. Their names are published and unambiguous; it is the scope that this project has not
verified, so they are recorded here rather than guessed at.</p>
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
