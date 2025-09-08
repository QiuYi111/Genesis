from __future__ import annotations

from .base import BaseProvider
from ...trinity.contracts import Msg, ModelCfg


class NullProvider(BaseProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:  # type: ignore[override]
        return "{}"  # Deterministic empty plan

