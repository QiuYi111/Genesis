"""
Enhanced memory system for Project Genesis agents.
Combines personal memory with cultural memory and knowledge transfer.
"""

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from enum import Enum

from loguru import logger


class MemoryType(Enum):
    """Types of memories agents can have"""
    PERSONAL = "personal"
    SOCIAL = "social"
    KNOWLEDGE = "knowledge"
    CULTURAL = "cultural"
    SKILL = "skill"
    EVENT = "event"


@dataclass
class Knowledge:
    """Represents a piece of knowledge or technology"""
    knowledge_id: str
    name: str
    description: str
    category: str  # "technology", "skill", "wisdom", "tradition", "secret"
    discovered_by: str  # Agent ID
    discovery_turn: int
    complexity: int  # 1-10, affects learning difficulty
    prerequisites: List[str] = field(default_factory=list)  # Required knowledge IDs
    spread_rate: float = 0.1  # How easily it spreads (0.0-1.0)
    cultural_value: int = 10  # Importance to society
    practical_value: int = 10  # Usefulness for survival
    
    def can_learn(self, agent_knowledge: Set[str], agent_attributes: Dict[str, float]) -> bool:
        """Check if an agent can learn this knowledge"""
        # Check prerequisites
        for prereq in self.prerequisites:
            if prereq not in agent_knowledge:
                return False
        
        # Check complexity vs agent capabilities
        relevant_skills = ["intelligence", "wisdom", "curiosity"]
        agent_capability = 0
        for skill in relevant_skills:
            agent_capability += agent_attributes.get(skill, 5)
        
        return agent_capability >= self.complexity * 3


@dataclass
class CulturalTradition:
    """Represents a cultural tradition or custom"""
    tradition_id: str
    name: str
    description: str
    origin_group: str  # Group ID
    creation_turn: int
    tradition_type: str  # "ritual", "custom", "law", "story", "celebration"
    strength: float = 1.0  # How strongly the tradition is followed
    participants: Set[str] = field(default_factory=set)  # Agent IDs
    effects: Dict[str, int] = field(default_factory=dict)  # Effects on participants
    
    def practice_tradition(self, agent_id: str):
        """Agent practices this tradition"""
        self.participants.add(agent_id)
        
        # Apply tradition effects
        for effect, value in self.effects.items():
            if effect == "social_bonus":
                # This would be handled by social system
                pass
            elif effect == "group_cohesion":
                pass
            elif effect == "skill_bonus":
                pass


@dataclass
class Memory:
    """Enhanced memory system with semantic capabilities"""
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: int = 0
    memory_type: MemoryType = MemoryType.PERSONAL
    content: Dict[str, Any] = field(default_factory=dict)
    importance: float = 1.0  # 0-1 scale
    emotional_impact: float = 0.0  # 0-1 scale
    tags: List[str] = field(default_factory=list)
    related_agents: List[str] = field(default_factory=list)
    related_locations: List[Tuple[int, int]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'memory_id': self.memory_id,
            'timestamp': self.timestamp,
            'memory_type': self.memory_type.value,
            'content': self.content,
            'importance': self.importance,
            'emotional_impact': self.emotional_impact,
            'tags': self.tags,
            'related_agents': self.related_agents,
            'related_locations': self.related_locations
        }


