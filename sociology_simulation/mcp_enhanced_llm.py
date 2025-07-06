"""
MCP-Enhanced LLM Service

Replaces JSON generation with structured MCP tool calls while preserving
the LLM as the core game engine for decision-making and generative content.
"""

import asyncio
import os
import json
import time
from typing import Dict, Any, Optional, Union, List, Tuple
import aiohttp
from loguru import logger
from dataclasses import dataclass

from .prompts import get_prompt_manager
from .config import get_config
from .enhanced_llm import LLMResponse, EnhancedLLMService


class MCPEnhancedLLMService(EnhancedLLMService):
    """Enhanced LLM Service that uses MCP tools instead of JSON generation"""
    
    def __init__(self, prompt_manager=None):
        super().__init__(prompt_manager)
        self.mcp_client = None
        
    def set_mcp_client(self, mcp_client):
        """Set the MCP client for tool calling"""
        self.mcp_client = mcp_client
        
    async def generate_agent_action_with_mcp(
        self,
        agent_id: int,
        era_prompt: str,
        perception: Dict,
        memory_summary: Dict,
        goal: str,
        skills: Dict,
        session: aiohttp.ClientSession
    ) -> str:
        """Generate agent action using LLM with MCP tools instead of JSON
        
        The LLM analyzes the situation and calls appropriate MCP tools to execute actions.
        This preserves the LLM as the decision engine while eliminating JSON parsing issues.
        """
        try:
            # Prepare rich context for the LLM
            context = {
                'agent_id': agent_id,
                'era': era_prompt,
                'position': perception.get('position', (0, 0)),
                'visible_tiles': perception.get('visible_tiles', []),
                'visible_agents': perception.get('visible_agents', []),
                'inventory': perception.get('inventory', {}),
                'health': perception.get('health', 100),
                'energy': perception.get('energy', 100),
                'goal': goal,
                'skills': skills,
                'known_agents': memory_summary.get('known_agents', []),
                'known_locations': memory_summary.get('known_locations', [])
            }
            
            # Create a prompt that guides the LLM to use MCP tools
            mcp_action_prompt = self._create_mcp_action_prompt(context)
            
            # Generate LLM response with tool calling guidance
            response = await self._generate_text_response(
                system="You are an intelligent agent in a sociology simulation. Use the available MCP tools to take actions.",
                user=mcp_action_prompt,
                temperature=0.7,
                session=session,
                config={"max_retries": 2, "timeout": 30}
            )
            
            if not response.success:
                logger.warning(f"LLM action generation failed for agent {agent_id}, using fallback")
                return await self._fallback_action_selection(context)
            
            # Parse LLM response to extract intended action and call appropriate MCP tool
            action_description, mcp_outcome = await self._execute_llm_intended_action(response.content, context)
            
            # Return both the description and the structured outcome
            return {
                'action_description': action_description,
                'mcp_outcome': mcp_outcome
            }
            
        except Exception as e:
            logger.error(f"MCP action generation error for agent {agent_id}: {str(e)}")
            logger.error(f"Context was: {context}")
            logger.error(f"LLM response was: {response.content if 'response' in locals() and hasattr(response, 'content') else 'No response generated'}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return await self._fallback_action_selection(context)
    
    def _create_mcp_action_prompt(self, context: Dict[str, Any]) -> str:
        """Create a rich prompt that guides LLM to choose and use MCP tools"""
        
        prompt = f"""You are Agent {context['agent_id']} in the {context['era']}.

CURRENT SITUATION:
- Position: {context['position']}
- Health: {context['health']}, Energy: {context['energy']}
- Goal: {context['goal']}
- Inventory: {context['inventory']}

PERCEPTION:
- Visible terrain: {[tile.get('terrain', 'unknown') for tile in context['visible_tiles']]}
- Resources nearby: {[tile.get('resources', {}) for tile in context['visible_tiles'] if tile.get('resources')]}
- Other agents nearby: {[f"Agent {agent.get('aid', '?')} at {agent.get('pos', '?')}" for agent in context['visible_agents']]}

SKILLS:
{self._format_skills_for_prompt(context['skills'])}

MEMORY:
- Known agents: {[agent['name'] for agent in context['known_agents']]}
- Known resource locations: {len(context['known_locations'])} locations

AVAILABLE ACTIONS:
Based on your situation, you can choose from these action types:

1. MOVEMENT: If you need to go somewhere
   - Format: "MOVE [direction] because [reasoning]"
   - Example: "MOVE north because I see wood resources there and need materials for crafting"

2. RESOURCE COLLECTION: If there are resources at your location
   - Format: "COLLECT [resource_type] [amount] with [efficiency_focus] because [reasoning]"
   - Example: "COLLECT wood 3 with quality because I need good materials for tool crafting"

3. CRAFTING: If you have materials and want to make something
   - Format: "CRAFT [item_name] using [materials] with [method] because [reasoning]"
   - Example: "CRAFT stone_axe using {{{{wood: 2, stone: 1}}}} with careful because I need better tools"

4. SOCIAL INTERACTION: If other agents are nearby
   - Format: "SOCIAL [target_agent_id] [interaction_type] '[message]' with [intent] because [reasoning]"
   - Example: "SOCIAL 5 trade_offer 'I have wood, need food' with friendly because mutual benefit"

5. BUILD STRUCTURE: If you have materials and want to create permanent buildings
   - Format: "BUILD [structure_type] using [materials] at [location] because [reasoning]"
   - Example: "BUILD shelter using {{{{wood: 5, stone: 3}}}} at current because need protection from weather"

6. MODIFY TERRAIN: If you want to permanently change the landscape
   - Format: "MODIFY [modification_type] using [tools] because [reasoning]"
   - Example: "MODIFY dig_well using {{{{stone_axe: 1}}}} because need reliable water source"

7. CREATIVE ACTION: If you want to try something innovative
   - Format: "CREATIVE [description] with [creativity_level] inspired by [inspiration] because [reasoning]"
   - Example: "CREATIVE combine stones to make fire with 0.8 inspired by sparks when stones hit because need warmth"

Choose the best action for your current situation. Consider your goal, needs, and opportunities.
Be specific about your reasoning - this helps with learning and skill development.

Your action decision:"""

        return prompt
    
    def _format_skills_for_prompt(self, skills: Dict[str, Any]) -> str:
        """Format skills in a readable way for the prompt"""
        if not skills:
            return "- No special skills yet"
        
        formatted = []
        for skill_name, skill_data in skills.items():
            if isinstance(skill_data, dict):
                level = skill_data.get('level', 1)
                description = skill_data.get('description', '')
                formatted.append(f"- {skill_name}: Level {level} - {description}")
            else:
                # Simple numeric skill level
                formatted.append(f"- {skill_name}: Level {skill_data:.1f}")
        
        return '\n'.join(formatted)
    
    async def _execute_llm_intended_action(self, llm_response: str, context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Parse LLM response and execute the intended action via MCP tools"""
        try:
            response_text = llm_response.strip()
            agent_id = context['agent_id']
            
            logger.debug(f"Agent {agent_id} LLM response: {response_text}")
            logger.debug(f"Agent {agent_id} context: {context}")
            
            # Parse the action type and parameters from LLM response
            if response_text.startswith("MOVE"):
                return await self._handle_move_action(response_text, agent_id)
            
            elif response_text.startswith("COLLECT"):
                return await self._handle_collect_action(response_text, agent_id)
            
            elif response_text.startswith("CRAFT"):
                return await self._handle_craft_action(response_text, agent_id)
            
            elif response_text.startswith("SOCIAL"):
                return await self._handle_social_action(response_text, agent_id)
            
            elif response_text.startswith("BUILD"):
                return await self._handle_build_action(response_text, agent_id)
            
            elif response_text.startswith("MODIFY"):
                return await self._handle_modify_action(response_text, agent_id)
            
            elif response_text.startswith("CREATIVE"):
                return await self._handle_creative_action(response_text, agent_id)
            
            else:
                # Try to extract action from free-form response  
                description = await self._parse_freeform_action(response_text, agent_id)
                return description, {"success": True, "description": description}
                
        except Exception as e:
            logger.error(f"Error executing LLM action: {str(e)}")
            error_desc = f"Action parsing failed: {str(e)}"
            return error_desc, {"success": False, "error": str(e)}
    
    async def _handle_move_action(self, response: str, agent_id: int) -> Tuple[str, Dict[str, Any]]:
        """Handle movement action via MCP tools"""
        try:
            # Parse: "MOVE [direction] because [reasoning]"
            parts = response.split(" because ")
            action_part = parts[0]
            reasoning = parts[1] if len(parts) > 1 else "No specific reason given"
            
            # Extract direction
            direction = action_part.replace("MOVE ", "").strip()
            
            if not self.mcp_client:
                description = f"Decided to move {direction}: {reasoning} (no MCP client available)"
                return description, {"success": False, "error": "No MCP client"}
            
            # Call MCP tool
            result = await self.mcp_client.agent_move(agent_id, direction, reasoning)
            
            if result.get('success'):
                description = f"Moved {direction}: {reasoning}. {result.get('description', '')}"
                return description, result
            else:
                description = f"Failed to move {direction}: {result.get('error', 'Unknown error')}"
                return description, result
                
        except Exception as e:
            error_desc = f"Move action error: {str(e)}"
            return error_desc, {"success": False, "error": str(e)}
    
    async def _handle_collect_action(self, response: str, agent_id: int) -> Tuple[str, Dict[str, Any]]:
        """Handle collection action via MCP tools"""
        try:
            # Parse: "COLLECT [resource_type] [amount] with [efficiency_focus] because [reasoning]"
            parts = response.split(" because ")
            action_part = parts[0]
            reasoning = parts[1] if len(parts) > 1 else "Resource gathering"
            
            # Extract parameters
            action_tokens = action_part.replace("COLLECT ", "").split()
            resource_type = action_tokens[0] if action_tokens else None
            amount = int(action_tokens[1]) if len(action_tokens) > 1 and action_tokens[1].isdigit() else 1
            
            efficiency_focus = "balanced"
            if "with" in action_part:
                efficiency_part = action_part.split("with")[1].split("because")[0].strip()
                if efficiency_part in ["speed", "quality", "quantity", "balanced"]:
                    efficiency_focus = efficiency_part
            
            if not self.mcp_client:
                return f"Decided to collect {resource_type}: {reasoning} (no MCP client available)", {"success": False, "error": "No MCP client"}
            
            # Call MCP tool
            result = await self.mcp_client.agent_collect_resource(
                agent_id, resource_type, amount, reasoning, efficiency_focus
            )
            
            if result.get('success'):
                return f"Collected {resource_type}: {reasoning}. {result.get('description', '')}", result
            else:
                return f"Failed to collect {resource_type}: {result.get('error', 'Unknown error')}", result
                
        except Exception as e:
            return f"Collect action error: {str(e)}", {"success": False, "error": str(e)}
    
    async def _handle_craft_action(self, response: str, agent_id: int) -> Tuple[str, Dict[str, Any]]:
        """Handle crafting action via MCP tools"""
        try:
            # Parse: "CRAFT [item_name] using {materials} with [method] because [reasoning]"
            parts = response.split(" because ")
            action_part = parts[0]
            reasoning = parts[1] if len(parts) > 1 else "Crafting attempt"
            
            # Extract item name
            craft_tokens = action_part.replace("CRAFT ", "").split(" using ")
            item_name = craft_tokens[0].strip()
            
            # Extract materials (try to parse JSON-like format)
            materials = {}
            if len(craft_tokens) > 1:
                materials_part = craft_tokens[1].split(" with ")[0]
                try:
                    # Handle {wood: 2, stone: 1} format
                    materials_clean = materials_part.replace("{", "").replace("}", "")
                    for pair in materials_clean.split(","):
                        if ":" in pair:
                            key, value = pair.split(":")
                            materials[key.strip()] = int(value.strip())
                except:
                    # Fallback: assume basic materials
                    materials = {"wood": 1, "stone": 1}
            
            # Extract crafting method
            crafting_method = "standard"
            if " with " in action_part:
                method_part = action_part.split(" with ")[1].split(" because ")[0].strip()
                if method_part in ["careful", "fast", "experimental", "standard"]:
                    crafting_method = method_part
            
            if not self.mcp_client:
                return f"Decided to craft {item_name}: {reasoning} (no MCP client available)", {"success": False, "error": "No MCP client"}
            
            # Call MCP tool
            result = await self.mcp_client.agent_craft_item(
                agent_id, item_name, materials, crafting_method
            )
            
            if result.get('success'):
                return f"Crafted {item_name}: {reasoning}. {result.get('description', '')}", result
            else:
                return f"Failed to craft {item_name}: {result.get('error', 'Unknown error')}", result
                
        except Exception as e:
            return f"Craft action error: {str(e)}", {"success": False, "error": str(e)}
    
    async def _handle_social_action(self, response: str, agent_id: int) -> Tuple[str, Dict[str, Any]]:
        """Handle social interaction via MCP tools"""
        try:
            # Parse: "SOCIAL [target_agent_id] [interaction_type] '[message]' with [intent] because [reasoning]"
            parts = response.split(" because ")
            action_part = parts[0]
            reasoning = parts[1] if len(parts) > 1 else "Social interaction"
            
            # Extract components
            social_tokens = action_part.replace("SOCIAL ", "").split()
            target_agent_id = int(social_tokens[0]) if social_tokens and social_tokens[0].isdigit() else None
            interaction_type = social_tokens[1] if len(social_tokens) > 1 else "chat"
            
            # Extract message (look for quoted text)
            message = "Hello!"
            if "'" in action_part:
                message_start = action_part.find("'") + 1
                message_end = action_part.find("'", message_start)
                if message_end > message_start:
                    message = action_part[message_start:message_end]
            
            # Extract intent
            intent = "friendly"
            if " with " in action_part:
                intent_part = action_part.split(" with ")[1].split(" because ")[0].strip()
                if intent_part in ["friendly", "formal", "urgent", "suspicious"]:
                    intent = intent_part
            
            if not target_agent_id:
                return f"Social action failed: No valid target agent specified", {"success": False, "error": "No target agent"}
            
            if not self.mcp_client:
                return f"Decided to interact with agent {target_agent_id}: {reasoning} (no MCP client available)", {"success": False, "error": "No MCP client"}
            
            # Call MCP tool
            result = await self.mcp_client.agent_social_interact(
                agent_id, target_agent_id, interaction_type, message, intent
            )
            
            if result.get('success'):
                return f"Social interaction with agent {target_agent_id}: {reasoning}. {result.get('description', '')}", result
            else:
                return f"Failed social interaction: {result.get('error', 'Unknown error')}", result
                
        except Exception as e:
            return f"Social action error: {str(e)}", {"success": False, "error": str(e)}
    
    async def _handle_build_action(self, response: str, agent_id: int) -> Tuple[str, Dict[str, Any]]:
        """Handle building action via MCP tools"""
        try:
            # Parse: "BUILD [structure_type] using {materials} at [location] because [reasoning]"
            parts = response.split(" because ")
            action_part = parts[0]
            reasoning = parts[1] if len(parts) > 1 else "Building structure"
            
            # Extract structure type
            build_tokens = action_part.replace("BUILD ", "").split(" using ")
            structure_type = build_tokens[0].strip()
            
            # Extract materials (try to parse JSON-like format)
            materials = {}
            if len(build_tokens) > 1:
                materials_part = build_tokens[1].split(" at ")[0]
                try:
                    # Handle {wood: 5, stone: 3} format
                    materials_clean = materials_part.replace("{", "").replace("}", "")
                    for pair in materials_clean.split(","):
                        if ":" in pair:
                            key, value = pair.split(":")
                            materials[key.strip()] = int(value.strip())
                except:
                    # Fallback: assume basic materials for shelter
                    materials = {"wood": 3, "stone": 2}
            
            # Extract location (optional - defaults to current position)
            location = None
            if " at " in action_part:
                location_part = action_part.split(" at ")[1].split(" because ")[0].strip()
                if location_part == "current":
                    location = None  # Use agent's current position
            
            if not self.mcp_client:
                return f"Decided to build {structure_type}: {reasoning} (no MCP client available)", {"success": False, "error": "No MCP client"}
            
            # Call MCP tool
            result = await self.mcp_client.agent_build_structure(
                agent_id, structure_type, materials, location, reasoning
            )
            
            if result.get('success'):
                return f"Built {structure_type}: {reasoning}. {result.get('description', '')}", result
            else:
                return f"Failed to build {structure_type}: {result.get('error', 'Unknown error')}", result
                
        except Exception as e:
            return f"Build action error: {str(e)}", {"success": False, "error": str(e)}
    
    async def _handle_modify_action(self, response: str, agent_id: int) -> Tuple[str, Dict[str, Any]]:
        """Handle terrain modification action via MCP tools"""
        try:
            # Parse: "MODIFY [modification_type] using {tools} because [reasoning]"
            parts = response.split(" because ")
            action_part = parts[0]
            reasoning = parts[1] if len(parts) > 1 else "Terrain modification"
            
            # Extract modification type
            modify_tokens = action_part.replace("MODIFY ", "").split(" using ")
            modification_type = modify_tokens[0].strip()
            
            # Extract required tools
            tools_required = []
            if len(modify_tokens) > 1:
                tools_part = modify_tokens[1]
                try:
                    # Handle {stone_axe: 1} format or simple tool names
                    if "{" in tools_part:
                        tools_clean = tools_part.replace("{", "").replace("}", "")
                        for pair in tools_clean.split(","):
                            if ":" in pair:
                                tool_name = pair.split(":")[0].strip()
                                tools_required.append(tool_name)
                    else:
                        # Simple tool name
                        tools_required = [tools_part.strip()]
                except:
                    # Fallback: assume basic tools
                    tools_required = ["stone_axe"]
            
            # Define modification area (simple default)
            area = {"center": None, "radius": 1}  # Will use agent's current position
            
            if not self.mcp_client:
                return f"Decided to modify terrain ({modification_type}): {reasoning} (no MCP client available)", {"success": False, "error": "No MCP client"}
            
            # Call MCP tool
            result = await self.mcp_client.agent_modify_terrain(
                agent_id, modification_type, area, tools_required, reasoning
            )
            
            if result.get('success'):
                return f"Modified terrain ({modification_type}): {reasoning}. {result.get('description', '')}", result
            else:
                return f"Failed to modify terrain: {result.get('error', 'Unknown error')}", result
                
        except Exception as e:
            return f"Modify action error: {str(e)}", {"success": False, "error": str(e)}

    async def _handle_creative_action(self, response: str, agent_id: int) -> Tuple[str, Dict[str, Any]]:
        """Handle creative/innovative action via MCP tools"""
        try:
            # Parse: "CREATIVE [description] with [creativity_level] inspired by [inspiration] because [reasoning]"
            parts = response.split(" because ")
            action_part = parts[0]
            reasoning = parts[1] if len(parts) > 1 else "Creative exploration"
            
            # Extract description
            desc_start = action_part.find("CREATIVE ") + 9
            desc_end = action_part.find(" with ")
            if desc_end == -1:
                desc_end = len(action_part)
            
            action_description = action_part[desc_start:desc_end].strip()
            
            # Extract creativity level
            creativity_level = 0.5
            if " with " in action_part:
                creativity_part = action_part.split(" with ")[1].split(" inspired by ")[0].strip()
                try:
                    creativity_level = float(creativity_part)
                except:
                    creativity_level = 0.5
            
            # Extract inspiration
            inspiration_source = "curiosity"
            if " inspired by " in action_part:
                inspiration_part = action_part.split(" inspired by ")[1].split(" because ")[0].strip()
                inspiration_source = inspiration_part
            
            if not self.mcp_client:
                return f"Decided to try creative action: {action_description} (no MCP client available)", {"success": False, "error": "No MCP client"}
            
            # Call MCP tool for creative action handling
            result = await self.mcp_client.handle_creative_action(
                agent_id, action_description, creativity_level, inspiration_source, reasoning
            )
            
            if result.get('success'):
                return f"Creative action: {action_description}. {result.get('description', '')}", result
            else:
                return f"Creative action failed: {result.get('error', 'Unknown error')}", result
                
        except Exception as e:
            return f"Creative action error: {str(e)}", {"success": False, "error": str(e)}
    
    async def _parse_freeform_action(self, response: str, agent_id: int) -> str:
        """Parse free-form LLM response and try to map to MCP tools"""
        try:
            response_lower = response.lower()
            
            # Look for collection keywords FIRST (higher priority than movement)
            if any(word in response_lower for word in ["collect", "gather", "harvest", "pick", "find resource"]):
                resource_type = None
                for resource in ["wood", "stone", "fish", "apple", "berries", "clay", "food"]:
                    if resource in response_lower:
                        resource_type = resource
                        break
                
                reasoning = response[:100] + "..." if len(response) > 100 else response
                return await self._handle_collect_action(f"COLLECT {resource_type or 'resource'} 2 with balanced because {reasoning}", agent_id)
            
            # Look for movement keywords
            elif any(word in response_lower for word in ["move", "go", "walk", "travel"]):
                direction = "north"  # Default
                for dir_word in ["north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"]:
                    if dir_word in response_lower:
                        direction = dir_word
                        break
                
                reasoning = response[:100] + "..." if len(response) > 100 else response
                return await self._handle_move_action(f"MOVE {direction} because {reasoning}", agent_id)
            
            # Look for collection keywords
            elif any(word in response_lower for word in ["collect", "gather", "harvest", "pick"]):
                resource_type = None
                for resource in ["wood", "stone", "food", "water", "fish", "apple"]:
                    if resource in response_lower:
                        resource_type = resource
                        break
                
                reasoning = response[:50] + "..." if len(response) > 50 else response
                return await self._handle_collect_action(f"COLLECT {resource_type or 'resource'} 1 with balanced because {reasoning}", agent_id)
            
            # Look for crafting keywords
            elif any(word in response_lower for word in ["craft", "make", "build", "create"]):
                item = "tool"
                for item_name in ["axe", "tool", "spear", "rope", "torch"]:
                    if item_name in response_lower:
                        item = item_name
                        break
                
                reasoning = response[:50] + "..." if len(response) > 50 else response
                return await self._handle_craft_action(f"CRAFT {item} using {{{{wood: 1, stone: 1}}}} with standard because {reasoning}", agent_id)
            
            # Look for social keywords
            elif any(word in response_lower for word in ["talk", "speak", "chat", "interact"]):
                # Try to find target agent ID
                import re
                agent_match = re.search(r'agent (\d+)', response_lower)
                target_id = int(agent_match.group(1)) if agent_match else 1
                
                reasoning = response[:50] + "..." if len(response) > 50 else response
                return await self._handle_social_action(f"SOCIAL {target_id} chat 'Hello!' with friendly because {reasoning}", agent_id)
            
            else:
                # Default to rest/explore
                return f"Agent contemplated: {response[:100]}{'...' if len(response) > 100 else ''}"
                
        except Exception as e:
            return f"Free-form action parsing error: {str(e)}"
    
    async def _fallback_action_selection(self, context: Dict[str, Any]) -> str:
        """Raise error when MCP action generation fails - no fallback allowed"""
        agent_id = context['agent_id']
        raise RuntimeError(f"MCP action generation failed for agent {agent_id}. This simulation requires MCP integration to function properly. Check MCP client connection and LLM service configuration.")
    
    async def generate_trinity_rules_with_mcp(
        self,
        era_prompt: str,
        world_size: int,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """Generate Trinity rules using LLM with MCP tools instead of JSON"""
        try:
            # Create prompt for Trinity to analyze the era and create appropriate rules
            trinity_prompt = f"""You are Trinity, the world AI managing a sociology simulation in the {era_prompt}.

WORLD CONTEXT:
- Era: {era_prompt}
- World Size: {world_size}x{world_size}
- Your role: Create world rules, terrain types, and resource distributions that fit this era

TASK: Analyze this era and create appropriate world elements using these tools:

1. CREATE TERRAIN TYPES that fit the era:
   - Use: "TERRAIN [name] '[description]' cost=[movement_cost] resources={{{{resource: probability}}}} color=[color]"
   - Example: "TERRAIN FOREST 'Dense woodlands with tall trees' cost=1.3 resources={{{{wood: 0.8, apple: 0.3}}}} color=green"

2. SET RESOURCE DISTRIBUTIONS for this era:
   - Use: "RESOURCE [resource_name] distribution={{{{terrain: probability}}}} depletion=[rate] regen=[rate]"
   - Example: "RESOURCE wood distribution={{{{FOREST: 0.8, GRASSLAND: 0.2}}}} depletion=0.1 regen=0.05"

3. CREATE WORLD RULES that govern this era:
   - Use: "RULE [name] '[description]' conditions=[list] effects=[list] priority=[number]"
   - Example: "RULE seasonal_change 'Resources change with seasons' conditions=['turn_mod_100'] effects=['resource_variation'] priority=1"

Consider what terrain types, resources, and rules would exist in the {era_prompt}. 
Think about the technology level, social structures, and environmental factors of this era.

Create 3-5 terrain types, 4-6 resource distributions, and 2-3 world rules that capture the essence of this era.

Your world creation decisions:"""

            # Generate LLM response
            response = await self._generate_text_response(
                system="You are Trinity, the intelligent world AI that creates and manages the simulation world.",
                user=trinity_prompt,
                temperature=0.8,
                session=session,
                config={"max_retries": 2, "timeout": 30}
            )
            
            if not response.success:
                raise RuntimeError(f"Trinity rule generation failed for era '{era_prompt}'. This simulation requires MCP integration to function properly. LLM service failed to generate world rules.")
            
            # Parse Trinity's response and execute via MCP tools
            rules_result = await self._execute_trinity_decisions(response.content, era_prompt, world_size)
            
            return rules_result
            
        except Exception as e:
            logger.error(f"Trinity MCP rule generation error: {str(e)}")
            raise RuntimeError(f"Trinity MCP rule generation failed for era '{era_prompt}': {str(e)}. This simulation requires MCP integration to function properly.")
    
    async def _execute_trinity_decisions(self, trinity_response: str, era_prompt: str, world_size: int) -> Dict[str, Any]:
        """Execute Trinity's decisions via MCP tools"""
        results = {
            'terrain_types': [],
            'resource_rules': {},
            'world_rules': [],
            'era_prompt': era_prompt
        }
        
        try:
            lines = trinity_response.split('\n')
            
            logger.info(f"Trinity response content:\n{trinity_response}")
            logger.info(f"Parsing {len(lines)} lines from Trinity response")
            
            for line in lines:
                line = line.strip()
                logger.debug(f"Processing line: '{line}'")
                
                # Handle numbered lists (e.g., "1. TERRAIN ..." or "2. RESOURCE ...")
                if '. TERRAIN ' in line:
                    # Extract just the TERRAIN part after the number
                    terrain_part = line[line.find('TERRAIN '):]
                    logger.debug(f"Found numbered TERRAIN line: {terrain_part}")
                    result = await self._handle_trinity_terrain(terrain_part)
                    if result:
                        results['terrain_types'].append(result)
                        logger.debug(f"Added terrain: {result}")
                    else:
                        logger.warning(f"Failed to parse terrain line: {terrain_part}")
                
                elif '. RESOURCE ' in line:
                    # Extract just the RESOURCE part after the number
                    resource_part = line[line.find('RESOURCE '):]
                    logger.debug(f"Found numbered RESOURCE line: {resource_part}")
                    result = await self._handle_trinity_resource(resource_part)
                    if result:
                        results['resource_rules'].update(result)
                        logger.debug(f"Added resource: {result}")
                    else:
                        logger.warning(f"Failed to parse resource line: {resource_part}")
                
                elif '. RULE ' in line:
                    # Extract just the RULE part after the number
                    rule_part = line[line.find('RULE '):]
                    logger.debug(f"Found numbered RULE line: {rule_part}")
                    result = await self._handle_trinity_rule(rule_part)
                    if result:
                        results['world_rules'].append(result)
                        logger.debug(f"Added rule: {result}")
                    else:
                        logger.warning(f"Failed to parse rule line: {rule_part}")
                
                # Also handle non-numbered format for backwards compatibility
                elif line.startswith("TERRAIN"):
                    logger.debug(f"Found direct TERRAIN line: {line}")
                    result = await self._handle_trinity_terrain(line)
                    if result:
                        results['terrain_types'].append(result)
                        logger.debug(f"Added terrain: {result}")
                    else:
                        logger.warning(f"Failed to parse terrain line: {line}")
                
                elif line.startswith("RESOURCE"):
                    logger.debug(f"Found direct RESOURCE line: {line}")
                    result = await self._handle_trinity_resource(line)
                    if result:
                        results['resource_rules'].update(result)
                        logger.debug(f"Added resource: {result}")
                    else:
                        logger.warning(f"Failed to parse resource line: {line}")
                
                elif line.startswith("RULE"):
                    logger.debug(f"Found direct RULE line: {line}")
                    result = await self._handle_trinity_rule(line)
                    if result:
                        results['world_rules'].append(result)
                        logger.debug(f"Added rule: {result}")
                    else:
                        logger.warning(f"Failed to parse rule line: {line}")
                else:
                    if line and not line.startswith('#') and not line.endswith(':'):  # Skip empty lines, comments, and headers
                        logger.debug(f"Unrecognized line format: '{line}'")
            
            logger.info(f"Trinity created {len(results['terrain_types'])} terrains, {len(results['resource_rules'])} resources, {len(results['world_rules'])} rules")
            
            return results
            
        except Exception as e:
            logger.error(f"Trinity decision execution error: {str(e)}")
            return results
    
    async def _handle_trinity_terrain(self, line: str) -> Optional[str]:
        """Handle Trinity terrain creation"""
        try:
            # Parse: "TERRAIN [name] '[description]' cost=[movement_cost] resources={resource: probability} color=[color]"
            if not self.mcp_client:
                return None
            
            # Extract terrain name
            name_start = line.find("TERRAIN ") + 8
            name_end = line.find(" '")
            if name_end == -1:
                return None
            
            terrain_name = line[name_start:name_end].strip()
            
            # Extract description
            desc_start = line.find("'") + 1
            desc_end = line.find("'", desc_start)
            description = line[desc_start:desc_end] if desc_end > desc_start else "Terrain type"
            
            # Extract movement cost
            movement_cost = 1.0
            if "cost=" in line:
                cost_part = line.split("cost=")[1].split()[0]
                try:
                    movement_cost = float(cost_part)
                except:
                    movement_cost = 1.0
            
            # Extract resources (simplified parsing)
            resources = {}
            if "resources={" in line:
                try:
                    res_start = line.find("resources={") + 11
                    res_end = line.find("}", res_start)
                    if res_end > res_start:
                        res_content = line[res_start:res_end]
                        # Simple parsing: wood: 0.8, apple: 0.3
                        for pair in res_content.split(","):
                            if ":" in pair:
                                key, value = pair.split(":")
                                resources[key.strip()] = float(value.strip())
                except:
                    resources = {}
            
            # Extract color
            color = "gray"
            if "color=" in line:
                color_part = line.split("color=")[1].split()[0]
                color = color_part
            
            # Call MCP tool
            result = await self.mcp_client.trinity_create_terrain(
                terrain_name, description, movement_cost, resources, color
            )
            
            return terrain_name if result.get('success') else None
            
        except Exception as e:
            logger.error(f"Trinity terrain creation error: {str(e)}")
            return None
    
    async def _handle_trinity_resource(self, line: str) -> Optional[Dict[str, Any]]:
        """Handle Trinity resource distribution"""
        try:
            if not self.mcp_client:
                return None
            
            # Parse: "RESOURCE [resource_name] distribution={terrain: probability} depletion=[rate] regen=[rate]"
            resource_name = line.split()[1]
            
            # Extract distribution
            distribution = {}
            if "distribution={" in line:
                try:
                    dist_start = line.find("distribution={") + 14
                    dist_end = line.find("}", dist_start)
                    if dist_end > dist_start:
                        dist_content = line[dist_start:dist_end]
                        for pair in dist_content.split(","):
                            if ":" in pair:
                                key, value = pair.split(":")
                                distribution[key.strip()] = float(value.strip())
                except:
                    distribution = {}
            
            # Call MCP tool
            result = await self.mcp_client.trinity_set_resource_distribution(
                resource_name, distribution
            )
            
            return {resource_name: distribution} if result.get('success') else None
            
        except Exception as e:
            logger.error(f"Trinity resource distribution error: {str(e)}")
            return None
    
    async def _handle_trinity_rule(self, line: str) -> Optional[Dict[str, Any]]:
        """Handle Trinity world rule creation"""
        try:
            if not self.mcp_client:
                return None
            
            # Parse: "RULE [name] '[description]' conditions=[list] effects=[list] priority=[number]"
            rule_parts = line.split("'")
            if len(rule_parts) < 3:
                return None
            
            rule_name = rule_parts[0].replace("RULE ", "").strip()
            description = rule_parts[1]
            
            # Extract conditions and effects (simplified)
            conditions = ["era_appropriate"]
            effects = ["world_balance"]
            priority = 1
            
            # Call MCP tool
            result = await self.mcp_client.trinity_create_rule(
                rule_name, description, conditions, effects, priority
            )
            
            return {
                'name': rule_name,
                'description': description,
                'conditions': conditions,
                'effects': effects,
                'priority': priority
            } if result.get('success') else None
            
        except Exception as e:
            logger.error(f"Trinity rule creation error: {str(e)}")
            return None
    
    # Removed _fallback_trinity_rules method - this simulation requires MCP integration


# Global instance for easy access
_mcp_llm_service = None

def init_mcp_llm_service(prompt_manager=None) -> MCPEnhancedLLMService:
    """Initialize the MCP-enhanced LLM service"""
    global _mcp_llm_service
    _mcp_llm_service = MCPEnhancedLLMService(prompt_manager)
    return _mcp_llm_service

def get_mcp_llm_service() -> Optional[MCPEnhancedLLMService]:
    """Get the global MCP-enhanced LLM service instance"""
    return _mcp_llm_service