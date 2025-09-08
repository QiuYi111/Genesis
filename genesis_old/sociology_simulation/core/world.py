"""Core World implementation with unified event settlement"""
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import random
from loguru import logger

from .protocols import WorldView, TurnResult, BehaviorEvent


class CoreWorldView(WorldView):
    """Implementation of WorldView protocol for agent perception"""
    
    def __init__(self, world: "CoreWorld"):
        self.world = world
    
    def get_visible_tiles(self, pos: Tuple[int, int], radius: int) -> List[Dict[str, Any]]:
        """Get visible tiles around a position"""
        visible_tiles = []
        x0, y0 = pos
        
        for x in range(max(0, x0 - radius), min(self.world.size, x0 + radius + 1)):
            for y in range(max(0, y0 - radius), min(self.world.size, y0 + radius + 1)):
                if max(abs(x - x0), abs(y - y0)) <= radius:
                    visible_tiles.append({
                        "pos": [x, y],
                        "terrain": self.world.map[x][y] if self.world.map else "unknown",
                        "resource": self.world.resources.get((x, y), {})
                    })
        
        return visible_tiles
    
    def get_visible_agents(self, pos: Tuple[int, int], radius: int) -> List[Dict[str, Any]]:
        """Get visible agents around a position"""
        visible_agents = []
        x0, y0 = pos
        
        for agent in self.world.agents:
            if agent.aid != self.world.current_agent_id:  # Don't include self
                ax, ay = agent.pos
                if max(abs(ax - x0), abs(ay - y0)) <= radius:
                    visible_agents.append({
                        "aid": agent.aid,
                        "name": agent.name,
                        "pos": list(agent.pos),
                        "attributes": agent.attributes,
                        "age": agent.age,
                        "charm": agent.charm
                    })
        
        return visible_agents
    
    def get_resource_signals(self) -> Dict[str, float]:
        """Get resource scarcity signals for decision making"""
        if not hasattr(self.world, 'resource_status'):
            return {}
        
        signals = {}
        for resource, status in self.world.resource_status.items():
            # Convert status to scarcity signal (0.0 = abundant, 1.0 = scarce)
            if status == "abundant":
                signals[resource] = 0.2
            elif status == "normal":
                signals[resource] = 0.5
            elif status == "scarce":
                signals[resource] = 0.8
            else:
                signals[resource] = 0.5  # default
        
        return signals


