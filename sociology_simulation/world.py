"""World class for sociology simulation"""
from __future__ import annotations
import asyncio
import random
import json
import aiohttp
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
from dataclasses import dataclass
from loguru import logger

from .config import VISION_RADIUS, DEFAULT_TERRAIN, TERRAIN_COLORS, DEFAULT_RESOURCE_RULES
from .enhanced_llm import get_llm_service
from .output_formatter import get_formatter
from .bible import Bible
from .agent import Agent
from .trinity import Trinity
from .terrain_generator import generate_advanced_terrain
from .social_structures import SocialStructureManager
from .cultural_memory import CulturalMemorySystem
from .technology_system import TechnologySystem
from .interaction_system import InteractionSystem
from .economic_system import EconomicSystem, PoliticalSystem
from .web_export import (
    initialize_web_export, save_world_for_web, save_turn_for_web, 
    export_web_data, export_incremental_web_data
)

if TYPE_CHECKING:
    from .world import World

class World:
    """Main simulation world class
    
    Attributes:
        size: World size (square)
        era_prompt: Era description
        num_agents: Number of agents
        agents: List of agents
        pending_interactions: Pending interactions
        bible: Rules manager
        trinity: World rules manager
        map: Terrain map
        resources: Resource distribution
        social_manager: Social structures manager
        cultural_memory: Cultural memory and knowledge system
        tech_system: Technology progression system
        interaction_system: Enhanced interaction system
        economic_system: Economic and trade system
        political_system: Political entities and governance
    """
    def __init__(self, size: int, era_prompt: str, num_agents: int):
        self.size = size
        self.era_prompt = era_prompt
        self.num_agents = num_agents
        self.agents: List[Agent] = []
        self.pending_interactions = []
        self.bible = Bible()
        self.trinity = Trinity(self.bible, era_prompt)
        self.map = None
        self.resources = {}
        self.social_manager = SocialStructureManager()
        self.cultural_memory = CulturalMemorySystem()
        self.tech_system = TechnologySystem()
        self.interaction_system = InteractionSystem()
        self.economic_system = EconomicSystem()
        self.political_system = PoliticalSystem()

    async def initialize(self, session: aiohttp.ClientSession):
        """Initialize world state"""
        self.bible = Bible()
        self.trinity = Trinity(self.bible, self.era_prompt)
        await self.trinity._generate_initial_rules(session)
        while not hasattr(self.trinity, 'resource_rules'):
            await asyncio.sleep(0.1)
        
        logger.info("\n" + "="*40)
        logger.info(f"INITIALIZING WORLD FOR ERA: {self.era_prompt}")
        logger.info("TERRAIN TYPES: " + ", ".join(self.trinity.terrain_types))
        logger.info("RESOURCE RULES:")
        for res, rules in self.trinity.resource_rules.items():
            logger.info(f"  {res.upper()}:")
            for terrain, prob in rules.items():
                logger.info(f"    - {terrain}: {prob*100}% chance")
        logger.info("="*40 + "\n")
        
        self.map = self.generate_realistic_terrain()
        self.resources = {}
        self.place_resources()
        
        resource_counts = {}
        for pos, resources in self.resources.items():
            for resource, count in resources.items():
                resource_counts[resource] = resource_counts.get(resource, 0) + count
        logger.info("INITIAL RESOURCE DISTRIBUTION:")
        for resource, count in sorted(resource_counts.items()):
            logger.info(f"  {resource.upper()}: {count} units")
        logger.info("="*40 + "\n")
        
        # Initialize web export
        initialize_web_export(
            world_size=self.size,
            era_prompt=self.era_prompt,
            num_agents=self.num_agents,
            terrain_types=self.trinity.terrain_types,
            resource_rules=self.trinity.resource_rules
        )
        
        # Save world state for web export
        save_world_for_web(self.map, self.resources)
        
        self.agents = []
        self.pending_interactions = []

        for aid in range(self.num_agents):
            pos = (random.randrange(self.size), random.randrange(self.size))
            attr = {
                "strength": random.randint(1,10),
                "curiosity": random.randint(1,10),
                "charm": random.randint(1,10)
            }
            inv = {
                "wood": random.randint(0,2), 
                "shell": random.randint(0,1),
                "apple": random.randint(0,2),  # Some starting food
                "fish": random.randint(0,1)    # Occasional fish
            }
            age = random.randint(17, 70)
            agent = Agent(aid, pos, attr, inv, age=age)
            self.agents.append(agent)

    def generate_realistic_terrain(self):
        """Generate realistic terrain using advanced algorithms"""
        terrain_types = getattr(self.trinity, "terrain_types", DEFAULT_TERRAIN)
        terrain_colors = getattr(self.trinity, "terrain_colors", {})
        
        # Choose algorithm based on era or randomly
        algorithms = ["noise", "voronoi", "mixed"]
        algorithm = "mixed"  # Default to mixed for best results
        
        # Use a seed based on era for consistency
        seed = hash(self.era_prompt) % 1000000
        
        logger.info(f"Generating terrain using '{algorithm}' algorithm with seed {seed}")
        
        try:
            terrain_map = generate_advanced_terrain(
                size=self.size,
                terrain_types=terrain_types,
                terrain_colors=terrain_colors,
                algorithm=algorithm,
                seed=seed
            )
            logger.success(f"Generated realistic {self.size}x{self.size} terrain map")
            return terrain_map
            
        except Exception as e:
            logger.error(f"Advanced terrain generation failed: {e}")
            logger.info("Falling back to simple terrain generation")
            return self.generate_simple_terrain()
    
    def generate_simple_terrain(self):
        """Fallback: Generate simple terrain map with contiguous regions"""
        terrain_types = getattr(self.trinity, "terrain_types", DEFAULT_TERRAIN)
        map = [["GRASSLAND"] * self.size for _ in range(self.size)]
        
        regions = len(terrain_types)
        region_size = self.size // regions
        
        for i, terrain in enumerate(terrain_types):
            x_start = i * region_size
            x_end = (i + 1) * region_size if i < regions - 1 else self.size
            
            for x in range(x_start, x_end):
                y_start = i * region_size
                y_end = (i + 1) * region_size if i < regions - 1 else self.size
                
                for y in range(y_start, y_end):
                    map[x][y] = terrain
        
        return map

    def place_resources(self):
        """Place resources according to distribution rules"""
        if self.map is None:
            logger.warning("Cannot place resources - world map not initialized")
            return
            
        resource_rules = getattr(self.trinity, "resource_rules", DEFAULT_RESOURCE_RULES)
        
        for resource, terrain_probs in resource_rules.items():
            for terrain, prob in terrain_probs.items():
                for x in range(self.size):
                    for y in range(self.size):
                        if self.map[x][y] == terrain and random.random() < prob:
                            if (x, y) not in self.resources:
                                self.resources[(x, y)] = {}
                            self.resources[(x, y)][resource] = self.resources[(x, y)].get(resource, 0) + 1

    def show_map(self):
        """Display terrain map using matplotlib"""
        if self.map is None:
            logger.warning("Cannot show map - world map not initialized")
            return
            
        # Use Trinity-generated colors, fallback to default colors, then to gray
        def get_terrain_color(terrain_type):
            # First try Trinity-generated colors
            if hasattr(self.trinity, 'terrain_colors') and terrain_type in self.trinity.terrain_colors:
                color = self.trinity.terrain_colors[terrain_type]
                if isinstance(color, list) and len(color) == 3:
                    return tuple(color)
            
            # Fallback to static colors
            if terrain_type in TERRAIN_COLORS:
                return TERRAIN_COLORS[terrain_type]
            
            # Default gray for unknown terrains
            logger.warning(f"Unknown terrain type '{terrain_type}', using gray color")
            return (0.5, 0.5, 0.5)
        
        img = [[get_terrain_color(self.map[x][y]) for y in range(self.size)] for x in range(self.size)]
        import matplotlib.pyplot as plt
        plt.figure(figsize=(6,6))
        plt.title("World Terrain")
        plt.imshow(img)
        plt.axis("off")
        plt.show()

    class ActionHandler:
        """Handles agent actions and interactions"""
        def __init__(self, bible: Bible, world: "World"):
            self.lock = asyncio.Lock()
            self.bible = bible
            self.world = world
            self.courtship_events = []
            self.dead_agents = []
            self.buildings = []
            self.tools = []
            self.creation_rules = {
                "axe": {
                    "required_attributes": {"strength": 5, "curiosity": 3},
                    "required_materials": {"wood": 2, "stone": 1}
                },
                "hut": {
                    "required_attributes": {"strength": 3},
                    "required_materials": {"wood": 5}
                }
            }

        async def resolve(self, action: str, agent: Agent, world: World, era_prompt: str) -> Dict:
            """Resolve natural language actions using enhanced LLM service"""
            formatter = get_formatter()
            attempt_text = f"(age {agent.age}) attempting: {action}"
            logger.info(formatter.format_agent_action(agent.name, agent.aid, attempt_text, None))
            
            # Age-based restrictions
            if "courtship" in action.lower() and agent.age < 18:
                return {"log": "年龄太小无法求偶", "position": list(agent.pos)}
            if "build" in action.lower() and agent.age < 16:
                return {"log": "年龄太小无法建造", "position": list(agent.pos)}

            async with self.lock:
                async with aiohttp.ClientSession() as session:
                    llm_service = get_llm_service()
                    bible_rules = json.dumps(self.bible.get_rules_for_action_handler(), ensure_ascii=False)
                    
                    outcome = await llm_service.resolve_action(
                        bible_rules=bible_rules,
                        agent_id=agent.aid,
                        agent_age=agent.age,
                        agent_attributes=agent.attributes,
                        agent_position=list(agent.pos),
                        agent_inventory=agent.inventory,
                        agent_health=agent.health,
                        agent_hunger=agent.hunger,
                        agent_skills=agent.skills,
                        action=action,
                        session=session
                    )
                    
                    return await self._process_outcome(outcome, agent, world, session, era_prompt)

        def _clean_json_response(self, response: str) -> str:
            """Clean potentially malformed JSON response"""
            if not response:
                return ""
            
            # Remove any text before first { and after last }
            start = response.find('{')
            end = response.rfind('}') + 1
            if start == -1 or end == 0:
                return ""
                
            cleaned = response[start:end]
            
            # Replace single quotes with double quotes
            cleaned = cleaned.replace("'", '"')
            
            # Remove any trailing commas
            cleaned = cleaned.replace(',}', '}').replace(',]', ']')
            
            return cleaned

        def _validate_outcome(self, outcome: Dict, agent: Agent) -> bool:
            """Validate action outcome structure"""
            if not isinstance(outcome, dict):
                return False
                
            if "position" in outcome:
                pos = outcome["position"]
                if not (isinstance(pos, list) and len(pos) == 2 and 
                       all(isinstance(coord, int) for coord in pos)):
                    return False
                    
            if "inventory" in outcome and not isinstance(outcome["inventory"], dict):
                return False
                
            if "attributes" in outcome and not isinstance(outcome["attributes"], dict):
                return False
                
            return True

        async def _process_outcome(self, outcome: Dict, agent: Agent, world: World, 
                                 session: aiohttp.ClientSession, era_prompt: str) -> Dict:
            """Process and record special events from action outcome"""
            logger.info(f"Processing outcome for {agent.name}({agent.aid}):")
            logger.debug(f"Outcome content: {outcome}")
            
            # Safety check: ensure outcome is a dictionary
            if not isinstance(outcome, dict):
                logger.error(f"Outcome is not a dictionary: {type(outcome)} - {outcome}")
                # Convert to dict if possible, otherwise return empty dict
                if isinstance(outcome, list):
                    merged_outcome = {}
                    for item in outcome:
                        if isinstance(item, dict):
                            merged_outcome.update(item)
                    outcome = merged_outcome
                else:
                    outcome = {}
            
            if "courtship_target" in outcome:
                self.courtship_events.append((agent.aid, outcome["courtship_target"]))
                
            if outcome.get("dead", False):
                self.dead_agents.append(agent.aid)
                
            if "build" in outcome:
                building = outcome["build"]
                building["owner"] = agent.aid
                building["position"] = list(agent.pos)
                self.buildings.append(building)
                self.bible.update({
                    f"building_{building['type']}": f"Requires {building.get('materials', 'unknown')}"
                })
                
            if "create_tool" in outcome:
                tool = outcome["create_tool"]
                tool["creator"] = agent.aid
                self.tools.append(tool)
                self.bible.update({
                    f"tool_{tool['type']}": f"Requires {tool.get('materials', 'unknown')} and attributes {tool.get('required_attributes', 'unknown')}"
                })
                
            if "attempt_create" in outcome:
                creation_type = outcome["attempt_create"]["type"]
                proposed_rules = outcome["attempt_create"].get("rules")
                
                if creation_type not in self.creation_rules and proposed_rules:
                    if (isinstance(proposed_rules, dict) and 
                        "required_attributes" in proposed_rules and 
                        "required_materials" in proposed_rules):
                        self.creation_rules[creation_type] = proposed_rules
                        rules = proposed_rules
                    else:
                        return {
                            "log": f"制造{creation_type}失败: 无效的规则格式"
                        }
                elif creation_type in self.creation_rules:
                    rules = self.creation_rules[creation_type]
                else:
                    return {
                        "log": f"制造{creation_type}失败: 未知的制造类型"
                    }
                
                meets_attributes = all(
                    agent.attributes.get(attr, 0) >= val 
                    for attr, val in rules["required_attributes"].items()
                )
                has_materials = all(
                    agent.inventory.get(mat, 0) >= qty 
                    for mat, qty in rules["required_materials"].items()
                )
                
                if meets_attributes and has_materials:
                    for mat, qty in rules["required_materials"].items():
                        agent.inventory[mat] = agent.inventory.get(mat, 0) - qty
                    
                    if creation_type not in ["hut"]:
                        return {
                            "create_tool": {
                                "type": creation_type,
                                "materials": rules["required_materials"],
                                "required_attributes": rules["required_attributes"]
                            },
                            "log": f"成功制造了{creation_type}!"
                        }
                    else:
                        return {
                            "build": {
                                "type": creation_type,
                                "materials": rules["required_materials"]
                            },
                            "log": f"成功建造了{creation_type}!"
                        }
                else:
                    return {
                        "log": f"制造{creation_type}失败: {'属性不足' if not meets_attributes else '材料不足'}"
                    }
            
            if "chat_request" in outcome:
                chat_data = outcome["chat_request"]
                if chat_data and isinstance(chat_data, dict) and "target_id" in chat_data and "topic" in chat_data:
                    # 验证目标智能体存在
                    target_agent = next((a for a in world.agents if a.aid == chat_data["target_id"]), None)
                    if target_agent:
                        world.pending_interactions.append({
                            "source_id": agent.aid,
                            "target_id": chat_data["target_id"],
                            "type": "chat",
                            "content": chat_data["topic"]
                        })
                        return {
                            "log": f"向智能体 {chat_data['target_id']} 发送聊天请求: {chat_data['topic']}"
                        }
                    else:
                        return {
                            "log": f"目标智能体 {chat_data['target_id']} 不存在"
                        }
                else:
                    # 提供更详细的错误信息但不记录为警告
                    if chat_data is None:
                        return {
                            "log": "聊天请求为空，继续其他行动"
                        }
                    else:
                        logger.debug(f"Invalid chat_request format: {chat_data}")
                        return {
                            "log": "聊天请求格式无效，继续其他行动"
                        }
            
            if "exchange_request" in outcome:
                exchange_data = outcome["exchange_request"]
                if (exchange_data and isinstance(exchange_data, dict) and 
                    "target_id" in exchange_data and "offer" in exchange_data and "request" in exchange_data):
                    world.pending_interactions.append({
                        "source_id": agent.aid,
                        "target_id": exchange_data["target_id"],
                        "type": "exchange",
                        "offer": exchange_data["offer"],
                        "request": exchange_data["request"]
                    })
                    return {
                        "log": f"向智能体 {exchange_data['target_id']} 发起交换: {exchange_data['offer']} 换 {exchange_data['request']}"
                    }
                else:
                    logger.warning(f"Invalid exchange_request data: {exchange_data}")
                    return {
                        "log": "交换请求格式无效"
                    }
                
            return outcome
            
        async def generate_chat_response(self, agent: Agent, topic: str, 
                                       era_prompt: str, session: aiohttp.ClientSession) -> str:
            """Generate response to chat request using enhanced LLM service"""
            llm_service = get_llm_service()
            return await llm_service.generate_chat_response(
                era_prompt, agent.age, agent.attributes, agent.inventory, topic, session
            )
        
        def process_courtship_events(self) -> List[Agent]:
            """Process courtship events and create new agents"""
            new_agents = []
            mutual_pairs = set()
            for a, b in self.courtship_events:
                if (b, a) in self.courtship_events:
                    mutual_pairs.add(frozenset([a, b]))
            
            for pair in mutual_pairs:
                agent_ids = list(pair)
                agent1 = next((a for a in self.world.agents if a.aid == agent_ids[0]), None)
                agent2 = next((a for a in self.world.agents if a.aid == agent_ids[1]), None)
                
                if agent1 and agent2:
                    if (agent1.health > 70 and agent2.health > 70 and
                        sum(agent1.inventory.values()) > 5 and 
                        sum(agent2.inventory.values()) > 5 and
                        abs(agent1.age - agent2.age) <= 20 and
                        agent1.age >= 18 and agent2.age >= 18):
                        
                        new_aid = max(a.aid for a in self.world.agents) + 1 if self.world.agents else 0
                        new_pos = (
                            (agent1.pos[0] + agent2.pos[0]) // 2,
                            (agent1.pos[1] + agent2.pos[1]) // 2
                        )
                        new_attr = {
                            "strength": (agent1.attributes.get("strength", 5) + agent2.attributes.get("strength", 5)) // 2,
                            "curiosity": (agent1.attributes.get("curiosity", 5) + agent2.attributes.get("curiosity", 5)) // 2
                        }
                        new_inv = {"fruit": 1, "cloth": 1}
                        
                        new_agent = Agent(new_aid, new_pos, new_attr, new_inv, age=0)
                        new_agents.append(new_agent)
            
            return new_agents
        
        def process_death_events(self, turn_log: list) -> List[Agent]:
            """Process death events and broadcast notifications"""
            dead_agents = []
            for aid in self.dead_agents:
                agent = next((a for a in self.world.agents if a.aid == aid), None)
                if agent:
                    dead_agents.append(agent)
                    turn_log.append(f"{agent.name}({agent.aid}) died in the wild at age {agent.age}!")
                    
                    for other in self.world.agents:
                        if other.aid != aid and max(abs(other.pos[0]-agent.pos[0]), abs(other.pos[1]-agent.pos[1])) <= VISION_RADIUS:
                            other.log.append(f"看到智能体 {agent.aid} 在野外遭遇中死亡！")
            
            return dead_agents

    async def _check_agent_status(self, turn_log: List[str], action_handler: "ActionHandler"):
        """Generate periodic agent status report"""
        status_report = []
        for agent in self.agents:
            status = {
                "aid": agent.aid,
                "age": agent.age,
                "health": agent.health,
                "hunger": agent.hunger,
                "inventory": sum(agent.inventory.values()),
                "log_entries": len(agent.log)
            }
            status_report.append(status)
            
            # Check for critical status
            if agent.health < 30:
                turn_log.append(f"{agent.name}({agent.aid}) is in critical health!")
            if agent.hunger > 80:
                turn_log.append(f"{agent.name}({agent.aid}) is starving!")
                
        return status_report

    async def step(self, session: aiohttp.ClientSession):
        """Process one simulation turn"""
        logger.info(f"\n=== TURN {self.trinity.turn} START ===")
        action_handler = World.ActionHandler(self.bible, self)
        turn_log = []
        
        # Process pending interactions
        new_interactions = []
        for interaction in self.pending_interactions:
            target_agent = next((a for a in self.agents if a.aid == interaction["target_id"]), None)
            if not target_agent:
                continue
                
            if interaction["type"] == "chat":
                response = await action_handler.generate_chat_response(
                    target_agent, 
                    interaction["content"], 
                    self.era_prompt,
                    session
                )
                
                source_agent = next((a for a in self.agents if a.aid == interaction["source_id"]), None)
                if source_agent:
                    source_agent.log.append(f"你向智能体 {target_agent.aid} 询问: {interaction['content']}，回答: {response}")
                    turn_log.append(f"{source_agent.name}({source_agent.aid}) ↔ {target_agent.name}({target_agent.aid}): {interaction['content']} → {response}")
                target_agent.log.append(f"智能体 {interaction['source_id']} 向你询问: {interaction['content']}，你回答: {response}")
                
            elif interaction["type"] == "exchange":
                source_agent = next((a for a in self.agents if a.aid == interaction["source_id"]), None)
                if not source_agent:
                    continue
                    
                # Check if exchange is possible
                can_exchange = True
                for item, qty in interaction["offer"].items():
                    if source_agent.inventory.get(item, 0) < qty:
                        can_exchange = False
                for item, qty in interaction["request"].items():
                    if target_agent.inventory.get(item, 0) < qty:
                        can_exchange = False
                
                if can_exchange:
                    # Perform exchange
                    for item, qty in interaction["offer"].items():
                        source_agent.inventory[item] = source_agent.inventory.get(item, 0) - qty
                        target_agent.inventory[item] = target_agent.inventory.get(item, 0) + qty
                    for item, qty in interaction["request"].items():
                        target_agent.inventory[item] = target_agent.inventory.get(item, 0) - qty
                        source_agent.inventory[item] = source_agent.inventory.get(item, 0) + qty
                    
                    source_agent.log.append(f"成功与智能体 {target_agent.aid} 交换: {interaction['offer']} 换 {interaction['request']}")
                    target_agent.log.append(f"与智能体 {source_agent.aid} 交换: 收到 {interaction['offer']} 付出 {interaction['request']}")
                    turn_log.append(f"{source_agent.name}({source_agent.aid}) ↔ {target_agent.name}({target_agent.aid}): 交换成功")
                else:
                    source_agent.log.append(f"与智能体 {target_agent.aid} 交换失败: 资源不足")
                    target_agent.log.append(f"智能体 {source_agent.aid} 试图交换但资源不足")
                    turn_log.append(f"{source_agent.name}({source_agent.aid}) ↔ {target_agent.name}({target_agent.aid}): 交换失败")
        
        self.pending_interactions = []
        
        # Process all agents
        tasks = []
        for agent in self.agents:
            if not agent.goal:
                await agent.decide_goal(self.era_prompt, session)
            task = agent.act(self, self.bible, self.era_prompt, session, action_handler)
            tasks.append(task)
        
        # Wait for all agents with timeout
        timeout_per_agent = 15.0
        total_timeout = timeout_per_agent * len(tasks)
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=total_timeout)
        except asyncio.TimeoutError:
            completed = sum(1 for task in tasks if task.done())
            logger.warning(f"Agent processing timed out - {completed}/{len(tasks)} agents completed")
        
        # Process special events
        new_agents = action_handler.process_courtship_events()
        dead_agents = action_handler.process_death_events(turn_log)
        
        # Update world state
        self.agents = [a for a in self.agents if a.aid not in {d.aid for d in dead_agents}]
        self.agents.extend(new_agents)
        
        # Age agents and handle hunger/health
        agents_to_remove = []
        for agent in self.agents:
            agent.age += 1
            
            # Try to consume food if hungry
            if agent.hunger > 50:
                food_consumed = self._try_consume_food(agent)
                if food_consumed:
                    turn_log.append(f"{agent.name}({agent.aid}) ate {food_consumed} to reduce hunger")
            
            # More gradual hunger increase based on activity
            base_hunger_increase = 3  # Reduced from 8
            activity_bonus = 1 if hasattr(agent, 'current_action') and agent.current_action else 0
            agent.hunger = min(100, agent.hunger + base_hunger_increase + activity_bonus)
            
            # More forgiving health decrease
            if agent.hunger > 85:  # Only at very high hunger
                agent.health = max(0, agent.health - 8)  # Higher damage but later
            elif agent.hunger > 70:
                agent.health = max(0, agent.health - 3)  # Gradual damage
            elif agent.hunger < 30:  # Bonus for well-fed agents
                agent.health = min(100, agent.health + 1)
            
            # Death handling
            if agent.health == 0:
                turn_log.append(f"{agent.name}({agent.aid}) starved to death at age {agent.age}!")
                agents_to_remove.append(agent)
        
        # Remove dead agents
        for agent in agents_to_remove:
            self.agents.remove(agent)
        
        # Generate status report every 5 turns
        if self.trinity.turn % 5 == 0:
            await self._check_agent_status(turn_log, action_handler)
            self.place_resources()
        
        # Process social structures and group dynamics
        self.social_manager.process_group_actions(self, self.trinity.turn)
        
        # Process cultural evolution and knowledge transfer
        self.cultural_memory.process_cultural_evolution(self, self.trinity.turn)
        
        # Process technology spread and innovation
        self.tech_system.spread_technology(self)
        
        # Process complex interactions
        self.interaction_system.process_interactions(self, self.trinity.turn)
        
        # Suggest and potentially start new interactions
        interaction_suggestions = self.interaction_system.suggest_interactions(self, self.trinity.turn)
        for suggestion in interaction_suggestions[:2]:  # Max 2 new interactions per turn
            if random.random() < suggestion["priority"]:
                interaction = self.interaction_system.initiate_interaction(
                    suggestion["initiator"], suggestion["target"], 
                    suggestion["type"], suggestion["context"], self.trinity.turn
                )
                if interaction:
                    turn_log.append(f"{suggestion['initiator'].name}与{suggestion['target'].name}开始{suggestion['type']}")
        
        # Check for technology discoveries
        for agent in random.sample(self.agents, min(len(self.agents), 3)):  # Max 3 attempts per turn
            if random.random() < 0.1:  # 10% chance per selected agent
                discovery = self.tech_system.attempt_discovery(agent, self, self.trinity.turn)
                if discovery:
                    turn_log.append(f"{agent.name}发明了{discovery.name}!")
        
        # Suggest new group formations
        group_suggestions = self.social_manager.suggest_group_formation(self.agents, self.trinity.turn)
        for suggestion in group_suggestions:
            founder = suggestion["founder"]
            if founder.leadership_score > 30 or random.random() < 0.3:  # Form group
                group = self.social_manager.create_group(
                    founder.aid, 
                    suggestion["type"], 
                    suggestion["purpose"], 
                    self.trinity.turn
                )
                founder.group_id = group.group_id
                
                # Add some partners to the group
                for partner in suggestion["partners"][:2]:  # Max 2 initial partners
                    if random.random() < 0.7:  # 70% chance each partner joins
                        group.add_member(partner.aid)
                        partner.group_id = group.group_id
                        founder.add_social_connection(partner.aid, "group_member", 3)
                        partner.add_social_connection(partner.aid, "group_member", 3)
                
                turn_log.append(f"{founder.name}组建了{group.group_type}: {group.name}")
        
        # Process economic activities
        self.economic_system.process_economic_activity(self, self.trinity.turn)
        
        # Process political activities
        self.political_system.process_political_activities(self, self.trinity.turn)
        
        # Let Trinity adjudicate
        await self.trinity.adjudicate(turn_log, session)
        await self.trinity.execute_actions(self, session)
        
        # Collect conversations for this turn
        conversations = self.get_conversations()
        
        # Save turn data for web export
        events = []
        for agent in self.agents:
            if agent.log:
                events.append(f"{agent.name}({agent.aid}): {agent.log[-1]}")
        
        save_turn_for_web(
            turn_num=self.trinity.turn,
            agents=self.agents,
            conversations=conversations,
            events=events,
            turn_log=turn_log
        )
        
        # Export incremental data every few turns
        exported_file = export_incremental_web_data(self.trinity.turn)
        if exported_file:
            logger.info(f"Web data exported to: {exported_file}")
        
        # Create feedback loops and emergent behavior reports
        emergent_report = self._generate_emergent_behavior_report()
        if emergent_report:
            turn_log.extend(emergent_report)
        
        # Log turn events
        logger.info("\n" + "="*40)
        logger.info(f"TURN SUMMARY - {len(self.agents)} agents alive")
        logger.info(f"Groups: {len(self.social_manager.groups)}, Technologies: {len(self.tech_system.discovered_techs)}")
        logger.info(f"Markets: {len(self.economic_system.markets)}, Political Entities: {len(self.political_system.political_entities)}")
        logger.info(f"Era: {self.tech_system.eras[self.tech_system.current_era].name}")
        for entry in turn_log:
            logger.info(entry)
        logger.info("="*40 + "\n")
        
        # Increment turn counter
        self.trinity.turn += 1

    def get_conversations(self) -> List[str]:
        """Collect and format all conversations from agent logs"""
        conversations = []
        for agent in self.agents:
            for log_entry in agent.log:
                if ("↔" in log_entry or "询问" in log_entry or "回答" in log_entry or 
                    "向" in log_entry and "号" in log_entry and ("问" in log_entry or "说" in log_entry) or
                    "发送聊天请求" in log_entry or "回答:" in log_entry):
                    # Standardize conversation format
                    if "↔" in log_entry:
                        conversations.append(log_entry)
                    elif "向" in log_entry and "号" in log_entry:
                        parts = log_entry.split(":")
                        if len(parts) > 1:
                            conversations.append(f"{agent.name}({agent.aid}) ↔ {parts[1].strip()}")
                        else:
                            conversations.append(log_entry)
                    else:
                        conversations.append(f"{agent.name}({agent.aid}): {log_entry}")
        return conversations
    
    def _generate_emergent_behavior_report(self) -> List[str]:
        """Generate report on emergent behaviors and feedback loops"""
        report = []
        
        # Analyze population dynamics
        if len(self.agents) > self.num_agents * 1.5:
            report.append("人口快速增长，社会承受压力增加")
        elif len(self.agents) < self.num_agents * 0.5:
            report.append("人口下降，社会面临生存挑战")
        
        # Analyze skill diversity
        all_skills = set()
        for agent in self.agents:
            all_skills.update(agent.skills.keys())
        
        if len(all_skills) > 15:
            report.append("技能多样化发展，社会分工出现")
        elif len(all_skills) < 5:
            report.append("技能单一，社会发展受限")
        
        # Analyze social complexity
        total_connections = sum(len(agent.social_connections) for agent in self.agents)
        avg_connections = total_connections / len(self.agents) if self.agents else 0
        
        if avg_connections > 8:
            report.append("社会网络复杂化，信息传播加速")
        elif avg_connections < 2:
            report.append("社会孤立现象严重，合作困难")
        
        # Analyze economic development
        if self.economic_system.economy.economic_health > 0.7:
            report.append("经济繁荣，贸易活跃")
        elif self.economic_system.economy.economic_health < 0.3:
            report.append("经济困难，资源分配不均")
        
        # Analyze technological progress
        tech_progress = self.tech_system.get_era_progress()
        if tech_progress.get("can_advance", False):
            report.append("科技发展迅速，即将进入新时代")
        
        # Analyze political development
        if len(self.political_system.political_entities) > 1:
            report.append("政治组织形成，治理结构出现")
        
        # Analyze cultural development
        total_knowledge = sum(len(knowledge) for knowledge in self.cultural_memory.agent_knowledge.values())
        if total_knowledge > len(self.agents) * 3:
            report.append("知识积累丰富，文化传承活跃")
        
        return report
    
    def _try_consume_food(self, agent) -> Optional[str]:
        """Try to consume food from agent's inventory to reduce hunger"""
        food_items = {
            "fish": 25,      # High nutrition
            "apple": 20,     # Good nutrition
            "fruit": 20,     # Good nutrition
            "berries": 15,   # Medium nutrition
            "bread": 30,     # High nutrition
            "meat": 35,      # Very high nutrition
            "vegetables": 10 # Low nutrition
        }
        
        # Find available food in inventory
        available_food = []
        for food_type, nutrition in food_items.items():
            if agent.inventory.get(food_type, 0) > 0:
                available_food.append((food_type, nutrition))
        
        if not available_food:
            return None
        
        # Choose the most nutritious food available
        available_food.sort(key=lambda x: x[1], reverse=True)
        food_type, nutrition = available_food[0]
        
        # Consume the food
        agent.inventory[food_type] -= 1
        if agent.inventory[food_type] == 0:
            del agent.inventory[food_type]
        
        # Reduce hunger
        agent.hunger = max(0, agent.hunger - nutrition)
        
        # Small health bonus for eating
        if agent.health < 100:
            agent.health = min(100, agent.health + 2)
        
        return food_type
