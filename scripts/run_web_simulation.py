#!/usr/bin/env python3
"""Launch the web monitor and optionally start the simulation."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import List


def _prepare_path() -> Path:
    """Ensure the project root is available on ``sys.path``."""

    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root


_prepare_path()

from sociology_simulation.web_monitor import LogCapture, get_monitor  # noqa: E402


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Build and parse the command-line interface."""

    parser = argparse.ArgumentParser(
        description="Start the Project Genesis monitoring console and simulation back-end."
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind HTTP and WebSocket servers")
    parser.add_argument("--http-port", type=int, default=8081, help="Port for the HTTP API and static assets")
    parser.add_argument("--ws-port", type=int, default=8765, help="Port for WebSocket updates")
    parser.add_argument(
        "--auto-start",
        action="store_true",
        help="Immediately start a simulation run instead of waiting for a monitor command",
    )
    parser.add_argument("--era", type=str, help="Override the era prompt when auto-starting")
    parser.add_argument("--scenario", type=str, help="Hydra simulation preset to use (e.g. stone_age)")
    parser.add_argument("--turns", type=int, help="Number of turns to simulate when auto-starting")
    parser.add_argument("--num-agents", type=int, help="Agent count when auto-starting")
    parser.add_argument("--world-size", type=int, help="World size when auto-starting")
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        help="Additional Hydra overrides for the simulation (may be repeated)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity for the launcher",
    )
    return parser.parse_args()


def build_overrides(args: argparse.Namespace) -> List[str]:
    """Translate CLI options into Hydra-style overrides."""

    overrides: List[str] = list(args.override or [])

    if args.era:
        overrides.append(f"simulation.era_prompt={json.dumps(args.era)}")
    if args.scenario:
        overrides.append(f"simulation={args.scenario}")
    if args.turns is not None:
        overrides.append(f"runtime.turns={int(args.turns)}")
    if args.num_agents is not None:
        overrides.append(f"world.num_agents={int(args.num_agents)}")
    if args.world_size is not None:
        overrides.append(f"world.size={int(args.world_size)}")

    return overrides


async def run_monitor(args: argparse.Namespace) -> None:
    """Start the monitor services and optional simulation."""

    monitor = get_monitor()
    log_capture = LogCapture(monitor)
    log_capture.start_capture()

    stop_event = asyncio.Event()
    http_runner = None

    loop = asyncio.get_running_loop()
    for sig_name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, sig_name):
            try:
                loop.add_signal_handler(getattr(signal, sig_name), stop_event.set)
            except NotImplementedError:
                # Signal handlers are not available on some platforms (e.g. Windows)
                pass

    try:
        monitor.setup_http_server(args.host, args.http_port)
        http_runner = await monitor.start_http_server(args.host, args.http_port)
        await monitor.start_websocket_server(args.host, args.ws_port)

        logger.info("Web monitor ready")
        logger.info("HTTP UI available at http://%s:%s", args.host, args.http_port)
        logger.info("WebSocket endpoint at ws://%s:%s", args.host, args.ws_port)

        if args.auto_start:
            overrides = build_overrides(args)
            controller = monitor._ensure_orchestrator()
            try:
                cfg = await controller.start(overrides)
                logger.info(
                    "Auto-started simulation: era=%s, turns=%s, agents=%s, world=%s",
                    cfg.simulation.era_prompt,
                    cfg.runtime.turns,
                    cfg.world.num_agents,
                    cfg.world.size,
                )
            except RuntimeError as exc:
                logger.warning("Simulation already running: %s", exc)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Failed to auto-start simulation", exc_info=exc)

        logger.info("Monitor running. Use Ctrl+C to exit or the web UI to control the simulation.")
        await stop_event.wait()
    finally:
        log_capture.stop_capture()
        await monitor.stop_websocket_server()
        if http_runner:
            await http_runner.cleanup()


def main() -> None:
    """Entry point for the launcher script."""

    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        asyncio.run(run_monitor(args))
    except KeyboardInterrupt:
        logger.info("Monitor interrupted by user")


if __name__ == "__main__":
    main()
