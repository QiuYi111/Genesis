from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from .agent import Agent
from .types import TurnResult, BehaviorEvent, Position


@dataclass
class _WorldView:
    def get_visible(self, pos: Position, radius: int):  # pragma: no cover - placeholder
        return []

    def get_neighbors(self, pos: Position, radius: int):  # pragma: no cover - placeholder
        return []

    def get_signals(self):  # pragma: no cover - placeholder
        return {}


class World:
    def __init__(self, size: int, seed: int, num_agents: int = 1) -> None:
        self.size = size
        self.seed = seed
        self._rng = random.Random(seed)
        self._world_view = _WorldView()
        self.agents: List[Agent] = []
        for i in range(num_agents):
            x, y = self._rng.randrange(0, size), self._rng.randrange(0, size)
            self.agents.append(Agent(id=i, name=f"agent-{i}", pos=Position(x, y), inventory={}))
        self._turn = 0

    def step(self, turn: int, *, trinity) -> TurnResult:  # type: ignore[override]
        events: list[BehaviorEvent] = []
        for agent in self.agents:
            ctx = agent.perceive(self, turn=turn)
            act = agent.decide(ctx)
            evs = agent.act(act, self._world_view)
            self._apply_agent_events(agent, evs)
            events.extend(evs)

        trinity.observe(events)
        ta = trinity.adjust(self)
        # Apply regen multiplier to a dummy internal metric for smoke only
        metrics = {"agents": float(len(self.agents)), "regen": float(ta.resource_regen_multiplier)}
        self._turn = turn
        return {"turn": turn, "events": events, "metrics": metrics}

    def _apply_agent_events(self, agent: Agent, evs: list[BehaviorEvent]) -> None:
        for e in evs:
            if e["name"] == "move":
                agent.pos = e["data"]["to"]

    def compute_resource_status(self) -> dict[str, float]:
        # Minimal signals for W1 smoke
        return {"agents": float(len(self.agents))}

    def snapshot(self) -> dict:
        return {
            "turn": self._turn,
            "world": {"size": self.size},
            "agents": [{"id": a.id, "x": a.pos.x, "y": a.pos.y} for a in self.agents],
        }

