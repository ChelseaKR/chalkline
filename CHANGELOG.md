# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- First working milestone: California educator credential authorizations modeled onto CTDL.
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
