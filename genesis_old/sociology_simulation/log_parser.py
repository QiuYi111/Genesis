"""
Log parser for extracting simulation data from log files.
Supports parsing historical simulation logs to reconstruct simulation state.
"""

import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SimulationLogParser:
    """Parser for simulation log files."""
    
    def __init__(self):
        # Regex patterns for different log types
        self.patterns = {
            'turn_start': re.compile(r'Turn (\d+):'),
            'agent_action': re.compile(r'(\w+)\((\d+)\) (.+)'),
            'agent_move': re.compile(r'(\w+)\((\d+)\) moved to \((\d+), (\d+)\)'),
            'agent_inventory': re.compile(r'(\w+)\((\d+)\) (?:gained|lost|has) (.+)'),
            'skill_unlock': re.compile(r'(\w+)\((\d+)\) unlocked skill: (.+)'),
            'group_formation': re.compile(r'Group "(.+)" formed with members: (.+)'),
            'trinity_action': re.compile(r'Trinity: (.+)'),
            'resource_change': re.compile(r'Resource (\w+) at \((\d+), (\d+)\): (.+)'),
            'world_event': re.compile(r'World event: (.+)'),
        }
    
    def parse_log_file(self, log_path: Path) -> Dict[str, Any]:
        """Parse a single log file and extract simulation data."""
        
        simulation_data = {
            'turns': {},
            'agents': {},
            'world_events': [],
            'trinity_actions': [],
            'groups': {},
            'metadata': {
                'file_path': str(log_path),
                'parsed_at': datetime.now().isoformat(),
                'total_turns': 0
            }
        }
        
        current_turn = 0
        
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        self._parse_line(line, simulation_data, current_turn)
                        
                        # Check for turn changes
                        turn_match = self.patterns['turn_start'].search(line)
                        if turn_match:
                            current_turn = int(turn_match.group(1))
                            if current_turn not in simulation_data['turns']:
                                simulation_data['turns'][current_turn] = {
                                    'events': [],
                                    'agent_actions': {},
                                    'world_changes': []
                                }
                    
                    except Exception as e:
                        logger.warning(f"Error parsing line {line_num} in {log_path}: {e}")
                        continue
            
            simulation_data['metadata']['total_turns'] = len(simulation_data['turns'])
            
        except Exception as e:
            logger.error(f"Error reading log file {log_path}: {e}")
            raise
        
        return simulation_data
    
    def _parse_line(self, line: str, data: Dict[str, Any], current_turn: int):
        """Parse a single log line and extract relevant information."""
        
        line = line.strip()
        if not line:
            return
        
        # Parse agent actions
        action_match = self.patterns['agent_action'].search(line)
        if action_match:
            agent_name, agent_id, action = action_match.groups()
            agent_id = int(agent_id)
            
            self._ensure_agent_exists(data, agent_id, agent_name)
            self._add_agent_action(data, current_turn, agent_id, action)
            return
        
        # Parse agent movements
        move_match = self.patterns['agent_move'].search(line)
        if move_match:
            agent_name, agent_id, x, y = move_match.groups()
            agent_id, x, y = int(agent_id), int(x), int(y)
            
            self._ensure_agent_exists(data, agent_id, agent_name)
            data['agents'][agent_id]['positions'].append({
                'turn': current_turn,
                'x': x,
                'y': y
            })
            return
        
        # Parse skill unlocks
        skill_match = self.patterns['skill_unlock'].search(line)
        if skill_match:
            agent_name, agent_id, skill = skill_match.groups()
            agent_id = int(agent_id)
            
            self._ensure_agent_exists(data, agent_id, agent_name)
            data['agents'][agent_id]['skills'].append({
                'turn': current_turn,
                'skill': skill
            })
            return
        
        # Parse group formations
        group_match = self.patterns['group_formation'].search(line)
        if group_match:
            group_name, members_str = group_match.groups()
            members = [m.strip() for m in members_str.split(',')]
            
            data['groups'][group_name] = {
                'formed_at_turn': current_turn,
                'members': members,
                'events': []
            }
            return
        
        # Parse Trinity actions
        trinity_match = self.patterns['trinity_action'].search(line)
        if trinity_match:
            action = trinity_match.group(1)
            data['trinity_actions'].append({
                'turn': current_turn,
                'action': action
            })
            return
        
        # Parse world events
        event_match = self.patterns['world_event'].search(line)
        if event_match:
            event = event_match.group(1)
            data['world_events'].append({
                'turn': current_turn,
                'event': event
            })
            return
    
    def _ensure_agent_exists(self, data: Dict[str, Any], agent_id: int, agent_name: str):
        """Ensure agent exists in data structure."""
        if agent_id not in data['agents']:
            data['agents'][agent_id] = {
                'name': agent_name,
                'actions': [],
                'positions': [],
                'skills': [],
                'inventory_changes': []
            }
    
    def _add_agent_action(self, data: Dict[str, Any], turn: int, agent_id: int, action: str):
        """Add agent action to data."""
        data['agents'][agent_id]['actions'].append({
            'turn': turn,
            'action': action
        })
        
        # Also add to turn data
        if turn in data['turns']:
            if agent_id not in data['turns'][turn]['agent_actions']:
                data['turns'][turn]['agent_actions'][agent_id] = []
            data['turns'][turn]['agent_actions'][agent_id].append(action)
    
    def parse_multiple_logs(self, log_directory: Path, pattern: str = "*.log") -> Dict[str, Any]:
        """Parse multiple log files and combine data."""
        
        combined_data = {
            'simulations': {},
            'summary': {
                'total_files': 0,
                'total_turns': 0,
                'date_range': None,
                'agents_seen': set(),
                'unique_actions': set()
            }
        }
        
        log_files = list(log_directory.glob(pattern))
        log_files.sort(key=lambda x: x.stat().st_mtime)  # Sort by modification time
        
        for log_file in log_files:
            try:
                logger.info(f"Parsing {log_file.name}")
                file_data = self.parse_log_file(log_file)
                
                # Use filename as simulation identifier
                sim_id = log_file.stem
                combined_data['simulations'][sim_id] = file_data
                
                # Update summary
                combined_data['summary']['total_files'] += 1
                combined_data['summary']['total_turns'] += file_data['metadata']['total_turns']
                
                # Collect agents and actions
                for agent_id, agent_data in file_data['agents'].items():
                    combined_data['summary']['agents_seen'].add(agent_data['name'])
                    for action_entry in agent_data['actions']:
                        combined_data['summary']['unique_actions'].add(action_entry['action'])
                
            except Exception as e:
                logger.error(f"Failed to parse {log_file}: {e}")
                continue
        
        # Convert sets to lists for JSON serialization
        combined_data['summary']['agents_seen'] = list(combined_data['summary']['agents_seen'])
        combined_data['summary']['unique_actions'] = list(combined_data['summary']['unique_actions'])
        
        return combined_data
    
    def extract_simulation_timeline(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract a chronological timeline of events from parsed data."""
        
        timeline = []
        
        # Process each turn
        for turn_num in sorted(parsed_data['turns'].keys()):
            turn_data = parsed_data['turns'][turn_num]
            
            turn_event = {
                'turn': turn_num,
                'type': 'turn_start',
                'timestamp': None,  # Would need to be extracted from log timestamps
                'events': []
            }
            
            # Add agent actions
            for agent_id, actions in turn_data['agent_actions'].items():
                agent_name = parsed_data['agents'][agent_id]['name']
                for action in actions:
                    turn_event['events'].append({
                        'type': 'agent_action',
                        'agent_id': agent_id,
                        'agent_name': agent_name,
                        'action': action
                    })
            
            # Add world changes
            for change in turn_data['world_changes']:
                turn_event['events'].append({
                    'type': 'world_change',
                    'change': change
                })
            
            timeline.append(turn_event)
        
        # Add Trinity actions
        for trinity_action in parsed_data['trinity_actions']:
            # Find the corresponding turn event
            for turn_event in timeline:
                if turn_event['turn'] == trinity_action['turn']:
                    turn_event['events'].append({
                        'type': 'trinity_action',
                        'action': trinity_action['action']
                    })
                    break
        
        # Add world events
        for world_event in parsed_data['world_events']:
            for turn_event in timeline:
                if turn_event['turn'] == world_event['turn']:
                    turn_event['events'].append({
                        'type': 'world_event',
                        'event': world_event['event']
                    })
                    break
        
        return timeline
    
    def generate_agent_summary(self, parsed_data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """Generate summary statistics for each agent."""
        
        summaries = {}
        
        for agent_id, agent_data in parsed_data['agents'].items():
            summary = {
                'name': agent_data['name'],
                'total_actions': len(agent_data['actions']),
                'unique_actions': len(set(action['action'] for action in agent_data['actions'])),
                'skills_learned': len(agent_data['skills']),
                'positions_visited': len(agent_data['positions']),
                'action_distribution': {},
                'skill_timeline': agent_data['skills'],
                'movement_pattern': self._analyze_movement_pattern(agent_data['positions'])
            }
            
            # Calculate action distribution
            for action_entry in agent_data['actions']:
                action = action_entry['action']
                summary['action_distribution'][action] = summary['action_distribution'].get(action, 0) + 1
            
            summaries[agent_id] = summary
        
        return summaries
    
    def _analyze_movement_pattern(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze agent movement patterns."""
        
        if len(positions) < 2:
            return {'total_distance': 0, 'avg_distance_per_turn': 0, 'exploration_radius': 0}
        
        total_distance = 0
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for i in range(1, len(positions)):
            prev_pos = positions[i-1]
            curr_pos = positions[i]
            
            # Calculate distance moved
            dx = curr_pos['x'] - prev_pos['x']
            dy = curr_pos['y'] - prev_pos['y']
            distance = (dx**2 + dy**2)**0.5
            total_distance += distance
            
            # Track exploration bounds
            min_x = min(min_x, curr_pos['x'])
            max_x = max(max_x, curr_pos['x'])
            min_y = min(min_y, curr_pos['y'])
            max_y = max(max_y, curr_pos['y'])
        
        exploration_radius = max(max_x - min_x, max_y - min_y)
        avg_distance_per_turn = total_distance / (len(positions) - 1) if len(positions) > 1 else 0
        
        return {
            'total_distance': total_distance,
            'avg_distance_per_turn': avg_distance_per_turn,
            'exploration_radius': exploration_radius,
            'bounds': {'min_x': min_x, 'max_x': max_x, 'min_y': min_y, 'max_y': max_y}
        }


def parse_logs_cli():
    """Command-line interface for log parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse sociology simulation logs')
    parser.add_argument('log_path', help='Path to log file or directory')
    parser.add_argument('-o', '--output', help='Output JSON file path')
    parser.add_argument('-s', '--summary', action='store_true', help='Generate summary only')
    parser.add_argument('-t', '--timeline', action='store_true', help='Generate timeline')
    
    args = parser.parse_args()
    
    log_path = Path(args.log_path)
    parser_instance = SimulationLogParser()
    
    if log_path.is_file():
        # Parse single file
        data = parser_instance.parse_log_file(log_path)
    else:
        # Parse directory
        data = parser_instance.parse_multiple_logs(log_path)
    
    # Generate additional analysis if requested
    result = {'parsed_data': data}
    
    if args.timeline:
        if 'simulations' in data:
            # Multiple simulations
            result['timelines'] = {}
            for sim_id, sim_data in data['simulations'].items():
                result['timelines'][sim_id] = parser_instance.extract_simulation_timeline(sim_data)
        else:
            # Single simulation
            result['timeline'] = parser_instance.extract_simulation_timeline(data)
    
    if args.summary:
        if 'simulations' in data:
            # Multiple simulations
            result['agent_summaries'] = {}
            for sim_id, sim_data in data['simulations'].items():
                result['agent_summaries'][sim_id] = parser_instance.generate_agent_summary(sim_data)
        else:
            # Single simulation
            result['agent_summary'] = parser_instance.generate_agent_summary(data)
    
    # Output results
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {args.output}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parse_logs_cli()