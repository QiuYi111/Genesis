#!/usr/bin/env python3
"""
Simple web simulation runner that doesn't rely on Hydra config.
This creates a basic simulation directly and runs it with web monitoring.
"""

import asyncio
import time
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to path
import sys
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sociology_simulation.web_monitor import start_web_servers, get_monitor, LogCapture
from sociology_simulation.world import World
from sociology_simulation.agent import Agent
from sociology_simulation.trinity import Trinity
from sociology_simulation.bible import Bible
from sociology_simulation.enhanced_llm import get_llm_service


def create_simple_simulation(era_prompt=None, num_agents=None, world_size=None):
    """Create a simple simulation without Hydra config."""
    
    # Basic configuration with command line overrides
    config = {
        'world': {
            'size': world_size or 32,
            'num_agents': num_agents or 8
        },
        'runtime': {
            'turns': 50,
            'show_conversations': True
        },
        'simulation': {
            'era_prompt': era_prompt or "Stone Age primitive tribe learning to use simple tools"
        }
    }
    
    # Create world with all required arguments
    world = World(
        size=config['world']['size'],
        era_prompt=config['simulation']['era_prompt'], 
        num_agents=config['world']['num_agents']
    )
    
    # Create agents
    agents = []
    agent_names = ['Rok', 'Ash', 'Flint', 'Clay', 'Storm', 'River', 'Pine', 'Stone', 'Wolf', 'Bear', 'Eagle', 'Fox']
    
    for i in range(config['world']['num_agents']):
        name = agent_names[i] if i < len(agent_names) else f"Agent{i}"
        
        # Place agent randomly
        import random
        x = random.randint(1, world.size - 2)
        y = random.randint(1, world.size - 2)
        
        agent = Agent(
            aid=i,
            name=name,
            pos=(x, y),
            attributes={'strength': 5, 'intelligence': 5, 'agility': 5},
            inventory={},
        )
        
        # Initialize basic attributes for web display
        agent.current_action = 'idle'
        agent.health = 100
        
        agents.append(agent)
        world.agents.append(agent)
    
    # Generate basic terrain and resources
    _generate_simple_terrain(world)
    
    return world, agents, config


def _generate_simple_terrain(world):
    """Generate simple terrain and resources for the world."""
    import random
    
    # Initialize terrain and resources
    world.terrain = {}
    world.resources = {}
    
    terrain_types = ['GRASSLAND', 'FOREST', 'MOUNTAIN', 'WATER', 'DESERT']
    resource_types = ['wood', 'stone', 'water', 'food', 'fruit']
    
    # Generate terrain using simple noise-like algorithm
    for x in range(world.size):
        for y in range(world.size):
            # Use position to create some patterns
            noise_value = (x * 7 + y * 11) % 100
            
            if noise_value < 30:
                terrain = 'GRASSLAND'
            elif noise_value < 50:
                terrain = 'FOREST'
            elif noise_value < 65:
                terrain = 'MOUNTAIN'
            elif noise_value < 75:
                terrain = 'WATER'
            else:
                terrain = 'DESERT'
            
            world.terrain[(x, y)] = terrain
            
            # Add resources based on terrain
            resources = {}
            if terrain == 'FOREST':
                if random.random() < 0.4:
                    resources['wood'] = random.randint(1, 5)
                if random.random() < 0.3:
                    resources['fruit'] = random.randint(1, 3)
            elif terrain == 'MOUNTAIN':
                if random.random() < 0.3:
                    resources['stone'] = random.randint(1, 4)
            elif terrain == 'WATER':
                if random.random() < 0.5:
                    resources['water'] = random.randint(2, 6)
                if random.random() < 0.2:
                    resources['food'] = random.randint(1, 2)
            elif terrain == 'GRASSLAND':
                if random.random() < 0.2:
                    resources['food'] = random.randint(1, 3)
            
            world.resources[(x, y)] = resources


