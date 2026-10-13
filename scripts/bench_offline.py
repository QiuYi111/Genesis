"""
Offline benchmark for sociology_simulation without real LLM calls.

This script monkeypatches EnhancedLLMService.generate to return fast
stubbed responses, allowing us to measure core loop performance under
different agent counts without network.

Usage examples:
  python scripts/bench_offline.py --agents 100 --turns 5 --size 64
  python scripts/bench_offline.py --agents 500 --turns 5 --size 64
"""

from __future__ import annotations

import asyncio
import argparse
import json
import statistics
import time
from typing import Any, Dict, Optional

import aiohttp

import os
import sys

# Ensure project root is on sys.path when running as a script
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from sociology_simulation.enhanced_llm import (
    EnhancedLLMService,
    init_llm_service,
    LLMResponse,
)
from sociology_simulation.world import World
from sociology_simulation.config import (
    Config,
    ModelConfig,
    SimulationConfig,
    WorldConfig,
    RuntimeConfig,
    PerceptionConfig,
    LoggingConfig,
    OutputConfig,
    set_config,
)


def _stub_llm_generate(template_name: str, **kwargs) -> LLMResponse:
    """Return fast, deterministic responses for templates we use."""
    # Minimal viable defaults
    if template_name == "trinity_generate_initial_rules":
        parsed = {
            "terrain_types": ["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"],
            "resource_rules": {
                "wood": {"FOREST": 0.15},
                "fish": {"OCEAN": 0.10},
                "stone": {"MOUNTAIN": 0.12},
                "apple": {"GRASSLAND": 0.08},
            },
            "terrain_colors": {},
        }
        return LLMResponse(content=json.dumps(parsed), success=True, parsed_data=parsed)

    if template_name == "agent_generate_name":
        return LLMResponse(content="A", success=True)

    if template_name == "agent_decide_goal":
        return LLMResponse(content="生存并收集资源", success=True)

    if template_name == "agent_action":
        # Keep simple movement/gather hint to exercise code paths
        return LLMResponse(content="寻找食物", success=True)

    if template_name in (
        "trinity_adjudicate",
        "trinity_execute_actions",
        "trinity_analyze_behaviors",
        "trinity_natural_events",
    ):
        return LLMResponse(content="{}", success=True, parsed_data={})

    if template_name == "trinity_turn_summary":
        parsed = {"summary": "stub", "highlights": [], "warnings": []}
        return LLMResponse(content=json.dumps(parsed), success=True, parsed_data=parsed)

    # Fallback empty
    return LLMResponse(content="", success=False, parsed_data={})


def patch_llm_service() -> EnhancedLLMService:
    svc = init_llm_service()

    async def _generate_stub(self: EnhancedLLMService, template_name: str, session, **kwargs):
        # ignore session; return immediate stub
        return _stub_llm_generate(template_name, **kwargs)

    # Monkeypatch the instance method
    setattr(EnhancedLLMService, "generate", _generate_stub)  # type: ignore[attr-defined]
    return svc


async def run_once(agents: int, turns: int, size: int) -> Dict[str, Any]:
    # Initialize minimal config (no real network access)
    model = ModelConfig(
        api_key_env="DEEPSEEK_API_KEY",
        agent_model="dummy-agent",
        trinity_model="dummy-trinity",
        base_url="http://localhost",
        temperatures={}
    )
    sim = SimulationConfig(
        era_prompt="石器时代",
        terrain_types=["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"],
        resource_rules={
            "wood": {"FOREST": 0.15},
            "fish": {"OCEAN": 0.10},
            "stone": {"MOUNTAIN": 0.12},
            "apple": {"GRASSLAND": 0.08},
        },
        agent_attributes={},
        agent_inventory={},
        agent_age={},
        survival={},
    )
    wc = WorldConfig(size=size, num_agents=agents, terrain_algorithm="simple")
    rc = RuntimeConfig(turns=turns, show_map_every=0, show_conversations=False, timeout_per_agent=5.0)
    pc = PerceptionConfig(vision_radius=5)
    log = LoggingConfig(
        level="WARNING",
        format="{time} {level} {message}",
        console_format="{time} {level} {message}",
        file={"enabled": False, "path": "logs/run.log", "rotation": "10 MB", "retention": "30 days", "compression": "zip"},
        console={"enabled": True, "level": "WARNING"},
    )
    out = OutputConfig(log_level="WARNING", use_colors=False, verbose=False, show_agent_status=False, turn_summary_llm=False)
    set_config(Config(model=model, simulation=sim, world=wc, runtime=rc, perception=pc, logging=log, output=out))

    patch_llm_service()
    async with aiohttp.ClientSession() as session:
        world = World(size=size, era_prompt="石器时代", num_agents=agents)
        await world.initialize(session)

        turn_times = []
        for _ in range(turns):
            t0 = time.perf_counter()
            await world.step(session)
            turn_times.append(time.perf_counter() - t0)

        return {
            "agents": agents,
            "turns": turns,
            "size": size,
            "turn_time_avg": statistics.mean(turn_times) if turn_times else 0.0,
            "turn_time_p95": statistics.quantiles(turn_times, n=20)[-1] if len(turn_times) >= 20 else max(turn_times or [0.0]),
            "turn_time_p50": statistics.median(turn_times) if turn_times else 0.0,
            "turn_time_list": turn_times,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", type=int, default=100)
    parser.add_argument("--turns", type=int, default=5)
    parser.add_argument("--size", type=int, default=64)
    args = parser.parse_args()

    results = asyncio.run(run_once(args.agents, args.turns, args.size))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
