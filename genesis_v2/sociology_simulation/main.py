"""
Main entry point for Project Genesis simulation.
Command-line interface for running the simulation.
"""

import asyncio
import sys
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf
from loguru import logger

from .core.simulation import Simulation


@hydra.main(version_base=None, config_path="conf", config_name="config")
def main(cfg: DictConfig) -> None:
    """Main entry point with Hydra configuration"""
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=cfg.get("runtime", {}).get("log_level", "INFO"),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: >8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.info("🌍 Starting Project Genesis - LLM-driven Sociology Simulation")
    logger.info(f"Configuration: {OmegaConf.to_yaml(cfg)}")
    
    try:
        # Create and run simulation
        simulation = Simulation(cfg)
        
        # Run the simulation
        asyncio.run(simulation.run())
        
        # Save final state
        output_dir = Path(hydra.core.hydra_config.HydraConfig.get().runtime.output_dir)
        simulation.save_state(str(output_dir / "final_state.json"))
        
        logger.success("✅ Simulation completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("⏸️ Simulation interrupted by user")
    except Exception as e:
        logger.error(f"❌ Simulation failed: {e}")
        raise


def run_simple_simulation(
    width: int = 32,
    height: int = 32,
    agents: int = 5,
    turns: int = 50,
    era: str = "stone age tribes",
    seed: int = 42,
    provider: str = "mock"
) -> None:
    """Run a simple simulation with basic parameters"""
    
    config = OmegaConf.create({
        "simulation": {
            "name": "Simple Genesis Simulation",
            "era_prompt": era,
            "seed": seed
        },
        "world": {
            "width": width,
            "height": height
        },
        "agents": {
            "count": agents,
            "spawn_radius": min(width, height) // 4
        },
        "llm": {
            "provider": provider
        },
        "runtime": {
            "max_turns": turns,
            "turn_delay": 0.1,
            "log_level": "INFO"
        },
        "output": {
            "show_stats": True,
            "show_map": True
        }
    })
    
    simulation = Simulation(config)
    return asyncio.run(simulation.run())


if __name__ == "__main__":
    # Allow direct execution for testing
    if len(sys.argv) == 1:
        # Run with default simple configuration
        asyncio.run(run_simple_simulation())
    else:
        # Use Hydra configuration
        main()