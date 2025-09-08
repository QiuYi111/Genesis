from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .agent import Agent
from .types import TurnResult, BehaviorEvent, Position, WorldView, ActionType


class _WorldView(WorldView):
    def __init__(self, world: "World") -> None:
        self._w = world

    def get_visible(self, pos: Position, radius: int) -> List[Tuple[Position, Dict[str, int]]]:
        cells: List[Tuple[Position, Dict[str, int]]] = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                x = (pos.x + dx) % self._w.size
                y = (pos.y + dy) % self._w.size
                cells.append((Position(x, y), dict(self._w.resources[y][x])))
        return cells

    def get_neighbors(self, pos: Position, radius: int) -> List[int]:
        ids: List[int] = []
        for a in self._w.agents:
            if a.pos != pos and abs(a.pos.x - pos.x) <= radius and abs(a.pos.y - pos.y) <= radius:
                ids.append(a.id)
        return ids

    def get_signals(self) -> Dict[str, float]:
        return self._w.compute_resource_status()


class World:
    def __init__(self, size: int, seed: int, num_agents: int = 1) -> None:
        self.size = size
        self.seed = seed
        self._rng = random.Random(seed)
        self.resources: List[List[Dict[str, int]]] = self._init_resources()
        self.agents: List[Agent] = []
        for i in range(num_agents):
            x, y = self._rng.randrange(0, size), self._rng.randrange(0, size)
            self.agents.append(Agent(id=i, name=f"agent-{i}", pos=Position(x, y)))
        self._world_view: WorldView = _WorldView(self)
        self._turn = 0
        self._last_actions_count = 0

    def _init_resources(self) -> List[List[Dict[str, int]]]:
        grid: List[List[Dict[str, int]]] = []
        for y in range(self.size):
            row: List[Dict[str, int]] = []
            for x in range(self.size):
                wood = 1 if self._rng.random() < 0.2 else 0
                flint = 1 if self._rng.random() < 0.1 else 0
                food = 1 if self._rng.random() < 0.15 else 0
                row.append({"wood": wood, "flint": flint, "food": food})
            grid.append(row)
        return grid

    def step(self, turn: int, *, trinity) -> TurnResult:  # type: ignore[override]
        events: list[BehaviorEvent] = []
        actions_count = 0
        for agent in self.agents:
            ctx = agent.perceive(self, turn=turn)
            act = agent.decide(ctx)
            evs = agent.act(act, self._world_view)
            for e in evs:
                e["turn"] = turn
            self._apply_agent_events(agent, evs)
            events.extend(evs)
            actions_count += len(evs)

        try:
            trinity.observe(events)
        except Exception:
            pass
        try:
            ta = trinity.adjust(self)
        except Exception:
            ta = type("_TA", (), {"resource_regen_multiplier": 1.0})()

        self._apply_trinity_actions(ta)
        self._regenerate_resources(multiplier=float(getattr(ta, "resource_regen_multiplier", 1.0)))
        metrics = self._compute_metrics(actions_count)
        self._turn = turn
        return {"turn": turn, "events": events, "metrics": metrics}

    def _apply_agent_events(self, agent: Agent, evs: list[BehaviorEvent]) -> None:
        for e in evs:
            name = e["name"]
            data = e.get("data", {})
            if name == ActionType.MOVE:
                to = data.get("to")
                if isinstance(to, Position):
                    agent.pos = Position(to.x % self.size, to.y % self.size)
            elif name == ActionType.FORAGE:
                x, y = agent.pos.x, agent.pos.y
                cell = self.resources[y][x]
                amount = int(data.get("amount", 1))
                for key in ("food", "wood", "flint"):
                    if cell.get(key, 0) > 0 and amount > 0:
                        take = min(1, cell[key])
                        cell[key] -= take
                        agent.inventory[key] = agent.inventory.get(key, 0) + take
                        amount -= take
            elif name == ActionType.CRAFT:
                recipe = data.get("recipe")
                if recipe == "spear":
                    if agent.inventory.get("wood", 0) >= 1 and agent.inventory.get("flint", 0) >= 1:
                        agent.inventory["wood"] -= 1
                        agent.inventory["flint"] -= 1
                        agent.inventory["spear"] = agent.inventory.get("spear", 0) + 1
            elif name == ActionType.TRADE:
                partner_id = self._nearest_neighbor(agent)
                if partner_id is not None:
                    # Prevent immediate trade reversal within the same turn by enforcing an order.
                    if agent.id >= partner_id:
                        continue
                    other = self._agent_by_id(partner_id)
                    if other is not None:
                        if agent.inventory.get("food", 0) >= 1 and other.inventory.get("flint", 0) >= 1:
                            agent.inventory["food"] -= 1
                            other.inventory["food"] = other.inventory.get("food", 0) + 1
                            other.inventory["flint"] -= 1
                            agent.inventory["flint"] = agent.inventory.get("flint", 0) + 1

    def _nearest_neighbor(self, agent: Agent) -> int | None:
        best = None
        best_d = 1e9
        for a in self.agents:
            if a.id == agent.id:
                continue
            d = abs(a.pos.x - agent.pos.x) + abs(a.pos.y - agent.pos.y)
            if d < best_d:
                best_d = d
                best = a.id
        return best

    def _agent_by_id(self, agent_id: int) -> Agent | None:
        for a in self.agents:
            if a.id == agent_id:
                return a
        return None

    def _apply_trinity_actions(self, ta: Any) -> None:
        _ = ta

    def _regenerate_resources(self, *, multiplier: float) -> None:
        regen_base = 0.05 * float(multiplier)
        for y in range(self.size):
            for x in range(self.size):
                cell = self.resources[y][x]
                for key in ("food", "wood", "flint"):
                    if cell.get(key, 0) < 1 and self._rng.random() < regen_base:
                        cell[key] = cell.get(key, 0) + 1

    def _compute_metrics(self, actions_count: int) -> Dict[str, float]:
        totals = {"wood": 0, "flint": 0, "food": 0}
        for y in range(self.size):
            for x in range(self.size):
                cell = self.resources[y][x]
                for k in totals:
                    totals[k] += cell.get(k, 0)
        inv_totals = {"wood": 0, "flint": 0, "food": 0, "spear": 0}
        for a in self.agents:
            for k in inv_totals:
                inv_totals[k] += a.inventory.get(k, 0)
        scarcity = 1.0 / (1.0 + totals["food"] + totals["wood"] + totals["flint"])
        self._last_actions_count = actions_count
        return {
            "actions_per_turn": float(actions_count),
            "resource_food": float(totals["food"]),
            "resource_wood": float(totals["wood"]),
            "resource_flint": float(totals["flint"]),
            "inv_spear": float(inv_totals["spear"]),
            "scarcity": float(scarcity),
        }

    def compute_resource_status(self) -> dict[str, float]:
        totals = {"wood": 0, "flint": 0, "food": 0}
        for y in range(self.size):
            for x in range(self.size):
                cell = self.resources[y][x]
                for k in totals:
                    totals[k] += cell.get(k, 0)
        return {
            "wood": float(totals["wood"]),
            "flint": float(totals["flint"]),
            "food": float(totals["food"]),
            "avg_per_cell": float(sum(totals.values()) / max(1, self.size * self.size)),
        }

    def snapshot(self) -> dict:
        return {
            "turn": self._turn,
            "world": {"size": self.size},
            "agents": [
                {
                    "id": a.id,
                    "x": a.pos.x,
                    "y": a.pos.y,
                    "inventory": dict(a.inventory),
                }
                for a in self.agents
            ],
            "metrics": self._compute_metrics(self._last_actions_count),
        }
