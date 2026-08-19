# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- `chalkline.sources.sort_table.load` returned `()` for an artifact that kept the
  Commission's six headers and lost every row under them. That page satisfies all four of
  the parser's structural refusals — one `<table>`, at least one `<tr>`, the expected
  headers, full-width rows — so nothing objected, and the empty read propagated as fact:
  a catalog of nothing, a graph holding the Commission and no licences, a `validate.check`
  that passed because that graph is not empty, a coverage statement counting zero of
  everything, a page of nine zeroed tiles, and `chalkline build` printing
  "0 authorizations modeled, 0 excluded" and exiting 0. This is the same refusal
  `leaflets.load` was given, on the same grounds, at the same boundary: `parse` still
  returns `()` for a fragment that genuinely holds no rows, and the artifact loader refuses.
  The `leaflets.load` docstring's claim that `sort_table.load` "has always refused its
  artifact on the same grounds" was true of every way that page could stop parsing and false
  of the one way it could stop having rows; it is now true as written.
- `chalkline.ctid.load_ledger` read a ledger file holding no `ctids` mapping as `{}`, which
  is what it also returns when there is no ledger file at all. The two are not the same
  state, and the difference is what the empty mapping is then used for: `mint_missing` finds
  every key unassigned, mints a fresh UUIDv4 for each, and `save_ledger` writes the result
  over the file. A `ctids` key renamed, dropped in a merge, or truncated away would
  therefore have been repaired by re-minting all 134 identifiers, reporting the new count as
  a successful run and exiting 0, with none of the committed CTIDs surviving — the one thing
  the module's own docstring says cannot happen. A missing file still reads as empty, an
  explicit `"ctids": {}` is still an allowed statement that nothing has been assigned, and
  a file that cannot be read now stops the run. A non-string assignment is reported as a
  value that is not a CTID rather than raising `TypeError` from inside `re`.
- The page printed "The Commission publishes `NONE` in the Subject Code column for this
  authorization" whenever an authorization had no subjects, reading a claim about the source
  off an empty list rather than off `declares_no_subject_codes`, the field that records it.
  The two coincide on the vendored artifact because `build_catalog` excludes an
  authorization whose subjects are neither published nor reachable by cross-reference, so
  the published page never carried a wrong sentence and its bytes do not change here. That
  invariant held across three code paths and nothing asserted it, which is why reading the
  wrong variable was invisible; it is now stated as a test over the real catalog, and the
  third case prints what is actually true of it.

- The CTDL validator accepted any string where a property's range admits a CTDL class. A
  string there is a reference to such a node, which is what the module docstring already
  claimed, but nothing enforced it: an organization's name sat in `ceterms:ownedBy` as
  happily as its IRI. Strings in that position must now be an absolute IRI or a blank node.
  Only the accepting half of the rule had a test, which is why the gap survived; both halves
  have one now.
- Four of the ten leaflet sha256 abbreviations in `PROVENANCE.md` had the wrong tail
  (`cl-812`, `cl-824`, `cl-879`, `cl-909`). The prefixes and byte counts were right, so the
  rows looked correct; the suffixes belonged to no file in the repository.
- `docs/IDENTIFIERS.md` claimed under "Counted, not asserted" that no emitted value other
  than `@id` uses the unresolved host. `ceterms:ownedBy` uses it on all 133 licences, so the
  host appears 267 times rather than 134.
- `docs/MODELING.md` still said the class is uniform across "125 modeled authorizations";
  cross-reference resolution took that to 133, as the same document says twice elsewhere.
- `README.md` said near misses and stopping headings are counted in `site/coverage.json`.
  The coverage statement counts headings read past without being classified, and refusals
  with their reasons; the other two are named in `PROVENANCE.md` only.
- `README.md` said "Every target runs `uv run --locked`". The targets that run a tool do;
  `install`, `lock`, and `lock-check` are `uv` invocations in their own right.
- The validator passed a language map with no language tags and any property present with
  an empty list. `all()` over no entries and `for` over no items are both true of nothing,
  so `ceterms:name: {}` on every licence validated clean: a graph in which no credential has
  a name would have shipped. Both shapes are findings now.
- `chalkline.sources.leaflets.load` returned `()` when the index linked no leaflet pages,
  where `sort_table.load` refuses. `_LINK_RE` needs a path-relative href, so a CMS switching
  to absolute URLs was enough to make the whole build succeed with no leaflets at all:
  nothing attached, descriptions and conditions left the graph, and the coverage statement
  published the smaller figures as fact with every gate green. `parse` still returns `()`
  for markup that genuinely lists none; the artifact loader is what refuses.
- `tests/test_cli.py::test_mint_is_a_no_op_once_the_ledger_is_complete` passed `None` to
  `cli.mint_ctids`, which resolves to `data/ctid-ledger.json` and saves in place. With any
  key missing, running pytest minted a fresh UUIDv4 into a tracked artifact, which is the
  one thing `chalkline.ctid` says cannot happen as a side effect. It now runs against a copy,
  and a second test states the real invariant without writing anything.
- The networking scan behind "no module in this package opens a socket" listed only HTTP
  clients, so `subprocess.run(["curl", ...])` passed it. `subprocess`, `asyncio`,
  `webbrowser`, `smtplib` and the rest are in the vocabulary now.
- `tests/test_documented_counts.py` captured figures as `[\d,]+`, so a row it could not read
  was not returned at all: a README figure written `~9,999` disappeared from the comparison
  rather than failing it. Values are read as written and a non-numeric one is now a failure.
- Two guards against a check that passes having measured nothing: the vendored-leaflet test
  counts how many snapshots reached its assertions (nine; the refusal branch `continue`s, so
  a parser refusing all ten used to look identical to one reading all ten), and the scope
  statement test requires the recorded quote to be non-empty (`"" in anything` is true, and
  the sidecars are the one artifact class the hash test does not cover).