@dataclass
class CoreWorld:
    """Core World implementation with clean architecture"""
    
    size: int
    seed: int
    agents: List[Any] = field(default_factory=list)
    map: Optional[List[List[str]]] = None
    resources: Dict[Tuple[int, int], Dict[str, int]] = field(default_factory=dict)
    resource_status: Dict[str, str] = field(default_factory=dict)
    current_agent_id: Optional[int] = None  # For WorldView context
    
    def __post_init__(self):
        """Initialize world state after creation"""
        random.seed(self.seed)
        self.map = self._generate_basic_terrain()
        self._place_initial_resources()
    
    def _generate_basic_terrain(self) -> List[List[str]]:
        """Generate basic terrain map"""
        # Simple terrain generation for MVP
        terrain_types = ["grassland", "forest", "mountain", "desert", "water"]
        return [[random.choice(terrain_types) for _ in range(self.size)] 
                for _ in range(self.size)]
    
    def _place_initial_resources(self):
        """Place initial resources on the map"""
        # Simple resource placement
        resource_types = ["food", "wood", "stone", "water"]
        
        for x in range(self.size):
            for y in range(self.size):
                if random.random() < 0.3:  # 30% chance of resources
                    self.resources[(x, y)] = {
                        resource: random.randint(1, 5) 
                        for resource in random.sample(resource_types, k=random.randint(1, 3))
                    }
    
    def get_world_view(self) -> CoreWorldView:
        """Get WorldView instance for agent perception"""
        return CoreWorldView(self)
    
    def step(self, turn: int, trinity) -> TurnResult:
        """Process one simulation turn with unified event settlement"""
        logger.info(f"=== TURN {turn} START ===")
        
        events = []
        
        # Process each agent
        for agent in self.agents:
            self.current_agent_id = agent.aid
            
            # Create decision context
            from .protocols import DecisionContext
            context = DecisionContext(
                world_view=self.get_world_view(),
                agent_state={
                    "aid": agent.aid,
                    "pos": agent.pos,
                    "attributes": agent.attributes,
                    "inventory": agent.inventory,
                    "age": agent.age,
                    "goal": agent.goal,
                    "hunger": agent.hunger,
                    "health": agent.health,
                    "skills": agent.skills,
                    "social_connections": agent.social_connections
                },
                turn=turn,
                memory=agent.memory,
                goal=agent.goal
            )
            
            # Agent makes decision (pure function)
            action = agent.decide(context)
            
            # Agent acts and produces events
            behavior_events = agent.act(action, self)
            
            # Apply events with unified settlement
            self._apply_agent_events(agent, behavior_events)
            
            # Collect events for reporting
            for event in behavior_events:
                events.append({
                    "agent_id": event.agent_id,
                    "event_type": event.event_type,
                    "data": event.data
                })
        
        # Let Trinity observe and adjust
        trinity.observe(events)
        trinity_actions = trinity.adjust(self)
        
        # Apply Trinity adjustments
        self._apply_trinity_actions(trinity_actions)
        
        # Regenerate resources
        self._regenerate_resources(trinity_actions.resource_regen_multiplier)
        
        # Compute metrics
        metrics = self._compute_metrics()
        
        return TurnResult(turn=turn, events=events, metrics=metrics)
    
    def _apply_agent_events(self, agent, events: List[BehaviorEvent]):
        """Apply agent behavior events with unified settlement"""
        for event in events:
            if event.event_type == "move":
                new_pos = event.data.get("new_position")
                if new_pos and self._is_valid_position(new_pos):
                    agent.pos = new_pos
                    logger.info(f"Agent {agent.aid} moved to {new_pos}")
            
            elif event.event_type == "forage":
                pos = agent.pos
                resource_type = event.data.get("resource_type")
                amount = event.data.get("amount", 1)
                
                if pos in self.resources and resource_type in self.resources[pos]:
                    available = self.resources[pos][resource_type]
                    collected = min(available, amount)
                    
                    # Update world resources
                    self.resources[pos][resource_type] -= collected
                    if self.resources[pos][resource_type] <= 0:
                        del self.resources[pos][resource_type]
                    
                    # Update agent inventory
                    agent.inventory[resource_type] = agent.inventory.get(resource_type, 0) + collected
                    logger.info(f"Agent {agent.aid} foraged {collected} {resource_type}")
            
            elif event.event_type == "craft":
                recipe = event.data.get("recipe")
                if recipe:
                    self._process_crafting(agent, recipe)
            
            elif event.event_type == "trade":
                trade_data = event.data
                self._process_trade(agent, trade_data)
    
    def _apply_trinity_actions(self, trinity_actions):
        """Apply Trinity's adjustment actions"""
        if trinity_actions.terrain_adjustments:
            for pos, terrain_type in trinity_actions.terrain_adjustments:
                if self._is_valid_position(pos):
                    x, y = pos
                    self.map[x][y] = terrain_type
        
        if trinity_actions.skill_updates:
            # Skill updates would be applied to agents in a real implementation
            pass
    
    def _regenerate_resources(self, multiplier: float = 1.0):
        """Regenerate resources based on Trinity's multiplier"""
        if multiplier <= 0:
            return
        
        # Simple regeneration logic
        resource_types = ["food", "wood", "stone", "water"]
        for x in range(self.size):
            for y in range(self.size):
                if random.random() < 0.1 * multiplier:  # 10% base chance * multiplier
                    resource_type = random.choice(resource_types)
                    amount = random.randint(1, 3)
                    
                    pos = (x, y)
                    if pos not in self.resources:
                        self.resources[pos] = {}
                    self.resources[pos][resource_type] = self.resources[pos].get(resource_type, 0) + amount
    
    def _compute_metrics(self) -> Dict[str, float]:
        """Compute simulation metrics"""
        metrics = {
            "agent_count": len(self.agents),
            "total_inventory_items": sum(sum(agent.inventory.values()) for agent in self.agents),
            "resource_locations": len(self.resources),
            "total_resources": sum(sum(resources.values()) for resources in self.resources.values())
        }
        
        return metrics
    
    def _is_valid_position(self, pos: Tuple[int, int]) -> bool:
        """Check if position is within world bounds"""
        x, y = pos
        return 0 <= x < self.size and 0 <= y < self.size
    
    def _process_crafting(self, agent, recipe: Dict[str, Any]):
        """Process crafting action"""
        # Simple crafting logic - check requirements and produce output
        requirements = recipe.get("requirements", {})
        output = recipe.get("output", {})
        
        # Check if agent has required materials
        can_craft = True
        for item, qty in requirements.items():
            if agent.inventory.get(item, 0) < qty:
                can_craft = False
                break
        
        if can_craft:
            # Consume requirements
            for item, qty in requirements.items():
                agent.inventory[item] -= qty
                if agent.inventory[item] <= 0:
                    del agent.inventory[item]
            
            # Produce output
            for item, qty in output.items():
                agent.inventory[item] = agent.inventory.get(item, 0) + qty
            
            logger.info(f"Agent {agent.aid} crafted {output}")
    
    def _process_trade(self, agent, trade_data: Dict[str, Any]):
        """Process trade action"""
        # This would handle agent-to-agent trading
        # For now, just log the attempt
        logger.info(f"Agent {agent.aid} attempted trade: {trade_data}")
    
    def snapshot(self) -> Dict[str, Any]:
        """Create world snapshot for export/monitoring"""
        return {
            "size": self.size,
            "seed": self.seed,
            "agents": [
                {
                    "aid": agent.aid,
                    "name": agent.name,
                    "pos": agent.pos,
                    "attributes": agent.attributes,
                    "inventory": agent.inventory,
                    "age": agent.age,
                    "health": agent.health,
                    "hunger": agent.hunger,
                    "skills": agent.skills
                }
                for agent in self.agents
            ],
            "terrain": self.map,
            "resources": {str(pos): resources for pos, resources in self.resources.items()},
            "resource_status": self.resource_status
        }