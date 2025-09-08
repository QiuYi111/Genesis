from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from .types import (
    Action,
    ActionType,
    BehaviorEvent,
    DecisionContext,
    Inventory,
    Position,
    WorldView,
)


@dataclass
class Agent:
    id: int
    name: str
    pos: Position
    inventory: Inventory = field(default_factory=dict)

    def perceive(self, world: Any, *, turn: int) -> DecisionContext:
        view: WorldView = world._world_view  # read-only facade
        visible = view.get_visible(self.pos, radius=1)
        neighbors = view.get_neighbors(self.pos, radius=1)
        signals = view.get_signals()
        return {
            "pos": self.pos,
            "visible": visible,
            "neighbors": neighbors,
            "signals": signals,
        }

    def decide(self, ctx: DecisionContext) -> Action:
        inv = self.inventory
        # Craft if possible (wood + flint -> spear)
        if inv.get("wood", 0) >= 1 and inv.get("flint", 0) >= 1 and inv.get("spear", 0) < 1:
            return Action(ActionType.CRAFT, {"recipe": "spear"})

        # Trade if lacking flint but holding food and neighbors exist
        if inv.get("flint", 0) == 0 and inv.get("food", 0) >= 1 and ctx["neighbors"]:
            return Action(ActionType.TRADE, {"offer": "food", "request": "flint"})

        # Forage if current tile has any resources
        here = [cell for (pos, cell) in ctx["visible"] if pos == ctx["pos"]]
        if here and any(v > 0 for v in here[0].values()):
            return Action(ActionType.FORAGE, {"amount": 1})

        # Otherwise, move to the richest visible cell
        richest = None
        best_score = -1
        for (pos, cell) in ctx["visible"]:
            score = cell.get("wood", 0) + cell.get("flint", 0) + cell.get("food", 0)
            if score > best_score:
                richest = pos
                best_score = score
        if richest is not None and richest != ctx["pos"]:
            return Action(ActionType.MOVE, {"to": richest})

        # Fallback: no-op forage attempt
        return Action(ActionType.FORAGE, {"amount": 1})

    def act(self, action: Action, world_view: WorldView) -> List[BehaviorEvent]:
        # Agent emits an intent event; world will settle effects.
        return [
            {
                "agent_id": self.id,
                "name": action.type,
                "turn": 0,
                "data": dict(action.payload),
            }
        ]
