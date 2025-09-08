from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RuntimeCfg:
    turns: int = 10
    seed: int = 42


@dataclass
class WorldCfg:
    size: int = 32
    num_agents: int = 5


@dataclass
class ModelCfg:
    provider: str = "null"  # null|deepseek|openai
    model: str = "placeholder"
    temperature: float = 0.0
    timeout: float = 5.0


@dataclass
class WebCfg:
    port: int = 8081
    export: bool = False
    export_dir: str = "web_data"


@dataclass
class AppCfg:
    runtime: RuntimeCfg = field(default_factory=RuntimeCfg)
    world: WorldCfg = field(default_factory=WorldCfg)
    model: ModelCfg = field(default_factory=ModelCfg)
    web: WebCfg = field(default_factory=WebCfg)


def _coerce(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def apply_overrides(cfg: AppCfg, overrides: list[str]) -> AppCfg:
    """Apply simple key=value overrides with dot notation.

    Example: ["world.num_agents=10", "runtime.turns=30"]
    """
    for item in overrides:
        if "=" not in item:
            continue
        key, val = item.split("=", 1)
        parts = key.split(".")
        target: Any = cfg
        for p in parts[:-1]:
            target = getattr(target, p)
        final = parts[-1]
        setattr(target, final, _coerce(val))
    return cfg


def to_dict(cfg: AppCfg) -> Dict[str, Any]:  # useful for logging/debug
    return {
        "runtime": vars(cfg.runtime),
        "world": vars(cfg.world),
        "model": vars(cfg.model),
        "web": vars(cfg.web),
    }
