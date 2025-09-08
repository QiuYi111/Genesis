"""
Web UI data export functionality
Saves world state, agents, and simulation data to JSON for web visualization
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class WebDataExporter:
    """Exports simulation data for web UI consumption"""
    
    def __init__(self, output_dir: str = "web_data"):
        self.output_dir = output_dir
        self.current_export = {
            'metadata': {},
            'world': {},
            'turns': [],
            'current_turn': 0
        }
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
    
    def initialize_export(self, world_size: int, era_prompt: str, num_agents: int, 
                         terrain_types: List[str], resource_rules: Dict):
        """Initialize export with world metadata"""
        self.current_export['metadata'] = {
            'era': era_prompt,
            'world_size': world_size,
            'num_agents': num_agents,
            'terrain_types': terrain_types,
            'resource_rules': resource_rules,
            'start_time': datetime.now().isoformat()
        }
        
        self.current_export['world'] = {
            'size': world_size,
            'terrain': None,
            'resources': {}
        }
    
    def save_world_state(self, world_map: List[List[str]], resources: Dict):
        """Save the world terrain and resource state"""
        self.current_export['world']['terrain'] = world_map
        
        # Convert resource coordinates to string format for JSON
        formatted_resources = {}
        for (x, y), resource_dict in resources.items():
            key = f"{x},{y}"
            formatted_resources[key] = resource_dict
        
        self.current_export['world']['resources'] = formatted_resources
    
    def save_turn_data(self, turn_num: int, agents: List, conversations: List[str], 
                      events: List[str], turn_log: List[str]):
        """Save data for a specific turn"""
        
        # Convert agents to serializable format
        agent_data = []
        for agent in agents:
            agent_dict = {
                'id': agent.aid,
                'name': agent.name,
                'pos': list(agent.pos),
                'age': agent.age,
                'health': agent.health,
                'hunger': agent.hunger,
                'attributes': agent.attributes,
                'inventory': agent.inventory,
                'goal': agent.goal,
                'log': agent.log[-5:] if len(agent.log) > 5 else agent.log,  # Last 5 actions
                'memory_agents': len(agent.memory.get('agents', [])),
                'memory_locations': len(agent.memory.get('locations', []))
            }
            agent_data.append(agent_dict)
        
        turn_data = {
            'turn': turn_num,
            'agents': agent_data,
            'conversations': conversations,
            'events': events,
            'turn_log': turn_log,
            'timestamp': datetime.now().isoformat()
        }
        
        self.current_export['turns'].append(turn_data)
        self.current_export['current_turn'] = turn_num
    
    def export_to_file(self, filename: Optional[str] = None):
        """Export current data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"simulation_data_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.current_export, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def export_incremental(self, turn_num: int):
        """Export data incrementally (every few turns)"""
        if turn_num % 5 == 0:  # Export every 5 turns
            filename = f"simulation_turn_{turn_num:03d}.json"
            return self.export_to_file(filename)
        return None

# Global exporter instance
_global_exporter: Optional[WebDataExporter] = None

def get_web_exporter() -> WebDataExporter:
    """Get or create the global web data exporter"""
    global _global_exporter
    if _global_exporter is None:
        _global_exporter = WebDataExporter()
    return _global_exporter

def initialize_web_export(world_size: int, era_prompt: str, num_agents: int, 
                         terrain_types: List[str], resource_rules: Dict):
    """Initialize web export with world data"""
    exporter = get_web_exporter()
    exporter.initialize_export(world_size, era_prompt, num_agents, terrain_types, resource_rules)

def save_world_for_web(world_map: List[List[str]], resources: Dict):
    """Save world state for web export"""
    exporter = get_web_exporter()
    exporter.save_world_state(world_map, resources)

def save_turn_for_web(turn_num: int, agents: List, conversations: List[str], 
                     events: List[str], turn_log: List[str]):
    """Save turn data for web export"""
    exporter = get_web_exporter()
    exporter.save_turn_data(turn_num, agents, conversations, events, turn_log)

def export_web_data(filename: Optional[str] = None) -> str:
    """Export all data to JSON file"""
    exporter = get_web_exporter()
    return exporter.export_to_file(filename)

def export_incremental_web_data(turn_num: int) -> Optional[str]:
    """Export data incrementally"""
    exporter = get_web_exporter()
    return exporter.export_incremental(turn_num)