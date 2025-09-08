"""File-based snapshot exporter (optional, W2).

Writes JSON snapshots into `web_data/snapshots/turn_XXXX.json`. The target
directory is ignored by Git per repository guidelines.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Final


_BASE_DIR: Final[str] = os.path.join("web_data", "snapshots")


@dataclass
class FileExporter:
    base_dir: str = _BASE_DIR

    def write_snapshot(self, snapshot: dict, *, turn: int) -> None:
        os.makedirs(self.base_dir, exist_ok=True)
        path = os.path.join(self.base_dir, f"turn_{turn:04d}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, separators=(",", ":"))

