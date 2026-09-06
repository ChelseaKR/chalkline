# Responsible-technology audit

Dated 2026-09-05. Written against version `0.1.0`, which has never been released, and the
portfolio standards pinned in `.standards-version`. The frame and the audit letters come from
`RESPONSIBLE-TECH-FRAMEWORK.md` in that standards set; the numeric thresholds it defers to
are cited here rather than restated, because a threshold copied into a second file is a
threshold that can drift out of agreement with the one that is enforced.

**Unofficial.** Chalkline is not affiliated with, endorsed by, or published by the California
Commission on Teacher Credentialing or by Credential Engine. Nothing here has been published
to the Credential Registry, in production or in a sandbox, and the CTIDs in this repository
are not Registry-assigned.

## Why this document exists, and what was already true without it

The substance of it was already in three places. The unofficial status, the refusal to
publish to the Credential Registry, and the refusal to circumvent bot protection or access
controls are stated at the top of `README.md`, in `SECURITY.md` under "What this project will
not do", and on the generated page itself, where `export.DISCLAIMER_LEAD` and
`export.DISCLAIMER_BODY` render as the first thing under the heading and ride the JSON-LD as
its `comment` and the coverage statement as its `note`. `PROVENANCE.md` records every source,
every exclusion with its reason, and every property deliberately not emitted.

What was missing was the document that collects them, decides each audit letter applies or
does not, and names who is carrying the residual risk. The README's conformance row said so
in as many words. This is that document; the row now cites it.

## What this project is, and who is downstream of it

The Commission publishes its credential authorizations as an HTML table and its credential
leaflets as web pages. This repository models what that table publishes as CTDL JSON-LD and
publishes the result as a static page and two files. It is one worked example of a
representation that does not exist yet, built from what the Commission already publishes.

Four groups are downstream of it, and only one of them is a user:

- **A developer or standards reader** evaluating whether CTDL can carry California educator
  credentials. This is the intended audience and the one the page is written for.
- **The educators and credential candidates the authorizations describe.** They are not
  users, they are not in the data as individuals, and no record here is about a person. They
  are still downstream, because a wrong or stale claim about what an authorization permits is
  a claim about what they may be assigned to teach.
- **The Commission**, whose publications are the entire input and whose name this project
  must be careful never to borrow.
- **Credential Engine and the Credential Registry**, whose identifier space this project
  models against and deliberately does not write to.

## A. Ethics and responsibility

**Applies.**

**What could go wrong.** The worst plausible failure is not a bug. It is this project working
exactly as intended and being mistaken for the Commission's own publication: a district
assignment or a hiring decision made against this graph rather than against the Commission's
page, on a credential whose authorizations changed after the retrieval date, or on one of the
authorizations this project excludes. A second failure is quieter: the graph is complete
enough to look complete, and a reader takes the authorizations that are absent as
authorizations that do not exist.

**How it is tested for.**

- Every emitted artifact carries the disclaimer. `tests/test_export.py` asserts the JSON-LD
  document's `comment` opens with `DISCLAIMER_LEAD`; the same string pair renders on the page
  and rides `coverage.json` as its `note`, so a reader who arrives at any one of the three
  files without the other two still gets the statement.
- Every modeled authorization on the page links back to the Commission's own Authorization
  Sort Table, and to its leaflet where one is attached, so the source is one click away from
  the claim.
- The exclusions are published rather than dropped. `site/index.html` carries a table headed
  "Not modeled, and why", `PROVENANCE.md` records each reason, and `site/coverage.json`
  counts them from the emitted graph at build time.

**What this project commits to.** These are refusals, in the order they are most likely to be
proposed as improvements:

- **Nothing is published to the Credential Registry.** Not production, not sandbox, not one
  test record. `CONTRIBUTING.md` rule 1 states it and `SECURITY.md` repeats it as a change
  that will be declined.
- **No source is accessed around a control that declined it.** `scripts/fetch_sources.py`
  stops on an HTTP error, and `CONTRIBUTING.md` rule 4 forbids adding retries with different
  headers or user agents. The Commission's `robots.txt` permits both paths that were read,
  no bot protection was encountered, and none was circumvented.
- **No prose is composed.** Where the Commission published no description, the page says so
  rather than writing one. Where a leaflet breaks its requirements out under a heading that
  does not match the qualifier in the authorization's own title, the requirements are not
  claimed for that authorization, and the gap is counted in `coverage.json` instead of being
  closed by inference.
- **No leaflet is attached on a resemblance.** Attachment is an equality against a string the
  Commission published. The near misses are recorded in `PROVENANCE.md` with both of the
  Commission's own titles for each document, and the pages that support those refusals are
  kept in the tree, because a recorded non-match whose evidence has been deleted is an
  assertion rather than a finding.
- **No identifier is minted that the Registry would assign.** CTIDs come from a committed
  ledger, are marked not Registry-assigned everywhere they appear, and the `@id` namespace is
  left unresolved on purpose. `docs/adr/0004-leave-the-id-namespace-unresolved.md` records
  that decision and its cost.

