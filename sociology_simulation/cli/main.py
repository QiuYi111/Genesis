from __future__ import annotations

import asyncio
import sys
from typing import Sequence

from ..core.world import World
from ..services.llm.null import NullProvider
from ..trinity.trinity import Trinity, NullPlanner
from .config import AppCfg, apply_overrides


def make_provider(provider_name: str):
    # For W1 only supports null; others will be wired later.
    if provider_name == "null":
        return NullProvider()
    # Fallback to null
    return NullProvider()


async def simulation_loop(world: World, trinity: Trinity, *, turns: int) -> None:
    for t in range(turns):
        result = world.step(t, trinity=trinity)
        # Minimal progress output for smoke; can be replaced with logging later.
        if t == 0 or (t + 1) % 5 == 0 or t == turns - 1:
            print(f"turn={result['turn']} metrics={result['metrics']}")


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = AppCfg()
    cfg = apply_overrides(cfg, argv)

    world = World(size=cfg.world.size, seed=cfg.runtime.seed, num_agents=cfg.world.num_agents)
    _provider = make_provider(cfg.model.provider)
    planner = NullPlanner()
    trinity = Trinity(planner)

    asyncio.run(simulation_loop(world, trinity, turns=cfg.runtime.turns))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

