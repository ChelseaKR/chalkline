# Rulesets

`main.json` is the branch-protection posture this repository intends for `main`, committed
so it is reviewable in the tree rather than existing only as a setting nobody can see in a
diff. CI-CD-STANDARD §5 asks for exactly that: "Branch protection is enforced through a
repository-owned GitHub Ruleset named `protect-main` and committed as a per-repo artifact so
the posture is reviewable in-tree."

It agrees with the live ruleset in every field it declares, `bypass_actors` included. It did
not until 2026-08-29, and the section below records what was stale, which way the reasoning
was reversed to fix it, and what to confirm after any re-apply.

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

## The owner bypass is intended, and `main.json` carries it

Recorded 2026-08-26, re-read 2026-08-28 and again 2026-08-29. The live ruleset and `main.json`
disagreed about the bypass posture and about nothing else. **The live posture was the correct
one**, so on 2026-08-29 `main.json` was changed to match it rather than the other way around.

| Query | Result, 2026-08-28, re-read unchanged 2026-08-29 |
|---|---|
| `gh api repos/ChelseaKR/chalkline/rulesets/21156701 --jq .bypass_actors` | `[{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]` |
| `... --jq .current_user_can_bypass` | `"always"` |
| `... --jq .updated_at` | `2026-08-26T21:27:29.806-07:00` |
| `... --jq .rules` | unchanged: `deletion`, `non_fast_forward`, and the same six required contexts, `strict_required_status_checks_policy: true` |
| the same response compared field by field against `main.json` | `name`, `enforcement`, `conditions`, `rules` and `bypass_actors` all equal, 2026-08-29 |

The admin bypass was added deliberately, on 2026-08-26, and the owner has confirmed it. It
stays. The reason is not hypothetical: an agent once removed an admin bypass from another
repository and locked the owner out of it, with no path back in that did not go through
support. A role-level `always` bypass is the way back in when a required check is wedged, a
runner is unavailable, or an automated change makes the branch unmergeable by anyone.

So this section recorded a documentation defect, not a configuration one. Every required check
is still required and still strict; what changed on 2026-08-26 is that the ruleset can be
bypassed by the repository role holding `actor_id: 5`, where on 2026-08-21 it could not be
bypassed by anyone. `main.json` went on declaring `"bypass_actors": []` for three days after
that, and three places asserted "not even an administrator can override it": the 2026-08-21
table above, the `ci.yml` header, and the `CHANGELOG.md` entry for #30.

The `ci.yml` header has been corrected to state the live posture, and its note that the
committed file had not caught up was dropped on 2026-08-29, when the file caught up. **The
`CHANGELOG.md` entry has not been touched**, because that entry is a record of what #30 did on
the day it did it; the change of posture belongs in a new entry, which is the owner's to write
rather than something to backdate into an existing one.

> **This paragraph used to say the opposite, and the reversal is the point.** From 2026-08-26
> to 2026-08-29 it read "Do not re-apply `main.json` as committed", because the procedure below
> posts the file to the live ruleset, the file declared `"bypass_actors": []`, and running it
> would have stripped the intended bypass and reproduced the lockout described above. That was
> correct for exactly as long as the field was stale. What it asked for was the edit, not the
> warning: `main.json` now carries the one bypass actor the live ruleset carries, so the
> committed file and the apply command finally say the same thing. Confirm it after an apply
> anyway, per "Re-applying it" below. An apply that lands every rule and loses the bypass
> returns 201 like any other.

### `bypass_actors`: the repository owner, and nobody else

`main.json` carries exactly one bypass actor, and it is the whole of the list:

`{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}`

`RepositoryRole` 5 is the admin role. The mode is `always` rather than the `pull_request`
CI-CD-STANDARD asks for at CICD-15 ("one designated maintainer, **PR-only**
(`bypass_mode: pull_request`); direct admin pushes remain blocked"), and the departure is
deliberate rather than an oversight: a bypass that only works inside a pull request is no use
when the thing that is wedged is the pull request. A repository role rather than a team or a
GitHub App, and one entry rather than two: a second entry here would be a real finding, and
this one is not.

An empty list is not a stricter reading of the same rule, it is the lockout. It leaves no
break-glass path, so the owner cannot merge, cannot push, and cannot delete the ruleset that
is blocking them, and GitHub returns 201 for that apply exactly as it does for any other.

`tests/test_ruleset.py` is what keeps the field from regressing, because correcting it once is
not the same as it staying corrected. That module parses this file rather than grepping it, so
a malformed file that still contains the string `bypass_actors` fails instead of passing; it
fails on a missing or unparseable file rather than reading an absent subject as nothing wrong;
and it rejects the five shapes an edit can lose the bypass in, which are an empty list, no key
at all, a value that is not a list, a different actor, and the right actor carrying
`bypass_mode: pull_request`. It also fails if this README stops naming the actor the file
carries, because the prose is what a person follows when the two disagree.

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

POST creates a ruleset rather than replacing one, which is why the 2026-08-21 update went
DELETE-then-POST; a bypass list belongs to the ruleset that carries it, so posting this file
on top of a live `protect-main` leaves two rulesets over `main` rather than one.

Confirm afterwards that `gh api repos/ChelseaKR/chalkline/rulesets` returns it, that
`gh api repos/ChelseaKR/chalkline/rulesets/<id> --jq .bypass_actors` holds exactly the one
actor `main.json` names and `--jq .current_user_can_bypass` reads `"always"`, and that
`gh api repos/ChelseaKR/chalkline/branches/main` reports `"protected": true` -- and, because
an API response is not the same thing as a merge actually being refused, confirm it with a
real PR: push a commit that fails one of the required checks, open a PR against `main`, and
confirm both `gh pr merge` and `mergeStateStatus` refuse it before closing the PR unmerged.

`outcome-receipts/.github/rulesets/main.json` is the portfolio's reference for a complete
committed profile. `ledger` has a live and working `protect-main` ruleset but no committed
artifact, which its own `DEFINITION_OF_DONE.md` records as an open gap.