**Enforcement.**

- **AUTO.** No module under `src/chalkline/` may import a networking library at all;
  `tests/test_provenance.py` scans for every shape of that import and carries a control test
  proving the scan can see one. `chalkline check` fails when the committed `site/` is not
  byte for byte what the code produces from the current sources, so a hand-edited claim in
  the published output cannot survive a gate run. Every figure the README and `PROVENANCE.md`
  quote about the build is recomputed from a fresh coverage statement in
  `tests/test_documented_counts.py`, and a figure in the prose that nothing recomputes fails
  the suite.
- **REVIEW.** This document, dated, and the accountable owner named below.

## B. Bias and fairness

**Applies, narrowly, and not in the shape the framework's usual case takes.**

Nothing here ranks, scores, recommends, or classifies a person, and no attribute of any
person is stored or inferred. The framework's allocational harms have no surface to attach
to. Two representational ones do:

- **Unevenness read as judgement.** Only some of the modeled authorizations carry a
  description, and fewer carry requirements or renewal terms. That distribution follows what
  the Commission published and which leaflet titles matched, not the importance of the
  credential. A reader skimming the page could take a sparse entry for a lesser credential.
  The page answers this in the entry itself rather than in a footnote: an authorization with
  no description says the Commission published no prose that applies to it as a whole and
  that this project does not compose one, and an authorization with no attached leaflet says
  so where a leaflet link would be.
- **Language.** For a California civic surface, English against Spanish is a first-class
  segment, and this project is English only. The declaration that names which strings could
  be translated and which are quoted source is `docs/I18N.md`, and the parity gate the
  standard asks for is not built. That is an open obligation, tracked in issue #63, and it is
  recorded here as unmet rather than argued away.

**Enforcement.** REVIEW for the representational reading, which is a judgement about framing
and is what this section is. AUTO for the part that is mechanical: the sentences above are
rendered from the catalog for every authorization that lacks the thing they describe, and
`tests/test_site.py` holds the branch that decides which of them a credential gets, including
the case where the Commission published `NONE` against a subject column and the case where it
published nothing at all. The distinction between those two matters: `NONE` is a statement
that an authorization is not subject-coded, and an empty column is an absence, and the page
does not render one as the other.

## C. Privacy and data protection

**N/A, with the reason stated rather than assumed.**

There is no personal data in this repository. The inputs are two categories of public page
published by a California state agency: a table of credential authorizations and a set of
leaflets describing document types. Neither is about an identified or identifiable person.
Nothing is collected from a reader of the published page either: there is no server, no
account, no cookie, no analytics, and no telemetry.

That last claim is the one worth making mechanically rather than promising, because it is the
one a reader cannot check by reading the source. `tests/test_performance.py` asserts that the
published page fetches nothing at all to render: no script, stylesheet, font, image, or
frame, and no `@import` or `url()` in the inline stylesheet. A tracking pixel or an analytics
snippet is a subresource, so the check that keeps the page self-contained is the same check
that keeps it from observing anybody.

The one piece of personal information in the repository is the author's own name, in
`LICENSE`, `CITATION.cff`, and the ADR deciders line, given deliberately.

## D. Transparency and explainability

**Applies. This is the audit this project is mostly about.**

**Every claim is attributable.** `PROVENANCE.md` records each source with its URL, retrieval
date, byte count, and sha256, and `tests/test_provenance.py` recomputes every hash and size
on each test run, so a snapshot refreshed or hand-edited without updating its sidecar fails
the build. Each leaflet is listed with both of the titles the Commission published for it,
because both are load-bearing in the matching rules.

**Every claim carries its uncertainty.** The page states its retrieval dates in the paragraph
under the heading. Where an authorization's subjects were supplied by following the
Commission's own cross-reference, the page prints the note it followed, the credential and
document it read, and which authorization codes supplied how many subjects. Where a leaflet
is attached, the page names the matching rule and which of the Commission's two published
titles it matched against.

**What the project cannot do is documented as prominently as what it can.** The `@id` host
does not resolve, and `docs/IDENTIFIERS.md` lays out what that costs and what the options
are. `docs/MODELING.md` records every class choice, every rejected alternative, and one
apparent gap in CTDL itself. The README's own status line says this is one worked example and
not a complete representation of California educator credentials.

**A second opinion is published beside the first.** `make verify` runs `ctdl-validate`, an
independently written structural checker, over the committed graph, and the report is
committed at `site/ctdl-validate.json`. `tests/test_ctdl_validate_evidence.py` re-runs it on
every test run and fails if the committed file is not what a fresh run reports, and it
carries a control test that mutates a `ceterms:ctid` into a bare UUID and asserts the tool
catches it. A clean report is therefore a statement about this build rather than a stale file
nobody re-checks.

**Enforcement.** AUTO for all four: the provenance hash recomputation, the byte-for-byte
`chalkline check`, the documented-count binding, and the committed independent-validator
evidence with its control. REVIEW for the honesty of the framing itself, which is this
document and the prose rule in `CONTRIBUTING.md` that forbids characterizing the Commission
as deficient.

