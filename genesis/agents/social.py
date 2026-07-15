"""
Social systems for Project Genesis v2.

This module provides comprehensive social systems including relationships, reputation,
social interactions, and influence mechanisms for agents in the simulation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import random
import uuid

from ..core.world import World
from .base import Agent


class RelationshipType(Enum):
    """Types of relationships between agents"""
    STRANGER = "stranger"
    ACQUAINTANCE = "acquaintance"
    FRIEND = "friend"
    CLOSE_FRIEND = "close_friend"
    RIVAL = "rival"
    ENEMY = "enemy"
    ALLY = "ally"
    LEADER = "leader"
    FOLLOWER = "follower"
    FAMILY = "family"
    PARTNER = "partner"


class SocialInteractionType(Enum):
    """Types of social interactions"""
    GREETING = "greeting"
    TRADE = "trade"
    HELP = "help"
    REQUEST = "request"
    CONFLICT = "conflict"
    COOPERATION = "cooperation"
    INFORMATION_SHARING = "information_sharing"
    RESOURCE_SHARING = "resource_sharing"
    DEFENSE = "defense"
    LEADERSHIP = "leadership"


@dataclass
class Relationship:
    """Represents a relationship between two agents"""
    target_agent_id: str
    relationship_type: RelationshipType
    strength: float  # -1.0 (hostile) to 1.0 (friendly)
    trust: float  # 0.0 to 1.0
    respect: float  # 0.0 to 1.0
    familiarity: float  # 0.0 to 1.0 (how well they know each other)
    interactions: int = 0
    last_interaction: int = 0
    shared_goals: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    cooperation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def update_strength(self, change: float):
        """Update relationship strength with bounds"""
        self.strength = max(-1.0, min(1.0, self.strength + change))
        
    def update_trust(self, change: float):
        """Update trust level with bounds"""
        self.trust = max(0.0, min(1.0, self.trust + change))
        
    def update_respect(self, change: float):
        """Update respect level with bounds"""
        self.respect = max(0.0, min(1.0, self.respect + change))
        
    def update_familiarity(self, change: float):
        """Update familiarity level with bounds"""
        self.familiarity = max(0.0, min(1.0, self.familiarity + change))


@dataclass
class SocialInteraction:
    """Represents a social interaction between agents"""
    interaction_id: str
    source_agent_id: str
    target_agent_id: str
    interaction_type: SocialInteractionType
    timestamp: int
    success: bool
    outcome: Dict[str, Any]
    impact_on_relationship: float  # How much this affects the relationship
    reputation_effects: Dict[str, float] = field(default_factory=dict)


@dataclass
class Reputation:
    """Represents an agent's reputation across different dimensions"""
    trustworthy: float = 0.5  # 0.0 to 1.0
    skilled: float = 0.5
    brave: float = 0.5
    wise: float = 0.5
    generous: float = 0.5
    leader: float = 0.5
    cooperative: float = 0.5
    aggressive: float = 0.0  # Can be negative
    
    def update_reputation(self, dimension: str, change: float):
        """Update reputation in a specific dimension"""
        if hasattr(self, dimension):
            current_value = getattr(self, dimension)
            new_value = max(0.0, min(1.0, current_value + change))
            setattr(self, dimension, new_value)
    
    def get_overall_reputation(self) -> float:
        """Calculate overall reputation score"""
        positive_dims = [
            'trustworthy', 'skilled', 'brave', 'wise', 
            'generous', 'leader', 'cooperative'
        ]
        positive_sum = sum(getattr(self, dim) for dim in positive_dims)
        negative_penalty = self.aggressive * 0.5  # Aggressive behavior reduces overall rep
        return max(0.0, (positive_sum / len(positive_dims)) - negative_penalty)


