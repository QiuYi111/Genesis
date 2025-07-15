"""
Main simulation loop for Project Genesis.
Orchestrates the world, agents, and LLM interactions.
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from loguru import logger
from omegaconf import DictConfig, OmegaConf

from .world import World
from ..agents.base import Agent
from ..llm.providers.mock_provider import MockLLMProvider
from ..llm.providers.base import LLMProvider
from ..trinity.trinity_system import TrinitySystem


@dataclass
class SimulationState:
    """Complete state of the simulation"""
    turn: int = 0
    world_state: Dict[str, Any] = field(default_factory=dict)
    agent_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class Simulation:
    """Main simulation orchestrator"""
    
    def __init__(self, config: DictConfig):
        self.config = config
        self.world = None
        self.agents: Dict[str, Agent] = {}
        self.llm_provider: LLMProvider = None
        self.state = SimulationState()
        self.running = False
        self.paused = False
        
        # Initialize random number generator
        self.rng = random.Random(config.simulation.seed)
        
        # Statistics
        self.stats = {
            "total_turns": 0,
            "start_time": None,
            "end_time": None,
            "agent_actions": [],
            "world_events": [],
            "trinity_actions": [],
            "era_transitions": [],
            "performance_metrics": {
                "avg_llm_response_time": 0.0,
                "llm_calls_per_turn": 0,
                "memory_usage": 0.0,
            }
        }
        
        self._initialize_simulation()
    
    def _initialize_simulation(self):
        """Initialize the simulation components"""
        logger.info("Initializing Project Genesis Simulation...")
        
        # Initialize world
        self.world = World(
            width=self.config.world.width,
            height=self.config.world.height,
            seed=self.config.simulation.seed
        )
        
        # Initialize LLM provider
        self._setup_llm_provider()
        
        # Initialize Trinity system
        self.trinity = TrinitySystem(self.config)
        
        # Initialize agents
        self._create_agents()
        
        logger.info(f"Simulation initialized with {len(self.agents)} agents in a {self.config.world.width}x{self.config.world.height} world")
        logger.info(f"Trinity system initialized - Current era: {self.trinity.get_current_era()}")
    
    def _setup_llm_provider(self):
        """Set up the LLM provider based on configuration"""
        provider_type = self.config.llm.provider
        
        if provider_type == "mock":
            self.llm_provider = MockLLMProvider(seed=self.config.simulation.seed)
            logger.info("Using mock LLM provider for testing")
        else:
            # Placeholder for other providers
            logger.warning(f"Provider '{provider_type}' not implemented, using mock")
            self.llm_provider = MockLLMProvider(seed=self.config.simulation.seed)
    
    def _create_agents(self):
        """Create agents and place them in valid positions"""
        valid_positions = self.world.get_valid_spawn_positions(
            radius=self.config.agents.spawn_radius
        )
        
        if len(valid_positions) < self.config.agents.count:
            logger.warning(f"Only {len(valid_positions)} valid spawn positions available for {self.config.agents.count} agents")
            spawn_positions = valid_positions
        else:
            spawn_positions = self.rng.sample(valid_positions, self.config.agents.count)
        
        for i in range(min(self.config.agents.count, len(spawn_positions))):
            agent = Agent(
                world=self.world,
                position=spawn_positions[i],
                name=f"Agent-{i+1}"
            )
            
            # Add starting inventory from config
            for item_name, quantity in self.config.agents.starting_inventory.items():
                from ..agents.base import Item
                agent.add_item(Item(
                    id=f"starting_{item_name}_{agent.id}",
                    name=item_name,
                    type="resource",
                    quantity=quantity
                ))
            
            self.agents[agent.id] = agent
            logger.debug(f"Created agent {agent.name} at {agent.position}")
    
    async def run_turn(self) -> bool:
        """Run a single simulation turn"""
        if not self.running:
            return False
        
        start_time = time.time()
        turn_events = []
        
        logger.debug(f"=== Turn {self.state.turn + 1} ===")
        
        # Update world state
        self.world.update_climate()
        
        # Process each agent's turn
        agent_actions = []
        for agent_id, agent in self.agents.items():
            if agent.attributes['health'].current <= 0:
                logger.info(f"Agent {agent.name} is deceased")
                continue
                
            action = await self._process_agent_turn(agent)
            if action:
                agent_actions.append({
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "action": action,
                    "position": agent.position
                })
        
        # Trinity system analysis
        simulation_state = {
            'agents': {aid: agent.get_state_summary() for aid, agent in self.agents.items()},
            'world': self.world.get_world_summary(),
            'agent_states': {aid: agent.get_state_summary() for aid, agent in self.agents.items()},
            'total_resources': self.world.get_world_summary()['total_resources'],
            'buildings': list(self.world.buildings.keys()),
            'discovered_technologies': list(set(skill for agent in self.agents.values() 
                                               for skill in agent.skills.keys() 
                                               if agent.skills[skill] > 0.5))
        }
        
        trinity_results = await self.trinity.analyze_turn(
            self.state.turn, simulation_state, self.config.world.width, self.config.world.height
        )
        
        if trinity_results.get('action_taken', False):
            self.stats["trinity_actions"].append({
                'turn': self.state.turn,
                'actions': trinity_results.get('actions', [])
            })
        
        # Handle era transitions
        if 'era_progression' in [action['type'] for action in trinity_results.get('actions', [])]:
            for action in trinity_results.get('actions', []):
                if action['type'] == 'era_progression':
                    self.stats["era_transitions"].append({
                        'turn': self.state.turn,
                        'old_era': action['old_era'],
                        'new_era': action['new_era']
                    })
        
        # Update simulation state
        self.state.turn += 1
        self.state.world_state = self.world.get_world_summary()
        self.state.agent_states = {
            agent_id: agent.get_state_summary()
            for agent_id, agent in self.agents.items()
        }
        
        # Record turn events
        turn_events.extend(agent_actions)
        self.state.events.extend(turn_events)
        
        # Update statistics
        self.stats["total_turns"] = self.state.turn
        self.stats["agent_actions"].extend(agent_actions)
        
        # Log turn summary
        if self.config.output.show_stats:
            self._log_turn_summary()
        
        # Check for simulation end conditions
        if self._check_end_conditions():
            return False
        
        return True
    
    async def _process_agent_turn(self, agent: Agent) -> Optional[Dict[str, Any]]:
        """Process a single agent's turn"""
        try:
            # Update agent needs
            agent.update_needs()
            
            # Get current context for LLM
            context = self._get_agent_context(agent)
            
            # Add Trinity context
            trinity_context = self.trinity.get_trinity_context_for_llm()
            context['trinity_context'] = trinity_context
            
            # Get Trinity event effects
            event_effects = self.trinity.get_event_effects(agent.position, self.state.turn)
            context['event_effects'] = event_effects
            
            # Get available Trinity skills
            available_skills = self.trinity.get_available_skills(
                {k: v.current for k, v in agent.attributes.items()},
                agent.skills,
                {item.name: item.quantity for item in agent.inventory.values()}
            )
            context['available_skills'] = [skill.name for skill in available_skills]
            
            # Get available rules
            agent_context = {
                'position': agent.position,
                'inventory_size': len(agent.inventory),
                'social_connections': len(agent.social_connections),
                'skills': agent.skills
            }
            available_rules = self.trinity.get_available_rules(agent.id, agent_context)
            context['available_rules'] = [rule.name for rule in available_rules]
            
            # Make LLM decision
            decision_start = time.time()
            decision = await self._make_agent_decision(agent, context)
            decision_time = time.time() - decision_start
            
            # Execute the decision
            result = await self._execute_agent_action(agent, decision)
            
            # Record action for Trinity observation
            self.trinity.observe_agent_action(
                self.state.turn, agent.id, 
                {"type": decision.get("action", "unknown"), **decision}, 
                context
            )
            
            return {
                "action": decision.get("action", "unknown"),
                "result": result,
                "decision_time": decision_time,
                "agent_state": agent.state.value
            }
            
        except Exception as e:
            logger.error(f"Error processing agent {agent.name}: {e}")
            return {"action": "error", "error": str(e)}
    
    def _get_agent_context(self, agent: Agent) -> Dict[str, Any]:
        """Get comprehensive context for agent decision making"""
        # Get nearby agents
        nearby_agents = []
        for other_agent in self.agents.values():
            if other_agent.id != agent.id:
                distance = self.world.manhattan_distance(agent.position, other_agent.position)
                if distance <= 5:  # Perception range
                    nearby_agents.append({
                        "id": other_agent.id,
                        "name": other_agent.name,
                        "position": other_agent.position,
                        "distance": distance,
                        "relationship": agent.social_connections.get(other_agent.id, 0.0),
                        "state": other_agent.state.value
                    })
        
        # Get visible resources
        visible_resources = {}
        for resource_type in self.world.resources:
            positions = []
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    x, y = agent.position[0] + dx, agent.position[1] + dy
                    if 0 <= x < self.world.width and 0 <= y < self.world.height:
                        amount = self.world.get_resource_at((x, y), resource_type)
                        if amount > 0.1:
                            positions.append((x, y, amount))
            visible_resources[resource_type] = positions
        
        # Get current terrain and buildings
        current_terrain = self.world.get_terrain_at(agent.position)
        current_building = self.world.get_building_at(agent.position)
        
        return {
            "agent": agent.get_state_summary(),
            "world": {
                "current_turn": self.state.turn,
                "climate": {
                    "temperature": self.world.climate.temperature,
                    "humidity": self.world.climate.humidity
                }
            },
            "nearby_agents": nearby_agents,
            "visible_resources": visible_resources,
            "current_terrain": current_terrain.name,
            "current_building": current_building.to_dict() if current_building else None,
            "valid_moves": self._get_valid_moves(agent)
        }
    
    def _get_valid_moves(self, agent: Agent) -> List[Tuple[int, int]]:
        """Get valid movement positions for an agent"""
        valid = []
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            new_x = agent.position[0] + dx
            new_y = agent.position[1] + dy
            if 0 <= new_x < self.world.width and 0 <= new_y < self.world.height:
                terrain = self.world.get_terrain_at((new_x, new_y))
                if terrain.name != "WATER":
                    valid.append((new_x, new_y))
        return valid
    
    async def _make_agent_decision(self, agent: Agent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to make agent decision"""
        # Create prompt for LLM
        prompt = self._create_agent_prompt(agent, context)
        
        messages = [
            {"role": "system", "content": self._get_system_prompt(agent)},
            {"role": "user", "content": prompt}
        ]
        
        # For now, use simple decision making (will be replaced with proper LLM calls)
        return await self._simple_decision_making(agent, context)
    
    def _get_system_prompt(self, agent: Agent) -> str:
        """Get system prompt for agent personality"""
        return f"""
        You are {agent.name}, an agent in a primitive society simulation.
        
        Your life goals: {', '.join(agent.life_goals)}
        Your current state: {agent.state.value}
        
        Make decisions based on:
        1. Survival needs (food, water, shelter)
        2. Social relationships
        3. Resource availability
        4. Your life goals
        5. Current context
        
        Always provide reasoning for your actions.
        Be realistic and consider your current capabilities.
        """
    
    def _create_agent_prompt(self, agent: Agent, context: Dict[str, Any]) -> str:
        """Create detailed prompt for agent decision"""
        return f"""
        Current situation:
        - Position: {agent.position}
        - Health: {agent.attributes['health'].current:.0f}/100
        - Hunger: {agent.needs['hunger'].current:.0f}/100
        - Thirst: {agent.needs['thirst'].current:.0f}/100
        - Inventory: {len(agent.inventory)} items, {agent.current_inventory_weight:.1f}kg
        
        Nearby:
        - Agents: {len(context['nearby_agents'])}
        - Resources: {sum(len(v) for v in context['visible_resources'].values())}
        - Terrain: {context['current_terrain']}
        
        What action should you take? Consider your needs, available resources, and social context.
        """
    
    async def _simple_decision_making(self, agent: Agent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simple decision making for testing (will be replaced with LLM)"""
        import random
        
        # Simple rules-based decision making
        if agent.needs['hunger'].current > 80:
            return {"action": "gather", "resource": "food", "reasoning": "High hunger"}
        elif agent.needs['thirst'].current > 80:
            return {"action": "gather", "resource": "water", "reasoning": "High thirst"}
        elif agent.current_inventory_weight < 10:
            return {"action": "gather", "resource": "food", "reasoning": "Low inventory"}
        else:
            # Move to explore
            valid_moves = context.get("valid_moves", [])
            if valid_moves:
                target = random.choice(valid_moves)
                return {"action": "move", "target": target, "reasoning": "Exploration"}
            else:
                return {"action": "rest", "reasoning": "No valid moves"}
    
    async def _execute_agent_action(self, agent: Agent, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's chosen action"""
        action = decision.get("action", "idle")
        
        if action == "move":
            target = decision.get("target")
            if target and agent.move_to(target):
                return {"success": True, "action": "move", "new_position": target}
        
        elif action == "gather":
            resource = decision.get("resource")
            if resource:
                amount = min(5.0, agent.attributes['strength'].current * 0.5)
                harvested = self.world.harvest_resource(agent.position, resource, amount)
                if harvested > 0:
                    from ..agents.base import Item
                    agent.add_item(Item(
                        id=f"{resource}_{agent.world.time}_{agent.id}",
                        name=resource,
                        type="resource",
                        quantity=harvested
                    ))
                    return {"success": True, "action": "gather", "resource": resource, "amount": harvested}
        
        elif action == "rest":
            agent.needs['fatigue'].decrease(10)
            agent.attributes['health'].increase(1)
            return {"success": True, "action": "rest", "fatigue_reduced": 10}
        
        return {"success": False, "action": action, "reason": "Action failed or invalid"}
    
    def _log_turn_summary(self):
        """Log summary of the current turn"""
        alive_agents = [a for a in self.agents.values() if a.attributes['health'].current > 0]
        
        logger.info(f"Turn {self.state.turn} summary:")
        logger.info(f"  Alive agents: {len(alive_agents)}/{len(self.agents)}")
        logger.info(f"  World time: {self.world.time}")
        logger.info(f"  Buildings: {len(self.world.buildings)}")
        logger.info(f"  Current era: {self.trinity.get_current_era().value}")
        logger.info(f"  Era progress: {self.trinity.state.era_progress:.0%}")
        
        # Resource summary
        resource_totals = self.world.get_world_summary()["total_resources"]
        logger.info(f"  Total resources: {resource_totals}")
        
        # Trinity summary
        trinity_summary = self.trinity.get_trinity_summary()
        logger.info(f"  Trinity - Skills: {trinity_summary['state']['skills_generated']}, "
                   f"Rules: {trinity_summary['state']['rules_evolved']}, "
                   f"Events: {trinity_summary['state']['events_triggered']}")
    
    def _check_end_conditions(self) -> bool:
        """Check if simulation should end"""
        if self.state.turn >= self.config.runtime.max_turns:
            logger.info(f"Simulation ended: reached max turns ({self.config.runtime.max_turns})")
            return True
        
        alive_agents = [a for a in self.agents.values() if a.attributes['health'].current > 0]
        if len(alive_agents) == 0:
            logger.info("Simulation ended: all agents have perished")
            return True
        
        return False
    
    async def run(self):
        """Run the complete simulation"""
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        logger.info("Starting Project Genesis simulation...")
        
        try:
            while self.running:
                if not self.paused:
                    turn_start = time.time()
                    
                    success = await self.run_turn()
                    if not success:
                        break
                    
                    turn_duration = time.time() - turn_start
                    
                    # Respect turn delay
                    if self.config.runtime.turn_delay > 0:
                        await asyncio.sleep(self.config.runtime.turn_delay)
                
                else:
                    await asyncio.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            raise
        finally:
            self.stats["end_time"] = datetime.now()
            self.running = False
            logger.info("Simulation completed")
    
    def pause(self):
        """Pause the simulation"""
        self.paused = True
        logger.info("Simulation paused")
    
    def resume(self):
        """Resume the simulation"""
        self.paused = False
        logger.info("Simulation resumed")
    
    def stop(self):
        """Stop the simulation"""
        self.running = False
        logger.info("Simulation stopped")
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        """Get comprehensive simulation summary"""
        return {
            "simulation_config": OmegaConf.to_yaml(self.config),
            "final_state": self.state,
            "statistics": self.stats,
            "world_summary": self.world.get_world_summary(),
            "agent_summary": {
                agent_id: agent.get_state_summary()
                for agent_id, agent in self.agents.items()
                if agent.attributes['health'].current > 0
            }
        }
    
    def save_state(self, filepath: str):
        """Save simulation state to file"""
        summary = self.get_simulation_summary()
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"Simulation state saved to {filepath}")


# Test the simulation
if __name__ == "__main__":
    import asyncio
    
    async def test_simulation():
        from omegaconf import OmegaConf
        
        # Load test config
        config = OmegaConf.create({
            "simulation": {
                "name": "Test Simulation",
                "era_prompt": "stone age",
                "seed": 42
            },
            "world": {
                "width": 16,
                "height": 16
            },
            "agents": {
                "count": 3,
                "spawn_radius": 5,
                "starting_inventory": {
                    "food": 5,
                    "water": 5
                }
            },
            "llm": {
                "provider": "mock"
            },
            "runtime": {
                "max_turns": 10,
                "turn_delay": 0.1
            },
            "output": {
                "show_stats": True
            }
        })
        
        simulation = Simulation(config)
        await simulation.run()
        
        # Save results
        simulation.save_state("test_simulation_results.json")
    
    asyncio.run(test_simulation())