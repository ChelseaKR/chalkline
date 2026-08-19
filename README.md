# Chalkline

California educator credential authorizations, modeled onto
[CTDL](https://credreg.net/ctdl/handbook) and published as JSON-LD plus a small browsable
page.

> **Unofficial.** Chalkline is not affiliated with, endorsed by, or published by the
> California Commission on Teacher Credentialing or by Credential Engine. It models
> information the Commission publishes on its public Authorization Sort Table, to
> demonstrate what a machine-readable representation of California educator credentials
> could look like. **Nothing here has been published to the Credential Registry**, in
> production or in a sandbox, and the CTIDs in this repository are not Registry-assigned.

**Status:** Beta. Version `0.1.0`, first signed tag not yet cut. 133 authorizations and
twelve credential leaflets are modeled, tested, and published as JSON-LD. This is one worked
example, not a complete representation of California educator credentials.

## What this is

The Commission on Teacher Credentialing publishes its credential authorizations as an HTML
table and its credential leaflets as web pages. There is no machine-readable representation
of California educator credentials yet. This repository is one worked example of what such a
representation could look like if it existed, built only from what the Commission already
publishes.

From the Commission's Authorization Sort Table, retrieved 2026-08-07, and nineteen of its
credential leaflets, retrieved 2026-08-07 and 2026-08-19:

| | |
|---|---|
| Rows published in the sort table | 553 |
| Authorizations in those rows | 136 |
| Modeled as `ceterms:License` | 133 |
| Excluded, each with a recorded reason | 3 |
| Subject alignments emitted | 1,014 |
| Of those, supplied by following a published cross-reference | 538 |
| Authorizations carrying `ceterms:description` | 53 |
| Authorizations carrying requirements or renewal terms | 15 |
| `ceterms:ConditionProfile` nodes emitted | 36 |
| Authorizations linked to a CTC leaflet | 22 |
| Leaflet pages vendored | 19 |
| Of those, retrieved and attached to nothing | 7 |

Output lives in [`site/`](site/): [`credentials.jsonld`](site/credentials.jsonld) is the
graph, [`coverage.json`](site/coverage.json) is a coverage statement counted from that graph
at build time, and [`index.html`](site/index.html) is the browsable page. All three are
committed, and `chalkline check` fails if they are not byte-for-byte what the current code
produces from the current sources.

## The model, in one paragraph

One `ceterms:License` per authorization, because CTDL defines a License as a credential
"awarded by a government agency ... that constitutes legal authority to do a specific job",
which is what a California teaching credential is. One `ceterms:CredentialOrganization` for
the Commission, which every license names with `ceterms:ownedBy`. Each authorized subject
becomes a `ceterms:CredentialAlignmentObject` under `ceterms:subject`, carrying the
Commission's subject code, subject name, and row notes. California rides
`ceterms:regulatedIn` as a `ceterms:JurisdictionProfile`. The Commission's own document and
authorization codes ride `ceterms:identifier`, because `ceterms:codedNotation` turns out not
to be in the domain of `ceterms:License`. Where a leaflet states requirements or renewal
terms under a heading this project can classify, they ride `ceterms:requires` and
`ceterms:renewal` as `ceterms:ConditionProfile` nodes named with the Commission's own heading.

Every class choice, every rejected alternative, and one apparent gap in CTDL itself are
written up in [docs/MODELING.md](docs/MODELING.md). The `@id` host does not resolve, and
[docs/IDENTIFIERS.md](docs/IDENTIFIERS.md) lays out what that costs and what the options are;
nothing has been registered, and the `@id` namespace itself is not served anywhere.

The decisions themselves are recorded as numbered, superseded-not-edited records in
[docs/adr/](docs/adr/), which cite those two documents rather than restating them.

## Two things a CTDL reader will want to check first

**The CTIDs follow the spec.** credreg.net says a CTID is "a standard UUID v4 prefixed with
`ce-`", and v4 means random, which is the one thing a deterministic re-export cannot be. The
usual workaround is to derive a UUIDv5 from a namespace and a key. This project does not take
it. The identifiers here are real UUIDv4s, minted once by `chalkline mint-ctids` and
committed to [`data/ctid-ledger.json`](data/ctid-ledger.json). Re-export is idempotent
because the ledger is in version control, which is the same reason a registry's CTIDs are
stable: somebody wrote them down. `tests/test_ctid.py` pins the grammar, including the
version nibble and variant bits.

You do not have to take that on this repository's word. `make verify` runs
[`ctdl-validate`](https://github.com/ChelseaKR/ctdl-validate), an independently written
structural checker for CTDL JSON-LD, over the committed graph, and the gate fails if it
reports anything. It checks a different rule family from this project's own validator — CTID
grammar, identifier kinds, reference targets, class pairings, each finding citing the
published rule it came from — so neither tool subsumes the other, and the interesting outcome
is a disagreement rather than a pass. Today it reports `0 findings` on all 134 entities. It
makes no network calls, so the gate stays offline.

**The modeling is checked against a fetched schema, not against memory.** The full CTDL
schema encoding is vendored with its retrieval hash, and every emitted document is validated
for four things before anything is written: the class exists, the property exists and is
declared in the context, the property's `schema:domainIncludes` admits the class it is used
on, and the value fits the declared range. That domain check is not decorative. It is what
caught `ceterms:codedNotation` on a License, and a range check caught `ceterms:postalCode`
being written as a language map when the schema gives it `xsd:string`.

## Scope, and the three exclusions left

An authorization is modeled only where its scope can be read from the sort table itself. The
Subject Code column says one of three things, and all three are read literally: a subject
code, the literal string `NONE` (which is a statement that the authorization is not
subject-coded, not a gap), or nothing at all.

Eight rows in the third case carry a Commission note pointing at another credential's rows in
the same table. All eight references were followed, code by code, against the vendored
artifact, which is what took the modeled count from 125 to 133 and added 538 subject
alignments. Exactly which rows supplied which subjects is recorded in
[PROVENANCE.md](PROVENANCE.md) and printed on the browsable page beside each resolved
credential. A reference this project could not follow would stay excluded with a reason
naming what was found.

Three authorizations remain unmodeled: two publish "Indicated on Document" and one publishes
nothing at all. No authorization is excluded for want of a name.

## Leaflets

Only 22 of the 133 authorizations have a Commission leaflet attached, and that is the point.
A leaflet is attached on an equality with a string the Commission published, and on nothing
else. Three rules: an exact title match, a title match with one trailing parenthesised
qualifier removed, and a document code the leaflet's own title names in parentheses that is
character-for-character a whole Document Title cell in the sort table.

A leaflet has up to two published titles — the one the Commission's index gives it and the
one the leaflet page gives itself — and the first two rules are applied to both. That is not
a loosening: it is the same equality against the other name the Commission published for the
same document. It matters for exactly one leaflet, and decisively. `CL-902` is indexed as
"The Teaching Permit for Statutory Leave (TPSL)", which matches nothing, and titles itself
"Teaching Permit for Statutory Leave", which is precisely the family base of the two
authorizations the sort table publishes as `Teaching Permit for Statutory Leave (Multiple
Subject)` and `(Single Subject)`.

Prose is read only where the leaflet page's own `<h1>` states the code it was asked for *and*
a title that identified the authorization. Two leaflets fail that, for opposite reasons, and
both keep their link and lose their prose. Ten leaflet pages were read; eighteen
authorizations carry prose from one.

Where a leaflet breaks its requirements out by variant, and heads that breakdown with the
same parenthesised qualifier the Commission put in the authorization's own title, those
requirements are read for that authorization. Six authorizations gain their own variant's
requirements this way. Two do not: their leaflets head that section "Education Specialist:"
where the authorization says "(Special Education)", and deciding those name the same thing
would be this project writing the Commission's key for it. That gap is counted, not closed.

Nineteen leaflet pages are vendored and seven of them are attached to nothing. Each of those
seven was retrieved because its index title was a word or a plural away from an
authorization's, to see what the Commission's own page calls the document; for each of them
the answer did not match either. They are kept because a recorded non-match whose evidence
has been deleted is an assertion rather than a finding.
[`site/coverage.json`](site/coverage.json) counts all of this: the rules that matched, the
strings they matched against, the refusals with their reasons, the variant gaps, and the
headings read past without being classified. [PROVENANCE.md](PROVENANCE.md) names each
leaflet, both of its titles, and why the near misses are still near misses.

## Usage

```bash
uv sync
uv run chalkline build        # write site/ from the vendored sources
uv run chalkline check        # verify committed site/ matches a fresh build
uv run chalkline mint-ctids   # assign CTIDs to any authorization lacking one
```

Nothing above touches the network. `scripts/fetch_sources.py` is the only code in this
repository that opens a socket, it is run by hand, and a test asserts that no module under
`src/chalkline/` imports a networking library at all.

```bash
python scripts/fetch_sources.py                     # the four base artifacts
python scripts/fetch_sources.py leaflets cl-858     # one leaflet page, named explicitly
```

The leaflet mode takes explicit codes rather than walking the Commission's index, so the
request count equals the number of documents actually looked at, and every one of them is
recorded in [PROVENANCE.md](PROVENANCE.md) whether or not it ended up attached. Requests in
one run are spaced two seconds apart. Two leaflets that a near-miss title suggested were
deliberately **not** retrieved, because the authorizations they would describe are excluded
for want of a published scope and no answer could have changed the graph.

```bash
make verify   # lockfile check, lint, typecheck, tests with coverage, build check, CTDL validation
make validate # the independent CTDL validator alone, over the committed graph
make lock     # regenerate uv.lock after changing a dependency; nothing else rewrites it
```

Every target that runs a tool runs it through `uv run --locked`, and `make verify` opens with
`uv lock --check --offline`, so a `uv.lock` that no longer agrees with `pyproject.toml` fails
the gate rather than being silently repaired by it. `make lock` is the one target allowed to
rewrite the lockfile.

## Provenance

Every source, retrieval date, byte count, and sha256 is in [PROVENANCE.md](PROVENANCE.md),
along with every exclusion and every property deliberately not emitted. The Commission's
pages were retrieved with single unauthenticated GETs; robots.txt permits both paths, no bot
protection was encountered, and none was circumvented.

## License

Apache 2.0. The credential data reproduced here is factual information published by a
California state agency; see [PROVENANCE.md](PROVENANCE.md).
