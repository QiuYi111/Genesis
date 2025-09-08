#!/usr/bin/env python3
"""
Run sociology simulation with web data export
This script runs a short simulation and exports data for web visualization
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path

# Add the sociology_simulation module to path
sys.path.insert(0, str(Path(__file__).parent))

from sociology_simulation.world import World
from sociology_simulation.config import set_config, Config, ModelConfig, SimulationConfig, WorldConfig, RuntimeConfig, PerceptionConfig, LoggingConfig, OutputConfig
from sociology_simulation.prompts import init_prompt_manager
from sociology_simulation.enhanced_llm import init_llm_service
from sociology_simulation.web_export import export_web_data

def create_test_config():
    """Create a minimal configuration for testing"""
    return Config(
        model=ModelConfig(
            api_key_env="DEEPSEEK_API_KEY",
            agent_model="deepseek-chat",
            trinity_model="deepseek-chat",
            base_url="https://api.deepseek.com",
            temperatures={"agent": 0.7, "trinity": 0.5},
            max_retries=3,
            retry_delay=1.0
        ),
        simulation=SimulationConfig(
            era_prompt="石器时代",
            terrain_types=["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"],
            resource_rules={
                "wood": {"FOREST": 0.5},
                "fish": {"OCEAN": 0.4},
                "stone": {"MOUNTAIN": 0.6}
            },
            agent_attributes={"strength": {"min": 1, "max": 10}},
            agent_inventory={"wood": {"min": 0, "max": 2}},
            agent_age={"min": 17, "max": 70},
            survival={"health": 100, "hunger": 0}
        ),
        world=WorldConfig(size=32, num_agents=10),  # Smaller world for testing
        runtime=RuntimeConfig(turns=5, show_map_every=0, show_conversations=True),  # Short simulation
        perception=PerceptionConfig(vision_radius=5),
        logging=LoggingConfig(
            level="INFO",
            format="{time} | {level} | {message}",
            console_format="{message}",
            file={"enabled": False},
            console={"enabled": True, "level": "INFO"}
        ),
        output=OutputConfig()
    )

async def run_test_simulation():
    """Run a test simulation with web export"""
    print("🚀 Starting test simulation with web export...")
    
    # Set up configuration
    config = create_test_config()
    set_config(config)
    
    # Initialize services (these will use fallback data if API fails)
    prompts_config_path = "sociology_simulation/conf/prompts.yaml"
    prompt_manager = init_prompt_manager(prompts_config_path)
    llm_service = init_llm_service(prompt_manager)
    
    print(f"📊 World: {config.world.size}x{config.world.size}")
    print(f"👥 Agents: {config.world.num_agents}")
    print(f"⏱️  Turns: {config.runtime.turns}")
    print()
    
    async with aiohttp.ClientSession() as session:
        # Create world
        world = World(
            size=config.world.size,
            era_prompt=config.simulation.era_prompt,
            num_agents=config.world.num_agents
        )
        
        try:
            # Initialize world (this will create the web export data)
            await world.initialize(session)
            print("✅ World initialized with terrain and resources")
            
            # Generate agent goals (may fail due to API, but we'll continue)
            print("🎯 Setting agent goals...")
            tasks = []
            for agent in world.agents:
                try:
                    task = agent.decide_goal(config.simulation.era_prompt, session)
                    tasks.append(task)
                except Exception as e:
                    print(f"⚠️  Agent {agent.aid} goal generation failed: {e}")
            
            if tasks:
                try:
                    await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10.0)
                except asyncio.TimeoutError:
                    print("⚠️  Agent goal generation timed out, continuing...")
            
            # Run simulation turns
            for t in range(config.runtime.turns):
                print(f"\n===== TURN {t} =====")
                try:
                    await world.step(session)
                    print(f"✅ Turn {t} completed")
                except Exception as e:
                    print(f"⚠️  Turn {t} had errors: {e}")
                    # Continue anyway to generate web data
            
        except Exception as e:
            print(f"⚠️  Simulation had issues: {e}")
            print("🔄 Continuing to generate web export with available data...")
        
        # Export final web data
        try:
            final_export_file = export_web_data("test_simulation_data.json")
            print(f"\n🎉 Web data exported successfully!")
            print(f"📁 File: {final_export_file}")
            
            # Show some stats
            if os.path.exists(final_export_file):
                import json
                with open(final_export_file, 'r') as f:
                    data = json.load(f)
                
                print(f"📈 Simulation Stats:")
                print(f"   • Era: {data['metadata']['era']}")
                print(f"   • Turns: {len(data['turns'])}")
                print(f"   • Final agents: {len(data['turns'][-1]['agents']) if data['turns'] else 0}")
                print(f"   • Terrain types: {len(data['metadata']['terrain_types'])}")
                
                # Check if terrain data exists
                if data['world']['terrain']:
                    terrain_count = {}
                    for row in data['world']['terrain']:
                        for cell in row:
                            terrain_count[cell] = terrain_count.get(cell, 0) + 1
                    print(f"   • Terrain distribution:")
                    for terrain, count in terrain_count.items():
                        print(f"     - {terrain}: {count} cells")
                
                print(f"\n🌐 To view the simulation:")
                print(f"   1. Open sociology_simulation_web_ui.html in a browser")
                print(f"   2. Click 'Choose Log File' and select: {final_export_file}")
                print(f"   3. Explore the visualization!")
                
        except Exception as e:
            print(f"❌ Failed to export web data: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main entry point"""
    print("🔬 Sociology Simulation Web Export Test")
    print("=" * 50)
    
    try:
        asyncio.run(run_test_simulation())
    except KeyboardInterrupt:
        print("\n⏹️  Simulation interrupted by user")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()