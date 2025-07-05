#!/usr/bin/env python3
"""Test the food consumption improvements."""

import sys
from pathlib import Path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sociology_simulation.world import World
from sociology_simulation.agent import Agent

def test_food_consumption():
    """Test that agents can consume food to reduce hunger."""
    print("Testing food consumption mechanics...")
    
    # Create test world and agent
    world = World(10, 'Stone Age test', 1)
    agent = Agent(0, (5, 5), {'strength': 5, 'curiosity': 5}, {'fish': 2, 'apple': 1}, age=25)
    
    # Set agent to be very hungry
    agent.hunger = 90
    agent.health = 80
    
    print(f"Initial state:")
    print(f"  Hunger: {agent.hunger}")
    print(f"  Health: {agent.health}")
    print(f"  Inventory: {agent.inventory}")
    
    # Test food consumption
    food_consumed = world._try_consume_food(agent)
    
    print(f"\nAfter food consumption:")
    print(f"  Food consumed: {food_consumed}")
    print(f"  Hunger: {agent.hunger}")
    print(f"  Health: {agent.health}")
    print(f"  Inventory: {agent.inventory}")
    
    # Verify the consumption worked
    assert food_consumed == "fish", f"Expected to consume fish, got {food_consumed}"
    assert agent.hunger < 90, f"Hunger should have decreased, was {agent.hunger}"
    assert agent.inventory["fish"] == 1, f"Fish count should be 1, was {agent.inventory['fish']}"
    assert agent.health > 80, f"Health should have increased slightly, was {agent.health}"
    
    print("\n✅ Food consumption test passed!")

def test_empty_inventory():
    """Test behavior when agent has no food."""
    print("\nTesting empty inventory...")
    
    world = World(10, 'Stone Age test', 1)
    agent = Agent(1, (5, 5), {'strength': 5}, {}, age=25)  # No food
    agent.hunger = 80
    
    food_consumed = world._try_consume_food(agent)
    
    print(f"  No food available: {food_consumed}")
    assert food_consumed is None, f"Expected None when no food, got {food_consumed}"
    
    print("✅ Empty inventory test passed!")

def test_multiple_foods():
    """Test that agent chooses most nutritious food."""
    print("\nTesting food selection...")
    
    world = World(10, 'Stone Age test', 1)
    agent = Agent(2, (5, 5), {'strength': 5}, {'berries': 3, 'meat': 1, 'apple': 2}, age=25)
    agent.hunger = 70
    
    food_consumed = world._try_consume_food(agent)
    
    print(f"  Food consumed: {food_consumed}")
    print(f"  Remaining inventory: {agent.inventory}")
    
    # Should choose meat (35 nutrition) over berries (15) or apple (20)
    assert food_consumed == "meat", f"Expected to consume meat (highest nutrition), got {food_consumed}"
    assert "meat" not in agent.inventory, "Meat should be consumed"
    
    print("✅ Food selection test passed!")

if __name__ == "__main__":
    test_food_consumption()
    test_empty_inventory()
    test_multiple_foods()
    print("\n🎉 All food consumption tests passed!")
    print("\nThe agent survival improvements should now prevent mass starvation!")