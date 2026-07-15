"""
Group systems for Project Genesis v2.

This module provides comprehensive group formation, management, and dynamics
for social groups and organizations within the simulation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import uuid
import random

from ..core.world import World
from .base import Agent
from .social import SocialSystem, RelationshipType


class GroupType(Enum):
    """Types of social groups"""
    FAMILY = "family"           # Small, tight-knit family units
    WORK_TEAM = "work_team"     # Collaborative work groups
    TRIBE = "tribe"            # Larger tribal organizations
    GUILD = "guild"            # Specialized skill-based groups
    SOCIAL_CLUB = "social_club" # Informal social groups
    DEFENSE_ALLIANCE = "defense_alliance" # Mutual defense pacts
    TRADE_CARAVAN = "trade_caravan" # Trading groups
    EXPLORATION_PARTY = "exploration_party" # Exploration-focused groups


class GroupRole(Enum):
    """Roles within groups"""
    LEADER = "leader"
    SECOND_IN_COMMAND = "second_in_command"
    ELDER = "elder"
    SPECIALIST = "specialist"
    WORKER = "worker"
    NEW_MEMBER = "new_member"
    OUTSIDER = "outsider"


@dataclass
class GroupMembership:
    """Represents an agent's membership in a group"""
    agent_id: str
    group_id: str
    role: GroupRole
    join_date: int
    contribution_score: float = 0.0  # 0.0 to 1.0
    loyalty: float = 0.5  # 0.0 to 1.0
    rank: int = 0
    responsibilities: List[str] = field(default_factory=list)
    privileges: List[str] = field(default_factory=list)