There is no model card and no datasheet-for-datasets here, because there is no model. The
README's AI Evaluation row records that as N/A with the reason, and the zero-runtime-
dependency posture is what makes the no-model claim mechanically checkable rather than a
promise.

## E. Accessibility

**Applies.** The published page is human-facing, so it is in scope, and the framework's rule
about a tool's own HTML output being the surface that must be gated is the rule that binds
here.

The generated page was reviewed on 2026-08-27. Three defects were found and fixed: table
header cells carrying no `scope`, two lists whose CSS-removed markers took their list
semantics with them in Safari, and a horizontally scrolling region a keyboard could not
reach. `tests/test_accessibility.py` is now the gate and `make verify` runs it. Every check
in it is exercised against a deliberately broken copy of the real page, and a check with no
such breakage fails the suite, so the gate cannot quietly stop checking something.

**What it does not cover, stated because the framework asks for the floor and the gap.** It
is a check against a named list of conditions, not an audit. No assistive technology is
driven, no browser lays the page out, and reading order and comprehension are not assessed.

**Enforcement.** AUTO for the structural checks, which are merge-blocking through
`make verify` and the required `verify` status check. The REVIEW gate the standard asks for,
a screen-reader walkthrough and an accessibility conformance report, is **open**. No
walkthrough has been performed and none is claimed. This row is a floor, not a clean bill,
and the README says so in the same words.

## F. Security

**Applies, on a small surface, and the surface is named rather than waved at.**

`SECURITY.md` carries the confidential reporting channel, a seven-day acknowledgement
expectation, and the real risk surface: untrusted input parsing over vendored HTML snapshots,
output escaping on the generated page, and the supply chain. There is no server, no database,
no authentication, and no runtime dependency.

**Enforcement, all AUTO and all merge-blocking**, by the required status checks named in the
header of `.github/workflows/ci.yml`: `make verify` byte for byte with the local target,
`pip-audit --strict` against the locked dependency set exported from `uv.lock`, gitleaks over
full history, Semgrep over `src tests scripts`, `zizmor` over the workflow files themselves,
and CodeQL. Every action is pinned to a full 40-character commit SHA, every workflow declares
a top-level least-privilege `permissions:` block, and Dependabot raises dependencies with a
cooldown. Output escaping has its own test: markup arriving through source data is escaped
rather than rendered.

**Residual, and deliberate.** The `main` ruleset carries a repository-role bypass actor with
`bypass_mode: always`. That is a decision, not an oversight: an agent once removed an admin
bypass on another repository and locked the owner out, so a way back in is kept. The
consequence is stated plainly in the workflow header and pinned by `tests/test_ruleset.py`:
these checks block a merge for anyone who cannot bypass, and deliberately do not block one
for the owner.

## Residual risk after the mitigations

| Risk | Who it lands on | What limits it | What does not limit it |
|---|---|---|---|
| The graph is read as authoritative and used for an assignment decision | An educator assigned against a stale or excluded authorization | The disclaimer rides the page, the JSON-LD, and the coverage statement; every entry links to the Commission's own row; retrieval dates are on the page | A file downloaded once and read later, where only the JSON-LD `comment` travels with it |
| Absent authorizations are read as authorizations that do not exist | Holders of the excluded credentials | The page publishes a table of what is not modeled and why, and the coverage statement counts it | A reader who takes the modeled list as the whole of the Commission's table |
| A CTID here is taken for a Registry-assigned one | Credential Engine, and anyone reconciling two graphs later | Every published surface says the CTIDs are not Registry-assigned; the ledger is committed and reviewable | A CTID copied out of the JSON-LD on its own |
| The sources age without anyone noticing | Any reader who trusts a figure years later | Retrieval dates appear on every source row and on the page; sidecar hashes fail the build if a snapshot changes without its record | Nothing re-fetches on a schedule; staleness is a decision a person has to make |
| A Spanish-reading Californian cannot read the page | Limited-English-proficient readers of a California civic surface | Nothing yet; the boundary between translatable and quoted source is declared in `docs/I18N.md` | The declaration itself, which is not a translation |
| The published page and this repository disagree | A reader who arrives from a search result rather than from the repo | `.github/workflows/live-integrity.yml` fetches the live surface daily and fails naming every byte-level difference | It is not a required check, deliberately: it grades a deployment, not a merge |

## What is asked of anyone citing this work

Name the retrieval date with the figure. Say that it is unofficial and that nothing has been
published to the Credential Registry. Do not present a modeled authorization as the
Commission's own statement of what a credential permits. That is the whole list.

## Ownership and review

Accountable owner: Chelsea Kelly-Reif, who is also the sole maintainer. There is no
independent reviewer, and no part of this document should be read as though there were.

This audit is reviewed, and the date at the top moves, when any of these happen: a source is
re-retrieved, a new source is added, the matching rules change, an audit letter changes its
applies or N/A call, or a release is cut. The open obligations it records, the accessibility
REVIEW gate and the internationalization catalog, are tracked as issues rather than as
sentences here, so closing one is a visible event.
