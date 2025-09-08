# Simulation Improvement Parallel Development Plan

## Overview
This plan breaks down the current bottlenecks and missing features in the sociology simulation
into three workstreams. Each stream can be developed in parallel by one developer and includes
code targets, acceptance tests, and coordination notes.

### Goals
- Faster, deterministic world initialization with meaningful terrain and resource variety.
- Agents capable of gathering and consuming resources while Trinity reliably seeds default skills.
- Autonomous evolution events (skills, rules, weather) and a probabilistic reproduction system.

## Workstream A – Initialization & Environment Diversity *(Dev A)*

**Scope**: `world.py`, `terrain_generator.py`, `trinity.py` (rule generation portions), related tests.

1. **Eliminate initialization polling**
   - In `World.initialize`, replace the `while not hasattr(self.trinity, 'resource_rules')` loop with a
     synchronous call that raises on failure.
   - Ensure `_generate_initial_rules` sets `resource_rules` and `terrain_types` before returning.
2. **Configurable terrain generation**
   - Add a `terrain.algorithm` option ("simple" | "realistic") and default to simple.
   - Cache results for deterministic seeds to speed up repeated runs.
3. **Improve terrain/resource diversity**
   - After `_generate_initial_rules`, validate that multiple terrain and resource types exist; if not,
     fall back to `DEFAULT_TERRAIN` and `DEFAULT_RESOURCES`.
   - Update `terrain_generator._classify_terrain` to randomize classification when types are scarce.
4. **Testing**
   - Add unit test verifying initialization finishes without polling and that at least two terrain types
     appear on a 16x16 map.

## Workstream B – Resource Interaction & Trinity Reliability *(Dev B)*

**Scope**: `world.py`, `action_handler.py` (if separated), `prompts.py`, `trinity.py`, relevant tests.

1. **Agent-driven gather/consume actions**
   - Extend `ActionHandler` with a dispatch table for actions (`gather`, `consume`, etc.).
   - On `gather_request`, transfer resources from `World.resources` to `agent.inventory`.
   - On `consume_request`, decrement inventory and reduce `agent.hunger`.
2. **Expose hunger configuration**
   - Add `hunger_growth_rate` to config with a lower default.
   - Remove automatic food consumption in `World.step`; rely on explicit `consume` actions.
3. **Seed Trinity with core skills**
   - Populate `Trinity.available_skills` with `move`, `gather`, `consume`, etc. during `__init__`.
   - Ensure `_generate_initial_rules` never clears these defaults even if LLM fails.
4. **Prompt updates**
   - Update `prompts.py` to advertise `gather` and `consume` actions and clarify hunger consequences.
5. **Testing**
   - Add tests confirming an agent can gather a resource and lower hunger by consuming it.

## Workstream C – Evolution & Reproduction Systems *(Dev C)*

**Scope**: `world.py`, `trinity.py`, `agent.py`, tests.

1. **Periodic evolution hooks**
   - In `Trinity.execute_actions`, trigger weather or rule evolution every N turns even when LLM
     returns nothing. Provide deterministic fallbacks.
2. **Default numeric state variables**
   - Extend `Agent` with `stamina` and `cooldowns: Dict[str, int]`.
   - `ActionHandler` deducts stamina or sets cooldowns when actions specify costs.
3. **Reproduction mechanism**
   - Allow Trinity to propose reproduction pairs based on health/inventory.
   - Update `World.step` to process these suggestions with probability instead of mutual consent.
   - Initialize offspring with random attributes and log births.
4. **Testing**
   - Add integration test running several turns to ensure population can grow when agents are healthy.

## Coordination Notes
- Each developer should run `uv run ruff check .` and `uv run pytest -q` before submitting PRs.
- Interfaces between workstreams (`ActionHandler` API, Trinity hooks) must remain backward compatible.
- Weekly sync to integrate changes and resolve merge conflicts.

