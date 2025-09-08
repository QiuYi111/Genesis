from __future__ import annotations

from ..typing_compat import AwaitableStr
from ...trinity.contracts import LLMProvider, Msg, ModelCfg


class BaseProvider(LLMProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:  # type: ignore[override]
        raise NotImplementedError

