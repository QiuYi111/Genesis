"""Tests for Workstream A: initialization and terrain diversity/determinism"""
import asyncio
from typing import Dict

import pytest

from sociology_simulation.world import World
from sociology_simulation.trinity import Trinity
from sociology_simulation.terrain_generator import generate_advanced_terrain


@pytest.mark.asyncio
async def test_world_initialization_diversity(monkeypatch):
    """Initialization completes without polling and 16x16 map has >= 2 terrains."""

    async def fake_generate_initial_rules(self: Trinity, session):
        # Minimal, deterministic rules
        self.terrain_types = ["OCEAN", "FOREST", "GRASSLAND", "MOUNTAIN"]
        self.resource_rules = {
            "wood": {"FOREST": 0.5},
            "fish": {"OCEAN": 0.4},
        }

    monkeypatch.setattr(Trinity, "_generate_initial_rules", fake_generate_initial_rules, raising=True)

    world = World(size=16, era_prompt="Stone Age", num_agents=2)

    # Use a single shared session to align with the code path
    import aiohttp

    async with aiohttp.ClientSession() as session:
        await world.initialize(session)

    # Validate diversity
    terrain_set = {world.map[x][y] for x in range(world.size) for y in range(world.size)}
    assert len(terrain_set) >= 2


def test_generate_advanced_terrain_deterministic_cache():
    """Same seed -> identical terrain map (cache hit should not change result)."""
    size = 16
    terrain_types = ["OCEAN", "FOREST", "GRASSLAND", "MOUNTAIN"]
    seed = 12345

    t1 = generate_advanced_terrain(size=size, terrain_types=terrain_types, terrain_colors={}, algorithm="mixed", seed=seed)
    t2 = generate_advanced_terrain(size=size, terrain_types=terrain_types, terrain_colors={}, algorithm="mixed", seed=seed)

    # Check equality
    assert t1 == t2

