# Engineering Audit and Improvement Plan

## Current State (Summary)
- Mixed structure: Python package in `sociology_simulation/`, many root‑level scripts (`run_*.py`, `test_*.py`, `demo_*.py`), and a placeholder `main.py` not tied to the package.
- Tooling mismatch: README suggests Black/Ruff/Pytest and `uv sync --group dev`, but `pyproject.toml` has no dev group or tool configs.
- Secrets committed: `.api_key.sh` contains a real API key; README and `index.html` demonstrate inline key usage. High risk.
- Tests inconsistent: unit tests inside `sociology_simulation/tests/` plus several top‑level test scripts that alter `sys.path` and print instead of assert. Some tests open websockets ports.
- Docs exist but are fragmented (CN/EN mix) and partially out of sync with code.
- No CI/CD, no pre‑commit, no type checking, no coverage enforcement.

## Risks and Issues
- Security: committed secret key; potential accidental exposure via logs, HTML or docs; unclear key loading path.
- Reproducibility: minimal `pyproject.toml` (no dev deps/groups), reliance on ad‑hoc scripts; missing Makefile or task runner.
- Maintainability: duplicated entry points, inconsistent naming and imports, `sys.path` hacks in tests, large data files in repo.
- Quality: tests mix prints and assertions; integration tests bind real network ports; no lint/format gate; no type checks.

## Recommended Improvements (Actionable)
1) Security (immediate)
- Revoke and rotate the leaked key; remove `.api_key.sh` from repo and history; add to `.gitignore`.
- Standardize config: load `DEEPSEEK_API_KEY` from env only; document `uv run --env-file .env` usage; never embed keys in HTML.

2) Project structure
- Keep all runtime/entry points under `sociology_simulation/` or a `cli/` module; convert root `run_*.py` into `python -m sociology_simulation...` commands.
- Move top‑level tests into `sociology_simulation/tests/` or a root `tests/` package; remove `sys.path` mutations.
- Store generated artifacts in `logs/`, `outputs/`, `web_data/` (already git‑ignored). Avoid committing large JSON snapshots.

3) Tooling and config
- Add dev dependencies and tool configs in `pyproject.toml`:
  - `optional-dependencies.dev = ["pytest", "black", "ruff", "mypy", "pytest-asyncio", "types-requests"]`
  - `[tool.black]`, `[tool.ruff]`, `[tool.pytest.ini_options]`, `[tool.mypy]` with sensible defaults.
- Add `pre-commit` hooks for Black/Ruff and forbid secrets (`detect-secrets` or `pre-commit-hooks`).
- Provide a `Makefile` or `justfile` with `make setup`, `make test`, `make lint`, `make format`, `make web`.

4) Testing
- Convert print‑based demos to true pytest tests with assertions and markers (`@pytest.mark.asyncio`).
- Guard network tests: use random free ports; `pytest.skip` if port or dependency unavailable.
- Add unit tests per module; target ≥80% changed‑line coverage; introduce `coverage.py` and CI gate.

5) Code quality and typing
- Enforce Black/Ruff in CI; fix imports to absolute package paths.
- Introduce `mypy` with gradual typing; require types for public functions.

6) Documentation
- Consolidate docs: align README with actual commands; keep language consistent per page; add troubleshooting and reproducibility notes.
- Add architecture overview and module ownership in `docs/technical/architecture.md` (link from README).

7) CI/CD
- Add GitHub Actions: matrix (py3.10/3.11), steps: uv cache → `uv sync --all-groups` → `ruff` → `black --check` → `pytest --maxfail=1 -q` → coverage upload.

## Prioritized Plan (2 weeks)
- Day 1–2: Revoke keys, purge file, add secrets guard; add dev deps + tool configs; pre‑commit.
- Day 3–5: Test hygiene (move tests, remove `sys.path` hacks), stabilize network tests, add coverage.
- Day 6–7: Refactor entry points; standardize CLI via `python -m sociology_simulation.main` and `web_monitor`.
- Day 8–9: Fix lint/type issues; enable mypy on core modules.
- Day 10–12: CI pipeline; documentation pass; finalize contributor guide (AGENTS.md done).

## Quick Commands (after changes)
- Install (all groups): `uv sync --all-groups`
- Lint/format: `uv run ruff check . && uv run black .`
- Tests: `uv run pytest -q` (or `-k core_systems` for focus)
- Type check: `uv run mypy sociology_simulation`
