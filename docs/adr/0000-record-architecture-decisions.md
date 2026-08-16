# 0000. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-08-15
- **Deciders:** Chelsea Kelly-Reif

## Context

Every modeling choice in this repository was already argued in prose before this log
existed. `docs/MODELING.md` gives the class and property choices with their rejected
alternatives; `docs/IDENTIFIERS.md` gives the `@id` question with three options and a
recommendation; `PROVENANCE.md` records every source, exclusion, and property deliberately
not emitted. The reasoning was written down. What was missing was a form in which a single
decision can be cited, dated, and superseded on its own.

That distinction matters here more than it would elsewhere. This project's argument is that
its outputs can be checked against something. A prose document that is edited in place
cannot be checked against anything, because the version that justified a past choice is gone
the moment the choice changes. A numbered record that is superseded rather than rewritten
keeps both.

DOCUMENTATION-STANDARD §3 (DOC-04, DOC-05) asks for this as `docs/adr/` with sequential,
immutable records.

## Decision

Architecture decisions are recorded here as Markdown files named `NNNN-kebab-title.md`,
numbered from 0000 and never renumbered. Each carries Status, Date, Deciders, Context,
Decision, and Consequences.

Status is one of `Proposed`, `Accepted`, `Superseded by NNNN`, or `Deprecated`. An Accepted
ADR is not edited to say something different. It is superseded by a later one that says what
changed and why, and its own Status line is updated to point at the successor. That is the
only permitted change to an accepted record.

The ADRs seeded alongside this one restate decisions already argued at length in
`docs/MODELING.md` and `docs/IDENTIFIERS.md`. They are deliberately short and they cite
those documents rather than copying them. The long-form reasoning stays where it is; the ADR
is the citable, dated handle on it.

## Consequences

A decision now has one place to be reversed, and reversing it leaves a trail. The cost is
duplication of a kind: a reader can find the License class argument in two places. The
duplication is bounded by keeping ADRs to the decision and the reason, and pointing at
`docs/MODELING.md` for the evidence.

Nothing enforces immutability yet. DOC-05 asks for CI that forbids content changes to an
Accepted ADR, and this repository has no such check. Until it exists, immutability here is a
convention rather than a gate, and this paragraph is the honest statement of that.
