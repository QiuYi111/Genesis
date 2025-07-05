"""World events and environmental changes system"""
import random
import time
import math
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger

from .agent_state import AgentState, AgentStatus
from ..config import get_config


class EventSeverity(Enum):
    """Severity levels for world events"""
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CATASTROPHIC = "catastrophic"


class EventType(Enum):
    """Types of world events"""
    WEATHER = "weather"
    NATURAL_DISASTER = "natural_disaster"
    RESOURCE = "resource"
    DISEASE = "disease"
    MIGRATION = "migration"
    DISCOVERY = "discovery"
    SEASONAL = "seasonal"
    TECHNOLOGICAL = "technological"


@dataclass
class EventEffect:
    """Effect of an event on the world"""
    area_affected: List[Tuple[int, int]] = field(default_factory=list)
    duration_turns: int = 1
    resource_changes: Dict[str, float] = field(default_factory=dict)  # Resource spawn rate multipliers
    terrain_changes: Dict[Tuple[int, int], str] = field(default_factory=dict)
    agent_effects: Dict[str, Any] = field(default_factory=dict)  # Effects on agents
    global_effects: Dict[str, Any] = field(default_factory=dict)  # World-wide effects
    message: str = ""


@dataclass
class ActiveEvent:
    """An active world event"""
    event_id: str
    event_type: EventType
    severity: EventSeverity
    start_turn: int
    duration: int
    effects: EventEffect
    description: str
    remaining_duration: int = 0
    
    def __post_init__(self):
        self.remaining_duration = self.duration


class BaseWorldEvent(ABC):
    """Base class for world events"""
    
    def __init__(self, severity: EventSeverity = EventSeverity.MINOR):
        self.severity = severity
        self.event_type = EventType.WEATHER  # Override in subclasses
    
    @abstractmethod
    def generate_effect(self, world_state: Dict[str, Any]) -> EventEffect:
        """Generate the effect of this event"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get human-readable description of the event"""
        pass
    
    def get_probability(self, world_state: Dict[str, Any]) -> float:
        """Get probability of this event occurring (0-1)"""
        return 0.1  # Default 10% chance


class WeatherEvent(BaseWorldEvent):
    """Weather-related events"""
    
    def __init__(self, weather_type: str, severity: EventSeverity = EventSeverity.MINOR):
        super().__init__(severity)
        self.event_type = EventType.WEATHER
        self.weather_type = weather_type  # "drought", "flood", "storm", "cold_snap", "heat_wave"
    
    def generate_effect(self, world_state: Dict[str, Any]) -> EventEffect:
        """Generate weather effects"""
        config = get_config()
        world_size = config.world.size
        
        effect = EventEffect()
        
        if self.weather_type == "drought":
            # Affects water sources and agriculture
            effect.duration_turns = 3 + (self.severity.value == "major") * 2
            effect.resource_changes = {
                "water": 0.1,  # Severely reduced water
                "fish": 0.3,   # Reduced fish
                "apple": 0.5   # Reduced fruit
            }
            effect.agent_effects = {
                "thirst_increase": 2.0,
                "health_decrease": 0.5
            }
            effect.message = "A severe drought has struck the land"
            
        elif self.weather_type == "flood":
            # Affects low-lying areas
            affected_area = []
            for x in range(world_size):
                for y in range(world_size):
                    if random.random() < 0.3:  # 30% of map affected
                        affected_area.append((x, y))
            
            effect.area_affected = affected_area
            effect.duration_turns = 2
            effect.resource_changes = {
                "fish": 1.5,   # More fish from flooding
                "wood": 0.7,   # Damaged trees
                "stone": 0.9   # Harder to mine
            }
            effect.agent_effects = {
                "health_decrease": 1.0,
                "movement_penalty": 0.5
            }
            effect.message = "Heavy rains have caused widespread flooding"
            
        elif self.weather_type == "storm":
            # Sudden destructive weather
            storm_center = (random.randint(0, world_size-1), random.randint(0, world_size-1))
            storm_radius = 5 + (self.severity.value == "major") * 3
            
            affected_area = []
            for x in range(max(0, storm_center[0] - storm_radius), 
                          min(world_size, storm_center[0] + storm_radius + 1)):
                for y in range(max(0, storm_center[1] - storm_radius), 
                              min(world_size, storm_center[1] + storm_radius + 1)):
                    distance = ((x - storm_center[0])**2 + (y - storm_center[1])**2)**0.5
                    if distance <= storm_radius:
                        affected_area.append((x, y))
            
            effect.area_affected = affected_area
            effect.duration_turns = 1
            effect.agent_effects = {
                "health_decrease": 2.0,
                "shelter_required": True
            }
            effect.message = f"A violent storm has hit the region around {storm_center}"
            
        return effect
    
    def get_description(self) -> str:
        return f"{self.severity.value.title()} {self.weather_type.replace('_', ' ')}"
    
    def get_probability(self, world_state: Dict[str, Any]) -> float:
        # Weather events more likely in certain seasons
        current_turn = world_state.get("current_turn", 0)
        season_factor = 1.0 + 0.3 * math.sin(current_turn * 0.1)  # Seasonal variation
        
        base_prob = {
            "drought": 0.05,
            "flood": 0.04,
            "storm": 0.08,
            "cold_snap": 0.06,
            "heat_wave": 0.05
        }.get(self.weather_type, 0.05)
        
        return base_prob * season_factor


