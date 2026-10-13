# Project Genesis – Refactor & Delivery Plan (MVP Scope)

## 1) Goals, Scope, Success Criteria
- Clean, modular, testable codebase that implements documented features at a smaller, reproducible scale.
- MVP world: 32×32 map, 10 agents, 30 turns, deterministic seed.
- Features in MVP:
  - Core: agents with inventory, simple actions (move/forage/craft/trade), tick loop.
  - Trinity: observes behavior → suggests/adjusts skills and resource dynamics via a provider‐agnostic LLM interface (with offline stub).
  - Environment: basic terrain and resource regeneration.
  - Web UI: live monitor via WebSocket, JSON export and timeline.
  - Config: Hydra overrides for key parameters.
- Success: `uv run python -m sociology_simulation.main` runs end‑to‑end; `uv run pytest -q` passes; CI green; docs and examples match behavior.

## 2) Target Architecture & Directory Layout
```
sociology_simulation/
  core/              # domain: Agent, World, Actions, Events
  services/          # LLMService (DeepSeek/OpenAI), WebSocket, Logging
  trinity/           # Trinity engine, rules, adapters
  analytics/         # metrics, log parser
  persistence/       # save/load, exporters
  conf/              # Hydra configs
  cli/               # CLI entrypoints
  web_export.py      # kept thin or moved into services/web
  web_monitor.py     # server + broadcast
  main.py            # orchestrates simulation via composition
web_ui/              # static client
tests/               # pytest (unit + integration)
```
Principles: dependency inward (UI→services→core), no circular imports, provider strategy for LLMs, deterministic by default.

## 3) Workstreams, Ownership, Deliverables
1. Core Simulation (Lead: A)
- Deliverables: `World`, `Agent`, `Action` API; tick loop; resource model; deterministic seed.
- Contracts:
  - `World.step(turn:int) -> TurnResult`
  - `Agent.decide(context) -> Action` (no LLM dependency)
- Acceptance: run 30 turns with no exceptions; resources change plausibly; logs emitted.

2. Trinity System & LLM Abstraction (Lead: B)
- Deliverables: `Trinity` that consumes telemetry and emits adjustments (skills, regen factors).
- Provider interface: `LLMService.generate(messages: list[Msg], cfg: ModelCfg) -> str`.
- Implement `NullLLMService` (offline), `DeepSeekService`, `OpenAIService` (config via env).
- Acceptance: offline stub produces deterministic suggestions; can swap providers by Hydra.

3. Configuration & Parameters (Lead: C)
- Deliverables: Hydra configs (`conf/`) for runtime, world, models; CLI overrides.
- Acceptance: `uv run python -m sociology_simulation.main runtime.turns=30 world.num_agents=10 model.provider=null` works.

4. Web Monitor & Export (Lead: D)
- Deliverables: WebSocket server (port from config), periodic JSON export schema:
  - world: size, terrain summary, resources heatmap
  - agents: id, name, pos, inventory, skills, current_action
  - logs: level, message, turn
- Acceptance: `run_simple_web_simulation.py` replaced by `python -m sociology_simulation.cli.web_demo`; web_ui shows map and agents.

5. Analytics, Logging, Persistence (Lead: E)
- Deliverables: structured logging (JSON lines), timeline extraction, save/load snapshot (optional), log parser stabilized.
- Acceptance: basic metrics computed; exported files readable; parser unit tests pass.

6. Testing & QA (Lead: F)
- Deliverables: pytest suite (unit for core/trinity, integration for CLI + web monitor), test data builders, ≥80% changed‑line coverage, async tests stable.
- Acceptance: `uv run pytest -q` green locally and in CI.

7. Tooling, CI, Security (Lead: G)
- Deliverables: `pyproject.toml` dev deps + tool configs (black, ruff, pytest, mypy, coverage), GitHub Actions (lint/format/test), pre‑commit, secrets check, remove `.api_key.sh`.
- Acceptance: CI green, no secrets in repo, formatting enforced.