class SocialSystem:
    """Comprehensive social system for managing agent relationships and interactions"""
    
    def __init__(self, world: World):
        self.world = world
        self.relationships: Dict[str, Dict[str, Relationship]] = {}  # agent_id -> {target_id: Relationship}
        self.reputations: Dict[str, Reputation] = {}  # agent_id -> Reputation
        self.interactions: List[SocialInteraction] = []
        self.influence_network: Dict[str, Dict[str, float]] = {}  # agent_id -> {target_id: influence_score}
        
    def initialize_agent_social_data(self, agent: Agent):
        """Initialize social data for a new agent"""
        agent_id = agent.id
        self.relationships[agent_id] = {}
        self.reputations[agent_id] = Reputation()
        self.influence_network[agent_id] = {}
        
        # Initialize reputation based on agent attributes
        charisma = agent.attributes['charisma'].current
        intelligence = agent.attributes['intelligence'].current
        strength = agent.attributes['strength'].current
        
        self.reputations[agent_id].trustworthy = max(0.1, min(0.9, charisma / 20.0))
        self.reputations[agent_id].skilled = max(0.1, min(0.9, intelligence / 20.0))
        self.reputations[agent_id].brave = max(0.1, min(0.9, strength / 20.0))
        self.reputations[agent_id].wise = max(0.1, min(0.9, intelligence / 25.0))
    
    def get_relationship(self, agent_id: str, target_id: str) -> Optional[Relationship]:
        """Get relationship between two agents"""
        if agent_id in self.relationships and target_id in self.relationships[agent_id]:
            return self.relationships[agent_id][target_id]
        return None
    
    def create_relationship(self, agent_id: str, target_id: str, 
                          relationship_type: RelationshipType = RelationshipType.STRANGER,
                          initial_strength: float = 0.0) -> Relationship:
        """Create a new relationship between two agents"""
        if agent_id not in self.relationships:
            self.relationships[agent_id] = {}
            
        relationship = Relationship(
            target_agent_id=target_id,
            relationship_type=relationship_type,
            strength=initial_strength,
            trust=abs(initial_strength) * 0.5,
            respect=abs(initial_strength) * 0.3,
            familiarity=0.1
        )
        
        self.relationships[agent_id][target_id] = relationship
        return relationship
    
    def update_relationship(self, agent_id: str, target_id: str, 
                          interaction_type: SocialInteractionType, 
                          success: bool, outcome: Dict[str, Any]) -> float:
        """Update relationship based on social interaction"""
        if agent_id not in self.relationships:
            self.create_relationship(agent_id, target_id)
        
        relationship = self.relationships[agent_id][target_id]
        
        # Calculate relationship impact
        impact = self._calculate_relationship_impact(interaction_type, success, outcome)
        relationship.update_strength(impact)
        
        # Update trust and respect based on interaction
        if success:
            relationship.update_trust(0.05 * abs(impact))
            if interaction_type in [SocialInteractionType.HELP, SocialInteractionType.COOPERATION]:
                relationship.update_respect(0.03)
        else:
            relationship.update_trust(-0.02)
            if interaction_type == SocialInteractionType.CONFLICT:
                relationship.update_respect(-0.05)
        
        # Update familiarity
        relationship.update_familiarity(0.02)
        relationship.interactions += 1
        relationship.last_interaction = self.world.time if hasattr(self.world, 'time') else 0
        
        # Update relationship type based on strength and familiarity
        self._update_relationship_type(relationship)
        
        # Create interaction record
        interaction = SocialInteraction(
            interaction_id=str(uuid.uuid4()),
            source_agent_id=agent_id,
            target_agent_id=target_id,
            interaction_type=interaction_type,
            timestamp=self.world.time if hasattr(self.world, 'time') else 0,
            success=success,
            outcome=outcome,
            impact_on_relationship=impact
        )
        
        self.interactions.append(interaction)
        
        # Update mutual relationship (bidirectional)
        if target_id in self.relationships:
            if agent_id in self.relationships[target_id]:
                self.relationships[target_id][agent_id].update_strength(impact * 0.8)
        
        return impact
    
    def _calculate_relationship_impact(self, interaction_type: SocialInteractionType, 
                                     success: bool, outcome: Dict[str, Any]) -> float:
        """Calculate how much an interaction affects the relationship"""
        base_impacts = {
            SocialInteractionType.GREETING: 0.02,
            SocialInteractionType.TRADE: 0.05,
            SocialInteractionType.HELP: 0.08,
            SocialInteractionType.REQUEST: 0.03,
            SocialInteractionType.CONFLICT: -0.15,
            SocialInteractionType.COOPERATION: 0.10,
            SocialInteractionType.INFORMATION_SHARING: 0.04,
            SocialInteractionType.RESOURCE_SHARING: 0.06,
            SocialInteractionType.DEFENSE: 0.12,
            SocialInteractionType.LEADERSHIP: 0.07,
        }
        
        impact = base_impacts.get(interaction_type, 0.0)
        
        if not success:
            impact *= -0.5  # Failed interactions have reduced or negative impact
        
        # Scale based on outcome value
        if 'value' in outcome:
            impact *= min(2.0, max(0.5, abs(outcome['value']) / 10.0))
        
        return impact if success else impact * 0.7
    
    def _update_relationship_type(self, relationship: Relationship):
        """Update relationship type based on current strength and familiarity"""
        if relationship.strength >= 0.8 and relationship.familiarity >= 0.7:
            relationship.relationship_type = RelationshipType.CLOSE_FRIEND
        elif relationship.strength >= 0.5 and relationship.familiarity >= 0.4:
            relationship.relationship_type = RelationshipType.FRIEND
        elif relationship.strength >= 0.2 and relationship.familiarity >= 0.2:
            relationship.relationship_type = RelationshipType.ACQUAINTANCE
        elif relationship.strength <= -0.5:
            relationship.relationship_type = RelationshipType.ENEMY
        elif relationship.strength <= -0.2:
            relationship.relationship_type = RelationshipType.RIVAL
        else:
            relationship.relationship_type = RelationshipType.STRANGER
    
    def get_social_influence(self, agent_id: str) -> float:
        """Calculate agent's overall social influence"""
        if agent_id not in self.relationships:
            return 0.0
        
        # Base influence from reputation
        reputation_score = self.reputations[agent_id].get_overall_reputation()
        
        # Influence from relationships
        relationship_influence = 0.0
        relationships = self.relationships[agent_id]
        for rel in relationships.values():
            relationship_influence += abs(rel.strength) * rel.familiarity
        
        # Network effect - agents with more connections have more influence
        network_bonus = min(0.5, len(relationships) * 0.05)
        
        return reputation_score + (relationship_influence * 0.3) + network_bonus
    
    def get_influence_on_target(self, agent_id: str, target_id: str) -> float:
        """Calculate how much influence one agent has over another"""
        if agent_id not in self.relationships or target_id not in self.relationships[agent_id]:
            return 0.0
        
        relationship = self.relationships[agent_id][target_id]
        
        # Influence based on relationship strength and trust
        base_influence = abs(relationship.strength) * relationship.trust
        
        # Reputation multiplier
        agent_reputation = self.reputations[agent_id].get_overall_reputation()
        target_reputation = self.reputations[target_id].get_overall_reputation()
        
        reputation_factor = (agent_reputation + 0.1) / (target_reputation + 0.2)
        
        return base_influence * min(2.0, max(0.1, reputation_factor))
    
    def find_potential_allies(self, agent_id: str, min_strength: float = 0.3) -> List[str]:
        """Find potential allies for an agent"""
        if agent_id not in self.relationships:
            return []
        
        allies = []
        for target_id, relationship in self.relationships[agent_id].items():
            if relationship.strength >= min_strength:
                allies.append(target_id)
        
        return sorted(allies, key=lambda x: self.relationships[agent_id][x].strength, reverse=True)
    
    def find_potential_enemies(self, agent_id: str, max_strength: float = -0.3) -> List[str]:
        """Find potential enemies for an agent"""
        if agent_id not in self.relationships:
            return []
        
        enemies = []
        for target_id, relationship in self.relationships[agent_id].items():
            if relationship.strength <= max_strength:
                enemies.append(target_id)
        
        return sorted(enemies, key=lambda x: self.relationships[agent_id][x].strength)
    
    def get_social_network_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive summary of agent's social network"""
        if agent_id not in self.relationships:
            return {"relationships": [], "reputation": {}, "influence": 0.0}
        
        relationships = self.relationships[agent_id]
        reputation = self.reputations[agent_id]
        
        relationship_summary = []
        for target_id, rel in relationships.items():
            relationship_summary.append({
                "target_id": target_id,
                "type": rel.relationship_type.value,
                "strength": rel.strength,
                "trust": rel.trust,
                "respect": rel.respect,
                "familiarity": rel.familiarity,
                "interactions": rel.interactions
            })
        
        return {
            "relationships": relationship_summary,
            "reputation": {
                "trustworthy": reputation.trustworthy,
                "skilled": reputation.skilled,
                "brave": reputation.brave,
                "wise": reputation.wise,
                "generous": reputation.generous,
                "leader": reputation.leader,
                "cooperative": reputation.cooperative,
                "aggressive": reputation.aggressive,
                "overall": reputation.get_overall_reputation()
            },
            "influence": self.get_social_influence(agent_id),
            "total_connections": len(relationships)
        }
    
    def decay_relationships(self, decay_rate: float = 0.001):
        """Gradually decay relationships over time"""
        for agent_id in self.relationships:
            for target_id, relationship in list(self.relationships[agent_id].items()):
                # Decay strength over time
                if relationship.interactions > 0:
                    relationship.update_strength(-decay_rate)
                    relationship.update_familiarity(-decay_rate * 0.5)
                    
                    # Remove very weak relationships
                    if abs(relationship.strength) < 0.01 and relationship.familiarity < 0.05:
                        del self.relationships[agent_id][target_id]
    
    def process_social_interaction(self, agent: Agent, target: Agent, 
                                 interaction_type: SocialInteractionType,
                                 success: bool, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Process a complete social interaction between two agents"""
        agent_id = agent.id
        target_id = target.id
        
        # Update relationships
        agent_impact = self.update_relationship(agent_id, target_id, interaction_type, success, outcome)
        target_impact = self.update_relationship(target_id, agent_id, interaction_type, success, outcome)
        
        # Update reputations based on interaction
        if success:
            if interaction_type in [SocialInteractionType.HELP, SocialInteractionType.COOPERATION]:
                self.reputations[agent_id].update_reputation("generous", 0.02)
                self.reputations[agent_id].update_reputation("cooperative", 0.01)
            elif interaction_type == SocialInteractionType.LEADERSHIP:
                self.reputations[agent_id].update_reputation("leader", 0.03)
        else:
            if interaction_type == SocialInteractionType.CONFLICT:
                self.reputations[agent_id].update_reputation("aggressive", 0.05)
        
        return {
            "agent_impact": agent_impact,
            "target_impact": target_impact,
            "agent_reputation": self.reputations[agent_id].get_overall_reputation(),
            "target_reputation": self.reputations[target_id].get_overall_reputation()
        }
    
    def calculate_social_influence_v1(self, agent_id: str) -> int:
        """Calculate agent's social influence (v1 compatibility method)"""
        if agent_id not in self.relationships:
            return 0
        
        # Connection influence
        connection_influence = sum(abs(conn["strength"]) for conn in self.relationships[agent_id].values())
        
        # Reputation influence
        reputation_influence = int(self.reputations[agent_id].get_overall_reputation() * 100)
        
        # Skill influence (assuming social skills)
        skill_influence = 0  # Will be populated by Trinity system
        
        return int(connection_influence + reputation_influence + skill_influence)
    
    def get_social_connections_count(self, agent_id: str) -> int:
        """Get count of social connections for v1 compatibility"""
        return len(self.relationships.get(agent_id, {}))
    
    def get_reputation_summary_v1(self, agent_id: str) -> Dict[str, int]:
        """Get reputation in v1 format (0-100 scale)"""
        if agent_id not in self.reputations:
            return {"trustworthy": 0, "skilled": 0, "brave": 0, "wise": 0}
        
        reputation = self.reputations[agent_id]
        return {
            "trustworthy": int(reputation.trustworthy * 100),
            "skilled": int(reputation.skilled * 100),
            "brave": int(reputation.brave * 100),
            "wise": int(reputation.wise * 100)
        }