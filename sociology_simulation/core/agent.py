from __future__ import annotations

from dataclasses import dataclass
from .types import Position, Inventory, DecisionContext, Action, ActionType, BehaviorEvent, WorldView


@dataclass
class Agent:
    id: int
    name: str
    pos: Position
    inventory: Inventory

    def perceive(self, world: "World", *, turn: int) -> DecisionContext:  # type: ignore[name-defined]
        return {
            "pos": self.pos,
            "visible": [],
            "neighbors": [],
            "signals": world.compute_resource_status(),
        }

    def decide(self, ctx: DecisionContext) -> Action:
        # Minimal deterministic behavior for smoke: alternate move/forage
        return Action(type=ActionType.MOVE, payload={"dx": 1, "dy": 0})

    def act(self, action: Action, world_view: WorldView) -> list[BehaviorEvent]:
        if action.type == ActionType.MOVE:
            to = Position(self.pos.x + int(action.payload.get("dx", 0)), self.pos.y + int(action.payload.get("dy", 0)))
            return [
                {
                    "agent_id": self.id,
                    "name": "move",
                    "turn": 0,
                    "data": {"from": self.pos, "to": to},
                }
            ]
        return []

