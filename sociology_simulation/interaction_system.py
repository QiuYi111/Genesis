"""Enhanced interaction and communication system"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from loguru import logger
import random

if TYPE_CHECKING:
    from .agent import Agent
    from .world import World

@dataclass
class Interaction:
    """Represents a complex interaction between agents"""
    interaction_id: str
    interaction_type: str  # "negotiation", "teaching", "trade", "conflict", "cooperation"
    participants: List[int]  # Agent IDs
    initiator_id: int
    turn_created: int
    duration: int = 1  # How many turns this interaction lasts
    status: str = "active"  # "active", "completed", "failed", "cancelled"
    context: Dict = field(default_factory=dict)  # Context-specific data
    outcomes: List[str] = field(default_factory=list)  # Results of the interaction
    
    def add_outcome(self, outcome: str):
        """Add an outcome to this interaction"""
        self.outcomes.append(outcome)


@dataclass
class CommunicationNetwork:
    """Represents information flow in the society"""
    rumors: List[Dict] = field(default_factory=list)  # Information spreading
    news: List[Dict] = field(default_factory=list)  # Important events
    gossip: Dict[int, List[str]] = field(default_factory=dict)  # Agent-specific gossip
    information_hubs: Set[int] = field(default_factory=set)  # Agents who spread info well


class InteractionSystem:
    """Manages complex agent interactions and communication"""
    
    def __init__(self):
        self.active_interactions: Dict[str, Interaction] = {}
        self.completed_interactions: List[Interaction] = []
        self.communication_network = CommunicationNetwork()
        self.next_interaction_id = 1
        self.interaction_cooldowns: Dict[tuple, int] = {}  # (agent1, agent2) -> turns
        
    def initiate_interaction(self, initiator: 'Agent', target: 'Agent', 
                           interaction_type: str, context: Dict, 
                           turn: int) -> Optional[Interaction]:
        """Initiate a complex interaction between agents"""
        # Check cooldown
        agent_pair = tuple(sorted([initiator.aid, target.aid]))
        if agent_pair in self.interaction_cooldowns:
            if self.interaction_cooldowns[agent_pair] > 0:
                return None
        
        interaction_id = f"interaction_{self.next_interaction_id}"
        self.next_interaction_id += 1
        
        interaction = Interaction(
            interaction_id=interaction_id,
            interaction_type=interaction_type,
            participants=[initiator.aid, target.aid],
            initiator_id=initiator.aid,
            turn_created=turn,
            context=context
        )
        
        # Set duration based on interaction type
        duration_map = {
            "negotiation": 2,
            "teaching": 3,
            "trade": 1,
            "conflict": random.randint(1, 3),
            "cooperation": random.randint(2, 5)
        }
        interaction.duration = duration_map.get(interaction_type, 1)
        
        self.active_interactions[interaction_id] = interaction
        
        # Set cooldown
        self.interaction_cooldowns[agent_pair] = interaction.duration + 1
        
        logger.info(f"Interaction started: {interaction_type} between {initiator.aid} and {target.aid}")
        return interaction
    
    def process_interactions(self, world: 'World', turn: int):
        """Process all active interactions"""
        completed = []
        agents_dict = {agent.aid: agent for agent in world.agents}
        
        for interaction_id, interaction in self.active_interactions.items():
            interaction.duration -= 1
            
            if interaction.duration <= 0:
                # Complete the interaction
                self._complete_interaction(interaction, agents_dict, world, turn)
                completed.append(interaction_id)
            else:
                # Continue the interaction
                self._continue_interaction(interaction, agents_dict, world, turn)
        
        # Remove completed interactions
        for interaction_id in completed:
            interaction = self.active_interactions.pop(interaction_id)
            self.completed_interactions.append(interaction)
        
        # Decrease cooldowns
        for agent_pair in list(self.interaction_cooldowns.keys()):
            self.interaction_cooldowns[agent_pair] -= 1
            if self.interaction_cooldowns[agent_pair] <= 0:
                del self.interaction_cooldowns[agent_pair]
    
    def _complete_interaction(self, interaction: Interaction, agents_dict: Dict, 
                            world: 'World', turn: int):
        """Complete an interaction and apply results"""
        interaction.status = "completed"
        
        participants = [agents_dict[aid] for aid in interaction.participants 
                       if aid in agents_dict]
        
        if len(participants) < 2:
            interaction.status = "failed"
            return
        
        if interaction.interaction_type == "negotiation":
            self._complete_negotiation(interaction, participants, world)
        elif interaction.interaction_type == "teaching":
            self._complete_teaching(interaction, participants, world)
        elif interaction.interaction_type == "trade":
            self._complete_trade(interaction, participants, world)
        elif interaction.interaction_type == "conflict":
            self._complete_conflict(interaction, participants, world)
        elif interaction.interaction_type == "cooperation":
            self._complete_cooperation(interaction, participants, world)
        
        # Update relationships
        for i, agent1 in enumerate(participants):
            for agent2 in participants[i+1:]:
                if interaction.status == "completed":
                    # Successful interactions strengthen relationships
                    relationship_type = "ally" if interaction.interaction_type == "cooperation" else "acquaintance"
                    agent1.add_social_connection(agent2.aid, relationship_type, 2)
                    agent2.add_social_connection(agent1.aid, relationship_type, 2)
                else:
                    # Failed interactions may weaken relationships
                    if agent2.aid in agent1.social_connections:
                        agent1.social_connections[agent2.aid]["strength"] = max(1, 
                            agent1.social_connections[agent2.aid]["strength"] - 1)
    
    def _complete_negotiation(self, interaction: Interaction, participants: List['Agent'], world: 'World'):
        """Complete a negotiation interaction"""
        agent1, agent2 = participants[0], participants[1]
        context = interaction.context
        
        # Calculate negotiation success based on social skills and relationship
        success_chance = 0.5  # Base 50%
        
        # Social skills affect negotiation
        for agent in participants:
            social_skill = agent.get_skill_level("social") if hasattr(agent, 'get_skill_level') else 0
            leadership_skill = agent.get_skill_level("leadership") if hasattr(agent, 'get_skill_level') else 0
            success_chance += (social_skill + leadership_skill) * 0.02
        
        # Existing relationship affects success
        if agent2.aid in agent1.social_connections:
            relationship_strength = agent1.social_connections[agent2.aid]["strength"]
            success_chance += relationship_strength * 0.01
        
        if random.random() < success_chance:
            # Successful negotiation
            topic = context.get("topic", "mutual agreement")
            interaction.add_outcome(f"Successful negotiation on {topic}")
            
            for agent in participants:
                agent.log.append(f"成功与智能体{[p.aid for p in participants if p != agent]}协商: {topic}")
                # Gain social experience
                if hasattr(agent, 'modify_skill'):
                    agent.modify_skill("social", 0, 5)
            
            # Create information spread
            self._spread_information(f"智能体{agent1.aid}和{agent2.aid}达成了协议", world, participants)
        else:
            interaction.status = "failed"
            interaction.add_outcome("Negotiation failed")
            for agent in participants:
                agent.log.append("协商失败")
    
    def _complete_teaching(self, interaction: Interaction, participants: List['Agent'], world: 'World'):
        """Complete a teaching interaction"""
        teacher = participants[0]  # Initiator is teacher
        student = participants[1]
        context = interaction.context
        
        skill_to_teach = context.get("skill")
        knowledge_to_teach = context.get("knowledge")
        
        if skill_to_teach and hasattr(teacher, 'get_skill_level'):
            teacher_level = teacher.get_skill_level(skill_to_teach)
            student_level = student.get_skill_level(skill_to_teach) if hasattr(student, 'get_skill_level') else 0
            
            if teacher_level > student_level:
                # Attempt skill transfer
                learning_chance = 0.4 + (teacher_level - student_level) * 0.1
                learning_chance += teacher.get_skill_level("social") * 0.02
                learning_chance += (student.attributes.get("curiosity", 5) - 5) * 0.02
                
                if random.random() < learning_chance:
                    # Successful teaching
                    if hasattr(student, 'modify_skill'):
                        student.modify_skill(skill_to_teach, 1, 0)
                    
                    interaction.add_outcome(f"Successfully taught {skill_to_teach}")
                    teacher.log.append(f"成功教授{student.name}: {skill_to_teach}")
                    student.log.append(f"从{teacher.name}学会了{skill_to_teach}")
                    
                    # Teacher gains teaching reputation
                    teacher.reputation["wise"] = teacher.reputation.get("wise", 0) + 5
        
        if knowledge_to_teach:
            # Use cultural memory system for knowledge transfer
            success = world.cultural_memory.attempt_learning(student, teacher, knowledge_to_teach)
            if success:
                interaction.add_outcome(f"Successfully taught knowledge: {knowledge_to_teach}")
    
    def _complete_trade(self, interaction: Interaction, participants: List['Agent'], world: 'World'):
        """Complete a trade interaction"""
        trader1, trader2 = participants[0], participants[1]
        context = interaction.context
        
        offer = context.get("offer", {})
        request = context.get("request", {})
        
        # Check if both parties can fulfill the trade
        can_trade = True
        for item, amount in offer.items():
            if trader1.inventory.get(item, 0) < amount:
                can_trade = False
                break
        
        for item, amount in request.items():
            if trader2.inventory.get(item, 0) < amount:
                can_trade = False
                break
        
        if can_trade and random.random() < 0.8:  # 80% success rate for valid trades
            # Execute trade
            for item, amount in offer.items():
                trader1.inventory[item] -= amount
                trader2.inventory[item] = trader2.inventory.get(item, 0) + amount
            
            for item, amount in request.items():
                trader2.inventory[item] -= amount
                trader1.inventory[item] = trader1.inventory.get(item, 0) + amount
            
            interaction.add_outcome(f"Trade completed: {offer} for {request}")
            trader1.log.append(f"与{trader2.name}交易: 给出{offer}，获得{request}")
            trader2.log.append(f"与{trader1.name}交易: 给出{request}，获得{offer}")
            
            # Spread trade information
            self._spread_information(f"智能体{trader1.aid}和{trader2.aid}进行了交易", world, participants)
        else:
            interaction.status = "failed"
            interaction.add_outcome("Trade failed")
    
    def _complete_conflict(self, interaction: Interaction, participants: List['Agent'], world: 'World'):
        """Complete a conflict interaction"""
        agent1, agent2 = participants[0], participants[1]
        
        # Calculate conflict outcome based on combat skills and attributes
        agent1_power = (agent1.attributes.get("strength", 5) + 
                       agent1.get_skill_level("combat") * 2 if hasattr(agent1, 'get_skill_level') else 0)
        agent2_power = (agent2.attributes.get("strength", 5) + 
                       agent2.get_skill_level("combat") * 2 if hasattr(agent2, 'get_skill_level') else 0)
        
        # Add randomness
        agent1_roll = agent1_power + random.randint(1, 10)
        agent2_roll = agent2_power + random.randint(1, 10)
        
        if agent1_roll > agent2_roll:
            winner, loser = agent1, agent2
        else:
            winner, loser = agent2, agent1
        
        # Apply conflict results
        damage = random.randint(5, 15)
        loser.health = max(10, loser.health - damage)
        
        # Winner might gain some resources from loser
        if loser.inventory:
            stolen_item = random.choice(list(loser.inventory.keys()))
            if loser.inventory[stolen_item] > 0:
                stolen_amount = min(loser.inventory[stolen_item], random.randint(1, 3))
                loser.inventory[stolen_item] -= stolen_amount
                winner.inventory[stolen_item] = winner.inventory.get(stolen_item, 0) + stolen_amount
        
        interaction.add_outcome(f"Conflict won by {winner.aid}")
        winner.log.append(f"与{loser.name}冲突并获胜")
        loser.log.append(f"与{winner.name}冲突并失败，损失了{damage}生命值")
        
        # Spread conflict news
        self._spread_information(f"智能体{winner.aid}和{loser.aid}发生了冲突", world, participants)
        
        # Weaken relationship
        winner.add_social_connection(loser.aid, "enemy", -2)
        loser.add_social_connection(winner.aid, "enemy", -2)
    
    def _complete_cooperation(self, interaction: Interaction, participants: List['Agent'], world: 'World'):
        """Complete a cooperation interaction"""
        context = interaction.context
        project_type = context.get("project", "joint_venture")
        
        # Calculate cooperation success
        combined_skills = 0
        for agent in participants:
            for skill_name, skill_data in agent.skills.items():
                combined_skills += skill_data.get("level", 1)
        
        success_chance = min(0.9, 0.3 + combined_skills * 0.02)
        
        if random.random() < success_chance:
            # Successful cooperation
            benefits = self._calculate_cooperation_benefits(participants, project_type)
            
            for agent in participants:
                for benefit_type, amount in benefits.items():
                    if benefit_type in agent.inventory:
                        agent.inventory[benefit_type] += amount
                    elif benefit_type == "reputation":
                        agent.reputation["trustworthy"] = agent.reputation.get("trustworthy", 0) + amount
                
                agent.log.append(f"与其他智能体合作完成了{project_type}")
            
            interaction.add_outcome(f"Successful cooperation: {project_type}")
            
            # Spread success story
            participant_ids = [str(p.aid) for p in participants]
            self._spread_information(f"智能体{','.join(participant_ids)}合作成功", world, participants)
        else:
            interaction.status = "failed"
            interaction.add_outcome("Cooperation failed")
    
    def _calculate_cooperation_benefits(self, participants: List['Agent'], project_type: str) -> Dict[str, int]:
        """Calculate benefits from successful cooperation"""
        base_benefits = {"reputation": 5}
        
        if project_type == "resource_gathering":
            base_benefits.update({"wood": 2, "stone": 1})
        elif project_type == "construction":
            base_benefits.update({"reputation": 10})
        elif project_type == "exploration":
            base_benefits.update({"knowledge": 1, "reputation": 3})
        
        # Scale benefits by number of participants
        scale_factor = min(2.0, len(participants) / 2)
        return {k: int(v * scale_factor) for k, v in base_benefits.items()}
    
    def _continue_interaction(self, interaction: Interaction, agents_dict: Dict, 
                            world: 'World', turn: int):
        """Continue an ongoing interaction"""
        # For multi-turn interactions, add intermediate effects
        participants = [agents_dict[aid] for aid in interaction.participants 
                       if aid in agents_dict]
        
        if interaction.interaction_type == "teaching":
            # Ongoing learning process
            for agent in participants:
                agent.log.append("继续学习过程...")
        elif interaction.interaction_type == "cooperation":
            # Ongoing project work
            for agent in participants:
                agent.log.append("继续合作项目...")
    
    def _spread_information(self, information: str, world: 'World', originators: List['Agent']):
        """Spread information through the communication network"""
        # Add to news
        self.communication_network.news.append({
            "content": information,
            "turn": world.trinity.turn,
            "originators": [agent.aid for agent in originators]
        })
        
        # Spread to nearby agents
        for agent in world.agents:
            if agent in originators:
                continue
            
            # Check if agent is nearby any originator
            is_nearby = False
            for originator in originators:
                distance = max(abs(agent.pos[0] - originator.pos[0]), 
                             abs(agent.pos[1] - originator.pos[1]))
                if distance <= 4:  # Information spread radius
                    is_nearby = True
                    break
            
            if is_nearby and random.random() < 0.3:  # 30% chance to hear news
                agent.log.append(f"听说: {information}")
    
    def suggest_interactions(self, world: 'World', turn: int) -> List[Dict]:
        """Suggest potential interactions between agents"""
        suggestions = []
        
        for agent in world.agents:
            # Skip if agent is already in an interaction
            if any(agent.aid in interaction.participants 
                  for interaction in self.active_interactions.values()):
                continue
            
            # Find nearby agents for potential interactions
            nearby_agents = []
            for other_agent in world.agents:
                if other_agent.aid == agent.aid:
                    continue
                
                distance = max(abs(agent.pos[0] - other_agent.pos[0]), 
                             abs(agent.pos[1] - other_agent.pos[1]))
                if distance <= 3:  # Interaction range
                    nearby_agents.append(other_agent)
            
            if not nearby_agents:
                continue
            
            # Suggest interactions based on agent characteristics and needs
            for target in nearby_agents:
                # Skip if these agents are in cooldown
                agent_pair = tuple(sorted([agent.aid, target.aid]))
                if agent_pair in self.interaction_cooldowns:
                    continue
                
                # Teaching opportunities
                if hasattr(agent, 'skills') and hasattr(target, 'skills'):
                    agent_can_teach = any(agent.get_skill_level(skill) > target.get_skill_level(skill) + 1
                                        for skill in agent.skills.keys() if skill in target.skills)
                    if agent_can_teach and agent.get_skill_level("social") >= 3:
                        suggestions.append({
                            "initiator": agent,
                            "target": target,
                            "type": "teaching",
                            "context": {"skill": "crafting"},  # Example skill
                            "priority": 0.3
                        })
                
                # Trade opportunities
                if agent.inventory and target.inventory:
                    # Simple trade suggestion logic
                    agent_has = set(k for k, v in agent.inventory.items() if v > 1)
                    target_has = set(k for k, v in target.inventory.items() if v > 1)
                    if agent_has and target_has and agent_has != target_has:
                        suggestions.append({
                            "initiator": agent,
                            "target": target,
                            "type": "trade",
                            "context": {
                                "offer": {random.choice(list(agent_has)): 1},
                                "request": {random.choice(list(target_has)): 1}
                            },
                            "priority": 0.2
                        })
                
                # Cooperation opportunities
                if (agent.group_id == target.group_id and agent.group_id is not None) or \
                   (target.aid in agent.social_connections and 
                    agent.social_connections[target.aid]["strength"] >= 5):
                    suggestions.append({
                        "initiator": agent,
                        "target": target,
                        "type": "cooperation",
                        "context": {"project": "resource_gathering"},
                        "priority": 0.4
                    })
        
        # Sort by priority and return top suggestions
        suggestions.sort(key=lambda x: x["priority"], reverse=True)
        return suggestions[:5]  # Return top 5 suggestions