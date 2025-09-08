from __future__ import annotations

from ...trinity.contracts import LLMProvider, ModelCfg, Msg


class BaseProvider(LLMProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:  # type: ignore[override]
        raise NotImplementedError
