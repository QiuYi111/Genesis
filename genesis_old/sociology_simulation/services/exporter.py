"""
Exporter service for simulation data export
Provides standardized snapshot export functionality
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Protocol
from pathlib import Path
from dataclasses import dataclass


class Exporter(Protocol):
    """Protocol for simulation data exporters"""
    
    def write_snapshot(self, snapshot: Dict[str, Any], *, turn: int) -> None:
        """Write a simulation snapshot for the given turn"""
        ...


@dataclass
class SnapshotSchema:
    """Standardized snapshot schema for simulation data"""
    
    # Required fields
    turn: int
    world: Dict[str, Any]
    agents: List[Dict[str, Any]]
    timestamp: str
    
    # Optional fields
    events: Optional[List[Dict[str, Any]]] = None
    metrics: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "turn": self.turn,
            "world": self.world,
            "agents": self.agents,
            "timestamp": self.timestamp
        }
        
        if self.events is not None:
            result["events"] = self.events
        if self.metrics is not None:
            result["metrics"] = self.metrics
        if self.metadata is not None:
            result["metadata"] = self.metadata
            
        return result


class FileExporter:
    """File-based exporter for simulation snapshots"""
    
    def __init__(self, output_dir: str = "snapshots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def write_snapshot(self, snapshot: Dict[str, Any], *, turn: int) -> None:
        """Write snapshot to file"""
        try:
            # Create turn-specific file
            filename = f"snapshot_turn_{turn:04d}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            
            # Update latest.json for convenience
            latest_path = self.output_dir / "latest.json"
            with open(latest_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            raise RuntimeError(f"Failed to write snapshot for turn {turn}: {e}")


class NullExporter:
    """No-op exporter for testing and offline mode"""
    
    def write_snapshot(self, snapshot: Dict[str, Any], *, turn: int) -> None:
        """Do nothing - for testing without file I/O"""
        pass


def create_snapshot_from_world(world_snapshot: Dict[str, Any], turn: int, 
                               events: Optional[List[Dict[str, Any]]] = None,
                               metrics: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Create standardized snapshot from world snapshot data"""
    
    # Validate required fields
    if "agents" not in world_snapshot or "terrain" not in world_snapshot:
        raise ValueError("World snapshot must contain 'agents' and 'terrain' fields")
    
    # Build standardized world data
    world_data = {
        "size": world_snapshot.get("size", 64),
        "terrain": world_snapshot["terrain"],
        "resources": world_snapshot.get("resources", {}),
        "resource_status": world_snapshot.get("resource_status", {})
    }
    
    # Standardize agent data
    agents_data = []
    for agent in world_snapshot["agents"]:
        agent_data = {
            "aid": agent.get("aid"),
            "name": agent.get("name", f"Agent_{agent.get('aid', 0)}"),
            "pos": agent.get("pos", [0, 0]),
            "attributes": agent.get("attributes", {}),
            "inventory": agent.get("inventory", {}),
            "age": agent.get("age", 0),
            "health": agent.get("health", 100),
            "hunger": agent.get("hunger", 0),
            "skills": agent.get("skills", {})
        }
        agents_data.append(agent_data)
    
    # Create snapshot
    snapshot = SnapshotSchema(
        turn=turn,
        world=world_data,
        agents=agents_data,
        timestamp=datetime.now().isoformat(),
        events=events,
        metrics=metrics,
        metadata={
            "schema_version": "1.0",
            "exporter": "file"
        }
    )
    
    return snapshot.to_dict()


def get_exporter(exporter_type: str = "file", **kwargs) -> Exporter:
    """Factory function to create exporters"""
    if exporter_type == "file":
        return FileExporter(**kwargs)
    elif exporter_type == "null":
        return NullExporter()
    else:
        raise ValueError(f"Unknown exporter type: {exporter_type}")