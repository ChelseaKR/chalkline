# Modeling decisions

Why each CTDL class and property here was chosen, and what was rejected. Every claim below
is checked mechanically by `src/chalkline/ctdl/validate.py` against the vendored schema
encoding (`src/chalkline/ctdl/ctdl-schema.json`, retrieved from
<https://credreg.net/ctdl/schema/encoding/json> on 2026-08-07), so the reasoning and the
behavior cannot drift apart. Quoted definitions come from that file.

## What the source is

The Commission on Teacher Credentialing publishes an Authorization Sort Table with six
columns of its own naming: Document Title, Authorization Title, Authorization Code, Subject
Code, Subject, Notes. The page states its own scope: "This table contains credential
authorizations and subjects that the Commission currently authorizes. This list does not
include credential authorizations that the Commission no longer issues."

One row is one (authorization, subject) pair. The vendored snapshot holds 553 rows, which
group into 136 authorizations.

## The unit of modeling

**One authorization is one (Document Title, Authorization Title, Authorization Code)
triple.** All three parts are load-bearing in the real data:

- `R2M` appears under six different authorization titles, on six different documents
  (Multiple Subject Teaching Credential, Teaching Permit for Statutory Leave, Exchange
  Certificated Employee, Short-Term Staff Permit, Provisional Internship Permit, and the
  General Education Multiple Subject Limited Assignment Teaching Permit).
- `R3MN` appears on both the Education Specialist Instruction Credential and the District
  Intern Education Specialist Instruction Credential.
- `SMAB` appears under two different authorization titles on the same document pair.

Keying on the authorization code alone would merge credentials the Commission keeps apart.

## Classes

### `ceterms:License` for every credential and permit

Definition: "Credential awarded by a government agency or other authorized organization that
constitutes legal authority to do a specific job and/or utilize a specific item, system or
infrastructure and are typically earned through some combination of degree or certificate
attainment, certifications, assessments, work experience, and/or fees, and are time-limited
and must be renewed periodically." Term status `vs:stable`.

That is what these documents are. The Commission is a state agency, and every entry in the
table, including the emergency permits and the child development permits, is state-conferred
legal authority to serve in a California public school position. The class is uniform across
all 133 modeled authorizations because the source is uniform in this respect.

**`ceterms:Certification` was considered and rejected.** Its definition is "Time-limited,
revocable, renewable credential awarded by an authoritative body for demonstrating the
knowledge, skills, and abilities to perform specific tasks or an occupation." That describes
the subject-matter examinations and preparation programs *behind* a California credential,
not the credential itself. CTDL's own distinction between the two classes turns on
government-conferred authority, and that is the side these documents fall on.

`ceterms:CertificateOfCompletion` was considered for the single entry titled "Certificate of
Completion of Staff Development" (`SA17` / `S17A`). It is listed in the Authorization Sort
Table as something the Commission authorizes, alongside the credentials and permits, so it
is modeled the same way as its neighbours rather than singled out on the strength of its
name. This is flagged here as the one class choice a reviewer might reasonably reopen.

### `ceterms:CredentialOrganization` for the Commission

Definition: "Organization that plays one or more key roles in the lifecycle of a credential."
The Commission issues and regulates every document in the table, which is that role.

`ceterms:QACredentialOrganization` is the class for the Commission's other role, accrediting
educator preparation programs. This export models no preparation programs, so it asserts no
quality assurance relationship.

### Nested profiles carry no CTID

`ceterms:CredentialAlignmentObject`, `ceterms:JurisdictionProfile`, `ceterms:Place`, and
`ceterms:IdentifierValue` are not independently published resources, and the schema agrees:
`ceterms:ctid` appears in none of their domains. They are emitted as nested nodes without
`@id` or `ceterms:ctid`.

## Properties

| Property | Why |
|---|---|
| `ceterms:name` | The Authorization Title, verbatim. |
| `ceterms:description` | The matched leaflet's own prose where there is one, otherwise the sort table's Notes column where every row of the authorization carries the same list. 51 of 133 qualify. Neither source is composed or paraphrased, and where neither says anything the property is absent. |
| `ceterms:subjectWebpage` | The matched leaflet where one exists, otherwise the sort table. |
| `ceterms:ownedBy` | "Agent with an enforceable claim or legal title to the resource." A state licensing body has exactly that over the credentials it confers. `ceterms:offeredBy` ("Agent that offers the resource") would be true too but says less. |
| `ceterms:regulatedIn` | "Region or political jurisdiction such as a state, province or locale in which the credential ... is regulated." This is precisely the Commission's relationship to these documents. `ceterms:recognizedIn` says something weaker and different (publicly recommended or endorsed), and the broader `ceterms:jurisdiction` would drop the regulatory fact the source establishes. |
| `ceterms:identifier` | The Commission's Document Title codes and Authorization Codes, as `ceterms:IdentifierValue` nodes naming both the code and its scheme. |
| `ceterms:requires` | "Requirement or set of requirements for this resource", range including `ceterms:ConditionProfile`. One profile per leaflet section headed "Requirements…", named with the Commission's own heading. |
| `ceterms:renewal` | "Entity describing the constraints, prerequisites, entry conditions, or requirements necessary to maintenance and renewal of an awarded credential", range `ceterms:ConditionProfile` only. One profile per leaflet section headed with a renewal wording, "Period of Validity", or "Term of the Credential". |
| `ceterms:subject` | Each authorized subject as a `ceterms:CredentialAlignmentObject`, pointing into the sort table as its framework. |
| `ceterms:inLanguage` | `en-US`. The Commission publishes these descriptions in English. |

### Requirements as condition profiles, and why they passed the test the competencies failed

The competency framework was rejected in the first milestone because the sort table publishes
subject names and `ceasn:competencyText` needs a statement of what a person knows or can do.
The leaflets are the other case. Under a heading the Commission wrote as "Requirements for
Issuance", it writes "Possession of a baccalaureate degree or higher from a
regionally-accredited college or university." That is a requirement, stated as one, by the
body that imposes it, and `ceterms:requires` is defined as "Requirement or set of requirements
for this resource" with `ceterms:License` in its domain. Nothing has to be invented for the
property to be true.

The same test rules out three things that were considered:

- **`ceterms:renewalFrequency`.** Its range is `schema:Duration`. The leaflets say "issued for
  five calendar years and must be renewed", which is a sentence, and turning it into `P5Y`
  would be this project parsing prose into a datatype the Commission never wrote. The
  sentence rides `ceterms:renewal` verbatim.
- **The leaflets' "Authorization" sections as structured scope.** They say what a holder may
  be assigned to teach, which is the gap named at the end of this document. CTDL has no
  property for it, so the prose rides `ceterms:description`, which is honestly what it is: an
  "account of the entity". It is not decomposed into anything.
- **Sections under headings this project does not recognise.** They are skipped rather than
  guessed at. `cl-858`'s "Single Subject:" and "Education Specialist:" are almost certainly
  the per-variant requirements for the Single Subject and Special Education Short-Term Staff
  Permits, and "almost certainly" is the whole problem. See `PROVENANCE.md`.

`ceterms:condition` is defined as a "Single constraint, prerequisite, entry condition,
requirement, or cost", singular, so each of the Commission's paragraphs and bullets is one
condition rather than the section being one blob. The context declares the property
`@container: @language`, and JSON-LD admits a list of strings under a language tag, which is
what several conditions in one language look like. The validator was extended to accept that
shape and to keep rejecting everything else, including an empty list.

### Reading a leaflet page: identity before content

A leaflet's prose is used only where the page confirms the identity it was matched under. The
`<h1>` reads `"<title> (<CODE>)"`, and both halves have to agree with the Commission's index.

This is not decorative either. `cl-893` is listed in the index as "American Indian Languages
Credential", which is character-for-character an authorization title in the sort table, and
the page itself is titled "American Indian Languages-Culture Credential". Under an
index-only rule this project would have published a page's requirements against a credential
whose name the page does not use. The two affected authorizations keep the Commission's own
link and get no prose, and the refusal is printed in the coverage statement.

### Two findings a reader of this repo should know about

**`ceterms:codedNotation` is not in the domain of `ceterms:License`.** It reads like the
obvious home for a code like `R1E` ("Set of alpha-numeric symbols as defined by the body
responsible for this resource that uniquely identifies this resource"), and the schema does
not put it on credentials at all: its domain has 17 classes, and `ceterms:License` is not
among them. The codes therefore ride `ceterms:identifier`, whose `IdentifierValue` range
carries both the code and the name of the scheme it belongs to, which is more information
rather than less. `tests/test_validate.py` pins this so the mistake cannot creep back in.

**`ceterms:postalCode` takes `xsd:string` while the address lines around it take
`rdf:langString`.** The first draft of this export wrote all five address fields as language
maps. The validator caught it. That is the case for validating against a fetched schema
rather than against a memory of one.

## What is deliberately not modeled

**`ceterms:occupationType`.** The sort table publishes no occupation codes. Aligning a
teaching credential to an SOC occupation would be this project's judgement, not the
Commission's statement.

**`ceterms:audienceLevelType`.** Grade ranges do appear, as prose in the Notes column
("Grade 9 and Below All Curriculum Levels"). Mapping that prose onto CTDL's audience level
concept scheme would be an interpretation the Commission has not published. The prose itself
is carried verbatim on the subject alignment as `ceterms:targetNodeDescription`, so nothing
is lost, only left uninterpreted.

**A competency framework.** The brief for this repo suggested `ceterms:Competency` for
authorization scopes. Two things ruled it out. First, `ceterms:targetCompetency` is not in
the domain of `ceterms:License`; a credential reaches competencies through
`ceterms:requires` and a `ConditionProfile`, which would say these subjects are *required to
earn* the credential rather than *authorized by* it. That is a different and false claim.
Second, CTDL-ASN competencies need `ceasn:competencyText`, a statement of what a person
knows or can do, and the sort table publishes subject names, not competency statements.
Modeling "Biological Sciences (Specialized)" as a competency would mean writing a skill
statement the Commission never wrote. Subject alignments carry the same information without
the invention.

### An observation worth taking to Credential Engine

CTDL has no property that means "this credential authorizes its holder to be assigned to
teach this subject". `ceterms:subject` is defined as topicality, which is close and is what
this export uses, but a teaching authorization is a narrower and legally operative claim:
it governs what a district may assign a holder to teach. Every state that licenses teachers
has this concept, and modeling it as topicality loses the part that matters to an employer
checking an assignment. This looks like a genuine schema gap rather than a modeling error,
and it is the kind of thing worth raising in the CTDL Advisory Group.

## Scope, cross-references, and exclusions

An authorization is modeled only where its scope can be read from the sort table. The
Subject Code column says one of three things and this project reads all three literally:

1. **A subject code.** Becomes a subject alignment. 59 authorizations directly.
2. **The literal string `NONE`.** A statement, not a gap: the authorization is not
   subject-coded. Becomes an absence of subject alignments plus a recorded flag. 66
   authorizations.
3. **Nothing at all.** The scope lives somewhere this table does not reproduce.

Case 3 splits. Eight of those rows carry a Commission note pointing at another credential's
rows **in this same table**, and following that pointer is reading the source, not inferring
past it. All eight resolve, adding 538 subject alignments and taking the modeled count from
125 to 133.

The two published wordings say different things and are handled differently. "Subject Codes
Same as on X" defers the subject list only, and the deferring row publishes its own
Authorization Code, so each of its codes is looked up under X and that code's subjects are
taken. "Authorization and Subject Codes Same as on X" defers both, and those rows publish no
Authorization Code at all, so X's codes come across with its subjects.

The lookup is exact equality on the published Authorization Title, and it refuses rather than
choosing whenever the reference does not identify one credential: a title no row publishes, a
title published on more than one document, an Authorization Code the named credential does not
carry, or a credential that defers its own scope in turn. A note whose wording is neither of
the two published forms is not treated as a cross-reference at all, so a new wording upstream
leaves the authorization excluded rather than resolved against the wrong rows.

**The referenced rows' Notes do not travel.** The Commission's statement is about subject
codes. Its remark on one credential's row is not a remark about another's.

Three authorizations remain excluded, and none of them for a deferred scope. Two publish
"Indicated on Document" and one publishes nothing at all. Their names are all published and
unambiguous, so no authorization is excluded for want of a name. See
[PROVENANCE.md](../PROVENANCE.md) for the row-by-row record of what supplied what.

## Identifiers

See the module docstring in `src/chalkline/ctid.py`. Short version: CTIDs here are real
UUIDv4s as the published grammar requires, minted once by `chalkline mint-ctids` and
committed to `data/ctid-ledger.json`. Stability comes from the ledger being in version
control, not from deriving the identifier. None of them is Registry-assigned.

The `@id` URIs those CTIDs sit inside point at a host that does not resolve. What that costs,
what CTDL and the Registry actually do with `@id` and CTID, and what the options are is
[docs/IDENTIFIERS.md](IDENTIFIERS.md). It is a recommendation, not a change: resolving the
host means publishing, and that is the owner's decision.
