# Security

## Reporting

Report suspected vulnerabilities privately through GitHub's
[private vulnerability reporting](https://github.com/ChelseaKR/chalkline/security/advisories/new).
Please do not open a public issue for a security problem. Expect an acknowledgement within
seven days.

## Scope

Chalkline is an offline data project. It has no server, no database, no authentication, and
no runtime dependencies. It reads vendored files and writes files. The realistic risk surface
is small and worth naming precisely:

- **Untrusted input parsing.** The HTML parsers read vendored snapshots of public pages. A
  malicious snapshot could in principle drive pathological regex behaviour. Snapshots are
  committed and hash-checked, so a change to one is visible in review.
- **Output escaping.** The generated page escapes all source-derived text. A test asserts
  that markup arriving through source data is escaped rather than rendered.
- **Supply chain.** There are no runtime dependencies. Development dependencies are pinned
  through `uv.lock`, updated by Dependabot with a seven-day cooldown, and audited by
  `pip-audit` in CI. Every GitHub Action is pinned to a full commit SHA.

## What this project will not do

It will not publish to the Credential Registry, and it will not circumvent bot protection or
access controls on any source site. Both are deliberate constraints, not oversights, and a
change proposing either will be declined.
