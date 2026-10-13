# Repository Reorganization Plan

This plan streamlines the repository layout while preserving current commands, public interfaces, and tests. It follows the project’s guidelines for structure, naming, and tooling.

## Objectives
- Reduce root-level clutter; group related assets by function.
- Align file locations with the documented structure: code under `sociology_simulation/`, web assets in `web_ui/`, runtime JSON in `web_data/`, scripts in `scripts/`, docs under `docs/`.
- Keep existing developer ergonomics: current run/test commands continue to work.

## Scope
- Moves/renames of files and folders only; no behavioral changes to code.
- Minimal edits: add compatibility stubs if required (e.g., entrypoints).

## Target Structure (high level)
```
/               # light root
├─ sociology_simulation/        # core package (agents, world, trinity, conf)
├─ scripts/                     # runnable scripts & CLIs
│  ├─ run_simple_web_simulation.py
│  ├─ run_web_simulation.py
│  ├─ run_with_web_export.py
│  └─ reorg_repo.sh
├─ web_ui/                      # web UI (static assets)
│  ├─ index.html
│  ├─ js/
│  ├─ landing/                  # landing/demo page(s)
│  └─ experimental/             # experimental UI(s)
├─ web_data/                    # runtime JSON for web UI (git-ignored)
├─ docs/                        # documentation
│  ├─ web-ui/    ├─ guides/    ├─ engineering/    ├─ plans/    └─ agents/
├─ logs/  outputs/              # runtime artifacts (git-ignored)
├─ README.md  pyproject.toml  uv.lock
└─ test_*.py (temporary; see Phase 2)
```

## Phases & Steps

### Phase 0 — Safeguards
- Ensure `.gitignore` ignores `web_data/`, `logs/`, `outputs/`, `.venv/`, `__pycache__/`, `.pytest_cache/`.
- Optional: create a dedicated branch for reorg, or run `scripts/reorg_repo.sh` in dry-run to preview.

### Phase 1 — Normalize layout (completed)
- Web assets:
  - Move root `index.html` and `styles.css` → `web_ui/landing/`.
  - Keep main monitor UI under `web_ui/` and `web_ui/js/` as tests expect.
  - Place experimental UI under `web_ui/experimental/`.
- Runtime JSON:
  - Move root `web_ui_data.json`, `real_simulation_data.json` → `web_data/`.
- Scripts:
  - Move `demo_refactored_features.py`, `export_simulation_data.py` → `scripts/`.
  - Retain root UX for the Web Demo via a thin stub `run_simple_web_simulation.py` delegating to `scripts/run_simple_web_simulation.py`.
- Docs:
  - Group guide/plan/engineering/agent docs under `docs/` subfolders.

### Phase 2 — Tests tidy-up (optional)
- Option A: keep top-level `test_*.py` (as cross-module tests) and do nothing.
- Option B: move top-level tests into `sociology_simulation/tests/` for a quieter root. Validate imports and fix any path assumptions.

### Phase 3 — Documentation updates
- Update `README.md` paths (e.g., landing page now `web_ui/landing/index.html`).
- Add a short “Repository Layout” section with the target structure.
- Ensure docs link paths match new locations.

### Phase 4 — Validation & polish
- Run basic validation:
  - `uv run pytest -q`
  - `uv run ruff check .` and `uv run black --check .`
  - Web UI smoke: `uv run python run_simple_web_simulation.py` then open `http://localhost:8081`.
  - Confirm `test_web_ui.py` still finds `web_ui/index.html` and `web_ui/js/simulation-ui.js`.
- Optional: add a short CONTRIB note about where to place new scripts, docs, and data.

## Compatibility Guardrails
- Preserve existing entrypoints; use root stub(s) if moving scripts.
- Do not change public module paths under `sociology_simulation/`.
- Avoid modifying code logic; only move files.

## Rollback Plan
- Perform changes on a branch. If needed, `git reset --hard <base>` or revert the reorg commit.
- `scripts/reorg_repo.sh` supports dry-run and commit options to control changes.

## Old → New Path Highlights
- `index.html` → `web_ui/landing/index.html`
- `styles.css` → `web_ui/landing/styles.css`
- `sociology_simulation_web_ui.html` → `web_ui/experimental/sociology_simulation_web_ui.html`
- `web_ui_data.json` → `web_data/web_ui_data.json`
- `real_simulation_data.json` → `web_data/real_simulation_data.json`
- `demo_refactored_features.py` → `scripts/demo_refactored_features.py`
- `export_simulation_data.py` → `scripts/export_simulation_data.py`
- `run_simple_web_simulation.py` (root) → stub that delegates to `scripts/run_simple_web_simulation.py`
- Docs moved under `docs/` subfolders (`web-ui/`, `guides/`, `engineering/`, `plans/`, `agents/`).

## How to Execute (if re-running)
- Preview: `bash scripts/reorg_repo.sh` (dry-run)
- Apply: `bash scripts/reorg_repo.sh --apply`
- With commit: `bash scripts/reorg_repo.sh --apply --commit`
- Custom branch: `bash scripts/reorg_repo.sh --apply --branch chore/reorg-YYYYMMDD`

## Next Decisions
- Do we proceed with Phase 2 (move root tests under `sociology_simulation/tests/`) or keep them top-level as cross-module tests?
- Should we add a “Repository Layout” section to `README.md` now?

