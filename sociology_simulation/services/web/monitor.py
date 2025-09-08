from __future__ import annotations

class Exporter:
    def write_snapshot(self, snapshot: dict, *, turn: int) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError


class WebSocketMonitor:
    async def start(self, port: int) -> None:  # pragma: no cover - placeholder
        # Skeleton only for W1; real WS comes in C-3.
        self._port = port

    async def broadcast(self, snapshot: dict) -> None:  # pragma: no cover - placeholder
        # No-op until C-3.
        return None

