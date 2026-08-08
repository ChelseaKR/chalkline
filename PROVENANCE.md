# Provenance

Every source this project reads, when it was retrieved, and everything it publishes that the
source does not support. Counts in this file are produced by the build and cross-checked by
`site/coverage.json`, which is recomputed from the emitted graph on every run.

**Unofficial.** Chalkline is not affiliated with, endorsed by, or published by the California
Commission on Teacher Credentialing or by Credential Engine. Nothing here has been published
to the Credential Registry, in production or in a sandbox.

## Sources

| Artifact | Source | Retrieved | Bytes | sha256 |
|---|---|---|---|---|
| `data/source/authorization-sort-table.html` | <https://www.ctc.ca.gov/employers/assignment-resources/resources/authorization-sort-table/> | 2026-08-07 | 257,373 | `75d6cdde…97eb83e` |
| `data/source/credential-leaflets.html` | <https://www.ctc.ca.gov/credentials/leaflets/> | 2026-08-07 | 115,673 | `d062aee5…56fefae` |
| `src/chalkline/ctdl/ctdl-context.json` | <https://credreg.net/ctdl/schema/context/json> | 2026-08-07 | 29,201 | `ddb6b458…4bf40db5` |
| `src/chalkline/ctdl/ctdl-schema.json` | <https://credreg.net/ctdl/schema/encoding/json> | 2026-08-07 | 1,052,234 | `a2dd28cb…cc538776` |

Full hashes and per-file notes are in the `.source.json` sidecar beside each artifact.
`tests/test_provenance.py` recomputes every hash and size on each test run, so a snapshot
that is refreshed or hand-edited without updating its sidecar fails the build.

### How they were retrieved

Each was fetched once, with a single unauthenticated GET over HTTPS.
<https://www.ctc.ca.gov/robots.txt> disallows only `/wp-admin/`, so both Commission paths are
permitted by the site's own policy. The sort table request was issued against the
`/credentials/assignment-resources/authorization-sort-table` path published in the brief and
followed a 301 to the `/employers/…` URL above; both are recorded in the sidecar.

**No bot protection was encountered, and none was circumvented.** No page was refused, so no
hand transcription was necessary and none of this data is hand-transcribed. `scripts/fetch_sources.py`
is the only code in this repository that opens a socket; it stops on an HTTP error rather than
retrying behind different headers, and `tests/test_provenance.py` asserts that no module under
`src/chalkline/` imports a networking library at all. Tests and CI are hermetic.

The Commission publishes its own statement of what the table covers, on the page: "This table
contains credential authorizations and subjects that the Commission currently authorizes. This
list does not include credential authorizations that the Commission no longer issues." A test
asserts that sentence is still present in the vendored snapshot.

### Licensing and attribution

The sort table and the leaflet index are works of a California state agency, published
publicly for public use. This project reproduces the Commission's factual data (credential
names, codes, subjects, and notes) and cites the source page on every credential it models.
CTDL is published by Credential Engine at credreg.net. Neither organization has reviewed or
approved this project.

## What is counted

Recomputed from the emitted graph at build time and written to `site/coverage.json`:

| Figure | Count |
|---|---|
| Rows published in the sort table | 553 |
| Authorizations in those rows | 136 |
| Modeled as `ceterms:License` | 125 |
| Excluded, with reasons below | 11 |
| `ceterms:CredentialAlignmentObject` subject alignments emitted | 476 |
| Authorizations with subject codes | 59 |
| Authorizations the Commission publishes as `NONE` (not subject-coded) | 66 |
| Authorizations carrying `ceterms:description` | 37 |
| Authorizations linked to a CTC leaflet | 12 |
| Leaflets in the Commission's index | 81 |
| CTIDs in the ledger (125 licenses plus the Commission) | 126 |

## Exclusions

An authorization is modeled only where its scope can be read from the sort table itself,
either as subject codes or as the Commission's published `NONE`. These 11 are the ones whose
scope the table points to somewhere else. Their names are published and unambiguous; it is
the scope that this project has not verified.

