"""Comprehensive interaction system for trade, combat, diplomacy, and social dynamics"""
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from loguru import logger

from .agent_state import AgentState, Relationship, SkillType, AgentStatus


class InteractionType(Enum):
    """Types of interactions between agents"""
    TRADE = "trade"
    COMBAT = "combat"
    DIPLOMACY = "diplomacy"
    SOCIAL = "social"
    COOPERATION = "cooperation"
    COMPETITION = "competition"
    TEACHING = "teaching"
    HEALING = "healing"


class InteractionOutcome(Enum):
    """Possible outcomes of interactions"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


@dataclass
class InteractionContext:
    """Context information for an interaction"""
    initiator_id: str
    target_id: str
    interaction_type: InteractionType
    location: Tuple[int, int]
    timestamp: float = field(default_factory=time.time)
    witnesses: List[str] = field(default_factory=list)
    environmental_factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InteractionResult:
    """Result of an interaction"""
    outcome: InteractionOutcome
    initiator_effects: Dict[str, Any] = field(default_factory=dict)
    target_effects: Dict[str, Any] = field(default_factory=dict)
    relationship_changes: Dict[str, float] = field(default_factory=dict)
    world_effects: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    reputation_changes: Dict[str, int] = field(default_factory=dict)


class BaseInteraction(ABC):
    """Base class for all interaction types"""
    
    def __init__(self, context: InteractionContext):
        self.context = context
        self.requirements_met = True
        self.failure_reasons: List[str] = []
    
    @abstractmethod
    def check_prerequisites(self, initiator: AgentState, target: AgentState) -> bool:
        """Check if interaction can proceed"""
        pass
    
    @abstractmethod
    def execute(self, initiator: AgentState, target: AgentState) -> InteractionResult:
        """Execute the interaction"""
        pass
    
    def calculate_success_probability(self, initiator: AgentState, target: AgentState) -> float:
        """Calculate base success probability (0-1)"""
        return 0.5  # Default 50% chance


class TradeInteraction(BaseInteraction):
    """Handles trading between agents"""
    
    def __init__(self, context: InteractionContext, offer: Dict[str, int], request: Dict[str, int]):
        super().__init__(context)
        self.offer = offer  # What initiator offers
        self.request = request  # What initiator wants
    
    def check_prerequisites(self, initiator: AgentState, target: AgentState) -> bool:
        """Check if trade can proceed"""
        # Check if initiator has offered items
        for item, quantity in self.offer.items():
            if item not in initiator.inventory or initiator.inventory[item].quantity < quantity:
                self.failure_reasons.append(f"Initiator lacks {quantity} {item}")
                return False
        
        # Check if target has requested items
        for item, quantity in self.request.items():
            if item not in target.inventory or target.inventory[item].quantity < quantity:
                self.failure_reasons.append(f"Target lacks {quantity} {item}")
                return False
        
        # Check if both agents can carry the additional weight
        offer_weight = sum(self.offer.values())
        request_weight = sum(self.request.values())
        
        if target.current_weight + offer_weight > target.max_carry_weight:
            self.failure_reasons.append("Target cannot carry offered items")
            return False
        
        if initiator.current_weight + request_weight > initiator.max_carry_weight:
            self.failure_reasons.append("Initiator cannot carry requested items")
            return False
        
        return True
    
    def calculate_success_probability(self, initiator: AgentState, target: AgentState) -> float:
        """Calculate trade success probability based on various factors"""
        base_prob = 0.5
        
        # Relationship factor
        if target.agent_id in initiator.relationships:
            rel = initiator.relationships[target.agent_id]
            base_prob += rel.strength / 200  # -0.5 to +0.5 modifier
            base_prob += rel.trust / 200     # 0 to +0.5 modifier
        
        # Charisma factor
        charisma_bonus = (initiator.attributes.get("charisma", 5) - 5) * 0.05
        base_prob += charisma_bonus
        
        # Trading skill factor
        trading_skill = initiator.get_skill_level(SkillType.TRADING)
        skill_bonus = (trading_skill - 1) * 0.03
        base_prob += skill_bonus
        
        # Fairness of trade (simple value comparison)
        offer_value = sum(self.offer.values())
        request_value = sum(self.request.values())
        if offer_value > 0 and request_value > 0:
            fairness = min(offer_value, request_value) / max(offer_value, request_value)
            base_prob += (fairness - 0.5) * 0.4
        
        return max(0.1, min(0.9, base_prob))
    
    def execute(self, initiator: AgentState, target: AgentState) -> InteractionResult:
        """Execute the trade"""
        if not self.check_prerequisites(initiator, target):
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description=f"Trade failed: {', '.join(self.failure_reasons)}"
            )
        
        success_prob = self.calculate_success_probability(initiator, target)
        
        if random.random() < success_prob:
            # Successful trade
            # Transfer items
            for item, quantity in self.offer.items():
                initiator.remove_inventory_item(item, quantity)
                target.add_inventory_item(item, quantity, source=f"trade_with_{initiator.agent_id}")
            
            for item, quantity in self.request.items():
                target.remove_inventory_item(item, quantity)
                initiator.add_inventory_item(item, quantity, source=f"trade_with_{target.agent_id}")
            
            # Update relationships
            initiator.update_relationship(target.agent_id, "trading_partner", 5.0, 2.0)
            target.update_relationship(initiator.agent_id, "trading_partner", 5.0, 2.0)
            
            # Add experience
            initiator.add_skill_experience(SkillType.TRADING, 10.0)
            target.add_skill_experience(SkillType.TRADING, 5.0)
            
            # Add memories
            trade_desc = f"Traded {self.offer} for {self.request} with {target.name}"
            initiator.add_memory(trade_desc, "event", 0.6, {target.agent_id})
            target.add_memory(f"Traded {self.request} for {self.offer} with {initiator.name}", 
                            "event", 0.6, {initiator.agent_id})
            
            return InteractionResult(
                outcome=InteractionOutcome.SUCCESS,
                description=f"Successful trade: {initiator.name} gave {self.offer} for {self.request}",
                relationship_changes={
                    f"{initiator.agent_id}->{target.agent_id}": 5.0,
                    f"{target.agent_id}->{initiator.agent_id}": 5.0
                }
            )
        else:
            # Failed trade
            initiator.update_relationship(target.agent_id, "rejected_trader", -2.0, -1.0)
            target.update_relationship(initiator.agent_id, "rejected_trader", -1.0)
            
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description=f"Trade rejected by {target.name}",
                relationship_changes={
                    f"{initiator.agent_id}->{target.agent_id}": -2.0,
                    f"{target.agent_id}->{initiator.agent_id}": -1.0
                }
            )


class CombatInteraction(BaseInteraction):
    """Handles combat between agents"""
    
    def __init__(self, context: InteractionContext, combat_type: str = "physical"):
        super().__init__(context)
        self.combat_type = combat_type  # "physical", "verbal", "intimidation"
    
    def check_prerequisites(self, initiator: AgentState, target: AgentState) -> bool:
        """Check if combat can proceed"""
        if initiator.status != AgentStatus.ALIVE:
            self.failure_reasons.append("Initiator is not alive")
            return False
        
        if target.status != AgentStatus.ALIVE:
            self.failure_reasons.append("Target is not alive")
            return False
        
        if initiator.health < 20:
            self.failure_reasons.append("Initiator too weak to fight")
            return False
        
        return True
    
    def calculate_combat_strength(self, agent: AgentState) -> float:
        """Calculate agent's combat effectiveness"""
        base_strength = agent.attributes.get("strength", 5)
        dexterity = agent.attributes.get("dexterity", 5)
        constitution = agent.attributes.get("constitution", 5)
        
        # Combat skill bonus
        combat_skill = agent.get_skill_level(SkillType.COMBAT)
        skill_bonus = combat_skill * 2
        
        # Health factor
        health_factor = agent.health / 100.0
        
        # Equipment bonus (simplified - count weapons/armor)
        equipment_bonus = 0
        for item_name in agent.inventory:
            if "sword" in item_name.lower() or "axe" in item_name.lower():
                equipment_bonus += 3
            elif "armor" in item_name.lower() or "shield" in item_name.lower():
                equipment_bonus += 2
        
        total_strength = (base_strength + dexterity + constitution) * health_factor + skill_bonus + equipment_bonus
        return max(1.0, total_strength)
    
    def execute(self, initiator: AgentState, target: AgentState) -> InteractionResult:
        """Execute combat"""
        if not self.check_prerequisites(initiator, target):
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description=f"Combat failed: {', '.join(self.failure_reasons)}"
            )
        
        initiator_strength = self.calculate_combat_strength(initiator)
        target_strength = self.calculate_combat_strength(target)
        
        # Calculate outcome probability
        total_strength = initiator_strength + target_strength
        initiator_win_chance = initiator_strength / total_strength
        
        # Determine outcome
        roll = random.random()
        
        if roll < initiator_win_chance:
            # Initiator wins
            damage_to_target = random.randint(10, 30)
            damage_to_initiator = random.randint(5, 15)
            
            target.health = max(0, target.health - damage_to_target)
            initiator.health = max(0, initiator.health - damage_to_initiator)
            
            # Experience and relationship changes
            initiator.add_skill_experience(SkillType.COMBAT, 15.0)
            target.add_skill_experience(SkillType.COMBAT, 8.0)
            
            initiator.update_relationship(target.agent_id, "defeated_enemy", 10.0, -5.0)
            target.update_relationship(initiator.agent_id, "victorious_enemy", -15.0, -10.0)
            
            # Check if target died
            if target.health <= 0:
                target.status = AgentStatus.DEAD
                target.add_memory(f"Killed in combat by {initiator.name}", "event", 1.0)
                initiator.add_memory(f"Killed {target.name} in combat", "event", 0.8, {target.agent_id})
                
                return InteractionResult(
                    outcome=InteractionOutcome.SUCCESS,
                    description=f"{initiator.name} killed {target.name} in combat",
                    initiator_effects={"health": -damage_to_initiator},
                    target_effects={"health": -damage_to_target, "status": "dead"},
                    relationship_changes={f"{initiator.agent_id}->{target.agent_id}": 10.0},
                    reputation_changes={initiator.agent_id: -5}  # Killing hurts reputation
                )
            else:
                return InteractionResult(
                    outcome=InteractionOutcome.SUCCESS,
                    description=f"{initiator.name} defeated {target.name} in combat",
                    initiator_effects={"health": -damage_to_initiator},
                    target_effects={"health": -damage_to_target},
                    relationship_changes={
                        f"{initiator.agent_id}->{target.agent_id}": 10.0,
                        f"{target.agent_id}->{initiator.agent_id}": -15.0
                    }
                )
        else:
            # Target wins
            damage_to_initiator = random.randint(15, 35)
            damage_to_target = random.randint(3, 12)
            
            initiator.health = max(0, initiator.health - damage_to_initiator)
            target.health = max(0, target.health - damage_to_target)
            
            initiator.add_skill_experience(SkillType.COMBAT, 8.0)
            target.add_skill_experience(SkillType.COMBAT, 15.0)
            
            initiator.update_relationship(target.agent_id, "victorious_enemy", -15.0, -10.0)
            target.update_relationship(initiator.agent_id, "defeated_enemy", 10.0, -5.0)
            
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description=f"{target.name} defeated {initiator.name} in combat",
                initiator_effects={"health": -damage_to_initiator},
                target_effects={"health": -damage_to_target},
                relationship_changes={
                    f"{initiator.agent_id}->{target.agent_id}": -15.0,
                    f"{target.agent_id}->{initiator.agent_id}": 10.0
                }
            )


