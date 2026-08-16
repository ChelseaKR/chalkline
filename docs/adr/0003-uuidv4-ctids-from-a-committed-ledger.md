# 0003. CTIDs are real UUIDv4s from a committed ledger, not derived UUIDv5s

- **Status:** Accepted
- **Date:** 2026-08-07
- **Deciders:** Chelsea Kelly-Reif

Implementation and the longer argument: `src/chalkline/ctid.py`, `tests/test_ctid.py`,
[`data/ctid-ledger.json`](../../data/ctid-ledger.json).

## Context

credreg.net defines a CTID as "a standard UUID v4 prefixed with `ce-`". Version 4 means
random, and randomness is the one thing a deterministic re-export cannot produce. A build
that must emit the same bytes twice cannot mint a fresh random identifier on each run.

The usual way out is to derive a UUIDv5 from a namespace and a key. It is deterministic, it
needs no state, and it is wrong here: a v5 UUID sets the version nibble to 5, so the result
is not what the specification asks for. It would be an identifier that looks conformant to a
reader and fails the grammar.

## Decision

Mint real UUIDv4s once, with `chalkline mint-ctids`, and commit them to
`data/ctid-ledger.json`. The export refuses to mint during a build; a build either finds an
identifier in the ledger or fails.

Re-export is idempotent because the ledger is in version control, which is the same reason a
registry's CTIDs are stable: somebody wrote them down. `tests/test_ctid.py` pins the grammar
including the version nibble and the variant bits.

## Consequences

The identifiers satisfy the published definition rather than approximating it, and the build
stays reproducible. `chalkline check` can assert the committed `site/` is byte-for-byte what
the code produces, which would be impossible with per-run randomness.

The cost is a state file that must be kept. Losing `data/ctid-ledger.json` means every
identifier in the graph changes, so it is as load-bearing as the source snapshots and is
treated the same way.

These CTIDs are not Registry-assigned and nothing here has been published to the Credential
Registry. What this demonstrates is narrower and still real: a publisher can hold stable,
spec-conformant identifiers for its own inventory before it publishes anything, which is the
position the Commission would be in.
