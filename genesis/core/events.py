"""
Event system for Project Genesis.
Manages world events, agent interactions, and system notifications.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from loguru import logger


class EventType(Enum):
    """Types of events that can occur in the simulation"""
    AGENT_BIRTH = "agent_birth"
    AGENT_DEATH = "agent_death"
    RESOURCE_DISCOVERY = "resource_discovery"
    RESOURCE_DEPLETION = "resource_depletion"
    BUILDING_CONSTRUCTED = "building_constructed"
    BUILDING_DESTROYED = "building_destroyed"
    CLIMATE_CHANGE = "climate_change"
    TECHNOLOGY_DISCOVERED = "technology_discovered"
    SOCIAL_INTERACTION = "social_interaction"
    TRINITY_EVENT = "trinity_event"
    ERA_TRANSITION = "era_transition"
    WORLD_EVENT = "world_event"


@dataclass
class Event:
    """Base event class"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.WORLD_EVENT
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    target: Optional[str] = None
    priority: int = 1  # 1=low, 5=high


@dataclass
class EventCallback:
    """Event callback registration"""
    event_types: List[EventType]
    callback: Callable[[Event], None]
    priority: int = 0
    once: bool = False


class EventManager:
    """Central event management system"""
    
    def __init__(self):
        self.events: List[Event] = []
        self.callbacks: List[EventCallback] = []
        self.event_history: List[Event] = []
        self.stats = {
            "total_events": 0,
            "events_by_type": {event_type: 0 for event_type in EventType},
            "events_by_priority": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }
    
    def register_callback(self, 
                         event_types: List[EventType], 
                         callback: Callable[[Event], None],
                         priority: int = 0,
                         once: bool = False):
        """Register a callback for specific event types"""
        callback_obj = EventCallback(
            event_types=event_types,
            callback=callback,
            priority=priority,
            once=once
        )
        self.callbacks.append(callback_obj)
        # Sort by priority (higher priority first)
        self.callbacks.sort(key=lambda x: x.priority, reverse=True)
    
    def unregister_callback(self, callback: Callable[[Event], None]):
        """Unregister a callback"""
        self.callbacks = [cb for cb in self.callbacks if cb.callback != callback]
    
    def emit(self, event: Event):
        """Emit an event to all registered callbacks"""
        self.events.append(event)
        self.event_history.append(event)
        self.stats["total_events"] += 1
        self.stats["events_by_type"][event.type] += 1
        self.stats["events_by_priority"][event.priority] += 1
        
        logger.debug(f"Event emitted: {event.type.value} - {event.data}")
        
        # Trigger callbacks
        for callback in self.callbacks:
            if event.type in callback.event_types:
                try:
                    callback.callback(event)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
                
                # Remove one-time callbacks
                if callback.once:
                    self.callbacks.remove(callback)
    
    def create_event(self, 
                    event_type: EventType,
                    data: Dict[str, Any] = None,
                    source: str = None,
                    target: str = None,
                    priority: int = 1) -> Event:
        """Create and emit a new event"""
        event = Event(
            type=event_type,
            data=data or {},
            source=source,
            target=target,
            priority=priority
        )
        self.emit(event)
        return event
    
    def get_events(self, 
                  event_type: EventType = None,
                  source: str = None,
                  target: str = None,
                  limit: int = None) -> List[Event]:
        """Get events matching criteria"""
        events = self.event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        if source:
            events = [e for e in events if e.source == source]
        if target:
            events = [e for e in events if e.target == target]
        
        if limit:
            events = events[-limit:]
        
        return events
    
    def get_recent_events(self, minutes: int = 60) -> List[Event]:
        """Get events from the last N minutes"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [e for e in self.event_history if e.timestamp > cutoff]
    
    def clear_events(self, event_type: EventType = None):
        """Clear events, optionally filtered by type"""
        if event_type:
            self.events = [e for e in self.events if e.type != event_type]
            self.event_history = [e for e in self.event_history if e.type != event_type]
        else:
            self.events.clear()
            self.event_history.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event statistics"""
        return {
            "total_events": self.stats["total_events"],
            "events_by_type": {k.value: v for k, v in self.stats["events_by_type"].items()},
            "events_by_priority": self.stats["events_by_priority"],
            "active_callbacks": len(self.callbacks),
            "total_history": len(self.event_history)
        }


class EventBus:
    """Global event bus for cross-system communication"""
    
    def __init__(self):
        self._instance = None
    
    def get_instance(self) -> EventManager:
        """Get the global event manager instance"""
        if self._instance is None:
            self._instance = EventManager()
        return self._instance


# Global event bus instance
event_bus = EventBus()


class EventEmitter:
    """Mixin class for objects that can emit events"""
    
    def __init__(self):
        self.event_manager = event_bus.get_instance()
    
    def emit_event(self, 
                  event_type: EventType,
                  data: Dict[str, Any] = None,
                  target: str = None,
                  priority: int = 1):
        """Emit an event from this object"""
        return self.event_manager.create_event(
            event_type=event_type,
            data=data,
            source=getattr(self, 'id', str(id(self))),
            target=target,
            priority=priority
        )


# Convenience functions for common events
def emit_agent_birth(agent_id: str, position: Tuple[int, int], attributes: Dict[str, Any]):
    """Emit agent birth event"""
    return event_bus.get_instance().create_event(
        EventType.AGENT_BIRTH,
        data={"agent_id": agent_id, "position": position, "attributes": attributes},
        source=agent_id
    )


def emit_agent_death(agent_id: str, position: Tuple[int, int], cause: str):
    """Emit agent death event"""
    return event_bus.get_instance().create_event(
        EventType.AGENT_DEATH,
        data={"agent_id": agent_id, "position": position, "cause": cause},
        source=agent_id
    )


def emit_resource_discovery(agent_id: str, resource_type: str, position: Tuple[int, int], amount: float):
    """Emit resource discovery event"""
    return event_bus.get_instance().create_event(
        EventType.RESOURCE_DISCOVERY,
        data={"resource_type": resource_type, "position": position, "amount": amount},
        source=agent_id
    )


def emit_building_construction(agent_id: str, building_type: str, position: Tuple[int, int]):
    """Emit building construction event"""
    return event_bus.get_instance().create_event(
        EventType.BUILDING_CONSTRUCTED,
        data={"building_type": building_type, "position": position},
        source=agent_id
    )


def emit_technology_discovered(agent_id: str, technology: str, complexity: float):
    """Emit technology discovery event"""
    return event_bus.get_instance().create_event(
        EventType.TECHNOLOGY_DISCOVERED,
        data={"technology": technology, "complexity": complexity},
        source=agent_id
    )


if __name__ == "__main__":
    # Test the event system
    manager = EventManager()
    
    def test_callback(event: Event):
        print(f"Received event: {event.type.value} - {event.data}")
    
    # Register callback
    manager.register_callback([EventType.AGENT_BIRTH, EventType.AGENT_DEATH], test_callback)
    
    # Emit test events
    manager.create_event(EventType.AGENT_BIRTH, data={"name": "Test Agent"})
    manager.create_event(EventType.AGENT_DEATH, data={"name": "Test Agent", "cause": "starvation"})
    
    print("Event system test completed")
    print(f"Stats: {manager.get_stats()}")