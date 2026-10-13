"""
Online benchmark for sociology_simulation using real LLM API calls.

This script initializes the project Config from environment-friendly
defaults and runs a small simulation, recording per-turn latency and
LLM service statistics. It requires a valid API key in env var
specified by `model.api_key_env` (default: DEEPSEEK_API_KEY).

Usage examples:
  DEEPSEEK_API_KEY=... uv run python scripts/bench_online.py --agents 10 --turns 3
  DEEPSEEK_API_KEY=... MODEL_BASE_URL=https://api.openai.com/v1/chat/completions \
    uv run python scripts/bench_online.py --agents 10 --turns 3 --agent-model gpt-4o-mini
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time
from typing import Any, Dict

import aiohttp

import sys
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sociology_simulation.world import World
from sociology_simulation.enhanced_llm import init_llm_service, get_llm_service, EnhancedLLMService, LLMResponse
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


def _maybe_cap_llm_calls(cap: int) -> None:
    """Optionally cap the number of expensive agent LLM calls to bound time/cost.

    We treat templates 'agent_generate_name', 'agent_decide_goal', 'agent_action'
    as expensive, and short-circuit to quick fallbacks when the budget is exceeded.
    """
    if cap <= 0:
        return

    remaining = {"n": cap}
    orig_generate = EnhancedLLMService.generate

    async def _wrapped_generate(self: EnhancedLLMService, template_name: str, session, **kwargs):
        expensive = template_name in {"agent_generate_name", "agent_decide_goal", "agent_action"}
        if expensive:
            if remaining["n"] <= 0:
                # Quick fallbacks: name=A, goal=生存并收集资源, action=寻找食物
                if template_name == "agent_generate_name":
                    return LLMResponse(content="A", success=True)
                if template_name == "agent_decide_goal":
                    return LLMResponse(content="生存并收集资源", success=True)
                if template_name == "agent_action":
                    return LLMResponse(content="寻找食物", success=True)
            else:
                remaining["n"] -= 1
        return await orig_generate(self, template_name, session, **kwargs)

    setattr(EnhancedLLMService, "generate", _wrapped_generate)  # type: ignore


async def run_once(agents: int, turns: int, size: int, agent_model: str, trinity_model: str, api_key_env: str, cap_calls: int, timeout_per_agent: float) -> Dict[str, Any]:
    base_url = os.getenv("MODEL_BASE_URL", "https://api.deepseek.com/v1/chat/completions")

    # Configure project
    model = ModelConfig(
        api_key_env=api_key_env,
        agent_model=agent_model,
        trinity_model=trinity_model,
        base_url=base_url,
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
    rc = RuntimeConfig(turns=turns, show_map_every=0, show_conversations=False, timeout_per_agent=timeout_per_agent)
    pc = PerceptionConfig(vision_radius=5)
    log = LoggingConfig(
        level="WARNING",
        format="{time} {level} {message}",
        console_format="{time} {level} {message}",
        file={"enabled": False, "path": "logs/run.log", "rotation": "10 MB", "retention": "30 days", "compression": "zip"},
        console={"enabled": True, "level": "WARNING"},
    )
    out = OutputConfig(
        log_level="WARNING",
        use_colors=False,
        verbose=False,
        show_agent_status=False,
        turn_summary_llm=False,  # reduce extra LLM calls
        web_export_every=0,      # disable incremental export
        max_agent_log_entries=3,
    )
    set_config(Config(model=model, simulation=sim, world=wc, runtime=rc, perception=pc, logging=log, output=out))

    # Initialize LLM service (real API)
    init_llm_service()
    if cap_calls >= 0:
        _maybe_cap_llm_calls(cap_calls)
    svc = get_llm_service()

    async with aiohttp.ClientSession() as session:
        world = World(size=size, era_prompt=sim.era_prompt, num_agents=agents)

        t_init0 = time.perf_counter()
        await world.initialize(session)
        t_init = time.perf_counter() - t_init0

        turn_times = []
        for _ in range(turns):
            t0 = time.perf_counter()
            await world.step(session)
            turn_times.append(time.perf_counter() - t0)

    stats = svc.get_statistics() if hasattr(svc, "get_statistics") else {}

    return {
        "agents": agents,
        "turns": turns,
        "size": size,
        "init_time": t_init,
        "turn_time_avg": statistics.mean(turn_times) if turn_times else 0.0,
        "turn_time_p50": statistics.median(turn_times) if turn_times else 0.0,
        "turn_time_max": max(turn_times) if turn_times else 0.0,
        "turn_time_list": turn_times,
        "llm_stats": stats,
        "base_url": base_url,
        "agent_model": agent_model,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", type=int, default=10)
    parser.add_argument("--turns", type=int, default=3)
    parser.add_argument("--size", type=int, default=64)
    parser.add_argument("--agent-model", type=str, default="deepseek-chat")
    parser.add_argument("--trinity-model", type=str, default="deepseek-chat")
    parser.add_argument("--api-key-env", type=str, default="DEEPSEEK_API_KEY")
    parser.add_argument("--api-key", type=str, default="", help="Direct API key value (optional)")
    parser.add_argument("--base-url", type=str, default="", help="Override model base URL")
    parser.add_argument("--turn-timeout", type=float, default=10.0, help="timeout_per_agent seconds (lower to avoid timeouts)")
    parser.add_argument("--cap-calls", type=int, default=-1, help="Max expensive agent LLM calls; -1 disables capping")
    args = parser.parse_args()

    # Allow direct API key injection to avoid external env reliance
    if args.api_key:
        os.environ[args.api_key_env] = args.api_key
    api_key = os.getenv(args.api_key_env)
    if not api_key:
        print(json.dumps({"error": f"Missing API key: set {args.api_key_env} or pass --api-key"}, ensure_ascii=False))
        raise SystemExit(2)

    # Optional base URL override
    if args.base_url:
        os.environ["MODEL_BASE_URL"] = args.base_url

    results = asyncio.run(
        run_once(
            agents=args.agents,
            turns=args.turns,
            size=args.size,
            agent_model=args.agent_model,
            trinity_model=args.trinity_model,
            api_key_env=args.api_key_env,
            cap_calls=args.cap_calls,
            timeout_per_agent=args.turn_timeout,
        )
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
