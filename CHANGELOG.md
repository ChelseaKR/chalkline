# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- The leaflet parser's "moved to another document" rule fired on headings that were still
  about the leaflet's own subject, and silently dropped real requirements and renewal terms
  from licenses already published in `site/credentials.jsonld`. Reading stopped at the first
  unclassified heading containing "credential", "permit", "certificate", "certification" or
  "authorization", which is a purely lexical test and cannot tell a second Commission
  document from an aside, an add-on or an alternate pathway. Fourteen of the nineteen
  vendored pages stopped early and twelve stopped before a heading `classify()` recognises.
  The three Speech-Language Pathology Services Credential licenses carried no
  `ceterms:requires` at all, because `cl-879` ended at "Special Class Authorization" and its
  own four "Requirements for ..." sections sat behind that; both Teaching Permit for
  Statutory Leave entries lost their period of validity to "TPSL Authorizations", which is
  an overview of what that same permit's variants authorize; `cl-562` ended at an alternate
  route to the same Teacher Librarian Services Credential; `cl-537` ended at its own title
  and published nothing at all. Issue #36.

  The Commission's own outline decides it now. A heading naming a document that has
  sub-headings under it is a second document with a structure of its own, and the page ends
  there; one with no sub-headings is a stretch of prose inside the outline being described,
  so it is set aside -- its own prose is still never read, because this module cannot say
  whose it is -- and reading resumes at the next heading. `cl-380`, the page the rule exists
  for, stops exactly where it always did: the Commission gave the Special Teaching
  Authorization in Health its own requirements section, and the "Term of the Credential"
  that page closes on reads "Qualified applicants will receive a Clear Health Services
  Credential issued for five calendar years", which is not the School Nurse Services
  Credential the leaflet is titled for. Six pages stop now.

  The repeat-heading stop was narrowed to classified headings in the same change, because
  leaflets reuse unclassified sub-headings on purpose: `cl-529` heads the out-of-state
  paragraph under each of three specializations "Out-of-State Applicants", and the second one
  ended the page one heading before its "Period Of Validity".

  The graph gains what was being dropped: `ceterms:requires` on 18 authorizations rather than
  15, `ceterms:renewal` on 12 rather than 9, and 57 `ceterms:ConditionProfile` nodes rather
  than 36. `site/`, the README and PROVENANCE.md figures are rebuilt to match, and
  `tests/test_documented_counts.py` is what caught each one that was not. The page carries
  the extra conditions too, at 1,868 bytes per authorization against 1,717: the weight budget
  is not raised for it, because a page carrying more of what the Commission published is the
  budget's formula working rather than a reason to move it.

### Added

- `LeafletPage.set_aside` and `Attachment.set_aside`, with
  `authorizations_whose_leaflet_set_a_subject_aside` and
  `headings_set_aside_as_another_subject` in `site/coverage.json`. The stop and the aside are
  two judgements of different strength and they are published separately: a wrong stop costs
  a page and a wrong aside costs a paragraph, so every set-aside heading is listed with a
  count rather than summarised, and a reader can check each call. The two stop counts fell
  from 16 and 15 to 6 and 6 with the fix above, which is less dropped rather than less
  disclosed.

- The committed ruleset was a lockout waiting to be re-applied.
  `.github/rulesets/main.json` declared `"bypass_actors": []`, and
  `.github/rulesets/README.md` documents applying it with
  `gh api repos/ChelseaKR/chalkline/rulesets -X POST --input .github/rulesets/main.json`,
  so following this repository's own instructions would have stripped the
  owner's standing bypass off live ruleset `21156701` and left her unable to
  merge, push, or delete the ruleset blocking her. GitHub answers that apply
  with 201 like any other, so nothing would have warned. The file now carries
  the one actor the live ruleset carries,
  `{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}`,
  and every other field was already equal, checked field by field against the
  API on 2026-08-29. `bypass_mode` is `always` rather than the `pull_request`
  CI-CD-STANDARD asks for at CICD-15, because a bypass that only works inside a
  pull request is no use when the pull request is the thing that is wedged. The
  ruleset README and the `ci.yml` header both said the file was stale and
  warned against re-applying it; both now say what the file carries, and the
  README keeps the reversed instruction visible rather than deleting it. The
  live posture change of 2026-08-26 is still unrecorded here, and stays the
  owner's to write.

