"""
Web adapter service to bridge World snapshot with web export functionality
Provides clean separation between core simulation and web concerns
"""

from typing import Dict, List, Any, Optional
from .exporter import FileExporter, NullExporter, create_snapshot_from_world, Exporter


class WebExportAdapter:
    """Adapter to convert World snapshot to web export format"""
    
    def __init__(self, exporter: Optional[Exporter] = None):
        """Initialize adapter with exporter"""
        self.exporter = exporter or FileExporter()
    
    def export_turn(self, world_snapshot: Dict[str, Any], turn: int, 
                   events: Optional[List[Dict[str, Any]]] = None,
                   metrics: Optional[Dict[str, float]] = None) -> None:
        """Export a turn snapshot using the configured exporter"""
        
        # Convert world snapshot to standardized format
        snapshot = create_snapshot_from_world(
            world_snapshot=world_snapshot,
            turn=turn,
            events=events,
            metrics=metrics
        )
        
        # Write snapshot using exporter
        self.exporter.write_snapshot(snapshot, turn=turn)
    
    def export_simulation_metadata(self, era: str, world_size: int, num_agents: int,
                                 terrain_types: List[str], resource_rules: Dict) -> Dict[str, Any]:
        """Create simulation metadata for web export"""
        
        return {
            "era": era,
            "world_size": world_size,
            "num_agents": num_agents,
            "terrain_types": terrain_types,
            "resource_rules": resource_rules,
            "schema_version": "1.0"
        }


class LegacyWebExportBridge:
    """Bridge to maintain compatibility with existing web export code during transition"""
    
    def __init__(self, adapter: WebExportAdapter):
        """Initialize bridge with new adapter"""
        self.adapter = adapter
        self._metadata_cache = None
    
    def initialize_export(self, world_size: int, era_prompt: str, num_agents: int,
                         terrain_types: List[str], resource_rules: Dict):
        """Initialize export (compatibility method)"""
        # Cache metadata for later use
        self._metadata_cache = {
            "era": era_prompt,
            "world_size": world_size,
            "num_agents": num_agents,
            "terrain_types": terrain_types,
            "resource_rules": resource_rules
        }
    
    def save_world_state(self, world_map: List[List[str]], resources: Dict):
        """Save world state (compatibility method)"""
        # This would be called during initialization, but we don't have turn info yet
        # Store for later export
        self._world_map = world_map
        self._resources = resources
    
    def save_turn_data(self, turn_num: int, agents: List, conversations: List[str],
                      events: List[str], turn_log: List[str]):
        """Save turn data and export snapshot"""
        
        # Convert agents to snapshot format
        agent_data = []
        for agent in agents:
            agent_dict = {
                'aid': agent.aid,
                'name': agent.name,
                'pos': list(agent.pos),
                'age': agent.age,
                'health': agent.health,
                'hunger': agent.hunger,
                'attributes': agent.attributes,
                'inventory': agent.inventory,
                'goal': agent.goal,
                'skills': agent.skills if hasattr(agent, 'skills') else {}
            }
            agent_data.append(agent_dict)
        
        # Create world snapshot
        world_snapshot = {
            "size": self._metadata_cache["world_size"],
            "agents": agent_data,
            "terrain": self._world_map,
            "resources": self._resources
        }
        
        # Convert events and logs to standardized format
        standardized_events = []
        for event in events:
            standardized_events.append({
                "type": "simulation_event",
                "content": event,
                "timestamp": turn_num
            })
        
        # Create metrics
        metrics = {
            "turn": turn_num,
            "agent_count": len(agents),
            "conversation_count": len(conversations),
            "event_count": len(events)
        }
        
        # Export using new adapter
        self.adapter.export_turn(
            world_snapshot=world_snapshot,
            turn=turn_num,
            events=standardized_events,
            metrics=metrics
        )


# Factory functions for easy setup
def create_web_adapter(exporter_type: str = "file", **exporter_kwargs) -> WebExportAdapter:
    """Create web export adapter with specified exporter type"""
    from .exporter import get_exporter
    
    exporter = get_exporter(exporter_type, **exporter_kwargs)
    return WebExportAdapter(exporter)


def create_legacy_bridge(exporter_type: str = "file", **exporter_kwargs) -> LegacyWebExportBridge:
    """Create legacy bridge for backward compatibility"""
    adapter = create_web_adapter(exporter_type, **exporter_kwargs)
    return LegacyWebExportBridge(adapter)