class NaturalDisasterEvent(BaseWorldEvent):
    """Natural disaster events"""
    
    def __init__(self, disaster_type: str, severity: EventSeverity = EventSeverity.MAJOR):
        super().__init__(severity)
        self.event_type = EventType.NATURAL_DISASTER
        self.disaster_type = disaster_type  # "earthquake", "volcano", "wildfire", "avalanche"
    
    def generate_effect(self, world_state: Dict[str, Any]) -> EventEffect:
        """Generate disaster effects"""
        config = get_config()
        world_size = config.world.size
        
        effect = EventEffect()
        
        if self.disaster_type == "earthquake":
            # Random epicenter with decreasing effects by distance
            epicenter = (random.randint(0, world_size-1), random.randint(0, world_size-1))
            max_radius = 8 if self.severity == EventSeverity.CATASTROPHIC else 5
            
            affected_area = []
            terrain_changes = {}
            
            for x in range(world_size):
                for y in range(world_size):
                    distance = ((x - epicenter[0])**2 + (y - epicenter[1])**2)**0.5
                    if distance <= max_radius:
                        affected_area.append((x, y))
                        
                        # Chance of terrain changes
                        if distance <= 2 and random.random() < 0.3:
                            terrain_changes[(x, y)] = "MOUNTAIN"  # Create mountains from upheaval
            
            effect.area_affected = affected_area
            effect.terrain_changes = terrain_changes
            effect.duration_turns = 1
            effect.resource_changes = {
                "stone": 1.3,  # More exposed stone
                "water": 0.8   # Disrupted water sources
            }
            effect.agent_effects = {
                "health_decrease": 5.0,
                "structure_damage": 0.7  # 70% chance to damage buildings
            }
            effect.message = f"A powerful earthquake has struck near {epicenter}"
            
        elif self.disaster_type == "wildfire":
            # Fire spreads from ignition point
            ignition_point = (random.randint(0, world_size-1), random.randint(0, world_size-1))
            fire_spread_radius = 6
            
            affected_area = []
            terrain_changes = {}
            
            for x in range(max(0, ignition_point[0] - fire_spread_radius), 
                          min(world_size, ignition_point[0] + fire_spread_radius + 1)):
                for y in range(max(0, ignition_point[1] - fire_spread_radius), 
                              min(world_size, ignition_point[1] + fire_spread_radius + 1)):
                    if random.random() < 0.4:  # Fire spread chance
                        affected_area.append((x, y))
                        # Convert forests to grassland
                        if random.random() < 0.6:
                            terrain_changes[(x, y)] = "GRASSLAND"
            
            effect.area_affected = affected_area
            effect.terrain_changes = terrain_changes
            effect.duration_turns = 2
            effect.resource_changes = {
                "wood": 0.2,   # Destroyed trees
                "apple": 0.1,  # Destroyed fruit
                "ash": 2.0     # Creates ash (new resource)
            }
            effect.agent_effects = {
                "health_decrease": 3.0,
                "evacuation_required": True
            }
            effect.message = f"A wildfire has started near {ignition_point} and is spreading"
        
        return effect
    
    def get_description(self) -> str:
        return f"{self.severity.value.title()} {self.disaster_type}"
    
    def get_probability(self, world_state: Dict[str, Any]) -> float:
        # Natural disasters are rare
        base_prob = {
            "earthquake": 0.01,
            "volcano": 0.005,
            "wildfire": 0.02,
            "avalanche": 0.008
        }.get(self.disaster_type, 0.01)
        
        return base_prob


