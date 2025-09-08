"""Trinity orchestrator, planners, and W2/W3 features.

Adds in W3:
- observe() aggregates simple statistics (total/events by name).
- Structured logging around observe()/adjust() and fallback paths.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from .contracts import LLMProvider, TrinityActions
from .utils import run_async, safe_json_loads


class Planner(Protocol):
    def plan(self, signals: dict[str, float]) -> dict: ...


class Trinity:
    def __init__(self, planner: Planner) -> None:
        self._planner = planner
        self._event_count = 0
        self._event_by_name: dict[str, int] = {}
        self._adjust_count = 0
        self._last_regen: float | None = None
        self._log = logging.getLogger(__name__ + ".Trinity")

    def observe(self, events: list[dict]) -> None:
        n = len(events)
        self._event_count += n
        for e in events:
            name = str(e.get("name", "unknown"))
            self._event_by_name[name] = self._event_by_name.get(name, 0) + 1
        if n:
            self._log.debug(
                "observe: %d events (total=%d) by_name=%s",
                n,
                self._event_count,
                dict(self._event_by_name),
            )

    def adjust(self, world: "WorldProtocol") -> TrinityActions:  # type: ignore[name-defined]
        # Collect signals from world (fallback to event count)
        try:
            signals = world.compute_resource_status()  # type: ignore[attr-defined]
        except Exception:
            signals = {"events": float(self._event_count)}
            self._log.warning("signals_fallback: using event_count=%d", self._event_count)

        # Plan with current signals (fallback to default regen)
        try:
            plan = self._planner.plan(signals)
        except Exception:
            self._log.warning("plan_fallback: using default regen=1.0")
            plan = {"regen": 1.0}

        ta = TrinityActions(
            resource_regen_multiplier=float(plan.get("regen", 1.0)),
            terrain_adjustments=plan.get("terrain"),
            skill_updates=plan.get("skills"),
        )
        self._adjust_count += 1
        self._last_regen = ta.resource_regen_multiplier
        self._log.info(
            "adjust: turn_adjust=%d regen=%.3f signals_keys=%s",
            self._adjust_count,
            ta.resource_regen_multiplier,
            sorted(list(signals.keys())),
        )
        return ta

    @property
    def stats(self) -> dict[str, object]:
        """Return aggregated Trinity statistics.

        Keys:
        - event_total: int
        - event_by_name: dict[str, int]
        - adjust_count: int
        - last_regen: float | None
        """
        return {
            "event_total": int(self._event_count),
            "event_by_name": dict(self._event_by_name),
            "adjust_count": int(self._adjust_count),
            "last_regen": self._last_regen,
        }


class NullPlanner:
    def plan(self, signals: dict[str, float]) -> dict:
        return {"regen": 1.0}


class WorldProtocol(Protocol):
    def compute_resource_status(self) -> dict[str, float]: ...


class LLMPlanner:
    """Planner that queries an async LLM provider with a synchronous wrapper.

    On any exception or timeout, returns a safe default plan.
    """

    def __init__(self, provider: LLMProvider, cfg: dict[str, Any]) -> None:
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
