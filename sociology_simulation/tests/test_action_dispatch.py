"""Tests for deterministic action dispatch (gather/consume)."""
from sociology_simulation.world import World
from sociology_simulation.agent import Agent


async def _resolve_sync(handler, action, agent, world, era):
    """Helper to call async resolve in a sync pytest test via asyncio loop."""
    import asyncio

    return await handler.resolve(action, agent, world, era)


def test_gather_dispatch(monkeypatch):
    world = World(8, "Stone Age", 0)
    agent = Agent(0, (2, 2), {"strength": 5, "curiosity": 5}, {}, age=20)
    world.resources[(2, 2)] = {"wood": 3}

    handler = World.ActionHandler(world.bible, world)

    # Run the async resolve using asyncio.run to avoid LLM due to dispatch
    import asyncio

    outcome = asyncio.run(_resolve_sync(handler, "gather 2 wood", agent, world, world.era_prompt))

    # Apply outcome to agent to reflect inventory changes
    agent.apply_outcome(outcome)

    assert agent.inventory.get("wood", 0) == 2
    assert world.resources.get((2, 2), {}).get("wood", 0) == 1
    assert "gathered" in outcome.get("log", "").lower()


def test_consume_dispatch_explicit():
    world = World(8, "Stone Age", 0)
    agent = Agent(1, (1, 1), {"strength": 5}, {"meat": 1}, age=25)
    agent.hunger = 80

    handler = World.ActionHandler(world.bible, world)

    import asyncio

    outcome = asyncio.run(_resolve_sync(handler, "consume meat", agent, world, world.era_prompt))
    agent.apply_outcome(outcome)

    assert agent.hunger < 80
    assert agent.inventory.get("meat", 0) == 0
    assert "consumed" in outcome.get("log", "").lower()