### Added

- `tests/test_ruleset.py`, so the empty list cannot come back quietly. Nothing
  in `src/` or `tests/` read the committed ruleset before this, which is why it
  could disagree with the live one for three days. `lockout_risk()` is a pure
  function of a parsed document and is run against the five shapes that lose
  the bypass -- an empty list, no key at all, a value that is not a list, a
  different actor, and the right actor carrying `bypass_mode: pull_request` --
  plus a positive control, so a pass is a statement about the file rather than
  about a check that refuses everything. The loader fails on a missing or
  unparseable file rather than reading an absent subject as nothing wrong: a
  malformed file still contains the string `bypass_actors`, so the parse is
  what catches it and a grep would not. A last test fails if the ruleset README
  stops naming the actor the file carries, because the prose is what a person
  follows when the two disagree.

### Added

- The prose style rule is now a gate. CONTRIBUTING.md has said "No em dashes" for as long as
  it has existed and nothing checked it, so the repository held 32 of them: 16 in README.md,
  9 in CHANGELOG.md, 3 in PROVENANCE.md, 2 in `.github/dependabot.yml` and one each in a
  `sort_table` docstring and a `test_sort_table` docstring. All 32 are rewritten here without
  changing what any of them says. `make no-dashes` runs inside `make verify`, which CI runs
  byte for byte. It keeps `git grep`'s three exit statuses apart, so a gate that could not run
  fails rather than announcing success. `data/source/`, the generated `site/` and the vendored
  CTDL schema are outside it, because they are transcribed or produced rather than written:
  `data/source/leaflets/cl-562.html` does contain an em dash, and editing the Commission's own
  page would make the snapshot a paraphrase and break the sha256 PROVENANCE.md publishes for
  it. En dashes are not checked, because CONTRIBUTING.md does not ban them.

- The page says what it is, and where it is. `site/index.html` carried a title
  and nothing else: no `<meta name="description">`, no canonical, no Open Graph,
  no Twitter card. It now carries all of them, built from one `TITLE` and one
  `DESCRIPTION` constant so the share card cannot describe the page differently
  from the page. The description keeps the word "unofficial" and states no
  figure: the page counts its own tallies from the catalog at build time, and a
  number in a meta tag would be a copy nothing derives. GitHub Pages serves this
  repository at a path on an origin five sibling projects publish under, and
  `https://chelseakr.github.io/` is itself a 404, so every absolute
  self-reference carries `/chalkline/`. `tests/test_site.py` fails on a
  canonical naming the bare origin, on a description that drops "unofficial" or
  quotes a figure, and on any root-relative `href`, `src` or `content`.

### Fixed

