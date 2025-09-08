from __future__ import annotations

import asyncio
from typing import Any

from sociology_simulation.trinity import LLMPlanner, Trinity


class _SlowBadProvider:
    async def generate(self, messages: list[dict[str, str]], cfg: dict[str, Any]) -> str:
        await asyncio.sleep(0.05)
        return "not-json"


class _GoodProvider:
    async def generate(self, messages: list[dict[str, str]], cfg: dict[str, Any]) -> str:
        return "{\"regen\": 1.25}"


def test_llm_planner_timeout_fallback():
    planner = LLMPlanner(_SlowBadProvider(), {"timeout": 0.001, "model": "x", "provider": "p"})
    out = planner.plan({"food": 1.0})
    assert isinstance(out, dict)
    assert out.get("regen", 1.0) == 1.0


def test_llm_planner_parses_valid_json():
    planner = LLMPlanner(_GoodProvider(), {"timeout": 1.0, "model": "x", "provider": "p"})
    t = Trinity(planner)

    class _W:
        def compute_resource_status(self) -> dict[str, float]:
            return {"food": 1.0}

    ta = t.adjust(_W())
    assert ta.resource_regen_multiplier == 1.25