class ResourceEvent(BaseWorldEvent):
    """Resource-related events"""
    
    def __init__(self, resource_type: str, change_type: str, severity: EventSeverity = EventSeverity.MODERATE):
        super().__init__(severity)
        self.event_type = EventType.RESOURCE
        self.resource_type = resource_type
        self.change_type = change_type  # "depletion", "discovery", "migration"
    
    def generate_effect(self, world_state: Dict[str, Any]) -> EventEffect:
        """Generate resource effects"""
        effect = EventEffect()
        
        if self.change_type == "depletion":
            # Resource becomes scarce
            multiplier = 0.3 if self.severity == EventSeverity.MAJOR else 0.6
            effect.resource_changes = {self.resource_type: multiplier}
            effect.duration_turns = 5
            effect.message = f"{self.resource_type.title()} deposits are becoming depleted"
            
        elif self.change_type == "discovery":
            # New resource deposits found
            multiplier = 2.0 if self.severity == EventSeverity.MAJOR else 1.5
            effect.resource_changes = {self.resource_type: multiplier}
            effect.duration_turns = 8
            effect.message = f"Rich {self.resource_type} deposits have been discovered"
            
        elif self.change_type == "migration":
            # Animals/resources migrate (fish, game)
            if self.resource_type in ["fish", "game"]:
                # Randomly redistribute
                effect.resource_changes = {self.resource_type: 0.5}  # Reduced in current areas
                effect.duration_turns = 3
                effect.message = f"{self.resource_type.title()} have migrated to new areas"
        
        return effect
    
    def get_description(self) -> str:
        return f"{self.resource_type.title()} {self.change_type}"
    
    def get_probability(self, world_state: Dict[str, Any]) -> float:
        # Resource events based on usage patterns
        return 0.03


class DiseaseEvent(BaseWorldEvent):
    """Disease outbreak events"""
    
    def __init__(self, disease_name: str, severity: EventSeverity = EventSeverity.MODERATE):
        super().__init__(severity)
        self.event_type = EventType.DISEASE
        self.disease_name = disease_name
    
    def generate_effect(self, world_state: Dict[str, Any]) -> EventEffect:
        """Generate disease effects"""
        effect = EventEffect()
        
        # Disease affects agents' health
        health_decrease = {
            EventSeverity.MINOR: 2.0,
            EventSeverity.MODERATE: 5.0,
            EventSeverity.MAJOR: 10.0,
            EventSeverity.CATASTROPHIC: 15.0
        }[self.severity]
        
        effect.duration_turns = 3 + (self.severity == EventSeverity.MAJOR) * 2
        effect.agent_effects = {
            "health_decrease": health_decrease,
            "contagion_chance": 0.3,  # 30% chance to spread to nearby agents
            "immunity_after_recovery": True
        }
        effect.message = f"An outbreak of {self.disease_name} has been reported"
        
        return effect
    
    def get_description(self) -> str:
        return f"{self.disease_name} outbreak ({self.severity.value})"
    
    def get_probability(self, world_state: Dict[str, Any]) -> float:
        # Disease more likely with higher population density
        population = world_state.get("population", 0)
        base_prob = 0.02
        density_factor = min(2.0, population / 50)  # More disease with more people
        return base_prob * density_factor