8. Documentation & DX (Lead: H)
- Deliverables: updated README quickstart, `docs/technical/architecture.md`, troubleshooting, AGENTS.md alignment; minimal API docs.
- Acceptance: a new contributor can install, run, test in <15 minutes.

## 4) Backlog → Tasks (Parallelizable)
Core Simulation
- Define data classes: Position, Inventory, Action, TurnResult.
- Implement terrain gen (seeded), resources grid, simple regen.
- Implement actions: move, forage, craft (recipe: wood+flint→spear), trade (barter).
- Agent loop: perceive→decide (heuristics)→act; hook telemetry emitter.

Trinity & LLM
- Telemetry schema (events from core).
- Skill catalogue minimal set; adjustment rules; regen factor tuning.
- LLMService: base + Null provider; provider selection via Hydra; env key loading.

Config
- Hydra: `runtime.yaml`, `world.yaml`, `model/{null,deepseek,openai}.yaml`, `logging.yaml`.
- CLI: `cli/main.py` with `run` command reading Hydra.

Web
- WebSocket broadcaster (asyncio), backpressure safe; export JSON schema v1.
- Minimal UI: render grid, agents, log ticker; connect via ws://.

Analytics & Persistence
- Structured logs; `log_parser` to timeline; metrics: actions per turn, scarcity ratio.

Testing
- Unit: core actions, resource calc, trinity adjustments (stubbed LLM).
- Integration: CLI run 5 turns; WebSocket start/connect (random port); export file exists.

Tooling & CI
- pyproject tools config; pre‑commit hooks; GitHub Actions matrix (3.10/3.11).
- Remove `.api_key.sh`, add `.env.example`.

Docs
- Update README commands; architecture diagram (ASCII); config guide.

## 5) Definition of Done (per Workstream)
- Code formatted (black), lint clean (ruff), typed for public API, unit tests included, docs snippets runnable, no secrets, CI green.

## 6) Milestones & Timeline (3 weeks)
- Week 1: Core (A), Config (C), Tooling/CI (G) start in parallel. Trinity stub (B) and Web monitor skeleton (D).
- Week 2: Trinity provider adapters (B), Web UI integration (D), Analytics/Parser (E), Tests expansion (F).
- Week 3: Stabilize integration, performance pass, docs polish (H), cut v0.1.0.

## 7) Interfaces & Contracts (details)
- `sociology_simulation.core.world.World`:
  - `__init__(size:int, seed:int)`
  - `step(turn:int, trinity:Trinity) -> TurnResult`
  - properties: `terrain: dict[(x,y)→type]`, `resources: dict[(x,y)→{str:int}]`
- `sociology_simulation.core.agent.Agent`:
  - `decide(ctx: DecisionContext) -> Action` (pure; no network)
- `sociology_simulation.trinity.Trinity`:
  - `observe(events: list[Event]) -> None`
  - `adjust(world: World) -> TrinityActions`
- `sociology_simulation.services.llm.LLMService`:
  - `generate(messages: list[dict], *, temperature: float=0.0) -> str`

## 8) Risks & Mitigation
- LLM variability → use Null provider by default; make live providers optional.
- Websocket fragility → random free port in tests; timeouts; retries.
- Scope creep → MVP features only; backlog for advanced systems (politics, culture memory).

## 9) Acceptance Demo Script
- `uv sync --all-groups`
- `uv run python -m sociology_simulation.main world.size=32 world.num_agents=10 runtime.turns=30 model.provider=null`
- Open `web_ui/index.html` and connect to `ws://localhost:8081` (configurable) to watch the run.
- `uv run pytest -q` → all green.

## 10) Post‑MVP Roadmap (Optional)
- Rich economy (prices, markets), group governance, culture transmission, save/load scenarios, profiling and performance on 256×256 world.
