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

Plus nineteen leaflet pages under `data/source/leaflets/`, each retrieved from
`https://www.ctc.ca.gov/credentials/leaflets/<code>/`. Both titles are recorded because both
are load-bearing: a leaflet is attached where either equals an authorization's published
title, and a page is read only where its own title is one that did.

| Leaflet | Title in the Commission's index | Title on the page itself | Retrieved | Bytes | sha256 |
|---|---|---|---|---|---|
| `cl-380` | School Nurse Services Credential | School Nurse Services Credential | 2026-08-07 | 92,774 | `62973ee1…f8dc99` |
| `cl-501` | Exchange Credential | Exchange Certificated Employee Credential | 2026-08-19 | 87,821 | `f48f4273…2fea30` |
| `cl-529` | Specialist Instruction Credentials | Specialist Instruction Credentials | 2026-08-19 | 92,964 | `d0bd2c1d…50e7ee` |
| `cl-537` | Reading and Literacy Leadership Specialist Credential | Reading And Literacy Leadership Specialist Credential | 2026-08-19 | 91,416 | `2e058586…e5f0c3` |
| `cl-562` | Teacher Librarian Services Credential | Teacher Librarian Services Credential | 2026-08-07 | 92,744 | `e363620f…785e56` |
| `cl-625` | Resource Specialist Added Authorization | Resource Specialist Added Authorization | 2026-08-07 | 94,052 | `90892ef0…e387db` |
| `cl-628b` | Bilingual Authorizations | Bilingual Authorizations | 2026-08-19 | 111,123 | `11a8aab3…93617e` |
| `cl-797` | Child Development Permits | Child Development Permits | 2026-08-19 | 115,619 | `85ceacc4…42c71d` |
| `cl-812` | Reading and Literacy Added Authorization | Reading and Literacy Added Authorization | 2026-08-07 | 88,048 | `b5d2e33c…204d5e` |
| `cl-824` | Certificate of Completion of Staff Development | Certificate of Completion of Staff Development | 2026-08-07 | 84,613 | `970801b3…013a6b` |
| `cl-828` | General Education Limited Assignment Teaching Permit | General Education Multiple and Single Subject Limited Assignment Teaching Permits | 2026-08-19 | 90,562 | `e4ec4d6b…f755e6` |
| `cl-856` | Provisional Internship Permit | Provisional Internship Permit | 2026-08-07 | 97,856 | `b5d411d2…c78992` |
| `cl-858` | Short-Term Staff Permit | Short-Term Staff Permit | 2026-08-07 | 96,347 | `53362652…9bcebc` |
| `cl-879` | Speech-Language Pathology Services Credential | Speech-Language Pathology Services Credential | 2026-08-07 | 119,415 | `a92e6307…b83bca` |
| `cl-889` | Special Education Limited Assignment Permit | Special Education Limited Assignment Permit | 2026-08-19 | 97,120 | `d2ad5623…d60756` |
| `cl-893` | American Indian Languages Credential | American Indian Languages-Culture Credential | 2026-08-07 | 86,939 | `ff04bc21…8437e3` |
| `cl-898` | Mathematics Instructional Leadership Specialist Credential (MILS) and Mathematics Instructional Added Authorization (MIAA) | Mathematics Instructional MILS and MIAA | 2026-08-19 | 90,849 | `5c51b1e6…fd1962` |
| `cl-902` | The Teaching Permit for Statutory Leave (TPSL) | Teaching Permit for Statutory Leave | 2026-08-19 | 94,943 | `545cc6ea…41d1b0` |
| `cl-909` | Emergency Specialist Teaching Permit in Early Childhood Education | Emergency Specialist Teaching Permit in Early Childhood Education | 2026-08-07 | 88,526 | `ddbd722e…a9131e` |

Twelve of the nineteen are attached to an authorization. The other seven were retrieved and
are attached to nothing, and they are kept deliberately. Each was fetched because the
Commission's index titled it within a word or a plural of an authorization this project
models, on the possibility that the page's own title was the authorization's; for each of
these seven it was not. Those are findings, and a finding whose evidence has been deleted is
just an assertion, so the snapshot stays and its sidecar says which it is. `cl-504`
(Eminence) and `cl-568` (Sojourn) were **not** retrieved at all: the authorizations they
would plausibly describe are both excluded for want of a published scope, so nothing about
them could change the graph, and a request that cannot change an answer is not worth making.

