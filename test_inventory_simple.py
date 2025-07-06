#!/usr/bin/env python3
"""Simple test to check if agents use their inventory"""

import asyncio
import aiohttp
from sociology_simulation.world import World
from sociology_simulation.mcp_integration_patch import apply_mcp_integration
from sociology_simulation.config import set_config
from sociology_simulation.enhanced_llm import get_llm_service
from loguru import logger
import sys

async def test_inventory_usage():
    """Test if agents actually use their inventory items"""
    
    # Initialize config first
    set_config({
        "openai_api_key": "dummy_key",
        "openai_base_url": "http://localhost:8000/v1",
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 1000
    })
    
    world = World(size=32, era_prompt='Stone Age survival test', num_agents=2)
    
    # Apply MCP integration
    apply_mcp_integration(world)
    
    async with aiohttp.ClientSession() as session:
        try:
            await world.initialize(session)
            
            # Print initial agent inventories
            print('\n=== INITIAL AGENT INVENTORIES ===')
            for agent in world.agents:
                print(f'Agent {agent.aid} ({agent.name}):')
                print(f'  Inventory: {agent.inventory}')
                print(f'  Health: {agent.health}, Hunger: {agent.hunger}')
                print(f'  Goal: {agent.goal}')
            
            # Test 1: Check if agent perception includes inventory
            print('\n=== TEST 1: Agent Perception Test ===')
            for agent in world.agents:
                perception = agent.perceive(world, world.bible)
                agent_info = perception.get('you', {})
                print(f'Agent {agent.aid} perceives inventory: {agent_info.get("inventory", "NOT FOUND")}')
            
            # Test 2: Run a few actions and observe inventory changes
            print('\n=== TEST 2: Action Execution Test ===')
            for turn in range(1, 3):
                print(f'\n--- Turn {turn} ---')
                
                for agent in world.agents:
                    if agent.health <= 0:
                        continue
                        
                    print(f'\nAgent {agent.aid} before action:')
                    print(f'  Inventory: {agent.inventory}')
                    print(f'  Health: {agent.health}, Hunger: {agent.hunger}')
                    
                    # Try to execute action
                    try:
                        # This should use MCP to execute actions
                        await agent.act(world, world.bible, world.era_prompt, session, None)
                        print(f'  After action:')
                        print(f'    Inventory: {agent.inventory}')
                        print(f'    Health: {agent.health}, Hunger: {agent.hunger}')
                    except Exception as e:
                        print(f'  Action failed: {e}')
                        # Let's see what the error is
                        import traceback
                        traceback.print_exc()
            
            # Test 3: Manual inventory manipulation test
            print('\n=== TEST 3: Manual Inventory Test ===')
            for agent in world.agents:
                if agent.health <= 0:
                    continue
                    
                print(f'Agent {agent.aid} manual test:')
                old_inventory = agent.inventory.copy()
                
                # Try to eat food if hungry
                if agent.hunger > 30:
                    food_items = ['apple', 'fish', 'berries']
                    for food in food_items:
                        if agent.inventory.get(food, 0) > 0:
                            old_count = agent.inventory[food]
                            agent.inventory[food] -= 1
                            agent.hunger = max(0, agent.hunger - 15)
                            print(f'  Ate {food}: {old_count} -> {agent.inventory[food]}')
                            print(f'  Hunger reduced to: {agent.hunger}')
                            break
                    else:
                        print(f'  Hungry ({agent.hunger}) but no food to eat')
                
                # Try to use tools
                if 'wood' in agent.inventory and agent.inventory['wood'] > 0:
                    print(f'  Has wood: {agent.inventory["wood"]} (could craft tools)')
                
                if 'stone' in agent.inventory and agent.inventory['stone'] > 0:
                    print(f'  Has stone: {agent.inventory["stone"]} (could craft tools)')
                
                print(f'  Inventory changes: {old_inventory} -> {agent.inventory}')
                
        except Exception as e:
            print(f'Test failed: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_inventory_usage())