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
from .llm import adeepseek_chat
from .bible import Bible
from .agent import Agent
from .trinity import Trinity

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
        
        self.map = self.generate_contiguous_terrain()
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
        
        self.agents = []
        self.pending_interactions = []

        for aid in range(self.num_agents):
            pos = (random.randrange(self.size), random.randrange(self.size))
            attr = {
                "strength": random.randint(1,10),
                "curiosity": random.randint(1,10),
                "charm": random.randint(1,10)
            }
            inv = {"wood": random.randint(0,2), "shell": random.randint(0,1)}
            age = random.randint(17, 70)
            agent = Agent(aid, pos, attr, inv, age=age)
            self.agents.append(agent)

    def generate_contiguous_terrain(self):
        """Generate terrain map with contiguous regions"""
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
            
        img = [[TERRAIN_COLORS[self.map[x][y]] for y in range(self.size)] for x in range(self.size)]
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
            """Resolve natural language actions using LLM arbitration"""
            logger.info(f"{agent.name}({agent.aid}) (age {agent.age}) attempting action: {action}")
            
            if "courtship" in action.lower() and agent.age < 18:
                return {
                    "log": "年龄太小无法求偶",
                    "position": list(agent.pos)
                }
            if "build" in action.lower() and agent.age < 16:
                return {
                    "log": "年龄太小无法建造",
                    "position": list(agent.pos)
                }

            system = (
                "你是一个行为裁决系统，根据以下要素评估行动结果:\n"
                f"1. 圣经规则: {json.dumps(self.bible.rules, ensure_ascii=False)}\n"
                "2. 智能体属性\n"
                "3. 当前世界状态\n\n"
                "请将自然语言行动转化为严格有效的JSON结果，必须使用双引号，包含以下字段:\n"
                "- 'inventory': 背包变化 {物品: 数量变化}\n"
                "- 'attributes': 属性变化 {属性: 数值变化}\n"
                "- 'position': 新位置 [x, y] (可选)\n"
                "- 'log': 行动日志描述\n"
                "- 'courtship_target': 求偶目标ID (可选)\n"
                "- 'dead': 是否死亡 (可选)\n"
                "- 'chat_request': 聊天请求 {\"target_id\": ID, \"topic\": \"话题\"} (可选)\n"
                "- 'exchange_request': 交换请求 {\"target_id\": ID, \"offer\": {\"物品\": 数量}, \"request\": {\"物品\": 数量}} (可选)\n"
                "示例输出: {\"inventory\": {\"apple\": -1}, \"attributes\": {\"hunger\": -10}, \"log\": \"吃了一个苹果\"}"
                "聊天示例: {\"chat_request\": {\"target_id\": 3, \"topic\": \"草药知识\"}, \"log\": \"询问3号草药知识\"}"
                "交换示例: {\"exchange_request\": {\"target_id\": 2, \"offer\": {\"apple\": 3}, \"request\": {\"fish\": 2}}, \"log\": \"向2号提供3个苹果换取2条鱼\"}"
                "\n\n重要: 必须返回严格有效的JSON，仅包含JSON对象，不要包含任何额外文本或注释!"
            )
            prompt = (
                f"智能体 {agent.aid} (属性: {agent.attributes}) 位于位置 {agent.pos} "
                f"背包: {agent.inventory} 想要执行行动: {action}\n"
                "请评估并返回严格有效的JSON结果:"
            )
            
            async with self.lock:
                async with aiohttp.ClientSession() as session:
                    for attempt in range(3):
                        response = await adeepseek_chat("deepseek-chat", system, prompt, session)
                        
                        # First try parsing as-is
                        try:
                            outcome = json.loads(response) if response else {}
                            if self._validate_outcome(outcome, agent):
                                return await self._process_outcome(outcome, agent, world, session, era_prompt)
                            continue
                        except json.JSONDecodeError:
                            pass
                        
                        # If first parse fails, try cleaning response
                        cleaned = self._clean_json_response(response)
                        try:
                            outcome = json.loads(cleaned) if cleaned else {}
                            if self._validate_outcome(outcome, agent):
                                return await self._process_outcome(outcome, agent, world, session, era_prompt)
                        except json.JSONDecodeError:
                            logger.warning(f"Attempt {attempt+1}: Invalid JSON response")
                    
                    logger.error(f"Failed to get valid JSON after 3 attempts for action: {action}")
                    return {
                        "log": f"行动失败: {action}",
                        "position": list(agent.pos)
                    }

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
                world.pending_interactions.append({
                    "source_id": agent.aid,
                    "target_id": chat_data["target_id"],
                    "type": "chat",
                    "content": chat_data["topic"]
                })
                return {
                    "log": f"向智能体 {chat_data['target_id']} 发送聊天请求: {chat_data['topic']}"
                }
            
            if "exchange_request" in outcome:
                exchange_data = outcome["exchange_request"]
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
                
            return outcome
            
        async def generate_chat_response(self, agent: Agent, topic: str, 
                                       era_prompt: str, session: aiohttp.ClientSession) -> str:
            """Generate response to chat request"""
            system = (
                "你是一个模拟世界中的智能体。另一个智能体向你提出了一个问题或请求。"
                "请根据你的知识、属性和当前状态，用一句话简洁回答。"
            )
            user = (
                f"时代背景: {era_prompt}\n"
                f"你的属性: {json.dumps(agent.attributes, ensure_ascii=False)}\n"
                f"你的背包: {json.dumps(agent.inventory, ensure_ascii=False)}\n"
                f"问题/请求: {topic}\n"
                "请用一句话回答:"
            )
            return await adeepseek_chat("deepseek-chat", system, user, session)
        
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
        
        # Age agents and handle hunger
        for agent in self.agents:
            agent.age += 1
            agent.hunger = min(100, agent.hunger + 8)
            if agent.hunger > 70:
                agent.health = max(0, agent.health - 5)
                if agent.health == 0:
                    turn_log.append(f"{agent.name}({agent.aid}) starved to death at age {agent.age}!")
                    self.agents.remove(agent)
        
        # Generate status report every 5 turns
        if self.trinity.turn % 5 == 0:
            await self._check_agent_status(turn_log, action_handler)
            self.place_resources()
        
        # Let Trinity adjudicate
        await self.trinity.adjudicate(turn_log, session)
        await self.trinity.execute_actions(self, session)
        
        # Log turn events
        logger.info("\n" + "="*40)
        logger.info(f"TURN SUMMARY - {len(self.agents)} agents alive")
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
