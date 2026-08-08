# Every target runs the same way locally and in CI. `make verify` is the gate.
UV := env -u VIRTUAL_ENV -u CONDA_PREFIX uv

.PHONY: install lint format typecheck test build check audit verify clean

install:
	$(UV) sync

lint:
	$(UV) run ruff check .
	$(UV) run ruff format --check .

format:
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck:
	$(UV) run mypy src tests scripts

test:
	$(UV) run pytest -q --cov --cov-report=term-missing --cov-report=xml

build:
	$(UV) run chalkline build

# Fails when the committed site/ is not byte-for-byte what the code produces.
check:
	$(UV) run chalkline check

audit:
	$(UV) run pip-audit --strict

verify: lint typecheck test check
	@echo "verify: ok"

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache coverage.xml .coverage