### Removed

- `chalkline.ctdl.export.write` and `ExportReport`. Nothing called them: the CLI builds
  through `cli._artifacts`, and `write` was a second copy of the validate-then-count-then-
  write sequence that emitted only the two JSON files and not the page, so anything that had
  used it would have produced an incomplete `site/`. Its one caller was the test that
  covered it, which is the arrangement that lets a duplicate path drift out of step with the
  real one while the coverage figure reports it exercised.

### Added

- `tests/test_provenance.py` binds both `PROVENANCE.md` sources tables to the bytes on disk:
  every abbreviated sha256 is recomputed and every byte count re-counted, and the set of
  tabulated artifacts must equal the set of vendored ones, so a row cannot be dropped to
  make the check pass. The sidecars were already bound to the bytes; the document a reader
  opens was not, which is where the four wrong hashes lived.
- Cross-reference resolution in the domain model. The eight authorizations whose Subject Code
  column is empty and whose Notes defer to another credential are now resolved by following
  that reference row by row against the vendored table. Modeled authorizations go from 125 to
  133, exclusions from 11 to 3, and subject alignments from 476 to 1,014. Each resolution
  records the note, the credential it names, and the referenced Authorization Codes with the
  number of subjects each supplied.
- Leaflet page source (`chalkline.sources.leaflet_pages`) reading the Commission's leaflets as
  the web pages they are served as, and refusing any page whose own heading does not state the
  code and title the Commission's index gave it.
- Attachment policy (`chalkline.attachment`) deciding which leaflet describes which
  authorization and what may be read from it, with every refusal recorded.
- A second leaflet matching rule: an authorization title that is a leaflet title plus one
  trailing parenthesised qualifier. Six more authorizations matched, 18 in total.
- `ceterms:requires` and `ceterms:renewal` as `ceterms:ConditionProfile` nodes built from
  leaflet sections, on 13 and 7 licenses respectively; 22 condition profiles in all.
- `ceterms:description` from leaflet prose where a leaflet was read, outranking the sort
  table's Notes column. Descriptions go from 37 to 51.
- Ten vendored leaflet snapshots under `data/source/leaflets/`, each with a provenance
  sidecar, plus tests asserting they are exactly the leaflets the matcher asks for and that
  each is one the Commission's index publishes.
- `scripts/fetch_sources.py leaflets <code>…` for retrieving named leaflet pages.
- `docs/IDENTIFIERS.md`: what CTDL and linked-data practice expect of an `@id`, what the
  unresolved `chalkline.chelseakr.com` host costs, the options, and a recommendation. Nothing
  registered, deployed, or published.

- California educator credential authorizations modeled onto CTDL, the first milestone.
- Parsers for the Commission on Teacher Credentialing's Authorization Sort Table and
  credential leaflet index, over vendored snapshots retrieved 2026-08-07 with recorded URLs,
  dates, byte counts, and sha256 hashes.
- Domain model grouping the table's 553 rows into 136 authorizations, of which 125 are
  modeled and 11 are excluded with per-item recorded reasons.
- CTDL export producing one `ceterms:License` per authorization, one
  `ceterms:CredentialOrganization` for the Commission, and 476
  `ceterms:CredentialAlignmentObject` subject alignments.
- Structural validator checking every emitted document against the vendored CTDL schema
  encoding: class existence, property existence, `schema:domainIncludes` pairing, and range
  shape.
- Spec-conformant CTIDs (`ce-` plus a standard UUIDv4) minted once and committed to
  `data/ctid-ledger.json`, with the export refusing to mint during a build.
- Coverage statement recomputed from the emitted graph at build time, which refuses to
  publish a figure the export contradicts.
- Self-contained browsable page listing every modeled credential with links to its source
  leaflet where one matched, and every exclusion with its reason.
- `chalkline check`, which fails when the committed `site/` is not byte-for-byte what the
  code produces from the current sources.
- `PROVENANCE.md` and `docs/MODELING.md` documenting every source, exclusion, class choice,
  and rejected alternative.

### Changed

- The validator accepts a list of strings under a language tag, which is what JSON-LD's
  `@container: @language` allows and what `ceterms:condition` needs in order to state several
  conditions. An empty list is still rejected.
- The coverage statement counts condition profiles, resolved scopes, which rule matched each
  leaflet, how many leaflet pages were read and refused, and every leaflet heading that
  reading skipped.
- The browsable page shows descriptions, requirements, and renewal terms where present, names
  where each description came from, prints the cross-reference behind every resolved scope,
  and states plainly where a description or a condition is absent.
- Every `uv run` in the Makefile is now `uv run --locked`, and `make install` is
  `uv sync --locked`. Regenerating the lockfile is `make lock`, and nothing else does it.
- Dependabot's Python updates move from the `pip` ecosystem to `uv`, so that a dependency
  change arrives as a manifest edit and a lockfile edit in the same pull request.

### Fixed

- `uv.lock` recorded dependency specifiers that `pyproject.toml` no longer stated
  (`pip-audit>=2.7`, `pytest>=8.0`, `pytest-cov>=5.0`, `pytest-xdist>=3.6` and
  `ruff>=0.15.0`, against a manifest asking for `>=2.10.1`, `>=9.1.1`, `>=7.1.0`, `>=3.8.0`
  and `>=0.16.1`). `uv lock --check` exited 1 on `main` while all four CI jobs were green,
  because a bare `uv run` repairs the lockfile in place before running anything and never
  reports that it did. `make verify` now runs `lock-check` first, so a lockfile that
  disagrees with the manifest fails the gate instead of being quietly rewritten by it. No
  resolved package version changed; only the five specifier lines the lockfile records.
