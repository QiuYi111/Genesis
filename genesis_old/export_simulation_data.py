#!/usr/bin/env python3
"""
Export simulation data for web UI visualization
Reads log files and outputs JSON data that can be consumed by the web interface
"""

import json
import re
import os
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

class SimulationDataExporter:
    def __init__(self):
        self.terrain_map = []
        self.resource_data = {}
        self.turns = []
        self.agents = {}
        self.conversations = []
        self.world_size = 64
        
    def parse_log_file(self, log_file_path: str) -> Dict[str, Any]:
        """Parse a simulation log file and extract data"""
        print(f"Parsing log file: {log_file_path}")
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        current_turn = None
        current_turn_data = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Extract world initialization data
            if "INITIALIZING WORLD FOR ERA:" in line:
                era_match = re.search(r'ERA: (.+)', line)
                if era_match:
                    self.era = era_match.group(1)
                    
            elif "TERRAIN TYPES:" in line:
                terrain_match = re.search(r'TERRAIN TYPES: (.+)', line)
                if terrain_match:
                    self.terrain_types = [t.strip() for t in terrain_match.group(1).split(',')]
                    
            elif "World size:" in line:
                size_match = re.search(r'World size: (\d+)x(\d+)', line)
                if size_match:
                    self.world_size = int(size_match.group(1))
                    
            elif "Number of agents:" in line:
                agent_match = re.search(r'Number of agents: (\d+)', line)
                if agent_match:
                    self.num_agents = int(agent_match.group(1))
                    
            # Extract resource information
            elif re.match(r'\s*[A-Z_]+: \d+ units', line):
                resource_match = re.search(r'([A-Z_]+): (\d+) units', line)
                if resource_match:
                    resource_name = resource_match.group(1).lower()
                    resource_count = int(resource_match.group(2))
                    self.resource_data[resource_name] = resource_count
                    
            # Extract turn information
            elif "===== TURN" in line:
                turn_match = re.search(r'TURN (\d+)', line)
                if turn_match:
                    turn_num = int(turn_match.group(1))
                    if current_turn_data:
                        self.turns.append(current_turn_data)
                    
                    current_turn = turn_num
                    current_turn_data = {
                        'turn': turn_num,
                        'agents': [],
                        'conversations': [],
                        'events': []
                    }
                    
            # Extract agent actions
            elif "行动 →" in line and current_turn_data:
                agent_match = re.search(r'(\S+)\((\d+)\).*行动 → (.+)', line)
                if agent_match:
                    agent_name = agent_match.group(1)
                    agent_id = int(agent_match.group(2))
                    action = agent_match.group(3)
                    
                    current_turn_data['events'].append({
                        'type': 'action',
                        'agent_name': agent_name,
                        'agent_id': agent_id,
                        'action': action
                    })
                    
            # Extract agent goals
            elif "personal goal ➜" in line and current_turn_data:
                goal_match = re.search(r'(\S+)\((\d+)\) personal goal ➜ (.+)', line)
                if goal_match:
                    agent_name = goal_match.group(1)
                    agent_id = int(goal_match.group(2))
                    goal = goal_match.group(3)
                    
                    # Store agent information
                    agent_key = f"{agent_name}_{agent_id}"
                    if agent_key not in self.agents:
                        self.agents[agent_key] = {
                            'id': agent_id,
                            'name': agent_name,
                            'goal': goal,
                            'history': []
                        }
                    
            # Extract conversations
            elif "↔" in line and current_turn_data:
                conv_match = re.search(r'(\S+)\((\d+)\) ↔ (\S+)\((\d+)\): (.+)', line)
                if conv_match:
                    agent1_name = conv_match.group(1)
                    agent1_id = int(conv_match.group(2))
                    agent2_name = conv_match.group(3)
                    agent2_id = int(conv_match.group(4))
                    content = conv_match.group(5)
                    
                    conversation = {
                        'agent1': {'name': agent1_name, 'id': agent1_id},
                        'agent2': {'name': agent2_name, 'id': agent2_id},
                        'content': content,
                        'turn': current_turn
                    }
                    
                    current_turn_data['conversations'].append(conversation)
                    self.conversations.append(conversation)
                    
            # Extract turn summary
            elif "TURN SUMMARY" in line:
                summary_match = re.search(r'TURN SUMMARY - (\d+) agents alive', line)
                if summary_match and current_turn_data:
                    current_turn_data['agents_alive'] = int(summary_match.group(1))
        
        # Add the last turn if it exists
        if current_turn_data:
            self.turns.append(current_turn_data)
            
        return self.create_export_data()
    
    def create_export_data(self) -> Dict[str, Any]:
        """Create the final export data structure"""
        
        # Generate sample terrain and resources since log doesn't contain this info
        terrain_map = self.generate_sample_terrain()
        resources = self.generate_sample_resources()
        
        # Generate agent positions for each turn
        self.generate_agent_positions()
        
        export_data = {
            'metadata': {
                'era': getattr(self, 'era', 'Stone Age'),
                'world_size': self.world_size,
                'num_agents': getattr(self, 'num_agents', 20),
                'terrain_types': getattr(self, 'terrain_types', ['FOREST', 'OCEAN', 'MOUNTAIN', 'GRASSLAND']),
                'export_time': datetime.now().isoformat()
            },
            'world': {
                'size': self.world_size,
                'terrain': terrain_map,
                'resources': resources
            },
            'turns': self.turns,
            'agents': self.agents,
            'conversations': self.conversations,
            'resource_totals': self.resource_data
        }
        
        return export_data
    
    def generate_sample_terrain(self) -> List[List[str]]:
        """Generate sample terrain map"""
        import random
        
        terrain_types = getattr(self, 'terrain_types', ['FOREST', 'OCEAN', 'MOUNTAIN', 'GRASSLAND'])
        terrain_map = []
        
        for y in range(self.world_size):
            row = []
            for x in range(self.world_size):
                # Generate varied terrain
                distance = ((x - self.world_size/2)**2 + (y - self.world_size/2)**2)**0.5
                noise = random.random() * 0.5
                
                if distance < 10 + noise * 5:
                    row.append('GRASSLAND')
                elif distance < 20 + noise * 8:
                    row.append(random.choice(['FOREST', 'GRASSLAND']))
                elif distance < 28 + noise * 5:
                    row.append(random.choice(['MOUNTAIN', 'FOREST']))
                else:
                    row.append('OCEAN')
            terrain_map.append(row)
        
        return terrain_map
    
    def generate_sample_resources(self) -> Dict[str, Dict[str, int]]:
        """Generate sample resource distribution"""
        import random
        
        resources = {}
        
        for y in range(self.world_size):
            for x in range(self.world_size):
                pos = f"{x},{y}"
                terrain = 'GRASSLAND'  # Default terrain
                
                # Add resources based on terrain type
                if pos not in resources:
                    resources[pos] = {}
                
                if terrain == 'FOREST' and random.random() > 0.5:
                    resources[pos]['wood'] = random.randint(1, 3)
                elif terrain == 'OCEAN' and random.random() > 0.6:
                    resources[pos]['fish'] = random.randint(1, 2)
                elif terrain == 'MOUNTAIN' and random.random() > 0.4:
                    resources[pos]['stone'] = random.randint(1, 3)
                elif terrain == 'GRASSLAND' and random.random() > 0.8:
                    resources[pos]['apple'] = random.randint(1, 2)
        
        return resources
    
    def generate_agent_positions(self):
        """Generate agent positions for each turn"""
        import random
        
        # Generate consistent agent data across turns
        agent_positions = {}
        
        for turn_data in self.turns:
            turn_num = turn_data['turn']
            agents_alive = turn_data.get('agents_alive', 20)
            
            # Generate or update agent positions
            turn_agents = []
            
            for i in range(agents_alive):
                agent_id = i
                agent_name = f"Agent{i}"
                
                # Get or create agent position
                if agent_id not in agent_positions:
                    agent_positions[agent_id] = {
                        'x': random.randint(0, self.world_size - 1),
                        'y': random.randint(0, self.world_size - 1),
                        'name': agent_name
                    }
                
                # Add some movement over time
                if turn_num > 0:
                    agent_positions[agent_id]['x'] = max(0, min(self.world_size - 1, 
                        agent_positions[agent_id]['x'] + random.randint(-2, 2)))
                    agent_positions[agent_id]['y'] = max(0, min(self.world_size - 1, 
                        agent_positions[agent_id]['y'] + random.randint(-2, 2)))
                
                # Create agent data
                agent_data = {
                    'id': agent_id,
                    'name': agent_positions[agent_id]['name'],
                    'pos': [agent_positions[agent_id]['x'], agent_positions[agent_id]['y']],
                    'age': 25 + random.randint(0, 30),
                    'health': 80 + random.randint(0, 20),
                    'hunger': random.randint(0, 50),
                    'attributes': {
                        'strength': random.randint(1, 10),
                        'curiosity': random.randint(1, 10),
                        'charm': random.randint(1, 10)
                    },
                    'inventory': {
                        'wood': random.randint(0, 5),
                        'stone': random.randint(0, 3),
                        'apple': random.randint(0, 2)
                    },
                    'goal': 'Explore the world and gather resources',
                    'recentMessages': []
                }
                
                turn_agents.append(agent_data)
            
            turn_data['agents'] = turn_agents
    
    def export_to_json(self, output_path: str, data: Dict[str, Any]):
        """Export data to JSON file"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Data exported to: {output_path}")
    
    def find_latest_log(self, logs_dir: str = "logs") -> Optional[str]:
        """Find the latest log file"""
        if not os.path.exists(logs_dir):
            return None
        
        log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
        if not log_files:
            return None
        
        # Sort by modification time
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)), reverse=True)
        return os.path.join(logs_dir, log_files[0])

def main():
    parser = argparse.ArgumentParser(description="Export simulation data for web UI")
    parser.add_argument('--log-file', type=str, help='Path to log file')
    parser.add_argument('--output', type=str, default='simulation_data.json', help='Output JSON file')
    parser.add_argument('--logs-dir', type=str, default='logs', help='Directory containing log files')
    
    args = parser.parse_args()
    
    exporter = SimulationDataExporter()
    
    # Determine log file to use
    log_file = args.log_file
    if not log_file:
        log_file = exporter.find_latest_log(args.logs_dir)
        if not log_file:
            print(f"No log files found in {args.logs_dir}")
            return
    
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return
    
    # Parse log file and export data
    try:
        data = exporter.parse_log_file(log_file)
        exporter.export_to_json(args.output, data)
        print(f"Successfully exported simulation data!")
        print(f"Turns: {len(data['turns'])}")
        print(f"Agents: {len(data['agents'])}")
        print(f"Conversations: {len(data['conversations'])}")
        
    except Exception as e:
        print(f"Error exporting data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()