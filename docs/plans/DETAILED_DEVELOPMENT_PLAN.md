# Simulation Improvement Parallel Development Plan (Updated)

## Overview
This plan addresses current bottlenecks and adds missing capabilities across four parallel workstreams.
It incorporates a new requirement: combine LLM‑generated turn summaries with statistics computed from
the actual simulation state to avoid contradictions in the “Turn Summary”. Each stream includes targets,
acceptance tests, and coordination notes.

### Goals
- Deterministic, fast world initialization with meaningful terrain/resource variety and safe fallbacks.
- Reliable agent resource interactions (gather/consume) and Trinity default skill seeding.
- Periodic, deterministic evolution hooks and a probabilistic reproduction system.
- Fact‑driven turn summaries: LLM narrative grounded in computed metrics, with consistency checks.

## Workstream A – Initialization & Environment Diversity (Dev A)

Scope: `world.py`, `terrain_generator.py`, `trinity.py` (rule generation), config, tests.

1) Eliminate initialization polling and add safe fallbacks
- In `World.initialize`, remove the `while not hasattr(self.trinity, 'resource_rules')` loop.
- Call `Trinity._generate_initial_rules(session)` once; on exceptions or invalid payloads, fall back to
  `DEFAULT_TERRAIN` and `DEFAULT_RESOURCE_RULES` (already imported), then continue.
- Make `_generate_initial_rules` resilient: catch LLM errors, validate schema, never clear defaults.

2) Configurable terrain generation + deterministic caching
- Add Hydra config `world.terrain.algorithm`: `simple | noise | voronoi | mixed` (default: `mixed`).
- Use a stable seed (derived from era) already passed; add an in‑process cache in
  `terrain_generator.generate_advanced_terrain` keyed by `(size, seed, algorithm, terrain_types)`.

3) Terrain/resource diversity validation
- After rules are generated, ensure at least 2 terrain types and ≥1 resource appear; otherwise fall back
  to `DEFAULT_TERRAIN/DEFAULT_RESOURCE_RULES`.
- In `_classify_terrain`, when coverage is too skewed, introduce light randomization to diversify tiles.

4) Testing
- Unit test: initialization completes without polling and a 16×16 map contains ≥2 terrain types.
- Property test (seeded): same seed → identical terrain map (cache hit should not change result).

## Workstream B – Resource Interaction & Trinity Reliability (Dev B)

Scope: `world.py` (inline `ActionHandler`), `prompts.py`, `trinity.py`, config, tests.

1) Deterministic gather/consume actions via dispatch
- Extend `World.ActionHandler` with a dispatch table: `{"gather": ..., "consume": ..., ...}`.
- `gather`: move items from `World.resources[(x,y)]` to `agent.inventory` respecting availability.
- `consume`: decrement inventory, reduce `agent.hunger` using the existing nutrition table
  (reuse `_try_consume_food` internally for consistency with current tests).

2) Configurable hunger progression with backwards compatibility
- Add Hydra keys: `runtime.hunger_growth_rate` and `runtime.auto_consume` (default `true` to avoid
  breaking existing behavior/tests). When `auto_consume=false`, only explicit `consume` lowers hunger.

3) Seed Trinity with core skills and keep on failures
- In `Trinity.__init__`, populate `available_skills` with baseline skills (`move`, `gather`, `consume`,
  `trade`, `craft`, `build`). `_generate_initial_rules` must never remove these on LLM failures.

4) Prompt updates
- Update `prompts.py` so agent prompt advertises `gather/consume` explicitly and clarifies consequences
  of hunger. Add Trinity prompts to reinforce default skills and deterministic fallbacks.

5) Testing
- Unit test: agent gathers N units from `World.resources` and inventory updates match; consuming decreases
  hunger; nutrition priority chooses highest nutrition when multiple foods exist (keeps current tests valid).

## Workstream C – Evolution & Reproduction Systems (Dev C)

Scope: `world.py`, `trinity.py`, `agent.py`, tests.

1) Periodic evolution hooks with deterministic fallbacks
- In `Trinity.execute_actions`, if LLM returns nothing, apply deterministic low‑impact updates every N
  turns (e.g., small resource regeneration or mild climate event) to ensure progress.

