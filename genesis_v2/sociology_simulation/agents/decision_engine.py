"""
LLM-powered decision engine for Project Genesis agents.
Provides intelligent decision-making based on context, memory, and goals.
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import random

from ..llm.providers.base import LLMProvider, ActionDecision, SocialInteraction, GoalSetting
from .memory import SemanticMemorySystem, MemoryContext
from .base import Agent, AgentState


@dataclass
class DecisionContext:
    """Complete context for agent decision making"""
    agent: Agent
    world_state: Dict[str, Any]
    nearby_agents: List[Dict[str, Any]]
    visible_resources: Dict[str, List[Tuple[int, int, float]]]
    current_terrain: str
    weather: Dict[str, float]
    recent_events: List[Dict[str, Any]]
    memory_context: MemoryContext
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent.get_state_summary(),
            "world_state": self.world_state,
            "nearby_agents": self.nearby_agents,
            "visible_resources": {
                resource: [(x, y, round(amt, 2)) for x, y, amt in positions]
                for resource, positions in self.visible_resources.items()
            },
            "current_terrain": self.current_terrain,
            "weather": self.weather,
            "recent_events": self.recent_events[-5:]  # Last 5 events
        }


class LLMDecisionEngine:
    """Advanced LLM-powered decision engine for agents"""
    
    def __init__(self, llm_provider: LLMProvider, memory_system: SemanticMemorySystem):
        self.llm_provider = llm_provider
        self.memory_system = memory_system
        self.decision_history: List[Dict[str, Any]] = []
    
    async def make_decision(
        self, 
        agent: Agent, 
        context: DecisionContext
    ) -> Dict[str, Any]:
        """Make intelligent decision using LLM"""
        
        # Build comprehensive context
        system_prompt = self._build_system_prompt(agent)
        user_prompt = self._build_user_prompt(agent, context)
        
        # Get relevant memories
        memory_context = self._build_memory_context(agent, context)
        memory_summary = self.memory_system.get_context_summary(memory_context)
        
        # Create messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prompt}\n\nRelevant memories:\n{memory_summary}"}
        ]
        
        try:
            # Get LLM decision
            decision = await self.llm_provider.generate_response(
                messages,
                ActionDecision,
                temperature=0.7,
                max_tokens=300
            )
            
            # Validate and enhance decision
            enhanced_decision = self._enhance_decision(decision, agent, context)
            
            # Record decision
            self._record_decision(agent, enhanced_decision, context)
            
            return enhanced_decision
            
        except Exception as e:
            # Fallback to simple decision making
            return await self._fallback_decision(agent, context)
    
    def _build_system_prompt(self, agent: Agent) -> str:
        """Build comprehensive system prompt for agent personality"""
        
        return f"""You are {agent.name}, an intelligent agent in a primitive society simulation. Your role is to make thoughtful decisions that balance survival, social relationships, and long-term goals.

**Your Identity:**
- Name: {agent.name}
- Life Goals: {', '.join(agent.life_goals)}
- Current Skills: {list(agent.skills.keys())}

**Personality Traits:**
Based on your attributes:
- Health: {agent.attributes['health'].current:.0f}/100 - {'Robust' if agent.attributes['health'].current > 80 else 'Average' if agent.attributes['health'].current > 50 else 'Weak'}
- Intelligence: {agent.attributes['intelligence'].current:.0f}/20 - {'Quick-thinking' if agent.attributes['intelligence'].current > 15 else 'Average' if agent.attributes['intelligence'].current > 10 else 'Simple-minded'}
- Strength: {agent.attributes['strength'].current:.0f}/20 - {'Physically capable' if agent.attributes['strength'].current > 15 else 'Average' if agent.attributes['strength'].current > 10 else 'Physically weak'}
- Charisma: {agent.attributes['charisma'].current:.0f}/20 - {'Socially adept' if agent.attributes['charisma'].current > 15 else 'Average' if agent.attributes['charisma'].current > 10 else 'Socially awkward'}

**Decision Making Principles:**
1. **Survival First**: Ensure basic needs (food, water, shelter) before luxury
2. **Social Intelligence**: Build relationships and consider group dynamics
3. **Resource Efficiency**: Use resources wisely, plan for future
4. **Risk Assessment**: Weigh risks vs rewards carefully
5. **Learning**: Improve skills through practice and observation
6. **Goal Alignment**: Make decisions that advance your life goals

**Behavior Guidelines:**
- Consider both immediate needs and long-term consequences
- Learn from past experiences and adapt strategies
- Balance individual needs with community benefits
- Use tools and skills effectively
- Plan ahead for seasonal/resource changes

