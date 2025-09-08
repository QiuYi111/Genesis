"""Trinity contracts (W1 skeleton).

Defines message types, provider protocol, and TrinityActions dataclass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, TypedDict


class Msg(TypedDict):
    role: str  # system|user|assistant
    content: str


class ModelCfg(TypedDict, total=False):
    provider: str
    model: str
    temperature: float
    timeout: float


class LLMProvider(Protocol):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str: ...


@dataclass
class TrinityActions:
    resource_regen_multiplier: float = 1.0
    terrain_adjustments: Optional[list[tuple["Position", str]]] = None
    skill_updates: Optional[dict[str, dict]] = None

