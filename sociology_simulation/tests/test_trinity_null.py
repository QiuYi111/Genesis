"""W1: Trinity + NullPlanner basic behavior tests."""

from __future__ import annotations

from sociology_simulation.trinity import NullPlanner, Trinity


class _FakeWorld:
    def __init__(self, signals: dict[str, float] | None = None) -> None:
        self._signals = signals or {"scarcity": 0.3}

    def compute_resource_status(self) -> dict[str, float]:
        return dict(self._signals)


def test_adjust_with_null_planner_defaults_to_regen_one() -> None:
    planner = NullPlanner()
    tri = Trinity(planner)
    world = _FakeWorld({"scarcity": 0.8})

    actions = tri.adjust(world)

    assert actions.resource_regen_multiplier == 1.0
    # Optional fields remain None for null plan
    assert actions.terrain_adjustments is None
    assert actions.skill_updates is None


def test_adjust_handles_world_without_signals_method() -> None:
    planner = NullPlanner()
    tri = Trinity(planner)

    class _NoSignals:  # type: ignore[too-many-ancestors]
        pass

    actions = tri.adjust(_NoSignals())
    assert actions.resource_regen_multiplier == 1.0

