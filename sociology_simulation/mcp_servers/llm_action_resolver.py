#!/usr/bin/env python3
"""
MCP Server for LLM-Driven Action Resolution

This server provides tools for the LLM to resolve complex agent actions
that require interpretation, context analysis, and outcome generation.
The LLM acts as the intelligent action interpreter while using structured tools.
"""

import asyncio
from typing import Any, Dict, List, Optional, Tuple
from mcp.server.models import InitializeResult
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource
)
import mcp.types as types
from loguru import logger


class LLMActionResolver:
    """MCP Server for LLM-driven action resolution and interpretation"""
    
    def __init__(self):
        self.server = Server("llm-action-resolver")
        self.world_reference = None
        self.bible_reference = None
        
        # Register tool handlers
        self._register_resolution_tools()
        
    def set_references(self, world, bible):
        """Set references to world and bible objects"""
        self.world_reference = world
        self.bible_reference = bible
        
    def _register_resolution_tools(self):
        """Register all action resolution tools for LLM to use"""
        
        @self.server.tool()
        async def resolve_natural_language_action(
            agent_id: int,
            natural_action: str,
            context: Dict[str, Any],
            interpretation: str,
            proposed_outcome: Dict[str, Any]
        ) -> List[types.TextContent]:
            """Resolve a natural language action using LLM interpretation
            
            Args:
                agent_id: The agent performing the action
                natural_action: The original natural language action
                context: Current game context (position, inventory, etc.)
                interpretation: LLM's interpretation of what the action means
                proposed_outcome: LLM's proposed results of the action
            
            Returns:
                Structured outcome of the action with all effects applied
            """
            try:
                agent = self._get_agent(agent_id)
                if not agent:
                    return [types.TextContent(type="text", text=f"Error: Agent {agent_id} not found")]
                
                # Validate proposed outcome against game rules
                validation_result = self._validate_outcome(agent, proposed_outcome, context)
                if not validation_result['valid']:
                    return [types.TextContent(
                        type="text", 
                        text=f"Action rejected: {validation_result['reason']}"
                    )]
                
                # Apply the LLM's proposed outcome
                final_outcome = self._apply_outcome(agent, proposed_outcome)
                
                # Log the resolution
                logger.info(f"Resolved action for agent {agent_id}: {natural_action} -> {interpretation}")
                
                # Format result
                result_text = f"Action resolved: {natural_action}\n"
                result_text += f"Interpretation: {interpretation}\n"
                result_text += f"Outcome: {final_outcome}\n"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Action resolution error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def handle_complex_social_interaction(
            initiator_id: int,
            target_id: int,
            interaction_description: str,
            emotional_context: Dict[str, Any],
            proposed_dialogue: List[str],
            relationship_effects: Dict[str, float]
        ) -> List[types.TextContent]:
            """Handle complex social interactions with rich dialogue and emotional depth
            
            Args:
                initiator_id: Agent starting the interaction
                target_id: Agent being interacted with
                interaction_description: Rich description of the interaction
                emotional_context: Emotional states, motivations, etc.
                proposed_dialogue: LLM-generated dialogue lines
                relationship_effects: How relationships should change
            
            Returns:
                Complete social interaction outcome with dialogue and relationship changes
            """
            try:
                initiator = self._get_agent(initiator_id)
                target = self._get_agent(target_id)
                
                if not initiator or not target:
                    return [types.TextContent(
                        type="text", 
                        text=f"Error: Agent not found (initiator: {initiator_id}, target: {target_id})"
                    )]
                
                # Check interaction feasibility
                distance = self._calculate_distance(initiator.pos, target.pos)
                if distance > 3:
                    return [types.TextContent(
                        type="text",
                        text=f"Agents too far apart (distance: {distance}). Social interaction requires proximity."
                    )]
                
                # Process emotional context
                emotional_impact = emotional_context.get('intensity', 1.0)
                interaction_type = emotional_context.get('type', 'neutral')
                
                # Apply relationship changes with emotional modifiers
                for agent_pair, effect in relationship_effects.items():
                    if agent_pair == f"{initiator_id}->{target_id}":
                        self._modify_relationship(initiator, target_id, effect * emotional_impact)
                    elif agent_pair == f"{target_id}->{initiator_id}":
                        self._modify_relationship(target, initiator_id, effect * emotional_impact)
                
                # Process knowledge/skill transfer if applicable
                if 'knowledge_transfer' in emotional_context:
                    knowledge = emotional_context['knowledge_transfer']
                    if knowledge.get('from_initiator_to_target'):
                        self._transfer_knowledge(initiator, target, knowledge['skills'])
                    if knowledge.get('from_target_to_initiator'):
                        self._transfer_knowledge(target, initiator, knowledge['skills'])
                
                # Create interaction log entry
                interaction_log = {
                    'participants': [initiator_id, target_id],
                    'description': interaction_description,
                    'dialogue': proposed_dialogue,
                    'emotional_context': emotional_context,
                    'relationship_changes': relationship_effects,
                    'type': interaction_type
                }
                
                # Store interaction in agent memories
                for agent in [initiator, target]:
                    if not hasattr(agent, 'social_memory'):
                        agent.social_memory = []
                    agent.social_memory.append(interaction_log)
                
                logger.info(f"Complex social interaction: {interaction_description}")
                
                # Format detailed result
                result_text = f"Social Interaction Complete:\n"
                result_text += f"Description: {interaction_description}\n"
                result_text += f"Emotional Context: {interaction_type} (intensity: {emotional_impact})\n"
                result_text += f"Dialogue:\n"
                for i, line in enumerate(proposed_dialogue):
                    speaker = "Initiator" if i % 2 == 0 else "Target"
                    result_text += f"  {speaker}: {line}\n"
                result_text += f"Relationship Effects: {relationship_effects}"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Social interaction error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def resolve_skill_development(
            agent_id: int,
            skill_name: str,
            learning_context: str,
            experience_source: str,
            innovation_level: float,
            teaching_involved: bool = False,
            teacher_id: Optional[int] = None
        ) -> List[types.TextContent]:
            """Resolve skill development and learning with rich context
            
            Args:
                agent_id: Agent developing the skill
                skill_name: Name of skill being developed
                learning_context: How/why the skill is being learned
                experience_source: What action/event triggered the learning
                innovation_level: How innovative/creative this learning is (0.0-1.0)
                teaching_involved: Whether another agent is teaching
                teacher_id: ID of teaching agent if applicable
            
            Returns:
                Skill development outcome with experience and potential innovations
            """
            try:
                agent = self._get_agent(agent_id)
                if not agent:
                    return [types.TextContent(type="text", text=f"Error: Agent {agent_id} not found")]
                
                if not hasattr(agent, 'skills'):
                    agent.skills = {}
                
                # Calculate base experience gain
                base_experience = 1.0
                
                # Modify based on context
                context_multipliers = {
                    'practice': 1.0,
                    'necessity': 1.5,
                    'experimentation': 2.0,
                    'crisis': 2.5,
                    'teaching': 1.2,
                    'discovery': 3.0
                }
                
                multiplier = 1.0
                for context_key, mult in context_multipliers.items():
                    if context_key in learning_context.lower():
                        multiplier = max(multiplier, mult)
                
                # Handle teaching
                if teaching_involved and teacher_id:
                    teacher = self._get_agent(teacher_id)
                    if teacher and hasattr(teacher, 'skills'):
                        teacher_skill_level = teacher.skills.get(skill_name, 0)
                        student_skill_level = agent.skills.get(skill_name, 0)
                        
                        if teacher_skill_level > student_skill_level:
                            # Effective teaching
                            multiplier *= 1.8
                            teaching_bonus = (teacher_skill_level - student_skill_level) * 0.1
                            base_experience += teaching_bonus
                            
                            # Teacher also gains some experience for teaching
                            teacher.skills[skill_name] = teacher.skills.get(skill_name, 0) + 0.2
                
                # Apply innovation effects
                final_experience = base_experience * multiplier * (1.0 + innovation_level)
                
                # Update skill
                current_level = agent.skills.get(skill_name, 0)
                new_level = current_level + final_experience
                agent.skills[skill_name] = new_level
                
                # Check for skill breakthrough/innovation
                innovation_result = ""
                if innovation_level > 0.7 and new_level > 5.0:
                    # High innovation might unlock related skills
                    related_skills = self._get_related_skills(skill_name)
                    for related_skill in related_skills:
                        if related_skill not in agent.skills:
                            agent.skills[related_skill] = 0.5
                            innovation_result += f" Discovered related skill: {related_skill}!"
                
                # Log skill development
                logger.info(f"Agent {agent_id} developed {skill_name}: {current_level:.2f} -> {new_level:.2f}")
                
                # Create detailed learning record
                if not hasattr(agent, 'learning_history'):
                    agent.learning_history = []
                
                learning_record = {
                    'skill': skill_name,
                    'context': learning_context,
                    'source': experience_source,
                    'innovation_level': innovation_level,
                    'experience_gained': final_experience,
                    'new_level': new_level,
                    'teaching_involved': teaching_involved,
                    'teacher_id': teacher_id
                }
                agent.learning_history.append(learning_record)
                
                result_text = f"Skill Development: {skill_name}\n"
                result_text += f"Context: {learning_context}\n"
                result_text += f"Experience Source: {experience_source}\n"
                result_text += f"Innovation Level: {innovation_level:.2f}\n"
                result_text += f"Experience Gained: {final_experience:.2f}\n"
                result_text += f"New Level: {new_level:.2f}\n"
                if teaching_involved:
                    result_text += f"Teaching by Agent {teacher_id}: Yes\n"
                result_text += innovation_result
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Skill development error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def handle_creative_action(
            agent_id: int,
            action_description: str,
            creativity_level: float,
            inspiration_source: str,
            intended_outcome: str,
            risk_level: str = "medium"
        ) -> List[types.TextContent]:
            """Handle creative/innovative actions that don't fit standard patterns
            
            Args:
                agent_id: Agent performing creative action
                action_description: Rich description of the creative attempt
                creativity_level: How creative/unprecedented this is (0.0-1.0)
                inspiration_source: What inspired this action
                intended_outcome: What the agent hopes to achieve
                risk_level: How risky this creative attempt is
            
            Returns:
                Creative action outcome with potential innovations or failures
            """
            try:
                agent = self._get_agent(agent_id)
                if not agent:
                    return [types.TextContent(type="text", text=f"Error: Agent {agent_id} not found")]
                
                # Calculate success probability based on creativity and skills
                relevant_skills = self._identify_relevant_skills(action_description, agent)
                skill_bonus = sum(agent.skills.get(skill, 0) for skill in relevant_skills) * 0.1
                
                base_success = 0.3  # Base chance for creative actions
                creativity_bonus = creativity_level * 0.4
                
                risk_modifiers = {
                    'low': 0.1, 'medium': 0.0, 'high': -0.2, 'extreme': -0.4
                }
                risk_modifier = risk_modifiers.get(risk_level, 0.0)
                
                success_chance = base_success + creativity_bonus + skill_bonus + risk_modifier
                success_chance = max(0.05, min(0.95, success_chance))  # Clamp between 5% and 95%
                
                # Determine outcome
                import random
                success = random.random() < success_chance
                
                outcome_description = ""
                effects = {}
                
                if success:
                    # Creative success
                    outcome_description = f"Creative breakthrough! {intended_outcome} achieved through {inspiration_source}."
                    
                    # Reward creativity with skill development
                    for skill in relevant_skills:
                        bonus_exp = creativity_level * 2.0
                        agent.skills[skill] = agent.skills.get(skill, 0) + bonus_exp
                        effects[f"{skill}_experience"] = bonus_exp
                    
                    # Possible invention/discovery
                    if creativity_level > 0.8:
                        invention_name = f"invented_{action_description.split()[0].lower()}"
                        if not hasattr(agent, 'inventions'):
                            agent.inventions = []
                        agent.inventions.append({
                            'name': invention_name,
                            'description': action_description,
                            'inspiration': inspiration_source
                        })
                        outcome_description += f" Invented: {invention_name}!"
                        effects['invention'] = invention_name
                
                else:
                    # Creative failure
                    failure_types = [
                        "The attempt didn't work as expected, but provided valuable learning.",
                        "Creative failure led to unexpected insights about the problem.",
                        "The approach was too ambitious for current skill level.",
                        "External factors prevented the creative breakthrough."
                    ]
                    
                    outcome_description = random.choice(failure_types)
                    
                    # Even failures provide some learning
                    for skill in relevant_skills:
                        consolation_exp = creativity_level * 0.5
                        agent.skills[skill] = agent.skills.get(skill, 0) + consolation_exp
                        effects[f"{skill}_experience"] = consolation_exp
                
                # Record creative attempt
                if not hasattr(agent, 'creative_history'):
                    agent.creative_history = []
                
                creative_record = {
                    'action': action_description,
                    'creativity_level': creativity_level,
                    'inspiration': inspiration_source,
                    'intended_outcome': intended_outcome,
                    'risk_level': risk_level,
                    'success': success,
                    'outcome': outcome_description,
                    'effects': effects
                }
                agent.creative_history.append(creative_record)
                
                logger.info(f"Creative action by agent {agent_id}: {action_description} -> {outcome_description}")
                
                result_text = f"Creative Action: {action_description}\n"
                result_text += f"Inspiration: {inspiration_source}\n"
                result_text += f"Creativity Level: {creativity_level:.2f}\n"
                result_text += f"Risk Level: {risk_level}\n"
                result_text += f"Success: {'Yes' if success else 'No'}\n"
                result_text += f"Outcome: {outcome_description}\n"
                result_text += f"Effects: {effects}"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Creative action error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
    
    def _get_agent(self, agent_id: int):
        """Get agent by ID from world"""
        if not self.world_reference or not hasattr(self.world_reference, 'agents'):
            return None
        
        for agent in self.world_reference.agents:
            if agent.aid == agent_id:
                return agent
        return None
    
    def _validate_outcome(self, agent, proposed_outcome: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that proposed outcome follows game rules"""
        try:
            # Check basic constraints
            if 'position_change' in proposed_outcome:
                new_pos = proposed_outcome['position_change']
                world_size = getattr(self.world_reference, 'size', 64)
                if not (0 <= new_pos[0] < world_size and 0 <= new_pos[1] < world_size):
                    return {'valid': False, 'reason': 'Position outside world boundaries'}
            
            if 'inventory_changes' in proposed_outcome:
                for item, change in proposed_outcome['inventory_changes'].items():
                    current_amount = getattr(agent, 'inventory', {}).get(item, 0)
                    if current_amount + change < 0:
                        return {'valid': False, 'reason': f'Insufficient {item} for proposed change'}
            
            return {'valid': True, 'reason': 'Outcome validated'}
            
        except Exception as e:
            return {'valid': False, 'reason': f'Validation error: {str(e)}'}
    
    def _apply_outcome(self, agent, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Apply the LLM's proposed outcome to the agent and world"""
        applied_effects = {}
        
        try:
            # Apply position changes
            if 'position_change' in outcome:
                new_pos = outcome['position_change']
                old_pos = agent.pos
                agent.pos = new_pos
                applied_effects['position'] = f"{old_pos} -> {new_pos}"
            
            # Apply inventory changes
            if 'inventory_changes' in outcome:
                if not hasattr(agent, 'inventory'):
                    agent.inventory = {}
                
                for item, change in outcome['inventory_changes'].items():
                    old_amount = agent.inventory.get(item, 0)
                    new_amount = max(0, old_amount + change)
                    agent.inventory[item] = new_amount
                    applied_effects[f"inventory_{item}"] = f"{old_amount} -> {new_amount}"
            
            # Apply health/energy changes
            for stat in ['health', 'energy', 'hunger']:
                if f"{stat}_change" in outcome:
                    change = outcome[f"{stat}_change"]
                    old_value = getattr(agent, stat, 100)
                    new_value = max(0, old_value + change)
                    setattr(agent, stat, new_value)
                    applied_effects[stat] = f"{old_value} -> {new_value}"
            
            # Apply skill changes
            if 'skill_changes' in outcome:
                if not hasattr(agent, 'skills'):
                    agent.skills = {}
                
                for skill, change in outcome['skill_changes'].items():
                    old_level = agent.skills.get(skill, 0)
                    new_level = max(0, old_level + change)
                    agent.skills[skill] = new_level
                    applied_effects[f"skill_{skill}"] = f"{old_level:.2f} -> {new_level:.2f}"
            
            return applied_effects
            
        except Exception as e:
            logger.error(f"Error applying outcome: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate distance between two positions"""
        return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
    
    def _modify_relationship(self, agent, target_id: int, change: float):
        """Modify relationship between agents"""
        if not hasattr(agent, 'relationships'):
            agent.relationships = {}
        
        current = agent.relationships.get(target_id, 0)
        agent.relationships[target_id] = max(-10, min(10, current + change))
    
    def _transfer_knowledge(self, from_agent, to_agent, skills: List[str]):
        """Transfer knowledge/skills between agents"""
        if not hasattr(from_agent, 'skills') or not hasattr(to_agent, 'skills'):
            return
        
        for skill in skills:
            if skill in from_agent.skills:
                teacher_level = from_agent.skills[skill]
                student_level = to_agent.skills.get(skill, 0)
                
                if teacher_level > student_level:
                    # Transfer some knowledge
                    transfer_amount = min(0.5, (teacher_level - student_level) * 0.2)
                    to_agent.skills[skill] = student_level + transfer_amount
    
    def _get_related_skills(self, skill_name: str) -> List[str]:
        """Get skills related to the given skill"""
        skill_relationships = {
            'gathering': ['foraging', 'botany', 'survival'],
            'crafting': ['engineering', 'creativity', 'tool_making'],
            'hunting': ['tracking', 'survival', 'weapon_use'],
            'social': ['leadership', 'diplomacy', 'teaching'],
            'exploration': ['navigation', 'cartography', 'courage']
        }
        
        return skill_relationships.get(skill_name, [])
    
    def _identify_relevant_skills(self, action_description: str, agent) -> List[str]:
        """Identify which skills are relevant to an action"""
        action_lower = action_description.lower()
        relevant = []
        
        if not hasattr(agent, 'skills'):
            return relevant
        
        skill_keywords = {
            'crafting': ['craft', 'make', 'build', 'create', 'construct'],
            'gathering': ['collect', 'gather', 'harvest', 'pick'],
            'social': ['talk', 'speak', 'convince', 'negotiate', 'lead'],
            'exploration': ['explore', 'discover', 'search', 'navigate'],
            'survival': ['survive', 'adapt', 'endure', 'overcome']
        }
        
        for skill, keywords in skill_keywords.items():
            if skill in agent.skills and any(keyword in action_lower for keyword in keywords):
                relevant.append(skill)
        
        return relevant


async def main():
    """Run the LLM Action Resolver MCP server"""
    server_instance = LLMActionResolver()
    
    # Setup server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializeResult(
                server_name="llm-action-resolver",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())