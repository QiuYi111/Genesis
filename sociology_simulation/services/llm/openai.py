from __future__ import annotations

import os

from .base import BaseProvider
from ...trinity.contracts import Msg, ModelCfg


class OpenAIProvider(BaseProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:  # type: ignore[override]
        # Stub implementation for W2: deterministic and offline.
        _ = os.getenv("OPENAI_API_KEY")
        return "{}"