| Leaflet | Its index title | The authorization it plausibly describes | What its own page calls it | Why it is still not attached |
|---|---|---|---|---|
| `cl-537` | Reading and Literacy Leadership Specialist Credential | Reading and Literacy Leadership Specialist | the same as the index | The Commission's own page confirms the index. The two names differ by "Credential", and neither source says they are the same document. |
| `cl-529` | Specialist Instruction Credentials | Specialist Instruction Credential | the same as the index | Singular against plural, confirmed on the page. A plural naming a family is not the name of a member. |
| `cl-628b` | Bilingual Authorizations | Bilingual Authorization | the same as the index | Singular against plural, confirmed on the page. |
| `cl-889` | Special Education Limited Assignment Permit | Special Education Limited Assignment Teaching Permit | the same as the index | One word apart, confirmed on the page. |
| `cl-797` | Child Development Permits | the six Child Development permits | the same as the index | A plural naming a family the Commission does name individually, in the sort table, and does not name individually here. |
| `cl-501` | Exchange Credential | Exchange Certificated Employee Teaching Credential | Exchange Certificated Employee Credential | The page's own title is closer than the index's and still not equal: "Teaching" separates them. |
| `cl-828` | General Education Limited Assignment Teaching Permit | General Education Single Subject Limited Assignment Teaching Permit, and the Multiple Subject one | General Education Multiple and Single Subject Limited Assignment Teaching Permits | The page names both authorizations at once, in one plural title, and equals neither. |

Each of these would still be a guess. A leaflet matched by guesswork is worse than no
leaflet, because the prose it carries is then attributed to a document that may not be the
one it describes. What has changed is that six of the seven near misses are now refused on
the Commission's own second statement of the name rather than on its first alone.

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
| Authorizations carrying `ceterms:description` | 53 |
| Of those, described in a Commission leaflet | 18 |
| Authorizations carrying `ceterms:requires` | 15 |
| Authorizations carrying `ceterms:renewal` | 9 |
| `ceterms:ConditionProfile` nodes emitted | 36 |
| Authorizations linked to a CTC leaflet | 22 |
| Of those, carrying requirements the leaflet states for their own variant | 6 |
| Leaflet pages read | 10 |
| Leaflet pages refused on identity | 2 |
| Leaflet pages vendored | 19 |
| Of those, retrieved and attached to nothing | 7 |
| Leaflets in the Commission's index | 81 |
| Index rows redirecting a retired document code | 8 |
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

A leaflet is attached to an authorization on an equality with a string the Commission
published, and on nothing else. Three rules, tried in this order:

1. **Exact title**, after case and punctuation normalization. 12 authorizations.
2. **Named family**: the authorization's title is a leaflet's title followed by one trailing
   parenthesised qualifier, and the part before it equals that leaflet's title under the same
   normalization. 8 authorizations: the three Short-Term Staff Permit variants (`cl-858`), the
   three Provisional Internship Permit variants (`cl-856`), and the two Teaching Permit for
   Statutory Leave variants (`cl-902`). Rule 1 is tried first, so an authorization with a
   leaflet of its own is never rolled up into a family one.
3. **Document code**: a parenthesised run in the leaflet's own published title is, character
   for character, a whole Document Title cell in the sort table. 2 authorizations, both of
   them the Mathematics Instructional Leadership Specialist, whose leaflet `cl-898` is titled
   "… Specialist Credential (MILS) and … Added Authorization (MIAA)" and whose Document Title
   cell is `MILS`. This is the Commission naming the document in its own key, which is a
   stronger statement than a name; it is also not a title, which is why it attaches a link and
   never any prose.

