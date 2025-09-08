"""Core type contracts for the simulation (W1 skeleton).

This mirrors the contracts in docs/rewrite_team_wbs_three_engineers.md for A-1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypedDict


@dataclass(frozen=True)
class Position:
    x: int
    y: int


class Inventory(TypedDict, total=False):
    wood: int
    flint: int
    spear: int
    food: int


class ActionType:
    MOVE = "move"
    FORAGE = "forage"
    CRAFT = "craft"
    TRADE = "trade"


@dataclass
class Action:
    type: str
    payload: dict[str, object] = field(default_factory=dict)


class BehaviorEvent(TypedDict):
    agent_id: int
    name: str
    turn: int
    data: dict[str, object]


class DecisionContext(TypedDict):
    pos: Position
    visible: list[tuple[Position, dict[str, int]]]
    neighbors: list[int]
    signals: dict[str, float]


class WorldView(Protocol):
    def get_visible(self, pos: Position, radius: int) -> list[tuple[Position, dict[str, int]]]:
        ...

    def get_neighbors(self, pos: Position, radius: int) -> list[int]:
        ...

    def get_signals(self) -> dict[str, float]:
        ...


class TurnResult(TypedDict):
    turn: int
    events: list[BehaviorEvent]
    metrics: dict[str, float]