class WorldEventManager:
    """Manages world events and environmental changes"""
    
    def __init__(self):
        self.active_events: Dict[str, ActiveEvent] = {}
        self.event_history: List[ActiveEvent] = []
        self.event_generators = self._initialize_event_generators()
        self.resource_multipliers: Dict[str, float] = {}
        self.global_effects: Dict[str, Any] = {}
        self.turn_counter = 0
        self.last_major_event_turn = 0
    
    def _initialize_event_generators(self) -> List[BaseWorldEvent]:
        """Initialize all possible event types"""
        generators = []
        
        # Weather events
        weather_types = ["drought", "flood", "storm", "cold_snap", "heat_wave"]
        for weather in weather_types:
            for severity in [EventSeverity.MINOR, EventSeverity.MODERATE, EventSeverity.MAJOR]:
                generators.append(WeatherEvent(weather, severity))
        
        # Natural disasters
        disaster_types = ["earthquake", "wildfire", "volcano", "avalanche"]
        for disaster in disaster_types:
            for severity in [EventSeverity.MODERATE, EventSeverity.MAJOR, EventSeverity.CATASTROPHIC]:
                generators.append(NaturalDisasterEvent(disaster, severity))
        
        # Resource events
        resource_types = ["wood", "stone", "fish", "apple", "water"]
        change_types = ["depletion", "discovery", "migration"]
        for resource in resource_types:
            for change in change_types:
                generators.append(ResourceEvent(resource, change))
        
        # Disease events
        diseases = ["fever", "plague", "infection", "weakness"]
        for disease in diseases:
            for severity in [EventSeverity.MINOR, EventSeverity.MODERATE, EventSeverity.MAJOR]:
                generators.append(DiseaseEvent(disease, severity))
        
        return generators
    
    def update(self, world_state: Dict[str, Any]) -> List[str]:
        """Update world events for the current turn"""
        self.turn_counter += 1
        events_this_turn = []
        
        # Update active events
        expired_events = []
        for event_id, event in self.active_events.items():
            event.remaining_duration -= 1
            if event.remaining_duration <= 0:
                expired_events.append(event_id)
        
        # Remove expired events
        for event_id in expired_events:
            event = self.active_events[event_id]
            self.event_history.append(event)
            del self.active_events[event_id]
            events_this_turn.append(f"{event.description} has ended")
            logger.info(f"Event ended: {event.description}")
        
        # Check for new events
        world_state["current_turn"] = self.turn_counter
        world_state["population"] = len(world_state.get("agents", []))
        
        # Prevent too many major events happening close together
        turns_since_major = self.turn_counter - self.last_major_event_turn
        major_event_cooldown = turns_since_major < 5
        
        for generator in self.event_generators:
            # Skip major events if in cooldown
            if major_event_cooldown and generator.severity in [EventSeverity.MAJOR, EventSeverity.CATASTROPHIC]:
                continue
            
            probability = generator.get_probability(world_state)
            
            if random.random() < probability:
                # Generate new event
                event_id = f"{generator.event_type.value}_{self.turn_counter}_{random.randint(1000, 9999)}"
                effect = generator.generate_effect(world_state)
                
                new_event = ActiveEvent(
                    event_id=event_id,
                    event_type=generator.event_type,
                    severity=generator.severity,
                    start_turn=self.turn_counter,
                    duration=effect.duration_turns,
                    effects=effect,
                    description=generator.get_description()
                )
                
                self.active_events[event_id] = new_event
                events_this_turn.append(effect.message)
                
                if generator.severity in [EventSeverity.MAJOR, EventSeverity.CATASTROPHIC]:
                    self.last_major_event_turn = self.turn_counter
                
                logger.info(f"New event: {generator.get_description()} - {effect.message}")
                
                # Only one event per turn to avoid chaos
                break
        
        # Update resource multipliers
        self._update_resource_multipliers()
        
        return events_this_turn
    
    def _update_resource_multipliers(self):
        """Update global resource multipliers based on active events"""
        self.resource_multipliers = {}
        
        for event in self.active_events.values():
            for resource, multiplier in event.effects.resource_changes.items():
                if resource not in self.resource_multipliers:
                    self.resource_multipliers[resource] = 1.0
                self.resource_multipliers[resource] *= multiplier
    
    def apply_effects_to_agents(self, agents: List[AgentState]) -> List[str]:
        """Apply active event effects to agents"""
        effect_messages = []
        
        for event in self.active_events.values():
            affected_agents = []
            
            # Determine which agents are affected
            if event.effects.area_affected:
                # Localized event
                for agent in agents:
                    if agent.position in event.effects.area_affected:
                        affected_agents.append(agent)
            else:
                # Global event
                affected_agents = agents
            
            # Apply effects
            for agent in affected_agents:
                if agent.status != AgentStatus.ALIVE:
                    continue
                
                effects = event.effects.agent_effects
                
                if "health_decrease" in effects:
                    damage = effects["health_decrease"]
                    agent.health = max(0, agent.health - damage)
                    if agent.health == 0:
                        agent.status = AgentStatus.DEAD
                        effect_messages.append(f"{agent.name} died from {event.description}")
                
                if "thirst_increase" in effects:
                    agent.thirst = min(100, agent.thirst + effects["thirst_increase"])
                
                if "structure_damage" in effects and random.random() < effects["structure_damage"]:
                    # Damage agent's buildings (simplified)
                    effect_messages.append(f"{agent.name}'s structures were damaged by {event.description}")
                
                if "evacuation_required" in effects:
                    # Force agent to move (simplified)
                    agent.add_memory(f"Had to evacuate due to {event.description}", "event", 0.8)
                
                if "contagion_chance" in effects and random.random() < effects["contagion_chance"]:
                    # Disease spreads to nearby agents
                    agent.add_memory(f"Contracted {event.description}", "event", 0.7)
        
        return effect_messages
    
    def get_resource_multiplier(self, resource_type: str) -> float:
        """Get current resource spawn multiplier"""
        return self.resource_multipliers.get(resource_type, 1.0)
    
    def get_active_events_summary(self) -> List[str]:
        """Get summary of currently active events"""
        return [
            f"{event.description} (turns remaining: {event.remaining_duration})"
            for event in self.active_events.values()
        ]
    
    def get_event_history_summary(self, limit: int = 10) -> List[str]:
        """Get summary of recent events"""
        recent_events = self.event_history[-limit:]
        return [
            f"Turn {event.start_turn}: {event.description}"
            for event in recent_events
        ]
    
    def force_event(self, event_type: str, severity: str = "moderate") -> bool:
        """Force a specific event to occur (for testing/storytelling)"""
        try:
            severity_enum = EventSeverity(severity)
            
            for generator in self.event_generators:
                if (hasattr(generator, 'weather_type') and generator.weather_type == event_type) or \
                   (hasattr(generator, 'disaster_type') and generator.disaster_type == event_type) or \
                   (hasattr(generator, 'disease_name') and generator.disease_name == event_type):
                    
                    generator.severity = severity_enum
                    event_id = f"forced_{event_type}_{self.turn_counter}"
                    effect = generator.generate_effect({"current_turn": self.turn_counter})
                    
                    forced_event = ActiveEvent(
                        event_id=event_id,
                        event_type=generator.event_type,
                        severity=severity_enum,
                        start_turn=self.turn_counter,
                        duration=effect.duration_turns,
                        effects=effect,
                        description=generator.get_description()
                    )
                    
                    self.active_events[event_id] = forced_event
                    logger.info(f"Forced event: {generator.get_description()}")
                    return True
            
            return False
            
        except ValueError:
            logger.error(f"Invalid severity level: {severity}")
            return False