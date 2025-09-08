"""Minimal Trinity orchestrator and NullPlanner for W1.

This keeps behavior deterministic and offline to satisfy early integration.
"""
from __future__ import annotations

from typing import Protocol

from .contracts import TrinityActions


class Planner(Protocol):
    def plan(self, signals: dict[str, float]) -> dict: ...


class Trinity:
    def __init__(self, planner: Planner) -> None:
        self._planner = planner
        self._event_count = 0

    def observe(self, events: list[dict]) -> None:
        self._event_count += len(events)

    def adjust(self, world: "WorldProtocol") -> TrinityActions:  # type: ignore[name-defined]
        try:
            signals = world.compute_resource_status()  # type: ignore[attr-defined]
        except Exception:
            signals = {"events": float(self._event_count)}
        try:
            plan = self._planner.plan(signals)
        except Exception:
            plan = {"regen": 1.0}
        return TrinityActions(
            resource_regen_multiplier=float(plan.get("regen", 1.0)),
            terrain_adjustments=plan.get("terrain"),
            skill_updates=plan.get("skills"),
        )


class NullPlanner:
    def plan(self, signals: dict[str, float]) -> dict:
        return {"regen": 1.0}


class WorldProtocol(Protocol):
    def compute_resource_status(self) -> dict[str, float]: ...

