"""Configuration parameters for sociology simulation using Hydra"""
import os
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from omegaconf import OmegaConf

# Terrain color mapping (static)
TERRAIN_COLORS = {
    "OCEAN": (0.129, 0.588, 0.953),    # blue
    "FOREST": (0.298, 0.686, 0.314),   # green
    "GRASSLAND": (0.667, 0.867, 0.467),# light green
    "MOUNTAIN": (0.5, 0.5, 0.5),       # gray
    "DESERT": (0.94, 0.82, 0.57),      # sand
    "RIVER": (0.176, 0.698, 0.902),    # light blue
    "CAVE": (0.3, 0.3, 0.3),           # dark gray
    "SWAMP": (0.4, 0.6, 0.4),          # dark green
    "TUNDRA": (0.8, 0.9, 0.9),         # light gray
    "JUNGLE": (0.2, 0.5, 0.2),         # dark green
    "PLATEAU": (0.7, 0.6, 0.5),        # brown
    "VALLEY": (0.6, 0.8, 0.3),         # yellowish green
    "VOLCANIC": (0.6, 0.2, 0.2),       # dark red
    "OASIS": (0.3, 0.8, 0.6),          # turquoise
    "RUINS": (0.6, 0.6, 0.5),          # brownish gray
    "CRYSTAL_CAVE": (0.8, 0.4, 0.9),   # purple
    "LAVA_FIELD": (0.8, 0.3, 0.1)      # red-orange
}

@dataclass
class ModelConfig:
    """Model configuration"""
    api_key_env: str
    agent_model: str
    trinity_model: str
    base_url: str
    temperatures: Dict[str, float]
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass  
class SimulationConfig:
    """Simulation-specific configuration"""
    era_prompt: str
    terrain_types: List[str]
    resource_rules: Dict[str, Dict[str, float]]
    agent_attributes: Dict[str, Dict[str, int]]
    agent_inventory: Dict[str, Dict[str, int]]
    agent_age: Dict[str, int]
    survival: Dict[str, int]

@dataclass
class WorldConfig:
    """World configuration"""
    size: int = 64
    num_agents: int = 20

@dataclass
class RuntimeConfig:
    """Runtime configuration"""
    turns: int = 10
    show_map_every: int = 1
    show_conversations: bool = False
    timeout_per_agent: float = 15.0

@dataclass
class PerceptionConfig:
    """Perception configuration"""
    vision_radius: int = 5

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str
    format: str
    console_format: str
    file: Dict[str, Any]
    console: Dict[str, Any]

@dataclass
class OutputConfig:
    """Output configuration"""
    log_level: str = "INFO"
    logs_dir: str = "logs"
    log_rotation: str = "10 MB"
    log_retention: str = "30 days"
    log_compression: str = "zip"
    use_colors: bool = True
    verbose: bool = True
    show_agent_status: bool = True

@dataclass
class Config:
    """Main configuration class"""
    model: ModelConfig
    simulation: SimulationConfig
    world: WorldConfig
    runtime: RuntimeConfig
    perception: PerceptionConfig
    logging: LoggingConfig
    output: OutputConfig

# Global configuration instance (will be set by Hydra)
cfg: Optional[Config] = None

def get_config() -> Config:
    """Get the global configuration instance"""
    if cfg is None:
        raise RuntimeError("Configuration not initialized. Use set_config() first.")
    return cfg

def set_config(config: Config):
    """Set the global configuration instance"""
    global cfg
    cfg = config

# Backward compatibility helpers
def get_api_key() -> str:
    """Get API key from environment"""
    config = get_config()
    return os.getenv(config.model.api_key_env, "")

def get_agent_model() -> str:
    """Get agent model name"""
    return get_config().model.agent_model

def get_trinity_model() -> str:
    """Get Trinity model name"""
    return get_config().model.trinity_model

def get_vision_radius() -> int:
    """Get vision radius"""
    return get_config().perception.vision_radius

def get_terrain_types() -> List[str]:
    """Get terrain types"""
    return get_config().simulation.terrain_types

def get_resource_rules() -> Dict[str, Dict[str, float]]:
    """Get resource rules"""
    return get_config().simulation.resource_rules

# Legacy constants for backward compatibility
OPENAI_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Will be deprecated
MODEL_AGENT = "deepseek-chat"                   # Will be deprecated  
MODEL_TRINITY = "deepseek-chat"                 # Will be deprecated
VISION_RADIUS = 5                               # Will be deprecated
DEFAULT_TERRAIN = ["OCEAN", "FOREST", "GRASSLAND", "MOUNTAIN"]  # Will be deprecated
DEFAULT_RESOURCE_RULES = {                      # Will be deprecated
    "wood": {"FOREST": 0.5, "OCEAN": 0},
    "apple": {"FOREST": 0.3, "GRASSLAND": 0.2},
    "fish": {"OCEAN": 0.4},
    "stone": {"MOUNTAIN": 0.6},
    "magical_crystal": {"MOUNTAIN": 0.1, "FOREST": 0.05}
}

# Legacy alias
from .enhanced_llm import init_llm_service

