"""Social structures and group formation system"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from loguru import logger
import random

if TYPE_CHECKING:
    from .agent import Agent
    from .world import World

@dataclass
class Group:
    """Represents a social group in the simulation"""
    group_id: int
    name: str
    group_type: str  # "family", "work_team", "tribe", "guild", etc.
    leader_id: Optional[int] = None
    members: Set[int] = field(default_factory=set)
    formation_turn: int = 0
    purpose: str = ""
    shared_resources: Dict[str, int] = field(default_factory=dict)
    group_knowledge: List[str] = field(default_factory=list)
    territory: Optional[Dict] = None  # {"center": [x,y], "radius": int}
    stability: float = 1.0  # Group cohesion (0.0 - 2.0)
    traditions: List[str] = field(default_factory=list)
    
    def add_member(self, agent_id: int):
        """Add a member to the group"""
        self.members.add(agent_id)
        logger.info(f"Agent {agent_id} joined group {self.name} ({self.group_id})")
    
    def remove_member(self, agent_id: int):
        """Remove a member from the group"""
        if agent_id in self.members:
            self.members.remove(agent_id)
            if agent_id == self.leader_id:
                self.elect_new_leader()
            logger.info(f"Agent {agent_id} left group {self.name} ({self.group_id})")
    
    def elect_new_leader(self, candidates: List = None):
        """Elect a new leader from group members"""
        if not self.members:
            self.leader_id = None
            return
        
        if candidates:
            # Choose leader with highest leadership score
            best_candidate = max(candidates, key=lambda agent: agent.leadership_score)
            self.leader_id = best_candidate.aid
        else:
            # Random selection if no candidates provided
            self.leader_id = random.choice(list(self.members))
        
        logger.info(f"Agent {self.leader_id} elected as leader of {self.name}")
    
    def get_influence_radius(self) -> int:
        """Calculate group's influence radius based on size and stability"""
        base_radius = min(10, len(self.members) // 2 + 2)
        return int(base_radius * self.stability)
    
    def share_resource(self, resource: str, amount: int):
        """Add resources to group's shared pool"""
        self.shared_resources[resource] = self.shared_resources.get(resource, 0) + amount
    
    def distribute_resources(self, agents: Dict[int, 'Agent']) -> Dict[int, Dict[str, int]]:
        """Distribute shared resources among members"""
        if not self.shared_resources or not self.members:
            return {}
        
        distribution = {}
        per_member = {}
        
        for resource, total in self.shared_resources.items():
            amount_per_member = total // len(self.members)
            if amount_per_member > 0:
                per_member[resource] = amount_per_member
        
        for member_id in self.members:
            if member_id in agents:
                distribution[member_id] = per_member.copy()
        
        # Clear shared resources after distribution
        self.shared_resources.clear()
        
        return distribution


class SocialStructureManager:
    """Manages all social structures and group dynamics"""
    
    def __init__(self):
        self.groups: Dict[int, Group] = {}
        self.next_group_id = 1
        self.group_formation_cooldown: Dict[int, int] = {}  # agent_id -> turn_count
        
    def create_group(self, founder_id: int, group_type: str, purpose: str, 
                    formation_turn: int, name: str = None) -> Group:
        """Create a new group"""
        if name is None:
            name = f"{group_type.title()} {self.next_group_id}"
        
        group = Group(
            group_id=self.next_group_id,
            name=name,
            group_type=group_type,
            leader_id=founder_id,
            formation_turn=formation_turn,
            purpose=purpose
        )
        group.add_member(founder_id)
        
        self.groups[self.next_group_id] = group
        self.next_group_id += 1
        
        logger.success(f"New group formed: {name} (Type: {group_type}, Leader: {founder_id})")
        return group
    
    def find_suitable_groups(self, agent: 'Agent', group_type: str = None) -> List[Group]:
        """Find groups that an agent could potentially join"""
        suitable_groups = []
        
        for group in self.groups.values():
            # Skip if looking for specific type
            if group_type and group.group_type != group_type:
                continue
            
            # Skip if already a member
            if agent.aid in group.members:
                continue
            
            # Check if group has space (max 10 members for most groups)
            max_size = {"family": 6, "work_team": 8, "tribe": 15, "guild": 12}.get(group.group_type, 10)
            if len(group.members) >= max_size:
                continue
            
            # Check compatibility (reputation, skills, etc.)
            compatibility_score = self.calculate_compatibility(agent, group)
            if compatibility_score > 0.3:  # Minimum compatibility threshold
                suitable_groups.append(group)
        
        return sorted(suitable_groups, key=lambda g: self.calculate_compatibility(agent, g), reverse=True)
    
    def calculate_compatibility(self, agent: 'Agent', group: Group) -> float:
        """Calculate how compatible an agent is with a group (0.0 - 1.0)"""
        score = 0.5  # Base compatibility
        
        # Skill compatibility
        if group.group_type == "work_team":
            # Work teams prefer skill diversity
            group_skills = set()
            # This would need access to other agents' skills
            # For now, assume moderate compatibility
            score += 0.2
        
        # Reputation compatibility
        trustworthy_rep = agent.reputation.get("trustworthy", 0)
        score += min(0.3, trustworthy_rep / 100)  # Max 0.3 bonus for high trust
        
        # Age compatibility for families
        if group.group_type == "family":
            if 18 <= agent.age <= 45:  # Prime family-forming age
                score += 0.3
        
        # Leadership potential
        if agent.leadership_score > 50:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def process_group_actions(self, world: 'World', turn: int):
        """Process group-level actions and maintenance"""
        for group in list(self.groups.values()):
            # Remove empty groups
            if not group.members:
                del self.groups[group.group_id]
                continue
            
            # Update group stability
            self.update_group_stability(group, world)
            
            # Process group resource sharing
            if group.shared_resources:
                agents_dict = {agent.aid: agent for agent in world.agents}
                distributions = group.distribute_resources(agents_dict)
                
                for agent_id, resources in distributions.items():
                    agent = agents_dict.get(agent_id)
                    if agent:
                        for resource, amount in resources.items():
                            agent.inventory[resource] = agent.inventory.get(resource, 0) + amount
                        agent.log.append(f"从{group.name}获得共享资源: {resources}")
            
            # Group decision making
            self.process_group_decisions(group, world, turn)
    
    def update_group_stability(self, group: Group, world: 'World'):
        """Update group stability based on member satisfaction"""
        if not group.members:
            return
        
        agents_dict = {agent.aid: agent for agent in world.agents}
        satisfaction_scores = []
        
        for member_id in list(group.members):
            agent = agents_dict.get(member_id)
            if not agent:
                group.remove_member(member_id)
                continue
            
            # Calculate member satisfaction
            satisfaction = 0.5  # Base satisfaction
            
            # Health and survival satisfaction
            if agent.health > 70:
                satisfaction += 0.2
            if agent.hunger < 50:
                satisfaction += 0.2
            
            # Social connection satisfaction
            social_connections = len([conn for conn in agent.social_connections.values() 
                                    if conn["strength"] > 3])
            satisfaction += min(0.3, social_connections * 0.1)
            
            satisfaction_scores.append(satisfaction)
        
        if satisfaction_scores:
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
            group.stability = group.stability * 0.8 + avg_satisfaction * 0.2
            
            # Disband group if stability too low
            if group.stability < 0.3:
                logger.warning(f"Group {group.name} disbanded due to low stability")
                for member_id in list(group.members):
                    agent = agents_dict.get(member_id)
                    if agent:
                        agent.group_id = None
                        agent.log.append(f"{group.name}解散了")
                del self.groups[group.group_id]
    
    def process_group_decisions(self, group: Group, world: 'World', turn: int):
        """Process collective group decisions"""
        if len(group.members) < 2:
            return
        
        # Territorial expansion for larger groups
        if len(group.members) >= 5 and not group.territory:
            leader_agent = next((a for a in world.agents if a.aid == group.leader_id), None)
            if leader_agent:
                group.territory = {
                    "center": list(leader_agent.pos),
                    "radius": group.get_influence_radius()
                }
                logger.info(f"Group {group.name} established territory around {leader_agent.pos}")
        
        # Collaborative projects (every 5 turns)
        if turn % 5 == 0 and len(group.members) >= 3:
            self.initiate_group_project(group, world)
    
    def initiate_group_project(self, group: Group, world: 'World'):
        """Initiate a collaborative group project"""
        agents_dict = {agent.aid: agent for agent in world.agents}
        group_members = [agents_dict[mid] for mid in group.members if mid in agents_dict]
        
        if not group_members:
            return
        
        # Calculate group capabilities
        total_skills = {}
        total_resources = {}
        
        for agent in group_members:
            for skill, data in agent.skills.items():
                total_skills[skill] = total_skills.get(skill, 0) + data.get("level", 1)
            for resource, amount in agent.inventory.items():
                total_resources[resource] = total_resources.get(resource, 0) + amount
        
        # Determine project type based on capabilities
        projects = []
        
        if total_skills.get("crafting", 0) >= 10 and total_resources.get("wood", 0) >= 10:
            projects.append(("build_workshop", "建造工坊"))
        
        if total_skills.get("exploration", 0) >= 8:
            projects.append(("explore_territory", "探索领土"))
        
        if total_skills.get("survival", 0) >= 12:
            projects.append(("establish_farm", "建立农场"))
        
        if projects:
            project_type, project_name = random.choice(projects)
            group.group_knowledge.append(f"Turn {world.trinity.turn}: 启动了{project_name}项目")
            
            for agent in group_members:
                agent.log.append(f"{group.name}启动了合作项目: {project_name}")
            
            logger.info(f"Group {group.name} initiated project: {project_name}")
    
    def get_group_by_agent(self, agent_id: int) -> Optional[Group]:
        """Get the group an agent belongs to"""
        for group in self.groups.values():
            if agent_id in group.members:
                return group
        return None
    
    def suggest_group_formation(self, agents: List['Agent'], turn: int) -> List[Dict]:
        """Suggest new group formations based on agent relationships"""
        suggestions = []
        
        # Find agents with strong social connections
        for agent in agents:
            if agent.aid in self.group_formation_cooldown:
                continue  # Skip agents in cooldown
            
            if agent.group_id is not None:
                continue  # Skip agents already in groups
            
            # Look for agents with strong social connections
            potential_partners = []
            for other_id, connection in agent.social_connections.items():
                if (connection["strength"] >= 5 and 
                    connection["interactions"] >= 3):
                    other_agent = next((a for a in agents if a.aid == other_id), None)
                    if other_agent and other_agent.group_id is None:
                        potential_partners.append(other_agent)
            
            if len(potential_partners) >= 1:
                # Suggest group formation
                group_type = self.determine_group_type(agent, potential_partners)
                suggestions.append({
                    "founder": agent,
                    "partners": potential_partners,
                    "type": group_type,
                    "purpose": self.generate_group_purpose(group_type, agent, potential_partners)
                })
        
        return suggestions
    
    def determine_group_type(self, founder: 'Agent', partners: List['Agent']) -> str:
        """Determine the most appropriate group type"""
        avg_age = (founder.age + sum(p.age for p in partners)) / (len(partners) + 1)
        
        # Family formation (age 18-45, mixed gender ideally)
        if 18 <= avg_age <= 45 and len(partners) <= 3:
            return "family"
        
        # Work team (skill-based cooperation)
        if any(founder.get_skill_level(skill) >= 3 for skill in founder.skills):
            return "work_team"
        
        # Tribal organization (larger groups, survival focused)
        if len(partners) >= 3:
            return "tribe"
        
        return "social_group"
    
    def generate_group_purpose(self, group_type: str, founder: 'Agent', partners: List['Agent']) -> str:
        """Generate a purpose for the group"""
        purposes = {
            "family": ["共同生活和繁衍", "建立家庭", "照顾彼此"],
            "work_team": ["合作制作工具", "共同建造", "技能分享"],
            "tribe": ["共同生存", "领土防护", "资源共享"],
            "social_group": ["友谊与互助", "信息交流", "社交支持"]
        }
        
        return random.choice(purposes.get(group_type, ["互助合作"]))