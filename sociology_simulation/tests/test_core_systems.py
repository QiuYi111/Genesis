from __future__ import annotations

from sociology_simulation.core.world import World
from sociology_simulation.core.types import Position


class DummyTrinity:
    def observe(self, events):
        pass

    def adjust(self, world: World):
        class TA:
            resource_regen_multiplier = 1.0

        return TA()


def test_seeded_resources_deterministic():
    w1 = World(size=6, seed=123, num_agents=0)
    w2 = World(size=6, seed=123, num_agents=0)
    w3 = World(size=6, seed=124, num_agents=0)
    assert w1.resources == w2.resources
    assert w1.resources != w3.resources


def test_regeneration_multiplier_zero_and_high():
    w = World(size=4, seed=99, num_agents=0)
    # zero out all resources
    for y in range(w.size):
        for x in range(w.size):
            w.resources[y][x]["wood"] = 0
            w.resources[y][x]["flint"] = 0
            w.resources[y][x]["food"] = 0

    # multiplier=0.0 -> no regeneration
    w._regenerate_resources(multiplier=0.0)
    assert all(
        w.resources[y][x][k] == 0 for y in range(w.size) for x in range(w.size) for k in ("wood", "flint", "food")
    )

    # very high multiplier -> effectively regenerate into 1s where 0
    w._regenerate_resources(multiplier=100.0)
    assert all(
        w.resources[y][x][k] >= 1 for y in range(w.size) for x in range(w.size) for k in ("wood", "flint", "food")
    )


def test_forage_consumes_cell_and_increases_inventory():
    w = World(size=4, seed=1, num_agents=1)
    a = w.agents[0]
    a.pos = Position(0, 0)
    w.resources[0][0] = {"wood": 0, "flint": 0, "food": 1}
    DummyTrinity().observe([])  # no-op, satisfy path
    # one step -> agent should forage food from current cell
    w.step(0, trinity=DummyTrinity())
    assert a.inventory.get("food", 0) >= 1
    assert w.resources[0][0]["food"] == 0


def test_craft_recipe_wood_flint_to_spear():
    w = World(size=4, seed=2, num_agents=1)
    a = w.agents[0]
    a.pos = Position(0, 0)
    w.resources[0][0] = {"wood": 0, "flint": 0, "food": 0}
    a.inventory = {"wood": 1, "flint": 1}
    w.step(0, trinity=DummyTrinity())
    assert a.inventory.get("spear", 0) == 1
    assert a.inventory.get("wood", 0) == 0
    assert a.inventory.get("flint", 0) == 0


def test_trade_food_for_flint():
    w = World(size=5, seed=3, num_agents=2)
    a0, a1 = w.agents[0], w.agents[1]
    a0.pos = Position(0, 0)
    a1.pos = Position(0, 1)  # neighbor
    # ensure current cell is empty so agent prefers trade over forage
    w.resources[0][0] = {"wood": 0, "flint": 0, "food": 0}
    w.resources[1][0] = {"wood": 0, "flint": 0, "food": 0}
    a0.inventory = {"food": 1}
    a1.inventory = {"flint": 1}
    w.step(0, trinity=DummyTrinity())
    assert a0.inventory.get("food", 0) == 0
    assert a0.inventory.get("flint", 0) == 1
    assert a1.inventory.get("food", 0) == 1
    assert a1.inventory.get("flint", 0) == 0


def test_move_to_richer_cell():
    w = World(size=4, seed=4, num_agents=1)
    a = w.agents[0]
    a.pos = Position(0, 0)
    # clear all visible cells first
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            x = (a.pos.x + dx) % w.size
            y = (a.pos.y + dy) % w.size
            w.resources[y][x] = {"wood": 0, "flint": 0, "food": 0}
    # make (1,0) richer
    w.resources[0][1] = {"wood": 0, "flint": 0, "food": 2}
    w.step(0, trinity=DummyTrinity())
    assert (a.pos.x, a.pos.y) == (1, 0)

