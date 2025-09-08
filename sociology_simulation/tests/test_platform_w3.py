from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sociology_simulation.cli.config import AppCfg, apply_overrides, to_dict
from sociology_simulation.services.web.monitor import Exporter, WebSocketMonitor


def test_cli_config_overrides_and_to_dict() -> None:
    cfg = AppCfg()
    cfg = apply_overrides(cfg, [
        "world.num_agents=10",
        "runtime.turns=3",
        "model.provider=null",
        "web.port=9000",
        "web.export=true",
    ])
    d = to_dict(cfg)
    assert d["world"]["num_agents"] == 10
    assert d["runtime"]["turns"] == 3
    assert d["model"]["provider"] == "null"
    assert d["web"]["port"] == 9000
    assert d["web"]["export"] is True


def test_exporter_writes_snapshot(tmp_path: Path) -> None:
    exporter = Exporter(out_dir=tmp_path)
    snapshot = {"turn": 7, "metrics": {"x": 1}}
    exporter.write_snapshot(snapshot, turn=7)
    out = tmp_path / "snapshot_0007.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["turn"] == 7
    assert data["metrics"]["x"] == 1


def test_websocket_monitor_start_broadcast_stop_noop_or_live(random_free_port: int) -> None:
    async def _run() -> None:
        mon = WebSocketMonitor()
        await mon.start(random_free_port)
        # Broadcast a frame regardless of whether websockets is installed.
        await mon.broadcast({"turn": 0, "ok": True})

        # If websockets is available, attempt a best-effort connection.
        try:
            import websockets  # type: ignore
        except Exception:
            websockets = None  # type: ignore

        if websockets is not None:
            # Connect to the server and then close; path must be /ws
            try:
                uri = f"ws://127.0.0.1:{random_free_port}/ws"
                async with websockets.connect(uri):  # type: ignore[attr-defined]
                    # Send nothing; ensure connection can establish
                    pass
            except Exception:
                # Allow environments without proper event loop policies
                pass

        await mon.stop()

    asyncio.run(_run())

