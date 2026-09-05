# Metrics ledger

Dated 2026-09-05. Every metric this repository holds itself to, what measures it, and whether
failing it blocks a merge (**AUTO**), waits on a person (**REVIEW**), or does not apply here
at all (**N/A**, with the reason). The portfolio standard this shape comes from allows
exactly those three dispositions. A control that is run but ignored, or written down and not
run, is neither, and is recorded below as an open obligation rather than as a metric.

This is a documentation gap being closed, not a measurement gap. Every AUTO row below was
already enforced before this file existed; what did not exist was the one place a reader
could see the whole list, including the rows that are empty.

## What this file deliberately does not contain

**A snapshot of measured values.** `CONTRIBUTING.md` rule 5 is "counts are counted: do not
write a total into prose that nothing recomputes", and a ledger that published its own test
count and coverage percentage would be the largest single violation of that rule in the
repository. The comment above `fail_under` in `pyproject.toml` shows the failure mode in
miniature: it records a measurement taken on a named date, and the suite has grown since.
Because it is dated it reads as history rather than as a current claim, which is the only
reason it is not drift.

So the columns below name the target and the mechanism. The current value is whatever the
mechanism reports on the run you are looking at, and `make verify` prints all of it.

**A restatement of the pinned tool floors.** The Python, ruff, mypy, and complexity floors are
stated once, in the README's Code Quality row, and `tests/test_documented_floors.py` reads
them out of `pyproject.toml` and fails when the prose and the pins disagree. A second copy
here would be a second thing to drift, and the check that exists reads the first copy.

The 97% coverage floor is the exception, and it is quoted here on purpose: that same test
already holds every document that states it to `pyproject.toml`'s `fail_under`, and this file
is now one of the documents it reads.

## Correctness and code quality

| Metric | Target | Measured by | Gate |
|---|---|---|---|
| Branch coverage | 97% coverage floor, `fail_under` in `pyproject.toml` | `make test`, inside `make verify` | AUTO |
| Lint and format | no finding, no reformatting | `ruff check .` and `ruff format --check .` | AUTO |
| Type checking | no error, `strict = true`, over `src tests scripts` | `mypy` | AUTO |
| Cyclomatic complexity | at or under the `mccabe` cap in `pyproject.toml` | `ruff` rule family `C90` | AUTO |
| Em dashes in prose this project wrote | none | `make no-dashes`, which fails on a `git grep` that could not run rather than reading its silence as a pass | AUTO |
| Lockfile agreement with `pyproject.toml` | exact | `uv lock --check --offline`, first in `make verify` | AUTO |
| Local gate equals CI | byte for byte | `.github/workflows/ci.yml` runs `make verify`, the same target a contributor runs | AUTO |

## The data, and what is published about it

| Metric | Target | Measured by | Gate |
|---|---|---|---|
| Committed `site/` against a fresh build | no byte differs | `chalkline check` | AUTO |
| Files under `site/` that no gate accounts for | none | `chalkline check`, which fails on an unaccounted file and names the gate for each one it skips | AUTO |
| Source snapshots against their sidecars | every sha256 and byte count recomputed | `tests/test_provenance.py` | AUTO |
| Independent CTDL validation of the published graph | no ERROR finding | `make validate`, running the separately written `ctdl-validate` over `site/credentials.jsonld` | AUTO |
| The committed validator report against a fresh run | identical | `tests/test_ctdl_validate_evidence.py`, with a control that mutates a `ceterms:ctid` and asserts the tool catches it | AUTO |
| CTDL class, property, domain, and range of every emitted document | valid against the vendored schema encoding | `src/chalkline/ctdl/validate.py`, before anything is written | AUTO |
| CTID grammar, including version nibble and variant bits | conforms | `tests/test_ctid.py` | AUTO |
| Figures quoted in `README.md` and `PROVENANCE.md` | equal to a freshly counted coverage statement | `tests/test_documented_counts.py`, over both tables and the prose, with a denominator test that fails on a figure nothing binds | AUTO |
| Tool floors quoted in prose | equal to the `pyproject.toml` pins | `tests/test_documented_floors.py` | AUTO |
| Networking imports under `src/chalkline/` | none | `tests/test_provenance.py`, with a control asserting the scan can see an import of every shape | AUTO |

## The published page

