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

## What this is

The Commission on Teacher Credentialing publishes its credential authorizations as an HTML
table and its credential leaflets as web pages. There is no machine-readable representation
of California educator credentials yet. This repository is one worked example of what such a
representation could look like if it existed, built only from what the Commission already
publishes.

From the Commission's Authorization Sort Table, retrieved 2026-08-07:

| | |
|---|---|
| Rows published | 553 |
| Authorizations in those rows | 136 |
| Modeled as `ceterms:License` | 125 |
| Excluded, each with a recorded reason | 11 |
| Subject alignments emitted | 476 |

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
to be in the domain of `ceterms:License`.

Every class choice, every rejected alternative, and one apparent gap in CTDL itself are
written up in [docs/MODELING.md](docs/MODELING.md).

## Two things a CTDL reader will want to check first

**The CTIDs follow the spec.** credreg.net says a CTID is "a standard UUID v4 prefixed with
`ce-`", and v4 means random, which is the one thing a deterministic re-export cannot be. The
usual workaround is to derive a UUIDv5 from a namespace and a key. This project does not take
it. The identifiers here are real UUIDv4s, minted once by `chalkline mint-ctids` and
committed to [`data/ctid-ledger.json`](data/ctid-ledger.json). Re-export is idempotent
because the ledger is in version control, which is the same reason a registry's CTIDs are
stable: somebody wrote them down. `tests/test_ctid.py` pins the grammar, including the
version nibble and variant bits.

**The modeling is checked against a fetched schema, not against memory.** The full CTDL
schema encoding is vendored with its retrieval hash, and every emitted document is validated
for four things before anything is written: the class exists, the property exists and is
declared in the context, the property's `schema:domainIncludes` admits the class it is used
on, and the value fits the declared range. That domain check is not decorative. It is what
caught `ceterms:codedNotation` on a License, and a range check caught `ceterms:postalCode`
being written as a language map when the schema gives it `xsd:string`.

## Exclusions

An authorization is modeled only where its scope can be read from the sort table itself. The
Subject Code column says one of three things, and all three are read literally: a subject
code, the literal string `NONE` (which is a statement that the authorization is not
subject-coded, not a gap), or nothing at all. The third case is the only cause of an
exclusion, and there are 11. All 11 are listed with per-item reasons in
[PROVENANCE.md](PROVENANCE.md). No authorization is excluded for want of a name.

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
make verify   # lint, format check, typecheck, tests with coverage, build check
```

## Provenance

Every source, retrieval date, byte count, and sha256 is in [PROVENANCE.md](PROVENANCE.md),
along with every exclusion and every property deliberately not emitted. The Commission's
pages were retrieved with single unauthenticated GETs; robots.txt permits both paths, no bot
protection was encountered, and none was circumvented.

## License

Apache 2.0. The credential data reproduced here is factual information published by a
California state agency; see [PROVENANCE.md](PROVENANCE.md).
