"""
Event Orchestrator - Triggers world events based on collective agent behavior.

This system creates meaningful world events that respond to and shape agent behavior,
including natural disasters, resource discoveries, technological breakthroughs, and social movements.
"""

import json
import random
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from loguru import logger


class EventType(Enum):
    """Types of world events"""
    NATURAL_DISASTER = "natural_disaster"
    RESOURCE_DISCOVERY = "resource_discovery"
    TECHNOLOGICAL_BREAKTHROUGH = "technological_breakthrough"
    SOCIAL_MOVEMENT = "social_movement"
    MIGRATION = "migration"
    CONFLICT = "conflict"
    COOPERATION = "cooperation"
    CLIMATE_CHANGE = "climate_change"
    DISEASE_OUTBREAK = "disease_outbreak"
    CULTURAL_AWAKENING = "cultural_awakening"


@dataclass
class WorldEvent:
    """Represents a world event triggered by the Trinity system"""
    event_id: str
    event_type: EventType
    name: str
    description: str
    severity: float  # 0-1 severity level
    duration: int  # number of turns the event lasts
    affected_area: List[Tuple[int, int]]  # grid positions affected
    effects: Dict[str, Any]  # actual game effects
    triggers: Dict[str, Any]  # what triggered this event
    prerequisites: Dict[str, Any]  # conditions that enabled this event
    generation_turn: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'name': self.name,
            'description': self.description,
            'severity': self.severity,
            'duration': self.duration,
            'affected_area': self.affected_area,
            'effects': self.effects,
            'triggers': self.triggers,
            'prerequisites': self.prerequisites,
            'generation_turn': self.generation_turn
        }


