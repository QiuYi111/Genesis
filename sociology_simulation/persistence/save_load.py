"""Comprehensive save/load system for simulation state persistence"""
import json
import pickle
import gzip
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
from loguru import logger

from ..core.agent_state import AgentState, AgentStateManager
from ..core.interactions import InteractionManager, InteractionResult, InteractionContext
from ..core.world_events import WorldEventManager, ActiveEvent
from ..analytics.metrics import SimulationAnalytics, MetricSnapshot
from ..config import Config


@dataclass
class SaveMetadata:
    """Metadata for a saved simulation"""
    save_id: str
    timestamp: float
    simulation_name: str
    description: str
    turn_number: int
    population_count: int
    file_size_bytes: int
    version: str = "2.0"
    compression: bool = True
    checksum: str = ""


@dataclass
class SimulationState:
    """Complete simulation state for serialization"""
    metadata: SaveMetadata
    config: Dict[str, Any]
    agents: Dict[str, Dict[str, Any]]
    world_state: Dict[str, Any]
    active_events: List[Dict[str, Any]]
    interaction_history: List[Dict[str, Any]]
    analytics_data: Dict[str, Any]
    resource_state: Dict[str, Any]
    turn_counter: int


class SimulationSaveManager:
    """Manages saving and loading of simulation states"""
    
    def __init__(self, save_directory: str = "saves"):
        self.save_directory = Path(save_directory)
        self.save_directory.mkdir(exist_ok=True)
        self.metadata_file = self.save_directory / "saves_metadata.json"
        self.auto_save_enabled = True
        self.auto_save_interval = 10  # Every 10 turns
        self.max_saves = 50  # Keep maximum 50 saves
        self.compression_enabled = True
        
        # Load existing metadata
        self.saves_metadata = self._load_metadata()
    
    def save_simulation(self, 
                       agents: List[AgentState],
                       world_state: Dict[str, Any],
                       event_manager: WorldEventManager,
                       interaction_manager: InteractionManager,
                       analytics: SimulationAnalytics,
                       config: Config,
                       simulation_name: str = "",
                       description: str = "",
                       auto_save: bool = False) -> str:
        """Save complete simulation state"""
        
        try:
            # Generate save ID and metadata
            timestamp = time.time()
            save_id = self._generate_save_id(timestamp, auto_save)
            
            if not simulation_name:
                simulation_name = f"Simulation_{datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')}"
            
            # Create save metadata
            metadata = SaveMetadata(
                save_id=save_id,
                timestamp=timestamp,
                simulation_name=simulation_name,
                description=description,
                turn_number=world_state.get("current_turn", 0),
                population_count=len([a for a in agents if a.status.value == "alive"]),
                file_size_bytes=0,  # Will be updated after saving
                compression=self.compression_enabled
            )
            
            # Serialize all components
            simulation_state = SimulationState(
                metadata=metadata,
                config=self._serialize_config(config),
                agents=self._serialize_agents(agents),
                world_state=world_state,
                active_events=self._serialize_events(event_manager),
                interaction_history=self._serialize_interactions(interaction_manager),
                analytics_data=self._serialize_analytics(analytics),
                resource_state=world_state.get("resources", {}),
                turn_counter=world_state.get("current_turn", 0)
            )
            
            # Save to file
            save_path = self._write_save_file(save_id, simulation_state)
            
            # Update metadata with file size and checksum
            metadata.file_size_bytes = save_path.stat().st_size
            metadata.checksum = self._calculate_checksum(save_path)
            simulation_state.metadata = metadata
            
            # Re-save with updated metadata
            self._write_save_file(save_id, simulation_state)
            
            # Update metadata registry
            self.saves_metadata[save_id] = asdict(metadata)
            self._save_metadata()
            
            # Cleanup old saves if needed
            if auto_save:
                self._cleanup_old_auto_saves()
            else:
                self._cleanup_old_saves()
            
            logger.info(f"Simulation saved: {save_id} ({simulation_name})")
            return save_id
            
        except Exception as e:
            logger.error(f"Failed to save simulation: {e}")
            raise
    
    def load_simulation(self, save_id: str) -> SimulationState:
        """Load complete simulation state"""
        
        try:
            save_path = self.save_directory / f"{save_id}.save"
            if not save_path.exists():
                raise FileNotFoundError(f"Save file not found: {save_id}")
            
            # Verify checksum if available
            if save_id in self.saves_metadata:
                expected_checksum = self.saves_metadata[save_id].get("checksum", "")
                if expected_checksum:
                    actual_checksum = self._calculate_checksum(save_path)
                    if actual_checksum != expected_checksum:
                        logger.warning(f"Checksum mismatch for save {save_id}")
            
            # Load and deserialize
            simulation_state = self._read_save_file(save_path)
            
            logger.info(f"Simulation loaded: {save_id}")
            return simulation_state
            
        except Exception as e:
            logger.error(f"Failed to load simulation {save_id}: {e}")
            raise
    
    def restore_simulation(self, 
                          simulation_state: SimulationState,
                          agent_manager: AgentStateManager,
                          event_manager: WorldEventManager,
                          interaction_manager: InteractionManager,
                          analytics: SimulationAnalytics) -> Dict[str, Any]:
        """Restore simulation components from saved state"""
        
        try:
            # Restore agents
            agents = self._deserialize_agents(simulation_state.agents, agent_manager)
            
            # Restore world events
            self._deserialize_events(simulation_state.active_events, event_manager)
            
            # Restore interaction history
            self._deserialize_interactions(simulation_state.interaction_history, interaction_manager)
            
            # Restore analytics
            self._deserialize_analytics(simulation_state.analytics_data, analytics)
            
            # Return world state
            world_state = simulation_state.world_state
            world_state["current_turn"] = simulation_state.turn_counter
            
            logger.info(f"Simulation restored from save {simulation_state.metadata.save_id}")
            return world_state
            
        except Exception as e:
            logger.error(f"Failed to restore simulation: {e}")
            raise
    
    def list_saves(self, include_auto_saves: bool = True) -> List[SaveMetadata]:
        """List all available saves"""
        saves = []
        
        for save_id, metadata_dict in self.saves_metadata.items():
            if not include_auto_saves and save_id.startswith("auto_"):
                continue
            
            # Convert dict back to SaveMetadata object
            metadata = SaveMetadata(**metadata_dict)
            saves.append(metadata)
        
        # Sort by timestamp, newest first
        saves.sort(key=lambda x: x.timestamp, reverse=True)
        return saves
    
    def delete_save(self, save_id: str) -> bool:
        """Delete a saved simulation"""
        try:
            save_path = self.save_directory / f"{save_id}.save"
            if save_path.exists():
                save_path.unlink()
            
            if save_id in self.saves_metadata:
                del self.saves_metadata[save_id]
                self._save_metadata()
            
            logger.info(f"Deleted save: {save_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete save {save_id}: {e}")
            return False
    
    def get_save_info(self, save_id: str) -> Optional[SaveMetadata]:
        """Get detailed information about a save"""
        if save_id not in self.saves_metadata:
            return None
        
        return SaveMetadata(**self.saves_metadata[save_id])
    
    def auto_save_if_needed(self, 
                           current_turn: int,
                           agents: List[AgentState],
                           world_state: Dict[str, Any],
                           event_manager: WorldEventManager,
                           interaction_manager: InteractionManager,
                           analytics: SimulationAnalytics,
                           config: Config) -> Optional[str]:
        """Perform auto-save if conditions are met"""
        
        if not self.auto_save_enabled:
            return None
        
        if current_turn % self.auto_save_interval != 0:
            return None
        
        try:
            save_id = self.save_simulation(
                agents=agents,
                world_state=world_state,
                event_manager=event_manager,
                interaction_manager=interaction_manager,
                analytics=analytics,
                config=config,
                simulation_name=f"Auto-save Turn {current_turn}",
                description=f"Automatic save at turn {current_turn}",
                auto_save=True
            )
            
            logger.info(f"Auto-save completed: {save_id}")
            return save_id
            
        except Exception as e:
            logger.error(f"Auto-save failed: {e}")
            return None
    
    def export_save_summary(self, save_id: str, output_file: str) -> bool:
        """Export human-readable summary of a save"""
        try:
            simulation_state = self.load_simulation(save_id)
            
            summary = {
                "metadata": asdict(simulation_state.metadata),
                "statistics": {
                    "total_agents": len(simulation_state.agents),
                    "living_agents": len([a for a in simulation_state.agents.values() 
                                        if a.get("status") == "alive"]),
                    "active_events": len(simulation_state.active_events),
                    "interactions_recorded": len(simulation_state.interaction_history),
                    "world_size": simulation_state.world_state.get("size", "unknown")
                },
                "world_state_summary": {
                    "turn": simulation_state.turn_counter,
                    "era": simulation_state.world_state.get("era", "unknown"),
                    "resource_types": len(simulation_state.resource_state)
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            logger.info(f"Save summary exported to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export save summary: {e}")
            return False
    
    # Private helper methods
    
    def _generate_save_id(self, timestamp: float, auto_save: bool = False) -> str:
        """Generate unique save ID"""
        prefix = "auto_" if auto_save else "manual_"
        time_str = datetime.fromtimestamp(timestamp).strftime('%Y%m%d_%H%M%S')
        hash_str = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
        return f"{prefix}{time_str}_{hash_str}"
    
    def _serialize_config(self, config: Config) -> Dict[str, Any]:
        """Serialize configuration"""
        # Convert config to dict representation
        return asdict(config)
    
    def _serialize_agents(self, agents: List[AgentState]) -> Dict[str, Dict[str, Any]]:
        """Serialize agents"""
        return {agent.agent_id: agent.to_dict() for agent in agents}
    
    def _serialize_events(self, event_manager: WorldEventManager) -> List[Dict[str, Any]]:
        """Serialize active world events"""
        return [asdict(event) for event in event_manager.active_events.values()]
    
    def _serialize_interactions(self, interaction_manager: InteractionManager) -> List[Dict[str, Any]]:
        """Serialize interaction history"""
        # Note: This is simplified - full implementation would need proper serialization
        return []  # Placeholder
    
    def _serialize_analytics(self, analytics: SimulationAnalytics) -> Dict[str, Any]:
        """Serialize analytics data"""
        return {
            "metric_history": [asdict(snapshot) for snapshot in analytics.metric_history],
            "trend_analyses": {name: asdict(trend) for name, trend in analytics.trend_analyses.items()},
            "alerts": analytics.alerts
        }
    
    def _deserialize_agents(self, agents_data: Dict[str, Dict[str, Any]], 
                           agent_manager: AgentStateManager) -> List[AgentState]:
        """Deserialize agents"""
        agents = []
        for agent_id, agent_data in agents_data.items():
            agent = AgentState.from_dict(agent_data)
            agent_manager.add_agent(agent)
            agents.append(agent)
        return agents
    
    def _deserialize_events(self, events_data: List[Dict[str, Any]], 
                           event_manager: WorldEventManager):
        """Deserialize world events"""
        for event_data in events_data:
            # Reconstruct ActiveEvent objects
            # Note: This would need proper deserialization logic
            pass
    
    def _deserialize_interactions(self, interactions_data: List[Dict[str, Any]], 
                                 interaction_manager: InteractionManager):
        """Deserialize interaction history"""
        # Reconstruct interaction history
        # Note: This would need proper deserialization logic
        pass
    
    def _deserialize_analytics(self, analytics_data: Dict[str, Any], 
                              analytics: SimulationAnalytics):
        """Deserialize analytics data"""
        # Restore metric history
        for snapshot_data in analytics_data.get("metric_history", []):
            # Convert back to MetricSnapshot objects
            pass
        
        # Restore alerts
        analytics.alerts = analytics_data.get("alerts", [])
    
    def _write_save_file(self, save_id: str, simulation_state: SimulationState) -> Path:
        """Write simulation state to file"""
        save_path = self.save_directory / f"{save_id}.save"
        
        # Serialize to JSON first
        data = asdict(simulation_state)
        json_data = json.dumps(data, default=str).encode('utf-8')
        
        if self.compression_enabled:
            # Compress the data
            with gzip.open(save_path, 'wb') as f:
                f.write(json_data)
        else:
            # Save uncompressed
            with open(save_path, 'wb') as f:
                f.write(json_data)
        
        return save_path
    
    def _read_save_file(self, save_path: Path) -> SimulationState:
        """Read simulation state from file"""
        try:
            # Try compressed first
            with gzip.open(save_path, 'rb') as f:
                json_data = f.read().decode('utf-8')
        except (gzip.BadGzipFile, OSError):
            # Try uncompressed
            with open(save_path, 'rb') as f:
                json_data = f.read().decode('utf-8')
        
        data = json.loads(json_data)
        
        # Reconstruct SimulationState object
        # Note: This would need proper deserialization of nested objects
        metadata = SaveMetadata(**data['metadata'])
        
        simulation_state = SimulationState(
            metadata=metadata,
            config=data['config'],
            agents=data['agents'],
            world_state=data['world_state'],
            active_events=data['active_events'],
            interaction_history=data['interaction_history'],
            analytics_data=data['analytics_data'],
            resource_state=data['resource_state'],
            turn_counter=data['turn_counter']
        )
        
        return simulation_state
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Load saves metadata from file"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load saves metadata: {e}")
            return {}
    
    def _save_metadata(self):
        """Save metadata to file"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.saves_metadata, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _cleanup_old_saves(self):
        """Remove old saves if exceeding maximum"""
        saves = self.list_saves(include_auto_saves=False)
        
        if len(saves) > self.max_saves:
            # Remove oldest saves
            to_remove = saves[self.max_saves:]
            for save_metadata in to_remove:
                self.delete_save(save_metadata.save_id)
                logger.info(f"Cleaned up old save: {save_metadata.save_id}")
    
    def _cleanup_old_auto_saves(self):
        """Remove old auto-saves (keep only last 10)"""
        auto_saves = [s for s in self.list_saves() if s.save_id.startswith("auto_")]
        
        if len(auto_saves) > 10:
            # Remove oldest auto-saves
            to_remove = auto_saves[10:]
            for save_metadata in to_remove:
                self.delete_save(save_metadata.save_id)


class SimulationImportExport:
    """Handles import/export of simulations in different formats"""
    
    @staticmethod
    def export_to_json(simulation_state: SimulationState, output_file: str):
        """Export simulation to human-readable JSON"""
        data = asdict(simulation_state)
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Simulation exported to JSON: {output_file}")
    
    @staticmethod
    def export_agents_csv(agents: List[AgentState], output_file: str):
        """Export agents data to CSV"""
        import csv
        
        with open(output_file, 'w', newline='') as csvfile:
            fieldnames = ['agent_id', 'name', 'age', 'status', 'health', 'position_x', 'position_y']
            fieldnames.extend(['strength', 'intelligence', 'charisma', 'dexterity', 'constitution', 'wisdom'])
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for agent in agents:
                row = {
                    'agent_id': agent.agent_id,
                    'name': agent.name,
                    'age': agent.age,
                    'status': agent.status.value,
                    'health': agent.health,
                    'position_x': agent.position[0],
                    'position_y': agent.position[1]
                }
                row.update(agent.attributes)
                writer.writerow(row)
        
        logger.info(f"Agents exported to CSV: {output_file}")
    
    @staticmethod
    def export_metrics_csv(analytics: SimulationAnalytics, output_file: str):
        """Export metrics history to CSV"""
        import csv
        
        if not analytics.metric_history:
            logger.warning("No metrics to export")
            return
        
        with open(output_file, 'w', newline='') as csvfile:
            # Extract all possible field names
            fieldnames = ['turn', 'timestamp']
            sample_snapshot = analytics.metric_history[0]
            
            for category in ['population_metrics', 'economic_metrics', 'social_metrics', 
                           'technology_metrics', 'environment_metrics']:
                category_data = getattr(sample_snapshot, category, {})
                for key in category_data.keys():
                    fieldnames.append(f"{category}_{key}")
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for snapshot in analytics.metric_history:
                row = {'turn': snapshot.turn, 'timestamp': snapshot.timestamp}
                
                # Flatten metrics
                for category in ['population_metrics', 'economic_metrics', 'social_metrics', 
                               'technology_metrics', 'environment_metrics']:
                    category_data = getattr(snapshot, category, {})
                    for key, value in category_data.items():
                        if isinstance(value, (int, float)):
                            row[f"{category}_{key}"] = value
                
                writer.writerow(row)
        
        logger.info(f"Metrics exported to CSV: {output_file}")


# Global save manager instance
_save_manager: Optional[SimulationSaveManager] = None

def get_save_manager() -> SimulationSaveManager:
    """Get global save manager instance"""
    global _save_manager
    if _save_manager is None:
        _save_manager = SimulationSaveManager()
    return _save_manager