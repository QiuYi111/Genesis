"""
Unified configuration system for Project Genesis.
Combines Hydra configuration management with OmegaConf flexibility.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import yaml
from dataclasses import dataclass

from omegaconf import OmegaConf, DictConfig
import hydra
from hydra import initialize, compose
from hydra.core.global_hydra import GlobalHydra


@dataclass
class ConfigurationPaths:
    """Configuration file paths"""
    base_config: str = "config/base.yaml"
    simulation_configs: str = "config/simulation"
    model_configs: str = "config/model"
    logging_configs: str = "config/logging"
    prompts_configs: str = "config/prompts"


class UnifiedConfig:
    """Unified configuration manager"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config: Optional[DictConfig] = None
        self.paths = ConfigurationPaths()
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.config_dir / "simulation").mkdir(exist_ok=True)
        (self.config_dir / "model").mkdir(exist_ok=True)
        (self.config_dir / "logging").mkdir(exist_ok=True)
        
        # Initialize default configurations
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Create default configuration files"""
        
        # Base configuration
        base_config = {
            "simulation": {
                "name": "Genesis Simulation",
                "description": "LLM-driven sociology simulation",
                "max_turns": 1000,
                "seed": 42,
                "save_frequency": 50,
                "backup_frequency": 100
            },
            "world": {
                "width": 64,
                "height": 64,
                "terrain_types": ["grassland", "forest", "mountain", "water", "desert"],
                "climate_enabled": True,
                "seasonal_cycles": True
            },
            "agents": {
                "count": 50,
                "spawn_radius": 10,
                "starting_inventory": {
                    "food": 5,
                    "water": 5,
                    "wood": 2,
                    "stone": 1
                },
                "max_inventory_weight": 50.0,
                "memory_capacity": 100,
                "learning_rate": 0.01
            },
            "llm": {
                "provider": "mock",
                "model": "deepseek-chat",
                "temperature": 0.7,
                "max_tokens": 500,
                "timeout": 30,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "trinity": {
                "enabled": True,
                "observation_frequency": 5,
                "skill_generation": True,
                "rule_evolution": True,
                "era_progression": True,
                "behavior_analysis": True,
                "pattern_recognition": True
            },
            "web": {
                "enabled": True,
                "host": "localhost",
                "port": 8080,
                "update_frequency": 1,
                "export_format": "json",
                "real_time_monitoring": True
            },
            "logging": {
                "level": "INFO",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
                "file_logging": True,
                "console_logging": True,
                "log_dir": "logs",
                "max_log_files": 10,
                "log_rotation": "10 MB"
            },
            "output": {
                "show_stats": True,
                "show_turn_summary": True,
                "export_data": True,
                "export_format": "json",
                "save_state": True,
                "state_dir": "outputs"
            }
        }
        
        # Create base config file
        base_config_path = self.config_dir / "base.yaml"
        if not base_config_path.exists():
            with open(base_config_path, 'w') as f:
                yaml.dump(base_config, f, default_flow_style=False, indent=2)
        
        # Create simulation configs
        simulation_configs = {
            "stone_age": {
                "simulation": {
                    "era": "stone_age",
                    "description": "Early human civilization with basic tools"
                },
                "agents": {
                    "starting_inventory": {
                        "food": 3,
                        "water": 3,
                        "stone": 1
                    }
                },
                "trinity": {
                    "era_prompt": "stone age",
                    "available_technologies": ["fire", "basic_tools", "gathering"]
                }
            },
            "bronze_age": {
                "simulation": {
                    "era": "bronze_age",
                    "description": "Advanced civilization with metalworking"
                },
                "agents": {
                    "starting_inventory": {
                        "food": 5,
                        "water": 5,
                        "wood": 3,
                        "stone": 2,
                        "metal": 1
                    }
                },
                "trinity": {
                    "era_prompt": "bronze age",
                    "available_technologies": ["bronze_tools", "agriculture", "pottery"]
                }
            },
            "magical_age": {
                "simulation": {
                    "era": "magical_age",
                    "description": "Mystical civilization with magical abilities"
                },
                "trinity": {
                    "era_prompt": "magical age",
                    "available_technologies": ["magic", "enchantment", "alchemy"]
                }
            }
        }
        
        for name, config in simulation_configs.items():
            config_path = self.config_dir / "simulation" / f"{name}.yaml"
            if not config_path.exists():
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
        
        # Create model configs
        model_configs = {
            "deepseek": {
                "llm": {
                    "provider": "deepseek",
                    "model": "deepseek-chat",
                    "api_key": "${DEEPSEEK_API_KEY}",
                    "base_url": "https://api.deepseek.com/v1",
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            },
            "openai": {
                "llm": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "api_key": "${OPENAI_API_KEY}",
                    "temperature": 0.7,
                    "max_tokens": 500
                }
            },
            "mock": {
                "llm": {
                    "provider": "mock",
                    "response_delay": 0.1,
                    "simulate_failures": 0.05
                }
            }
        }
        
        for name, config in model_configs.items():
            config_path = self.config_dir / "model" / f"{name}.yaml"
            if not config_path.exists():
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
        
        # Create logging configs
        logging_configs = {
            "debug": {
                "logging": {
                    "level": "DEBUG",
                    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name: <15} | {function: <15} | {line: <4} | {message}"
                }
            },
            "default": {
                "logging": {
                    "level": "INFO",
                    "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
                }
            },
            "quiet": {
                "logging": {
                    "level": "WARNING",
                    "console_logging": False
                }
            }
        }
        
        for name, config in logging_configs.items():
            config_path = self.config_dir / "logging" / f"{name}.yaml"
            if not config_path.exists():
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
    
    def load_config(self, 
                   simulation: str = "stone_age",
                   model: str = "mock",
                   logging: str = "default",
                   overrides: Dict[str, Any] = None) -> DictConfig:
        """Load configuration with overrides"""
        
        # Clear any existing Hydra instance
        GlobalHydra.instance().clear()
        
        try:
            with initialize(config_path=str(self.config_dir), version_base=None):
                config_files = [
                    "base.yaml",
                    f"simulation/{simulation}.yaml",
                    f"model/{model}.yaml",
                    f"logging/{logging}.yaml"
                ]
                
                config = compose(config_name=None, config_files=config_files)
                
                # Apply overrides
                if overrides:
                    override_config = OmegaConf.create(overrides)
                    config = OmegaConf.merge(config, override_config)
                
                # Resolve environment variables
                config = OmegaConf.to_container(config, resolve=True)
                config = OmegaConf.create(config)
                
                self.config = config
                return config
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Return basic config as fallback
            return OmegaConf.create({
                "simulation": {"max_turns": 100, "seed": 42},
                "world": {"width": 32, "height": 32},
                "agents": {"count": 10},
                "llm": {"provider": "mock"},
                "trinity": {"enabled": False},
                "web": {"enabled": False},
                "logging": {"level": "INFO"}
            })
    
    def save_config(self, config: DictConfig, filepath: str):
        """Save configuration to file"""
        config_dict = OmegaConf.to_container(config, resolve=True)
        with open(filepath, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        if not self.config:
            return default
        
        keys = key.split('.')
        current = self.config
        
        try:
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError):
            return default
    
    def update_config(self, key: str, value: Any):
        """Update configuration value"""
        if not self.config:
            return
        
        keys = key.split('.')
        current = self.config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def validate_config(self, config: DictConfig) -> bool:
        """Validate configuration"""
        required_keys = [
            "simulation.max_turns",
            "world.width",
            "world.height",
            "agents.count",
            "llm.provider"
        ]
        
        for key in required_keys:
            if self.get_config_value(key) is None:
                logger.error(f"Missing required configuration: {key}")
                return False
        
        return True
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        if not self.config:
            return {"status": "not_loaded"}
        
        return {
            "simulation": {
                "name": self.get_config_value("simulation.name"),
                "max_turns": self.get_config_value("simulation.max_turns"),
                "seed": self.get_config_value("simulation.seed")
            },
            "world": {
                "dimensions": (
                    self.get_config_value("world.width"),
                    self.get_config_value("world.height")
                )
            },
            "agents": {
                "count": self.get_config_value("agents.count")
            },
            "llm": {
                "provider": self.get_config_value("llm.provider"),
                "model": self.get_config_value("llm.model")
            },
            "trinity": {
                "enabled": self.get_config_value("trinity.enabled", False)
            },
            "web": {
                "enabled": self.get_config_value("web.enabled", False),
                "port": self.get_config_value("web.port", 8080)
            }
        }


# Global configuration instance
_config_instance = None

def get_config() -> UnifiedConfig:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = UnifiedConfig()
    return _config_instance


def load_simulation_config(
    simulation: str = "stone_age",
    model: str = "mock",
    logging: str = "default",
    overrides: Dict[str, Any] = None
) -> DictConfig:
    """Convenience function to load simulation configuration"""
    config = get_config()
    return config.load_config(simulation, model, logging, overrides)


if __name__ == "__main__":
    # Test configuration system
    config = get_config()
    cfg = config.load_config("stone_age", "mock", "debug")
    
    print("Configuration loaded successfully:")
    print(f"Simulation: {cfg.simulation.name}")
    print(f"World: {cfg.world.width}x{cfg.world.height}")
    print(f"Agents: {cfg.agents.count}")
    print(f"LLM Provider: {cfg.llm.provider}")
    
    # Test overrides
    custom_cfg = config.load_config(
        overrides={"agents.count": 25, "world.width": 32}
    )
    print(f"Custom agents: {custom_cfg.agents.count}")
    print(f"Custom world: {custom_cfg.world.width}x{custom_cfg.world.height}")