**Response Format:**
Always provide:
- **action**: The specific action to take
- **reasoning**: Detailed explanation of why this action is optimal
- **target_position**: If moving, where to go
- **target_agent**: If interacting, with whom
- **resource_target**: If gathering, what resource
- **urgency**: How urgent this action is (0-1)
- **expected_outcome**: What you expect to achieve

Think step-by-step about your decision, considering your current state, resources, relationships, and environment."""

    def _build_user_prompt(self, agent: Agent, context: DecisionContext) -> str:
        """Build detailed context prompt for current situation"""
        
        # Critical needs assessment
        critical_needs = []
        if agent.needs['hunger'].current > 80:
            critical_needs.append(f"CRITICAL HUNGER: {agent.needs['hunger'].current:.0f}/100")
        if agent.needs['thirst'].current > 80:
            critical_needs.append(f"CRITICAL THIRST: {agent.needs['thirst'].current:.0f}/100")
        if agent.needs['fatigue'].current > 90:
            critical_needs.append(f"CRITICAL FATIGUE: {agent.needs['fatigue'].current:.0f}/100")
        
        # Resource assessment
        inventory_summary = []
        for item in agent.inventory.values():
            inventory_summary.append(f"{item.name}: {item.quantity}")
        
        # Nearby agents
        nearby_summary = []
        for other in context.nearby_agents:
            relationship = agent.social_connections.get(other['id'], 0.0)
            relationship_desc = "friend" if relationship > 0.5 else "neutral" if relationship > -0.5 else "rival"
            nearby_summary.append(f"{other['name']} ({relationship_desc}) at distance {other['distance']}")
        
        # Resource opportunities
        resource_opportunities = []
        for resource, positions in context.visible_resources.items():
            if positions:
                closest = min(positions, key=lambda p: abs(p[0] - agent.position[0]) + abs(p[1] - agent.position[1]))
                distance = abs(closest[0] - agent.position[0]) + abs(closest[1] - agent.position[1])
                resource_opportunities.append(f"{resource}: {len(positions)} locations, closest at {distance} tiles")
        
        return f"""**Current Situation Analysis:**

**Position:** {agent.position} (Terrain: {context.current_terrain})
**Time:** Turn {context.world_state.get('time', 0)}
**Weather:** Temperature {context.weather.get('temperature', 20):.1f}°C, Humidity {context.weather.get('humidity', 50):.1f}%

**Critical Status:**
{chr(10).join(critical_needs) if critical_needs else "No critical needs"}

**Current State:**
- Health: {agent.attributes['health'].current:.0f}/100
- Hunger: {agent.needs['hunger'].current:.0f}/100
- Thirst: {agent.needs['thirst'].current:.0f}/100
- Fatigue: {agent.needs['fatigue'].current:.0f}/100
- Social: {agent.needs['social'].current:.0f}/100

**Inventory:**
{chr(10).join(inventory_summary) if inventory_summary else "Empty"}
Total weight: {agent.current_inventory_weight:.1f}/{agent.max_inventory_weight:.1f}kg

**Nearby Agents:**
{chr(10).join(nearby_summary) if nearby_summary else "No agents nearby"}

**Resource Opportunities:**
{chr(10).join(resource_opportunities) if resource_opportunities else "No visible resources"}

**Skills:** {', '.join([f"{skill}:{prof:.2f}" for skill, prof in agent.skills.items() if prof > 0.1])}

**Current Goal:** {agent.current_goal.description if agent.current_goal else "None"}

**Recent Events:**
{chr(10).join([f"- {event.get('description', 'Unknown event')}" for event in context.recent_events[-3:]])}

**Decision Task:**
Based on your current state, available resources, nearby agents, and your life goals, what is the most optimal action to take right now?

Consider:
1. Immediate survival needs
2. Resource efficiency
3. Social opportunities/threats
4. Skill development
5. Progress toward goals
6. Environmental factors

