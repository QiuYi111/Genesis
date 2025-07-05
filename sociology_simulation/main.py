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
except ImportError:
    # Handle running as script
    from world import World
    from config import (
        Config, ModelConfig, SimulationConfig, WorldConfig, RuntimeConfig, 
        PerceptionConfig, LoggingConfig, OutputConfig, set_config, get_config
    )

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
    
    logger.info("Starting sociology simulation with Hydra configuration")
    logger.info(f"Era: {cfg.simulation.era_prompt}")
    logger.info(f"World size: {cfg.world.size}x{cfg.world.size}")
    logger.info(f"Number of agents: {cfg.world.num_agents}")
    logger.info(f"Turns: {cfg.runtime.turns}")
    
    async def run_simulation():
        async with aiohttp.ClientSession() as session:
            world = World(cfg.world.size, cfg.simulation.era_prompt, cfg.world.num_agents)
            
            # Show initial map if requested
            if cfg.runtime.show_map_every > 0:
                world.show_map()
            
            await world.initialize(session)
            
            # Initialize agent goals
            tasks = [agent.decide_goal(cfg.simulation.era_prompt, session) for agent in world.agents]
            await asyncio.gather(*tasks)
            
            for t in range(cfg.runtime.turns):
                logger.info(f"===== TURN {t} =====")
                await world.step(session)
                
                # Show map periodically
                if cfg.runtime.show_map_every > 0 and (t+1) % cfg.runtime.show_map_every == 0:
                    world.show_map()
                
                # Show conversations if requested
                if cfg.runtime.show_conversations:
                    conversations = world.get_conversations()
                    if conversations:
                        print("\n=== AGENT CONVERSATIONS ===")
                        for conv in conversations:
                            print(conv)

    asyncio.run(run_simulation())

if __name__ == "__main__":
    main()