Rule 2 is still an equality. It is not a prefix rule: `Education Specialist Instruction
Credential Requirements for Teachers Prepared Outside of California` (`cl-808`) matches
nothing, because what separates it from `Education Specialist Instruction Credential` is not
a trailing parenthetical. Rule 3 requires the *whole* Document Title cell: a cell reading
`TC1, TC2` lists two documents, and a leaflet naming one of them says nothing about a row
that carries both.

Rules 1 and 2 are applied twice, because a leaflet has up to two published titles: the one
the Commission's index gives it, and the one the leaflet page gives itself in its `<h1>`.
Usually these are the same string. Where they differ, both are still the Commission's name
for that document. `cl-902` is the case that matters: the index calls it "The Teaching Permit
for Statutory Leave (TPSL)", which matches nothing, and the page calls it "Teaching Permit
for Statutory Leave", which is exactly rule 2's base for the two modeled TPSL
authorizations. Reading the second title is not a loosening of the rule; it is the same
equality applied to the other name the Commission published.

22 of 133 authorizations match a leaflet; 111 do not. That ceiling is low, and it is low
because the Commission's leaflet titles and its sort-table authorization titles are written
independently and mostly do not agree. The remaining near misses are named in **Sources**
above, together with what each leaflet's own page calls itself, because that second title is
now evidence rather than an assumption: six of the seven were refused on the Commission's own
confirmation of its first name, not merely on the absence of a second.

Each of them would still be a guess. A leaflet matched by guesswork is worse than no leaflet,
because the prose it carries is then attributed to a document that may not be the one it
describes.

### The index publishes a title only on a leaflet's own row

The leaflet index is a three-column table: the linked title, the Commission's document code,
and a category. It also carries a redirection row for each retired document, pointing at the
leaflet that replaced it, with the retired code in the code column and a sentence where a
title would go: "CL-740 has been replaced by CL-828." There are 8 such rows, covering 6
leaflets, and the Commission prints all of them **above** the leaflet's own row.

This project used to read only the link and its text, taking the first non-empty text for a
path. So all six of those leaflets were published under a sentence about a document that no
longer exists, and their real titles were never read at all:

| Leaflet | Title this project published | Title the Commission publishes |
|---|---|---|
| `cl-533o-clad-bl` | CL-533o has been replaced by CL-533o-CLAD-BL | Crosscultural, Language and Academic Development (CLAD) and Bilingual Authorization Permits - EMERGENCY PERMITS |
| `cl-697b` | CL-697a has been replaced by CL-697b | Designated Subjects Adult Education Teaching Credentials (Based on AB 1374 - Issued on or after January 1, 2011) |
| `cl-760ge` | CL-760 has been replaced by CL-760GE | Commission Appeals For General Education Teaching Credentials (Multiple and Single Subject) |
| `cl-828` | CL-740 has been replaced by CL-828. | General Education Limited Assignment Teaching Permit |
| `cl-888` | CL-620a has been replaced by CL-888 | Career Technical Education Teaching Credential - Designated Subject Based on SB 1104 - Issued on or after January 1, 2009 |
| `cl-892` | CL-765 has been replaced by CL-892 | Military Service |

A row that publishes no title is not a title, so a leaflet's title is now taken from the row
whose code column names the code its own link path names. None of the six changes a match:
none of the recovered titles equals an authorization's under any of the three rules. What it
changes is that the count of 81 leaflets is 81 leaflets with names, rather than 75 with names
and 6 labelled with a notice about something else. The 8 redirection rows are counted
separately in `site/coverage.json`.

### Reading

A matched leaflet's prose is read only where the leaflet page states its own identity, and
that is now two separate questions.

**The code must be the code.** The `<h1>` reads `"<title> (<CODE>)"`, and the code must be
the leaflet that was asked for. A snapshot whose page calls itself another document is the
wrong file, and the parser refuses it outright. No vendored snapshot fails this.

**The page's own title must be one of the titles that identified the authorization.** This is
the check that used to be "the page agrees with the index", and that wording was too blunt to
survive `cl-902`. Matching on the index's title requires the page to agree with the index;
matching on the page's own title satisfies the check by construction; matching on a document
code is not a title match at all and never permits a read.

