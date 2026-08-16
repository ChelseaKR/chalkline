# 0004. Leave the `@id` namespace unresolved, and say so

- **Status:** Accepted
- **Date:** 2026-08-07
- **Deciders:** Chelsea Kelly-Reif

Full argument, all three options, and the counted costs:
[`docs/IDENTIFIERS.md`](../IDENTIFIERS.md).

## Context

Every node carrying a CTID also carries an `@id` under
`https://chalkline.chelseakr.com/ctdl/resources/`. That host does not resolve; as of
2026-08-15 it does not exist in DNS. 134 `@id` values dereference to nothing.

Correctness is unaffected. The graph merges, the identifiers are unique and conformant, and
every statement is true whether or not the host answers. What is affected is the fourth
linked-data principle and the impression: a reader who dereferences an `@id` and gets
nothing reads it as unfinished.

`docs/IDENTIFIERS.md` sets out three options. Option 2, pointing the host at a static site,
is the one that keeps the linked-data promise, and it is also the one that amounts to
publishing a page of California credential data that looks authoritative to anyone who lands
on it mid-scroll.

## Decision

Take option 1. Keep `RESOURCE_BASE` as it is, state in the graph and the documentation that
the namespace is a pre-publication identifier for records deliberately not published, and
point readers at `ceterms:subjectWebpage` on ctc.ca.gov, which is emitted on all 133 licenses
and on the organization and does resolve.

The reason is that the host resolving and the records being published are the same decision
rather than two. An `@id` that resolves is a page that exists, and a page that exists is
publication. Standing up a domain so that a URI stops returning nothing would be publication
arrived at through a technical side door rather than chosen.

A registry-shaped URI under `credentialengineregistry.org` is rejected outright and a test
asserts it: those URIs would imply these records exist in the Credential Registry, and a URI
resolving to someone else's 404 is a worse claim than one resolving to nothing.

## Consequences

The cost is one documented line and it is bounded. Nothing in the build depends on the host
resolving, no test fetches it, and `chalkline check` is unaffected.

**One thing this decision did not anticipate, recorded here rather than left to be
discovered.** `.github/workflows/pages.yml` now publishes `site/` to GitHub Pages, and it is
live: `https://chelseakr.github.io/chalkline/` returned HTTP 200 and the same 216,002 bytes
as the committed `index.html` when checked on 2026-08-15, and `credentials.jsonld` is served
alongside it. So a public page of California credential data exists, at a host that is
neither the `@id` namespace nor ctc.ca.gov, while `docs/IDENTIFIERS.md` still reasons from
the premise that nothing has been deployed or published.

Two of the three conditions that document attaches to publishing are already met by that
page: the unofficial statement is above the fold, and the 2026-08-07 retrieval date is
visible. The third, per-CTID routes, is not, which is why no `@id` resolves even now.

This ADR stands as the decision about the `@id` namespace, which is unchanged. Whether the
Pages deploy was the publication decision this document reserved for the owner is a separate
question and it is open.
