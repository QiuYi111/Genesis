"""
MCP Integration Patch

This module patches the existing simulation to use MCP-enhanced LLM service
instead of JSON-based generation, eliminating JSON parsing failures while
preserving the LLM as the game engine.
"""

import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger

from .mcp_enhanced_llm import init_mcp_llm_service, get_mcp_llm_service
from .enhanced_llm import get_llm_service


class MCPClient:
    """Mock MCP client that provides the tool interface for the enhanced LLM service"""
    
    def __init__(self, world_reference=None):
        self.world_reference = world_reference
        self.fallback_mode = True  # Start in fallback mode, no actual MCP servers needed
        
    async def agent_move(self, agent_id: int, direction: str, reasoning: str, urgency: str = "normal"):
        """Move agent using direct simulation integration"""
        try:
            agent = self._get_agent(agent_id)
            if not agent:
                return {"success": False, "error": f"Agent {agent_id} not found"}
            
            direction_map = {
                "north": (0, -1), "south": (0, 1),
                "east": (1, 0), "west": (-1, 0),
                "northeast": (1, -1), "northwest": (-1, -1),
                "southeast": (1, 1), "southwest": (-1, 1)
            }
            
            if direction.lower() not in direction_map:
                return {"success": False, "error": f"Invalid direction: {direction}"}
            
            dx, dy = direction_map[direction.lower()]
            old_pos = agent.pos
            new_pos = (old_pos[0] + dx, old_pos[1] + dy)
            
            # Check boundaries
            world_size = getattr(self.world_reference, 'size', 64)
            if not (0 <= new_pos[0] < world_size and 0 <= new_pos[1] < world_size):
                return {"success": False, "error": "Cannot move outside world boundaries"}
            
            # Execute movement
            agent.pos = new_pos
            
            return {
                "success": True,
                "description": f"Moved {direction} to {new_pos}. {reasoning}",
                "position_change": new_pos
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def agent_collect_resource(self, agent_id: int, resource_type: Optional[str] = None, 
                                   amount: int = 1, reasoning: str = "", efficiency_focus: str = "balanced"):
        """Collect resources using direct simulation integration"""
        try:
            agent = self._get_agent(agent_id)
            if not agent:
                return {"success": False, "error": f"Agent {agent_id} not found"}
            
            pos = agent.pos
            if not hasattr(self.world_reference, 'resources') or pos not in self.world_reference.resources:
                return {"success": False, "error": f"No resources at position {pos}"}
            
            available_resources = self.world_reference.resources[pos]
            if not available_resources:
                return {"success": False, "error": "Resources depleted"}
            
            # Select resource to collect
            if resource_type and resource_type in available_resources:
                target_resource = resource_type
            else:
                target_resource = list(available_resources.keys())[0]
            
            # Calculate collection amount
            max_available = available_resources[target_resource]
            actual_amount = min(amount, max_available, 3)  # Max 3 per action
            
            # Execute collection
            self.world_reference.resources[pos][target_resource] -= actual_amount
            if self.world_reference.resources[pos][target_resource] <= 0:
                del self.world_reference.resources[pos][target_resource]
                if not self.world_reference.resources[pos]:
                    del self.world_reference.resources[pos]
            
            # Add to inventory
            if not hasattr(agent, 'inventory'):
                agent.inventory = {}
            agent.inventory[target_resource] = agent.inventory.get(target_resource, 0) + actual_amount
            
            return {
                "success": True,
                "description": f"Collected {actual_amount} {target_resource}. {reasoning}",
                "inventory_changes": {target_resource: actual_amount}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def agent_craft_item(self, agent_id: int, item_name: str, materials: Dict[str, int], 
                              crafting_method: str = "standard", innovation_attempt: bool = False):
        """Craft items using direct simulation integration"""
        try:
            agent = self._get_agent(agent_id)
            if not agent:
                return {"success": False, "error": f"Agent {agent_id} not found"}
            
            if not hasattr(agent, 'inventory'):
                agent.inventory = {}
            
            # Check materials
            for material, amount in materials.items():
                if agent.inventory.get(material, 0) < amount:
                    return {"success": False, "error": f"Insufficient {material}"}
            
            # Consume materials
            for material, amount in materials.items():
                agent.inventory[material] -= amount
                if agent.inventory[material] <= 0:
                    del agent.inventory[material]
            
            # Add crafted item
            agent.inventory[item_name] = agent.inventory.get(item_name, 0) + 1
            
            return {
                "success": True,
                "description": f"Crafted {item_name} using {crafting_method} method",
                "inventory_changes": {item_name: 1, **{mat: -amt for mat, amt in materials.items()}}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def agent_social_interact(self, agent_id: int, target_agent_id: int, interaction_type: str,
                                   message: str, intent: str = "friendly"):
        """Handle social interactions"""
        try:
            agent = self._get_agent(agent_id)
            target = self._get_agent(target_agent_id)
            
            if not agent or not target:
                return {"success": False, "error": "Agent not found"}
            
            # Check distance
            distance = abs(agent.pos[0] - target.pos[0]) + abs(agent.pos[1] - target.pos[1])
            if distance > 2:
                return {"success": False, "error": "Agents too far apart"}
            
            # Simple social interaction
            response = f"Agent {target_agent_id} responds to {interaction_type}: {message}"
            
            return {
                "success": True,
                "description": f"Social interaction with agent {target_agent_id}: {response}",
                "response": response
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def agent_build_structure(self, agent_id: int, structure_type: str, materials: Dict[str, int], 
                                   location: Optional[tuple] = None, description: str = ""):
        """Build permanent structures on the map"""
        try:
            agent = self._get_agent(agent_id)
            if not agent:
                return {"success": False, "error": f"Agent {agent_id} not found"}
            
            if not hasattr(agent, 'inventory'):
                agent.inventory = {}
            
            # Check materials
            for material, amount in materials.items():
                if agent.inventory.get(material, 0) < amount:
                    return {"success": False, "error": f"Insufficient {material}: need {amount}, have {agent.inventory.get(material, 0)}"}
            
            # Use agent's current position if no location specified
            build_location = location or agent.pos
            
            # Consume materials
            for material, amount in materials.items():
                agent.inventory[material] -= amount
                if agent.inventory[material] <= 0:
                    del agent.inventory[material]
            
            # Add structure to world
            if not hasattr(self.world_reference, 'structures'):
                self.world_reference.structures = {}
            
            structure_id = f"{structure_type}_{agent_id}_{build_location[0]}_{build_location[1]}"
            structure_data = {
                'type': structure_type,
                'builder': agent_id,
                'builder_name': getattr(agent, 'name', f'Agent{agent_id}'),
                'location': build_location,
                'materials_used': materials,
                'description': description,
                'built_turn': getattr(self.world_reference, 'turn', 0),
                'durability': 100,
                'benefits': self._get_structure_benefits(structure_type)
            }
            
            self.world_reference.structures[structure_id] = structure_data
            
            return {
                "success": True,
                "description": f"Built {structure_type} at {build_location}: {description}",
                "structure_id": structure_id,
                "inventory_changes": {mat: -amt for mat, amt in materials.items()},
                "world_changes": {"structure_added": structure_data}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def agent_modify_terrain(self, agent_id: int, modification_type: str, area: Dict[str, Any], 
                                  tools_required: List[str] = [], description: str = ""):
        """Modify terrain permanently"""
        try:
            agent = self._get_agent(agent_id)
            if not agent:
                return {"success": False, "error": f"Agent {agent_id} not found"}
            
            # Check if agent has required tools
            for tool in tools_required:
                if agent.inventory.get(tool, 0) < 1:
                    return {"success": False, "error": f"Required tool missing: {tool}"}
            
            # Apply terrain modification
            if not hasattr(self.world_reference, 'terrain_modifications'):
                self.world_reference.terrain_modifications = {}
            
            modification_id = f"{modification_type}_{agent_id}_{area.get('center', agent.pos)[0]}_{area.get('center', agent.pos)[1]}"
            modification_data = {
                'type': modification_type,
                'modifier': agent_id,
                'modifier_name': getattr(agent, 'name', f'Agent{agent_id}'),
                'area': area,
                'description': description,
                'modified_turn': getattr(self.world_reference, 'turn', 0),
                'tools_used': tools_required
            }
            
            self.world_reference.terrain_modifications[modification_id] = modification_data
            
            # Apply specific terrain changes
            if modification_type == "clear_path":
                # Create paths that improve movement
                pass
            elif modification_type == "dig_well":
                # Add water source
                if not hasattr(self.world_reference, 'resources'):
                    self.world_reference.resources = {}
                center = area.get('center', agent.pos)
                if center not in self.world_reference.resources:
                    self.world_reference.resources[center] = {}
                self.world_reference.resources[center]['water'] = 20
            
            return {
                "success": True,
                "description": f"Modified terrain: {modification_type} - {description}",
                "modification_id": modification_id,
                "world_changes": {"terrain_modified": modification_data}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def handle_creative_action(self, agent_id: int, action_description: str, creativity_level: float,
                                   inspiration_source: str, intended_outcome: str, risk_level: str = "medium"):
        """Handle creative actions"""
        try:
            import random
            success = random.random() < (0.3 + creativity_level * 0.4)
            
            if success:
                return {
                    "success": True,
                    "description": f"Creative breakthrough: {intended_outcome}",
                    "innovation": True
                }
            else:
                return {
                    "success": True,
                    "description": f"Creative attempt provided learning experience",
                    "innovation": False
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_structure_benefits(self, structure_type: str) -> Dict[str, Any]:
        """Get benefits provided by different structure types"""
        benefits = {
            'shelter': {
                'provides_protection': True,
                'health_regeneration': 2,
                'storage_capacity': 20,
                'warmth': True
            },
            'workshop': {
                'crafting_bonus': 1.5,
                'tool_efficiency': 1.3,
                'skill_learning_bonus': 1.2
            },
            'storage_pit': {
                'storage_capacity': 50,
                'preservation_bonus': 1.4,
                'shared_access': True
            },
            'watchtower': {
                'vision_range_bonus': 3,
                'early_warning': True,
                'coordination_bonus': 1.2
            },
            'fire_pit': {
                'cooking_capability': True,
                'warmth_radius': 3,
                'tool_improvement': True,
                'social_gathering_point': True
            }
        }
        return benefits.get(structure_type, {})
    
    # Trinity MCP methods
    async def trinity_create_terrain(self, name: str, description: str, movement_cost: float, resources: Dict[str, float], color: str):
        """Create terrain type"""
        return {"success": True, "description": f"Created terrain {name}"}
    
    async def trinity_set_resource_distribution(self, resource_name: str, distribution: Dict[str, float]):
        """Set resource distribution"""
        return {"success": True, "description": f"Set distribution for {resource_name}"}
    
    async def trinity_create_rule(self, rule_name: str, description: str, conditions: list, effects: list, priority: int):
        """Create world rule"""
        return {"success": True, "description": f"Created rule {rule_name}"}
    
    def _get_agent(self, agent_id: int):
        """Get agent by ID"""
        if not self.world_reference or not hasattr(self.world_reference, 'agents'):
            return None
        
        for agent in self.world_reference.agents:
            if agent.aid == agent_id:
                return agent
        return None


def apply_mcp_integration(world_reference=None):
    """Apply MCP integration to the simulation"""
    try:
        logger.info("Applying MCP integration...")
        
        # Initialize MCP-enhanced LLM service
        from .prompts import get_prompt_manager
        prompt_manager = get_prompt_manager()
        mcp_llm_service = init_mcp_llm_service(prompt_manager)
        
        # Create mock MCP client
        mcp_client = MCPClient(world_reference)
        mcp_llm_service.set_mcp_client(mcp_client)
        
        # Patch agent action generation
        _patch_agent_actions(mcp_llm_service)
        
        # Patch Trinity rule generation  
        _patch_trinity_rules(mcp_llm_service)
        
        logger.success("MCP integration applied successfully")
        return mcp_llm_service
        
    except Exception as e:
        logger.error(f"MCP integration failed: {str(e)}")
        return None


def _patch_agent_actions(mcp_llm_service):
    """Patch agent actions to use MCP-enhanced LLM"""
    from . import agent
    
    # No longer storing original method since we don't fallback
    
    async def mcp_enhanced_act(self, world, bible, era_prompt, session, action_handler):
        """MCP-enhanced agent action method"""
        try:
            # Get perception and memory as before
            perception = self.perceive(world, bible)
            memory_summary = {
                "known_agents": [{"id": a["aid"], "name": a["name"], "last_seen": a["last_seen"]} 
                                for a in self.memory.get("agents", [])],
                "known_locations": [{"pos": l["pos"], "terrain": l["terrain"], "last_visited": l["last_visited"]}
                                  for l in self.memory.get("locations", [])]
            }
            
            # Use MCP-enhanced LLM service which returns both action description AND outcome
            action_result = await mcp_llm_service.generate_agent_action_with_mcp(
                self.aid, era_prompt, perception, memory_summary, self.goal, self.skills, session
            )
            
            # Check if this is an MCP result with structured outcome
            if isinstance(action_result, dict) and 'mcp_outcome' in action_result:
                # MCP provided structured outcome - use it directly
                natural_language_action = action_result['action_description']
                mcp_outcome = action_result['mcp_outcome']
                
                # Convert MCP outcome to simulation format
                outcome = {
                    'log': mcp_outcome.get('description', natural_language_action),
                    'position': mcp_outcome.get('position_change'),
                    'inventory': mcp_outcome.get('inventory_changes', {}),
                    'health': mcp_outcome.get('health_change', 0),
                    'energy': mcp_outcome.get('energy_change', 0)
                }
                
                # Remove None values
                outcome = {k: v for k, v in outcome.items() if v is not None}
                
                logger.info(f"MCP action executed directly for agent {self.aid}: {natural_language_action}")
                
            else:
                # MCP didn't provide structured outcome - this indicates an MCP failure
                raise RuntimeError(f"MCP action generation failed for agent {self.aid}. Expected structured MCP outcome but got: {type(action_result)}. This simulation requires MCP integration to function properly.")
            
            self.apply_outcome(outcome)
            
            from .output_formatter import get_formatter
            formatter = get_formatter()
            logger.info(formatter.format_agent_action_complete(self.name, self.aid, natural_language_action))
            
        except Exception as e:
            logger.error(f"MCP-enhanced action failed for agent {self.aid}: {str(e)}")
            raise RuntimeError(f"MCP-enhanced action failed for agent {self.aid}: {str(e)}. This simulation requires MCP integration to function properly.")
    
    # Replace the method
    agent.Agent.act = mcp_enhanced_act
    logger.info("Agent actions patched for MCP")


def _patch_trinity_rules(mcp_llm_service):
    """Patch Trinity rule generation to use MCP-enhanced LLM"""
    try:
        from . import trinity
        
        # No longer storing original methods since we don't fallback
        
        async def mcp_enhanced_generate_rules(self, session):
            """MCP-enhanced Trinity rule generation"""
            try:
                # Use MCP-enhanced LLM service for rule generation
                rules_result = await mcp_llm_service.generate_trinity_rules_with_mcp(
                    self.era_prompt, getattr(self, 'world_size', 64), session
                )
                
                # Apply the generated rules
                if 'terrain_types' in rules_result and rules_result['terrain_types']:
                    self.terrain_types = rules_result['terrain_types']
                else:
                    raise RuntimeError(f"MCP failed to generate terrain types for era '{self.era_prompt}'. This simulation requires MCP integration to function properly.")
                    
                if 'resource_rules' in rules_result and rules_result['resource_rules']:
                    self.resource_rules = rules_result['resource_rules']
                else:
                    raise RuntimeError(f"MCP failed to generate resource rules for era '{self.era_prompt}'. This simulation requires MCP integration to function properly.")
                
                logger.info(f"Trinity rules generated via MCP: {len(self.terrain_types)} terrains, {len(self.resource_rules)} resources")
                
            except Exception as e:
                logger.error(f"MCP Trinity rule generation failed: {str(e)}")
                raise RuntimeError(f"MCP Trinity rule generation failed for era '{self.era_prompt}': {str(e)}. This simulation requires MCP integration to function properly.")
        
        async def mcp_enhanced_adjudicate(self, global_log: List[str], session):
            """MCP-enhanced Trinity adjudication"""
            try:
                # Use MCP for adjudication instead of JSON parsing
                if mcp_llm_service and hasattr(mcp_llm_service, 'mcp_client'):
                    # Analyze the global log and make decisions via MCP tools
                    analysis = {
                        'turn': self.turn,
                        'events': global_log,
                        'era': self.era_prompt,
                        'agent_count': len([e for e in global_log if 'agent' in e.lower()])
                    }
                    
                    # Use MCP tools to make adjudication decisions
                    if analysis['agent_count'] > 5 and self.turn % 10 == 0:
                        # Every 10 turns with many agents, consider adding new rules
                        await mcp_llm_service.mcp_client.trinity_create_rule(
                            f"social_rule_{self.turn}",
                            f"Rule for managing {analysis['agent_count']} agents in {self.era_prompt}",
                            ["large_population", "era_appropriate"],
                            ["social_organization", "resource_management"],
                            1
                        )
                    
                    # Create new skills based on agent activities
                    if any("craft" in event.lower() or "tool" in event.lower() for event in global_log):
                        # Agents are crafting - unlock related skills
                        logger.info("[Trinity MCP] Detected crafting activities - potential new skills")
                    
                    if any("social" in event.lower() or "chat" in event.lower() for event in global_log):
                        # Social activities detected
                        logger.info("[Trinity MCP] Detected social activities - enhancing cooperation")
                    
                    logger.info(f"[Trinity MCP] Adjudicated turn {self.turn} with {len(global_log)} events")
                else:
                    # No MCP client available - this is a critical failure
                    raise RuntimeError("[Trinity MCP] No MCP client available. This simulation requires MCP integration to function properly.")
                
                self.turn += 1
                
            except Exception as e:
                logger.error(f"[Trinity MCP] Adjudication error: {str(e)}")
                raise RuntimeError(f"[Trinity MCP] Adjudication failed: {str(e)}. This simulation requires MCP integration to function properly.")
        
        async def mcp_enhanced_execute_actions(self, world, session):
            """MCP-enhanced Trinity action execution"""
            try:
                # Use MCP for world management instead of JSON parsing
                if mcp_llm_service and hasattr(mcp_llm_service, 'mcp_client'):
                    # Analyze world state
                    alive_agents = [a for a in world.agents if getattr(a, 'health', 0) > 0]
                    resource_count = len(getattr(world, 'resources', {}))
                    
                    # Make decisions based on world state
                    if len(alive_agents) < 5 and resource_count < 50:
                        # Low population and resources - add more resources
                        await mcp_llm_service.mcp_client.trinity_set_resource_distribution(
                            "emergency_food",
                            {"FOREST": 0.5, "GRASSLAND": 0.3}
                        )
                        logger.info("[Trinity MCP] Added emergency resources due to low population")
                    
                    if self.turn % 50 == 0:
                        # Every 50 turns, consider world events
                        await mcp_llm_service.mcp_client.trinity_create_terrain(
                            f"evolved_terrain_{self.turn}",
                            f"Terrain that emerged during turn {self.turn} in {self.era_prompt}",
                            1.0,
                            {"rare_resource": 0.1},
                            "brown"
                        )
                        logger.info(f"[Trinity MCP] Created new terrain evolution at turn {self.turn}")
                    
                    logger.info(f"[Trinity MCP] Executed world management for turn {self.turn}")
                else:
                    # No MCP client available - this is a critical failure
                    raise RuntimeError("[Trinity MCP] No MCP client available for action execution. This simulation requires MCP integration to function properly.")
                
            except Exception as e:
                logger.error(f"[Trinity MCP] Action execution error: {str(e)}")
                raise RuntimeError(f"[Trinity MCP] Action execution failed: {str(e)}. This simulation requires MCP integration to function properly.")
        
        # Replace the methods
        trinity.Trinity._generate_initial_rules = mcp_enhanced_generate_rules
        trinity.Trinity.adjudicate = mcp_enhanced_adjudicate
        trinity.Trinity.execute_actions = mcp_enhanced_execute_actions
        logger.info("Trinity rule generation, adjudication, and action execution patched for MCP")
        
    except Exception as e:
        logger.warning(f"Trinity patching failed: {str(e)}")


# Global MCP service instance
_global_mcp_service = None

def get_global_mcp_service():
    """Get the global MCP service instance"""
    return _global_mcp_service

def set_global_mcp_service(service):
    """Set the global MCP service instance"""
    global _global_mcp_service
    _global_mcp_service = service