2) Default numeric states and costs
- Extend default numeric states (`stamina`, `cooldowns: Dict[str, int]`), exposed via `Agent.numeric_states`
  which already exists; adjust `ActionHandler` to optionally apply stamina costs/cooldowns per action.

3) Probabilistic reproduction (LLM‑assisted suggestions)
- Trinity proposes reproduction candidates (based on health/inventory/proximity). `World.step` processes
  suggestions with probability and spawns offspring with randomized attributes; keep existing mutual
  courtship path for backward compatibility during transition.

4) Testing
- Integration test: over multiple turns with healthy agents and sufficient resources, population can grow.
- Unit test: stamina/cooldown updates are applied when configured on actions.

## Workstream D – Turn Summary & Analytics (Dev D)

Scope: `world.py`, `prompts.py`, `services/llm_service.py`, optionally `sociology_simulation/analytics/summary.py`,
minimal wiring (no dependency on `core.*` analytics).

Problem: Current “TURN SUMMARY” can contradict reality (e.g., reports “技能单一” while multiple skills
were unlocked). We need a hybrid approach: compute facts first, then ask LLM to narrate based strictly on
those facts, and finally perform a consistency guard.

1) Fact collector (deterministic)
- Implement `World._collect_turn_facts(turn_log)` producing a compact dict, e.g.:
  - `agents_alive`, `groups_count`, `markets_count`, `political_entities`, `technologies_count`.
  - `skill_diversity` (unique skills across agents), `new_skills_this_turn` (from Trinity logs or deltas).
  - `avg_social_connections`, `economic_health`, `notable_events` (top agent logs, births/deaths).
- Replace `_generate_emergent_behavior_report` with fact‑based heuristics only (no generic “单一/复杂”
  unless thresholds trigger). Keep thresholds explicit and documented.

2) LLM‑generated narrative grounded in facts
- Add a new prompt template `trinity_turn_summary` in `prompts.py` with strict instructions:
  - Input: the facts JSON and selected notable events.
  - Output JSON: `{ "summary": str, "highlights": [str], "warnings": [str] }`.
  - Must not contradict provided facts; if unsure, omit claims.
- Add `LLMService.trinity_turn_summary(facts)`; on failure, fall back to a minimal templated summary.

3) Consistency guard and final output
- Validate the LLM output against facts (e.g., if `skill_diversity >= 5`, forbid phrases like “技能单一”).
  If contradictions are detected, rewrite/clip the offending lines and append a note: “(auto‑corrected
  to match metrics)”.
- Final “TURN SUMMARY” format:
  - Header lines (counts from facts)
  - Bulleted facts (computed)
  - LLM narrative summary (post‑validated)

4) Testing
- Unit test: construct facts with high `skill_diversity`; ensure the final summary does not include
  “技能单一” and includes at least one `new_skills_this_turn` highlight.
- Integration smoke test: run a short seeded sim and snapshot‑test that the facts section matches the
  computed values in code.

## Coordination Notes
- Run `uv run ruff check .` and `uv run pytest -q` before submitting PRs.
- Keep interfaces backward compatible: `World.ActionHandler` remains inline; `_try_consume_food` stays for
  tests while adding explicit `consume` handling; Trinity default skills are additive.
- Config additions via Hydra (no breaking defaults):
  - `world.terrain.algorithm` (default `mixed`)
  - `runtime.hunger_growth_rate` (default keep current effective behavior)
  - `runtime.auto_consume` (default `true`)
  - `output.turn_summary.llm` (default `true`) and `output.turn_summary.max_highlights` (e.g., 5)
- Weekly sync to integrate cross‑cutting changes (Trinity hooks, prompts, config keys).

## Acceptance Criteria (global)
- Initialization is synchronous and robust to LLM failures; map diversity verified on 16×16.
- Agents can deterministically `gather` and `consume`; hunger decreases and tests pass unchanged.
- Trinity periodically evolves world state even with silent LLMs; default skills persist.
- Turn summaries cannot contradict core facts; when LLM is used, contradictions are auto‑corrected.

## Milestones
1. A (init + terrain) complete with tests and config keys exposed.
2. B (gather/consume + prompts) complete, default skills seeded, all current tests green.
3. D (turn summary rework) complete: facts collector, prompt, guard, tests.
4. C (evolution + reproduction + numeric costs) complete with integration test.