@dataclass
class Group:
    """Represents a social group in the simulation"""
    id: str
    name: str
    group_type: GroupType
    formation_date: int
    purpose: str
    description: str
    
    # Membership
    members: Dict[str, GroupMembership] = field(default_factory=dict)
    leader_id: Optional[str] = None
    max_members: int = 10
    
    # Group attributes
    stability: float = 1.0  # 0.0 to 1.0 (group cohesion)
    reputation: float = 0.5  # 0.0 to 1.0 (group's overall reputation)
    resources: Dict[str, float] = field(default_factory=dict)  # Shared resources
    territory: Optional[Tuple[int, int]] = None  # Group's territory center
    territory_radius: int = 0
    
    # Group knowledge and culture
    shared_knowledge: List[str] = field(default_factory=list)
    traditions: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    
    # Group projects and goals
    active_projects: List[Dict[str, Any]] = field(default_factory=list)
    collective_goals: List[str] = field(default_factory=list)
    
    # Internal dynamics
    conflict_level: float = 0.0  # 0.0 to 1.0
    cooperation_level: float = 0.8  # 0.0 to 1.0
    decision_making_style: str = "democratic"  # democratic, hierarchical, consensus
    
    def add_member(self, agent_id: str, role: GroupRole = GroupRole.NEW_MEMBER) -> bool:
        """Add a new member to the group"""
        if len(self.members) >= self.max_members:
            return False
        
        if agent_id in self.members:
            return False
        
        membership = GroupMembership(
            agent_id=agent_id,
            group_id=self.id,
            role=role,
            join_date=self.world_time if hasattr(self, 'world_time') else 0
        )
        
        self.members[agent_id] = membership
        
        # Auto-assign leader if first member
        if len(self.members) == 1:
            membership.role = GroupRole.LEADER
            membership.rank = 1
            self.leader_id = agent_id
        
        return True
    
    def remove_member(self, agent_id: str) -> bool:
        """Remove a member from the group"""
        if agent_id not in self.members:
            return False
        
        # Handle leader departure
        if agent_id == self.leader_id:
            self.leader_id = None
            # Find new leader (highest contribution score)
            if len(self.members) > 1:
                new_leader = max(
                    [m for m in self.members.values() if m.agent_id != agent_id],
                    key=lambda m: m.contribution_score
                )
                new_leader.role = GroupRole.LEADER
                new_leader.rank = 1
                self.leader_id = new_leader.agent_id
        
        del self.members[agent_id]
        
        # Disband if no members left
        if not self.members:
            return True  # Signal that group should be disbanded
        
        return False
    
    def update_member_contribution(self, agent_id: str, contribution: float):
        """Update a member's contribution score"""
        if agent_id in self.members:
            member = self.members[agent_id]
            member.contribution_score = max(0.0, min(1.0, member.contribution_score + contribution))
            
            # Update role based on contribution
            self._update_member_role(member)
    
    def _update_member_role(self, membership: GroupMembership):
        """Update member role based on contribution and loyalty"""
        if membership.contribution_score >= 0.8 and membership.loyalty >= 0.8:
            membership.role = GroupRole.ELDER if membership.role != GroupRole.LEADER else GroupRole.LEADER
        elif membership.contribution_score >= 0.6:
            membership.role = GroupRole.SPECIALIST
        elif membership.contribution_score >= 0.3:
            membership.role = GroupRole.WORKER
        elif membership.contribution_score < 0.2:
            membership.role = GroupRole.NEW_MEMBER
    
    def get_member_count(self) -> int:
        """Get current member count"""
        return len(self.members)
    
    def is_full(self) -> bool:
        """Check if group is at capacity"""
        return len(self.members) >= self.max_members
    
    def has_member(self, agent_id: str) -> bool:
        """Check if agent is a member"""
        return agent_id in self.members
    
    def get_member_role(self, agent_id: str) -> Optional[GroupRole]:
        """Get member's role in the group"""
        if agent_id in self.members:
            return self.members[agent_id].role
        return None
    
    def calculate_group_stability(self) -> float:
        """Calculate group stability based on member satisfaction"""
        if not self.members:
            return 0.0
        
        total_satisfaction = 0.0
        for membership in self.members.values():
            # Satisfaction based on role, contribution, and loyalty
            role_satisfaction = 0.5  # Base satisfaction
            if membership.role == GroupRole.LEADER:
                role_satisfaction = 0.9
            elif membership.role in [GroupRole.ELDER, GroupRole.SPECIALIST]:
                role_satisfaction = 0.8
            elif membership.role == GroupRole.WORKER:
                role_satisfaction = 0.6
            
            contribution_alignment = min(1.0, membership.contribution_score + 0.2)
            loyalty_factor = membership.loyalty
            
            member_satisfaction = (role_satisfaction + contribution_alignment + loyalty_factor) / 3.0
            total_satisfaction += member_satisfaction
        
        avg_satisfaction = total_satisfaction / len(self.members)
        
        # Factor in group resources and conflicts
        resource_factor = min(1.0, sum(self.resources.values()) / 100.0)
        conflict_penalty = self.conflict_level * 0.3
        
        stability = (avg_satisfaction * 0.6 + resource_factor * 0.2 + 
                    self.cooperation_level * 0.2 - conflict_penalty)
        
        return max(0.0, min(1.0, stability))
    
    def add_resource(self, resource_type: str, amount: float):
        """Add resources to group's shared pool"""
        if resource_type in self.resources:
            self.resources[resource_type] += amount
        else:
            self.resources[resource_type] = amount
    
    def consume_resource(self, resource_type: str, amount: float) -> bool:
        """Consume resources from group's shared pool"""
        if resource_type not in self.resources or self.resources[resource_type] < amount:
            return False
        
        self.resources[resource_type] -= amount
        if self.resources[resource_type] <= 0:
            del self.resources[resource_type]
        
        return True
    
    def distribute_resources(self, resource_type: str, amount_per_member: float) -> Dict[str, float]:
        """Distribute resources equally among members"""
        if not self.members or resource_type not in self.resources:
            return {}
        
        total_needed = amount_per_member * len(self.members)
        if self.resources[resource_type] < total_needed:
            return {}  # Not enough resources
        
        distribution = {}
        for agent_id in self.members:
            distribution[agent_id] = amount_per_member
        
        self.resources[resource_type] -= total_needed
        if self.resources[resource_type] <= 0:
            del self.resources[resource_type]
        
        return distribution
    
    def set_territory(self, center: Tuple[int, int], radius: int):
        """Set group's territory"""
        self.territory = center
        self.territory_radius = radius
    
    def is_in_territory(self, position: Tuple[int, int]) -> bool:
        """Check if position is within group's territory"""
        if not self.territory:
            return False
        
        dx = abs(position[0] - self.territory[0])
        dy = abs(position[1] - self.territory[1])
        return dx + dy <= self.territory_radius


