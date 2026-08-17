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

Plus ten leaflet pages under `data/source/leaflets/`, each retrieved 2026-08-07 from
`https://www.ctc.ca.gov/credentials/leaflets/<code>/`:

| Leaflet | Title as the Commission's index lists it | Bytes | sha256 |
|---|---|---|---|
| `cl-380` | School Nurse Services Credential | 92,774 | `62973ee1…f8dc99` |
| `cl-562` | Teacher Librarian Services Credential | 92,744 | `e363620f…785e56` |
| `cl-625` | Resource Specialist Added Authorization | 94,052 | `90892ef0…e387db` |
| `cl-812` | Reading and Literacy Added Authorization | 88,048 | `b5d2e33c…204d5e` |
| `cl-824` | Certificate of Completion of Staff Development | 84,613 | `970801b3…013a6b` |
| `cl-856` | Provisional Internship Permit | 97,856 | `b5d411d2…c78992` |
| `cl-858` | Short-Term Staff Permit | 96,347 | `53362652…9bcebc` |
| `cl-879` | Speech-Language Pathology Services Credential | 119,415 | `a92e6307…b83bca` |
| `cl-893` | American Indian Languages Credential | 86,939 | `ff04bc21…8437e3` |
| `cl-909` | Emergency Specialist Teaching Permit in Early Childhood Education | 88,526 | `ddbd722e…a9131e` |

Those ten are the only leaflets retrieved. Each one is a leaflet a published title identifies
with an authorization this project models; nothing was fetched speculatively, and a test
asserts that the set of vendored snapshots is exactly the set the matcher asks for.

Full hashes and per-file notes are in the `.source.json` sidecar beside each artifact.
`tests/test_provenance.py` recomputes every hash and size on each test run, so a snapshot
that is refreshed or hand-edited without updating its sidecar fails the build.

### How they were retrieved

Each was fetched once, with a single unauthenticated GET over HTTPS.
<https://www.ctc.ca.gov/robots.txt> disallows only `/wp-admin/`, so every Commission path
below is permitted by the site's own policy. The sort table request was issued against the
`/credentials/assignment-resources/authorization-sort-table` path published in the brief and
followed a 301 to the `/employers/…` URL above; both are recorded in the sidecar.

**No bot protection was encountered, and none was circumvented.** Every request returned
HTTP 200 to a plain unauthenticated GET, including all ten leaflet pages. No page was
refused, so no hand transcription was necessary and none of this data is hand-transcribed.
`scripts/fetch_sources.py` is the only code in this repository that opens a socket; it stops
on an HTTP error rather than retrying behind different headers, and
`tests/test_provenance.py` asserts that no module under `src/chalkline/` imports a networking
library at all. Tests and CI are hermetic.

### The leaflets are web pages

The brief for this milestone described the leaflets as PDFs. They are served as HTML: every
leaflet linked from the Commission's index under `/credentials/leaflets/<code>/` returns its
full text as a web page, headings and all. That is what this project reads, so no PDF text
extraction is involved and none of the failure modes of PDF extraction apply here. The
Commission does also publish downloadable forms from `docs.ctc.ca.gov`, and this project
retrieves none of them.

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
| Modeled as `ceterms:License` | 133 |
| Excluded, with reasons below | 3 |
| `ceterms:CredentialAlignmentObject` subject alignments emitted | 1,014 |
| Of those, supplied by following a published cross-reference | 538 |
| Authorizations whose scope was resolved by cross-reference | 8 |
| Authorizations with subject codes | 67 |
| Authorizations the Commission publishes as `NONE` (not subject-coded) | 66 |
| Authorizations carrying `ceterms:description` | 51 |
| Of those, described in a Commission leaflet | 16 |
| Authorizations carrying `ceterms:requires` | 13 |
| Authorizations carrying `ceterms:renewal` | 7 |
| `ceterms:ConditionProfile` nodes emitted | 22 |
| Authorizations linked to a CTC leaflet | 18 |
| Leaflet pages read | 9 |
| Leaflet pages refused on identity | 1 |
| Leaflets in the Commission's index | 81 |
| CTIDs in the ledger (133 licenses plus the Commission) | 134 |

## Following the Commission's cross-references