class DiplomacyInteraction(BaseInteraction):
    """Handles diplomatic interactions"""
    
    def __init__(self, context: InteractionContext, proposal_type: str, terms: Dict[str, Any]):
        super().__init__(context)
        self.proposal_type = proposal_type  # "alliance", "peace", "trade_agreement", etc.
        self.terms = terms
    
    def check_prerequisites(self, initiator: AgentState, target: AgentState) -> bool:
        """Check if diplomacy can proceed"""
        # Both agents must be alive and have sufficient charisma/intelligence
        if initiator.status != AgentStatus.ALIVE or target.status != AgentStatus.ALIVE:
            self.failure_reasons.append("Both agents must be alive")
            return False
        
        min_charisma = 3
        if initiator.attributes.get("charisma", 1) < min_charisma:
            self.failure_reasons.append("Initiator lacks charisma for diplomacy")
            return False
        
        return True
    
    def calculate_success_probability(self, initiator: AgentState, target: AgentState) -> float:
        """Calculate diplomacy success probability"""
        base_prob = 0.4
        
        # Relationship factor (very important for diplomacy)
        if target.agent_id in initiator.relationships:
            rel = initiator.relationships[target.agent_id]
            base_prob += rel.strength / 100  # -1 to +1 modifier
            base_prob += rel.trust / 150     # 0 to +0.67 modifier
        
        # Charisma factor
        initiator_charisma = initiator.attributes.get("charisma", 5)
        target_charisma = target.attributes.get("charisma", 5)
        charisma_factor = (initiator_charisma - target_charisma) * 0.05
        base_prob += charisma_factor
        
        # Intelligence factor (understanding complex proposals)
        intelligence_factor = (initiator.attributes.get("intelligence", 5) - 5) * 0.03
        base_prob += intelligence_factor
        
        # Leadership skill
        leadership_skill = initiator.get_skill_level(SkillType.LEADERSHIP)
        skill_bonus = (leadership_skill - 1) * 0.04
        base_prob += skill_bonus
        
        return max(0.1, min(0.9, base_prob))
    
    def execute(self, initiator: AgentState, target: AgentState) -> InteractionResult:
        """Execute diplomatic interaction"""
        if not self.check_prerequisites(initiator, target):
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description=f"Diplomacy failed: {', '.join(self.failure_reasons)}"
            )
        
        success_prob = self.calculate_success_probability(initiator, target)
        
        if random.random() < success_prob:
            # Successful diplomacy
            relationship_type = f"diplomatic_{self.proposal_type}"
            
            initiator.update_relationship(target.agent_id, relationship_type, 15.0, 10.0)
            target.update_relationship(initiator.agent_id, relationship_type, 15.0, 10.0)
            
            # Add to group memberships if alliance
            if self.proposal_type == "alliance":
                alliance_id = f"alliance_{min(initiator.agent_id, target.agent_id)}_{max(initiator.agent_id, target.agent_id)}"
                initiator.group_memberships.add(alliance_id)
                target.group_memberships.add(alliance_id)
            
            # Add experience
            initiator.add_skill_experience(SkillType.LEADERSHIP, 12.0)
            
            # Add memories
            diplo_desc = f"Formed {self.proposal_type} with {target.name}"
            initiator.add_memory(diplo_desc, "event", 0.7, {target.agent_id})
            target.add_memory(f"Accepted {self.proposal_type} from {initiator.name}", 
                            "event", 0.7, {initiator.agent_id})
            
            return InteractionResult(
                outcome=InteractionOutcome.SUCCESS,
                description=f"Diplomatic success: {self.proposal_type} agreed between {initiator.name} and {target.name}",
                relationship_changes={
                    f"{initiator.agent_id}->{target.agent_id}": 15.0,
                    f"{target.agent_id}->{initiator.agent_id}": 15.0
                },
                reputation_changes={initiator.agent_id: 3}  # Diplomacy increases reputation
            )
        else:
            # Failed diplomacy
            initiator.update_relationship(target.agent_id, "rejected_diplomat", -5.0, -3.0)
            target.update_relationship(initiator.agent_id, "failed_diplomat", -2.0)
            
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description=f"Diplomatic failure: {target.name} rejected {self.proposal_type}",
                relationship_changes={
                    f"{initiator.agent_id}->{target.agent_id}": -5.0,
                    f"{target.agent_id}->{initiator.agent_id}": -2.0
                }
            )