class GroupManager:
    """Manages all groups in the simulation"""
    
    def __init__(self, world: World, social_system: SocialSystem):
        self.world = world
        self.social_system = social_system
        self.groups: Dict[str, Group] = {}
        self.group_formations: Dict[str, int] = {}  # agent_id -> last_formation_attempt
        
        # Group type configurations
        self.group_configs = {
            GroupType.FAMILY: {
                'max_members': 6,
                'formation_requirements': {'min_age': 16, 'max_age': 50},
                'preferred_purpose': ['共同生活', '建立家庭', '照顾子女']
            },
            GroupType.WORK_TEAM: {
                'max_members': 8,
                'formation_requirements': {'min_skill_level': 0.3},
                'preferred_purpose': ['合作制作', '技能分享', '共同建造']
            },
            GroupType.TRIBE: {
                'max_members': 15,
                'formation_requirements': {'min_connections': 2},
                'preferred_purpose': ['共同生存', '领土防护', '资源共享']
            },
            GroupType.GUILD: {
                'max_members': 12,
                'formation_requirements': {'min_skill_level': 0.5},
                'preferred_purpose': ['专业技能', '知识传承', '贸易合作']
            },
            GroupType.SOCIAL_CLUB: {
                'max_members': 10,
                'formation_requirements': {'min_charisma': 8},
                'preferred_purpose': ['友谊交流', '信息共享', '社交支持']
            },
            GroupType.DEFENSE_ALLIANCE: {
                'max_members': 20,
                'formation_requirements': {'min_strength': 12},
                'preferred_purpose': ['共同防御', '安全保护', '危机应对']
            }
        }
    
    def create_group(self, group_type: GroupType, founder_id: str, 
                    purpose: str, name: Optional[str] = None) -> Optional[str]:
        """Create a new group"""
        # Check cooldown
        if founder_id in self.group_formations:
            cooldown_period = 50  # turns
            if (self.world.time if hasattr(self.world, 'time') else 0) - self.group_formations[founder_id] < cooldown_period:
                return None
        
        # Check if founder already has a group of this type
        existing_groups = self.get_groups_by_member(founder_id)
        for group in existing_groups:
            if group.group_type == group_type:
                return None
        
        group_id = str(uuid.uuid4())[:8]
        
        if not name:
            name = f"{group_type.value.title()}_{group_id}"
        
        group = Group(
            id=group_id,
            name=name,
            group_type=group_type,
            formation_date=self.world.time if hasattr(self.world, 'time') else 0,
            purpose=purpose,
            description=f"A {group_type.value} formed with the purpose of {purpose}",
            max_members=self.group_configs[group_type]['max_members']
        )
        
        # Add founder as leader
        if group.add_member(founder_id, GroupRole.LEADER):
            self.groups[group_id] = group
            self.group_formations[founder_id] = self.world.time if hasattr(self.world, 'time') else 0
            return group_id
        
        return None
    
    def disband_group(self, group_id: str) -> bool:
        """Disband a group"""
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        
        # Notify all members
        for agent_id in list(group.members.keys()):
            group.remove_member(agent_id)
        
        del self.groups[group_id]
        return True
    
    def add_member_to_group(self, group_id: str, agent_id: str) -> bool:
        """Add a member to an existing group"""
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        return group.add_member(agent_id)
    
    def remove_member_from_group(self, group_id: str, agent_id: str) -> bool:
        """Remove a member from a group"""
        if group_id not in self.groups:
            return False
        
        group = self.groups[group_id]
        should_disband = group.remove_member(agent_id)
        
        if should_disband:
            self.disband_group(group_id)
        
        return True
    
    def get_group(self, group_id: str) -> Optional[Group]:
        """Get group by ID"""
        return self.groups.get(group_id)
    
    def get_groups_by_member(self, agent_id: str) -> List[Group]:
        """Get all groups an agent is a member of"""
        return [group for group in self.groups.values() if group.has_member(agent_id)]
    
    def get_groups_by_type(self, group_type: GroupType) -> List[Group]:
        """Get all groups of a specific type"""
        return [group for group in self.groups.values() if group.group_type == group_type]
    
    def find_suitable_groups(self, agent: Agent, group_type: Optional[GroupType] = None) -> List[Group]:
        """Find groups that would accept this agent"""
        suitable = []
        
        for group in self.groups.values():
            if group_type and group.group_type != group_type:
                continue
            
            if group.has_member(agent.id):
                continue
            
            if group.is_full():
                continue
            
            # Check compatibility
            compatibility = self._calculate_group_compatibility(agent, group)
            if compatibility > 0.3:  # Minimum compatibility threshold
                suitable.append(group)
        
        return sorted(suitable, key=lambda g: self._calculate_group_compatibility(agent, g), reverse=True)
    
    def _calculate_group_compatibility(self, agent: Agent, group: Group) -> float:
        """Calculate how compatible an agent is with a group"""
        score = 0.5  # Base compatibility
        
        # Skill compatibility
        if group.group_type == GroupType.WORK_TEAM or group.group_type == GroupType.GUILD:
            # Work teams prefer skilled agents
            avg_skill = sum(agent.skills.values()) / len(agent.skills) if agent.skills else 0.0
            score += avg_skill * 0.3
        
        # Social reputation compatibility
        if hasattr(agent, 'social_system') and agent.id in self.social_system.reputations:
            reputation = self.social_system.reputations[agent.id]
            score += reputation.cooperative * 0.2
            score += reputation.trustworthy * 0.1
        
        # Age compatibility for families
        if group.group_type == GroupType.FAMILY:
            # Prefer adults for family formation
            if hasattr(agent, 'attributes'):
                age_factor = min(1.0, agent.attributes.get('age', 25) / 35.0)
                score += age_factor * 0.3
        
        return min(1.0, score)
    
    def suggest_group_formations(self, agents: List[Agent]) -> List[Dict[str, Any]]:
        """Suggest new group formations based on agent relationships"""
        suggestions = []
        
        for agent in agents:
            # Skip agents in cooldown
            if agent.id in self.group_formations:
                cooldown_period = 50
                if (self.world.time if hasattr(self.world, 'time') else 0) - self.group_formations[agent.id] < cooldown_period:
                    continue
            
            # Skip agents already in max groups
            existing_groups = self.get_groups_by_member(agent.id)
            if len(existing_groups) >= 3:  # Max 3 groups per agent
                continue
            
            # Find potential partners
            potential_partners = []
            if hasattr(agent, 'social_system') and agent.id in agent.social_system.relationships:
                relationships = agent.social_system.relationships[agent.id]
                for target_id, rel in relationships.items():
                    # Find agents with strong positive relationships
                    if (rel.strength >= 0.5 and 
                        rel.familiarity >= 0.3 and
                        len([g for g in self.get_groups_by_member(target_id) 
                             if g.group_type not in [g.group_type for g in existing_groups]]) < 3):
                        
                        target_agent = next((a for a in agents if a.id == target_id), None)
                        if target_agent:
                            potential_partners.append(target_agent)
            
            # Suggest group formation
            if len(potential_partners) >= 1:
                group_type = self._determine_group_type(agent, potential_partners)
                suggestions.append({
                    'founder': agent,
                    'partners': potential_partners,
                    'type': group_type,
                    'purpose': self._generate_group_purpose(group_type, agent, potential_partners)
                })
        
        return suggestions
    
    def _determine_group_type(self, founder: Agent, partners: List[Agent]) -> GroupType:
        """Determine the most appropriate group type based on agent characteristics"""
        # Analyze agent characteristics
        avg_attributes = {
            'strength': sum(a.attributes.get('strength', 10).current for a in [founder] + partners) / (len(partners) + 1),
            'intelligence': sum(a.attributes.get('intelligence', 10).current for a in [founder] + partners) / (len(partners) + 1),
            'charisma': sum(a.attributes.get('charisma', 10).current for a in [founder] + partners) / (len(partners) + 1)
        }
        
        # Determine group type based on characteristics and relationships
        if len(partners) <= 2 and avg_attributes['charisma'] > 12:
            return GroupType.FAMILY
        elif avg_attributes['intelligence'] > 14:
            return GroupType.GUILD
        elif avg_attributes['strength'] > 14:
            return GroupType.DEFENSE_ALLIANCE
        elif len(partners) <= 4:
            return GroupType.WORK_TEAM
        else:
            return GroupType.TRIBE
    
    def _generate_group_purpose(self, group_type: GroupType, founder: Agent, partners: List[Agent]) -> str:
        """Generate a purpose for the new group"""
        purposes = {
            GroupType.FAMILY: [
                "建立家庭，共同生活和繁衍后代",
                "创建温馨的家庭环境",
                "照顾家庭成员，传承家族传统"
            ],
            GroupType.WORK_TEAM: [
                "合作制作工具和物品",
                "技能分享和协作建造",
                "提高工作效率，实现共同目标"
            ],
            GroupType.TRIBE: [
                "共同生存和领土防护",
                "资源共享和集体决策",
                "建立稳定的部落社区"
            ],
            GroupType.GUILD: [
                "专业技能传承和发展",
                "贸易合作和知识交流",
                "建立专业标准和技术创新"
            ],
            GroupType.SOCIAL_CLUB: [
                "友谊交流和社交支持",
                "信息共享和经验交流",
                "建立社交网络和社区联系"
            ],
            GroupType.DEFENSE_ALLIANCE: [
                "共同防御和安全保护",
                "危机应对和相互支援",
                "维护社区和平与稳定"
            ]
        }
        
        return random.choice(purposes.get(group_type, ["共同发展，互利共赢"]))
    
    def update_group_dynamics(self):
        """Update all group dynamics periodically"""
        for group in list(self.groups.values()):
            # Update stability
            group.stability = group.calculate_group_stability()
            
            # Check for disbandment
            if group.stability < 0.2 and len(group.members) > 1:
                # Try to improve stability through leadership
                if group.leader_id:
                    # Leader can try to resolve conflicts
                    group.conflict_level *= 0.9
                    group.cooperation_level = min(1.0, group.cooperation_level + 0.1)
            
            # Disband group if stability too low
            if group.stability < 0.1 or len(group.members) <= 1:
                self.disband_group(group.id)
                continue
            
            # Update territory for larger groups
            if len(group.members) >= 5 and not group.territory:
                # Find average position of members
                positions = []
                for agent_id in group.members:
                    agent = next((a for a in self.world.agents if a.id == agent_id), None)
                    if agent:
                        positions.append(agent.position)
                
                if positions:
                    avg_x = sum(pos[0] for pos in positions) / len(positions)
                    avg_y = sum(pos[1] for pos in positions) / len(positions)
                    group.set_territory((int(avg_x), int(avg_y)), len(group.members) // 2 + 2)
    
    def get_group_summary(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive summary of a group"""
        if group_id not in self.groups:
            return None
        
        group = self.groups[group_id]
        return {
            'id': group.id,
            'name': group.name,
            'type': group.group_type.value,
            'purpose': group.purpose,
            'description': group.description,
            'formation_date': group.formation_date,
            'member_count': len(group.members),
            'max_members': group.max_members,
            'stability': group.stability,
            'reputation': group.reputation,
            'leader': group.leader_id,
            'territory': group.territory,
            'territory_radius': group.territory_radius,
            'resources': group.resources,
            'shared_knowledge': group.shared_knowledge,
            'traditions': group.traditions,
            'rules': group.rules,
            'active_projects': group.active_projects,
            'collective_goals': group.collective_goals,
            'conflict_level': group.conflict_level,
            'cooperation_level': group.cooperation_level,
            'decision_making_style': group.decision_making_style,
            'members': [
                {
                    'agent_id': m.agent_id,
                    'role': m.role.value,
                    'contribution_score': m.contribution_score,
                    'loyalty': m.loyalty,
                    'rank': m.rank,
                    'join_date': m.join_date
                }
                for m in group.members.values()
            ]
        }
    
    def get_group_by_agent(self, agent_id: str) -> Optional[str]:
        """Get the primary group for an agent (v1 compatibility)"""
        groups = self.get_groups_by_member(agent_id)
        if groups:
            # Return the most relevant group (first in list or highest stability)
            return max(groups, key=lambda g: g.stability).id
        return None
    
    def get_group_members(self, group_id: str) -> List[str]:
        """Get list of member IDs for a group (v1 compatibility)"""
        if group_id not in self.groups:
            return []
        return list(self.groups[group_id].members.keys())
    
    def get_group_type_v1(self, group_id: str) -> str:
        """Get group type as string (v1 compatibility)"""
        if group_id not in self.groups:
            return "unknown"
        return self.groups[group_id].group_type.value
    
    def process_group_resources_v1(self, group_id: str) -> Dict[str, int]:
        """Process group resources in v1 format"""
        if group_id not in self.groups:
            return {}
        
        group = self.groups[group_id]
        return {k: int(v) for k, v in group.resources.items()}
    
    def distribute_resources_to_members(self, group_id: str, 
                                      resource_type: str, 
                                      amount_per_member: int) -> Dict[str, int]:
        """Distribute resources to members (v1 compatibility)"""
        if group_id not in self.groups:
            return {}
        
        group = self.groups[group_id]
        distribution = group.distribute_resources(resource_type, float(amount_per_member))
        return {k: int(v) for k, v in distribution.items()}
    
    def get_group_stability_v1(self, group_id: str) -> float:
        """Get group stability in v1 format (0.0-2.0 scale)"""
        if group_id not in self.groups:
            return 0.0
        
        group = self.groups[group_id]
        # Convert from 0.0-1.0 to 0.0-2.0 scale
        return group.stability * 2.0