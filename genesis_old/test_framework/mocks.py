"""
Mock objects and test utilities for Project Genesis testing framework

This module provides fake implementations of core interfaces to enable
pure function testing without external dependencies.
"""

from typing import List, Tuple, Dict, Optional, Any
from dataclasses import dataclass
import random


@dataclass
class Position:
    """Simple position representation for testing"""
    x: int
    y: int
    
    def __iter__(self):
        return iter((self.x, self.y))


class FakeWorldView:
    """
    Fake implementation of WorldView Protocol for testing Agent.decide()
    
    Provides deterministic, controlled world state for pure function testing.
    """
    
    def __init__(self, 
                 visible_resources: Optional[Dict[Tuple[int, int], Dict[str, int]]] = None,
                 neighbor_agents: Optional[List[int]] = None,
                 resource_signals: Optional[Dict[str, float]] = None):
        """
        Initialize fake world view with controlled data
        
        Args:
            visible_resources: Map of positions to resource counts
            neighbor_agents: List of nearby agent IDs  
            resource_signals: Resource scarcity signals
        """
        self._visible_resources = visible_resources or {}
        self._neighbor_agents = neighbor_agents or []
        self._resource_signals = resource_signals or {"wood": 0.5, "fish": 0.3, "stone": 0.7}
    
    def get_visible(self, pos: Position, radius: int) -> List[Tuple[Tuple[int, int], Dict[str, int]]]:
        """
        Get visible resources within radius of position
        
        Returns list of (position, resources) tuples
        """
        visible = []
        pos_tuple = (pos.x, pos.y)
        
        for resource_pos, resources in self._visible_resources.items():
            # Simple Manhattan distance for testing
            distance = abs(resource_pos[0] - pos_tuple[0]) + abs(resource_pos[1] - pos_tuple[1])
            if distance <= radius:
                visible.append((resource_pos, resources.copy()))
        
        return visible
    
    def get_neighbors(self, pos: Position, radius: int) -> List[int]:
        """
        Get neighboring agents within radius
        
        Returns list of agent IDs
        """
        # For testing, return predefined neighbors
        # In real implementation, this would check actual agent positions
        return self._neighbor_agents.copy()
    
    def get_signals(self) -> Dict[str, float]:
        """
        Get resource scarcity signals
        
        Returns dict mapping resource types to scarcity scores (0.0-1.0)
        """
        return self._resource_signals.copy()
    
    # Builder methods for test setup
    def with_resource(self, pos: Tuple[int, int], resource_type: str, amount: int) -> 'FakeWorldView':
        """Add a resource at specific position (fluent interface)"""
        if pos not in self._visible_resources:
            self._visible_resources[pos] = {}
        self._visible_resources[pos][resource_type] = amount
        return self
    
    def with_neighbor(self, agent_id: int) -> 'FakeWorldView':
        """Add a neighboring agent (fluent interface)"""
        if agent_id not in self._neighbor_agents:
            self._neighbor_agents.append(agent_id)
        return self
    
    def with_signal(self, resource_type: str, scarcity: float) -> 'FakeWorldView':
        """Set resource scarcity signal (fluent interface)"""
        self._resource_signals[resource_type] = max(0.0, min(1.0, scarcity))
        return self


class FakeAgentContext:
    """
    Test data builder for agent decision context
    
    Provides fluent interface for building test scenarios
    """
    
    def __init__(self):
        self.agent_id = 1
        self.position = Position(0, 0)
        self.attributes = {"strength": 5, "intelligence": 5, "agility": 5}
        self.inventory = {}
        self.skills = {}
        self.world_view = FakeWorldView()
        self.turn = 1
        self.era = "石器时代"
        
    def with_agent(self, agent_id: int, position: Tuple[int, int] = (0, 0)) -> 'FakeAgentContext':
        """Set agent properties"""
        self.agent_id = agent_id
        self.position = Position(*position)
        return self
        
    def with_attributes(self, **attrs) -> 'FakeAgentContext':
        """Set agent attributes"""
        self.attributes.update(attrs)
        return self
        
    def with_inventory(self, **items) -> 'FakeAgentContext':
        """Set agent inventory"""
        self.inventory.update(items)
        return self
        
    def with_skills(self, **skills) -> 'FakeAgentContext':
        """Set agent skills"""
        for skill_name, level in skills.items():
            self.skills[skill_name] = {"level": level, "experience": 0}
        return self
        
    def with_world_view(self, world_view: FakeWorldView) -> 'FakeAgentContext':
        """Set world view"""
        self.world_view = world_view
        return self
        
    def with_turn(self, turn: int) -> 'FakeAgentContext':
        """Set current turn"""
        self.turn = turn
        return self
        
    def with_era(self, era: str) -> 'FakeAgentContext':
        """Set era context"""
        self.era = era
        return self
        
    def build(self) -> Dict[str, Any]:
        """Build complete test context"""
        return {
            "agent_id": self.agent_id,
            "position": self.position,
            "attributes": self.attributes.copy(),
            "inventory": self.inventory.copy(),
            "skills": self.skills.copy(),
            "world_view": self.world_view,
            "turn": self.turn,
            "era": self.era
        }


# Test data constants for common scenarios
SCENARIOS = {
    "abundant_forest": lambda: FakeWorldView().with_resource((1, 1), "wood", 10).with_resource((2, 2), "wood", 8).with_signal("wood", 0.2),
    "scarce_forest": lambda: FakeWorldView().with_resource((5, 5), "wood", 1).with_signal("wood", 0.9),
    "coastal_village": lambda: FakeWorldView().with_resource((1, 1), "fish", 5).with_resource((2, 1), "fish", 3).with_signal("fish", 0.3),
    "social_gathering": lambda: FakeWorldView().with_neighbor(2).with_neighbor(3).with_neighbor(4),
    "empty_wilderness": lambda: FakeWorldView(),
    "resource_rich": lambda: (FakeWorldView()
                             .with_resource((1, 1), "wood", 5)
                             .with_resource((2, 2), "stone", 3)
                             .with_resource((3, 3), "food", 2)
                             .with_signal("wood", 0.3)
                             .with_signal("stone", 0.4)
                             .with_signal("food", 0.5))
}


def create_test_agent_context(scenario: str = "empty_wilderness", **overrides) -> Dict[str, Any]:
    """
    Convenience function to create test agent contexts
    
    Args:
        scenario: Predefined scenario name from SCENARIOS
        **overrides: Override any context properties
        
    Returns:
        Test agent context dictionary
    """
    builder = FakeAgentContext()
    
    if scenario in SCENARIOS:
        builder.with_world_view(SCENARIOS[scenario]())
    
    # Apply overrides
    for key, value in overrides.items():
        if hasattr(builder, f"with_{key}"):
            getattr(builder, f"with_{key}")(value)
        elif hasattr(builder, key):
            setattr(builder, key, value)
    
    return builder.build()