**Two leaflets are refused, and they are opposite cases.** `cl-893` is listed in the index as
"American Indian Languages Credential" — exactly the title of the two authorizations that
match it — and titles itself "American Indian Languages-Culture Credential". The sort table
publishes *both* `AIL` and `AILC` as document codes, so the page's own name may well be the
other document's; the two authorizations keep the leaflet link and get no prose. `cl-898` is
matched by its document code alone, and its page titles itself "Mathematics Instructional
MILS and MIAA", which is not the authorization's published title and names two documents at
once; same outcome, different reason. Both refusals are recorded in `site/coverage.json` with
their reasons and printed on the browsable page.

So: 22 authorizations matched, 12 distinct leaflets, 10 pages read, 2 refused, and 18
authorizations carrying leaflet prose.

### Variant sections

A leaflet matched by the named-family rule was matched by setting aside a parenthesised
qualifier the Commission wrote in the authorization's own title. Where that leaflet's
requirements contain a sub-section headed with that same qualifier, the Commission has stated
the requirements for that variant, and this project reads them for that authorization only.

The equality is the same normalized title comparison the matcher uses, and the nesting is
read from the Commission's own outline: a sub-heading counts only where it sits inside a
section this project classified as requirements, by heading level. A sub-heading of the same
words under a validity heading is not requirements and is not read.

| Leaflet | Its breakdown | Qualifier it matches | Outcome |
|---|---|---|---|
| `cl-858` | Single Subject: / Multiple Subject: / Education Specialist: | (Single Subject), (Multiple Subject) | Two of three variants read |
| `cl-856` | Single Subject: / Multiple Subject: / Education Specialist: | (Single Subject), (Multiple Subject) | Two of three variants read |
| `cl-902` | Single Subject / Multiple Subject / Special Education | (Single Subject), (Multiple Subject) | Both modeled variants read |

6 authorizations carry requirements the leaflet states for their own variant. **Two do not,
and that is the point.** `Short-Term Staff Permit (Special Education)` and
`Provisional Internship Permit (Special Education)` get only the requirements common to the
permit, because their leaflets head that breakdown "Education Specialist:" and deciding that
"Education Specialist" and "Special Education" name the same variant would be this project
writing the Commission's key for it. The gap is counted in
`leaflets.variant_qualifiers_no_heading_states` and printed on the page beside those two
credentials, rather than closed by inference. `cl-902` heads its third breakdown "Special
Education", which does match — and the authorization it would serve is one of the three the
sort table gives no publishable scope, so it is excluded for that reason and gains nothing
here.

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

That is deliberately blunt, and it still costs real content. The one place it has been
narrowed is the variant breakdown described above: a sub-heading that is not a section kind
but *is* the qualifier the Commission put in the authorization's own title now contributes to
that authorization, because both strings are the Commission's and the test between them is an
equality. Everything else unclassified is still skipped and still counted.

`headings_read_past_but_not_classified` counts a heading per authorization that passed over
it, not per page. "Single Subject:" is unclassified on `cl-858`'s page and is read for the
authorization titled "(Single Subject)", so counting it against that authorization would
report a heading as skipped by the very credential that used it.

### What the leaflets supplied

| Property | From what |
|---|---|
| `ceterms:description` | The leaflet's prose between its title and its first heading, plus the text of an `Authorization` section where the leaflet heads one. Both are "a statement, characterization or account of the entity", which is CTDL's definition. Where a leaflet supplied nothing, the sort table's Notes column stands as before. |
| `ceterms:requires` | One `ceterms:ConditionProfile` per requirements section, named with the Commission's own heading, followed by the variant section where the leaflet states one under this authorization's own qualifier. |
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

**Leaflet links.** A leaflet is attached only by an equality with a string the Commission
published, under the three rules above. No prefix matching, no keyword overlap, no reasoning
from a document code to a leaflet number, no similarity score. Rule 3 reads a document code
out of a leaflet title and compares it to the sort table's own Document Title cell; it does
not reason from `CL-898` to anything, and it does not reason from a code to a name. That
matches 22 of 133 authorizations. The other 111 link to the sort table, which is the page
that does describe them.

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
