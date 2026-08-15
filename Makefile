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

.PHONY: install lock lock-check lint format typecheck test build check audit verify clean

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

# Not part of `verify`: pip-audit queries the PyPI advisory API, and `verify` is offline by
# design. CI runs this as its own job, and a new advisory against an unchanged tree is a
# fact about the world rather than a regression in this commit.
audit:
	$(UVRUN) pip-audit --strict

# lock-check runs first on purpose. Every later target would otherwise be the thing that
# repaired the lockfile it was supposed to be checked against.
verify: lock-check lint typecheck test check
	@echo "verify: ok"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache coverage.xml .coverage
