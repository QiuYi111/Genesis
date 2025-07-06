#!/usr/bin/env python3
"""
MCP Server for LLM-Driven Agent Actions

This server provides tools that the LLM can call to execute agent actions
in a structured way, replacing unreliable JSON generation while preserving
the LLM as the core game engine.
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


class LLMAgentServer:
    """MCP Server that provides LLM with structured tools for agent actions"""
    
    def __init__(self):
        self.server = Server("llm-agent-server")
        self.world_reference = None
        self.agent_states = {}  # Track agent states
        
        # Register tool handlers
        self._register_agent_tools()
        
    def set_world_reference(self, world):
        """Set reference to the world object"""
        self.world_reference = world
        
    def _register_agent_tools(self):
        """Register all agent action tools for LLM to use"""
        
        @self.server.tool()
        async def move_agent(
            agent_id: int,
            direction: str,
            reasoning: str,
            urgency: str = "normal"
        ) -> List[types.TextContent]:
            """Move agent in specified direction
            
            Args:
                agent_id: The agent's unique identifier
                direction: Direction to move (north, south, east, west, northeast, etc.)
                reasoning: Why the agent chose this action (LLM's decision process)
                urgency: How urgent this action is (low, normal, high, critical)
            
            Returns:
                Movement outcome with new position and costs
            """
            try:
                agent = self._get_agent(agent_id)
                if not agent:
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Agent {agent_id} not found"
                    )]
                
                # Parse direction
                direction_map = {
                    "north": (0, -1), "south": (0, 1),
                    "east": (1, 0), "west": (-1, 0),
                    "northeast": (1, -1), "northwest": (-1, -1),
                    "southeast": (1, 1), "southwest": (-1, 1)
                }
                
                if direction.lower() not in direction_map:
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Invalid direction '{direction}'. Use: {list(direction_map.keys())}"
                    )]
                
                dx, dy = direction_map[direction.lower()]
                old_pos = agent.pos
                new_pos = (old_pos[0] + dx, old_pos[1] + dy)
                
                # Check world boundaries
                world_size = getattr(self.world_reference, 'size', 64)
                if not (0 <= new_pos[0] < world_size and 0 <= new_pos[1] < world_size):
                    return [types.TextContent(
                        type="text",
                        text=f"Cannot move outside world boundaries. Current: {old_pos}, Attempted: {new_pos}"
                    )]
                
                # Calculate movement cost based on terrain
                energy_cost = self._calculate_movement_cost(agent, old_pos, new_pos)
                
                # Check if agent has enough energy
                agent_energy = getattr(agent, 'energy', 100)
                if agent_energy < energy_cost:
                    return [types.TextContent(
                        type="text",
                        text=f"Insufficient energy for movement. Need {energy_cost}, have {agent_energy}"
                    )]
                
                # Execute movement
                agent.pos = new_pos
                if hasattr(agent, 'energy'):
                    agent.energy -= energy_cost
                
                # Log the action with LLM reasoning
                action_log = f"Agent {agent_id} moved {direction} from {old_pos} to {new_pos}. Reasoning: {reasoning}"
                logger.info(action_log)
                
                # Update agent's action history
                if not hasattr(agent, 'action_history'):
                    agent.action_history = []
                agent.action_history.append({
                    "action": "move",
                    "direction": direction,
                    "reasoning": reasoning,
                    "urgency": urgency,
                    "outcome": "success",
                    "energy_cost": energy_cost
                })
                
                return [types.TextContent(
                    type="text",
                    text=f"Successfully moved {direction} to {new_pos}. Energy cost: {energy_cost}. {reasoning}"
                )]
                
            except Exception as e:
                error_msg = f"Movement error for agent {agent_id}: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def collect_resource(
            agent_id: int,
            resource_type: Optional[str],
            amount: int = 1,
            reasoning: str = "",
            efficiency_focus: str = "balanced"
        ) -> List[types.TextContent]:
            """Collect resources from current location
            
            Args:
                agent_id: The agent's unique identifier
                resource_type: Specific resource to collect (wood, stone, food, etc.) or None for any
                amount: Amount to attempt to collect
                reasoning: Why the agent chose this action
                efficiency_focus: Collection strategy (speed, quality, quantity, balanced)
            
            Returns:
                Collection outcome with resources gained and skill experience
            """
            try:
                agent = self._get_agent(agent_id)
                if not agent:
                    return [types.TextContent(type="text", text=f"Error: Agent {agent_id} not found")]
                
                pos = agent.pos
                
                # Check for resources at current location
                if not hasattr(self.world_reference, 'resources') or pos not in self.world_reference.resources:
                    return [types.TextContent(
                        type="text",
                        text=f"No resources available at position {pos}. Reasoning was: {reasoning}"
                    )]
                
                available_resources = self.world_reference.resources[pos]
                if not available_resources:
                    return [types.TextContent(
                        type="text",
                        text=f"Resources depleted at position {pos}. Need to move to find more resources."
                    )]
                
                # Determine what to collect
                if resource_type and resource_type in available_resources:
                    target_resource = resource_type
                    max_available = available_resources[resource_type]
                else:
                    # Auto-select best resource if type not specified or not available
                    target_resource = max(available_resources.keys(), key=lambda x: available_resources[x])
                    max_available = available_resources[target_resource]
                
                # Calculate actual collection amount based on skills and efficiency
                collection_skill = agent.skills.get('gathering', 1)
                efficiency_multiplier = {
                    'speed': 0.8, 'quality': 1.2, 'quantity': 1.5, 'balanced': 1.0
                }[efficiency_focus]
                
                actual_amount = min(amount, max_available, int(collection_skill * efficiency_multiplier))
                
                # Execute collection
                self.world_reference.resources[pos][target_resource] -= actual_amount
                if self.world_reference.resources[pos][target_resource] <= 0:
                    del self.world_reference.resources[pos][target_resource]
                    if not self.world_reference.resources[pos]:
                        del self.world_reference.resources[pos]
                
                # Add to agent inventory
                if not hasattr(agent, 'inventory'):
                    agent.inventory = {}
                agent.inventory[target_resource] = agent.inventory.get(target_resource, 0) + actual_amount
                
                # Award skill experience
                experience_gained = actual_amount * 2.0
                if 'gathering' not in agent.skills:
                    agent.skills['gathering'] = 1
                agent.skills['gathering'] += experience_gained / 100.0  # Convert to skill levels
                
                # Log with LLM reasoning
                action_log = f"Agent {agent_id} collected {actual_amount} {target_resource}. Reasoning: {reasoning}"
                logger.info(action_log)
                
                # Update action history
                if not hasattr(agent, 'action_history'):
                    agent.action_history = []
                agent.action_history.append({
                    "action": "collect",
                    "resource": target_resource,
                    "amount": actual_amount,
                    "reasoning": reasoning,
                    "efficiency_focus": efficiency_focus,
                    "experience_gained": experience_gained
                })
                
                return [types.TextContent(
                    type="text",
                    text=f"Collected {actual_amount} {target_resource} using {efficiency_focus} approach. Gained {experience_gained:.1f} gathering experience. {reasoning}"
                )]
                
            except Exception as e:
                error_msg = f"Collection error for agent {agent_id}: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def social_interact(
            agent_id: int,
            target_agent_id: int,
            interaction_type: str,
            message: str,
            intent: str = "friendly"
        ) -> List[types.TextContent]:
            """Interact socially with another agent
            
            Args:
                agent_id: The initiating agent's ID
                target_agent_id: The target agent's ID
                interaction_type: Type of interaction (chat, trade_offer, share_knowledge, alliance, etc.)
                message: What the agent wants to communicate
                intent: The emotional intent (friendly, formal, urgent, suspicious, etc.)
            
            Returns:
                Interaction outcome and target agent's response
            """
            try:
                agent = self._get_agent(agent_id)
                target = self._get_agent(target_agent_id)
                
                if not agent:
                    return [types.TextContent(type="text", text=f"Error: Agent {agent_id} not found")]
                if not target:
                    return [types.TextContent(type="text", text=f"Error: Target agent {target_agent_id} not found")]
                
                # Check if agents are close enough to interact
                distance = self._calculate_distance(agent.pos, target.pos)
                if distance > 2:  # Can only interact with nearby agents
                    return [types.TextContent(
                        type="text",
                        text=f"Target agent {target_agent_id} is too far away (distance: {distance}). Need to move closer first."
                    )]
                
                # Process different interaction types
                response = ""
                relationship_change = 0
                
                if interaction_type == "chat":
                    # Simple conversation
                    response = f"Agent {target_agent_id} responds to {message} with interest"
                    relationship_change = 1
                    
                elif interaction_type == "trade_offer":
                    # Trading interaction
                    response = f"Agent {target_agent_id} considers the trade proposal: {message}"
                    relationship_change = 0
                    
                elif interaction_type == "share_knowledge":
                    # Knowledge sharing
                    if hasattr(agent, 'skills') and agent.skills:
                        shared_skill = max(agent.skills.keys(), key=lambda x: agent.skills[x])
                        if not hasattr(target, 'skills'):
                            target.skills = {}
                        target.skills[shared_skill] = target.skills.get(shared_skill, 0) + 0.1
                        response = f"Agent {target_agent_id} learned about {shared_skill} from agent {agent_id}"
                        relationship_change = 2
                    else:
                        response = f"Agent {agent_id} has no knowledge to share"
                        
                elif interaction_type == "alliance":
                    # Alliance proposal
                    response = f"Agent {target_agent_id} considers alliance with agent {agent_id}"
                    relationship_change = 1
                
                # Update relationships
                if not hasattr(agent, 'relationships'):
                    agent.relationships = {}
                if not hasattr(target, 'relationships'):
                    target.relationships = {}
                    
                agent.relationships[target_agent_id] = agent.relationships.get(target_agent_id, 0) + relationship_change
                target.relationships[agent_id] = target.relationships.get(agent_id, 0) + relationship_change
                
                # Log the interaction
                action_log = f"Agent {agent_id} {interaction_type} with agent {target_agent_id}: {message}"
                logger.info(action_log)
                
                # Update action history
                if not hasattr(agent, 'action_history'):
                    agent.action_history = []
                agent.action_history.append({
                    "action": "social_interact",
                    "target": target_agent_id,
                    "type": interaction_type,
                    "message": message,
                    "intent": intent,
                    "response": response,
                    "relationship_change": relationship_change
                })
                
                return [types.TextContent(
                    type="text", 
                    text=f"Social interaction complete. {response}. Relationship change: +{relationship_change}"
                )]
                
            except Exception as e:
                error_msg = f"Social interaction error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def craft_item(
            agent_id: int,
            item_name: str,
            materials: Dict[str, int],
            crafting_method: str = "standard",
            innovation_attempt: bool = False
        ) -> List[types.TextContent]:
            """Craft an item using available materials
            
            Args:
                agent_id: The agent's unique identifier
                item_name: Name of item to craft
                materials: Required materials as {material: amount} dict
                crafting_method: Approach to crafting (careful, fast, experimental, standard)
                innovation_attempt: Whether to try creating something new
            
            Returns:
                Crafting outcome with item created and skill experience
            """
            try:
                agent = self._get_agent(agent_id)
                if not agent:
                    return [types.TextContent(type="text", text=f"Error: Agent {agent_id} not found")]
                
                if not hasattr(agent, 'inventory'):
                    agent.inventory = {}
                
                # Check if agent has required materials
                for material, amount in materials.items():
                    available = agent.inventory.get(material, 0)
                    if available < amount:
                        return [types.TextContent(
                            type="text",
                            text=f"Insufficient {material}: need {amount}, have {available}. Cannot craft {item_name}."
                        )]
                
                # Calculate crafting success based on skill and method
                crafting_skill = agent.skills.get('crafting', 1)
                method_modifiers = {
                    'careful': (0.9, 1.2),    # (speed, quality)
                    'fast': (1.5, 0.7),
                    'experimental': (0.8, 0.9),
                    'standard': (1.0, 1.0)
                }
                speed_mod, quality_mod = method_modifiers[crafting_method]
                
                success_chance = min(0.95, crafting_skill * quality_mod * 0.15 + 0.3)
                
                # Innovation handling
                if innovation_attempt:
                    innovation_chance = crafting_skill * 0.1
                    if innovation_chance > 0.8:  # Random chance for innovation
                        # Create new item variant
                        item_name = f"improved_{item_name}"
                        success_chance *= 0.7  # Innovation is harder
                
                # Execute crafting
                import random
                if random.random() < success_chance:
                    # Success - consume materials
                    for material, amount in materials.items():
                        agent.inventory[material] -= amount
                        if agent.inventory[material] <= 0:
                            del agent.inventory[material]
                    
                    # Add crafted item
                    agent.inventory[item_name] = agent.inventory.get(item_name, 0) + 1
                    
                    # Award experience
                    experience_gained = sum(materials.values()) * 3.0
                    if 'crafting' not in agent.skills:
                        agent.skills['crafting'] = 1
                    agent.skills['crafting'] += experience_gained / 100.0
                    
                    result_text = f"Successfully crafted {item_name} using {crafting_method} method"
                    if innovation_attempt and item_name.startswith("improved_"):
                        result_text += " with innovative improvements!"
                    
                    # Log crafting
                    logger.info(f"Agent {agent_id} crafted {item_name} using {materials}")
                    
                else:
                    # Failure - lose some materials but gain experience
                    materials_lost = {mat: amount // 2 for mat, amount in materials.items()}
                    for material, amount in materials_lost.items():
                        agent.inventory[material] = max(0, agent.inventory.get(material, 0) - amount)
                    
                    experience_gained = sum(materials.values()) * 1.0
                    agent.skills['crafting'] = agent.skills.get('crafting', 1) + experience_gained / 100.0
                    
                    result_text = f"Crafting failed! Lost some materials but gained {experience_gained:.1f} experience"
                
                # Update action history
                if not hasattr(agent, 'action_history'):
                    agent.action_history = []
                agent.action_history.append({
                    "action": "craft",
                    "item": item_name,
                    "materials": materials,
                    "method": crafting_method,
                    "innovation": innovation_attempt,
                    "success": "crafted" in result_text.lower(),
                    "experience_gained": experience_gained
                })
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Crafting error for agent {agent_id}: {str(e)}"
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
    
    def _calculate_movement_cost(self, agent, old_pos, new_pos):
        """Calculate energy cost for movement based on terrain and agent stats"""
        base_cost = 5
        
        # Factor in agent fitness/health
        health_modifier = getattr(agent, 'health', 100) / 100.0
        
        # Factor in terrain (if world has terrain info)
        terrain_cost = 1.0
        if hasattr(self.world_reference, 'terrain') and new_pos in self.world_reference.terrain:
            terrain_type = self.world_reference.terrain[new_pos]
            terrain_costs = {
                'MOUNTAIN': 2.0, 'FOREST': 1.3, 'GRASSLAND': 1.0, 
                'WATER': 1.5, 'DESERT': 1.4, 'SWAMP': 1.8
            }
            terrain_cost = terrain_costs.get(terrain_type, 1.0)
        
        return int(base_cost * terrain_cost * (2.0 - health_modifier))
    
    def _calculate_distance(self, pos1, pos2):
        """Calculate distance between two positions"""
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])


async def main():
    """Run the LLM Agent MCP server"""
    server_instance = LLMAgentServer()
    
    # Setup server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializeResult(
                server_name="llm-agent-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())