Provide a detailed decision with clear reasoning."""

    def _build_memory_context(self, agent: Agent, context: DecisionContext) -> MemoryContext:
        """Build memory context for relevant memory retrieval"""
        return MemoryContext(
            current_position=agent.position,
            current_time=context.world_state.get('time', 0),
            nearby_agents=[a['id'] for a in context.nearby_agents],
            current_goals=[agent.current_goal.description] if agent.current_goal else [],
            emotional_state={
                'hunger': agent.needs['hunger'].current / 100,
                'thirst': agent.needs['thirst'].current / 100,
                'fatigue': agent.needs['fatigue'].current / 100
            },
            urgency=max([
                agent.needs['hunger'].current / 100,
                agent.needs['thirst'].current / 100,
                agent.needs['fatigue'].current / 100
            ])
        )
    
    def _enhance_decision(self, decision: ActionDecision, agent: Agent, context: DecisionContext) -> Dict[str, Any]:
        """Enhance and validate LLM decision"""
        
        enhanced = {
            "action": decision.action,
            "reasoning": decision.reasoning,
            "urgency": decision.urgency,
            "expected_outcome": decision.expected_outcome,
            "original_decision": decision.dict()
        }
        
        # Validate position
        if decision.target_position:
            x, y = decision.target_position
            if 0 <= x < context.world_state.get('width', 64) and 0 <= y < context.world_state.get('height', 64):
                enhanced["target_position"] = (x, y)
            else:
                enhanced["target_position"] = agent.position
                enhanced["reasoning"] += " (adjusted position to stay within bounds)"
        
        # Validate resource
        if decision.resource_target:
            valid_resources = list(context.visible_resources.keys())
            if decision.resource_target not in valid_resources:
                if valid_resources:
                    enhanced["resource_target"] = max(valid_resources, key=lambda r: len(context.visible_resources[r]))
                    enhanced["reasoning"] += f" (adjusted resource target to {enhanced['resource_target']})"
                else:
                    enhanced["resource_target"] = None
                    enhanced["action"] = "explore"
        
        # Validate target agent
        if decision.target_agent:
            valid_agents = [a['id'] for a in context.nearby_agents]
            if decision.target_agent not in valid_agents:
                if valid_agents:
                    enhanced["target_agent"] = min(valid_agents, key=lambda a_id: 
                        next(a['distance'] for a in context.nearby_agents if a['id'] == a_id)
                    )
                    enhanced["reasoning"] += f" (adjusted target to nearby agent {enhanced['target_agent']})"
                else:
                    enhanced["target_agent"] = None
                    enhanced["action"] = "explore"
        
        return enhanced
    
    async def _fallback_decision(self, agent: Agent, context: DecisionContext) -> Dict[str, Any]:
        """Simple fallback decision when LLM fails"""
        
        # Priority-based decision making
        if agent.needs['hunger'].current > 80:
            return {
                "action": "gather",
                "resource": "food",
                "reasoning": "Critical hunger - must find food immediately",
                "urgency": 0.9,
                "expected_outcome": "Reduce hunger and maintain survival"
            }
        
        elif agent.needs['thirst'].current > 80:
            return {
                "action": "gather",
                "resource": "water",
                "reasoning": "Critical thirst - must find water immediately",
                "urgency": 0.9,
                "expected_outcome": "Reduce thirst and maintain survival"
            }
        
        elif agent.needs['fatigue'].current > 90:
            return {
                "action": "rest",
                "reasoning": "Critical fatigue - need to rest",
                "urgency": 0.8,
                "expected_outcome": "Reduce fatigue and recover energy"
            }
        
        elif agent.current_inventory_weight < 10:
            return {
                "action": "gather",
                "resource": "food",
                "reasoning": "Low inventory - gather basic resources",
                "urgency": 0.4,
                "expected_outcome": "Stock up on basic resources"
            }
        
        else:
            # Explore nearby
            valid_moves = []
            if hasattr(agent, 'world') and agent.world:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    new_x, new_y = agent.position[0] + dx, agent.position[1] + dy
                    if 0 <= new_x < agent.world.width and 0 <= new_y < agent.world.height:
                        valid_moves.append((new_x, new_y))
            
            if valid_moves:
                target = random.choice(valid_moves)
                return {
                    "action": "move",
                    "target_position": target,
                    "reasoning": "Exploring nearby area to find resources",
                    "urgency": 0.3,
                    "expected_outcome": "Discover new resources or opportunities"
                }
            else:
                return {
                    "action": "rest",
                    "reasoning": "No valid moves available, conserving energy",
                    "urgency": 0.1,
                    "expected_outcome": "Maintain current state"
                }
    
    def _record_decision(self, agent: Agent, decision: Dict[str, Any], context: DecisionContext):
        """Record decision for analysis and learning"""
        self.decision_history.append({
            "timestamp": context.world_state.get('time', 0),
            "agent_id": agent.id,
            "agent_name": agent.name,
            "decision": decision,
            "agent_state": agent.get_state_summary(),
            "context_hash": hash(json.dumps(context.to_dict(), sort_keys=True))
        })
    
    async def make_social_decision(
        self,
        agent: Agent,
        target_agent: Agent,
        context: DecisionContext
    ) -> Dict[str, Any]:
        """Make social interaction decision"""
        
        # Build social context
        relationship = agent.social_connections.get(target_agent.id, 0.0)
        
        system_prompt = f"""You are {agent.name} considering social interaction with {target_agent.name}.