class SocialInteraction(BaseInteraction):
    """Handles general social interactions"""
    
    def __init__(self, context: InteractionContext, social_type: str, content: str = ""):
        super().__init__(context)
        self.social_type = social_type  # "chat", "gossip", "joke", "compliment", "insult"
        self.content = content
    
    def check_prerequisites(self, initiator: AgentState, target: AgentState) -> bool:
        """Check if social interaction can proceed"""
        return initiator.status == AgentStatus.ALIVE and target.status == AgentStatus.ALIVE
    
    def execute(self, initiator: AgentState, target: AgentState) -> InteractionResult:
        """Execute social interaction"""
        if not self.check_prerequisites(initiator, target):
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description="Social interaction failed: One or both agents not available"
            )
        
        # Different effects based on social type
        if self.social_type == "compliment":
            initiator.update_relationship(target.agent_id, "friend", 3.0, 1.0)
            target.update_relationship(initiator.agent_id, "friend", 5.0, 2.0)
            target.morale = min(100, target.morale + 5)
            
            description = f"{initiator.name} complimented {target.name}"
            
        elif self.social_type == "insult":
            initiator.update_relationship(target.agent_id, "antagonist", -8.0, -3.0)
            target.update_relationship(initiator.agent_id, "antagonist", -10.0, -5.0)
            target.morale = max(0, target.morale - 8)
            
            description = f"{initiator.name} insulted {target.name}"
            
        elif self.social_type == "joke":
            humor_success = random.random() < 0.7  # 70% chance humor works
            if humor_success:
                initiator.update_relationship(target.agent_id, "friend", 2.0, 1.0)
                target.update_relationship(initiator.agent_id, "friend", 2.0, 1.0)
                target.morale = min(100, target.morale + 3)
                description = f"{initiator.name} told a funny joke to {target.name}"
            else:
                initiator.update_relationship(target.agent_id, "awkward_acquaintance", -1.0)
                description = f"{initiator.name}'s joke fell flat with {target.name}"
                
        elif self.social_type == "gossip":
            # Gossip about other agents
            initiator.update_relationship(target.agent_id, "confidant", 2.0, 1.0)
            target.update_relationship(initiator.agent_id, "confidant", 2.0, 1.0)
            description = f"{initiator.name} shared gossip with {target.name}"
            
        else:  # general chat
            initiator.update_relationship(target.agent_id, "acquaintance", 1.0, 0.5)
            target.update_relationship(initiator.agent_id, "acquaintance", 1.0, 0.5)
            description = f"{initiator.name} chatted with {target.name}"
        
        # Add memories for both agents
        initiator.add_memory(f"Had {self.social_type} interaction with {target.name}", 
                           "social", 0.3, {target.agent_id})
        target.add_memory(f"{initiator.name} {self.social_type} with me", 
                        "social", 0.3, {initiator.agent_id})
        
        return InteractionResult(
            outcome=InteractionOutcome.SUCCESS,
            description=description
        )


