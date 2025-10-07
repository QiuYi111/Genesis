"""Main entry point for sociology simulation using Hydra"""
import asyncio
import os
import time
from pathlib import Path
from typing import Optional, TYPE_CHECKING

import aiohttp
import hydra
from loguru import logger
from omegaconf import DictConfig

try:
    from .world import World
    from .config import (
        Config, ModelConfig, SimulationConfig, WorldConfig, RuntimeConfig, 
        PerceptionConfig, LoggingConfig, OutputConfig, set_config, get_config
    )
    from .prompts import init_prompt_manager
    from .enhanced_llm import init_llm_service
    from .output_formatter import get_formatter, set_formatter_options

if TYPE_CHECKING:
    from .web_monitor import SimulationMonitor
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

async def run_simulation_from_config(
    cfg: DictConfig,
    monitor: Optional["SimulationMonitor"] = None,
) -> None:
    """Run the sociology simulation using a composed Hydra config."""

    # Convert to dataclasses and set global configuration for downstream modules
    config = hydra_config_to_dataclasses(cfg)
    set_config(config)

    # Initialize prompt manager and LLM service
    prompts_config_path = "sociology_simulation/conf/prompts.yaml"
    prompt_manager = init_prompt_manager(prompts_config_path)
    init_llm_service(prompt_manager)

    logger.info("Starting sociology simulation with Hydra configuration")
    logger.info(f"Initialized {len(prompt_manager.list_templates())} prompt templates")
    logger.info(f"Prompt statistics: {prompt_manager.get_statistics()}")
    logger.info(f"Era: {cfg.simulation.era_prompt}")
    logger.info(f"World size: {cfg.world.size}x{cfg.world.size}")
    logger.info(f"Number of agents: {cfg.world.num_agents}")
    logger.info(f"Turns: {cfg.runtime.turns}")

    # Initialize formatter
    formatter = get_formatter()
    set_formatter_options(
        use_colors=cfg.output.get("use_colors", True),
        verbose=cfg.output.get("verbose", True),
    )

    # Notify monitor about simulation plan
    if monitor:
        monitor.update_status(
            state="initializing",
            era=cfg.simulation.era_prompt,
            total_turns=cfg.runtime.turns,
            num_agents=cfg.world.num_agents,
            world_size=cfg.world.size,
        )

    # Print simulation start banner
    formatter.print_simulation_start(
        era=cfg.simulation.era_prompt,
        world_size=cfg.world.size,
        num_agents=cfg.world.num_agents,
        total_turns=cfg.runtime.turns,
    )

    async with aiohttp.ClientSession() as session:
        world = World(cfg.world.size, cfg.simulation.era_prompt, cfg.world.num_agents)

        if monitor:
            monitor.attach_world(world)

        await world.initialize(session)

        if monitor:
            monitor.add_log_entry("INFO", "World initialization complete")
            monitor.update_world_data(world, world.agents, 0)
            monitor.update_status(state="running", started_at=time.time(), turn=0)

        # Show initial map if requested
        if cfg.runtime.show_map_every > 0:
            world.show_map()

        # Initialize agent goals
        tasks = [agent.decide_goal(cfg.simulation.era_prompt, session) for agent in world.agents]
        await asyncio.gather(*tasks)

        if monitor:
            monitor.add_log_entry("INFO", "Agent goals initialised")

        # Display agent goals
        print(formatter.format_header("AGENT GOALS", 2))
        for agent in world.agents:
            goal = getattr(agent, "goal", "No goal set")
            print(f"  {formatter.format_world_event(f'{agent.name}(aid={agent.aid}): {goal}', 'info')}")

        cumulative_births = 0
        cumulative_deaths = 0
        prev_alive_ids = {a.aid for a in world.agents if a.health > 0}

        for t in range(cfg.runtime.turns):
            if monitor and monitor.should_stop():
                monitor.add_log_entry("INFO", "Stop requested – finishing current turn")
                print(formatter.format_world_event("Stop requested – ending simulation", "warning"))
                break

            formatter.print_turn_start(t + 1)

            # Track turn statistics
            turn_stats = {
                "actions_completed": 0,
                "actions_failed": 0,
                "social_interactions": 0,
                "resource_gathered": 0,
                "discoveries": [],
                "deaths": [],
            }

            # Snapshot alive agents pre-step
            pre_ids = prev_alive_ids

            await world.step(session)

            # Snapshot alive agents post-step
            post_alive_ids = {a.aid for a in world.agents if a.health > 0}

            deaths_this_turn = len(pre_ids - post_alive_ids)
            births_this_turn = len(post_alive_ids - pre_ids)

            cumulative_deaths += deaths_this_turn
            cumulative_births += births_this_turn
            prev_alive_ids = post_alive_ids

            turn_stats["deaths"] = deaths_this_turn
            turn_stats["births"] = births_this_turn

            formatter.update_stats(
                active_agents=len(post_alive_ids),
                total_agents=cfg.world.num_agents + cumulative_births,
                actions_completed=formatter.stats.actions_completed + turn_stats["actions_completed"],
                actions_failed=formatter.stats.actions_failed + turn_stats["actions_failed"],
                social_interactions=formatter.stats.social_interactions + turn_stats["social_interactions"],
                resource_gathered=formatter.stats.resource_gathered + turn_stats["resource_gathered"],
                agent_deaths=cumulative_deaths,
            )

            if cfg.runtime.show_map_every > 0 and (t + 1) % cfg.runtime.show_map_every == 0:
                world.show_map()

            if cfg.output.get("show_agent_status", True) and (t + 1) % 5 == 0:
                print(formatter.format_header("AGENT STATUS", 3))
                agent_data = []
                for agent in world.agents:
                    agent_data.append(
                        {
                            "name": agent.name,
                            "age": agent.age,
                            "health": agent.health,
                            "x": agent.pos[0],
                            "y": agent.pos[1],
                            "current_action": getattr(agent, "current_action", "idle"),
                        }
                    )
                print(formatter.format_agent_status_table(agent_data))

            if cfg.runtime.show_conversations:
                conversations = world.get_conversations()
                if conversations:
                    print(formatter.format_header("AGENT CONVERSATIONS", 3))
                    for conv in conversations:
                        print(f"  {formatter.format_world_event(conv, 'info')}")

            formatter.print_turn_summary(turn_stats)

            if (t + 1) % 10 == 0:
                print(formatter.format_statistics_summary())

            if monitor:
                monitor.update_world_data(world, world.agents, t + 1)
                monitor.add_log_entry("INFO", f"Turn {t + 1} completed")

        formatter.print_simulation_end()

        if monitor:
            monitor.add_log_entry("INFO", "Simulation finished")

        try:
            from .web_export import export_web_data

            final_export_file = export_web_data("final_simulation_data.json")
            print(
                formatter.format_world_event(
                    f"Final simulation data exported to: {final_export_file}",
                    "success",
                )
            )
        except Exception as e:
            print(formatter.format_world_event(f"Failed to export web data: {e}", "error"))

        if monitor:
            final_state = "stopped" if monitor.should_stop() else "completed"
            monitor.detach_world()
            monitor.clear_stop_request()
            monitor.update_status(
                state="idle",
                stopped_at=time.time(),
                last_outcome=final_state,
            )


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Main entry point with Hydra configuration."""

    configure_logging(cfg)
    asyncio.run(run_simulation_from_config(cfg))


if __name__ == "__main__":
    main()
