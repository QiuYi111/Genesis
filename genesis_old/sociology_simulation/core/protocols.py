"""Core protocols and interfaces for sociology simulation"""
from typing import Protocol, Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

# Type aliases
Position = Tuple[int, int]

@dataclass
class Action:
    """Represents an agent action"""
    type: str  # "move" | "forage" | "craft" | "trade" | ...
    payload: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BehaviorEvent:
    """Event representing agent behavior that can have side effects"""
    agent_id: int
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TurnResult:
    """Result of processing one simulation turn"""
    turn: int
    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

class WorldView(Protocol):
    """Minimal read-only interface for agent perception"""
    
    def get_visible_tiles(self, pos: Position, radius: int) -> List[Dict[str, Any]]:
        """Get visible tiles around a position"""
        ...
    
    def get_visible_agents(self, pos: Position, radius: int) -> List[Dict[str, Any]]:
        """Get visible agents around a position"""
        ...
    
    def get_resource_signals(self) -> Dict[str, float]:
        """Get resource scarcity signals for decision making"""
        ...

class DecisionContext:
    """Context for agent decision making"""
    
    def __init__(self, world_view: WorldView, agent_state: Dict[str, Any], 
                 turn: int, memory: Dict[str, Any], goal: str):
        self.world_view = world_view
        self.agent_state = agent_state
        self.turn = turn
        self.memory = memory
        self.goal = goal
    
    def get_visible_tiles(self, radius: int = 3) -> List[Dict[str, Any]]:
        """Get visible tiles around agent position"""
        pos = self.agent_state.get("pos", (0, 0))
        return self.world_view.get_visible_tiles(pos, radius)
    
    def get_visible_agents(self, radius: int = 3) -> List[Dict[str, Any]]:
        """Get visible agents around agent position"""
        pos = self.agent_state.get("pos", (0, 0))
        return self.world_view.get_visible_agents(pos, radius)
    
    def get_resource_signals(self) -> Dict[str, float]:
        """Get resource signals for decision making"""
        return self.world_view.get_resource_signals()
    
    def get_agent_state(self) -> Dict[str, Any]:
        """Get current agent state"""
        return self.agent_state.copy()
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summarized memory information"""
        return {
            "known_agents": self.memory.get("agents", []),
            "known_locations": self.memory.get("locations", [])
        }