# Repository Guidelines

## Project Structure & Module Organization
- Source code: `sociology_simulation/` (core systems like `agent.py`, `world.py`, `trinity.py`).
- Configs: `sociology_simulation/conf/` (Hydra). Docs in `docs/`.
- Web UI: `web_ui/` (static assets) and runtime JSON in `web_data/`.
- Tests: `sociology_simulation/tests/` and several top‑level `test_*.py` files.
- Runtime artifacts: `logs/`, `outputs/`, `web_data/` are git‑ignored.

### Repository Layout (Tree)

```
.
├── sociology_simulation/           # Core code + Hydra conf/
├── scripts/                        # Runnable scripts/tools
│   ├── run_simple_web_simulation.py
│   ├── run_web_simulation.py
│   ├── run_with_web_export.py
│   └── reorg_repo.sh
├── web_ui/                         # Web UI static assets
│   ├── index.html                  # Monitor main page (tests depend on this)
│   ├── js/simulation-ui.js
│   ├── landing/index.html          # Landing/demo page
│   └── experimental/               # Experimental pages
├── web_data/                       # Runtime JSON (git-ignored)
├── docs/                           # Documentation (web-ui/, guides/, engineering/, plans/, agents/)
├── logs/  outputs/                 # Runtime artifacts (git-ignored)
├── test_*.py                       # Cross-module tests (optionally move under package tests/)
├── pyproject.toml  uv.lock
└── README.md
```

## Build, Test, and Development Commands
- Install deps: `uv sync` (requires Python 3.10+ and uv).
- Run simulation: `uv run python -m sociology_simulation.main world.num_agents=10 runtime.turns=30`.
- Web demo: `uv run python run_simple_web_simulation.py` then open `http://localhost:8081`.
- Run tests: `uv run pytest -q`.
- Lint: `uv run ruff check .` | Format: `uv run black .`.

## Coding Style & Naming Conventions
- Python: 4‑space indent, type hints required for public functions, docstrings for modules/classes.
- Naming: modules `snake_case.py`, classes `PascalCase`, functions/vars `snake_case`, constants `UPPER_CASE`.
- Imports: standard → third‑party → local; prefer absolute imports under `sociology_simulation`.
- Tools: Black (format), Ruff (lint). Fix lint before committing.

## Testing Guidelines
- Framework: Pytest. Place unit tests beside modules in `sociology_simulation/tests/` or add top‑level `test_*.py` when cross‑module.
- Conventions: test files `test_*.py`, functions `test_*`. Use fakes/mocks for I/O, websockets, and LLM calls.
- Coverage: aim ≥ 80% for changed lines; add tests for bug fixes and new features.
- Run selective tests: `uv run pytest sociology_simulation/tests/test_core_systems.py -q`.

## Commit & Pull Request Guidelines
- Commits: use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`. Keep messages imperative; include scope when helpful (e.g., `feat(trinity): …`).
- PRs: link issues, describe motivation and approach, list testing steps, and include screenshots/GIFs for Web UI changes. Keep diffs focused; update docs when behavior changes.

## Security & Configuration Tips
- API keys: set `DEEPSEEK_API_KEY` in your environment (e.g., `source .api_key.sh`). Never commit secrets.
- Hydra: prefer CLI overrides for experiments (e.g., `simulation.era_prompt="石器时代"`). Check `HYDRA_USAGE.md` for details.
- Logs/data: large artifacts live in `logs/`, `outputs/`, `web_data/`; avoid adding generated files to Git.

## Agent‑Specific Instructions
- When modifying code, preserve existing public interfaces and update tests/docs accordingly.
- Prefer minimal, focused patches; follow this guide for style and structure.
