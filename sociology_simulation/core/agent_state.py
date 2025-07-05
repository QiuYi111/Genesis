"""Enhanced agent state management with validation and persistence"""
import json
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
from loguru import logger

from ..config import get_config


class AgentStatus(Enum):
    """Agent lifecycle status"""
    ALIVE = "alive"
    DEAD = "dead"
    SICK = "sick"
    SLEEPING = "sleeping"
    BUSY = "busy"


class SkillType(Enum):
    """Types of skills agents can develop"""
    HUNTING = "hunting"
    CRAFTING = "crafting"
    TRADING = "trading"
    LEADERSHIP = "leadership"
    MEDICINE = "medicine"
    BUILDING = "building"
    FARMING = "farming"
    COMBAT = "combat"


@dataclass
class Skill:
    """Individual skill with experience and level"""
    type: SkillType
    level: int = 1
    experience: float = 0.0
    last_used: float = field(default_factory=time.time)
    
    def add_experience(self, amount: float):
        """Add experience and handle level ups"""
        self.experience += amount
        self.last_used = time.time()
        
        # Level up every 100 experience points
        new_level = int(self.experience // 100) + 1
        if new_level > self.level:
            self.level = new_level
            logger.info(f"Skill {self.type.value} leveled up to {self.level}")


@dataclass
class Relationship:
    """Relationship between two agents"""
    target_id: str
    relationship_type: str  # "friend", "enemy", "family", "ally", etc.
    strength: float  # -100 to +100
    trust: float     # 0 to 100
    last_interaction: float = field(default_factory=time.time)
    interaction_count: int = 0
    
    def update_relationship(self, delta_strength: float, delta_trust: float = 0.0):
        """Update relationship values"""
        self.strength = max(-100, min(100, self.strength + delta_strength))
        self.trust = max(0, min(100, self.trust + delta_trust))
        self.last_interaction = time.time()
        self.interaction_count += 1


@dataclass
class MemoryEntry:
    """Individual memory entry with metadata"""
    content: str
    category: str  # "agent", "location", "event", "resource", etc.
    importance: float  # 0-1, affects retention
    timestamp: float = field(default_factory=time.time)
    related_entities: Set[str] = field(default_factory=set)
    
    def decay_importance(self, decay_rate: float = 0.001):
        """Gradually reduce importance over time"""
        time_passed = time.time() - self.timestamp
        self.importance *= (1 - decay_rate * time_passed)


@dataclass
class InventoryItem:
    """Enhanced inventory item with metadata"""
    name: str
    quantity: int
    quality: float = 1.0  # 0-1, affects durability/value
    durability: float = 1.0  # 0-1, for tools/equipment
    acquired_from: Optional[str] = None  # Source tracking
    last_used: float = field(default_factory=time.time)
    
    def use_item(self, wear_amount: float = 0.01) -> bool:
        """Use item and apply wear. Returns False if item breaks"""
        self.last_used = time.time()
        self.durability = max(0, self.durability - wear_amount)
        return self.durability > 0


@dataclass
class AgentGoals:
    """Agent's goals and motivations"""
    primary_goal: str = ""
    secondary_goals: List[str] = field(default_factory=list)
    current_action_plan: List[str] = field(default_factory=list)
    goal_progress: Dict[str, float] = field(default_factory=dict)
    
    def update_progress(self, goal: str, progress: float):
        """Update progress towards a goal"""
        self.goal_progress[goal] = max(0, min(1, progress))


class AgentState:
    """Enhanced agent state with validation and persistence"""
    
    def __init__(self, 
                 agent_id: str,
                 position: Tuple[int, int],
                 name: str = "",
                 age: int = 18):
        
        self.agent_id = agent_id
        self.uuid = str(uuid.uuid4())  # Unique identifier
        self.name = name or f"Agent_{agent_id}"
        self.age = age
        self.position = position
        self.status = AgentStatus.ALIVE
        
        # Core attributes with bounds
        self.attributes = {
            "strength": 5,
            "intelligence": 5,
            "charisma": 5,
            "dexterity": 5,
            "constitution": 5,
            "wisdom": 5
        }
        
        # Physical state
        self.health = 100.0
        self.max_health = 100.0
        self.hunger = 0.0
        self.thirst = 0.0
        self.fatigue = 0.0
        self.morale = 50.0
        
        # Advanced inventory system
        self.inventory: Dict[str, InventoryItem] = {}
        self.max_carry_weight = 50.0
        self.current_weight = 0.0
        
        # Skills and experience
        self.skills: Dict[SkillType, Skill] = {}
        self.total_experience = 0.0
        
        # Social connections
        self.relationships: Dict[str, Relationship] = {}
        self.family_members: Set[str] = set()
        self.group_memberships: Set[str] = set()
        
        # Enhanced memory system
        self.memories: List[MemoryEntry] = []
        self.max_memories = 500
        self.memory_categories = {
            "agents": [],
            "locations": [],
            "events": [],
            "resources": [],
            "secrets": []
        }
        
        # Goals and planning
        self.goals = AgentGoals()
        
        # State tracking
        self.birth_time = time.time()
        self.last_update = time.time()
        self.state_version = 1
        
        # Action history
        self.action_history: List[Dict[str, Any]] = []
        self.action_history_limit = 100
    
    def validate_state(self) -> List[str]:
        """Validate agent state and return list of issues"""
        issues = []
        
        # Validate position
        config = get_config()
        if not (0 <= self.position[0] < config.world.size and 
                0 <= self.position[1] < config.world.size):
            issues.append(f"Invalid position: {self.position}")
        
        # Validate attributes
        for attr, value in self.attributes.items():
            if not (1 <= value <= 20):
                issues.append(f"Invalid {attr}: {value} (should be 1-20)")
        
        # Validate physical state
        if not (0 <= self.health <= self.max_health):
            issues.append(f"Invalid health: {self.health}")
        
        if not (0 <= self.hunger <= 100):
            issues.append(f"Invalid hunger: {self.hunger}")
        
        # Validate inventory
        calculated_weight = sum(item.quantity for item in self.inventory.values())
        if abs(calculated_weight - self.current_weight) > 0.1:
            issues.append("Inventory weight mismatch")
        
        return issues
    
    def add_memory(self, content: str, category: str, importance: float = 0.5, 
                   related_entities: Optional[Set[str]] = None):
        """Add a memory with automatic cleanup"""
        if related_entities is None:
            related_entities = set()
        
        memory = MemoryEntry(
            content=content,
            category=category,
            importance=importance,
            related_entities=related_entities
        )
        
        self.memories.append(memory)
        
        # Add to category-specific storage
        if category in self.memory_categories:
            self.memory_categories[category].append(memory)
        
        # Cleanup old memories if at limit
        if len(self.memories) > self.max_memories:
            self._cleanup_memories()
    
    def _cleanup_memories(self):
        """Remove least important memories"""
        # Decay importance of all memories
        for memory in self.memories:
            memory.decay_importance()
        
        # Remove memories below importance threshold
        self.memories = [m for m in self.memories if m.importance > 0.1]
        
        # If still too many, remove oldest low-importance memories
        if len(self.memories) > self.max_memories:
            self.memories.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
            self.memories = self.memories[:self.max_memories]
        
        # Rebuild category storage
        for category in self.memory_categories:
            self.memory_categories[category] = [
                m for m in self.memories if m.category == category
            ]
    
    def get_skill_level(self, skill_type: SkillType) -> int:
        """Get current level for a skill"""
        return self.skills.get(skill_type, Skill(skill_type)).level
    
    def add_skill_experience(self, skill_type: SkillType, amount: float):
        """Add experience to a skill"""
        if skill_type not in self.skills:
            self.skills[skill_type] = Skill(skill_type)
        
        self.skills[skill_type].add_experience(amount)
        self.total_experience += amount
    
    def update_relationship(self, target_id: str, relationship_type: str,
                          strength_delta: float, trust_delta: float = 0.0):
        """Update relationship with another agent"""
        if target_id not in self.relationships:
            self.relationships[target_id] = Relationship(
                target_id=target_id,
                relationship_type=relationship_type,
                strength=0.0,
                trust=50.0
            )
        
        self.relationships[target_id].update_relationship(strength_delta, trust_delta)
    
    def add_inventory_item(self, item_name: str, quantity: int = 1, 
                          quality: float = 1.0, source: Optional[str] = None) -> bool:
        """Add item to inventory with weight checking"""
        # Estimate weight (1 unit per item for simplicity)
        item_weight = quantity
        
        if self.current_weight + item_weight > self.max_carry_weight:
            return False  # Cannot carry more
        
        if item_name in self.inventory:
            self.inventory[item_name].quantity += quantity
        else:
            self.inventory[item_name] = InventoryItem(
                name=item_name,
                quantity=quantity,
                quality=quality,
                acquired_from=source
            )
        
        self.current_weight += item_weight
        return True
    
    def remove_inventory_item(self, item_name: str, quantity: int = 1) -> bool:
        """Remove item from inventory"""
        if item_name not in self.inventory:
            return False
        
        item = self.inventory[item_name]
        if item.quantity < quantity:
            return False
        
        item.quantity -= quantity
        self.current_weight -= quantity
        
        if item.quantity <= 0:
            del self.inventory[item_name]
        
        return True
    
    def use_inventory_item(self, item_name: str) -> bool:
        """Use an item from inventory"""
        if item_name not in self.inventory:
            return False
        
        item = self.inventory[item_name]
        still_usable = item.use_item()
        
        if not still_usable:
            # Item broke, remove from inventory
            self.current_weight -= item.quantity
            del self.inventory[item_name]
            self.add_memory(f"My {item_name} broke from use", "event", 0.3)
        
        return True
    
    def age_one_turn(self):
        """Age the agent by one turn and apply effects"""
        self.age += 1
        self.last_update = time.time()
        
        # Natural aging effects
        if self.age > 50:
            # Gradual decline in physical attributes
            decline_rate = (self.age - 50) * 0.001
            self.attributes["strength"] = max(1, self.attributes["strength"] - decline_rate)
            self.attributes["dexterity"] = max(1, self.attributes["dexterity"] - decline_rate)
            self.attributes["constitution"] = max(1, self.attributes["constitution"] - decline_rate)
            
            # But wisdom might increase
            self.attributes["wisdom"] = min(20, self.attributes["wisdom"] + decline_rate * 0.5)
        
        # Check for natural death
        death_chance = max(0, (self.age - 70) * 0.01)
        if death_chance > 0:
            import random
            if random.random() < death_chance:
                self.status = AgentStatus.DEAD
                self.add_memory("I died of old age", "event", 1.0)
    
    def record_action(self, action: str, outcome: Dict[str, Any]):
        """Record an action in history"""
        action_record = {
            "timestamp": time.time(),
            "action": action,
            "outcome": outcome,
            "age": self.age,
            "position": self.position
        }
        
        self.action_history.append(action_record)
        
        # Maintain history limit
        if len(self.action_history) > self.action_history_limit:
            self.action_history = self.action_history[-self.action_history_limit:]
    
    def get_memory_summary(self, category: Optional[str] = None, limit: int = 10) -> List[str]:
        """Get summary of recent important memories"""
        if category:
            relevant_memories = self.memory_categories.get(category, [])
        else:
            relevant_memories = self.memories
        
        # Sort by importance and recency
        sorted_memories = sorted(
            relevant_memories,
            key=lambda m: (m.importance, m.timestamp),
            reverse=True
        )
        
        return [m.content for m in sorted_memories[:limit]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent state to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "uuid": self.uuid,
            "name": self.name,
            "age": self.age,
            "position": self.position,
            "status": self.status.value,
            "attributes": self.attributes,
            "health": self.health,
            "max_health": self.max_health,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "fatigue": self.fatigue,
            "morale": self.morale,
            "inventory": {name: asdict(item) for name, item in self.inventory.items()},
            "skills": {skill_type.value: asdict(skill) for skill_type, skill in self.skills.items()},
            "relationships": {id: asdict(rel) for id, rel in self.relationships.items()},
            "memories": [asdict(m) for m in self.memories[-50:]],  # Last 50 memories
            "goals": asdict(self.goals),
            "birth_time": self.birth_time,
            "last_update": self.last_update,
            "state_version": self.state_version,
            "total_experience": self.total_experience
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create agent state from dictionary"""
        agent = cls(
            agent_id=data["agent_id"],
            position=tuple(data["position"]),
            name=data["name"],
            age=data["age"]
        )
        
        # Restore all attributes
        agent.uuid = data.get("uuid", str(uuid.uuid4()))
        agent.status = AgentStatus(data.get("status", "alive"))
        agent.attributes = data.get("attributes", agent.attributes)
        agent.health = data.get("health", 100.0)
        agent.max_health = data.get("max_health", 100.0)
        agent.hunger = data.get("hunger", 0.0)
        agent.thirst = data.get("thirst", 0.0)
        agent.fatigue = data.get("fatigue", 0.0)
        agent.morale = data.get("morale", 50.0)
        
        # Restore inventory
        for name, item_data in data.get("inventory", {}).items():
            agent.inventory[name] = InventoryItem(**item_data)
        
        # Restore skills
        for skill_name, skill_data in data.get("skills", {}).items():
            skill_type = SkillType(skill_name)
            agent.skills[skill_type] = Skill(**skill_data)
        
        # Restore relationships
        for rel_id, rel_data in data.get("relationships", {}).items():
            agent.relationships[rel_id] = Relationship(**rel_data)
        
        # Restore memories
        for mem_data in data.get("memories", []):
            memory = MemoryEntry(**mem_data)
            agent.memories.append(memory)
        
        agent.goals = AgentGoals(**data.get("goals", {}))
        agent.birth_time = data.get("birth_time", time.time())
        agent.last_update = data.get("last_update", time.time())
        agent.state_version = data.get("state_version", 1)
        agent.total_experience = data.get("total_experience", 0.0)
        
        return agent


class AgentStateManager:
    """Manages agent states with persistence and validation"""
    
    def __init__(self):
        self.agents: Dict[str, AgentState] = {}
        self.state_history: Dict[str, List[Dict[str, Any]]] = {}
        self.validation_enabled = True
    
    def add_agent(self, agent: AgentState) -> bool:
        """Add agent with validation"""
        if self.validation_enabled:
            issues = agent.validate_state()
            if issues:
                logger.error(f"Agent {agent.agent_id} validation failed: {issues}")
                return False
        
        self.agents[agent.agent_id] = agent
        logger.info(f"Added agent {agent.name} ({agent.agent_id})")
        return True
    
    def remove_agent(self, agent_id: str) -> bool:
        """Remove agent and archive state"""
        if agent_id not in self.agents:
            return False
        
        agent = self.agents[agent_id]
        
        # Archive final state
        if agent_id not in self.state_history:
            self.state_history[agent_id] = []
        self.state_history[agent_id].append(agent.to_dict())
        
        del self.agents[agent_id]
        logger.info(f"Removed agent {agent.name} ({agent_id})")
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_agents_in_area(self, center: Tuple[int, int], radius: int) -> List[AgentState]:
        """Get all agents within radius of center point"""
        cx, cy = center
        nearby_agents = []
        
        for agent in self.agents.values():
            ax, ay = agent.position
            distance = max(abs(ax - cx), abs(ay - cy))  # Chebyshev distance
            if distance <= radius:
                nearby_agents.append(agent)
        
        return nearby_agents
    
    def update_all_agents(self):
        """Update all agents (aging, cleanup, etc.)"""
        for agent in list(self.agents.values()):
            agent.age_one_turn()
            
            # Remove dead agents
            if agent.status == AgentStatus.DEAD:
                self.remove_agent(agent.agent_id)
    
    def get_population_stats(self) -> Dict[str, Any]:
        """Get population statistics"""
        if not self.agents:
            return {"total": 0}
        
        ages = [agent.age for agent in self.agents.values()]
        healths = [agent.health for agent in self.agents.values()]
        
        return {
            "total": len(self.agents),
            "avg_age": sum(ages) / len(ages),
            "avg_health": sum(healths) / len(healths),
            "oldest": max(ages),
            "youngest": min(ages),
            "status_counts": {
                status.value: sum(1 for a in self.agents.values() if a.status == status)
                for status in AgentStatus
            }
        }