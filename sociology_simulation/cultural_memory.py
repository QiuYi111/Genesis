"""Cultural memory and knowledge transfer system"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from loguru import logger
import json

if TYPE_CHECKING:
    from .agent import Agent
    from .world import World
    from .social_structures import Group

@dataclass
class Knowledge:
    """Represents a piece of knowledge or technology"""
    knowledge_id: str
    name: str
    description: str
    category: str  # "technology", "skill", "wisdom", "tradition", "secret"
    discovered_by: int  # Agent ID
    discovery_turn: int
    complexity: int  # 1-10, affects learning difficulty
    prerequisites: List[str] = field(default_factory=list)  # Required knowledge IDs
    spread_rate: float = 0.1  # How easily it spreads (0.0-1.0)
    cultural_value: int = 10  # Importance to society
    practical_value: int = 10  # Usefulness for survival
    
    def can_learn(self, agent: 'Agent', available_knowledge: Set[str]) -> bool:
        """Check if an agent can learn this knowledge"""
        # Check prerequisites
        for prereq in self.prerequisites:
            if prereq not in available_knowledge:
                return False
        
        # Check complexity vs agent capabilities
        relevant_skills = ["curiosity", "wisdom", "intelligence"]
        agent_capability = 0
        for skill in relevant_skills:
            if skill in agent.attributes:
                agent_capability += agent.attributes[skill]
            elif skill in agent.skills:
                agent_capability += agent.skills[skill].get("level", 1) * 2
        
        return agent_capability >= self.complexity * 3


@dataclass
class CulturalTradition:
    """Represents a cultural tradition or custom"""
    tradition_id: str
    name: str
    description: str
    origin_group: int  # Group ID
    creation_turn: int
    tradition_type: str  # "ritual", "custom", "law", "story", "celebration"
    strength: float = 1.0  # How strongly the tradition is followed
    participants: Set[int] = field(default_factory=set)  # Agent IDs
    effects: Dict[str, int] = field(default_factory=dict)  # Effects on participants
    
    def practice_tradition(self, agent: 'Agent'):
        """Agent practices this tradition"""
        self.participants.add(agent.aid)
        
        # Apply tradition effects
        for effect, value in self.effects.items():
            if effect == "social_bonus":
                agent.reputation["wise"] = agent.reputation.get("wise", 0) + value
            elif effect == "group_cohesion":
                # This would be handled at group level
                pass
            elif effect == "skill_bonus":
                # Temporary skill bonus
                pass
        
        agent.log.append(f"参与了传统活动: {self.name}")


class CulturalMemorySystem:
    """Manages knowledge transfer and cultural memory"""
    
    def __init__(self):
        self.knowledge_base: Dict[str, Knowledge] = {}
        self.traditions: Dict[str, CulturalTradition] = {}
        self.agent_knowledge: Dict[int, Set[str]] = {}  # agent_id -> knowledge_ids
        self.group_knowledge: Dict[int, Set[str]] = {}  # group_id -> knowledge_ids
        self.next_knowledge_id = 1
        self.next_tradition_id = 1
        
        # Initialize with basic knowledge
        self._initialize_basic_knowledge()
    
    def _initialize_basic_knowledge(self):
        """Initialize basic survival knowledge"""
        basic_knowledge = [
            Knowledge("fire_making", "生火技术", "使用摩擦生火的方法", "technology", 
                     0, 0, 2, [], 0.3, 20, 25),
            Knowledge("tool_crafting", "工具制作", "制作简单石器工具", "technology", 
                     0, 0, 3, [], 0.2, 15, 30),
            Knowledge("food_preservation", "食物保存", "保存食物的方法", "wisdom", 
                     0, 0, 4, ["fire_making"], 0.15, 10, 20),
            Knowledge("shelter_building", "建造庇护所", "建造基本住所", "technology", 
                     0, 0, 5, ["tool_crafting"], 0.1, 18, 28),
        ]
        
        for knowledge in basic_knowledge:
            self.knowledge_base[knowledge.knowledge_id] = knowledge
    
    def discover_knowledge(self, agent: 'Agent', knowledge_name: str, 
                          description: str, category: str, turn: int,
                          complexity: int = 5) -> Knowledge:
        """Agent discovers new knowledge"""
        knowledge_id = f"knowledge_{self.next_knowledge_id}"
        self.next_knowledge_id += 1
        
        knowledge = Knowledge(
            knowledge_id=knowledge_id,
            name=knowledge_name,
            description=description,
            category=category,
            discovered_by=agent.aid,
            discovery_turn=turn,
            complexity=complexity
        )
        
        self.knowledge_base[knowledge_id] = knowledge
        
        # Agent automatically learns their own discovery
        if agent.aid not in self.agent_knowledge:
            self.agent_knowledge[agent.aid] = set()
        self.agent_knowledge[agent.aid].add(knowledge_id)
        
        # Increase agent's reputation
        agent.reputation["skilled"] = agent.reputation.get("skilled", 0) + 10
        agent.reputation["wise"] = agent.reputation.get("wise", 0) + 5
        
        agent.log.append(f"发现了新知识: {knowledge_name}!")
        logger.success(f"Agent {agent.aid} discovered knowledge: {knowledge_name}")
        
        return knowledge
    
    def attempt_learning(self, student: 'Agent', teacher: 'Agent', 
                        knowledge_id: str) -> bool:
        """Attempt to transfer knowledge from teacher to student"""
        if knowledge_id not in self.knowledge_base:
            return False
        
        knowledge = self.knowledge_base[knowledge_id]
        
        # Check if teacher knows this knowledge
        teacher_knowledge = self.agent_knowledge.get(teacher.aid, set())
        if knowledge_id not in teacher_knowledge:
            return False
        
        # Check if student can learn this knowledge
        student_knowledge = self.agent_knowledge.get(student.aid, set())
        if not knowledge.can_learn(student, student_knowledge):
            return False
        
        # Calculate learning success probability
        success_chance = 0.3  # Base chance
        
        # Teacher's social skill affects teaching ability
        teacher_social = teacher.get_skill_level("social") if hasattr(teacher, 'get_skill_level') else 0
        success_chance += teacher_social * 0.05
        
        # Student's learning ability
        student_curiosity = student.attributes.get("curiosity", 5)
        success_chance += (student_curiosity - 5) * 0.02
        
        # Relationship affects learning
        if teacher.aid in student.social_connections:
            connection_strength = student.social_connections[teacher.aid]["strength"]
            success_chance += connection_strength * 0.02
        
        # Knowledge complexity affects difficulty
        success_chance -= (knowledge.complexity - 3) * 0.05
        
        success_chance = max(0.1, min(0.9, success_chance))  # Clamp between 10%-90%
        
        import random
        if random.random() < success_chance:
            # Successful learning
            if student.aid not in self.agent_knowledge:
                self.agent_knowledge[student.aid] = set()
            self.agent_knowledge[student.aid].add(knowledge_id)
            
            # Both agents gain experience
            student.log.append(f"从{teacher.name}学会了: {knowledge.name}")
            teacher.log.append(f"教授{student.name}: {knowledge.name}")
            
            # Strengthen social connection
            student.add_social_connection(teacher.aid, "teacher", 1)
            teacher.add_social_connection(student.aid, "student", 1)
            
            # Teacher gains reputation for teaching
            teacher.reputation["wise"] = teacher.reputation.get("wise", 0) + 2
            
            logger.info(f"Knowledge transfer: {teacher.name} -> {student.name} ({knowledge.name})")
            return True
        else:
            student.log.append(f"尝试学习{knowledge.name}，但没有成功")
            return False
    
    def create_tradition(self, group: 'Group', tradition_name: str, 
                        description: str, tradition_type: str, 
                        turn: int, effects: Dict[str, int] = None) -> CulturalTradition:
        """Create a new cultural tradition"""
        tradition_id = f"tradition_{self.next_tradition_id}"
        self.next_tradition_id += 1
        
        tradition = CulturalTradition(
            tradition_id=tradition_id,
            name=tradition_name,
            description=description,
            origin_group=group.group_id,
            creation_turn=turn,
            tradition_type=tradition_type,
            effects=effects or {}
        )
        
        self.traditions[tradition_id] = tradition
        group.traditions.append(tradition_id)
        
        logger.success(f"New tradition created: {tradition_name} by group {group.name}")
        return tradition
    
    def spread_knowledge_naturally(self, world: 'World'):
        """Natural spread of knowledge through interactions"""
        for agent in world.agents:
            agent_knowledge = self.agent_knowledge.get(agent.aid, set())
            
            # Knowledge spreads to nearby agents
            for other_agent in world.agents:
                if other_agent.aid == agent.aid:
                    continue
                
                # Check proximity
                distance = max(abs(agent.pos[0] - other_agent.pos[0]), 
                             abs(agent.pos[1] - other_agent.pos[1]))
                if distance > 3:  # Must be nearby
                    continue
                
                # Check for knowledge that can spread
                other_knowledge = self.agent_knowledge.get(other_agent.aid, set())
                
                for knowledge_id in agent_knowledge:
                    if knowledge_id in other_knowledge:
                        continue  # Other agent already knows this
                    
                    knowledge = self.knowledge_base[knowledge_id]
                    if not knowledge.can_learn(other_agent, other_knowledge):
                        continue
                    
                    # Natural spread chance
                    import random
                    if random.random() < knowledge.spread_rate * 0.1:  # Reduced for natural spread
                        if other_agent.aid not in self.agent_knowledge:
                            self.agent_knowledge[other_agent.aid] = set()
                        self.agent_knowledge[other_agent.aid].add(knowledge_id)
                        
                        other_agent.log.append(f"通过观察学会了: {knowledge.name}")
                        logger.info(f"Natural knowledge spread: {knowledge.name} to Agent {other_agent.aid}")
    
    def update_group_knowledge(self, world: 'World'):
        """Update group collective knowledge"""
        for group_id, group in world.social_manager.groups.items():
            if group_id not in self.group_knowledge:
                self.group_knowledge[group_id] = set()
            
            # Aggregate knowledge from all group members
            group_knowledge = set()
            for member_id in group.members:
                member_knowledge = self.agent_knowledge.get(member_id, set())
                group_knowledge.update(member_knowledge)
            
            self.group_knowledge[group_id] = group_knowledge
            
            # Update group's knowledge list for display
            group.group_knowledge = []
            for knowledge_id in group_knowledge:
                if knowledge_id in self.knowledge_base:
                    knowledge = self.knowledge_base[knowledge_id]
                    group.group_knowledge.append(f"{knowledge.name}: {knowledge.description}")
    
    def process_cultural_evolution(self, world: 'World', turn: int):
        """Process cultural evolution and tradition changes"""
        # Natural knowledge spread
        if turn % 3 == 0:  # Every 3 turns
            self.spread_knowledge_naturally(world)
        
        # Update group knowledge
        self.update_group_knowledge(world)
        
        # Practice traditions
        for tradition in self.traditions.values():
            # Traditions may fade over time if not practiced
            if turn - tradition.creation_turn > 20:  # After 20 turns
                if len(tradition.participants) == 0:
                    tradition.strength *= 0.95  # Gradual fade
        
        # Remove very weak traditions
        weak_traditions = [tid for tid, tradition in self.traditions.items() 
                          if tradition.strength < 0.1]
        for tid in weak_traditions:
            del self.traditions[tid]
            logger.info(f"Tradition {self.traditions[tid].name} has been forgotten")
    
    def get_agent_knowledge_summary(self, agent_id: int) -> Dict:
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
                    "description": knowledge.description
                })
        
        return summary
    
    def suggest_knowledge_discoveries(self, agent: 'Agent', turn: int) -> List[Dict]:
        """Suggest potential knowledge discoveries based on agent's skills and situation"""
        suggestions = []
        agent_knowledge = self.agent_knowledge.get(agent.aid, set())
        
        # Check what knowledge agent could potentially discover
        skill_levels = {skill: data.get("level", 1) for skill, data in agent.skills.items()}
        
        # Crafting-based discoveries
        if skill_levels.get("crafting", 0) >= 5:
            if "advanced_tools" not in agent_knowledge:
                suggestions.append({
                    "name": "高级工具制作",
                    "description": "制作更复杂精密的工具",
                    "category": "technology",
                    "trigger": "agent shows advanced crafting behavior"
                })
        
        # Social discoveries
        if skill_levels.get("social", 0) >= 4 and len(agent.social_connections) >= 5:
            if "cooperation_techniques" not in agent_knowledge:
                suggestions.append({
                    "name": "合作技术",
                    "description": "组织团体合作的方法",
                    "category": "wisdom",
                    "trigger": "agent demonstrates leadership in group activities"
                })
        
        return suggestions