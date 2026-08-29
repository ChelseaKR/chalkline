# Rulesets

`main.json` is the branch-protection posture this repository intends for `main`, committed
so it is reviewable in the tree rather than existing only as a setting nobody can see in a
diff. CI-CD-STANDARD §5 asks for exactly that: "Branch protection is enforced through a
repository-owned GitHub Ruleset named `protect-main` and committed as a per-repo artifact so
the posture is reviewable in-tree."

It is currently stale in one field: `bypass_actors`. See the section below before re-applying
it.

## Applied and verified, 2026-08-21

Posted via `gh api repos/ChelseaKR/chalkline/rulesets -X POST --input .github/rulesets/main.json`
(recreated once, at ruleset id `21156701`, after a PATCH attempt against the first posting
404'd for reasons that look like a `gh` CLI/API quirk rather than anything about the ruleset
itself -- DELETE then POST again worked cleanly).

| Query | Result |
|---|---|
| `gh api repos/ChelseaKR/chalkline/rulesets` | one active `protect-main` ruleset, `current_user_can_bypass: "never"` |
| `gh api repos/ChelseaKR/chalkline/branches/main` | `"protected": true` |

Not taken on the API response's word: a throwaway PR (#29) carried a deliberately failing
test so `verify` would go red for real. With `verify` red, `gh pr merge` was refused
("the base branch policy prohibits the merge") and `mergeStateStatus` read `BLOCKED`. The PR
was closed unmerged and its branch deleted. `portfolio-standards/automation/conformance_check.py
--repo` also reports `branch_protection_effective: PASS` against the live repository.

## The owner bypass is intended, and `main.json` is the file that is out of date

Recorded 2026-08-26, re-read 2026-08-28. The live ruleset and `main.json` disagree about the
bypass posture, and nothing about the required checks. **The live posture is the correct one.**

| Query | Result, 2026-08-28 |
|---|---|
| `gh api repos/ChelseaKR/chalkline/rulesets/21156701 --jq .bypass_actors` | `[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]` |
| `... --jq .current_user_can_bypass` | `"always"` |
| `... --jq .updated_at` | `2026-08-26T21:27:29.806-07:00` |
| `... --jq .rules` | unchanged: `deletion`, `non_fast_forward`, and the same six required contexts, `strict_required_status_checks_policy: true` |

The admin bypass was added deliberately, on 2026-08-26, and the owner has confirmed it. It
stays. The reason is not hypothetical: an agent once removed an admin bypass from another
repository and locked the owner out of it, with no path back in that did not go through
support. A role-level `always` bypass is the way back in when a required check is wedged, a
runner is unavailable, or an automated change makes the branch unmergeable by anyone.

So this section records a documentation defect, not a configuration one. Every required check
is still required and still strict; what changed is that the ruleset can now be bypassed by
the repository role holding `actor_id: 5`, where on 2026-08-21 it could not be bypassed by
anyone. `main.json` still declares `"bypass_actors": []` and is simply stale, and three places
asserted "not even an administrator can override it": the 2026-08-21 table above, the `ci.yml`
header, and the `CHANGELOG.md` entry for #30.

The `ci.yml` header has been corrected to state the live posture. **The `CHANGELOG.md` entry
has not been touched**, because that entry is a record of what #30 did on the day it did it;
the change of posture belongs in a new entry, which is the owner's to write rather than
something to backdate into an existing one.

> **Do not re-apply `main.json` as committed.** The procedure below posts the file to the live
> ruleset, and the file declares `"bypass_actors": []`, so running it today would strip the
> intended bypass and reproduce the lockout described above. `main.json` needs its
> `bypass_actors` updated to match the live ruleset first. That edit is left to the owner
> rather than made here, because this file is what a re-apply executes and changing it changes
> what that procedure does.

Nothing in this section changed a repository setting.

Checked before applying, 2026-08-15:

| Query | Result |
|---|---|
| `gh api repos/ChelseaKR/chalkline/rulesets` | `[]` |
| `gh api repos/ChelseaKR/chalkline/branches/main` | `"protected": false` |
| `gh api repos/ChelseaKR/chalkline/branches/main/protection` | 404, Branch not protected |

## What it covers, and what it deliberately does not

`main.json` carries three rules: `deletion`, `non_fast_forward`, and `required_status_checks`
naming `verify`, `audit`, `secret-scan`, `sast`, `zizmor` and `analyze` (the last two added
2026-08-21, when `zizmor` and CodeQL's `actions` language joined `ci.yml`/`codeql.yml` as a
second, independently built opinion on the workflow files, issue #22). Those are every job
name across `.github/workflows/*.yml` today, and they are the whole of what this repository
can require without requiring a check that does not exist. A required context that never
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

## Re-applying it

The file is in the shape the REST API accepts, so it can be posted as-is:

`gh api repos/ChelseaKR/chalkline/rulesets -X POST --input .github/rulesets/main.json`

(`gh api ... -X PATCH repos/.../rulesets/<id>` 404'd against this repository on 2026-08-21 for
reasons that did not reproduce as a documented API or `gh` behavior; DELETE-then-POST worked.
If updating an existing ruleset in place ever matters again, try PATCH first and fall back to
delete-then-recreate.)

Confirm afterwards that `gh api repos/ChelseaKR/chalkline/rulesets` returns it and that
`gh api repos/ChelseaKR/chalkline/branches/main` reports `"protected": true` -- and, because
an API response is not the same thing as a merge actually being refused, confirm it with a
real PR: push a commit that fails one of the required checks, open a PR against `main`, and
confirm both `gh pr merge` and `mergeStateStatus` refuse it before closing the PR unmerged.

`outcome-receipts/.github/rulesets/main.json` is the portfolio's reference for a complete
committed profile. `ledger` has a live and working `protect-main` ruleset but no committed
artifact, which its own `DEFINITION_OF_DONE.md` records as an open gap.
