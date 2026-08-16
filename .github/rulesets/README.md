# Rulesets

`main.json` is the branch-protection posture this repository intends for `main`, committed
so it is reviewable in the tree rather than existing only as a setting nobody can see in a
diff. CI-CD-STANDARD §5 asks for exactly that: "Branch protection is enforced through a
repository-owned GitHub Ruleset named `protect-main` and committed as a per-repo artifact so
the posture is reviewable in-tree."

## It is not applied yet

Checked 2026-08-15:

| Query | Result |
|---|---|
| `gh api repos/ChelseaKR/chalkline/rulesets` | `[]` |
| `gh api repos/ChelseaKR/chalkline/branches/main` | `"protected": false` |
| `gh api repos/ChelseaKR/chalkline/branches/main/protection` | 404, Branch not protected |

Applying it is a repository setting and a deliberate act by the owner, not something a
change to this directory performs. Committing the file does not enforce it, and this README
exists so nobody reads the file's presence as evidence that it is in force.

## What it covers, and what it deliberately does not

`main.json` carries three rules: `deletion`, `non_fast_forward`, and `required_status_checks`
naming `verify`, `audit`, `secret-scan` and `sast`. Those are the four job names in
`.github/workflows/ci.yml` as they stand, and they are the whole of what this repository can
require today without requiring a check that does not exist. A required context that never
reports is a branch nothing can merge to.

The full profile in `CI-CD-STANDARD.md` §5 has three more rules, and each is left out for a
stated reason rather than an oversight:

- **`required_signatures`.** Left out as an ordering choice, not because of a lockout risk.
  Re-measured against the API on 2026-08-15: of the 23 commits on `main`, 19 report
  `verification.verified: true` and 4 report `unsigned`. All four unsigned ones are dated
  2026-08-08 and are the oldest on the branch; every maintainer commit after that date is
  signed, as is every Dependabot commit. The rule governs commits being pushed rather than
  history already merged, so enabling it would not lock the maintainer out. An earlier draft
  of this bullet said no maintainer commit was signed. That came from reading `git log %G?`
  locally, which reports `N` for every SSH-signed commit while `gpg.ssh.allowedSignersFile`
  is unset, and it is unset on this workstation. Local `N` and GitHub `verified` answer
  different questions. Whether to turn the rule on is still the owner's call.
- **`required_linear_history`.** `main` already contains merge commits from PRs #1 and #2.
  The rule only governs future merges, so this is safe to add alongside
  `allowed_merge_methods` of squash and rebase, but it is a workflow decision rather than a
  safety one.
- **`pull_request`.** Adding it means every change to `main` goes through a pull request,
  including one-line fixes. That is the standard's position and probably the right one; it
  is still a change to how the owner works, so it is hers to make rather than one to slip in
  under a security heading.

Also missing, and the reason `automation/check_ruleset_profile.py` would reject this file as
a solo profile: that validator requires a `solo-governance` status check, and no such job
exists here. Standing up an attestation job only so a validator passes would be the same
kind of empty gate this file is trying to correct.

## Applying it

The file is in the shape the REST API accepts, so it can be posted as-is by the owner:

`gh api repos/ChelseaKR/chalkline/rulesets -X POST --input .github/rulesets/main.json`

Confirm afterwards that `gh api repos/ChelseaKR/chalkline/rulesets` returns it and that
`gh api repos/ChelseaKR/chalkline/branches/main` reports `"protected": true`, then update
the header of `.github/workflows/ci.yml`, which currently states that nothing is enforced.

`outcome-receipts/.github/rulesets/main.json` is the portfolio's reference for a complete
committed profile. `ledger` has a live and working `protect-main` ruleset but no committed
artifact, which its own `DEFINITION_OF_DONE.md` records as an open gap.