class EnhancedMemorySystem:
    """Enhanced memory system combining personal and cultural memory"""
    
    def __init__(self):
        self.agent_memories: Dict[str, List[Memory]] = {}  # agent_id -> memories
        self.knowledge_base: Dict[str, Knowledge] = {}  # knowledge_id -> knowledge
        self.traditions: Dict[str, CulturalTradition] = {}  # tradition_id -> tradition
        self.agent_knowledge: Dict[str, Set[str]] = {}  # agent_id -> knowledge_ids
        self.group_knowledge: Dict[str, Set[str]] = {}  # group_id -> knowledge_ids
        self.cultural_memory: Dict[str, Any] = {}  # Shared cultural memory
        
        self.next_knowledge_id = 1
        self.next_tradition_id = 1
        
        # Initialize with basic knowledge
        self._initialize_basic_knowledge()
    
    def _initialize_basic_knowledge(self):
        """Initialize basic survival knowledge"""
        basic_knowledge = [
            Knowledge(
                knowledge_id="fire_making",
                name="Fire Making",
                description="Methods for creating fire through friction",
                category="technology",
                discovered_by="system",
                discovery_turn=0,
                complexity=2,
                prerequisites=[],
                spread_rate=0.3,
                cultural_value=20,
                practical_value=25
            ),
            Knowledge(
                knowledge_id="tool_crafting",
                name="Tool Crafting",
                description="Creating simple stone tools",
                category="technology",
                discovered_by="system",
                discovery_turn=0,
                complexity=3,
                prerequisites=[],
                spread_rate=0.2,
                cultural_value=15,
                practical_value=30
            ),
            Knowledge(
                knowledge_id="food_preservation",
                name="Food Preservation",
                description="Methods for preserving food",
                category="wisdom",
                discovered_by="system",
                discovery_turn=0,
                complexity=4,
                prerequisites=["fire_making"],
                spread_rate=0.15,
                cultural_value=10,
                practical_value=20
            ),
            Knowledge(
                knowledge_id="shelter_building",
                name="Shelter Building",
                description="Constructing basic shelters",
                category="technology",
                discovered_by="system",
                discovery_turn=0,
                complexity=5,
                prerequisites=["tool_crafting"],
                spread_rate=0.1,
                cultural_value=18,
                practical_value=28
            ),
        ]
        
        for knowledge in basic_knowledge:
            self.knowledge_base[knowledge.knowledge_id] = knowledge
    
    def add_agent_memory(self, agent_id: str, memory: Memory):
        """Add memory to specific agent"""
        if agent_id not in self.agent_memories:
            self.agent_memories[agent_id] = []
        
        self.agent_memories[agent_id].append(memory)
        
        # Keep only most important memories (limit to 100 per agent)
        memories = self.agent_memories[agent_id]
        if len(memories) > 100:
            memories.sort(key=lambda m: (m.importance, m.emotional_impact), reverse=True)
            self.agent_memories[agent_id] = memories[:100]
    
    def discover_knowledge(self, agent_id: str, knowledge_name: str, 
                          description: str, category: str, turn: int,
                          complexity: int = 5, **kwargs) -> Knowledge:
        """Agent discovers new knowledge"""
        knowledge_id = f"knowledge_{self.next_knowledge_id}"
        self.next_knowledge_id += 1
        
        knowledge = Knowledge(
            knowledge_id=knowledge_id,
            name=knowledge_name,
            description=description,
            category=category,
            discovered_by=agent_id,
            discovery_turn=turn,
            complexity=complexity,
            prerequisites=kwargs.get('prerequisites', []),
            spread_rate=kwargs.get('spread_rate', 0.1),
            cultural_value=kwargs.get('cultural_value', 10),
            practical_value=kwargs.get('practical_value', 10)
        )
        
        self.knowledge_base[knowledge_id] = knowledge
        
        # Agent automatically learns their own discovery
        if agent_id not in self.agent_knowledge:
            self.agent_knowledge[agent_id] = set()
        self.agent_knowledge[agent_id].add(knowledge_id)
        
        # Create discovery memory
        discovery_memory = Memory(
            timestamp=turn,
            memory_type=MemoryType.KNOWLEDGE,
            content={
                'knowledge_id': knowledge_id,
                'knowledge_name': knowledge_name,
                'category': category,
                'description': description
            },
            importance=0.8,
            emotional_impact=0.7,
            tags=['discovery', 'knowledge', category]
        )
        
        self.add_agent_memory(agent_id, discovery_memory)
        
        logger.info(f"Agent {agent_id} discovered knowledge: {knowledge_name}")
        return knowledge
    
    def attempt_knowledge_transfer(self, teacher_id: str, student_id: str, 
                                 knowledge_id: str, turn: int) -> bool:
        """Attempt to transfer knowledge from teacher to student"""
        if knowledge_id not in self.knowledge_base:
            return False
        
        knowledge = self.knowledge_base[knowledge_id]
        
        # Check if teacher knows this knowledge
        teacher_knowledge = self.agent_knowledge.get(teacher_id, set())
        if knowledge_id not in teacher_knowledge:
            return False
        
        # Check if student already knows this knowledge
        student_knowledge = self.agent_knowledge.get(student_id, set())
        if knowledge_id in student_knowledge:
            return False
        
        # Check if student can learn this knowledge
        # This would need agent attributes passed in
        # For now, use basic probability
        import random
        success_chance = knowledge.spread_rate
        
        if random.random() < success_chance:
            # Successful learning
            if student_id not in self.agent_knowledge:
                self.agent_knowledge[student_id] = set()
            self.agent_knowledge[student_id].add(knowledge_id)
            
            # Create learning memory
            learning_memory = Memory(
                timestamp=turn,
                memory_type=MemoryType.KNOWLEDGE,
                content={
                    'knowledge_id': knowledge_id,
                    'knowledge_name': knowledge.name,
                    'teacher_id': teacher_id,
                    'method': 'direct_teaching'
                },
                importance=0.6,
                emotional_impact=0.4,
                tags=['learning', 'knowledge', 'social'],
                related_agents=[teacher_id]
            )
            
            self.add_agent_memory(student_id, learning_memory)
            
            # Create teaching memory
            teaching_memory = Memory(
                timestamp=turn,
                memory_type=MemoryType.SOCIAL,
                content={
                    'knowledge_id': knowledge_id,
                    'knowledge_name': knowledge.name,
                    'student_id': student_id,
                    'action': 'taught_knowledge'
                },
                importance=0.5,
                emotional_impact=0.3,
                tags=['teaching', 'knowledge', 'social'],
                related_agents=[student_id]
            )
            
            self.add_agent_memory(teacher_id, teaching_memory)
            
            logger.info(f"Knowledge transfer: {teacher_id} -> {student_id} ({knowledge.name})")
            return True
        
        return False
    
    def create_tradition(self, origin_group: str, tradition_name: str, 
                        description: str, tradition_type: str, 
                        turn: int, effects: Dict[str, int] = None) -> CulturalTradition:
        """Create a new cultural tradition"""
        tradition_id = f"tradition_{self.next_tradition_id}"
        self.next_tradition_id += 1
        
        tradition = CulturalTradition(
            tradition_id=tradition_id,
            name=tradition_name,
            description=description,
            origin_group=origin_group,
            creation_turn=turn,
            tradition_type=tradition_type,
            effects=effects or {}
        )
        
        self.traditions[tradition_id] = tradition
        
        # Create tradition memory for group
        tradition_memory = Memory(
            timestamp=turn,
            memory_type=MemoryType.CULTURAL,
            content={
                'tradition_id': tradition_id,
                'tradition_name': tradition_name,
                'tradition_type': tradition_type,
                'description': description,
                'origin_group': origin_group
            },
            importance=0.7,
            emotional_impact=0.6,
            tags=['tradition', 'culture', tradition_type]
        )
        
        # Add to cultural memory
        if origin_group not in self.cultural_memory:
            self.cultural_memory[origin_group] = []
        self.cultural_memory[origin_group].append(tradition_memory)
        
        logger.info(f"New tradition created: {tradition_name} by group {origin_group}")
        return tradition
    
    def spread_knowledge_naturally(self, agent_positions: Dict[str, Tuple[int, int]], turn: int):
        """Natural spread of knowledge through proximity and interaction"""
        for agent_id, position in agent_positions.items():
            agent_knowledge = self.agent_knowledge.get(agent_id, set())
            
            # Knowledge spreads to nearby agents
            for other_agent_id, other_position in agent_positions.items():
                if other_agent_id == agent_id:
                    continue
                
                # Check proximity (within 3 tiles)
                distance = max(abs(position[0] - other_position[0]), 
                             abs(position[1] - other_position[1]))
                if distance > 3:
                    continue
                
                # Check for knowledge that can spread
                other_knowledge = self.agent_knowledge.get(other_agent_id, set())
                
                for knowledge_id in agent_knowledge:
                    if knowledge_id in other_knowledge:
                        continue
                    
                    knowledge = self.knowledge_base[knowledge_id]
                    # Natural spread chance
                    import random
                    if random.random() < knowledge.spread_rate * 0.1:
                        if other_agent_id not in self.agent_knowledge:
                            self.agent_knowledge[other_agent_id] = set()
                        self.agent_knowledge[other_agent_id].add(knowledge_id)
                        
                        logger.debug(f"Natural knowledge spread: {knowledge.name} to {other_agent_id}")
    
    def get_agent_knowledge_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get summary of an agent's knowledge"""
        agent_knowledge = self.agent_knowledge.get(agent_id, set())
        
        summary = {
            "total_knowledge": len(agent_knowledge),
            "knowledge_by_category": {},
            "knowledge_list": []
        }
        
        for knowledge_id in agent_knowledge:
            if knowledge_id in self.knowledge_base:
                knowledge = self.knowledge_base[knowledge_id]
                category = knowledge.category
                summary["knowledge_by_category"][category] = summary["knowledge_by_category"].get(category, 0) + 1
                summary["knowledge_list"].append({
                    "name": knowledge.name,
                    "category": knowledge.category,
                    "description": knowledge.description,
                    "complexity": knowledge.complexity,
                    "discovered_by": knowledge.discovered_by
                })
        
        return summary
    
    def get_cultural_memory_summary(self) -> Dict[str, Any]:
        """Get summary of cultural memory system"""
        return {
            "total_knowledge": len(self.knowledge_base),
            "total_traditions": len(self.traditions),
            "agent_knowledge_count": {agent_id: len(knowledge) 
                                    for agent_id, knowledge in self.agent_knowledge.items()},
            "knowledge_categories": list(set(k.category for k in self.knowledge_base.values())),
            "tradition_types": list(set(t.tradition_type for t in self.traditions.values()))
        }
    
    def suggest_new_knowledge(self, agent_id: str, agent_skills: Dict[str, float], 
                            turn: int) -> List[Dict[str, Any]]:
        """Suggest potential new knowledge discoveries"""
        agent_knowledge = self.agent_knowledge.get(agent_id, set())
        suggestions = []
        
        skill_levels = agent_skills
        
        # Technology discoveries based on skills
        if skill_levels.get('crafting', 0) >= 0.7:
            if 'advanced_tools' not in agent_knowledge:
                suggestions.append({
                    'name': 'Advanced Tool Making',
                    'description': 'Creating more complex and precise tools',
                    'category': 'technology',
                    'complexity': 7,
                    'prerequisites': ['tool_crafting']
                })
        
        if skill_levels.get('gathering', 0) >= 0.8:
            if 'efficient_gathering' not in agent_knowledge:
                suggestions.append({
                    'name': 'Efficient Gathering Techniques',
                    'description': 'Advanced methods for resource collection',
                    'category': 'skill',
                    'complexity': 5,
                    'prerequisites': ['gathering']
                })
        
        # Social discoveries
        if skill_levels.get('communication', 0) >= 0.6:
            if 'social_cooperation' not in agent_knowledge:
                suggestions.append({
                    'name': 'Social Cooperation',
                    'description': 'Methods for organizing group activities',
                    'category': 'wisdom',
                    'complexity': 4,
                    'prerequisites': []
                })
        
        return suggestions