| Metric | Target | Measured by | Gate |
|---|---|---|---|
| Subresources fetched to render | none: no script, stylesheet, font, image, or frame, and no `@import` or `url()` in the inline stylesheet | `tests/test_performance.py` | AUTO |
| Page weight | the formula in `tests/test_performance.py`: `FIXED_OVERHEAD_BUDGET` plus `PER_AUTHORIZATION_BUDGET` for each modeled authorization, so markup growth fails and the Commission publishing more credentials does not | `tests/test_performance.py`, which also binds the figures the README publishes to the page it measured | AUTO |
| Relative links on the page | every one resolves | `tests/test_performance.py` | AUTO |
| Escaping of source-derived text | markup arriving through source data is escaped, not rendered | `tests/test_site.py` | AUTO |
| Structural accessibility checks | no fault, and every check exercised against a deliberately broken copy of the real page | `tests/test_accessibility.py` | AUTO |
| Screen-reader walkthrough and an accessibility conformance report | one per release | nothing yet | **REVIEW, open.** No walkthrough has been performed and none is claimed. The structural gate is a floor, and the README's Accessibility row says so in the same words |
| The live page against this repository | no byte differs | `.github/workflows/live-integrity.yml`, daily and on demand | AUTO on a schedule, and **not** a required check. It reaches the network, which the merge gate never does, and it grades a deployment rather than a change. A deployment that has not happened yet is not a reason to block a merge |

## Security and supply chain

| Metric | Target | Measured by | Gate |
|---|---|---|---|
| Known advisories against the locked dependency set | none | `make audit`, running `pip-audit --strict --require-hashes` over the set exported from `uv.lock` with the project itself dropped | AUTO, as the last step of `make verify` and again as its own CI job |
| Secrets in the tree or its history | none | gitleaks over full history, in CI and in `.pre-commit-config.yaml`, with no `|| true` | AUTO |
| Static analysis of `src tests scripts` | no finding | Semgrep, and CodeQL as a second and independently built opinion | AUTO |
| Static analysis of the workflow files themselves | no finding | `zizmor` | AUTO |
| Action pinning | every `uses:` at a full 40-character commit SHA | reviewed at the pin, and `tests/test_workflow_pins.py` | AUTO |
| The committed branch ruleset against the live one | the committed file carries what the live ruleset carries, bypass actor included | `tests/test_ruleset.py` | AUTO |
| The portfolio standards pin | a released `vMAJOR.MINOR.PATCH` tag, never a branch | `tests/test_standards_pin.py` | AUTO |
| Runtime dependencies | none | `pyproject.toml`, and it is what makes the no-model claim checkable rather than promised | AUTO |

## Rows that are open

These are obligations, not metrics, and they are here so that the absence is countable.

| Obligation | State | Where it is tracked |
|---|---|---|
| Screen-reader walkthrough and conformance report | not performed | the Accessibility row above, and the README's Accessibility row |
| EN and ES catalog parity | scope declared in `docs/I18N.md`; no catalog and no parity check exist | issue #63 |
| First signed tag | no tag cut, so nothing has been released and the version in `pyproject.toml` has never been published anywhere | issue #61 |

## Rows that are N/A, with the reason

Declaring these is the point of the exercise. A silent skip and a considered exemption look
identical from outside the repository, so each one is written down.

| Metric the standard names | Why it does not apply here |
|---|---|
| p95 server response, first-token latency, load-test budgets | There is no server and no runtime. The published output is static files served from GitHub Pages with no client-side fetch, and the page weight budget above is what replaces a latency budget for that shape |
| Lighthouse performance score, critical-path JS budget | The page ships no JavaScript at all, which the subresource check enforces |
| Structured logs, OTel spans, `/livez` and `/readyz`, SLOs, burn-rate alerts | Nothing runs. The observable surface is the build, and `chalkline check` is what surfaces drift between sources, code, and published output |
| RAG faithfulness, hallucination rate, red-team suites, judge calibration | No model, prompt, retrieval, embedding, or generation runs at build time or ships in the output |
| Cross-browser matrix, container build, IaC plan | No container, no infrastructure, and one static page with no scripted behaviour to differ across engines |
| Retention schedules, subject-access and deletion paths, no-PII-in-logs | There is no personal data and there are no logs. The inputs are a state agency's published pages about document types |
| DORA delivery metrics | A portfolio-level signal collected across repositories, not a per-repository gate, and not measured here |
| AI-development activity counters: sessions, tokens, lines changed, percent AI-generated | Not tracked and not gated, deliberately. The gates in this repository are outcome-side: `make verify` on every change, and the merge is blocked by what the change does rather than by how it was written |
| Incident metrics: MTTR, change fail rate | No incident has been recorded, so there is nothing to measure. `SECURITY.md` carries the reporting channel and the seven-day acknowledgement expectation, and there is no `docs/incidents/` directory yet |

## How this file stays true

Nothing regenerates it. It is prose, and prose is exactly what this repository does not
trust, so it is deliberately built out of things that fail elsewhere when they stop being
true: it quotes one number, and a test reads that number out of `pyproject.toml`; every other
cell names a target and the file that enforces it, so a row describing a gate that has been
deleted points at a path that no longer exists.

It is reviewed, and the date at the top moves, when a gate is added to or removed from
`make verify` or the CI workflows, when an open row above closes, or when a release is cut.