**Relationship Status:** {relationship:.2f} ({'Friends' if relationship > 0.5 else 'Neutral' if relationship > -0.5 else 'Rivals'})

**Social Guidelines:**
- Build positive relationships through cooperation
- Share resources when possible
- Resolve conflicts peacefully
- Trade beneficial items
- Form alliances for mutual benefit

Consider the current situation and what would be the most beneficial interaction."""
        
        user_prompt = f"""**Current Social Context:**
- Your needs: hunger={agent.needs['hunger'].current:.0f}, thirst={agent.needs['thirst'].current:.0f}
- Their needs: hunger={target_agent.needs['hunger'].current:.0f}, thirst={target_agent.needs['thirst'].current:.0f}
- Your inventory: {len(agent.inventory)} items
- Their inventory: {len(target_agent.inventory)} items
- Distance: {abs(agent.position[0] - target_agent.position[0]) + abs(agent.position[1] - target_agent.position[1])} tiles

**Interaction Decision:**
What type of social interaction would be most beneficial? Consider:
1. Current relationship level
2. Resource trading opportunities
3. Cooperation benefits
4. Conflict resolution needs

Choose from: greet, trade, share, cooperate, conflict_resolution"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            interaction = await self.llm_provider.generate_response(
                messages,
                SocialInteraction,
                temperature=0.8,
                max_tokens=200
            )
            
            return {
                "interaction_type": interaction.interaction_type,
                "target_agent": target_agent.id,
                "message": interaction.message,
                "offer_items": interaction.offer_items,
                "request_items": interaction.request_items,
                "reasoning": interaction.reasoning or "Social interaction decision"
            }
            
        except Exception as e:
            return {
                "interaction_type": "greet",
                "target_agent": target_agent.id,
                "message": "Hello",
                "reasoning": f"Fallback greeting due to LLM error: {str(e)}"
            }
    
    async def set_new_goal(
        self,
        agent: Agent,
        context: DecisionContext
    ) -> Dict[str, Any]:
        """Set new life goal using LLM"""
        
        system_prompt = f"""You are {agent.name} setting new life goals based on your experiences and current situation.

**Current Life Goals:** {', '.join(agent.life_goals)}
**Skills:** {', '.join([f"{skill}:{prof:.2f}" for skill, prof in agent.skills.items() if prof > 0.1])}

**Goal Setting Principles:**
1. Align with current capabilities and resources
2. Address current needs and challenges
3. Consider social relationships and opportunities
4. Balance short-term needs with long-term aspirations
5. Be specific and achievable

**Goal Categories:**
- Survival: Secure food, water, shelter
- Social: Build relationships, form alliances
- Exploration: Discover new areas and resources
- Mastery: Improve skills and knowledge
- Achievement: Create lasting impact

Provide a clear, specific goal with measurable outcomes."""
        
        user_prompt = f"""**Current Situation Analysis:**
- Health: {agent.attributes['health'].current}/100
- Resources: {len(agent.inventory)} items
- Skills: {len([s for s,p in agent.skills.items() if p > 0.3])} active skills
- Social connections: {len(agent.social_connections)} relationships
- Current position: {agent.position}
- World state: {context.world_state.get('time', 0)} turns elapsed

**Goal Setting Task:**
Based on your current situation, skills, and life goals, what should be your next primary objective? Consider your immediate needs, available opportunities, and long-term aspirations.

Provide:
1. Goal type (survival, social, exploration, mastery, achievement)
2. Specific description
3. Expected duration
4. Required resources/skills
5. Success criteria"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            goal = await self.llm_provider.generate_response(
                messages,
                GoalSetting,
                temperature=0.7,
                max_tokens=250
            )
            
            return {
                "goal_type": goal.goal_type,
                "description": goal.description,
                "priority": goal.priority,
                "expected_duration": goal.expected_duration,
                "target_resource": goal.target_resource,
                "target_position": goal.target_position,
                "required_items": goal.required_items,
                "reasoning": f"LLM-generated goal based on situation analysis"
            }
            
        except Exception as e:
            return {
                "goal_type": "survival",
                "description": "Find food and water to survive",
                "priority": 0.8,
                "expected_duration": 10,
                "reasoning": f"Fallback survival goal due to LLM error: {str(e)}"
            }