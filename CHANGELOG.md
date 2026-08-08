# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Cross-reference resolution in the domain model. The eight authorizations whose Subject Code
  column is empty and whose Notes defer to another credential are now resolved by following
  that reference row by row against the vendored table. Modeled authorizations go from 125 to
  133, exclusions from 11 to 3, and subject alignments from 476 to 1,014. Each resolution
  records the note, the credential it names, and the referenced Authorization Codes with the
  number of subjects each supplied.
- Leaflet page source (`chalkline.sources.leaflet_pages`) reading the Commission's leaflets as
  the web pages they are served as, and refusing any page whose own heading does not state the
  code and title the Commission's index gave it.
- Attachment policy (`chalkline.attachment`) deciding which leaflet describes which
  authorization and what may be read from it, with every refusal recorded.
- A second leaflet matching rule: an authorization title that is a leaflet title plus one
  trailing parenthesised qualifier. Six more authorizations matched, 18 in total.
- `ceterms:requires` and `ceterms:renewal` as `ceterms:ConditionProfile` nodes built from
  leaflet sections, on 13 and 7 licenses respectively; 22 condition profiles in all.
- `ceterms:description` from leaflet prose where a leaflet was read, outranking the sort
  table's Notes column. Descriptions go from 37 to 51.
- Ten vendored leaflet snapshots under `data/source/leaflets/`, each with a provenance
  sidecar, plus tests asserting they are exactly the leaflets the matcher asks for and that
  each is one the Commission's index publishes.
- `scripts/fetch_sources.py leaflets <code>…` for retrieving named leaflet pages.
- `docs/IDENTIFIERS.md`: what CTDL and linked-data practice expect of an `@id`, what the
  unresolved `chalkline.chelseakr.com` host costs, the options, and a recommendation. Nothing
  registered, deployed, or published.

- California educator credential authorizations modeled onto CTDL, the first milestone.
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

### Changed

- The validator accepts a list of strings under a language tag, which is what JSON-LD's
  `@container: @language` allows and what `ceterms:condition` needs in order to state several
  conditions. An empty list is still rejected.
- The coverage statement counts condition profiles, resolved scopes, which rule matched each
  leaflet, how many leaflet pages were read and refused, and every leaflet heading that
  reading skipped.
- The browsable page shows descriptions, requirements, and renewal terms where present, names
  where each description came from, prints the cross-reference behind every resolved scope,
  and states plainly where a description or a condition is absent.
