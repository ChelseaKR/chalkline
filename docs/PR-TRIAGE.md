# Pull request triage, 2026-08-28

Eight open pull requests, one open issue, all eight PRs based on `main`. Nothing is stacked
and no merge would auto-close another PR.

Every claim below is marked **verified** (re-derived here from the repository, the GitHub
API, or the CI logs) or **on trust** (taken from a PR description without re-running it).
No test suite was run for this triage.

## The two things that decide the order

**`protect-main` is strict.** `strict_required_status_checks_policy: true`, so every branch
must be up to date with `main` before it merges. Every merge below puts every other open PR
into `BEHIND` and forces an update plus a full re-run of `verify`, `audit`, `secret-scan`,
`sast`, `zizmor` and `analyze`. Order matters for cost as well as for correctness.
(Verified: `gh api repos/ChelseaKR/chalkline/rulesets/21156701`.)

**#39 moves the numbers #40 writes into the README.** `site/index.html` on `main` today is
7,006 bytes of fixed overhead and 1,711.4 bytes per authorization, which is exactly what
#40's new Performance row states. After #39 those become 7,212 and 1,717.5. Both stay well
inside #40's budget, so **no gate fails**: the README simply becomes wrong and stays wrong.
`tests/test_documented_counts.py` cannot catch it, because `prose()` drops every line
starting with `|` and `TABLES` binds only the README's "What this is" table and PROVENANCE's
"What is counted" table. The Standards Conformance table is bound by neither. (Verified: both
page variants measured directly from the committed `site/index.html` on each branch.)

## Per pull request

### #41 coverage: say how much a stopped leaflet read left behind (base `main`)

Adds `LeafletPage.classified_beyond_the_stop` and `Attachment.classified_beyond_the_stop`,
two new `site/coverage.json` keys sizing what a truncated leaflet read left unread, and a
correction to PROVENANCE's "Where reading stops". Refactors `_sections()` to walk headings
past the stop without reading them.

