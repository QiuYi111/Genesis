"""Technology progression and innovation system"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from loguru import logger
import random

if TYPE_CHECKING:
    from .agent import Agent
    from .world import World

@dataclass
class Technology:
    """Represents a technology or innovation"""
    tech_id: str
    name: str
    description: str
    era_level: int  # 1=Stone Age, 2=Bronze Age, 3=Iron Age, etc.
    category: str  # "tools", "agriculture", "construction", "warfare", "transportation"
    discoverer_id: int
    discovery_turn: int
    prerequisites: List[str] = field(default_factory=list)  # Required tech IDs
    required_resources: Dict[str, int] = field(default_factory=dict)
    required_skills: Dict[str, int] = field(default_factory=dict)
    unlocks_actions: List[str] = field(default_factory=list)  # New actions this tech enables
    societal_impact: int = 1  # How much this tech advances society (1-10)
    
    def can_discover(self, agent: 'Agent', available_techs: Set[str], 
                    available_resources: Dict[str, int]) -> bool:
        """Check if an agent can discover this technology"""
        # Check prerequisites
        for prereq in self.prerequisites:
            if prereq not in available_techs:
                return False
        
        # Check required skills
        for skill, required_level in self.required_skills.items():
            if not agent.has_skill(skill, required_level):
                return False
        
        # Check available resources (for prototype creation)
        for resource, required_amount in self.required_resources.items():
            if available_resources.get(resource, 0) < required_amount:
                return False
        
        return True


@dataclass
class TechnologicalEra:
    """Represents a technological era"""
    era_id: int
    name: str
    description: str
    required_techs: List[str]  # Technologies needed to advance to this era
    new_materials: List[str] = field(default_factory=list)
    new_concepts: List[str] = field(default_factory=list)
    societal_changes: List[str] = field(default_factory=list)


class TechnologySystem:
    """Manages technological progression and innovation"""
    
    def __init__(self):
        self.technologies: Dict[str, Technology] = {}
        self.discovered_techs: Set[str] = set()
        self.agent_technologies: Dict[int, Set[str]] = {}  # agent_id -> tech_ids
        self.current_era: int = 1  # Start in Stone Age
        self.eras: Dict[int, TechnologicalEra] = {}
        self.innovation_points: int = 0  # Accumulates from discoveries
        
        self._initialize_tech_tree()
        self._initialize_eras()
    
    def _initialize_tech_tree(self):
        """Initialize the technology tree"""
        # Stone Age Technologies (Era 1)
        stone_age_techs = [
            Technology("stone_knapping", "石器打制", "制作尖锐的石制工具", 1, "tools", 
                      0, 0, [], {"stone": 2}, {"crafting": 2}, 
                      ["craft_sharp_tools", "process_materials"], 2),
            
            Technology("fire_control", "火的控制", "可靠地生火和控制火焰", 1, "tools", 
                      0, 0, [], {"wood": 3}, {"survival": 3}, 
                      ["cook_food", "night_activities", "metalworking_prep"], 3),
            
            Technology("cordage", "绳索制作", "制作绳索和编织", 1, "tools", 
                      0, 0, [], {"plant_fiber": 5}, {"crafting": 3}, 
                      ["bind_objects", "create_nets", "advanced_construction"], 2),
            
            Technology("primitive_shelter", "原始住所", "建造基本的住所结构", 1, "construction", 
                      0, 0, ["fire_control"], {"wood": 10, "stone": 5}, {"crafting": 3, "survival": 2}, 
                      ["build_permanent_shelter", "establish_settlements"], 3),
            
            # Advanced Stone Age
            Technology("advanced_toolmaking", "高级工具制作", "制作复合工具和专用工具", 1, "tools", 
                      0, 0, ["stone_knapping", "cordage"], {"stone": 5, "wood": 3}, {"crafting": 5}, 
                      ["create_specialized_tools", "efficient_hunting"], 4),
            
            Technology("agriculture", "农业", "植物栽培和驯化", 1, "agriculture", 
                      0, 0, ["advanced_toolmaking"], {"seeds": 10, "wood": 5}, {"survival": 4, "exploration": 3}, 
                      ["plant_crops", "food_surplus", "permanent_settlements"], 6),
        ]
        
        # Bronze Age Technologies (Era 2)
        bronze_age_techs = [
            Technology("metallurgy", "金属学", "金属的提取和加工", 2, "tools", 
                      0, 0, ["fire_control", "advanced_toolmaking"], {"copper": 5, "tin": 2}, {"crafting": 6}, 
                      ["create_metal_tools", "advanced_weapons"], 5),
            
            Technology("wheel", "轮子", "轮子和轴的发明", 2, "transportation", 
                      0, 0, ["advanced_toolmaking"], {"wood": 8, "stone": 3}, {"crafting": 5, "innovation": 3}, 
                      ["build_carts", "pottery_wheel", "advanced_transportation"], 7),
            
            Technology("writing", "文字", "符号记录系统", 2, "knowledge", 
                      0, 0, ["agriculture"], {}, {"social": 5, "innovation": 4}, 
                      ["record_knowledge", "complex_administration", "long_distance_communication"], 8),
        ]
        
        # Add all technologies to the system
        for tech in stone_age_techs + bronze_age_techs:
            self.technologies[tech.tech_id] = tech
    
    def _initialize_eras(self):
        """Initialize technological eras"""
        self.eras = {
            1: TechnologicalEra(
                1, "石器时代", "使用石制工具的早期人类文明",
                [], ["stone", "wood", "bone"], 
                ["toolmaking", "fire_use", "hunting"], 
                ["nomadic_lifestyle", "small_groups"]
            ),
            2: TechnologicalEra(
                2, "青铜时代", "金属工具和早期文明的兴起",
                ["metallurgy", "agriculture", "wheel"],
                ["bronze", "copper", "tin"],
                ["metalworking", "farming", "transportation"],
                ["permanent_settlements", "social_stratification", "trade_networks"]
            ),
            3: TechnologicalEra(
                3, "铁器时代", "铁制工具和复杂社会的发展",
                ["iron_working", "writing", "advanced_agriculture"],
                ["iron", "steel"],
                ["mass_production", "written_records", "complex_governance"],
                ["city_states", "standing_armies", "formal_education"]
            )
        }
    
    def attempt_discovery(self, agent: 'Agent', world: 'World', turn: int) -> Optional[Technology]:
        """Attempt to discover a new technology"""
        available_resources = self._calculate_available_resources(agent, world)
        agent_techs = self.agent_technologies.get(agent.aid, set())
        
        # Find discoverable technologies
        candidates = []
        for tech_id, tech in self.technologies.items():
            if (tech_id not in self.discovered_techs and 
                tech_id not in agent_techs and
                tech.can_discover(agent, self.discovered_techs, available_resources)):
                candidates.append(tech)
        
        if not candidates:
            return None
        
        # Sort by era level and societal impact
        candidates.sort(key=lambda t: (t.era_level, -t.societal_impact))
        
        # Higher chance for lower-era technologies
        for tech in candidates:
            discovery_chance = self._calculate_discovery_chance(agent, tech)
            
            if random.random() < discovery_chance:
                return self._discover_technology(agent, tech, turn)
        
        return None
    
    def _calculate_discovery_chance(self, agent: 'Agent', tech: Technology) -> float:
        """Calculate the chance of discovering a technology"""
        base_chance = 0.05  # 5% base chance
        
        # Agent's relevant skills
        skill_bonus = 0
        for skill, required_level in tech.required_skills.items():
            agent_level = agent.get_skill_level(skill) if hasattr(agent, 'get_skill_level') else 0
            if agent_level >= required_level:
                skill_bonus += (agent_level - required_level + 1) * 0.02
        
        # Innovation bonus for high curiosity/intelligence
        innovation_bonus = (agent.attributes.get("curiosity", 5) - 5) * 0.01
        
        # Era appropriateness (easier to discover current era techs)
        era_bonus = 0
        if tech.era_level == self.current_era:
            era_bonus = 0.03
        elif tech.era_level == self.current_era + 1:
            era_bonus = 0.01
        
        # Societal pressure (more people = more innovation pressure)
        # This would need world context
        
        total_chance = base_chance + skill_bonus + innovation_bonus + era_bonus
        return min(0.3, max(0.01, total_chance))  # Clamp between 1% and 30%
    
    def _discover_technology(self, agent: 'Agent', tech: Technology, turn: int) -> Technology:
        """Agent discovers a technology"""
        # Update discovery info
        tech.discoverer_id = agent.aid
        tech.discovery_turn = turn
        
        # Add to discovered technologies
        self.discovered_techs.add(tech.tech_id)
        
        # Add to agent's technologies
        if agent.aid not in self.agent_technologies:
            self.agent_technologies[agent.aid] = set()
        self.agent_technologies[agent.aid].add(tech.tech_id)
        
        # Consume required resources
        for resource, amount in tech.required_resources.items():
            agent.inventory[resource] = max(0, agent.inventory.get(resource, 0) - amount)
        
        # Increase innovation points
        self.innovation_points += tech.societal_impact
        
        # Update agent reputation and skills
        agent.reputation["skilled"] = agent.reputation.get("skilled", 0) + tech.societal_impact * 5
        agent.reputation["wise"] = agent.reputation.get("wise", 0) + tech.societal_impact * 3
        
        # Check for era advancement
        self._check_era_advancement()
        
        agent.log.append(f"发明了新技术: {tech.name}!")
        logger.success(f"Technology discovered: {tech.name} by Agent {agent.aid}")
        
        return tech
    
    def _calculate_available_resources(self, agent: 'Agent', world: 'World') -> Dict[str, int]:
        """Calculate resources available to an agent (personal + group)"""
        available = agent.inventory.copy()
        
        # Add group resources if agent is in a group
        if hasattr(agent, 'group_id') and agent.group_id is not None:
            group = world.social_manager.groups.get(agent.group_id)
            if group:
                for resource, amount in group.shared_resources.items():
                    available[resource] = available.get(resource, 0) + amount
        
        return available
    
    def _check_era_advancement(self):
        """Check if society has advanced to a new era"""
        next_era_id = self.current_era + 1
        if next_era_id not in self.eras:
            return
        
        next_era = self.eras[next_era_id]
        
        # Check if all required technologies are discovered
        required_discovered = all(tech_id in self.discovered_techs 
                                for tech_id in next_era.required_techs)
        
        # Check innovation threshold
        innovation_threshold = next_era_id * 50  # Higher eras need more innovation
        
        if required_discovered and self.innovation_points >= innovation_threshold:
            self.current_era = next_era_id
            logger.success(f"Society advanced to {next_era.name}!")
            return True
        
        return False
    
    def spread_technology(self, world: 'World'):
        """Spread technology between agents through interaction"""
        for agent in world.agents:
            agent_techs = self.agent_technologies.get(agent.aid, set())
            
            # Technology spreads to group members
            if hasattr(agent, 'group_id') and agent.group_id is not None:
                group = world.social_manager.groups.get(agent.group_id)
                if group:
                    for member_id in group.members:
                        if member_id == agent.aid:
                            continue
                        
                        member = next((a for a in world.agents if a.aid == member_id), None)
                        if member:
                            self._attempt_tech_transfer(agent, member, 0.2)  # 20% chance per tech
            
            # Technology spreads to social connections
            for connection_id, connection_data in agent.social_connections.items():
                if connection_data["strength"] >= 5:  # Strong connections only
                    other_agent = next((a for a in world.agents if a.aid == connection_id), None)
                    if other_agent:
                        self._attempt_tech_transfer(agent, other_agent, 0.1)  # 10% chance per tech
    
    def _attempt_tech_transfer(self, source: 'Agent', target: 'Agent', base_chance: float):
        """Attempt to transfer technology between agents"""
        source_techs = self.agent_technologies.get(source.aid, set())
        target_techs = self.agent_technologies.get(target.aid, set())
        
        for tech_id in source_techs:
            if tech_id in target_techs:
                continue  # Target already has this tech
            
            tech = self.technologies[tech_id]
            
            # Check if target can learn this technology
            if not tech.can_discover(target, target_techs, {}):  # Simplified check
                continue
            
            # Calculate transfer chance
            transfer_chance = base_chance
            
            # Social skill of source affects teaching
            if hasattr(source, 'get_skill_level'):
                social_skill = source.get_skill_level("social")
                transfer_chance += social_skill * 0.02
            
            # Learning ability of target
            curiosity = target.attributes.get("curiosity", 5)
            transfer_chance += (curiosity - 5) * 0.01
            
            if random.random() < transfer_chance:
                if target.aid not in self.agent_technologies:
                    self.agent_technologies[target.aid] = set()
                self.agent_technologies[target.aid].add(tech_id)
                
                source.log.append(f"向{target.name}传授了{tech.name}")
                target.log.append(f"从{source.name}学会了{tech.name}")
                
                logger.info(f"Technology transfer: {tech.name} from {source.aid} to {target.aid}")
                break  # Only one tech per interaction
    
    def get_era_progress(self) -> Dict:
        """Get current era advancement progress"""
        current_era_info = self.eras[self.current_era]
        next_era_id = self.current_era + 1
        
        progress = {
            "current_era": current_era_info.name,
            "discovered_techs": len(self.discovered_techs),
            "innovation_points": self.innovation_points,
            "can_advance": False,
            "next_era_requirements": {}
        }
        
        if next_era_id in self.eras:
            next_era = self.eras[next_era_id]
            required_techs = next_era.required_techs
            discovered_required = [tech_id for tech_id in required_techs 
                                 if tech_id in self.discovered_techs]
            
            innovation_threshold = next_era_id * 50
            
            progress["next_era_requirements"] = {
                "era_name": next_era.name,
                "required_techs": len(required_techs),
                "discovered_required_techs": len(discovered_required),
                "innovation_threshold": innovation_threshold,
                "current_innovation": self.innovation_points,
                "missing_techs": [tech_id for tech_id in required_techs 
                                if tech_id not in self.discovered_techs]
            }
            
            progress["can_advance"] = (len(discovered_required) == len(required_techs) and 
                                     self.innovation_points >= innovation_threshold)
        
        return progress
    
    def suggest_research_directions(self, agent: 'Agent') -> List[Technology]:
        """Suggest technologies the agent could work towards"""
        agent_techs = self.agent_technologies.get(agent.aid, set())
        suggestions = []
        
        for tech_id, tech in self.technologies.items():
            if tech_id in self.discovered_techs or tech_id in agent_techs:
                continue
            
            # Check if agent is close to being able to discover this
            missing_prereqs = [p for p in tech.prerequisites if p not in self.discovered_techs]
            missing_skills = []
            
            for skill, required_level in tech.required_skills.items():
                current_level = agent.get_skill_level(skill) if hasattr(agent, 'get_skill_level') else 0
                if current_level < required_level:
                    missing_skills.append((skill, required_level - current_level))
            
            # Suggest if close to requirements
            if len(missing_prereqs) <= 1 and len(missing_skills) <= 2:
                suggestions.append(tech)
        
        return sorted(suggestions, key=lambda t: (t.era_level, t.societal_impact))[:5]