| Authorization | Document | Code | Reason |
|---|---|---|---|
| Teaching Permit for Statutory Leave (Single Subject) | `TPSL` | `R1S` | Scope deferred to another credential's subject list. Commission note: Subject Codes Same as on Single Subject Teaching Credential |
| Teaching Permit for Statutory Leave (Special Education) | `TPSL` | `R3SE` | No scope published at all. Commission note: (none) |
| Eminence Teaching Credential | `TC5` | `R5F` | Scope indicated on the issued document. Commission note: (none) |
| Exchange Certificated Employee Teaching Credential | `TC7` | `R1S` | Scope deferred to another credential's subject list. Commission note: Subject Codes Same as on Single Subject Teaching Credential |
| Sojourn Certificated Employee Teaching Credential | `TC8` | `R8` | Scope indicated on the issued document. Commission note: (none) |
| Short-Term Staff Permit (Single Subject) | `TC13` | `R1S, R1F, R1GS, R1WL` | Scope deferred to another credential's subject list. Commission note: Subject Codes Same as on Single Subject Teaching Credential |
| Short-Term Staff Permit (Special Education) | `TC13` | (none published) | Scope deferred to another credential's subject list. Commission note: Authorization and Subject Codes Same as on Education Specialist Instruction Credential |
| Provisional Internship Permit (Single Subject) | `TC14` | `R1S, R1F, R1GS, R1WL` | Scope deferred to another credential's subject list. Commission note: Subject Codes Same as on Single Subject Teaching Credential |
| Provisional Internship Permit (Special Education) | `TC14` | (none published) | Scope deferred to another credential's subject list. Commission note: Authorization and Subject Codes Same as on Education Specialist Instruction Credential |
| General Education Single Subject Limited Assignment Teaching Permit | `TLA1` | `R1S, R1F, R1GS, R1WL` | Scope deferred to another credential's subject list. Commission note: Subject Codes Same as on Single Subject Teaching Credential |
| Special Education Limited Assignment Teaching Permit | `TLA3` | (none published) | Scope deferred to another credential's subject list. Commission note: Authorization and Subject Codes Same as on Education Specialist Instruction Credential |

Resolving the eight deferred cases is tractable and is the obvious next milestone: it means
asserting that, for example, the Provisional Internship Permit (Single Subject) carries the
same 95 subject codes as the Single Subject Teaching Credential. The Commission states that
in prose. This project has not verified it row by row, so it does not assert it.

## Properties deliberately not emitted

| Property | Why not |
|---|---|
| `ceterms:occupationType` | The sort table publishes no occupation codes. Aligning a teaching credential to an SOC occupation would be this project's judgement, not the Commission's statement. |
| `ceterms:audienceLevelType` | Grade ranges appear as prose in the Notes column. Mapping that prose onto CTDL's audience level concept scheme would be an interpretation the Commission has not published. The prose is carried verbatim on the subject alignment instead. |
| Competency framework | The sort table publishes subject names, not competency statements, and `ceterms:targetCompetency` is not in the domain of `ceterms:License`. See [docs/MODELING.md](docs/MODELING.md). |
| `ceterms:description` on 88 of 125 licenses | The Commission published no prose that applies to the whole authorization. Absence, not a placeholder. |
| `ceterms:codedNotation` | Not in the domain of `ceterms:License`. The codes ride `ceterms:identifier` instead. |

## Things this project asserts that need naming

**The organization address.** `ceterms:address` on the Commission is transcribed from the
footer of the vendored sort table page ("Commission on Teacher Credentialing, 651 Bannon
Street, Sacramento, CA 95811"). Two values expand what the page abbreviates: `CA` is emitted
as "California" and the country as "United States", the latter from the page's own "Official
website of the State of California" banner. A test asserts the printed strings are still in
the artifact.

**Leaflet links.** A leaflet is attached to an authorization only where the leaflet's
published title equals the authorization's published title after case and punctuation
normalization. Nothing else: no prefix matching, no keyword overlap, no reasoning from a
document code to a leaflet number. That rule matches 12 of 125 authorizations. The other 113
link to the sort table, which is the page that does describe them.

**Note joining.** The Notes column is a bulleted list. Where notes become a single CTDL
string value, the bullets are joined with newlines rather than run together into a sentence.

**Comma-separated cells.** Two columns sometimes hold a list (`TC1, TC2`, and
`R1S, R1F, R1GS, R1WL`). These are split on the comma into separate identifiers. The verbatim
cell is kept on the model object beside the split.

**`Multiple` is not a code.** Where the Document Title column reads `Multiple`, the Commission
is saying that more than one document type carries the authorization without naming them. It
is kept verbatim on the model and never emitted as an identifier value.

## Identifiers

CTIDs here follow the published grammar exactly: `ce-` plus a standard UUIDv4, per
<https://credreg.net/ctdl/ctid> (retrieved 2026-08-07). They are minted once by
`chalkline mint-ctids` and committed to `data/ctid-ledger.json`; re-export is idempotent
because the ledger is in version control, not because the identifier is derived from a key.

They are **not Registry-assigned**. A CTID becomes meaningful when a registry assigns it to a
resource it holds, and nothing here is published to any registry. `@id` URIs live under this
project's own namespace and deliberately not under `credentialengineregistry.org`; a test
asserts that.