class InteractionManager:
    """Manages all interactions between agents"""
    
    def __init__(self):
        self.interaction_history: List[Tuple[InteractionContext, InteractionResult]] = []
        self.active_interactions: Dict[str, BaseInteraction] = {}
        self.interaction_handlers = {
            InteractionType.TRADE: TradeInteraction,
            InteractionType.COMBAT: CombatInteraction,
            InteractionType.DIPLOMACY: DiplomacyInteraction,
            InteractionType.SOCIAL: SocialInteraction
        }
    
    def create_trade_interaction(self, initiator_id: str, target_id: str, location: Tuple[int, int],
                                offer: Dict[str, int], request: Dict[str, int]) -> str:
        """Create a trade interaction"""
        context = InteractionContext(
            initiator_id=initiator_id,
            target_id=target_id,
            interaction_type=InteractionType.TRADE,
            location=location
        )
        
        interaction = TradeInteraction(context, offer, request)
        interaction_id = f"trade_{initiator_id}_{target_id}_{int(time.time())}"
        self.active_interactions[interaction_id] = interaction
        
        return interaction_id
    
    def create_combat_interaction(self, initiator_id: str, target_id: str, location: Tuple[int, int],
                                 combat_type: str = "physical") -> str:
        """Create a combat interaction"""
        context = InteractionContext(
            initiator_id=initiator_id,
            target_id=target_id,
            interaction_type=InteractionType.COMBAT,
            location=location
        )
        
        interaction = CombatInteraction(context, combat_type)
        interaction_id = f"combat_{initiator_id}_{target_id}_{int(time.time())}"
        self.active_interactions[interaction_id] = interaction
        
        return interaction_id
    
    def create_diplomacy_interaction(self, initiator_id: str, target_id: str, location: Tuple[int, int],
                                   proposal_type: str, terms: Dict[str, Any]) -> str:
        """Create a diplomacy interaction"""
        context = InteractionContext(
            initiator_id=initiator_id,
            target_id=target_id,
            interaction_type=InteractionType.DIPLOMACY,
            location=location
        )
        
        interaction = DiplomacyInteraction(context, proposal_type, terms)
        interaction_id = f"diplomacy_{initiator_id}_{target_id}_{int(time.time())}"
        self.active_interactions[interaction_id] = interaction
        
        return interaction_id
    
    def create_social_interaction(self, initiator_id: str, target_id: str, location: Tuple[int, int],
                                social_type: str, content: str = "") -> str:
        """Create a social interaction"""
        context = InteractionContext(
            initiator_id=initiator_id,
            target_id=target_id,
            interaction_type=InteractionType.SOCIAL,
            location=location
        )
        
        interaction = SocialInteraction(context, social_type, content)
        interaction_id = f"social_{initiator_id}_{target_id}_{int(time.time())}"
        self.active_interactions[interaction_id] = interaction
        
        return interaction_id
    
    def execute_interaction(self, interaction_id: str, initiator: AgentState, target: AgentState) -> Optional[InteractionResult]:
        """Execute an interaction and return the result"""
        if interaction_id not in self.active_interactions:
            logger.warning(f"Interaction {interaction_id} not found")
            return None
        
        interaction = self.active_interactions[interaction_id]
        
        try:
            result = interaction.execute(initiator, target)
            
            # Record in history
            self.interaction_history.append((interaction.context, result))
            
            # Clean up
            del self.active_interactions[interaction_id]
            
            logger.info(f"Executed interaction {interaction_id}: {result.description}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute interaction {interaction_id}: {e}")
            return InteractionResult(
                outcome=InteractionOutcome.FAILURE,
                description=f"Interaction failed due to error: {e}"
            )
    
    def get_interaction_history(self, agent_id: str, limit: int = 50) -> List[Tuple[InteractionContext, InteractionResult]]:
        """Get interaction history for an agent"""
        relevant_history = [
            (context, result) for context, result in self.interaction_history
            if context.initiator_id == agent_id or context.target_id == agent_id
        ]
        
        return relevant_history[-limit:]
    
    def get_reputation(self, agent_id: str) -> int:
        """Calculate agent's reputation based on interaction history"""
        reputation = 0
        
        for context, result in self.interaction_history:
            if agent_id in result.reputation_changes:
                reputation += result.reputation_changes[agent_id]
        
        return reputation
    
    def cleanup_old_interactions(self, max_age_hours: int = 24):
        """Clean up old interaction history"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        
        self.interaction_history = [
            (context, result) for context, result in self.interaction_history
            if context.timestamp > cutoff_time
        ]