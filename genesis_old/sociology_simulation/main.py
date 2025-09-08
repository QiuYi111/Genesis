"""Main entry point for sociology simulation using Hydra"""
import asyncio
import aiohttp
import os
from pathlib import Path
from loguru import logger
from omegaconf import DictConfig, OmegaConf
import hydra

try:
    from .world import World
    from .config import (
        Config, ModelConfig, SimulationConfig, WorldConfig, RuntimeConfig, 
        PerceptionConfig, LoggingConfig, OutputConfig, set_config, get_config
    )
    from .prompts import init_prompt_manager
    from .enhanced_llm import init_llm_service
    from .output_formatter import get_formatter, set_formatter_options
except ImportError:
    # Handle running as script
    from world import World
    from config import (
        Config, ModelConfig, SimulationConfig, WorldConfig, RuntimeConfig, 
        PerceptionConfig, LoggingConfig, OutputConfig, set_config, get_config
    )
    from prompts import init_prompt_manager
    from enhanced_llm import init_llm_service
    from output_formatter import get_formatter, set_formatter_options

def configure_logging(cfg: DictConfig):
    """Configure logging based on Hydra configuration"""
    logger.remove()
    
    # Console logging
    if cfg.logging.console.enabled:
        logger.add(
            lambda msg: print(msg, end=""), 
            level=cfg.logging.console.level,
            format=cfg.logging.console_format
        )
    
    # File logging
    if cfg.logging.file.enabled:
        os.makedirs(Path(cfg.logging.file.path).parent, exist_ok=True)
        logger.add(
            cfg.logging.file.path,
            rotation=cfg.logging.file.rotation,
            retention=cfg.logging.file.retention,
            compression=cfg.logging.file.compression,
            level=cfg.logging.level,
            format=cfg.logging.format
        )

def hydra_config_to_dataclasses(cfg: DictConfig) -> Config:
    """Convert Hydra DictConfig to dataclass structures"""
    return Config(
        model=ModelConfig(**cfg.model),
        simulation=SimulationConfig(**cfg.simulation),
        world=WorldConfig(**cfg.world),
        runtime=RuntimeConfig(**cfg.runtime),
        perception=PerceptionConfig(**cfg.perception),
        logging=LoggingConfig(**cfg.logging),
        output=OutputConfig(**cfg.output)
    )

