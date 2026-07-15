"""
Social System Integration for Project Genesis v2.

This module provides integration between the social systems (social.py and groups.py)
and the Trinity system, ensuring compatibility with the enhanced memory system
and LLM-native design.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
import uuid

from ..core.world import World
from .base import Agent
from .social import SocialSystem, SocialInteractionType, RelationshipType
from .groups import GroupManager, GroupType, GroupRole
from .memory import Memory


class SocialIntegration:
    """Main integration class for social systems in Project Genesis v2"""
    
    def __init__(self, world: World):
        self.world = world
        self.social_system = SocialSystem(world)
        self.group_manager = GroupManager(world, self.social_system)
        
    def initialize_agent(self, agent: Agent):
        """Initialize social data for a new agent"""
        self.social_system.initialize_agent_social_data(agent)
        
    def get_agent_social_context(self, agent: Agent) -> Dict[str, Any]:
        """Get comprehensive social context for an agent"""
        agent_id = agent.id
        
        # Get social network summary
        social_summary = self.social_system.get_social_network_summary(agent_id)
        
        # Get group memberships
        groups = self.group_manager.get_groups_by_member(agent_id)
        group_summaries = []
        for group in groups:
            membership = group.members.get(agent_id)
            if membership:
                group_summaries.append({
                    'group_id': group.id,
                    'group_name': group.name,
                    'group_type': group.group_type.value,
                    'role': membership.role.value,
                    'contribution_score': membership.contribution_score,
                    'loyalty': membership.loyalty
                })
        
        return {
            'social_network': social_summary,
            'group_memberships': group_summaries,
            'total_groups': len(groups),
            'social_influence': agent.get_social_influence_score()
        }
    
    def process_social_interaction(self, agent1: Agent, agent2: Agent, 
                                 interaction_type: str, success: bool, 
                                 outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Process a social interaction between two agents"""
        # Map string interaction type to enum
        interaction_enum = self._map_interaction_type(interaction_type)
        
        # Process through social system
        result = self.social_system.process_social_interaction(
            agent1, agent2, interaction_enum, success, outcome
        )
        
        # Add memory entries for both agents
        memory_content = {
            'interaction_type': interaction_type,
            'target_agent': agent2.id,
            'success': success,
            'outcome': outcome,
            'relationship_impact': result['agent_impact']
        }
        
        agent1.add_memory('social_interaction', memory_content, importance=0.6)
        
        memory_content['target_agent'] = agent1.id
        memory_content['relationship_impact'] = result['target_impact']
        agent2.add_memory('social_interaction', memory_content, importance=0.6)
        
        return result
    
    def suggest_group_formation(self, agent: Agent) -> List[Dict[str, Any]]:
        """Suggest potential group formations for an agent"""
        return self.group_manager.suggest_group_formations([agent])
    
    def create_group(self, agent: Agent, group_type: GroupType, 
                    purpose: str, name: Optional[str] = None) -> Optional[str]:
        """Create a new group with the agent as founder"""
        group_id = self.group_manager.create_group(group_type, agent.id, purpose, name)
        if group_id:
            agent.join_group(group_id)
            
            # Add memory entry
            memory_content = {
                'group_id': group_id,
                'group_type': group_type.value,
                'purpose': purpose,
                'action': 'group_creation'
            }
            agent.add_memory('group_formation', memory_content, importance=0.8)
            
        return group_id
    
    def join_group(self, agent: Agent, group_id: str) -> bool:
        """Add an agent to an existing group"""
        success = self.group_manager.add_member_to_group(group_id, agent.id)
        if success:
            agent.join_group(group_id)
            
            # Add memory entry
            group = self.group_manager.get_group(group_id)
            if group:
                memory_content = {
                    'group_id': group_id,
                    'group_name': group.name,
                    'group_type': group.group_type.value,
                    'action': 'group_join'
                }
                agent.add_memory('group_membership', memory_content, importance=0.5)
                
        return success
    
    def leave_group(self, agent: Agent, group_id: str) -> bool:
        """Remove an agent from a group"""
        success = self.group_manager.remove_member_from_group(group_id, agent.id)
        if success:
            agent.leave_group(group_id)
            
            # Add memory entry
            group = self.group_manager.get_group(group_id)
            if group:
                memory_content = {
                    'group_id': group_id,
                    'group_name': group.name,
                    'action': 'group_leave'
                }
                agent.add_memory('group_membership', memory_content, importance=0.4)
                
        return success
    
    def update_group_contribution(self, agent: Agent, group_id: str, 
                                contribution: float) -> bool:
        """Update an agent's contribution to a group"""
        group = self.group_manager.get_group(group_id)
        if group and group.has_member(agent.id):
            group.update_member_contribution(agent.id, contribution)
            
            # Update agent's leadership score based on contribution
            agent.leadership_score = min(1.0, agent.leadership_score + contribution * 0.1)
            
            return True
        return False
    
    def get_recommendations_for_agent(self, agent: Agent) -> Dict[str, Any]:
        """Get social recommendations for an agent"""
        recommendations = {
            'potential_groups': [],
            'potential_allies': [],
            'social_actions': []
        }
        
        # Find suitable groups
        suitable_groups = self.group_manager.find_suitable_groups(agent)
        for group in suitable_groups[:3]:  # Top 3 recommendations
            recommendations['potential_groups'].append({
                'group_id': group.id,
                'group_name': group.name,
                'group_type': group.group_type.value,
                'purpose': group.purpose,
                'member_count': len(group.members),
                'max_members': group.max_members
            })
        
        # Find potential allies
        if agent.id in self.social_system.relationships:
            allies = self.social_system.find_potential_allies(agent.id)
            for ally_id in allies[:5]:  # Top 5 recommendations
                ally_info = {
                    'agent_id': ally_id,
                    'relationship_type': self.social_system.relationships[agent.id][ally_id].relationship_type.value,
                    'strength': self.social_system.relationships[agent.id][ally_id].strength
                }
                recommendations['potential_allies'].append(ally_info)
        
        # Suggest social actions based on needs and context
        if agent.needs['social'].current > 70:
            recommendations['social_actions'].append({
                'action': 'seek_social_interaction',
                'priority': 'high',
                'description': 'Your social needs are high - consider interacting with other agents'
            })
        
        if len(agent.group_memberships) == 0:
            recommendations['social_actions'].append({
                'action': 'join_or_form_group',
                'priority': 'medium',
                'description': 'Consider joining or forming a group for mutual benefit'
            })
        
        return recommendations
    
    def get_social_memory_context(self, agent: Agent) -> Dict[str, Any]:
        """Get social context for memory system integration"""
        agent_id = agent.id
        
        # Get recent social memories
        social_memories = [m for m in agent.memories if m.type == 'social_interaction'][-10:]
        
        # Get group-related memories
        group_memories = [m for m in agent.memories if m.type in ['group_formation', 'group_membership']][-5:]
        
        # Get relationship summaries
        relationships = []
        if agent_id in self.social_system.relationships:
            for target_id, rel in self.social_system.relationships[agent_id].items():
                relationships.append({
                    'target_id': target_id,
                    'type': rel.relationship_type.value,
                    'strength': f"{rel.strength:.2f}",
                    'trust': f"{rel.trust:.2f}",
                    'last_interaction': rel.last_interaction
                })
        
        return {
            'recent_social_interactions': [m.to_dict() for m in social_memories],
            'group_history': [m.to_dict() for m in group_memories],
            'current_relationships': relationships,
            'group_memberships': agent.group_memberships
        }
    
    def _map_interaction_type(self, interaction_str: str) -> SocialInteractionType:
        """Map string interaction type to enum"""
        mapping = {
            'greeting': SocialInteractionType.GREETING,
            'trade': SocialInteractionType.TRADE,
            'help': SocialInteractionType.HELP,
            'request': SocialInteractionType.REQUEST,
            'conflict': SocialInteractionType.CONFLICT,
            'cooperation': SocialInteractionType.COOPERATION,
            'information_sharing': SocialInteractionType.INFORMATION_SHARING,
            'resource_sharing': SocialInteractionType.RESOURCE_SHARING,
            'defense': SocialInteractionType.DEFENSE,
            'leadership': SocialInteractionType.LEADERSHIP
        }
        return mapping.get(interaction_str.lower(), SocialInteractionType.COOPERATION)
    
    def update_all_groups(self):
        """Update all group dynamics"""
        self.group_manager.update_group_dynamics()
    
    def get_world_social_summary(self) -> Dict[str, Any]:
        """Get comprehensive social summary for the entire world"""
        return {
            'total_groups': len(self.group_manager.groups),
            'group_types': {
                gt.value: len(self.group_manager.get_groups_by_type(gt))
                for gt in GroupType
            },
            'total_agents': len(self.world.agents),
            'social_connections': len(self.social_system.interactions),
            'group_distribution': {
                group_id: {
                    'type': group.group_type.value,
                    'members': len(group.members),
                    'stability': group.stability
                }
                for group_id, group in self.group_manager.groups.items()
            }
        }