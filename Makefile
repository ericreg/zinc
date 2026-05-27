# .PHONY tells make that these aren't real files — they're just task names.
# Without this, make might skip a task if a file with the same name exists.
.PHONY: ci docs fmt lint lint-fix test test-fast test-live

# Run all linting checks (on the dcs_simulation_engine/ package here).
lint:
	uv run ruff check

lint-fix:
	uv run ruff check --fix

# format code in place (on the dcs_simulation_engine/ package here).
fmt:
	uv run ruff format && uv run ruff check --select I --fix

# Run test suite quietly
test:
	uv run pytest -n auto

build:
	uv run python test/test_compile.py --update-output

all: fmt build test
