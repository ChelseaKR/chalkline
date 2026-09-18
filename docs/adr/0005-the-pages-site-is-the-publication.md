# 0005. The GitHub Pages site is the publication

- **Status:** Accepted
- **Date:** 2026-09-18
- **Deciders:** Chelsea Kelly-Reif

## Context

[ADR 0004](0004-leave-the-id-namespace-unresolved.md) kept the `@id` namespace unresolved
because a resolving host would amount to publication, and it reserved publication for the
owner. It closed by recording a question it had not anticipated: `.github/workflows/pages.yml`
already deploys `site/` to `https://chelseakr.github.io/chalkline/`, the deploy is live, and
whether that deploy was the publication decision ADR 0004 reserved was left open (issue #65).

While it stayed open, `docs/IDENTIFIERS.md` reasoned from the premise that nothing had been
deployed or published, and work that grows what the deploy serves (#87, the subject pages;
#88, the dataset descriptor) was parked behind it.

## Decision

The owner confirmed on 2026-09-18: **the live GitHub Pages site is the publication.** What
`pages.yml` serves from `site/` at `https://chelseakr.github.io/chalkline/` is published, on
purpose, and growing it is an ordinary change held to the same gates as the rest of `site/`.

Every published page that quotes the Commission keeps the unofficial notice above the fold
and a link to the Commission's source it quotes, and `tests/test_subjects.py` holds every
subject page to both. Where the source publishes nothing, the page says so rather than
filling the gap.

## Consequences

This is publication on GitHub Pages and nowhere else. Nothing is published to the Credential
Registry, the CTIDs are still not Registry-assigned, and the unofficial notice says both.

It does not change ADR 0004. The `@id` namespace stays where it is and still does not
resolve, because the site is served at a host that is neither that namespace nor ctc.ca.gov.
The third condition `docs/IDENTIFIERS.md` sets, per-CTID routes, is not built. It is tracked
in issue #77, which was gated on this decision and no longer is; until it lands, no `@id`
dereferences, and that is a known gap rather than an oversight.
