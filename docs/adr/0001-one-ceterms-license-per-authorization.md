# 0001. One `ceterms:License` per authorization

- **Status:** Accepted
- **Date:** 2026-08-07
- **Deciders:** Chelsea Kelly-Reif

Full argument and quoted schema definitions: [`docs/MODELING.md`](../MODELING.md), "Classes".

## Context

The Commission on Teacher Credentialing's Authorization Sort Table publishes 553 rows that
group into 136 authorizations. CTDL offers several credential classes that could plausibly
carry them, and the choice determines what the graph claims about the thing.

The unit of modeling is itself a decision. `R2M` appears under six different authorization
titles on six different documents, `R3MN` on two, and `SMAB` under two titles on the same
document pair. Keying on the authorization code alone would merge credentials the Commission
keeps apart.

## Decision

One authorization is one `(Document Title, Authorization Title, Authorization Code)` triple,
and each becomes one `ceterms:License`. The Commission is one
`ceterms:CredentialOrganization`, named by every license through `ceterms:ownedBy`.

`ceterms:License` is CTDL's class for a credential "awarded by a government agency or other
authorized organization that constitutes legal authority to do a specific job", which is
what a California teaching credential is. The class is uniform across all modeled
authorizations because the source is uniform in this respect: every entry in the table,
including the emergency permits and the child development permits, is state-conferred legal
authority to serve in a California public school position.

`ceterms:Certification` was considered and rejected. Its definition describes demonstrating
knowledge, skills and abilities, which fits the subject-matter examinations and preparation
programs behind a California credential rather than the credential itself. CTDL's own
distinction turns on government-conferred authority.

`ceterms:CertificateOfCompletion` was considered for the single entry titled "Certificate of
Completion of Staff Development" and rejected: the table lists it as something the
Commission authorizes, alongside the credentials and permits, so it is modeled like its
neighbours rather than singled out on the strength of its title.

## Consequences

133 licenses are emitted from 136 published authorizations. The three exclusions are
recorded with reasons in `PROVENANCE.md` and none is excluded for want of a name.

Uniformity of class is a claim, and it is the claim most likely to need revisiting if the
Commission ever publishes something in this table that is not state-conferred authority.
Revisiting it means a new ADR superseding this one, not an edit here.
