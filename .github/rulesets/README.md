# Rulesets

`main.json` is the branch-protection posture this repository intends for `main`, committed
so it is reviewable in the tree rather than existing only as a setting nobody can see in a
diff. CI-CD-STANDARD §5 asks for exactly that: "Branch protection is enforced through a
repository-owned GitHub Ruleset named `protect-main` and committed as a per-repo artifact so
the posture is reviewable in-tree."

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

The `current_user_can_bypass: "never"` in that table was the answer on 2026-08-21 and is not
the answer now. The ruleset gained the repository owner's standing bypass on 2026-08-26 and
keeps it; read "Why the owner can bypass" below before taking that row for the current
posture.

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

## Why the owner can bypass

`bypass_actors` holds exactly the repository owner's standing bypass -- `RepositoryRole` 5
with `bypass_mode: "always"` -- deliberately and permanently: an agent once applied a ruleset
with no bypass and locked the owner out of their own repository, and restoring access took a
sweep across eighteen repositories. An empty list here is not a stricter gate, it is the
lockout.

Read off the live ruleset on 2026-08-28:

| Query | Result |
|---|---|
| `gh api repos/ChelseaKR/chalkline/rulesets/21156701 --jq .bypass_actors` | `[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]` |
| `gh api repos/ChelseaKR/chalkline/rulesets/21156701 --jq .current_user_can_bypass` | `"always"` |

Nothing else moved with it. The same six contexts are required, still with
`strict_required_status_checks_policy`, and `deletion` and `non_fast_forward` still refuse.
What the bypass buys is a way back in when a required check is wedged, when a workflow file
is broken badly enough that CI stops reporting at all, or when the repository has to be
recovered -- the cases whose only other route is a support ticket against your own
repository. It is one actor, and it is a repository role rather than a team or a GitHub App:
a second bypass actor turning up in this list would be a real finding, and this one is not.

`main.json` declared `"bypass_actors": []` until 2026-08-28, which made the command in the
next section a way to reproduce the lockout rather than a way to restore the posture. The
file now records the bypass, so re-applying it is safe -- and the confirmation below asks
after `bypass_actors` by name, because that is the field that goes missing quietly.

## Re-applying it

**Before running this, open `main.json` and check that `bypass_actors` still holds
`{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}`.** The file
declared `"bypass_actors": []` until 2026-08-28, and applying that version is how the owner
gets locked out of this repository. Note that POST is not the safe half of the pair either:
posting a second ruleset over `main` does not replace the live one, it adds to it, and rules
from every applicable ruleset combine while bypass actors are per-ruleset. A new ruleset with
an empty bypass list blocks the owner no matter what the existing one allows. Delete the
ruleset that no longer matches before posting a replacement.

The file is in the shape the REST API accepts, so it can be posted as-is:

`gh api repos/ChelseaKR/chalkline/rulesets -X POST --input .github/rulesets/main.json`

(`gh api ... -X PATCH repos/.../rulesets/<id>` 404'd against this repository on 2026-08-21 for
reasons that did not reproduce as a documented API or `gh` behavior; DELETE-then-POST worked.
If updating an existing ruleset in place ever matters again, try PATCH first and fall back to
delete-then-recreate.)

Confirm afterwards that `gh api repos/ChelseaKR/chalkline/rulesets` returns it, that
`gh api repos/ChelseaKR/chalkline/branches/main` reports `"protected": true`, and that
`gh api repos/ChelseaKR/chalkline/rulesets/<id> --jq .current_user_can_bypass` still reads
`"always"` -- a re-apply that quietly drops the owner's bypass looks like a clean 201. Then,
because an API response is not the same thing as a merge actually being refused, confirm it
with a real PR: push a commit that fails one of the required checks, open a PR against
`main`, and confirm both `gh pr merge` and `mergeStateStatus` refuse it before closing the
PR unmerged.

`outcome-receipts/.github/rulesets/main.json` is the portfolio's reference for a complete
committed profile. `ledger` has a live and working `protect-main` ruleset but no committed
artifact, which its own `DEFINITION_OF_DONE.md` records as an open gap.