class EventOrchestrator:
    """
    Orchestrates world events based on collective agent behavior patterns.
    
    This system creates meaningful events that respond to the evolving state of the society,
    including both challenges and opportunities that shape the agents' development.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.active_events: List[WorldEvent] = []
        self.event_history: List[WorldEvent] = []
        self.event_templates = self._load_event_templates()
        self.trigger_thresholds = config.get('event_trigger_thresholds', {
            'social_cooperation': 0.7,
            'resource_stress': 0.8,
            'population_density': 0.6,
            'skill_diversity': 0.5
        })
        
        # Event generation parameters
        self.event_probability = config.get('event_trigger_probability', 0.1)
        self.max_active_events = config.get('max_active_events', 3)
        self.event_cooldown = config.get('event_cooldown', 20)  # turns between events
        self.last_event_turn = 0
    
    def _load_event_templates(self) -> Dict[EventType, List[Dict[str, Any]]]:
        """Load event templates for different event types"""
        return {
            EventType.NATURAL_DISASTER: [
                {
                    'name': 'Drought',
                    'description': 'Extended period without rain affects water and food availability',
                    'severity_range': (0.6, 0.9),
                    'duration_range': (10, 30),
                    'effects': {
                        'water_reduction': 0.7,
                        'food_reduction': 0.4,
                        'temperature_increase': 5,
                        'migration_pressure': 0.3
                    }
                },
                {
                    'name': 'Flood',
                    'description': 'Heavy rains flood low-lying areas, destroying resources',
                    'severity_range': (0.5, 0.8),
                    'duration_range': (5, 15),
                    'effects': {
                        'water_increase': 2.0,
                        'food_destruction': 0.5,
                        'building_damage': 0.3,
                        'displacement': 0.4
                    }
                },
                {
                    'name': 'Wildfire',
                    'description': 'Fire spreads through forests, destroying wood and food sources',
                    'severity_range': (0.7, 0.9),
                    'duration_range': (3, 8),
                    'effects': {
                        'wood_destruction': 0.8,
                        'food_destruction': 0.6,
                        'forest_regrowth_time': 50,
                        'ash_fertilization': 0.2
                    }
                }
            ],
            EventType.RESOURCE_DISCOVERY: [
                {
                    'name': 'Rich Ore Vein',
                    'description': 'Discovery of a rich mineral deposit increases metal availability',
                    'severity_range': (0.4, 0.7),
                    'duration_range': (100, 200),
                    'effects': {
                        'metal_increase': 3.0,
                        'tool_quality_bonus': 0.3,
                        'population_attraction': 0.4
                    }
                },
                {
                    'name': 'Fertile Valley',
                    'description': 'Discovery of highly fertile land boosts food production',
                    'severity_range': (0.5, 0.8),
                    'duration_range': (150, 300),
                    'effects': {
                        'food_increase': 2.5,
                        'farming_efficiency': 1.5,
                        'settlement_growth': 0.5
                    }
                }
            ],
            EventType.TECHNOLOGICAL_BREAKTHROUGH: [
                {
                    'name': 'Fire Mastery',
                    'description': 'Collective understanding of fire creation and control revolutionizes survival',
                    'severity_range': (0.8, 1.0),
                    'duration_range': (200, 400),
                    'effects': {
                        'cooking_efficiency': 2.0,
                        'tool_crafting_bonus': 0.5,
                        'night_vision': 0.8,
                        'predator_defense': 0.7
                    }
                },
                {
                    'name': 'Advanced Agriculture',
                    'description': 'Development of systematic farming techniques transforms food production',
                    'severity_range': (0.7, 0.9),
                    'duration_range': (300, 500),
                    'effects': {
                        'food_sustainability': 3.0,
                        'population_capacity': 2.0,
                        'trade_goods': 1.5
                    }
                }
            ],
            EventType.SOCIAL_MOVEMENT: [
                {
                    'name': 'Great Migration',
                    'description': 'Collective decision to migrate to better territory',
                    'severity_range': (0.6, 0.8),
                    'duration_range': (15, 30),
                    'effects': {
                        'territory_expansion': 0.5,
                        'exploration_bonus': 2.0,
                        'social_cohesion': 0.3
                    }
                },
                {
                    'name': 'Cultural Renaissance',
                    'description': 'Period of rapid cultural and technological advancement',
                    'severity_range': (0.5, 0.7),
                    'duration_range': (50, 100),
                    'effects': {
                        'skill_learning_rate': 1.8,
                        'social_rule_adoption': 1.5,
                        'cooperation_bonus': 1.3
                    }
                }
            ],
            EventType.CONFLICT: [
                {
                    'name': 'Resource War',
                    'description': 'Escalating conflict over scarce resources',
                    'severity_range': (0.7, 0.9),
                    'duration_range': (10, 25),
                    'effects': {
                        'resource_destruction': 0.4,
                        'population_decline': 0.2,
                        'territory_reorganization': 0.6,
                        'leadership_emergence': 0.5
                    }
                },
                {
                    'name': 'Ideological Split',
                    'description': 'Society divides over fundamental disagreements',
                    'severity_range': (0.5, 0.8),
                    'duration_range': (20, 50),
                    'effects': {
                        'population_fragmentation': 0.4,
                        'cultural_divergence': 0.7,
                        'new_settlements': 0.6
                    }
                }
            ],
            EventType.COOPERATION: [
                {
                    'name': 'Great Alliance',
                    'description': 'Multiple groups form lasting cooperative relationships',
                    'severity_range': (0.6, 0.8),
                    'duration_range': (100, 200),
                    'effects': {
                        'trade_networks': 2.0,
                        'resource_sharing': 1.5,
                        'cultural_exchange': 1.3,
                        'defense_bonus': 1.4
                    }
                },
                {
                    'name': 'Collective Project',
                    'description': 'Society undertakes massive cooperative construction',
                    'severity_range': (0.5, 0.7),
                    'duration_range': (50, 100),
                    'effects': {
                        'infrastructure_bonus': 2.5,
                        'social_cohesion': 1.8,
                        'technological_advancement': 1.4
                    }
                }
            ]
        }
    
    def should_trigger_event(self, turn: int, patterns: List[Any], 
                           world_state: Dict[str, Any]) -> bool:
        """Determine if an event should be triggered based on current conditions"""
        
        # Check cooldown
        if turn - self.last_event_turn < self.event_cooldown:
            return False
        
        # Check max active events
        if len(self.active_events) >= self.max_active_events:
            return False
        
        # Calculate event probability based on patterns and world state
        probability = self._calculate_event_probability(patterns, world_state)
        
        return random.random() < probability
    
    def _calculate_event_probability(self, patterns: List[Any], 
                                   world_state: Dict[str, Any]) -> float:
        """Calculate probability of event based on current conditions"""
        base_probability = self.event_probability
        
        # Adjust based on patterns
        for pattern in patterns:
            if pattern.confidence >= 0.7:
                if pattern.pattern_type == 'collective':
                    base_probability += 0.1
                elif pattern.pattern_type == 'resource_usage':
                    base_probability += 0.05
                elif pattern.pattern_type == 'social':
                    base_probability += 0.08
        
        # Adjust based on world state
        agent_count = len(world_state.get('agents', {}))
        if agent_count > 20:
            base_probability += 0.05
        
        resource_stress = self._calculate_resource_stress(world_state)
        base_probability += resource_stress * 0.1
        
        return min(0.8, base_probability)
    
    def _calculate_resource_stress(self, world_state: Dict[str, Any]) -> float:
        """Calculate overall resource stress in the world"""
        total_resources = world_state.get('total_resources', {})
        agent_count = len(world_state.get('agents', {}))
        
        if agent_count == 0:
            return 0.0
        
        # Simple resource stress calculation
        total_food = total_resources.get('food', 0)
        total_water = total_resources.get('water', 0)
        
        # Stress increases as population grows relative to resources
        resource_per_agent = (total_food + total_water) / (agent_count * 10)
        return max(0.0, min(1.0, 1.0 - resource_per_agent))
    
    def generate_event(self, turn: int, patterns: List[Any], 
                      world_state: Dict[str, Any], world_width: int, world_height: int) -> Optional[WorldEvent]:
        """Generate a world event based on current conditions"""
        
        if not self.should_trigger_event(turn, patterns, world_state):
            return None
        
        # Select event type based on patterns and world state
        event_type = self._select_event_type(patterns, world_state)
        
        # Get event template
        templates = self.event_templates.get(event_type, [])
        if not templates:
            return None
        
        template = random.choice(templates)
        
        # Generate event details
        event_id = self._generate_event_id(event_type, turn)
        severity = random.uniform(*template['severity_range'])
        duration = random.randint(*template['duration_range'])
        affected_area = self._select_affected_area(world_width, world_height, event_type)
        
        event = WorldEvent(
            event_id=event_id,
            event_type=event_type,
            name=template['name'],
            description=template['description'],
            severity=severity,
            duration=duration,
            affected_area=affected_area,
            effects=template['effects'],
            triggers={
                'patterns': [p.pattern_id for p in patterns],
                'world_state': world_state
            },
            prerequisites=self._extract_prerequisites(patterns, world_state),
            generation_turn=turn
        )
        
        self.active_events.append(event)
        self.event_history.append(event)
        self.last_event_turn = turn
        
        logger.info(f"Generated world event: {event.name} (severity: {event.severity:.2f})")
        
        return event
    
    def _select_event_type(self, patterns: List[Any], world_state: Dict[str, Any]) -> EventType:
        """Select appropriate event type based on patterns and world state"""
        
        # Weight different event types based on conditions
        weights = {
            EventType.NATURAL_DISASTER: 0.1,
            EventType.RESOURCE_DISCOVERY: 0.2,
            EventType.TECHNOLOGICAL_BREAKTHROUGH: 0.15,
            EventType.SOCIAL_MOVEMENT: 0.15,
            EventType.CONFLICT: 0.1,
            EventType.COOPERATION: 0.2,
            EventType.CLIMATE_CHANGE: 0.1
        }
        
        # Adjust weights based on patterns
        for pattern in patterns:
            if pattern.pattern_type == 'resource_usage' and 'scarcity' in pattern.description.lower():
                weights[EventType.RESOURCE_DISCOVERY] += 0.1
                weights[EventType.CONFLICT] += 0.05
            elif pattern.pattern_type == 'collective':
                weights[EventType.COOPERATION] += 0.1
                weights[EventType.TECHNOLOGICAL_BREAKTHROUGH] += 0.05
            elif pattern.pattern_type == 'social' and 'isolation' in pattern.description.lower():
                weights[EventType.SOCIAL_MOVEMENT] += 0.1
        
        # Normalize weights
        total_weight = sum(weights.values())
        weights = {k: v/total_weight for k, v in weights.items()}
        
        # Select event type
        return random.choices(
            list(weights.keys()),
            weights=list(weights.values())
        )[0]
    
    def _select_affected_area(self, world_width: int, world_height: int, 
                            event_type: EventType) -> List[Tuple[int, int]]:
        """Select area affected by the event"""
        affected_area = []
        
        # Determine event center
        center_x = random.randint(world_width // 4, 3 * world_width // 4)
        center_y = random.randint(world_height // 4, 3 * world_height // 4)
        
        # Determine affected radius based on event type
        radius_map = {
            EventType.NATURAL_DISASTER: 8,
            EventType.RESOURCE_DISCOVERY: 5,
            EventType.TECHNOLOGICAL_BREAKTHROUGH: 0,  # Global effect
            EventType.SOCIAL_MOVEMENT: 0,  # Global effect
            EventType.CONFLICT: 6,
            EventType.COOPERATION: 0,  # Global effect
            EventType.CLIMATE_CHANGE: 0  # Global effect
        }
        
        radius = radius_map.get(event_type, 5)
        
        if radius == 0:  # Global effect
            return [(x, y) for x in range(world_width) for y in range(world_height)]
        
        # Localized effect
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                x, y = center_x + dx, center_y + dy
                if 0 <= x < world_width and 0 <= y < world_height:
                    affected_area.append((x, y))
        
        return affected_area
    
    def _generate_event_id(self, event_type: EventType, turn: int) -> str:
        """Generate unique event ID"""
        content = f"{event_type.value}_{turn}_{datetime.now().isoformat()}"
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _extract_prerequisites(self, patterns: List[Any], world_state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract event prerequisites from patterns and world state"""
        return {
            'patterns': [p.to_dict() for p in patterns],
            'agent_count': len(world_state.get('agents', {})),
            'total_resources': world_state.get('total_resources', {}),
            'buildings': world_state.get('buildings', 0)
        }
    
    def update_events(self, turn: int):
        """Update active events and remove expired ones"""
        expired_events = []
        
        for event in self.active_events:
            if turn - event.generation_turn >= event.duration:
                expired_events.append(event)
                logger.info(f"Event ended: {event.name}")
        
        # Remove expired events
        for event in expired_events:
            self.active_events.remove(event)
    
    def get_event_effects(self, position: Tuple[int, int], turn: int) -> Dict[str, Any]:
        """Get cumulative effects of active events at a specific position"""
        effects = {}
        
        for event in self.active_events:
            if position in event.affected_area:
                # Merge effects
                for effect_key, effect_value in event.effects.items():
                    if effect_key in effects:
                        if isinstance(effect_value, (int, float)):
                            effects[effect_key] *= effect_value
                        else:
                            effects[effect_key] = effect_value
                    else:
                        effects[effect_key] = effect_value
        
        return effects
    
    def get_active_events_summary(self) -> Dict[str, Any]:
        """Get summary of currently active events"""
        return {
            'active_events': len(self.active_events),
            'events': [event.to_dict() for event in self.active_events],
            'total_events_triggered': len(self.event_history)
        }
    
    def get_event_history_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get summary of event history"""
        recent_events = self.event_history[-limit:] if limit else self.event_history
        
        event_type_counts = {}
        for event in self.event_history:
            event_type = event.event_type.value
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
        
        return {
            'total_events': len(self.event_history),
            'events_by_type': event_type_counts,
            'recent_events': [event.to_dict() for event in recent_events]
        }
    
    def reset_events(self):
        """Reset all events (for testing purposes)"""
        self.active_events.clear()
        self.event_history.clear()
        self.last_event_turn = 0