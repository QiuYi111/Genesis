from __future__ import annotations

from ...trinity.contracts import ModelCfg, Msg
from .base import BaseProvider


class NullProvider(BaseProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:  # type: ignore[override]
        return "{}"  # Deterministic empty plan

