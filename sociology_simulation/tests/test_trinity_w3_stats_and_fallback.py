from __future__ import annotations

import asyncio
import logging
from typing import Any

import pytest

from sociology_simulation.trinity import NullPlanner, Trinity
from sociology_simulation.services.llm.deepseek import DeepSeekProvider


def test_trinity_observe_aggregates_event_counts() -> None:
    tri = Trinity(NullPlanner())

    events = [
        {"name": "move", "data": {}},
        {"name": "forage", "data": {}},
        {"name": "move", "data": {}},
    ]

    tri.observe(events)

    stats = tri.stats
    assert stats["event_total"] == 3
    assert stats["event_by_name"]["move"] == 2
    assert stats["event_by_name"]["forage"] == 1
    assert stats["adjust_count"] == 0
    assert stats["last_regen"] is None


def test_trinity_adjust_increments_stats_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    tri = Trinity(NullPlanner())

    class _W:
        def compute_resource_status(self) -> dict[str, float]:
            return {"scarcity": 0.5}

    caplog.set_level(logging.INFO)
    ta = tri.adjust(_W())
    assert ta.resource_regen_multiplier == 1.0

    stats = tri.stats
    assert stats["adjust_count"] == 1
    assert stats["last_regen"] == 1.0

    # Ensure an info-level structured log was emitted from adjust()
    assert any("adjust:" in rec.getMessage() for rec in caplog.records)


def test_trinity_adjust_planner_exception_fallback(caplog: pytest.LogCaptureFixture) -> None:
    class _BadPlanner:
        def plan(self, signals: dict[str, float]) -> dict:  # type: ignore[override]
            raise RuntimeError("planner boom")

    tri = Trinity(_BadPlanner())

    class _W2:
        def compute_resource_status(self) -> dict[str, float]:
            return {"x": 1.0}

    caplog.set_level(logging.WARNING)
    ta = tri.adjust(_W2())
    assert ta.resource_regen_multiplier == 1.0
    # Warning about planner fallback should be present
    assert any("plan_fallback" in rec.getMessage() for rec in caplog.records)


def test_deepseek_provider_without_key_returns_empty_json_text() -> None:
    provider = DeepSeekProvider()

    async def _run() -> str:
        # No DEEPSEEK_API_KEY in env → immediate fallback to "{}"
        return await provider.generate([
            {"role": "user", "content": "probe"}
        ], {"model": "deepseek-chat", "timeout": 0.1})

    text = asyncio.get_event_loop().run_until_complete(_run())
    assert text == "{}"