- The README published tool floors a release behind the ones `pyproject.toml` pins. The Code
  Quality row said "ruff >= 0.16.2, mypy >= 2.3.0" while the pins read `ruff>=0.16.4` and
  `mypy>=2.3.1`. That is drift with a motor behind it: Dependabot raises the floor in
  `pyproject.toml`, the merged PR touches no prose, and the sentence describing the pins falls
  one release further behind on every bump. `tests/test_documented_counts.py` could never have
  caught it, and correctly so: its figure regex excludes version strings, dates and leaflet
  codes by design, because none of those is a count of anything the build emits. That
  exclusion is untouched. `tests/test_documented_floors.py` reads the floors out of
  `pyproject.toml` instead, which is where they come from, and holds the Python, ruff, mypy
  and complexity floors and the 97% coverage floor (stated in two README rows and in
  CONTRIBUTING.md) to what is actually pinned. It carries the same doctored-copy control the
  counts module uses, so a passing run is a statement about the floors rather than about the
  check being unable to fail.

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
- `tests/test_performance.py`. Two claims this repository made in prose and checked nowhere.
  `chalkline.site`'s docstring says "No external stylesheet, script, font, or image: the page
  is one file and works offline", and the README's Performance row said a budget was not yet
  enforced. Self-containment is now asserted against the rendered page (no script, link, img,
  iframe, object, embed, media or track element, and no `@import` or `url()` in the inline
  stylesheet), which is also what makes the Observability row's "no analytics on the published
  page, by design" checkable rather than intended. The one `<link>` the page carries, the
  `rel="canonical"` added with the head metadata, is exempt by relation rather than by
  element: `METADATA_LINK_RELS` names the relations that leave the browser nothing to fetch,
  it holds `canonical` and nothing else, `rel` is read as a token list so
  `rel="alternate stylesheet"` cannot slip past a cleared first token, a `<link>` with no
  `rel` at all is refused as undeclared rather than harmless, and a separate test asserts the
  canonical link is the only `<link>` on the page so the exemption cannot hide one the
  scanner never saw. Exempting the element would have let a stylesheet in behind it.
  The weight budget is a formula, 12,000
  bytes of fixed overhead plus 2,200 per modeled authorization against 8,102 and 1,717 today,
  so growth in the markup fails the gate and growth in the Commission's table does not; a test
  asserts both halves of that, including that twice as many authorizations at today's weight
  each would still pass. `credentials.jsonld` and `coverage.json` are deliberately not
  budgeted, with the reason recorded: they are downloads a reader chooses rather than
  page-load cost, and a cap on them would be a cap on how much of the source may be modeled.
  The README's Performance row publishes both budgets and what the page spends against them,
  and all four figures are bound to the rendered page here. The spend had already drifted:
  the row said 7,006 bytes of fixed overhead when the head metadata added with the canonical
  link had taken it to 7,896, and the accessibility fixes have since taken it to 8,102, which
  this check is what noticed. `tests/test_documented_counts.py` binds the README's prose
  figures to the coverage statement but only where one stands beside a counted noun, and
  "bytes" is not one of them, so these two figures sat outside every check the repository
  had.
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

- Three accessibility defects in the generated page, found by the review the README's
  Accessibility row had been recording as not yet performed. The exclusions table's four
  `<th>` cells carried no `scope`, so nothing said whether they head a column or a row
  (technique H63, for WCAG 1.3.1). `.counts` and `.subjects` are styled `list-style: none`,
  and Safari drops list semantics from a list whose markers are removed, so 134 list items
  were no longer announced as lists; `role="list"` restores what the styling took away.
  `.wrap`, the one horizontally scrolling region on the page, could not be focused, so a
  keyboard-only reader could not scroll the exclusions table at all (WCAG 2.1.1); it now
  carries `tabindex="0"`, a region role, an accessible name, and a visible focus ring.

### Added

- `tests/test_accessibility.py`, an accessibility gate over the rendered page: page language,
  page title, heading order, table header scope, list semantics under removed markers,
  keyboard reach into scrolling regions, image alternatives, zoom not being pinned, and text
  contrast across both palettes. It is a check against a named list, not an audit, and it
  says so. Every check records how much it examined, so a check that ran over nothing is
  distinguishable from one that ran over everything and found nothing, and every check is
  exercised against a deliberately broken copy of the real page. A check with no such
  breakage fails the suite, which is what stops the list growing by accretion of things that
  cannot disagree with the page.

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
  `audit` job to pass, so `make verify` did not tell the truth about what CI required, which
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
  catches it, so a clean report proves the graph was actually read, not merely that the
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
  (CTID grammar, identifier kinds, reference targets, class pairings), so neither subsumes
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
  redirection row for each retired document (the retired code in the code column and "CL-740
  has been replaced by CL-828." where a title would go) and prints it *above* the leaflet's
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
  the parser's structural refusals (one `<table>`, at least one `<tr>`, the expected
  headers, full-width rows), so nothing objected, and the empty read propagated as fact:
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
  a successful run and exiting 0, with none of the committed CTIDs surviving: the one thing
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
