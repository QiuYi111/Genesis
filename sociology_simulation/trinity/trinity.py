"""Trinity orchestrator, planners, and W2 sync wrapper."""
from __future__ import annotations

from typing import Any, Protocol

from .contracts import TrinityActions
from .utils import run_async, safe_json_loads


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


class LLMPlanner:
    """Planner that queries an async LLM provider with a synchronous wrapper.

    On any exception or timeout, returns a safe default plan.
    """

    def __init__(self, provider: "LLMProvider", cfg: dict[str, Any]) -> None:  # type: ignore[name-defined]
        self._provider = provider
        # Keep only the expected keys to avoid passing unknowns further
        self._cfg = {
            "provider": cfg.get("provider", "null"),
            "model": cfg.get("model", "placeholder"),
            "temperature": float(cfg.get("temperature", 0.0)),
            "timeout": float(cfg.get("timeout", 5.0)),
        }

    def plan(self, signals: dict[str, float]) -> dict:
        messages = [
            {"role": "system", "content": "You are an ecosystem tuner. Return compact JSON."},
            {"role": "user", "content": f"signals={signals}"},
        ]
        try:
            text = run_async(
                self._provider.generate(messages, self._cfg), timeout=self._cfg.get("timeout", 5.0)
            )
            doc = safe_json_loads(text)
            if not isinstance(doc, dict):
                return {"regen": 1.0}
            return doc
        except Exception:
            return {"regen": 1.0}
