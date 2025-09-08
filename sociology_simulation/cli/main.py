from __future__ import annotations

import asyncio
import sys
from typing import Sequence

from ..core.world import World
from ..services.web.monitor import WebSocketMonitor, Exporter
from pathlib import Path
from ..services.llm.null import NullProvider
from ..trinity.trinity import Trinity, NullPlanner, LLMPlanner
from .config import AppCfg, apply_overrides


def make_provider(provider_name: str):
    # Default/null path remains deterministic and offline
    if provider_name == "null":
        return NullProvider()
    # Lazy import to avoid importing optional deps when unused
    if provider_name == "deepseek":
        from ..services.llm.deepseek import DeepSeekProvider

        return DeepSeekProvider()
    if provider_name == "openai":
        from ..services.llm.openai import OpenAIProvider

        return OpenAIProvider()
    # Fallback to null
    return NullProvider()


async def simulation_loop(world: World, trinity: Trinity, monitor: WebSocketMonitor, *, turns: int) -> None:
    for t in range(turns):
        result = world.step(t, trinity=trinity)
        # Broadcast one frame per turn; schema defined by world.snapshot().
        await monitor.broadcast(world.snapshot())
        # Minimal progress output for smoke; can be replaced with logging later.
        if t == 0 or (t + 1) % 5 == 0 or t == turns - 1:
            print(f"turn={result['turn']} metrics={result['metrics']}")


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = AppCfg()
    cfg = apply_overrides(cfg, argv)

    world = World(size=cfg.world.size, seed=cfg.runtime.seed, num_agents=cfg.world.num_agents)
    _provider = make_provider(cfg.model.provider)
    planner = NullPlanner() if cfg.model.provider == "null" else LLMPlanner(_provider, vars(cfg.model))
    trinity = Trinity(planner)

    monitor = WebSocketMonitor()
    exporter = Exporter(Path(cfg.web.export_dir)) if getattr(cfg.web, "export", False) else None
    async def _run():
        await monitor.start(cfg.web.port)
        await simulation_loop(world, trinity, monitor, turns=cfg.runtime.turns)

        # After loop completes, write final snapshot if exporter is enabled.
        if exporter is not None:
            try:
                exporter.write_snapshot(world.snapshot(), turn=cfg.runtime.turns - 1)
            except Exception:
                # Rollback strategy: ignore exporter failures to keep simulation healthy.
                pass

    # Write snapshots during the loop as well if enabled by config.
    if exporter is not None:
        # Monkey-patch a lightweight broadcaster that also writes to disk.
        orig_broadcast = monitor.broadcast

        async def _broadcast_and_export(snapshot: dict) -> None:
            try:
                exporter.write_snapshot(snapshot, turn=snapshot.get("turn", 0))
            except Exception:
                pass
            await orig_broadcast(snapshot)

        monitor.broadcast = _broadcast_and_export  # type: ignore[assignment]

    asyncio.run(_run())
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
