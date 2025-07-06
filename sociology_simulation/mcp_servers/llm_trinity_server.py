#!/usr/bin/env python3
"""
MCP Server for LLM-Driven Trinity (World AI)

This server provides tools for the LLM to act as Trinity - the world AI that
generates rules, manages world events, and drives era progression. The LLM
remains the decision-making engine while using structured tools instead of JSON.
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


class LLMTrinityServer:
    """MCP Server that provides LLM with structured tools for world management"""
    
    def __init__(self):
        self.server = Server("llm-trinity-server")
        self.world_reference = None
        self.trinity_reference = None
        
        # Register tool handlers
        self._register_trinity_tools()
        
    def set_references(self, world, trinity):
        """Set references to world and trinity objects"""
        self.world_reference = world
        self.trinity_reference = trinity
        
    def _register_trinity_tools(self):
        """Register all Trinity tools for LLM to use as world AI"""
        
        @self.server.tool()
        async def create_terrain_type(
            name: str,
            description: str,
            movement_cost_multiplier: float,
            resource_spawn_rates: Dict[str, float],
            color: str = "gray",
            special_properties: List[str] = []
        ) -> List[types.TextContent]:
            """Create a new terrain type for the world
            
            Args:
                name: Terrain type name (e.g., "VOLCANIC_FIELD", "ANCIENT_FOREST")
                description: Rich description of the terrain
                movement_cost_multiplier: How this terrain affects movement (1.0 = normal)
                resource_spawn_rates: Resource probabilities as {resource: probability}
                color: Display color for the terrain
                special_properties: Unique effects (e.g., "causes_fire", "heals_agents")
            
            Returns:
                Confirmation of terrain creation and its effects
            """
            try:
                if not self.trinity_reference:
                    return [types.TextContent(type="text", text="Error: Trinity reference not set")]
                
                # Add to Trinity's terrain types
                if not hasattr(self.trinity_reference, 'terrain_types'):
                    self.trinity_reference.terrain_types = []
                
                if name not in self.trinity_reference.terrain_types:
                    self.trinity_reference.terrain_types.append(name)
                
                # Update resource rules
                if not hasattr(self.trinity_reference, 'resource_rules'):
                    self.trinity_reference.resource_rules = {}
                
                for resource, probability in resource_spawn_rates.items():
                    if resource not in self.trinity_reference.resource_rules:
                        self.trinity_reference.resource_rules[resource] = {}
                    self.trinity_reference.resource_rules[resource][name] = probability
                
                # Update terrain colors if available
                if hasattr(self.trinity_reference, 'terrain_colors'):
                    self.trinity_reference.terrain_colors[name] = color
                
                # Log the creation with rich description
                logger.info(f"Trinity created new terrain: {name} - {description}")
                
                result_text = f"Created terrain '{name}': {description}. "
                result_text += f"Movement cost: {movement_cost_multiplier}x, "
                result_text += f"Resources: {resource_spawn_rates}, "
                result_text += f"Special: {special_properties}"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Terrain creation error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def set_resource_distribution(
            resource_name: str,
            terrain_probabilities: Dict[str, float],
            seasonal_variations: Dict[str, float] = {},
            depletion_rate: float = 0.1,
            regeneration_rate: float = 0.05
        ) -> List[types.TextContent]:
            """Set or update resource distribution across terrains
            
            Args:
                resource_name: Name of the resource (wood, stone, rare_metals, etc.)
                terrain_probabilities: Spawn probability per terrain type
                seasonal_variations: How probability changes by season
                depletion_rate: How fast resources deplete when harvested
                regeneration_rate: How fast resources regenerate naturally
            
            Returns:
                Confirmation of resource distribution update
            """
            try:
                if not self.trinity_reference:
                    return [types.TextContent(type="text", text="Error: Trinity reference not set")]
                
                # Update Trinity's resource rules
                if not hasattr(self.trinity_reference, 'resource_rules'):
                    self.trinity_reference.resource_rules = {}
                
                self.trinity_reference.resource_rules[resource_name] = terrain_probabilities
                
                # Store additional parameters for advanced resource management
                if not hasattr(self.trinity_reference, 'resource_metadata'):
                    self.trinity_reference.resource_metadata = {}
                
                self.trinity_reference.resource_metadata[resource_name] = {
                    'seasonal_variations': seasonal_variations,
                    'depletion_rate': depletion_rate,
                    'regeneration_rate': regeneration_rate
                }
                
                logger.info(f"Trinity updated resource distribution for {resource_name}")
                
                result_text = f"Updated {resource_name} distribution: {terrain_probabilities}. "
                result_text += f"Depletion: {depletion_rate}, Regeneration: {regeneration_rate}"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Resource distribution error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def create_world_rule(
            rule_name: str,
            description: str,
            conditions: List[str],
            effects: List[str],
            priority: int = 1,
            duration: str = "permanent"
        ) -> List[types.TextContent]:
            """Create a new world rule that governs agent behavior and world physics
            
            Args:
                rule_name: Unique name for the rule
                description: What this rule does and why
                conditions: When this rule applies
                effects: What happens when rule is triggered
                priority: Rule priority (higher numbers override lower)
                duration: How long rule lasts (permanent, temporary, conditional)
            
            Returns:
                Confirmation of rule creation and its integration
            """
            try:
                if not self.trinity_reference:
                    return [types.TextContent(type="text", text="Error: Trinity reference not set")]
                
                # Access Trinity's bible for rule storage
                bible = getattr(self.trinity_reference, 'bible', None)
                if not bible:
                    return [types.TextContent(type="text", text="Error: Trinity bible not accessible")]
                
                # Create structured rule entry
                new_rule = {
                    'name': rule_name,
                    'description': description,
                    'conditions': conditions,
                    'effects': effects,
                    'priority': priority,
                    'duration': duration,
                    'created_by': 'trinity_llm',
                    'active': True
                }
                
                # Add to bible rules
                if not hasattr(bible, 'rules'):
                    bible.rules = {}
                bible.rules[rule_name] = new_rule
                
                # Log rule creation
                logger.info(f"Trinity created new world rule: {rule_name} - {description}")
                
                result_text = f"Created world rule '{rule_name}': {description}. "
                result_text += f"Conditions: {conditions}. Effects: {effects}. "
                result_text += f"Priority: {priority}, Duration: {duration}"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Rule creation error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def trigger_world_event(
            event_type: str,
            severity: str,
            affected_area: Optional[Dict[str, Any]] = None,
            description: str = "",
            consequences: List[str] = []
        ) -> List[types.TextContent]:
            """Trigger a world event that affects agents and environment
            
            Args:
                event_type: Type of event (weather, disaster, discovery, social, etc.)
                severity: Impact level (minor, moderate, major, catastrophic)
                affected_area: Geographic area or agent groups affected
                description: Rich description of what happens
                consequences: List of specific effects on world/agents
            
            Returns:
                Event execution results and world state changes
            """
            try:
                if not self.world_reference:
                    return [types.TextContent(type="text", text="Error: World reference not set")]
                
                # Process different event types
                event_results = []
                
                if event_type == "weather":
                    # Weather events affect movement and resource availability
                    weather_effects = {
                        'minor': 0.9, 'moderate': 0.7, 'major': 0.5, 'catastrophic': 0.2
                    }
                    effect_multiplier = weather_effects.get(severity, 1.0)
                    
                    # Apply weather effects to resource generation
                    if hasattr(self.world_reference, 'resources'):
                        affected_positions = affected_area.get('positions', []) if affected_area else []
                        if not affected_positions and hasattr(self.world_reference, 'size'):
                            # Global weather - affect entire world
                            import random
                            for x in range(self.world_reference.size):
                                for y in range(self.world_reference.size):
                                    if random.random() < 0.3:  # 30% of tiles affected
                                        affected_positions.append((x, y))
                        
                        for pos in affected_positions:
                            if pos in self.world_reference.resources:
                                for resource in self.world_reference.resources[pos]:
                                    original = self.world_reference.resources[pos][resource]
                                    self.world_reference.resources[pos][resource] = int(original * effect_multiplier)
                    
                    event_results.append(f"Weather event ({severity}) affected {len(affected_positions)} locations")
                
                elif event_type == "discovery":
                    # Discovery events reveal new resources or technologies
                    if affected_area and 'discovery_type' in affected_area:
                        discovery_type = affected_area['discovery_type']
                        if discovery_type == "resource_vein":
                            # Add new resource deposits
                            import random
                            new_resource = affected_area.get('resource', 'rare_mineral')
                            positions = affected_area.get('positions', [])
                            for pos in positions:
                                if not hasattr(self.world_reference, 'resources'):
                                    self.world_reference.resources = {}
                                if pos not in self.world_reference.resources:
                                    self.world_reference.resources[pos] = {}
                                self.world_reference.resources[pos][new_resource] = random.randint(5, 20)
                            
                            event_results.append(f"Discovered {new_resource} deposits at {len(positions)} locations")
                
                elif event_type == "social":
                    # Social events affect agent relationships and behaviors
                    if affected_area and 'agents' in affected_area:
                        affected_agents = affected_area['agents']
                        relationship_change = {'minor': 1, 'moderate': 3, 'major': 5, 'catastrophic': -10}[severity]
                        
                        for agent_id in affected_agents:
                            agent = self._get_agent(agent_id)
                            if agent and hasattr(agent, 'relationships'):
                                for other_id in agent.relationships:
                                    agent.relationships[other_id] += relationship_change
                        
                        event_results.append(f"Social event affected {len(affected_agents)} agents' relationships")
                
                # Log the event
                logger.info(f"Trinity triggered {event_type} event ({severity}): {description}")
                
                result_text = f"World event triggered: {event_type} ({severity}). "
                result_text += f"Description: {description}. "
                result_text += f"Results: {', '.join(event_results)}. "
                result_text += f"Consequences: {consequences}"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"World event error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def trigger_era_transition(
            new_era: str,
            transition_description: str,
            changes: Dict[str, Any],
            affected_systems: List[str] = ["all"]
        ) -> List[types.TextContent]:
            """Transition to a new historical era with systemic changes
            
            Args:
                new_era: Name of the new era (e.g., "Bronze Age", "Agricultural Revolution")
                transition_description: Rich narrative of how the transition happens
                changes: Specific changes to world systems
                affected_systems: Which systems change (technology, society, environment, etc.)
            
            Returns:
                Era transition results and new world state
            """
            try:
                if not self.trinity_reference:
                    return [types.TextContent(type="text", text="Error: Trinity reference not set")]
                
                # Update era prompt
                old_era = getattr(self.trinity_reference, 'era_prompt', 'Unknown Era')
                self.trinity_reference.era_prompt = new_era
                
                transition_results = []
                
                # Apply technological changes
                if 'technology' in changes:
                    tech_changes = changes['technology']
                    if 'new_crafting_recipes' in tech_changes:
                        # Add new crafting possibilities
                        recipes = tech_changes['new_crafting_recipes']
                        transition_results.append(f"Unlocked {len(recipes)} new crafting recipes")
                    
                    if 'skill_unlocks' in tech_changes:
                        # Make new skills available
                        skills = tech_changes['skill_unlocks']
                        transition_results.append(f"New skills available: {', '.join(skills)}")
                
                # Apply social changes
                if 'society' in changes:
                    social_changes = changes['society']
                    if 'relationship_modifiers' in social_changes:
                        # Change how social interactions work
                        modifiers = social_changes['relationship_modifiers']
                        transition_results.append(f"Social interaction changes: {modifiers}")
                
                # Apply environmental changes
                if 'environment' in changes:
                    env_changes = changes['environment']
                    if 'new_terrains' in env_changes:
                        # Add new terrain types that appear in this era
                        terrains = env_changes['new_terrains']
                        for terrain_data in terrains:
                            # Use the create_terrain_type tool internally
                            await self.create_terrain_type(
                                terrain_data['name'],
                                terrain_data['description'],
                                terrain_data.get('movement_cost', 1.0),
                                terrain_data.get('resources', {}),
                                terrain_data.get('color', 'brown')
                            )
                        transition_results.append(f"New terrains: {[t['name'] for t in terrains]}")
                
                # Update all agents' context with new era
                if self.world_reference and hasattr(self.world_reference, 'agents'):
                    for agent in self.world_reference.agents:
                        # Agents will learn about new era through their next actions
                        if not hasattr(agent, 'era_knowledge'):
                            agent.era_knowledge = []
                        agent.era_knowledge.append({
                            'era': new_era,
                            'transition': transition_description,
                            'learned_at': 'era_transition'
                        })
                
                # Log the major transition
                logger.info(f"Trinity triggered era transition: {old_era} → {new_era}")
                
                result_text = f"Era transition complete: {old_era} → {new_era}. "
                result_text += f"Transition: {transition_description}. "
                result_text += f"Changes applied: {', '.join(transition_results)}. "
                result_text += f"Affected systems: {affected_systems}"
                
                return [types.TextContent(type="text", text=result_text)]
                
            except Exception as e:
                error_msg = f"Era transition error: {str(e)}"
                logger.error(error_msg)
                return [types.TextContent(type="text", text=error_msg)]
        
        @self.server.tool()
        async def analyze_world_state(
            focus_areas: List[str] = ["population", "resources", "technology", "society"],
            analysis_depth: str = "standard"
        ) -> List[types.TextContent]:
            """Analyze current world state to inform Trinity's decisions
            
            Args:
                focus_areas: What aspects to analyze
                analysis_depth: How detailed the analysis should be (basic, standard, deep)
            
            Returns:
                Comprehensive world state analysis for Trinity's decision-making
            """
            try:
                if not self.world_reference:
                    return [types.TextContent(type="text", text="Error: World reference not set")]
                
                analysis_results = {}
                
                # Population analysis
                if "population" in focus_areas:
                    agents = getattr(self.world_reference, 'agents', [])
                    alive_agents = [a for a in agents if getattr(a, 'health', 0) > 0]
                    
                    population_data = {
                        'total_agents': len(alive_agents),
                        'average_health': sum(getattr(a, 'health', 100) for a in alive_agents) / len(alive_agents) if alive_agents else 0,
                        'skill_distribution': {},
                        'location_density': {}
                    }
                    
                    # Analyze skills
                    for agent in alive_agents:
                        if hasattr(agent, 'skills'):
                            for skill, level in agent.skills.items():
                                if skill not in population_data['skill_distribution']:
                                    population_data['skill_distribution'][skill] = []
                                population_data['skill_distribution'][skill].append(level)
                    
                    # Calculate averages
                    for skill in population_data['skill_distribution']:
                        levels = population_data['skill_distribution'][skill]
                        population_data['skill_distribution'][skill] = {
                            'agents_with_skill': len(levels),
                            'average_level': sum(levels) / len(levels),
                            'max_level': max(levels)
                        }
                    
                    analysis_results['population'] = population_data
                
                # Resource analysis
                if "resources" in focus_areas:
                    resources = getattr(self.world_reference, 'resources', {})
                    resource_data = {
                        'total_deposits': len(resources),
                        'resource_types': {},
                        'abundance_map': {}
                    }
                    
                    for pos, deposits in resources.items():
                        for resource, amount in deposits.items():
                            if resource not in resource_data['resource_types']:
                                resource_data['resource_types'][resource] = {
                                    'locations': 0,
                                    'total_amount': 0,
                                    'average_amount': 0
                                }
                            
                            resource_data['resource_types'][resource]['locations'] += 1
                            resource_data['resource_types'][resource]['total_amount'] += amount
                    
                    # Calculate averages
                    for resource in resource_data['resource_types']:
                        data = resource_data['resource_types'][resource]
                        data['average_amount'] = data['total_amount'] / data['locations'] if data['locations'] > 0 else 0
                    
                    analysis_results['resources'] = resource_data
                
                # Technology analysis
                if "technology" in focus_areas:
                    agents = getattr(self.world_reference, 'agents', [])
                    tech_data = {
                        'available_skills': set(),
                        'crafted_items': {},
                        'innovation_potential': 0
                    }
                    
                    for agent in agents:
                        if hasattr(agent, 'skills'):
                            tech_data['available_skills'].update(agent.skills.keys())
                        
                        if hasattr(agent, 'inventory'):
                            for item in agent.inventory:
                                if item not in tech_data['crafted_items']:
                                    tech_data['crafted_items'][item] = 0
                                tech_data['crafted_items'][item] += agent.inventory[item]
                    
                    tech_data['available_skills'] = list(tech_data['available_skills'])
                    tech_data['innovation_potential'] = len(tech_data['available_skills']) * 0.1
                    
                    analysis_results['technology'] = tech_data
                
                # Society analysis
                if "society" in focus_areas:
                    agents = getattr(self.world_reference, 'agents', [])
                    social_data = {
                        'relationship_density': 0,
                        'average_relationship_strength': 0,
                        'social_clusters': 0,
                        'cooperation_level': 'unknown'
                    }
                    
                    total_relationships = 0
                    total_strength = 0
                    
                    for agent in agents:
                        if hasattr(agent, 'relationships'):
                            total_relationships += len(agent.relationships)
                            total_strength += sum(agent.relationships.values())
                    
                    if total_relationships > 0:
                        social_data['relationship_density'] = total_relationships / len(agents) if agents else 0
                        social_data['average_relationship_strength'] = total_strength / total_relationships
                        
                        if social_data['average_relationship_strength'] > 5:
                            social_data['cooperation_level'] = 'high'
                        elif social_data['average_relationship_strength'] > 2:
                            social_data['cooperation_level'] = 'moderate'
                        else:
                            social_data['cooperation_level'] = 'low'
                    
                    analysis_results['society'] = social_data
                
                # Generate analysis summary
                summary = f"World State Analysis ({analysis_depth}):\n"
                for area, data in analysis_results.items():
                    summary += f"\n{area.title()}:\n"
                    if isinstance(data, dict):
                        for key, value in data.items():
                            summary += f"  {key}: {value}\n"
                
                logger.info("Trinity performed world state analysis")
                
                return [types.TextContent(type="text", text=summary)]
                
            except Exception as e:
                error_msg = f"World analysis error: {str(e)}"
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


async def main():
    """Run the LLM Trinity MCP server"""
    server_instance = LLMTrinityServer()
    
    # Setup server
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializeResult(
                server_name="llm-trinity-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())