"""
Genesis Agent System

This package provides comprehensive agent systems including:
- Base agent functionality
- Social systems (relationships, reputation, interactions)
- Group management and dynamics
- Memory systems
- Skills and attributes
"""

from .base import Agent, AgentState, AgentAttribute, Item, Memory, Goal
from .social import SocialSystem, RelationshipType, SocialInteractionType, Relationship, Reputation
from .groups import GroupManager, Group, GroupType, GroupRole, GroupMembership
from .social_integration import SocialIntegration

__all__ = [
    # Base classes
    'Agent',
    'AgentState',
    'AgentAttribute',
    'Item',
    'Memory',
    'Goal',
    
    # Social system
    'SocialSystem',
    'RelationshipType',
    'SocialInteractionType',
    'Relationship',
    'Reputation',
    
    # Group system
    'GroupManager',
    'Group',
    'GroupType',
    'GroupRole',
    'GroupMembership',
    
    # Integration
    'SocialIntegration'
]