Eight authorizations publish no subject code of their own and carry a note pointing at
another credential's rows in the same table. All eight references were followed, row by row,
against the vendored artifact. Two wordings appear, and they mean different things.

**`Subject Codes Same as on Single Subject Teaching Credential`** defers only the subject
list. The deferring row publishes its own Authorization Code, so each code was looked up
under the Authorization Title the note names, and that code's subjects were taken.

| Authorization | Document | Own codes | Rows read from `TC1` / Single Subject Teaching Credential | Subjects |
|---|---|---|---|---|
| Teaching Permit for Statutory Leave (Single Subject) | `TPSL` | `R1S` | `R1S` (95) | 95 |
| Exchange Certificated Employee Teaching Credential | `TC7` | `R1S` | `R1S` (95) | 95 |
| Short-Term Staff Permit (Single Subject) | `TC13` | `R1S, R1F, R1GS, R1WL` | `R1S` (95), `R1F` (2), `R1GS` (2), `R1WL` (2) | 101 |
| Provisional Internship Permit (Single Subject) | `TC14` | `R1S, R1F, R1GS, R1WL` | `R1S` (95), `R1F` (2), `R1GS` (2), `R1WL` (2) | 101 |
| General Education Single Subject Limited Assignment Teaching Permit | `TLA1` | `R1S, R1F, R1GS, R1WL` | `R1S` (95), `R1F` (2), `R1GS` (2), `R1WL` (2) | 101 |

The four codes those three permits publish are exactly the four the Commission publishes
under the Authorization Title `Single Subject Teaching Credential`, with none left over on
either side. `Single Subject Teaching Credential (Specialized)` is a different published
title, carrying `R1E`, `R1G`, `R1H`, and `R1P`, and none of its subjects crossed.

**`Authorization and Subject Codes Same as on Education Specialist Instruction Credential`**
defers both. These three rows publish no Authorization Code at all, so the codes came across
too, all sixteen the Commission publishes under that title on `TC3S`:

| Authorization | Document | Codes taken | Subjects |
|---|---|---|---|
| Short-Term Staff Permit (Special Education) | `TC13` | `R3MN`, `R3EN`, `R3HD`, `R3ER`, `R3VB`, `SEEC`, `R3BM`, `R3BE`, `R3BC`, `R3DH`, `R3EC`, `R3LD`, `R3MM`, `R3MS`, `R3PI`, `R3VI` | 15 |
| Provisional Internship Permit (Special Education) | `TC14` | the same sixteen | 15 |
| Special Education Limited Assignment Teaching Permit | `TLA3` | the same sixteen | 15 |

Sixteen codes, fifteen subjects: `SEEC` (Early Childhood Added Authorization) is the one row
of the sixteen whose Subject Code column reads `NONE`, so it supplies an Authorization Code
and no subject alignment. That is recorded per code in the browsable page and per
authorization in the coverage statement rather than quietly rounded away.

**What crosses, and what does not.** The subject code and the subject name cross. The
referenced rows' Notes do not. The Commission's statement is that the *subject codes* are the
same; a note it wrote on a row of the Single Subject Teaching Credential, such as "Pursuant
to Title 5 80004(c), Authorized to Teach Subject in CTE or Vocational Classes at the
Discretion of the Employing Agency", is a remark about that row, and repeating it on a
different credential would be this project asserting something the Commission did not.

**The cross-reference note is not a description.** Once followed, it is recorded as
provenance on the authorization and shown on the page. It never becomes `ceterms:description`,
because "Subject Codes Same as on Single Subject Teaching Credential" is an instruction for
reading a table, not prose about a credential.

## Exclusions

Three authorizations remain unmodeled. None of them is a deferred scope: all eight of those
were followed. These three publish no scope this project can read from any source it holds.

| Authorization | Document | Code | Reason |
|---|---|---|---|
| Eminence Teaching Credential | `TC5` | `R5F` | The Subject column reads "Indicated on Document", so the scope is written on the issued credential and not in any machine-readable source this project reads. |
| Sojourn Certificated Employee Teaching Credential | `TC8` | `R8` | The same: "Indicated on Document". |
| Teaching Permit for Statutory Leave (Special Education) | `TPSL` | `R3SE` | No subject code, no subject, and no note. The Commission publishes nothing about this authorization's scope in this table, including no cross-reference to follow. Its two sibling permits on `TPSL` are modeled, so the absence is specific to this row. |

