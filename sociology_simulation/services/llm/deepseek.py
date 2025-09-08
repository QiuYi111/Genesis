from __future__ import annotations

import os

from .base import BaseProvider
from ...trinity.contracts import Msg, ModelCfg


class DeepSeekProvider(BaseProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:  # type: ignore[override]
        # Stub implementation for W2: ensure deterministic, offline behavior.
        # Read API key if present (no network calls in tests).
        _ = os.getenv("DEEPSEEK_API_KEY")
        return "{}"

