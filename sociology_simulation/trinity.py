"""Trinity class for generating world rules"""
import asyncio
import random
import json
import aiohttp
from typing import Dict, List
from dataclasses import dataclass
from loguru import logger

from .config import DEFAULT_TERRAIN, DEFAULT_RESOURCE_RULES
from .llm import adeepseek_chat
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
        """Generate initial terrain and resource rules based on era using LLM"""
        system = (
            "You are TRINITY - the world builder for a sociological simulation. "
            "Generate appropriate terrain types and resource distribution rules "
            "based on the given era description. Return valid JSON only."
        )
        user = (
            f"Era description: {self.era_prompt}\n"
            "Return JSON with:\n"
            "- 'terrain_types': array of terrain names\n"
            "- 'resource_rules': dict mapping resources to terrain probabilities\n"
            "For dangerous/magical eras, include rare and dangerous resources."
        )
        
        # Try up to 3 times to get valid rules
        for attempt in range(3):
            resp = await adeepseek_chat("deepseek-chat", system, user, session, temperature=0.7)
            try:
                rules = json.loads(resp)
                self.terrain_types = rules.get("terrain_types", DEFAULT_TERRAIN)
                self.resource_rules = rules.get("resource_rules", DEFAULT_RESOURCE_RULES)
                logger.success(f"[Trinity] Generated rules for era: {self.era_prompt}")
                return
            except json.JSONDecodeError:
                if attempt < 2:
                    logger.warning(f"[Trinity] Attempt {attempt+1}: Invalid rules JSON, retrying...")
                else:
                    logger.warning("[Trinity] Using default rules after 3 failures")
                    self.terrain_types = DEFAULT_TERRAIN
                    self.resource_rules = DEFAULT_RESOURCE_RULES

    async def adjudicate(self, global_log: List[str], session: aiohttp.ClientSession):
        """Adjudicate simulation events and update rules"""
        user = (
            f"时代背景: {self.era_prompt}\n"
            f"TURN {self.turn} global log:\n" + "\n".join(global_log) + "\n"
            "Based on these events, decide if:\n"
            "1. A new rule should be added\n"
            "2. Resource distribution rules should be updated\n"
            "3. The era should change (only if turn is multiple of 10)\n"
            "Return VALID JSON ONLY with one of these structures:\n"
            "1. Add rules: {\"add_rules\": {\"rule_name\": \"description\"}}\n"
            "2. Update resource distribution: {\"update_resource_rules\": {\"resource_name\": {\"terrain1\": probability, \"terrain2\": probability}}}\n"
            "3. Change era: {\"change_era\": \"new era name\"}\n"
            "4. Any combination of the above\n"
            "5. No change: {}\n"
            "DO NOT include any additional text outside the JSON object."
        )
        
        # Try up to 3 times to get valid JSON
        for attempt in range(3):
            resp = await adeepseek_chat("deepseek-chat", self.system_prompt, user, session, temperature=0.2)
            try:
                data = json.loads(resp)
                if "add_rules" in data:
                    self.bible.update(data["add_rules"])
                if "update_resource_rules" in data:
                    self.resource_rules.update(data["update_resource_rules"])
                    logger.success(f"[Trinity] Updated resource rules: {data['update_resource_rules']}")
                if "change_era" in data and self.turn % 10 == 0:
                    self.era_prompt = data["change_era"]
                    logger.success(f"[Trinity] Era changed to: {self.era_prompt}")
                break  # Exit loop if successful
            except json.JSONDecodeError:
                if attempt < 2:
                    logger.warning(f"[Trinity] Attempt {attempt+1}: Invalid JSON, retrying...")
                else:
                    logger.warning(f"[Trinity] Final attempt failed. Raw response: {resp[:200]}")
        self.turn += 1

    async def execute_actions(self, world, session: aiohttp.ClientSession):
        """Execute Trinity's actions at the end of each turn"""
        system = (
            "You are TRINITY - the omniscient adjudicator of a sociological simulation.\n"
            "Based on the current state of the world, decide what actions to take to maintain balance.\n"
            "Possible actions include:\n"
            "1. Spawning new resources\n"
            "2. Adjusting terrain\n"
            "3. Directly influencing agents\n"
            "4. Adding new resource rules\n"
            "Return VALID JSON ONLY with one of these structures:\n"
            "1. Spawn resources: {\"spawn_resources\": {\"resource_name\": quantity}}\n"
            "2. Adjust terrain: {\"adjust_terrain\": {\"positions\": [[x1,y1],...], \"new_terrain\": \"type\"}}\n"
            "3. Influence agents: {\"influence_agents\": {\"agent_ids\": [id1,id2,...], \"effect\": \"description\"}}\n"
            "4. Add resource rules: {\"add_resource_rules\": {\"resource_name\": {\"terrain1\": probability, \"terrain2\": probability}}}\n"
            "5. Any combination of the above\n"
            "6. No action: {}\n"
            "DO NOT include any additional text outside the JSON object."
        )
        
        user = (
            f"Current era: {self.era_prompt}\n"
            f"Current turn: {self.turn}\n"
            f"Number of agents: {len(world.agents)}\n"
            f"Current resource rules: {json.dumps(self.resource_rules, ensure_ascii=False)}\n"
            "What actions should TRINITY take this turn?"
        )
        
        # Try up to 3 times to get valid JSON
        for attempt in range(3):
            resp = await adeepseek_chat("deepseek-chat", system, user, session, temperature=0.3)
            try:
                data = json.loads(resp)
                if "spawn_resources" in data:
                    for resource, quantity in data["spawn_resources"].items():
                        for _ in range(quantity):
                            x, y = random.randint(0, world.size-1), random.randint(0, world.size-1)
                            if (x,y) not in world.resources:
                                world.resources[(x,y)] = {}
                            world.resources[(x,y)][resource] = world.resources[(x,y)].get(resource, 0) + 1
                    logger.success(f"[Trinity] Spawned resources: {data['spawn_resources']}")
                
                if "adjust_terrain" in data:
                    if world.map is None:
                        logger.warning("[Trinity] Cannot adjust terrain - world map not initialized")
                    else:
                        for pos in data["adjust_terrain"]["positions"]:
                            x, y = pos[0], pos[1]
                            if 0 <= x < world.size and 0 <= y < world.size:
                                world.map[x][y] = data["adjust_terrain"]["new_terrain"]
                        logger.success(f"[Trinity] Adjusted terrain at {len(data['adjust_terrain']['positions'])} positions")
                
                if "influence_agents" in data:
                    for agent_id in data["influence_agents"]["agent_ids"]:
                        agent = next((a for a in world.agents if a.aid == agent_id), None)
                        if agent:
                            agent.log.append(f"TRINITY干预: {data['influence_agents']['effect']}")
                    logger.success(f"[Trinity] Influenced {len(data['influence_agents']['agent_ids'])} agents")
                
                if "add_resource_rules" in data:
                    self.resource_rules.update(data["add_resource_rules"])
                    logger.success(f"[Trinity] Added new resource rules: {data['add_resource_rules']}")
                
                break  # Exit loop if successful
            except json.JSONDecodeError:
                if attempt < 2:
                    logger.warning(f"[Trinity] Attempt {attempt+1}: Invalid JSON, retrying...")
                else:
                    logger.warning(f"[Trinity] Final attempt failed. Raw response: {resp[:200]}")