A reference this project could not follow would also land here, with a reason naming what was
found: a title no row publishes, a title published on more than one document, an Authorization
Code the named credential does not carry, or a credential that defers its own scope in turn.
None of the eight fell into any of those, and `tests/test_model.py` exercises each refusal.

## Properties deliberately not emitted

| Property | Why not |
|---|---|
| `ceterms:occupationType` | The sort table publishes no occupation codes. Aligning a teaching credential to an SOC occupation would be this project's judgement, not the Commission's statement. |
| `ceterms:audienceLevelType` | Grade ranges appear as prose in the Notes column. Mapping that prose onto CTDL's audience level concept scheme would be an interpretation the Commission has not published. The prose is carried verbatim on the subject alignment instead. |
| Competency framework | The sort table publishes subject names, not competency statements, and `ceterms:targetCompetency` is not in the domain of `ceterms:License`. See [docs/MODELING.md](docs/MODELING.md). |
| `ceterms:description` on 82 of 133 licenses | No leaflet is matched to them and the Commission published no Notes that apply to the whole authorization. Absence, not a placeholder. |
| `ceterms:requires` on 120 of 133, `ceterms:renewal` on 126 | The leaflet those licenses would need either was not matched, was not read, or states its requirements under headings this project does not classify. Counted, not hidden. |
| `ceterms:renewalFrequency` | The leaflets state validity in prose ("issued for five calendar years"). Turning that into a `schema:Duration` would be this project parsing a sentence into a datatype the Commission never wrote. The sentence rides `ceterms:renewal` verbatim instead. |
| `ceterms:codedNotation` | Not in the domain of `ceterms:License`. The codes ride `ceterms:identifier` instead. |

## The leaflets: what was matched, what was read, and what was not

### Matching

A leaflet is attached to an authorization on title equality, and on nothing else. Two rules:

1. **Exact title**, after case and punctuation normalization. 12 authorizations.
2. **Named family**: the authorization's title is a leaflet's title followed by one trailing
   parenthesised qualifier, and the part before it equals the leaflet's title under the same
   normalization. 6 authorizations, all of them the three Short-Term Staff Permit variants
   (`cl-858`) and the three Provisional Internship Permit variants (`cl-856`). Rule 1 is tried
   first, so an authorization with a leaflet of its own is never rolled up into a family one.

Rule 2 is still an equality. It is not a prefix rule: `Education Specialist Instruction
Credential Requirements for Teachers Prepared Outside of California` (`cl-808`) matches
nothing, because what separates it from `Education Specialist Instruction Credential` is not
a trailing parenthetical.

18 of 133 authorizations match a leaflet; 115 do not. Near misses were left unmatched
deliberately, and they are worth naming because a human at the Commission could confirm any
of them in a minute and this project cannot:

| Leaflet | Its title | An authorization it plausibly describes | Why it is not attached |
|---|---|---|---|
| `cl-504` | Eminence Credential | Eminence Teaching Credential | One word apart. Nothing in either source says the two names are the same document. |
| `cl-501` | Exchange Credential | Exchange Certificated Employee Teaching Credential | Two words apart. |
| `cl-568` | Sojourn Certificated Employee Credential | Sojourn Certificated Employee Teaching Credential | One word apart. |
| `cl-889` | Special Education Limited Assignment Permit | Special Education Limited Assignment Teaching Permit | One word apart. |
| `cl-902` | The Teaching Permit for Statutory Leave (TPSL) | Teaching Permit for Statutory Leave (Multiple Subject) | Would need a leading article dropped as well as the qualifier. |
| `cl-797` | Child Development Permits | The six Child Development permits | A plural naming a family the Commission does not name individually here. |
| `cl-537` | Reading and Literacy Leadership Specialist Credential | Reading and Literacy Leadership Specialist | One word apart. |
| `cl-529` | Specialist Instruction Credentials | Specialist Instruction Credential | Singular against plural. |
| `cl-628b` | Bilingual Authorizations | Bilingual Authorization | Singular against plural. |

Each of these would be a guess. A leaflet matched by guesswork is worse than no leaflet,
because the prose it carries is then attributed to a document that may not be the one it
describes.