async def run_simulation_async(era_prompt=None, num_agents=None, world_size=None):
    """Run the simulation asynchronously."""
    
    # Get monitor and start web servers
    monitor = get_monitor()
    log_capture = LogCapture(monitor)
    log_capture.start_capture()
    
    try:
        # Start web servers
        logger.info("Starting web servers...")
        
        # Start WebSocket server
        await monitor.start_websocket_server("localhost", 8765)
        
        # Start HTTP server  
        monitor.setup_http_server("localhost", 8081)
        http_runner = await monitor.start_http_server("localhost", 8081)
        
        logger.info("Web UI available at: http://localhost:8081")
        logger.info("WebSocket server at: ws://localhost:8765")
        
        # Create simulation
        logger.info("Creating simulation...")
        world, agents, config = create_simple_simulation(era_prompt, num_agents, world_size)
        
        # Run simulation turns
        logger.info("Starting simulation...")
        
        for turn in range(config['runtime']['turns']):
            logger.info(f"=== Turn {turn + 1} ===")
            
            # Update world turn
            world.turn = turn + 1
            
            # Simple agent actions
            for agent in agents:
                # Basic random movement
                import random
                actions = ['move_north', 'move_south', 'move_east', 'move_west', 'forage', 'rest']
                action = random.choice(actions)
                
                if action.startswith('move_'):
                    direction = action.split('_')[1]
                    x, y = agent.pos
                    if direction == 'north' and y > 0:
                        agent.pos = (x, y - 1)
                    elif direction == 'south' and y < world.size - 1:
                        agent.pos = (x, y + 1)
                    elif direction == 'east' and x < world.size - 1:
                        agent.pos = (x + 1, y)
                    elif direction == 'west' and x > 0:
                        agent.pos = (x - 1, y)
                
                # Set current action for display
                agent.current_action = action
                
                # Add some basic inventory
                if not hasattr(agent, 'inventory'):
                    agent.inventory = {}
                
                if action == 'forage' and random.random() < 0.3:
                    item = random.choice(['wood', 'stone', 'food', 'fruit'])
                    agent.inventory[item] = agent.inventory.get(item, 0) + 1
                    logger.info(f"{agent.name} found {item}")
                
                # Add basic skills if not present
                if not hasattr(agent, 'skills') or not agent.skills:
                    agent.skills = {'foraging': {'level': 1, 'experience': 0}, 'crafting': {'level': 1, 'experience': 0}}
                
                # Sometimes improve skills
                if random.random() < 0.1 and agent.skills:
                    skill = random.choice(list(agent.skills.keys()))
                    if isinstance(agent.skills[skill], dict):
                        agent.skills[skill]['level'] += 1
                        logger.info(f"{agent.name} improved {skill} to level {agent.skills[skill]['level']}")
                    else:
                        # Simple format
                        agent.skills[skill] += 1
                        logger.info(f"{agent.name} improved {skill} to level {agent.skills[skill]}")
            
            # Terrain and resources are already generated in create_simple_simulation
            
            # Update monitor with current state
            monitor.update_world_data(world, agents, turn + 1)
            
            # Add some log entries
            monitor.add_log_entry("INFO", f"Turn {turn + 1} completed with {len(agents)} active agents")
            
            # Wait a bit for better visualization
            await asyncio.sleep(1)
            
            # Show progress
            if (turn + 1) % 10 == 0:
                logger.info(f"Completed {turn + 1} turns")
        
        logger.info("Simulation completed!")
        
        # Keep servers running for a while after simulation ends
        logger.info("Keeping web servers running for 5 minutes...")
        await asyncio.sleep(300)  # 5 minutes
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    except Exception as e:
        logger.error(f"Error during simulation: {e}")
        raise
    finally:
        # Cleanup
        log_capture.stop_capture()
        await monitor.stop_websocket_server()
        if 'http_runner' in locals():
            await http_runner.cleanup()
        logger.info("Simulation ended")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run sociology simulation with web UI')
    parser.add_argument('--era_prompt', type=str, default=None,
                       help='Era description prompt (default: Stone Age primitive tribe)')
    parser.add_argument('--num_agents', type=int, default=None,
                       help='Number of agents (default: 8)')
    parser.add_argument('--world_size', type=int, default=None,
                       help='World size (default: 32)')
    parser.add_argument('--turns', type=int, default=50,
                       help='Number of simulation turns (default: 50)')
    
    args = parser.parse_args()
    
    logger.info("Starting simple web simulation...")
    logger.info(f"Era: {args.era_prompt or 'Stone Age primitive tribe'}")
    logger.info(f"Agents: {args.num_agents or 8}")
    logger.info(f"World size: {args.world_size or 32}")
    logger.info(f"Turns: {args.turns}")
    
    asyncio.run(run_simulation_async(args.era_prompt, args.num_agents, args.world_size))


if __name__ == "__main__":
    main()