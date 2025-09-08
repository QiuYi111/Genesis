"""Trinity class for generating world rules"""
import random
import aiohttp
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from loguru import logger

from .config import DEFAULT_TERRAIN, DEFAULT_RESOURCE_RULES
from .enhanced_llm import get_llm_service
from .bible import Bible

if TYPE_CHECKING:
    from .agent import Agent

class Trinity:
    """World rules generator class
    
    Attributes:
        bible: Rules manager
        era_prompt: Era description
        terrain_types: List of terrain types
        resource_rules: Resource distribution rules
        turn: Current turn number
        system_prompt: System prompt for Trinity
        available_skills: All possible skills in the world
        skill_unlock_conditions: Conditions for unlocking skills
    """
    def __init__(self, bible: Bible, era_prompt: str):
        self.bible = bible
        self.era_prompt = era_prompt
        self.terrain_types = DEFAULT_TERRAIN
        self.resource_rules = DEFAULT_RESOURCE_RULES
        self.turn = 0
        # Seed baseline core skills to ensure deterministic availability (Workstream B)
        self.available_skills = {
            "move": {"description": "Move across the map", "category": "core"},
            "gather": {"description": "Gather nearby resources", "category": "core"},
            "consume": {"description": "Consume food to reduce hunger", "category": "core"},
            "trade": {"description": "Trade items with others", "category": "core"},
            "craft": {"description": "Craft tools or items", "category": "core"},
            "build": {"description": "Construct simple buildings", "category": "core"},
        }
        self.skill_unlock_conditions = {}  # skill_name -> unlock_conditions
        self.system_prompt = (
            "You are TRINITY – the omniscient adjudicator of a sociological simulation.\n"
            "You control the skill system, creating new skills and unlocking them for agents.\n"
            "Always respect the era context, be fair & impartial (公正公平)."
        )

    async def _generate_initial_rules(self, session: aiohttp.ClientSession):
        """Generate initial terrain and resource rules based on era using enhanced LLM.

        Resilient: catches LLM errors, validates schema, and preserves defaults on failure.
        """
        try:
            llm_service = get_llm_service()
            rules = await llm_service.trinity_generate_rules(self.era_prompt, session)
        except Exception as e:
            logger.error(f"[Trinity] LLM error generating initial rules: {e}")
            # Keep defaults already set in __init__
            self.terrain_colors = {}
            return

        # Validate and apply results without clearing defaults on invalid payloads
        try:
            terrain_types = rules.get("terrain_types") if isinstance(rules, dict) else None
            if isinstance(terrain_types, list) and all(isinstance(t, str) for t in terrain_types) and len(terrain_types) >= 1:
                self.terrain_types = terrain_types

            resource_rules = rules.get("resource_rules") if isinstance(rules, dict) else None
            if isinstance(resource_rules, dict) and resource_rules:
                # Shallow validate probabilities
                valid = True
                for res, terrains in resource_rules.items():
                    if not isinstance(res, str) or not isinstance(terrains, dict) or not terrains:
                        valid = False
                        break
                    for terr, prob in terrains.items():
                        if not isinstance(terr, str) or not isinstance(prob, (int, float)):
                            valid = False
                            break
                if valid:
                    self.resource_rules = resource_rules

            self.terrain_colors = rules.get("terrain_colors", {}) if isinstance(rules, dict) else {}
            logger.success(f"[Trinity] Generated rules for era: {self.era_prompt}")
        except Exception as e:
            logger.error(f"[Trinity] Invalid rules payload; keeping defaults. Error: {e}")
            self.terrain_colors = {}

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
        
        # Handle skill system updates
        if "skill_updates" in data:
            self._process_skill_updates(data["skill_updates"])
        
        self.turn += 1

    async def execute_actions(self, world, session: aiohttp.ClientSession):
        """Execute Trinity's ecological management actions using enhanced LLM"""
        # Calculate resource status for Trinity's decision making
        resource_status = self._calculate_resource_status(world)
        
        # First, analyze agent behaviors and update skills
        await self.analyze_agent_behaviors(world, session)
        
        llm_service = get_llm_service()
        data = await llm_service.trinity_execute_actions(
            self.era_prompt, self.turn, len(world.agents), 
            self.resource_rules, resource_status, session
        )
        recognized_update = False
        
        # Process new action types
        if "update_resource_distribution" in data:
            for resource, terrain_probs in data["update_resource_distribution"].items():
                if resource in self.resource_rules:
                    self.resource_rules[resource].update(terrain_probs)
                else:
                    self.resource_rules[resource] = terrain_probs
            logger.success(f"[Trinity] Updated resource distribution: {data['update_resource_distribution']}")
            recognized_update = True
        
        if "regenerate_resources" in data:
            regenerate_data = data["regenerate_resources"]
            multiplier = regenerate_data.get("probability_multiplier", 1.0)
            specific_resources = regenerate_data.get("specific_resources", [])
            self._regenerate_resources(world, multiplier, specific_resources)
            logger.success(f"[Trinity] Regenerated resources with multiplier {multiplier}")
            recognized_update = True
        
        if "adjust_terrain" in data:
            if world.map is None:
                logger.warning("[Trinity] Cannot adjust terrain - world map not initialized")
            else:
                for pos in data["adjust_terrain"]["positions"]:
                    x, y = pos[0], pos[1]
                    if 0 <= x < world.size and 0 <= y < world.size:
                        world.map[x][y] = data["adjust_terrain"]["new_terrain"]
                logger.success(f"[Trinity] Adjusted terrain at {len(data['adjust_terrain']['positions'])} positions")
            recognized_update = True
        
        if "environmental_influence" in data:
            for agent_id in data["environmental_influence"]["agent_ids"]:
                agent = next((a for a in world.agents if a.aid == agent_id), None)
                if agent:
                    agent.log.append(f"环境影响: {data['environmental_influence']['effect']}")
            logger.success(f"[Trinity] Environmental influence on {len(data['environmental_influence']['agent_ids'])} agents")
            recognized_update = True
        
        if "add_resource_rules" in data:
            self.resource_rules.update(data["add_resource_rules"])
            logger.success(f"[Trinity] Added new resource rules: {data['add_resource_rules']}")
            recognized_update = True
        
        if "climate_change" in data:
            climate_data = data["climate_change"]
            self._apply_climate_change(world, climate_data)
            logger.success(f"[Trinity] Climate change: {climate_data['type']} - {climate_data['effect']}")
            recognized_update = True

        # Deterministic evolution fallback: if LLM produced nothing actionable, nudge world gently
        if not recognized_update and (self.turn % 3 == 0):
            # Light resource regeneration and a mild climate note
            self._regenerate_resources(world, multiplier=0.4, specific_resources=[])
            self._apply_climate_change(world, {"type": "mild_abundance", "effect": "小幅度资源丰收"})
            logger.info("[Trinity] Applied deterministic fallback: mild regeneration and climate effect")

        # Always suggest reproduction candidates (LLM-assisted path can be added later)
        try:
            suggestions = self._suggest_reproduction_candidates(world)
            # Store suggestions on world for processing in step()
            world.reproduction_suggestions = suggestions
        except Exception as e:
            logger.warning(f"[Trinity] Reproduction suggestion failed: {e}")
    
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

    def _suggest_reproduction_candidates(self, world) -> List[Dict[str, int]]:
        """Heuristically suggest reproduction pairs based on health, inventory and proximity"""
        candidates: List[Dict[str, int]] = []
        agents = list(world.agents)
        # Filter healthy, adult agents with sufficient resources
        adults = [a for a in agents if a.age >= 18 and a.health >= 70 and sum(a.inventory.values()) >= 3]
        # Greedy pairing within proximity
        used = set()
        for a in adults:
            if a.aid in used:
                continue
            # Find nearest compatible partner
            best = None
            best_dist = 9999
            for b in adults:
                if b.aid == a.aid or b.aid in used:
                    continue
                # Proximity check (Chebyshev distance)
                dist = max(abs(a.pos[0] - b.pos[0]), abs(a.pos[1] - b.pos[1]))
                if dist <= 3 and abs(a.age - b.age) <= 20:
                    if dist < best_dist:
                        best_dist = dist
                        best = b
            if best:
                candidates.append({"a": a.aid, "b": best.aid})
                used.add(a.aid)
                used.add(best.aid)
        return candidates
    
    def _process_skill_updates(self, skill_updates: Dict):
        """Process skill system updates from Trinity"""
        if "new_skills" in skill_updates:
            for skill_name, skill_data in skill_updates["new_skills"].items():
                self.available_skills[skill_name] = skill_data
                logger.success(f"[Trinity] Created new skill: {skill_name}")
        
        if "update_unlock_conditions" in skill_updates:
            for skill_name, conditions in skill_updates["update_unlock_conditions"].items():
                self.skill_unlock_conditions[skill_name] = conditions
                logger.info(f"[Trinity] Updated unlock conditions for {skill_name}")
    
    async def analyze_agent_behaviors(self, world, session: aiohttp.ClientSession):
        """Analyze agent behaviors and unlock skills accordingly"""
        # Collect behavior data from all agents
        agent_behaviors = {}
        for agent in world.agents:
            agent_behaviors[agent.aid] = agent.get_behavior_data()
        
        # Ask Trinity to analyze behaviors and determine skill changes
        llm_service = get_llm_service()
        skill_analysis = await llm_service.trinity_analyze_behaviors(
            era_prompt=self.era_prompt,
            turn=self.turn,
            agent_behaviors=agent_behaviors,
            available_skills=self.available_skills,
            unlock_conditions=self.skill_unlock_conditions,
            session=session
        )
        
        # Apply skill changes to agents
        if skill_analysis and "agent_skill_changes" in skill_analysis:
            for agent_id, skill_changes in skill_analysis["agent_skill_changes"].items():
                agent = next((a for a in world.agents if a.aid == int(agent_id)), None)
                if agent:
                    self._apply_skill_changes_to_agent(agent, skill_changes)
        
        # Update global skill system
        if skill_analysis and "global_skill_updates" in skill_analysis:
            self._process_skill_updates(skill_analysis["global_skill_updates"])
        
        return skill_analysis
    
    def _apply_skill_changes_to_agent(self, agent, skill_changes: Dict):
        """Apply skill changes to a specific agent"""
        for skill_name, changes in skill_changes.items():
            if "unlock" in changes:
                if skill_name not in agent.skills:
                    agent.add_skill(skill_name, changes["unlock"].get("level", 1),
                                   changes["unlock"].get("description", ""))
                    logger.info(f"[Trinity] Agent {agent.aid} unlocked skill: {skill_name}")
            
            if "modify" in changes:
                agent.modify_skill(skill_name, 
                                 changes["modify"].get("level_change", 0),
                                 changes["modify"].get("exp_change", 0))
            
            if "remove" in changes:
                agent.remove_skill(skill_name, changes["remove"].get("reason", ""))
                logger.info(f"[Trinity] Agent {agent.aid} lost skill: {skill_name}")

    def update_agent_numeric_state(
        self,
        agent: "Agent",
        updates: Optional[Dict[str, float]] = None,
        deltas: Optional[Dict[str, float]] = None,
        remove: Optional[List[str]] = None,
    ) -> None:
        """Allow Trinity to modify an agent's numeric state variables"""

        if updates:
            for name, value in updates.items():
                agent.set_numeric_state(name, value)

        if deltas:
            for name, delta in deltas.items():
                agent.adjust_numeric_state(name, delta)

        if remove:
            for name in remove:
                agent.remove_numeric_state(name)
