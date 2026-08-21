# Every target runs the same way locally and in CI. `make verify` is the gate.
#
# Every invocation is `uv run --locked`, never a bare `uv run`. A bare `uv run` performs an
# implicit sync: when `uv.lock` no longer agrees with `pyproject.toml` it silently rewrites
# the lockfile in place and carries on, so the gate would pass against a resolution nobody
# committed and nobody reviewed. `--locked` makes that case an error instead. Regenerating
# the lockfile is a deliberate act with its own target, `make lock`, and its result is a
# reviewable diff.
UV := env -u VIRTUAL_ENV -u CONDA_PREFIX uv
UVRUN := $(UV) run --locked

.PHONY: install lock lock-check lint format typecheck test build check validate audit verify clean

install:
	$(UV) sync --locked

# The only target allowed to rewrite uv.lock. Run it after changing dependencies in
# pyproject.toml, and commit the result.
lock:
	$(UV) lock

# Fails when uv.lock does not agree with pyproject.toml. Offline, so it is a cheap first
# gate and it never reaches the network to decide.
lock-check:
	$(UV) lock --check --offline

lint:
	$(UVRUN) ruff check .
	$(UVRUN) ruff format --check .

format:
	$(UVRUN) ruff format .
	$(UVRUN) ruff check --fix .

typecheck:
	$(UVRUN) mypy src tests scripts

test:
	$(UVRUN) pytest -q --cov --cov-report=term-missing --cov-report=xml

build:
	$(UVRUN) chalkline build

# Fails when the committed site/ is not byte-for-byte what the code produces.
check:
	$(UVRUN) chalkline check

# A second opinion on the published graph, from an implementation this repository did not
# write. `chalkline check` says the bytes are what this code produces; this says those bytes
# also satisfy a checker built from the same specification by other means. The two tools
# check different rule families -- this project validates class, property, domain and range
# against the vendored schema encoding, and ctdl-validate checks CTID grammar, identifier
# kinds, reference targets and class pairings -- so neither subsumes the other and the
# interesting outcome is a disagreement, not a pass.
#
# scripts/validate_evidence.py runs the installed `ctdl-validate` CLI as a separate process
# over site/credentials.jsonld with --format json and checks the result against the committed
# site/ctdl-validate.json, so a disagreement is never silently absorbed -- it fails the gate
# and the stale evidence has to be regenerated and reviewed as a diff, the same discipline
# `chalkline check` holds credentials.jsonld and coverage.json to.
#
# It makes no network calls itself. ctdl-validate is pinned in pyproject.toml. (`verify` as a
# whole does reach the network, once, in the `audit` step that runs after this one.)
validate:
	$(UVRUN) python scripts/validate_evidence.py --check

# pip-audit queries the PyPI advisory API, so this is the one target in `verify` that is not
# offline. It runs last, for the same reason a network call belongs last in a chain of
# otherwise-deterministic gates: everything decidable from the committed tree alone has
# already been decided by the time this one reaches the network. It is also its own CI job
# (`make audit`, matching this target exactly), because a new advisory against an unchanged
# tree is a fact about the world discovered between commits rather than a regression *in* a
# commit, and that distinction is worth its own line in a CI run. Until 2026-08-21 this target
# was excluded from `verify` on the reasoning above; the reasoning was correct about what an
# audit finding *means* and wrong about what `make verify` is for. A contributor who ran only
# `make verify` locally saw green while an unrun `pip-audit` sat behind it, and `verify` is
# supposed to be the one target that tells the truth about what CI requires (issue #22).
audit:
	$(UVRUN) pip-audit --strict

# lock-check runs first on purpose. Every later target would otherwise be the thing that
# repaired the lockfile it was supposed to be checked against.
#
# `validate` runs after `check`, and the order is the point: `check` proves site/ is what the
# code produces, and only then is validating those committed bytes a statement about this
# build rather than about whatever was last committed. `audit` runs last because it is the
# one target here that reaches the network; everything before it is decided from the
# committed tree alone.
verify: lock-check lint typecheck test check validate audit
	@echo "verify: ok"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache coverage.xml .coverage
