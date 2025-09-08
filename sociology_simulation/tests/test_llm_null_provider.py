"""W1: NullProvider determinism test."""

from __future__ import annotations

import asyncio

from sociology_simulation.services.llm import NullProvider


def test_null_provider_returns_empty_json_text() -> None:
    provider = NullProvider()

    async def _run() -> str:
        return await provider.generate(
            messages=[{"role": "user", "content": "hello"}],
            cfg={"model": "null"},
        )

    text = asyncio.get_event_loop().run_until_complete(_run())
    assert text == "{}"

