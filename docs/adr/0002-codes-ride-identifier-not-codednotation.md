# 0002. Commission codes ride `ceterms:identifier`, not `ceterms:codedNotation`

- **Status:** Accepted
- **Date:** 2026-08-07
- **Deciders:** Chelsea Kelly-Reif

Full argument: [`docs/MODELING.md`](../MODELING.md), "Two findings a reader of this repo
should know about".

## Context

The Commission's document codes and authorization codes, such as `R1E`, need a home on the
emitted license. `ceterms:codedNotation` reads like the obvious one: "Set of alpha-numeric
symbols as defined by the body responsible for this resource that uniquely identifies this
resource."

It is not available. The vendored CTDL schema encoding gives `ceterms:codedNotation` a
`schema:domainIncludes` of 17 classes, and `ceterms:License` is not among them. This was not
noticed by reading the handbook. The export wrote `codedNotation` first and the structural
validator rejected it, because the validator checks the domain of every property against the
fetched schema rather than against a memory of it.

## Decision

The codes ride `ceterms:identifier`, whose `ceterms:IdentifierValue` range carries both the
code and the name of the scheme it belongs to. `tests/test_validate.py` pins the domain rule
so the mistake cannot creep back in.

## Consequences

The output carries more information than the rejected form would have, not less: an
identifier states which scheme a code belongs to, where a coded notation would have been a
bare string.

This is one of two findings this repository exists to surface. The other, recorded in the
same section of `docs/MODELING.md`, is that `ceterms:postalCode` takes `xsd:string` while
the address lines around it take `rdf:langString`; the first draft wrote all five address
fields as language maps and the validator caught it.

Both are arguments for validating against a fetched schema with a recorded retrieval hash
rather than against documentation. Neither would have been caught by a reader who was
confident.
