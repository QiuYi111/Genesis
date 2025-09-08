import aiohttp
import pytest
from types import SimpleNamespace

from sociology_simulation.agent import Agent
from sociology_simulation.world import World
from sociology_simulation.bible import Bible
from sociology_simulation.trinity import Trinity


@pytest.mark.asyncio
async def test_action_handler_applies_numeric_state_changes():
    agent = Agent(1, (0, 0), {}, {})
    world_stub = SimpleNamespace(pending_interactions=[])
    handler = World.ActionHandler(Bible(), world_stub)
    async with aiohttp.ClientSession() as session:
        await handler._process_outcome(
            {
                "state_updates": {"stamina": 10},
                "state_deltas": {"stamina": -3, "energy": 5},
                "state_remove": ["energy"],
            },
            agent,
            world_stub,
            session,
            "",
        )
    assert agent.get_numeric_state("stamina") == 7.0
    assert "energy" not in agent.numeric_states


def test_trinity_can_modify_numeric_state():
    bible = Bible()
    trinity = Trinity(bible, "Stone Age")
    agent = Agent(2, (0, 0), {}, {})
    trinity.update_agent_numeric_state(agent, updates={"stamina": 5})
    assert agent.get_numeric_state("stamina") == 5.0
    trinity.update_agent_numeric_state(agent, deltas={"stamina": -2})
    assert agent.get_numeric_state("stamina") == 3.0
    trinity.update_agent_numeric_state(agent, remove=["stamina"])
    assert agent.get_numeric_state("stamina") == 0.0
    assert "stamina" not in agent.numeric_states
