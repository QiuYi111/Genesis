#!/usr/bin/env python3
"""Direct test of agent inventory mechanics without LLM"""

from sociology_simulation.agent import Agent
from sociology_simulation.config import set_config
from sociology_simulation.bible import Bible
import random

def test_inventory_mechanics():
    """Test agent inventory mechanics directly"""
    
    print("=== TESTING AGENT INVENTORY MECHANICS ===\n")
    
    # Create test agents with realistic starting inventory
    agents = []
    for i in range(3):
        agent = Agent(
            aid=i,
            pos=(random.randint(0, 10), random.randint(0, 10)),
            attributes={"strength": 5, "intelligence": 5, "dexterity": 5},
            inventory={
                "wood": random.randint(1, 3),
                "shell": random.randint(0, 2),
                "apple": random.randint(2, 4),
                "fish": random.randint(1, 2),
                "berries": random.randint(1, 3),
                "flint": random.randint(0, 1)
            },
            name=f"TestAgent{i}",
            hunger=random.randint(10, 25),
            health=random.randint(80, 100)
        )
        agents.append(agent)
    
    print("1. INITIAL AGENT STATE:")
    for agent in agents:
        print(f"   Agent {agent.aid} ({agent.name}):")
        print(f"     Inventory: {agent.inventory}")
        print(f"     Health: {agent.health}, Hunger: {agent.hunger}")
        print()
    
    # Test 2: Agent perception includes inventory
    print("2. AGENT PERCEPTION TEST:")
    bible = Bible()
    
    # Create a mock world object for perception
    class MockWorld:
        def __init__(self):
            self.size = 20
            self.map = None
            self.agents = agents
            self.resources = {}
            self.pending_interactions = []
    
    world = MockWorld()
    
    for agent in agents:
        # Test perception without map (should still include inventory)
        perception = agent.perceive(world, bible)
        agent_info = perception.get('you', {})
        
        print(f"   Agent {agent.aid} perception:")
        print(f"     Includes inventory: {'inventory' in agent_info}")
        if 'inventory' in agent_info:
            print(f"     Perceived inventory: {agent_info['inventory']}")
            print(f"     Matches actual: {agent_info['inventory'] == agent.inventory}")
        print()
    
    # Test 3: Apply outcomes and see inventory changes
    print("3. INVENTORY MODIFICATION TEST:")
    
    for agent in agents:
        print(f"   Agent {agent.aid} before changes:")
        print(f"     Inventory: {agent.inventory}")
        
        # Test consuming food
        if agent.inventory.get('apple', 0) > 0:
            old_apples = agent.inventory['apple']
            old_hunger = agent.hunger
            
            outcome = {
                'inventory': {'apple': -1},
                'hunger': -15,
                'log': 'Ate an apple'
            }
            
            agent.apply_outcome(outcome)
            print(f"     Ate apple: {old_apples} -> {agent.inventory.get('apple', 0)}")
            print(f"     Hunger: {old_hunger} -> {agent.hunger}")
        
        # Test crafting (consume materials, create item)
        if agent.inventory.get('wood', 0) >= 2 and agent.inventory.get('flint', 0) >= 1:
            outcome = {
                'inventory': {'wood': -2, 'flint': -1, 'spear': 1},
                'log': 'Crafted a spear'
            }
            
            agent.apply_outcome(outcome)
            print(f"     Crafted spear: now has {agent.inventory.get('spear', 0)} spear(s)")
        
        print(f"     Final inventory: {agent.inventory}")
        print()
    
    # Test 4: Check if agents can make decisions based on inventory
    print("4. INVENTORY-BASED DECISION SIMULATION:")
    
    for agent in agents:
        print(f"   Agent {agent.aid} decision analysis:")
        
        # Food availability
        food_items = ['apple', 'fish', 'berries']
        total_food = sum(agent.inventory.get(food, 0) for food in food_items)
        print(f"     Total food available: {total_food}")
        
        # Tool availability
        tools = ['spear', 'axe', 'knife']
        total_tools = sum(agent.inventory.get(tool, 0) for tool in tools)
        print(f"     Total tools available: {total_tools}")
        
        # Crafting materials
        materials = ['wood', 'stone', 'flint']
        total_materials = sum(agent.inventory.get(mat, 0) for mat in materials)
        print(f"     Total materials available: {total_materials}")
        
        # Hunger-based decisions
        if agent.hunger > 60:
            print(f"     Agent is hungry ({agent.hunger}) - should eat food")
            if total_food > 0:
                print(f"     ✓ Can satisfy hunger with available food")
            else:
                print(f"     ✗ No food available, should seek food")
        
        # Health-based decisions
        if agent.health < 70:
            print(f"     Agent has low health ({agent.health}) - should rest/heal")
        
        # Resource management
        if total_materials >= 3:
            print(f"     Agent has enough materials for crafting")
        
        print()
    
    # Test 5: Simulate inventory usage over time
    print("5. INVENTORY USAGE SIMULATION:")
    
    for turn in range(1, 4):
        print(f"   Turn {turn}:")
        
        for agent in agents:
            print(f"     Agent {agent.aid}:")
            
            # Increase hunger each turn
            agent.hunger = min(100, agent.hunger + 8)
            
            # Agent tries to eat if hungry
            if agent.hunger > 50:
                food_items = ['apple', 'fish', 'berries']
                for food in food_items:
                    if agent.inventory.get(food, 0) > 0:
                        agent.inventory[food] -= 1
                        agent.hunger = max(0, agent.hunger - 20)
                        print(f"       Ate {food}, hunger now {agent.hunger}")
                        break
                else:
                    print(f"       Hungry ({agent.hunger}) but no food!")
            
            # Try to craft if has materials
            if (agent.inventory.get('wood', 0) >= 1 and 
                agent.inventory.get('flint', 0) >= 1 and 
                agent.inventory.get('knife', 0) == 0):
                agent.inventory['wood'] -= 1
                agent.inventory['flint'] -= 1
                agent.inventory['knife'] = 1
                print(f"       Crafted knife!")
            
            # Health loss if very hungry
            if agent.hunger > 85:
                agent.health = max(0, agent.health - 10)
                print(f"       Starving! Health now {agent.health}")
            
            print(f"       Inventory: {agent.inventory}")
        
        print()
    
    print("=== INVENTORY MECHANICS TEST COMPLETE ===")

if __name__ == "__main__":
    test_inventory_mechanics()