- **Correctness: good.** The `_sections()` rewrite is behaviour preserving. The old code set
  `stopped_at` then `break`, then closed the open section after the loop; the new code closes
  the open section immediately before the stop test and skips the tail close when a stop
  happened. Same sections, same order. That `credentials.jsonld` and `index.html` are
  unchanged on the branch is independent evidence, since `chalkline check` compares them
  byte for byte. (Verified by reading the diff and the branch's file list.)
- The new tests cannot pass on `main`: they reference attributes that do not exist there.
  The specific list of ten failures in the PR body is **on trust**.
- Figures are internally consistent: 15 authorizations losing something, 38 headings in
  `headings_left_unread_beyond_the_stop`, one of sixteen stops losing nothing. (Verified by
  summing the committed `coverage.json` diff.)
- **Defect, invisible in the diff.** The `### Fixed` heading this PR opens lands directly
  above PR #30's `- main is protected` bullet, which is an **Added** entry. After the merge
  that bullet is filed under Fixed. The hunk applies cleanly and every gate passes.
  (Verified by reconstructing the merged region from the branch's `CHANGELOG.md`.)
- Overlaps: `CHANGELOG.md` conflicts with #39 and #40. No source overlap with either. Does
  not touch `site/index.html`, so it cannot disturb #39's or #40's page checks.
- Real merge state: `CLEAN`, up to date with `main`, all eight checks `SUCCESS`.
- **Recommendation: merge after changelog reposition.** Move the new `### Fixed` block so it
  does not capture a foreign Added bullet, or file the PROVENANCE bullet under the existing
  `### Fixed` at the top of `[Unreleased]`.

### #40 perf: gate the page's self-containment and its weight (base `main`)

Adds `tests/test_performance.py` (13 tests): no subresource element and no `@import` or
`url()` in the inline stylesheet, relative links resolve, and a weight budget expressed as
12,000 bytes of fixed overhead plus 2,200 per modeled authorization. Rewrites the README's
Observability and Performance rows.

- **Correctness: the gate is sound**, and the PR is honest that it found no defect and that
  its tests pass unmodified against `main`. That is legitimate for a regression gate, but it
  means nothing here fails without the change.
- **Defect: four figures nothing recomputes.** The new Performance row says "Today the page
  spends 7,006 and 1,711", and `test_performance.py`'s two budget docstrings repeat them.
  They are correct today and become wrong the moment #39 lands, with no test to notice. This
  is the class of defect #38 was written to close, landing in the one region of the README
  that #38's scan does not reach. CONTRIBUTING rule 5: "Do not write a total into prose that
  nothing recomputes."
- Minor: in `test_a_heavier_page_is_caught`, `spent * 2 / (modeled * 2)` reduces to
  `spent / modeled`, which the budget assertion already makes. That half of the test restates
  the current state rather than proving the budget tolerates a larger table.
- Minor: `SUBRESOURCE_TAGS` lists `link` unqualified, so a future `<link rel="canonical">`
  would read as a fetched subresource. The docstring justifies the unqualified `script` but
  not the unqualified `link`.
- Overlaps: `CHANGELOG.md` and `README.md` both conflict with #39. #39's added markup does
  not threaten the budget (7,212 and 1,717.5 against 12,000 and 2,200).
- Real merge state: `CLEAN`, up to date with `main`, all eight checks `SUCCESS`.
- **Recommendation: merge after rebase, last of the three**, with the two page figures
  recomputed against the post-#39 page (7,212 and 1,718) or dropped from the row.

### #39 a11y: review the published page, fix what it found, and gate it (base `main`)

Three accessibility fixes to the generated page (`scope="col"` on four `<th>`, `role="list"`
on the counts list and 67 subject lists, and `tabindex="0"` plus a region role, an accessible
name and a focus ring on the one horizontally scrolling container), the rebuilt
`site/index.html`, and a 16-test gate over nine named conditions.

- **Correctness of the code: good.** The `site.py` changes are minimal and right, and the
  rebuilt page carries exactly 68 `role="list"`, 4 `scope="col"`, and one focusable region.
  (Verified by counting both committed pages.) The gate's design is strong: it asserts how
  much each check examined, and `test_every_check_is_covered_by_a_breakage` refuses a check
  with nothing proving it can fail.
- **Defect: a wrong count in the CHANGELOG.** It says the removed markers meant "134 list
  items were no longer announced as lists". The affected lists hold **1,023** `<li>`: 9 in
  `ul.counts` and 1,014 in `ul.subjects`, across 68 lists. 134 is the entity count (133
  licenses plus the Commission), the wrong denominator entirely. In a repository whose
  CONTRIBUTING rule 5 is "Counts are counted", and one merge after #38 fixed exactly this
  class of error, this should not land. (Verified by counting the committed page.)
- **Defect, invisible in the diff.** The bullet describing "Three accessibility defects ...
  found and fixed" is inserted under the `### Added` heading that PR #38 opened, with no
  `### Fixed` heading of its own. A fix is filed as an addition. (Verified by reconstructing
  the merged region.) The separate `### Added` heading it opens afterwards is correctly
  placed and leaves #30's bullet classified as before.
- Overlaps: `CHANGELOG.md` and `README.md` conflict with #40. Changes `site/index.html`, and
  therefore invalidates #40's stated page figures.
- Real merge state: `CLEAN`, up to date with `main`, all eight checks `SUCCESS`.
- **Recommendation: needs work.** Correct "134 list items" to 1,023 items across 68 lists,
  and give the fix bullet a `### Fixed` heading. Then merge, before #40.

### #35 codeql-action/init 4.37.4 to 4.37.7, and #32 codeql-action/analyze 4.37.4 to 4.37.7 (base `main`)

Dependabot split one action's version bump into two pull requests, one per subaction. Each
therefore pins `init` and `analyze` to different versions, and `codeql-action` refuses that.

- **Genuinely failed, and mirror images of each other.** From the job logs:
  - #35 (`init` bumped, `analyze` left behind):
    `Loaded a configuration file for version '4.37.7', but running version '4.37.4'`
  - #32 (`analyze` bumped, `init` left behind):
    `Loaded a configuration file for version '4.37.4', but running version '4.37.7'`
  (Verified: `gh api .../actions/jobs/{96962504607,96962353766}/logs`.)
- **Not billing starvation.** Both jobs ran 8 steps over roughly 24 seconds and carry a real
  error annotation from the `analyze` step. (Verified against the jobs API.)
- Neither can merge alone. `analyze` is a required context, so the ruleset refuses both; and
  merging either one anyway would leave `main` red.
- The other four checks are green on both, and `.github/` has not changed since their base
  commit, so those greens are still representative.
- **Recommendation: fold both SHAs into one branch, merge that, and close the other as
  superseded.** Both edits are adjacent lines in `.github/workflows/codeql.yml`, so this is a
  one line addition to whichever branch is kept.

### #34 astral-sh/setup-uv 9.0.0 to 10.0.1 (base `main`)

Four occurrences: three in `ci.yml`, one in `pages.yml`.

- All eight checks green, and `.github/`, `Makefile` and `pyproject.toml` are byte identical
  between its base (`5c3bfa0`) and current `main`, so the green still describes the change.
  (Verified: `git diff --stat 5c3bfa0 origin/main -- .github/ Makefile pyproject.toml` is
  empty.)
- **Absent is not green.** `pages.yml` triggers only on `push` to `main` and
  `workflow_dispatch`, never on `pull_request`, so the fourth edit has never been exercised
  by any run. `publish-site` is also not a required check, so a break there lands on `main`
  silently. Mitigating: the `setup-uv` block in `pages.yml` is input for input identical to
  the three in `ci.yml` that did run green. (Verified by reading both files and the
  `pages.yml` run history.)
- **Recommendation: merge after rebase**, then watch the first `publish-site` run on `main`.

### #33 zizmorcore/zizmor-action 0.5.7 to 0.6.2 (base `main`)

One line in `ci.yml`. The `zizmor` job is green, and no workflow file has changed since the
base commit, so the result is current. Lowest risk of the eight.

- **Recommendation: merge after rebase.**

### #31 ruff 0.16.2 to 0.16.3 (base `main`)

`pyproject.toml` floor plus the `uv.lock` entry. Dependabot's `uv` ecosystem produced both
files, which is what `dependabot.yml` asks it to confirm.

- **Its green is stale, and this is the one dependabot PR where that matters.** It ran on
  2026-08-22 against `5c3bfa0`. Since then #37 and #38 added roughly 460 lines of test code,
  including 377 in `tests/test_documented_counts.py`. Ruff 0.16.3 has never linted those
  files. A new or changed rule in the patch release would surface only on re-run. (Verified:
  `git diff --stat 5c3bfa0 origin/main`.)
- Leaves the README's Code Quality row saying "ruff >= 0.16.2" while `pyproject.toml` says
  0.16.3. Nothing fails: it is a table row, so `prose()` skips it, and `_FIGURE_TOKEN`
  excludes dotted version strings anyway.
- **Recommendation: merge after rebase**, re-running `verify` against current `main`, and
  update the README floor in the same change.

## Issue #36 (leaflet stop rule) stays open

#41 references it, explicitly declines to close it, and posts evidence that the fix the issue
proposes would not stop at `cl-380`, the single case the stop rule was written for: "Special
Teaching Authorization in Health" appears nowhere in the sort table or the leaflet index, so
an equality grounded rule would read straight past it and attach that document's requirements
to the School Nurse Services Credential. #41 publishes the size of the gap and leaves the
judgement open, which is the right split. (Evidence taken **on trust** from the PR body; the
`coverage.json` figure that sizes it is verified.)

## Safe order of operations

Each step below makes every later branch `BEHIND` and forces an update and a full re-run.

1. **#33** (zizmor-action). One line, no interaction with anything.
2. **#34** (setup-uv). No interaction. Confirm the first `publish-site` run on `main` after
   it lands, because its `pages.yml` edit was never exercised on a PR.
3. **#35 with #32 folded in** (codeql-action). Must move as one commit, or `main` goes red.
   Close whichever PR is not used as superseded by the other.
4. **#31** (ruff). After the action bumps, so its re-run happens against current `main` with
   the new test files present. Update the README's "ruff >= 0.16.2" floor in the same change.
5. **#41** (coverage). First of the three feature PRs, because it touches neither
   `site/index.html` nor `README.md` and so cannot invalidate the other two.
   **Changelog reposition required** before merge.
6. **#39** (a11y). **Before #40**, because it changes the page and therefore the page weight
   figures #40 writes into the README. **Needs work first:** correct "134 list items" to
   1,023 across 68 lists, and file the fix bullet under `### Fixed`.
7. **#40** (perf). Last. **Regeneration step:** recompute the Performance row's "7,006 and
   1,711" against the post-#39 page (7,212 and 1,718), and the same two figures in
   `test_performance.py`'s `FIXED_OVERHEAD_BUDGET` and `PER_AUTHORIZATION_BUDGET`
   docstrings. Resolve the README conflict by keeping #40's Observability and Performance
   rows alongside #39's Accessibility row; the three rows are adjacent lines and independent.

No identifier renumbering is needed: no ADR, migration, or rule identifier is added by any
open PR, and `CHANGELOG.md` has no released section, so no hunk can land inside one. The
changelog hazard here is the neighbouring one described under #39 and #41: a heading inserted
next to a bullet it does not own.

## Defects on `main` that no open pull request addresses

Both are described in the handover notes and fixed in the working tree separately from this
triage.

1. **The committed ruleset no longer matches the live one.** `.github/rulesets/main.json`
   declares `"bypass_actors": []`, and `.github/rulesets/README.md`, the `ci.yml` header and
   `CHANGELOG.md` all state `current_user_can_bypass: never`, the header adding "not even an
   administrator can override it". The live ruleset carries a `RepositoryRole` bypass actor
   with `bypass_mode: "always"` and reports `current_user_can_bypass: "always"`, and its
   `updated_at` is 2026-08-26, five days after it was created. The `ci.yml` header records
   that this same claim was wrong twice before.
2. **Dependabot has no `groups:` configuration**, which is why one `codeql-action` bump
   arrived as #32 and #35, two PRs that cannot pass individually and deadlock each other.

Observed but not fixed: CONTRIBUTING says "No em dashes", `make verify` does not check for
them, and the README's Standards Conformance table uses them throughout. Correcting that
would collide with both #39 and #40.
