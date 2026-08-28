# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- The README's prose quoted the build and nothing recomputed it. `tests/test_documented_counts.py`
  bound every numeric row of the README and PROVENANCE tables, and its own docstring opened
  "The numbers in the prose are the numbers the build produces", but the prose around those
  tables was never in scope. Eight prose figures were replaced at once with plainly wrong
  values (999 authorizations, 888 leaflets, 555 entities) and all 298 tests passed. One of
  the eight was already wrong: the Status line read "19 vendored credential leaflets extend
  22 of them with descriptions, requirements, or renewal terms", where 22 is the number of
  authorizations linked to a leaflet and 18 is the number carrying anything read from one,
  the other four being those whose leaflet page this project refuses to read on identity.
  That same sentence was hand-corrected once before, on 2026-08-21, from a figure that had
  been stale since 2026-08-08. It is now bound rather than corrected again.

### Added

- Fifteen README sentences that quote a counted figure are bound to a freshly counted
  coverage statement, in both directions. A claim whose sentence is reworded fails instead of
  silently checking nothing; a new prose figure standing beside a counted noun fails until it
  is bound or named in `NOT_A_BUILD_FIGURE` with the reason the build cannot produce it; and
  four doctored-figure controls run the claims over an altered copy of the prose so a green
  run is a statement about the figures rather than about the check being unable to fail.
  Figures spelled as English words ("Ten leaflet pages were read; eighteen authorizations
  carry prose from one") are read as figures, which is four of the leaflet totals a reader
  meets.
- `site/coverage.json` now says how much a stopped leaflet read left behind, not only that
  one stopped. `authorizations_whose_stop_left_a_classified_heading_unread` and
  `headings_left_unread_beyond_the_stop` join the two counts added alongside them. Sixteen
  attached authorizations have a leaflet whose read stopped early; exactly one of those stops
  costs nothing this project would have read, and the other fifteen lose between one and five
  headings apiece. Those two cases published identical property counts and, until now,
  identical coverage. `LeafletPage.classified_beyond_the_stop` carries the measurement, and
  the parser walks the headings past a stop without reading a word of them to take it. It is
  an upper bound on what a corrected stop rule could recover and not a claim that any of it
  was wrongly dropped: where the stop was right the headings belong to another Commission
  document. Issue #36, the judgement about which is which, stays open.

### Fixed

- `PROVENANCE.md`'s "Where reading stops" asserted that "everything past that point belongs
  to another document and is never read". The first half of that is the assumption the rule
  was written on rather than a finding about the leaflets, and issue #36 disproves it on
  three vendored pages. The section now states the rule, names what it gets wrong, and points
  at the figures that size it.

- `main` is protected. A `protect-main` ruleset requires `verify`, `audit`, `secret-scan`,
  `sast`, `zizmor` and `analyze` to pass, plus branch deletion and non-fast-forward pushes are
  refused, and `current_user_can_bypass` is `never`. Verified against a real merge, not just
  the API response: a throwaway PR (#29) carrying a deliberately failing test was refused by
  both `gh pr merge` and `mergeStateStatus` while `verify` was red, then closed unmerged.
  `.github/rulesets/main.json` (already committed 2026-08-15, per CI-CD-STANDARD §5, but not
  yet applied) is the posture now live; `.github/rulesets/README.md` records the before/after
  and the verification. Closes #22.

### Fixed

- `make verify` now runs `make audit` as its last step. Until 2026-08-21 a local `make verify`
  was green without `pip-audit` ever having run, while CI additionally required a separate
  `audit` job to pass — so `make verify` did not tell the truth about what CI required, which
  is the one thing a target named `verify` cannot afford to get wrong (issue #22).
- The README's Status line said "twelve credential leaflets" since 2026-08-08 and was never
  updated as leaflet coverage moved; it now reads 19 vendored leaflets extending 22
  authorizations, matching `site/coverage.json`.
- "private reporting channel" in two Standards Conformance rows read as "private repo" to a
  naive substring check (`portfolio-standards/automation/conformance_check.py`'s
  `stale_private_refs` control), a false positive this repository is in fact public and has
  been since 2026-08-08. Reworded to "confidential reporting channel"; the meaning is
  unchanged.

### Added

- `.github/workflows/codeql.yml`: CodeQL's `actions` language over the workflow files, and a
  `zizmor` job in `ci.yml`, a second, independently built implementation of the same
  workflow-SAST idea. Both upload SARIF to Code Scanning.
- `.standards-version` (`v2.0.0`), the vendored portfolio-standards pin DOC-01 asks for, and
  `tests/test_standards_pin.py`, which checks it names a released tag and never a branch.
- A `## Quickstart` section in the README's first 20 lines.
- `scripts/validate_evidence.py`, which runs the independently written `ctdl-validate` CLI
  (pinned `0.2.1`) as a separate process against the committed `site/credentials.jsonld` and
  writes or checks its `--format json` report at `site/ctdl-validate.json`, a fourth
  committed artifact held to the same byte-for-byte gate `chalkline check` already holds
  `credentials.jsonld` and `coverage.json` to. `make validate` now runs the `--check` form,
  and `tests/test_ctdl_validate_evidence.py` runs it again from the test suite, including a
  control test that mutates one `ceterms:ctid` into a bare UUID and asserts the validator
  catches it — so a clean report proves the graph was actually read, not merely that the
  file exists. Today: `0 findings` on all 134 entities. Closes #21.
- `.pre-commit-config.yaml`: ruff, mypy, and gitleaks as a pre-flight, run
  through `uv run --locked` so the versions are the lockfile's and cannot drift
  away from `make verify`.
- `.github/CODEOWNERS`.
- A Standards Conformance section in the README declaring all fifteen
  standards. Four rows are obligations rather than passing results and say so:
  Accessibility has no gate on the published page, Internationalization has no
  catalog or scope declaration, Performance has no measured budget, and there
  is no separate responsible-technology audit or metrics ledger document.
- A leaflet's own page title is now read as a second published title for the same document,
  and both are tried against the two title-equality rules. Nothing is loosened: it is the
  same equality applied to the other name the Commission published. `CL-902` is listed in
  the index as "The Teaching Permit for Statutory Leave (TPSL)", which matches nothing, and
  titles itself "Teaching Permit for Statutory Leave", which is exactly the named-family base
  of `Teaching Permit for Statutory Leave (Multiple Subject)` and `(Single Subject)`.
- A third attachment rule: a parenthesised run in a leaflet's published title that is,
  character for character, a whole Document Title cell in the sort table. `CL-898` names
  `MILS` that way, and the sort table publishes `MILS` as the Document Title of exactly one
  credential. A code is not a title, so this rule attaches the Commission's link and never
  any prose. The cell must match whole: `TC1, TC2` lists two documents, and a leaflet naming
  one of them says nothing about a row carrying both.
- Variant requirements. Where a leaflet matched by the named-family rule breaks its
  requirements out under a sub-heading equal to the parenthesised qualifier the Commission
  wrote in the authorization's own title, those requirements are read for that authorization
  alone. The nesting is read from the Commission's outline by heading level, so the same
  words under a validity heading are not requirements. Six authorizations gain their own
  variant's requirements. Two do not: `Short-Term Staff Permit (Special Education)` and
  `Provisional Internship Permit (Special Education)`, whose leaflets head that breakdown
  "Education Specialist:". Deciding those two phrases name the same variant would be this
  project writing the Commission's key for it, so the gap is counted in
  `leaflets.variant_qualifiers_no_heading_states` and printed on the page instead.
- Nine leaflet snapshots, retrieved 2026-08-19: `cl-501`, `cl-529`, `cl-537`, `cl-628b`,
  `cl-797`, `cl-828`, `cl-889`, `cl-898`, `cl-902`. Two are attached. The other seven were
  retrieved to read what the Commission's own page calls a document whose index title was a
  word or a plural away from an authorization's, and for all seven it was not the
  authorization's title either. They stay vendored because a recorded non-match whose
  evidence has been deleted is an assertion rather than a finding, and `PROVENANCE.md` now
  prints both titles for every snapshot. `cl-504` and `cl-568` were deliberately **not**
  retrieved: the authorizations they would describe are excluded for want of a published
  scope, so no answer could have changed the graph.
- `make validate` runs [`ctdl-validate`](https://github.com/ChelseaKR/ctdl-validate) `0.2.1`,
  an independently written CTDL structural checker, over the committed graph, and `make
  verify` depends on it. It checks a different rule family from this project's own validator
  — CTID grammar, identifier kinds, reference targets, class pairings — so neither subsumes
  the other and the interesting outcome is a disagreement. It reports `0 findings` on all 134
  entities today; rewriting one `ceterms:ctid` to a bare UUID makes it report `CTID_BARE_UUID`
  and exit 1, so the zero is being earned. It makes no network calls and the gate stays
  offline. Pinned rather than floated: a new rule in a patch release is a fact about CTDL
  worth seeing in a diff. Closes #21.
- `scripts/fetch_sources.py` waits two seconds between consecutive requests in one run.
  Nothing has ever been rate-limited; the only cost of waiting is the script's own clock.

### Fixed

- The leaflet index publishes a document code beside each title, and this project read only
  the link and its text, taking the first non-empty text for a path. The index also carries a
  redirection row for each retired document — the retired code in the code column and "CL-740
  has been replaced by CL-828." where a title would go — and prints it *above* the leaflet's
  own row. So six leaflets were published under a sentence about a document that no longer
  exists, and their real titles were never read: `cl-828` came out titled "CL-740 has been
  replaced by CL-828." rather than "General Education Limited Assignment Teaching Permit".
  A row that publishes no title is not a title. A leaflet's title is now taken from the row
  whose code column names the code its own link path names, which is an agreement between two
  published strings and therefore independent of the order the Commission prints the rows in.
  No match changes: none of the six recovered titles equals an authorization's under any
  rule. The count of 81 leaflets is now 81 leaflets with names rather than 75 with names and
  six labelled with a notice about something else, and the 8 redirection rows are counted
  separately.
- `headings_read_past_but_not_classified` counted a heading against every authorization the
  leaflet served, including the one that read it. "Single Subject:" is unclassified on
  `cl-858`'s page and is now read for the authorization titled "(Single Subject)", so
  counting it there would report a heading as passed over by the very credential that used
  it. It is now counted per authorization that actually passed over it.

### Changed

- The leaflet page parser no longer refuses a page whose title disagrees with the index. It
  still refuses a page whose `<h1>` names a different document code, which is the check that
  says the snapshot is the right file. The title question moved to `chalkline.attachment`,
  because it is not a question about the page: `cl-893` and `cl-902` both disagree with the
  index and they are opposite cases, and which one is a doubt depends on the authorization
  being matched. The rule is now "did the title the page publishes identify this
  authorization", which refuses `cl-893` on the same grounds and with the same recorded
  reason as before, and admits `cl-902`. Deciding it in the parser is why `cl-902` could not
  be read at all.
- Counted, from 18 to 22 authorizations with a leaflet; 16 to 18 carrying leaflet prose; 9 to
  10 leaflet pages read; 22 to 36 `ceterms:ConditionProfile` nodes; 51 to 53 carrying
  `ceterms:description`; 13 to 15 carrying requirements or renewal terms. The coverage
  statement gains `matched_against_a_string_published_by`,
  `authorizations_with_variant_requirements`, `variant_qualifiers_no_heading_states`,
  `leaflet_pages_vendored`, `leaflet_pages_vendored_and_attached_to_nothing` and
  `index_rows_redirecting_a_retired_document_code`. All 134 CTIDs are unchanged, byte for
  byte, and none was minted: the catalog comes from the sort table, and no leaflet rule can
  add or remove a subject.

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