class PersonalMemory:
    """Personal memory management for individual agents"""
    
    def __init__(self, agent_id: str, max_memories: int = 100):
        self.agent_id = agent_id
        self.memories: List[Memory] = []
        self.max_memories = max_memories
        self.memory_weights: Dict[str, float] = {}  # memory_id -> importance weight
    
    def add_memory(self, memory: Memory):
        """Add a memory with automatic importance calculation"""
        memory.memory_id = str(uuid.uuid4())[:8]
        
        # Calculate importance based on various factors
        importance = self._calculate_importance(memory)
        memory.importance = importance
        
        self.memories.append(memory)
        self.memory_weights[memory.memory_id] = importance
        
        # Keep only most important memories
        if len(self.memories) > self.max_memories:
            self._prune_memories()
    
    def _calculate_importance(self, memory: Memory) -> float:
        """Calculate memory importance based on content and context"""
        base_importance = memory.importance
        
        # Boost importance for certain types
        type_multipliers = {
            MemoryType.KNOWLEDGE: 1.5,
            MemoryType.CULTURAL: 1.3,
            MemoryType.SOCIAL: 1.2,
            MemoryType.EVENT: 1.1,
            MemoryType.PERSONAL: 1.0
        }
        
        importance = base_importance * type_multipliers.get(memory.memory_type, 1.0)
        
        # Boost for high emotional impact
        importance += memory.emotional_impact * 0.3
        
        return min(1.0, importance)
    
    def _prune_memories(self):
        """Remove least important memories"""
        self.memories.sort(key=lambda m: (m.importance, m.emotional_impact, m.timestamp), reverse=True)
        removed = self.memories[self.max_memories:]
        self.memories = self.memories[:self.max_memories]
        
        # Clean up weights
        for memory in removed:
            self.memory_weights.pop(memory.memory_id, None)
    
    def get_memories_by_type(self, memory_type: MemoryType, limit: int = 10) -> List[Memory]:
        """Get memories filtered by type"""
        filtered = [m for m in self.memories if m.memory_type == memory_type]
        return sorted(filtered, key=lambda m: m.timestamp, reverse=True)[:limit]
    
    def get_memories_by_tag(self, tag: str, limit: int = 10) -> List[Memory]:
        """Get memories filtered by tag"""
        filtered = [m for m in self.memories if tag in m.tags]
        return sorted(filtered, key=lambda m: m.timestamp, reverse=True)[:limit]
    
    def get_recent_memories(self, limit: int = 10) -> List[Memory]:
        """Get most recent memories"""
        return sorted(self.memories, key=lambda m: m.timestamp, reverse=True)[:limit]
    
    def search_memories(self, query: str, limit: int = 10) -> List[Memory]:
        """Search memories by content"""
        query_lower = query.lower()
        matches = []
        
        for memory in self.memories:
            content_str = str(memory.content).lower()
            if query_lower in content_str:
                matches.append(memory)
        
        # Sort by importance and recency
        matches.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
        return matches[:limit]
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of agent's memory"""
        return {
            "total_memories": len(self.memories),
            "memory_types": {},
            "average_importance": 0.0,
            "recent_memories": len([m for m in self.memories if m.timestamp > 0])  # Adjust as needed
        }


# Global memory system instance
_global_memory_system = None

def get_memory_system() -> EnhancedMemorySystem:
    """Get the global memory system instance"""
    global _global_memory_system
    if _global_memory_system is None:
        _global_memory_system = EnhancedMemorySystem()
    return _global_memory_system