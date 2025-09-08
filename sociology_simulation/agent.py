"""Agent class for sociology simulation"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
import aiohttp
from loguru import logger

if TYPE_CHECKING:
    from .world import World
    from .bible import Bible

from .config import VISION_RADIUS
from .enhanced_llm import get_llm_service
from .output_formatter import get_formatter

@dataclass
class Agent:
    """Represents an intelligent agent in the simulation
    
    Attributes:
        aid: Agent ID
        pos: Current position (x,y)
        attributes: Dictionary of agent attributes
        inventory: Dictionary of items
        age: Agent age
        goal: Personal goal
        name: Agent name
        charm: Charm attribute
        log: Action log
        memory: Memory storage
        hunger: Hunger level (0-100)
        health: Health level (0-100)
    """
    aid: int
    pos: Tuple[int, int]
    attributes: Dict[str, int]
    inventory: Dict[str, int]
    age: int = 0
    goal: str = ""
    name: str = ""
    charm: int = 5
    log: List[str] = field(default_factory=list)
    memory: Dict[str, List[Dict]] = field(default_factory=dict)
    hunger: float = 0.0
    health: int = 100
    skills: Dict[str, Dict] = field(default_factory=dict)
    experience: Dict[str, int] = field(default_factory=dict)
    social_connections: Dict[int, Dict] = field(default_factory=dict)
    group_id: Optional[int] = None
    leadership_score: int = 0
    reputation: Dict[str, int] = field(default_factory=dict)
    numeric_states: Dict[str, float] = field(default_factory=dict)
    # Optional per-action cooldowns (action_name -> remaining turns)
    action_cooldowns: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize basic agent state - skills will be set by Trinity"""
        # Trinity will initialize skills during world setup
        if not self.skills:
            self.skills = {}
        if not self.experience:
            self.experience = {}
        if not self.reputation:
            self.reputation = {"trustworthy": 0, "skilled": 0, "brave": 0, "wise": 0}
        # Seed default numeric states
        if "stamina" not in self.numeric_states:
            # Default stamina pool for optional action costs
            self.numeric_states["stamina"] = 100.0
    
    def add_skill(self, skill_name: str, initial_level: int = 1, description: str = ""):
        """Add a new skill to the agent (called by Trinity)"""
        self.skills[skill_name] = {
            "level": initial_level,
            "experience": 0,
            "description": description,
            "unlocked_turn": 0  # Trinity can set this
        }
        self.experience[skill_name] = 0
        self.log.append(f"获得新技能: {skill_name}!")
        logger.info(f"{self.name}({self.aid}) unlocked new skill: {skill_name}")
    
    def modify_skill(self, skill_name: str, level_change: int = 0, exp_change: int = 0):
        """Modify skill level or experience (called by Trinity)"""
        if skill_name not in self.skills:
            return False
        
        if level_change != 0:
            old_level = self.skills[skill_name]["level"]
            self.skills[skill_name]["level"] = max(0, old_level + level_change)
            if level_change > 0:
                self.log.append(f"{skill_name}技能提升到{self.skills[skill_name]['level']}级!")
                self.leadership_score += level_change
            elif level_change < 0:
                self.log.append(f"{skill_name}技能下降到{self.skills[skill_name]['level']}级")
        
        if exp_change != 0:
            self.experience[skill_name] = max(0, self.experience.get(skill_name, 0) + exp_change)
        
        return True
    
    def remove_skill(self, skill_name: str, reason: str = ""):
        """Remove a skill from the agent (called by Trinity)"""
        if skill_name in self.skills:
            del self.skills[skill_name]
            if skill_name in self.experience:
                del self.experience[skill_name]
            self.log.append(f"失去了技能: {skill_name}" + (f" ({reason})" if reason else ""))
            logger.info(f"{self.name}({self.aid}) lost skill: {skill_name}")

    # === Numeric state management ===
    def set_numeric_state(self, name: str, value: float) -> None:
        """Create or overwrite a numeric state variable"""
        self.numeric_states[name] = float(value)

    def adjust_numeric_state(self, name: str, delta: float) -> float:
        """Adjust a numeric state variable by delta, creating it if missing"""
        new_value = float(self.numeric_states.get(name, 0.0) + delta)
        self.numeric_states[name] = new_value
        return new_value

    def remove_numeric_state(self, name: str) -> None:
        """Remove a numeric state variable if it exists"""
        self.numeric_states.pop(name, None)

    def get_numeric_state(self, name: str) -> float:
        """Get current value of a numeric state variable"""
        return float(self.numeric_states.get(name, 0.0))
    
    def get_skill_level(self, skill: str) -> int:
        """Get current skill level"""
        return self.skills.get(skill, {}).get("level", 0)
    
    def has_skill(self, skill_name: str, min_level: int = 1) -> bool:
        """Check if agent has a skill at minimum level"""
        return (skill_name in self.skills and 
                self.skills[skill_name]["level"] >= min_level)
    
    def get_behavior_data(self) -> Dict:
        """Get agent behavior data for Trinity analysis"""
        return {
            "recent_actions": self.log[-5:] if len(self.log) >= 5 else self.log,
            "inventory_usage": self.inventory,
            "social_interactions": len(self.social_connections),
            "movement_pattern": getattr(self, 'movement_history', []),
            "age": self.age,
            "attributes": self.attributes,
            "current_skills": list(self.skills.keys()),
            "leadership_score": self.leadership_score,
            "reputation": self.reputation
        }
    
    def add_social_connection(self, other_agent_id: int, relationship_type: str, strength: int = 1):
        """Add or strengthen social connection with another agent"""
        if other_agent_id not in self.social_connections:
            self.social_connections[other_agent_id] = {
                "relationship_type": relationship_type,
                "strength": strength,
                "interactions": 0,
                "last_interaction_turn": 0
            }
        else:
            # Strengthen existing connection
            self.social_connections[other_agent_id]["strength"] += strength
            self.social_connections[other_agent_id]["interactions"] += 1
    
    def get_social_influence(self) -> int:
        """Calculate agent's social influence based on connections and reputation"""
        connection_influence = sum(conn["strength"] for conn in self.social_connections.values())
        reputation_influence = sum(self.reputation.values())
        skill_influence = self.get_skill_level("social") * 2 + self.get_skill_level("leadership") * 3
        
        return connection_influence + reputation_influence + skill_influence
    
    async def generate_name(
        self,
        session: aiohttp.ClientSession,
        era: str = "石器时代",
        goal: str = "",
    ):
        """Generate agent name using enhanced LLM service"""
        llm_service = get_llm_service()
        self.name = await llm_service.generate_agent_name(
            era,
            self.attributes,
            self.age,
            session,
            goal=goal,
        )

    async def decide_goal(self, era_prompt: str, session: aiohttp.ClientSession):
        """Determine agent's personal goal using enhanced LLM service"""
        if self.goal:
            return
        
        llm_service = get_llm_service()
        self.goal = await llm_service.generate_agent_goal(
            era_prompt,
            self.attributes,
            self.age,
            self.inventory,
            session,
        )

        await self.generate_name(session, era_prompt, goal=self.goal)

        formatter = get_formatter()
        logger.info(formatter.format_agent_goal(self.name, self.aid, self.goal))

    def perceive(self, world: "World", bible: "Bible") -> Dict:
        """Generate perception dictionary for agent"""
        vis_tiles, vis_agents, pending_interactions = [], [], []
        x0, y0 = self.pos
        
        if world.map is None:
            logger.warning("World map not initialized yet")
            return bible.apply({
                "you": {
                    "aid": self.aid, 
                    "pos": self.pos, 
                    "attributes": self.attributes, 
                    "inventory": self.inventory, 
                    "age": self.age,
                    "goal": self.goal,
                    "hunger": self.hunger,
                    "health": self.health,
                    "skills": {skill: data["level"] for skill, data in self.skills.items()},
                    "social_connections": len(self.social_connections),
                    "leadership_score": self.leadership_score,
                    "reputation": self.reputation
                },
                "visible_tiles": [],
                "visible_agents": []
            })
            
        for x in range(max(0, x0 - VISION_RADIUS), min(world.size, x0 + VISION_RADIUS + 1)):
            for y in range(max(0, y0 - VISION_RADIUS), min(world.size, y0 + VISION_RADIUS + 1)):
                if max(abs(x - x0), abs(y - y0)) <= VISION_RADIUS:
                    vis_tiles.append({
                        "pos": [x, y], 
                        "terrain": world.map[x][y], 
                        "resource": world.resources.get((x, y), {})
                    })
        for agent in world.agents:
            if agent.aid != self.aid and max(abs(agent.pos[0]-x0), abs(agent.pos[1]-y0)) <= VISION_RADIUS:
                vis_agents.append({
                    "aid": agent.aid,
                    "name": agent.name,
                    "pos": list(agent.pos),
                    "attributes": agent.attributes,
                    "age": agent.age,
                    "charm": agent.charm
                })
        
        # Get pending interactions for this agent
        for interaction in world.pending_interactions:
            if interaction["target_id"] == self.aid:
                pending_interactions.append({
                    "source_id": interaction["source_id"],
                    "type": interaction["type"],
                    "content": interaction["content"]
                })
        
        # Store memory information
        if "agents" not in self.memory:
            self.memory["agents"] = []
        if "locations" not in self.memory:
            self.memory["locations"] = []
        
        # Store encountered agent information
        for agent in vis_agents:
            existing = next((a for a in self.memory["agents"] if a["aid"] == agent["aid"]), None)
            if not existing:
                self.memory["agents"].append({
                    "aid": agent["aid"],
                    "name": agent["name"],
                    "attributes": agent["attributes"],
                    "last_seen": self.age,
                    "last_pos": agent["pos"],
                    "interactions": []
                })
            else:
                existing["last_seen"] = self.age
                existing["last_pos"] = agent["pos"]
        
        # Store location information
        for tile in vis_tiles:
            existing = next((loc for loc in self.memory["locations"] if loc["pos"] == tile["pos"]), None)
            if not existing:
                self.memory["locations"].append({
                    "pos": tile["pos"],
                    "terrain": tile["terrain"],
                    "resources": tile.get("resource", {}),
                    "last_visited": self.age
                })
            else:
                existing["resources"] = tile.get("resource", {})
                existing["last_visited"] = self.age
        
        perception = {
            "you": {
                "aid": self.aid, 
                "pos": self.pos, 
                "attributes": self.attributes, 
                "inventory": self.inventory, 
                "age": self.age,
                "goal": self.goal,
                "hunger": self.hunger,
                "health": self.health,
                "skills": {skill: data["level"] for skill, data in self.skills.items()},
                "social_connections": len(self.social_connections),
                "leadership_score": self.leadership_score,
                "reputation": self.reputation
            },
            "visible_tiles": vis_tiles,
            "visible_agents": vis_agents,
        }
        return bible.apply(perception)

    def apply_outcome(self, outcome: Dict):
        """Apply action outcome to agent"""
        if "inventory" in outcome:
            for item, qty in outcome["inventory"].items():
                # Convert string quantities to integers
                try:
                    qty_int = int(qty) if isinstance(qty, str) else qty
                    self.inventory[item] = self.inventory.get(item, 0) + qty_int
                except (ValueError, TypeError):
                    logger.warning(f"Invalid quantity for {item}: {qty}, skipping")
        
        if "attributes" in outcome:
            for attr, val in outcome["attributes"].items():
                # Convert string values to integers/floats
                try:
                    val_num = float(val) if isinstance(val, str) else val
                    self.attributes[attr] = self.attributes.get(attr, 0) + val_num
                except (ValueError, TypeError):
                    logger.warning(f"Invalid attribute value for {attr}: {val}, skipping")
        
        if "position" in outcome:
            new_pos = outcome["position"]
            if (isinstance(new_pos, list) and len(new_pos) == 2 and 
                all(isinstance(coord, int) for coord in new_pos)):
                self.pos = tuple(new_pos)
        
        if "health" in outcome:
            self.health = max(0, min(100, outcome["health"]))
            
        if "hunger" in outcome:
            self.hunger = max(0, min(100, outcome["hunger"]))
        
        # Handle skill experience gains based on action type
        if "skill_experience" in outcome:
            for skill, exp in outcome["skill_experience"].items():
                self.gain_experience(skill, exp)
        
        # Trinity controls all skill changes through specific outcome keys
        if "skill_changes" in outcome:
            for skill_name, changes in outcome["skill_changes"].items():
                if "add" in changes:
                    self.add_skill(skill_name, changes["add"].get("level", 1), 
                                 changes["add"].get("description", ""))
                elif "modify" in changes:
                    self.modify_skill(skill_name, 
                                    changes["modify"].get("level_change", 0),
                                    changes["modify"].get("exp_change", 0))
                elif "remove" in changes:
                    self.remove_skill(skill_name, changes["remove"].get("reason", ""))
        
        if "log" in outcome:
            self.log.append(outcome["log"])
        elif outcome:
            action_desc = "执行了行动"
            if "inventory" in outcome:
                items = ", ".join([f"{item}{qty:+d}" for item, qty in outcome["inventory"].items()])
                action_desc += f"，背包变化: {items}"
            if "attributes" in outcome:
                attrs = ", ".join([f"{attr}{val:+d}" for attr, val in outcome["attributes"].items()])
                action_desc += f"，属性变化: {attrs}"
            self.log.append(f"{action_desc}")

    async def act(self, world: "World", bible: "Bible", era_prompt: str, session: aiohttp.ClientSession, action_handler):
        """Execute agent's action for the turn"""
        perception = self.perceive(world, bible)
        
        # Prepare memory information summary
        memory_summary = {
            "known_agents": [{"id": a["aid"], "name": a["name"], "last_seen": a["last_seen"]} 
                            for a in self.memory.get("agents", [])],
            "known_locations": [{"pos": loc["pos"], "terrain": loc["terrain"], "last_visited": loc["last_visited"]}
                              for loc in self.memory.get("locations", [])]
        }
        
        llm_service = get_llm_service()
        natural_language_action = await llm_service.generate_agent_action(
            era_prompt, perception, memory_summary, self.goal, self.skills, session
        )
        
        outcome = await action_handler.resolve(natural_language_action, self, world, era_prompt)
        self.apply_outcome(outcome)
        formatter = get_formatter()
        logger.info(formatter.format_agent_action_complete(self.name, self.aid, natural_language_action))