### Reading

A matched leaflet's prose is read only where the leaflet page states its own identity: the
`<h1>` reads `"<title> (<CODE>)"`, and both halves must agree with what the Commission's index
said about it. **One leaflet fails that check.** `cl-893` is listed in the index as "American
Indian Languages Credential" and titles itself "American Indian Languages-Culture
Credential". The two authorizations that match it (`AIL` and `AILC`) keep the leaflet link,
because the Commission's own index made that association, and they get no prose, because a
page whose title is not the title it was matched under is not evidence about the
authorization it was matched to. The refusal is recorded in `site/coverage.json` and printed
on the page.

So: 18 authorizations matched, 10 distinct leaflets, 9 pages read, 1 refused, and 16
authorizations carrying leaflet prose.

### Where reading stops

Several leaflets describe more than one document. `cl-380` is titled for the School Nurse
Services Credential and then moves on to the Special Teaching Authorization in Health and the
Other Health Services Credentials, each with its own requirements section. Reading stops at
the first heading that this project cannot classify **and** that names a credential, permit,
certificate, certification, or authorization, and at the first heading that repeats one
already seen. Everything past that point belongs to another document and is never read.

Within the readable range, only sections whose heading classifies contribute anything. The
vocabulary is small and published in `src/chalkline/sources/leaflet_pages.py`: a heading
beginning "Requirements", a heading containing "renew", "Period of Validity" or "Term of the
Credential", "Authorization", "Introduction", and "Terms and Definitions" or a heading
beginning "Definition". Anything else is skipped, recorded, and counted in
`site/coverage.json` under `headings_read_past_but_not_classified`.

That is deliberately blunt, and it costs real content. `cl-858` and `cl-856` state their
requirements under "Requirements for Issuance" and then break them out under "Single
Subject:", "Multiple Subject:", and "Education Specialist:". Those three sub-headings are
skipped, so the Short-Term Staff Permit and Provisional Internship Permit carry only the
requirements common to all three variants. Reading the per-variant sections would mean
deciding that "Education Specialist:" is the section for the permit titled "(Special
Education)", which is a judgement about the Commission's wording rather than a reading of it.

### What the leaflets supplied

| Property | From what |
|---|---|
| `ceterms:description` | The leaflet's prose between its title and its first heading, plus the text of an `Authorization` section where the leaflet heads one. Both are "a statement, characterization or account of the entity", which is CTDL's definition. Where a leaflet supplied nothing, the sort table's Notes column stands as before. |
| `ceterms:requires` | One `ceterms:ConditionProfile` per requirements section, named with the Commission's own heading. |
| `ceterms:renewal` | One `ceterms:ConditionProfile` per renewal or validity section. |

Each condition profile carries the leaflet URL on `ceterms:subjectWebpage`, because the
leaflet states more about these conditions than this project reads out of it.

## Things this project asserts that need naming

**The organization address.** `ceterms:address` on the Commission is transcribed from the
footer of the vendored sort table page ("Commission on Teacher Credentialing, 651 Bannon
Street, Sacramento, CA 95811"). Two values expand what the page abbreviates: `CA` is emitted
as "California" and the country as "United States", the latter from the page's own "Official
website of the State of California" banner. A test asserts the printed strings are still in
the artifact.

**Leaflet links.** A leaflet is attached only by title equality, under the two rules above.
No prefix matching, no keyword overlap, no reasoning from a document code to a leaflet
number, no similarity score. That matches 18 of 133 authorizations. The other 115 link to the
sort table, which is the page that does describe them.

**Note joining.** The Notes column is a bulleted list, and a leaflet section is a run of
paragraphs and bullets. Where either becomes a single CTDL string value, the pieces are
joined with newlines rather than run together into a sentence. Where a leaflet section
becomes `ceterms:condition`, each paragraph and bullet is a separate value instead, because
that property's definition is a *single* constraint.

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

That namespace, `chalkline.chelseakr.com`, does not resolve. What CTDL and linked-data
practice expect of an `@id`, what breaks while the host stays unresolved, and the options for
changing it are laid out in [docs/IDENTIFIERS.md](docs/IDENTIFIERS.md). Nothing has been
registered, deployed, or published; that document is a recommendation for the owner to decide
on.