@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Main entry point with Hydra configuration"""
    
    # Configure logging first
    configure_logging(cfg)
    
    # Convert to dataclasses and set global config
    config = hydra_config_to_dataclasses(cfg)
    set_config(config)
    
    # Initialize prompt manager and enhanced LLM service
    # Use English templates from config file
    prompts_config_path = "sociology_simulation/conf/prompts.yaml"
    prompt_manager = init_prompt_manager(prompts_config_path)
    
    # Initialize LLM provider based on configuration
    provider_type = cfg.model.get('provider', 'deepseek')
    logger.info(f"Using LLM provider: {provider_type}")
    
    if provider_type == 'null':
        # Use NullProvider for offline testing
        logger.info("Running in offline mode with NullProvider")
        llm_service = init_llm_service(prompt_manager)
        # Configure existing service to use NullProvider behavior
        # Note: In the future, this will be fully integrated with the new provider system
    else:
        # Use existing enhanced LLM service
        llm_service = init_llm_service(prompt_manager)
    
    logger.info("Starting sociology simulation with Hydra configuration")
    logger.info(f"Initialized {len(prompt_manager.list_templates())} prompt templates")
    logger.info(f"Prompt statistics: {prompt_manager.get_statistics()}")
    logger.info(f"Era: {cfg.simulation.era_prompt}")
    logger.info(f"World size: {cfg.world.size}x{cfg.world.size}")
    logger.info(f"Number of agents: {cfg.world.num_agents}")
    logger.info(f"Turns: {cfg.runtime.turns}")
    
    async def run_simulation():
        # Initialize formatter
        formatter = get_formatter()
        set_formatter_options(
            use_colors=cfg.output.get('use_colors', True),
            verbose=cfg.output.get('verbose', True)
        )
        
        # Print simulation start
        formatter.print_simulation_start(
            era=cfg.simulation.era_prompt,
            world_size=cfg.world.size,
            num_agents=cfg.world.num_agents,
            total_turns=cfg.runtime.turns
        )
        
        # Check if we need network session based on provider
        provider_type = cfg.model.get('provider', 'deepseek')
        use_network = provider_type != 'null'
        
        if use_network:
            async with aiohttp.ClientSession() as session:
                world = World(cfg.world.size, cfg.simulation.era_prompt, cfg.world.num_agents)
                
                await world.initialize(session)
                
                # Show initial map if requested
                if cfg.runtime.show_map_every > 0:
                    world.show_map()
                
                # Initialize agent goals
                tasks = [agent.decide_goal(cfg.simulation.era_prompt, session) for agent in world.agents]
                await asyncio.gather(*tasks)
                
                # Run simulation with network
                await run_simulation_with_session(session, world, cfg, formatter)
        else:
            # Offline mode with NullProvider - no network session needed
            world = World(cfg.world.size, cfg.simulation.era_prompt, cfg.world.num_agents)
            
            # Use None for session in offline mode
            await world.initialize(None)
            
            # Show initial map if requested
            if cfg.runtime.show_map_every > 0:
                world.show_map()
            
            # Initialize agent goals without network
            for agent in world.agents:
                # Use a simple deterministic goal for offline mode
                agent.goal = "Survive and gather resources"
            
            # Run simulation without network
            await run_simulation_offline(world, cfg, formatter)
            
            # Display agent goals
            print(formatter.format_header("AGENT GOALS", 2))
            for agent in world.agents:
                goal = getattr(agent, 'goal', 'No goal set')
                print(f"  {formatter.format_world_event(f'{agent.name}(aid={agent.aid}): {goal}', 'info')}")
            
            for t in range(cfg.runtime.turns):
                formatter.print_turn_start(t + 1)
                
                # Track turn statistics
                turn_stats = {
                    'actions_completed': 0,
                    'actions_failed': 0,
                    'social_interactions': 0,
                    'resource_gathered': 0,
                    'discoveries': [],
                    'deaths': []
                }
                
                # Store initial agent count
                initial_agent_count = len([a for a in world.agents if a.health > 0])
                
                await world.step(session)
                
                # Calculate turn statistics
                final_agent_count = len([a for a in world.agents if a.health > 0])
                turn_stats['deaths'] = initial_agent_count - final_agent_count
                
                # Update formatter stats
                formatter.update_stats(
                    active_agents=final_agent_count,
                    actions_completed=formatter.stats.actions_completed + turn_stats['actions_completed'],
                    actions_failed=formatter.stats.actions_failed + turn_stats['actions_failed'],
                    social_interactions=formatter.stats.social_interactions + turn_stats['social_interactions'],
                    resource_gathered=formatter.stats.resource_gathered + turn_stats['resource_gathered'],
                    agent_deaths=formatter.stats.agent_deaths + turn_stats['deaths']
                )
                
                # Show map periodically
                if cfg.runtime.show_map_every > 0 and (t+1) % cfg.runtime.show_map_every == 0:
                    world.show_map()
                
                # Show agent status table every few turns
                if cfg.output.get('show_agent_status', True) and (t+1) % 5 == 0:
                    print(formatter.format_header("AGENT STATUS", 3))
                    agent_data = []
                    for agent in world.agents:
                        agent_data.append({
                            'name': agent.name,
                            'age': agent.age,
                            'health': agent.health,
                            'x': agent.pos[0],
                            'y': agent.pos[1],
                            'current_action': getattr(agent, 'current_action', 'idle')
                        })
                    print(formatter.format_agent_status_table(agent_data))
                
                # Show conversations if requested
                if cfg.runtime.show_conversations:
                    conversations = world.get_conversations()
                    if conversations:
                        print(formatter.format_header("AGENT CONVERSATIONS", 3))
                        for conv in conversations:
                            print(f"  {formatter.format_world_event(conv, 'info')}")
                
                # Print turn summary
                formatter.print_turn_summary(turn_stats)
                
                # Show statistics summary every 10 turns
                if (t+1) % 10 == 0:
                    print(formatter.format_statistics_summary())
            
            # Print simulation end
            formatter.print_simulation_end()
            
            # Export final web data
            try:
                from .web_export import export_web_data
                final_export_file = export_web_data("final_simulation_data.json")
                print(formatter.format_world_event(f"Final simulation data exported to: {final_export_file}", 'success'))
            except Exception as e:
                print(formatter.format_world_event(f"Failed to export web data: {e}", 'error'))

async def run_simulation_with_session(session, world, cfg, formatter):
    """Run simulation with network session (existing logic)"""
    # Display agent goals
    print(formatter.format_header("AGENT GOALS", 2))
    for agent in world.agents:
        goal = getattr(agent, 'goal', 'No goal set')
        print(f"  {formatter.format_world_event(f'{agent.name}(aid={agent.aid}): {goal}', 'info')}")
    
    for t in range(cfg.runtime.turns):
        formatter.print_turn_start(t + 1)
        
        # Track turn statistics
        turn_stats = {
            'actions_completed': 0,
            'actions_failed': 0,
            'social_interactions': 0,
            'resource_gathered': 0,
            'discoveries': [],
            'deaths': []
        }
        
        # Store initial agent count
        initial_agent_count = len([a for a in world.agents if a.health > 0])
        
        await world.step(session)
        
        # Calculate turn statistics
        final_agent_count = len([a for a in world.agents if a.health > 0])
        turn_stats['deaths'] = initial_agent_count - final_agent_count
        
        # Update formatter stats
        formatter.update_stats(
            active_agents=final_agent_count,
            actions_completed=formatter.stats.actions_completed + turn_stats['actions_completed'],
            actions_failed=formatter.stats.actions_failed + turn_stats['actions_failed'],
            social_interactions=formatter.stats.social_interactions + turn_stats['social_interactions'],
            resource_gathered=formatter.stats.resource_gathered + turn_stats['resource_gathered'],
            agent_deaths=formatter.stats.agent_deaths + turn_stats['deaths']
        )
        
        # Show map periodically
        if cfg.runtime.show_map_every > 0 and (t+1) % cfg.runtime.show_map_every == 0:
            world.show_map()
        
        # Show agent status table every few turns
        if cfg.output.get('show_agent_status', True) and (t+1) % 5 == 0:
            print(formatter.format_header("AGENT STATUS", 3))
            agent_data = []
            for agent in world.agents:
                agent_data.append({
                    'name': agent.name,
                    'age': agent.age,
                    'health': agent.health,
                    'x': agent.pos[0],
                    'y': agent.pos[1],
                    'current_action': getattr(agent, 'current_action', 'idle')
                })
            print(formatter.format_agent_status_table(agent_data))
        
        # Show conversations if requested
        if cfg.runtime.show_conversations:
            conversations = world.get_conversations()
            if conversations:
                print(formatter.format_header("AGENT CONVERSATIONS", 3))
                for conv in conversations:
                    print(f"  {formatter.format_world_event(conv, 'info')}")
        
        # Print turn summary
        formatter.print_turn_summary(turn_stats)
        
        # Show statistics summary every 10 turns
        if (t+1) % 10 == 0:
            print(formatter.format_statistics_summary())
    
    # Print simulation end
    formatter.print_simulation_end()

async def run_simulation_offline(world, cfg, formatter):
    """Run simulation in offline mode without network"""
    # Display agent goals
    print(formatter.format_header("AGENT GOALS", 2))
    for agent in world.agents:
        goal = getattr(agent, 'goal', 'No goal set')
        print(f"  {formatter.format_world_event(f'{agent.name}(aid={agent.aid}): {goal}', 'info')}")
    
    for t in range(cfg.runtime.turns):
        formatter.print_turn_start(t + 1)
        
        # Track turn statistics
        turn_stats = {
            'actions_completed': 0,
            'actions_failed': 0,
            'social_interactions': 0,
            'resource_gathered': 0,
            'discoveries': [],
            'deaths': []
        }
        
        # Store initial agent count
        initial_agent_count = len([a for a in world.agents if a.health > 0])
        
        # In offline mode, pass None as session
        await world.step(None)
        
        # Calculate turn statistics
        final_agent_count = len([a for a in world.agents if a.health > 0])
        turn_stats['deaths'] = initial_agent_count - final_agent_count
        
        # Update formatter stats
        formatter.update_stats(
            active_agents=final_agent_count,
            actions_completed=formatter.stats.actions_completed + turn_stats['actions_completed'],
            actions_failed=formatter.stats.actions_failed + turn_stats['actions_failed'],
            social_interactions=formatter.stats.social_interactions + turn_stats['social_interactions'],
            resource_gathered=formatter.stats.resource_gathered + turn_stats['resource_gathered'],
            agent_deaths=formatter.stats.agent_deaths + turn_stats['deaths']
        )
        
        # Show map periodically
        if cfg.runtime.show_map_every > 0 and (t+1) % cfg.runtime.show_map_every == 0:
            world.show_map()
        
        # Show agent status table every few turns
        if cfg.output.get('show_agent_status', True) and (t+1) % 5 == 0:
            print(formatter.format_header("AGENT STATUS", 3))
            agent_data = []
            for agent in world.agents:
                agent_data.append({
                    'name': agent.name,
                    'age': agent.age,
                    'health': agent.health,
                    'x': agent.pos[0],
                    'y': agent.pos[1],
                    'current_action': getattr(agent, 'current_action', 'idle')
                })
            print(formatter.format_agent_status_table(agent_data))
        
        # Show conversations if requested
        if cfg.runtime.show_conversations:
            conversations = world.get_conversations()
            if conversations:
                print(formatter.format_header("AGENT CONVERSATIONS", 3))
                for conv in conversations:
                    print(f"  {formatter.format_world_event(conv, 'info')}")
        
        # Print turn summary
        formatter.print_turn_summary(turn_stats)
        
        # Show statistics summary every 10 turns
        if (t+1) % 10 == 0:
            print(formatter.format_statistics_summary())
    
    # Print simulation end
    formatter.print_simulation_end()

    asyncio.run(run_simulation())

if __name__ == "__main__":
    main()
