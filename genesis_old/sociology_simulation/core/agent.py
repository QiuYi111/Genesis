"""Core Agent implementation with pure function decision making"""
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import random
from loguru import logger

from .protocols import Action, BehaviorEvent, DecisionContext


@dataclass
class CoreAgent:
    """Core Agent implementation with clean decision logic"""
    
    aid: int
    pos: Tuple[int, int]
    attributes: Dict[str, int] = field(default_factory=dict)
    inventory: Dict[str, int] = field(default_factory=dict)
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
    leadership_score: int = 0
    reputation: Dict[str, int] = field(default_factory=dict)
    
    def decide(self, context: DecisionContext) -> Action:
        """Pure function decision making - no network dependencies"""
        # Get current state from context
        agent_state = context.get_agent_state()
        visible_tiles = context.get_visible_tiles()
        visible_agents = context.get_visible_agents()
        resource_signals = context.get_resource_signals()
        
        # Simple decision logic based on current state
        # This replaces the complex LLM-based decision making with deterministic logic
        
        # Priority 1: Survival - if hungry, look for food
        if agent_state.get("hunger", 0) > 60:
            # Look for food in visible tiles
            for tile in visible_tiles:
                resources = tile.get("resource", {})
                if "food" in resources and resources["food"] > 0:
                    # Move towards food or forage if adjacent
                    tile_pos = tuple(tile["pos"])
                    if self._is_adjacent(self.pos, tile_pos):
                        return Action(type="forage", payload={"resource_type": "food", "amount": 1})
                    else:
                        # Move towards food
                        direction = self._get_direction_towards(self.pos, tile_pos)
                        return Action(type="move", payload={"direction": direction})
        
        # Priority 2: Resource gathering if inventory is low
        inventory = agent_state.get("inventory", {})
        total_items = sum(inventory.values())
        
        if total_items < 5:  # Low inventory threshold
            # Look for any available resources
            for tile in visible_tiles:
                resources = tile.get("resource", {})
                if resources:
                    # Forage the first available resource
                    for resource_type, amount in resources.items():
                        if amount > 0:
                            tile_pos = tuple(tile["pos"])
                            if self._is_adjacent(self.pos, tile_pos):
                                return Action(type="forage", payload={"resource_type": resource_type, "amount": min(amount, 2)})
                            else:
                                direction = self._get_direction_towards(self.pos, tile_pos)
                                return Action(type="move", payload={"direction": direction})
        
        # Priority 3: Exploration if not much to do
        # Random movement with slight preference towards unexplored areas
        if random.random() < 0.7:  # 70% chance to move
            # Prefer moving towards areas with visible resources
            resource_directions = []
            for tile in visible_tiles:
                if tile.get("resource"):
                    tile_pos = tuple(tile["pos"])
                    direction = self._get_direction_towards(self.pos, tile_pos)
                    resource_directions.append(direction)
            
            if resource_directions:
                # Move towards a random resource
                direction = random.choice(resource_directions)
                return Action(type="move", payload={"direction": direction})
            else:
                # Random movement
                directions = ["north", "south", "east", "west"]
                direction = random.choice(directions)
                return Action(type="move", payload={"direction": direction})
        
        # Priority 4: Crafting if have materials
        # Simple crafting: wood + stone -> tool
        if (inventory.get("wood", 0) >= 2 and inventory.get("stone", 0) >= 1):
            return Action(type="craft", payload={
                "recipe": {
                    "requirements": {"wood": 2, "stone": 1},
                    "output": {"tool": 1}
                }
            })
        
        # Default: Wait/rest to conserve energy
        return Action(type="rest", payload={"duration": 1})
    
    def act(self, action: Action, world) -> List[BehaviorEvent]:
        """Execute action and return behavior events for unified settlement"""
        events = []
        
        if action.type == "move":
            direction = action.payload.get("direction", "north")
            new_pos = self._calculate_new_position(self.pos, direction)
            
            if world._is_valid_position(new_pos):
                events.append(BehaviorEvent(
                    agent_id=self.aid,
                    event_type="move",
                    data={"new_position": new_pos, "direction": direction}
                ))
                self.log.append(f"向{direction}移动")
            else:
                self.log.append(f"尝试向{direction}移动但被阻挡")
        
        elif action.type == "forage":
            resource_type = action.payload.get("resource_type", "food")
            amount = action.payload.get("amount", 1)
            
            events.append(BehaviorEvent(
                agent_id=self.aid,
                event_type="forage",
                data={"resource_type": resource_type, "amount": amount}
            ))
            self.log.append(f"采集{resource_type}")
        
        elif action.type == "craft":
            recipe = action.payload.get("recipe", {})
            
            events.append(BehaviorEvent(
                agent_id=self.aid,
                event_type="craft",
                data={"recipe": recipe}
            ))
            
            output_items = recipe.get("output", {})
            item_names = list(output_items.keys())
            self.log.append(f"制作{','.join(item_names)}")
        
        elif action.type == "trade":
            trade_data = action.payload
            events.append(BehaviorEvent(
                agent_id=self.aid,
                event_type="trade",
                data=trade_data
            ))
            self.log.append(f"尝试交易")
        
        elif action.type == "rest":
            duration = action.payload.get("duration", 1)
            # Reduce hunger slightly when resting
            self.hunger = max(0, self.hunger - duration * 0.5)
            self.log.append(f"休息{duration}回合")
        
        # Always increase hunger slightly
        self.hunger = min(100, self.hunger + 1.0)
        
        # Health management
        if self.hunger > 80:
            self.health = max(0, self.health - 2)
        elif self.hunger > 60:
            self.health = max(0, self.health - 1)
        elif self.hunger < 30:
            self.health = min(100, self.health + 0.5)
        
        return events
    
    def _calculate_new_position(self, current_pos: Tuple[int, int], direction: str) -> Tuple[int, int]:
        """Calculate new position based on direction"""
        x, y = current_pos
        
        if direction == "north":
            return (x, y - 1)
        elif direction == "south":
            return (x, y + 1)
        elif direction == "east":
            return (x + 1, y)
        elif direction == "west":
            return (x - 1, y)
        else:
            return current_pos  # Invalid direction, stay put
    
    def _is_adjacent(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        """Check if two positions are adjacent"""
        x1, y1 = pos1
        x2, y2 = pos2
        return abs(x1 - x2) <= 1 and abs(y1 - y2) <= 1 and (x1, y1) != (x2, y2)
    
    def _get_direction_towards(self, from_pos: Tuple[int, int], to_pos: Tuple[int, int]) -> str:
        """Get direction from one position to another"""
        x1, y1 = from_pos
        x2, y2 = to_pos
        
        dx = x2 - x1
        dy = y2 - y1
        
        if abs(dx) > abs(dy):
            return "east" if dx > 0 else "west"
        elif abs(dy) > 0:
            return "south" if dy > 0 else "north"
        else:
            return random.choice(["north", "south", "east", "west"])  # Random if same position
    
    def get_skill_level(self, skill: str) -> int:
        """Get current skill level"""
        return self.skills.get(skill, {}).get("level", 0)
    
    def has_skill(self, skill_name: str, min_level: int = 1) -> bool:
        """Check if agent has a skill at minimum level"""
        return (skill_name in self.skills and 
                self.skills[skill_name]["level"] >= min_level)
    
    def gain_experience(self, skill_name: str, amount: int):
        """Gain experience in a skill"""
        if skill_name not in self.experience:
            self.experience[skill_name] = 0
        
        self.experience[skill_name] += amount
        
        # Simple level-up logic
        current_level = self.get_skill_level(skill_name)
        exp_needed = (current_level + 1) * 10
        
        if self.experience[skill_name] >= exp_needed:
            if skill_name not in self.skills:
                self.skills[skill_name] = {"level": 0, "description": ""}
            self.skills[skill_name]["level"] += 1
            self.experience[skill_name] -= exp_needed
            logger.info(f"Agent {self.aid} advanced {skill_name} to level {self.skills[skill_name]['level']}")
    
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
    
    def get_behavior_data(self) -> Dict[str, Any]:
        """Get agent behavior data for Trinity analysis"""
        return {
            "recent_actions": self.log[-5:] if len(self.log) >= 5 else self.log,
            "inventory_usage": self.inventory,
            "social_interactions": len(self.social_connections),
            "movement_pattern": [],  # Simplified for MVP
            "age": self.age,
            "attributes": self.attributes,
            "current_skills": list(self.skills.keys()),
            "leadership_score": self.leadership_score,
            "reputation": self.reputation
        }