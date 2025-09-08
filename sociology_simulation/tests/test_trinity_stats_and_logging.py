from __future__ import annotations

import asyncio
from typing import Any

import pytest

from sociology_simulation.services.llm import DeepSeekProvider
from sociology_simulation.trinity import LLMPlanner, NullPlanner, Trinity


def test_observe_aggregates_event_stats() -> None:
    t = Trinity(NullPlanner())
    events = [
        {"name": "move", "data": {}},
        {"name": "forage", "data": {}},
        {"name": "move", "data": {}},
        {"name": "craft", "data": {}},
    ]
    t.observe(events)
    stats = t.stats
    assert stats["event_total"] == 4
    by = stats["event_by_name"]  # type: ignore[assignment]
    assert isinstance(by, dict)
    assert by.get("move") == 2
    assert by.get("forage") == 1
    assert by.get("craft") == 1


def test_adjust_logs_and_updates_stats_with_fallback(caplog: pytest.LogCaptureFixture) -> None:
    t = Trinity(NullPlanner())

    class _NoSignals:  # world without compute_resource_status
        pass

    with caplog.at_level("INFO"):
        ta = t.adjust(_NoSignals())

    # Stats updated
    s = t.stats
    assert s["adjust_count"] == 1
    assert s["last_regen"] == ta.resource_regen_multiplier == 1.0

    # Logged something informative (message content may vary, check presence)
    assert any("adjust:" in rec.getMessage() for rec in caplog.records)


def test_llm_planner_exception_fallback() -> None:
    class _ExplodingProvider:
        async def generate(self, messages: list[dict[str, str]], cfg: dict[str, Any]) -> str:  # type: ignore[override]
            raise RuntimeError("boom")

    planner = LLMPlanner(_ExplodingProvider(), {"timeout": 0.01, "model": "x", "provider": "p"})
    out = planner.plan({"x": 1.0})
    assert out.get("regen", 1.0) == 1.0


def test_deepseek_provider_without_key_returns_empty_json_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ensure no API key is visible
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    provider = DeepSeekProvider()

    async def _run() -> str:
        return await provider.generate(
            messages=[{"role": "user", "content": "hi"}], cfg={"model": "deepseek-chat"}
        )

    text = asyncio.get_event_loop().run_until_complete(_run())
    assert text == "{}"
