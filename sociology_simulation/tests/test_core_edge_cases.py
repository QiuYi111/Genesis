from __future__ import annotations

from sociology_simulation.core.world import World


class _DummyTrinity:
    def observe(self, events):
        pass

    def adjust(self, world: World):
        class _TA:
            resource_regen_multiplier = 1.0

        return _TA()


def test_world_with_no_agents_runs_and_snapshots_ok():
    w = World(size=3, seed=42, num_agents=0)
    result = w.step(0, trinity=_DummyTrinity())
    assert result["events"] == []
    assert result["metrics"]["actions_per_turn"] == 0.0

    snap = w.snapshot()
    assert isinstance(snap["agents"], list) and len(snap["agents"]) == 0
    assert isinstance(snap["metrics"], dict)
    heat = snap["resources_heat"]
    assert isinstance(heat, list) and len(heat) == 3
    assert all(isinstance(row, list) and len(row) == 3 for row in heat)


def test_compute_resource_status_zero_and_full_grid():
    w = World(size=4, seed=7, num_agents=0)
    # zero out all resources -> all totals 0, avg_per_cell 0.0
    for y in range(w.size):
        for x in range(w.size):
            w.resources[y][x]["wood"] = 0
            w.resources[y][x]["flint"] = 0
            w.resources[y][x]["food"] = 0
    status = w.compute_resource_status()
    assert status["wood"] == 0.0
    assert status["flint"] == 0.0
    assert status["food"] == 0.0
    assert status["avg_per_cell"] == 0.0

    # set to full grid (each cell has 1 for each resource) -> totals each = size*size, avg_per_cell = 3.0
    for y in range(w.size):
        for x in range(w.size):
            w.resources[y][x]["wood"] = 1
            w.resources[y][x]["flint"] = 1
            w.resources[y][x]["food"] = 1
    status2 = w.compute_resource_status()
    assert status2["wood"] == float(w.size * w.size)
    assert status2["flint"] == float(w.size * w.size)
    assert status2["food"] == float(w.size * w.size)
    assert status2["avg_per_cell"] == 3.0


def test_full_grid_regeneration_does_not_overflow():
    w = World(size=5, seed=5, num_agents=0)
    for y in range(w.size):
        for x in range(w.size):
            w.resources[y][x] = {"wood": 1, "flint": 1, "food": 1}
    # even with very high multiplier, values capped at >=1 and should not increase beyond 1 by our scheme
    w._regenerate_resources(multiplier=100.0)
    assert all(
        w.resources[y][x][k] == 1 for y in range(w.size) for x in range(w.size) for k in ("wood", "flint", "food")
    )


def test_high_agent_density_produces_one_action_per_agent():
    # Place many agents on a tiny map; ensure step runs and counts actions deterministically
    n_agents = 20
    w = World(size=2, seed=9, num_agents=n_agents)
    # remove resources so agents either move or attempt no-op forage; still one intent per agent
    for y in range(w.size):
        for x in range(w.size):
            w.resources[y][x] = {"wood": 0, "flint": 0, "food": 0}

    result = w.step(0, trinity=_DummyTrinity())
    assert result["metrics"]["actions_per_turn"] == float(n_agents)

