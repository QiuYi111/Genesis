from __future__ import annotations

from sociology_simulation.core.world import World


def test_step_returns_metrics_and_updates_turn():
    w = World(size=5, seed=7, num_agents=2)
    result = w.step(0, trinity=_DummyTrinity())
    assert result["turn"] == 0
    m = result["metrics"]
    # Basic keys exist and are non-negative
    for k in ("actions_per_turn", "resource_food", "resource_wood", "resource_flint", "inv_spear", "scarcity"):
        assert k in m
        assert isinstance(m[k], float)
        assert m[k] >= 0.0


def test_snapshot_schema_has_world_agents_metrics_and_heatmap():
    w = World(size=6, seed=11, num_agents=3)
    w.step(0, trinity=_DummyTrinity())
    snap = w.snapshot()
    assert snap["world"]["size"] == 6
    assert isinstance(snap["agents"], list) and len(snap["agents"]) == 3
    assert isinstance(snap["metrics"], dict)
    heat = snap["resources_heat"]
    assert isinstance(heat, list) and len(heat) == 6
    assert all(isinstance(row, list) and len(row) == 6 for row in heat)
    # Values are integers >= 0
    assert all(isinstance(v, int) and v >= 0 for row in heat for v in row)


class _DummyTrinity:
    def observe(self, events):
        pass

    def adjust(self, world: World):
        class _TA:
            resource_regen_multiplier = 1.0

        return _TA()

