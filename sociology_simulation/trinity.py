"""Trinity class for generating world rules"""
import asyncio
import random
import json
import aiohttp
from typing import Dict, List, Any
from dataclasses import dataclass
from loguru import logger

from .config import DEFAULT_TERRAIN, DEFAULT_RESOURCE_RULES
from .enhanced_llm import get_llm_service
from .bible import Bible

class Trinity:
    """World rules generator class
    
    Attributes:
        bible: Rules manager
        era_prompt: Era description
        terrain_types: List of terrain types
        resource_rules: Resource distribution rules
        turn: Current turn number
        system_prompt: System prompt for Trinity
    """
    def __init__(self, bible: Bible, era_prompt: str):
        self.bible = bible
        self.era_prompt = era_prompt
        self.terrain_types = DEFAULT_TERRAIN
        self.resource_rules = DEFAULT_RESOURCE_RULES
        self.turn = 0
        self.system_prompt = (
            "You are TRINITY – the omniscient adjudicator of a sociological simulation.\n"
            "Always respect the era context, be fair & impartial (公正公平)."
        )

    async def _generate_initial_rules(self, session: aiohttp.ClientSession):
        """Generate initial terrain and resource rules based on era using enhanced LLM"""
        llm_service = get_llm_service()
        rules = await llm_service.trinity_generate_rules(self.era_prompt, session)
        
        self.terrain_types = rules.get("terrain_types", DEFAULT_TERRAIN)
        self.resource_rules = rules.get("resource_rules", DEFAULT_RESOURCE_RULES)
        logger.success(f"[Trinity] Generated rules for era: {self.era_prompt}")

    async def adjudicate(self, global_log: List[str], session: aiohttp.ClientSession):
        """Adjudicate simulation events and update rules using enhanced LLM"""
        llm_service = get_llm_service()
        data = await llm_service.trinity_adjudicate(
            self.era_prompt, self.turn, global_log, session
        )
        
        if "add_rules" in data:
            self.bible.update(data["add_rules"])
        if "update_resource_rules" in data:
            self.resource_rules.update(data["update_resource_rules"])
            logger.success(f"[Trinity] Updated resource rules: {data['update_resource_rules']}")
        if "change_era" in data and self.turn % 10 == 0:
            self.era_prompt = data["change_era"]
            logger.success(f"[Trinity] Era changed to: {self.era_prompt}")
        
        self.turn += 1

    async def execute_actions(self, world, session: aiohttp.ClientSession):
        """Execute Trinity's ecological management actions using enhanced LLM"""
        # Calculate resource status for Trinity's decision making
        resource_status = self._calculate_resource_status(world)
        
        llm_service = get_llm_service()
        data = await llm_service.trinity_execute_actions(
            self.era_prompt, self.turn, len(world.agents), 
            self.resource_rules, resource_status, session
        )
        
        # Process new action types
        if "update_resource_distribution" in data:
            for resource, terrain_probs in data["update_resource_distribution"].items():
                if resource in self.resource_rules:
                    self.resource_rules[resource].update(terrain_probs)
                else:
                    self.resource_rules[resource] = terrain_probs
            logger.success(f"[Trinity] Updated resource distribution: {data['update_resource_distribution']}")
        
        if "regenerate_resources" in data:
            regenerate_data = data["regenerate_resources"]
            multiplier = regenerate_data.get("probability_multiplier", 1.0)
            specific_resources = regenerate_data.get("specific_resources", [])
            self._regenerate_resources(world, multiplier, specific_resources)
            logger.success(f"[Trinity] Regenerated resources with multiplier {multiplier}")
        
        if "adjust_terrain" in data:
            if world.map is None:
                logger.warning("[Trinity] Cannot adjust terrain - world map not initialized")
            else:
                for pos in data["adjust_terrain"]["positions"]:
                    x, y = pos[0], pos[1]
                    if 0 <= x < world.size and 0 <= y < world.size:
                        world.map[x][y] = data["adjust_terrain"]["new_terrain"]
                logger.success(f"[Trinity] Adjusted terrain at {len(data['adjust_terrain']['positions'])} positions")
        
        if "environmental_influence" in data:
            for agent_id in data["environmental_influence"]["agent_ids"]:
                agent = next((a for a in world.agents if a.aid == agent_id), None)
                if agent:
                    agent.log.append(f"环境影响: {data['environmental_influence']['effect']}")
            logger.success(f"[Trinity] Environmental influence on {len(data['environmental_influence']['agent_ids'])} agents")
        
        if "add_resource_rules" in data:
            self.resource_rules.update(data["add_resource_rules"])
            logger.success(f"[Trinity] Added new resource rules: {data['add_resource_rules']}")
        
        if "climate_change" in data:
            climate_data = data["climate_change"]
            self._apply_climate_change(world, climate_data)
            logger.success(f"[Trinity] Climate change: {climate_data['type']} - {climate_data['effect']}")
    
    def _calculate_resource_status(self, world) -> Dict[str, Any]:
        """Calculate current resource status for Trinity's decision making"""
        resource_counts = {}
        total_tiles = world.size * world.size
        
        # Count current resources
        for pos, resources in world.resources.items():
            for resource, count in resources.items():
                resource_counts[resource] = resource_counts.get(resource, 0) + count
        
        # Calculate resource density and scarcity
        resource_status = {}
        for resource in self.resource_rules.keys():
            count = resource_counts.get(resource, 0)
            density = count / total_tiles
            
            # Calculate expected count based on terrain and probability
            expected = 0
            for terrain, prob in self.resource_rules[resource].items():
                terrain_count = sum(1 for x in range(world.size) for y in range(world.size) 
                                  if world.map and world.map[x][y] == terrain)
                expected += terrain_count * prob
            
            scarcity_ratio = count / max(expected, 1)
            
            resource_status[resource] = {
                "current_count": count,
                "expected_count": int(expected),
                "density": density,
                "scarcity_ratio": scarcity_ratio,
                "status": "abundant" if scarcity_ratio > 1.2 else 
                         "normal" if scarcity_ratio > 0.8 else "scarce"
            }
        
        return resource_status
    
    def _regenerate_resources(self, world, multiplier: float, specific_resources: List[str]):
        """Regenerate resources according to current rules with probability multiplier"""
        if not world.map:
            return
        
        resources_to_regenerate = specific_resources if specific_resources else self.resource_rules.keys()
        
        for resource in resources_to_regenerate:
            if resource not in self.resource_rules:
                continue
                
            terrain_probs = self.resource_rules[resource]
            for terrain, base_prob in terrain_probs.items():
                adjusted_prob = min(1.0, base_prob * multiplier)
                
                # Find all tiles of this terrain type
                for x in range(world.size):
                    for y in range(world.size):
                        if world.map[x][y] == terrain and random.random() < adjusted_prob:
                            if (x, y) not in world.resources:
                                world.resources[(x, y)] = {}
                            world.resources[(x, y)][resource] = world.resources[(x, y)].get(resource, 0) + 1
    
    def _apply_climate_change(self, world, climate_data: Dict[str, str]):
        """Apply climate/seasonal changes to the world"""
        climate_type = climate_data.get("type", "")
        effect = climate_data.get("effect", "")
        
        # Example climate effects - can be expanded
        if "drought" in climate_type.lower():
            # Reduce water-related resources
            for pos, resources in world.resources.items():
                if "water" in resources:
                    resources["water"] = max(0, resources["water"] - 1)
        elif "abundance" in climate_type.lower():
            # Increase plant-related resources slightly
            self._regenerate_resources(world, 1.3, ["wood", "apple", "fruit"])
        
        # Broadcast climate change to all agents
        for agent in world.agents:
            agent.log.append(f"气候变化: {effect}")
