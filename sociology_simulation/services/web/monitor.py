from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set


# Optional dependency: we degrade to a no-op monitor if not installed.
try:  # pragma: no cover - import guard
    import websockets
    from websockets.server import WebSocketServerProtocol
except Exception:  # pragma: no cover - import guard
    websockets = None
    WebSocketServerProtocol = object  # type: ignore


@dataclass
class Exporter:
    """Write snapshots to web_data/ for offline inspection.

    Files are written as JSON: web_data/snapshot_0000.json, ...
    """

    out_dir: Path = Path("web_data")

    def write_snapshot(self, snapshot: dict, *, turn: int) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"snapshot_{turn:04d}.json"
        # Keep ASCII + sorted keys for readability and deterministic diffs.
        path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True))


class WebSocketMonitor:
    """Minimal WebSocket broadcaster.

    - start(port): starts a WS server at ws://localhost:port/ws
    - broadcast(snapshot): sends JSON text to all connected clients
    - If websockets isn't available, acts as a no-op while keeping API stable.
    """

    def __init__(self) -> None:
        self._server: Optional[asyncio.AbstractServer] = None
        self._clients: Set[WebSocketServerProtocol] = set()  # type: ignore[type-arg]
        self._port: Optional[int] = None
        self._enabled: bool = websockets is not None

    async def _ws_handler(self, websocket: WebSocketServerProtocol):  # type: ignore[override]
        # Register client and keep the connection alive until it closes.
        self._clients.add(websocket)
        try:
            # Drain incoming messages to keep connection healthy; ignore contents.
            async for _ in websocket:
                pass
        finally:
            self._clients.discard(websocket)

    async def start(self, port: int) -> None:
        self._port = int(port)
        if not self._enabled:
            return  # websockets not installed; operate as no-op

        # Start a WS server at /ws. If the chosen port is unavailable, let it raise.
        async def _app(websocket, path):  # type: ignore[no-redef]
            # Only accept the designated path; close others politely.
            if path != "/ws":
                await websocket.close()
                return
            await self._ws_handler(websocket)

        # websockets.serve returns a Server which is an awaitable context manager
        self._server = await websockets.serve(  # type: ignore[attr-defined]
            _app, host="127.0.0.1", port=self._port, ping_interval=20, ping_timeout=20
        )

    async def broadcast(self, snapshot: dict) -> None:
        if not self._enabled or not self._clients:
            return
        msg = json.dumps(snapshot, ensure_ascii=False)
        send_tasks = []
        dead: list[WebSocketServerProtocol] = []
        for ws in list(self._clients):
            try:
                send_tasks.append(asyncio.create_task(ws.send(msg)))
            except Exception:
                dead.append(ws)
        # Cleanup any clients that failed immediately
        for ws in dead:
            self._clients.discard(ws)
        if send_tasks:
            # Shield to isolate per-client failures; we don't need results.
            await asyncio.gather(*send_tasks, return_exceptions=True)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
