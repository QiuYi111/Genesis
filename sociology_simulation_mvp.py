#!/usr/bin/env python3
"""
Sociological Simulation MVP ++ (Terrain viz • Local Perception • Goals)
=====================================================================
A runnable minimal‑viable prototype with **terrain visualisation, 5‑tile vision, inter‑agent
interaction, and attribute‑driven personal goals** – all powered by DeepSeek.

Requirements
------------
```bash
pip install openai>=1.3.0 loguru matplotlib
export DEEPSEEK_API_KEY="sk‑..."
```

Quick Start
-----------
```bash
python sociology_simulation_mvp.py            # run 10 turns, shows map once
python sociology_simulation_mvp.py --turns 50 --show-map-every 10
```

Key Features Added
------------------
* **Terrain display** – `World.show_map()` pops a matplotlib window colouring FOREST 🌲, OCEAN 🌊, HILL ⛰️.
* **5‑tile perception** – `Agent.perceive()` returns nearby tiles, resources & agents.
* **Inter‑agent actions** – LLM can return actions like `{"action":"talk","target_id":3,"topic":"trade"}`.
* **Personal goals** – each agent calls DeepSeek once at spawn to set a realistic, attribute‑aligned goal.
* **Rule enforcement** – Bible rules are injected into every perception prompt. Agents must comply.

────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import os, json, random, argparse, asyncio, aiohttp
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import openai  # OpenAI‑compatible SDK for DeepSeek
from loguru import logger
import matplotlib.pyplot as plt

# ─────────────────────────── Config ────────────────────────────────
openai.api_key = os.getenv("DEEPSEEK_API_KEY")
MODEL_AGENT = "deepseek-chat"           # or -reasoner when perf‑needed
MODEL_TRINITY = "deepseek-reasoner"     # more deliberative
VISION_RADIUS = 5                       # tiles in chebyshev dist
TERRAIN = ["OCEAN", "FOREST", "GRASSLAND", "MOUNTAIN"]
COLOR = {
    "OCEAN": (0.129, 0.588, 0.953),    # blue
    "FOREST": (0.298, 0.686, 0.314),   # green
    "GRASSLAND": (0.667, 0.867, 0.467),# light green
    "MOUNTAIN": (0.5, 0.5, 0.5)        # gray
}

# Default resource distribution rules
DEFAULT_RESOURCE_RULES = {
    "wood": {"FOREST": 0.5, "OCEAN": 0},
    "apple": {"FOREST": 0.3, "GRASSLAND": 0.2},
    "fish": {"OCEAN": 0.4},
    "stone": {"MOUNTAIN": 0.6}
}

# ─────────────────────── Utility: Async LLM wrapper ─────────────────

async def adeepseek_chat(model: str, system: str, user: str, session: aiohttp.ClientSession, temperature=0.7) -> str:
    """Async chat completion using aiohttp for DeepSeek API"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    }
    
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
            return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.error(f"API error: {e}")
        return "{}"

# ───────────────────────────── Bible ───────────────────────────────
@dataclass
class Bible:
    rules: Dict[str, str] = field(default_factory=dict)

    def apply(self, perception: Dict) -> Dict:
        """Inject current rules into perception JSON sent to agent."""
        perception["rules"] = self.rules
        return perception

    def update(self, new_rules: Dict[str, str]):
        self.rules.update(new_rules)
        logger.success(f"[Bible] Updated rules: {new_rules}")

# ─────────────────────────── Agent ────────────────────────────────
@dataclass
class Agent:
    aid: int
    pos: Tuple[int, int]
    attributes: Dict[str, int]
    inventory: Dict[str, int]
    age: int = 0         # 新增年龄属性
    goal: str = ""
    log: List[str] = field(default_factory=list)
    hunger: float = 0.0  # 0-100, 100 = starving
    health: int = 100    # 0-100, 0 = dead

    # ── Goal determination at spawn ────────────────────────────────
    async def decide_goal(self, era_prompt: str, session: aiohttp.ClientSession):
        if self.goal:
            return  # already decided
        system = (
            "You are a simulated person in a large‑scale sociological experiment. "
            "Be realistic (实事求是) and strive for a personal goal that aligns with your innate attributes."
        )
        user = (
            f"时代背景: {era_prompt}\n"
            f"你的初始属性: {json.dumps(self.attributes, ensure_ascii=False)}\n"
            "请用一句话 (简体中文) 给出你的个人长期目标。"
        )
        self.goal = await adeepseek_chat(MODEL_AGENT, system, user, session, temperature=0.9)
        logger.info(f"Agent {self.aid} personal goal ➜ {self.goal}")

    # ── Perception (5‑tile radius) ────────────────────────────────
    def perceive(self, world: "World", bible: Bible) -> Dict:
        vis_tiles, vis_agents = [], []
        x0, y0 = self.pos
        for x in range(max(0, x0 - VISION_RADIUS), min(world.size, x0 + VISION_RADIUS + 1)):
            for y in range(max(0, y0 - VISION_RADIUS), min(world.size, y0 + VISION_RADIUS + 1)):
                if max(abs(x - x0), abs(y - y0)) <= VISION_RADIUS:
                    vis_tiles.append({"pos": [x, y], "terrain": world.map[x][y], "resource": world.resources.get((x, y), {})})
        for agent in world.agents:
            if agent.aid != self.aid and max(abs(agent.pos[0]-x0), abs(agent.pos[1]-y0)) <= VISION_RADIUS:
                vis_agents.append({"aid": agent.aid, "pos": list(agent.pos), "attributes": agent.attributes, "age": agent.age})
        perception = {
            "you": {
                "aid": self.aid, 
                "pos": self.pos, 
                "attributes": self.attributes, 
                "inventory": self.inventory, 
                "age": self.age,  # 暴露自身年龄
                "goal": self.goal,
                "hunger": self.hunger,
                "health": self.health
            },
            "visible_tiles": vis_tiles,
            "visible_agents": vis_agents,
        }
        return bible.apply(perception)

    # ── Act using DeepSeek (Natural Language) ─────────────────────
    async def act(self, world: "World", bible: Bible, era_prompt: str, session: aiohttp.ClientSession, action_handler):
        perception = self.perceive(world, bible)
        system = (
            "你控制着模拟世界中的智能体。请始终遵守给定的规则。"
            "根据你的感知、属性和目标，用自然语言描述你的下一步行动。"
            "行动示例: '我想和3号交易木材', '我饿了，要摘苹果吃', '收集附近的石头'"
        )
        user = (
            f"时代背景: {era_prompt}\n"
            f"当前状态(JSON):\n{json.dumps(perception, ensure_ascii=False, indent=2)}\n"
            "请用一句话描述你的下一步行动:"
        )
        natural_language_action = await adeepseek_chat(MODEL_AGENT, system, user, session)
        
        # Resolve natural language action through handler
        outcome = await action_handler.resolve(natural_language_action, self, world)
        self.apply_outcome(outcome)
        
        logger.info(f"Agent {self.aid} 行动 → {natural_language_action}")

    def apply_outcome(self, outcome: Dict):
        """Apply changes from action handler outcome (natural language)"""
        # Apply inventory changes
        if "inventory" in outcome:
            for item, qty in outcome["inventory"].items():
                self.inventory[item] = self.inventory.get(item, 0) + qty
        
        # Apply attribute changes
        if "attributes" in outcome:
            for attr, val in outcome["attributes"].items():
                self.attributes[attr] = self.attributes.get(attr, 0) + val
        
        # Apply position changes if present
        if "position" in outcome:
            new_pos = outcome["position"]
            if (isinstance(new_pos, list) and len(new_pos) == 2 and 
                all(isinstance(coord, int) for coord in new_pos)):
                self.pos = tuple(new_pos)
        
        # Log the action outcome
        if "log" in outcome:
            self.log.append(outcome["log"])
        elif outcome:  # Auto-generate log if missing
            action_desc = "执行了行动"
            if "inventory" in outcome:
                items = ", ".join([f"{item}{qty:+d}" for item, qty in outcome["inventory"].items()])
                action_desc += f"，背包变化: {items}"
            if "attributes" in outcome:
                attrs = ", ".join([f"{attr}{val:+d}" for attr, val in outcome["attributes"].items()])
                action_desc += f"，属性变化: {attrs}"
            self.log.append(f"{action_desc}")

        # (Removed execute method - all actions now handled by action handler)

# ─────────────────────────── Trinity ───────────────────────────────
class Trinity:
    def __init__(self, bible: Bible, era_prompt: str):
        self.bible = bible
        self.era_prompt = era_prompt
        self.turn = 0
        self.system_prompt = (
            "You are TRINITY – the omniscient adjudicator of a sociological simulation.\n"
            "Always respect the era context, be fair & impartial (公正公平)."
        )
        # Resource distribution rules
        self.resource_rules = DEFAULT_RESOURCE_RULES

    async def adjudicate(self, global_log: List[str], session: aiohttp.ClientSession):
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
            resp = await adeepseek_chat(MODEL_TRINITY, self.system_prompt, user, session, temperature=0.2)
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

# ─────────────────────────── World ────────────────────────────────
class World:
    def __init__(self, size: int, era_prompt: str, num_agents: int = 5):
        self.size = size
        self.era_prompt = era_prompt
        
        # Generate deterministic terrain with contiguous regions
        self.map = self.generate_contiguous_terrain()
        self.resources: Dict[Tuple[int,int], Dict[str,int]] = {}
        
        # Initialize Bible and Trinity first for resource rules
        self.bible = Bible()
        self.trinity = Trinity(self.bible, era_prompt)
        
        # Place resources based on Trinity's distribution rules
        self.place_resources()
        
        self.agents: List[Agent] = []
        # Agents will be initialized without goals first
        for aid in range(num_agents):
            pos = (random.randrange(size), random.randrange(size))
            attr = {"strength": random.randint(1,10), "curiosity": random.randint(1,10)}
            inv = {"wood": random.randint(0,2), "shell": random.randint(0,1)}
            agent = Agent(aid, pos, attr, inv)
            self.agents.append(agent)

    # ── Generate contiguous terrain regions ──────────────────────
    def generate_contiguous_terrain(self):
        """Create deterministic terrain with contiguous regions"""
        map = [["GRASSLAND"] * self.size for _ in range(self.size)]
        
        # Ocean region (bottom-left)
        for x in range(self.size//2):
            for y in range(self.size//2):
                map[x][y] = "OCEAN"
        
        # Forest region (top-right)
        for x in range(self.size//2, self.size):
            for y in range(self.size//2, self.size):
                map[x][y] = "FOREST"
        
        # Mountain region (top-left)
        for x in range(self.size//2):
            for y in range(self.size//2, self.size):
                map[x][y] = "MOUNTAIN"
        
        # Grassland is already set as default for bottom-right
        return map

    # ── Place resources based on Trinity's distribution rules ─────
    def place_resources(self):
        """Place resources according to Trinity's distribution rules"""
        # Use Trinity's resource rules if available, else default
        resource_rules = getattr(self.trinity, "resource_rules", DEFAULT_RESOURCE_RULES)
        
        for resource, terrain_probs in resource_rules.items():
            for terrain, prob in terrain_probs.items():
                # For each tile of this terrain type
                for x in range(self.size):
                    for y in range(self.size):
                        if self.map[x][y] == terrain and random.random() < prob:
                            if (x, y) not in self.resources:
                                self.resources[(x, y)] = {}
                            self.resources[(x, y)][resource] = self.resources[(x, y)].get(resource, 0) + 1

    # ── Display terrain using matplotlib ───────────────────────── 
    def show_map(self):
        # Create RGB image array
        img = [[COLOR[self.map[x][y]] for y in range(self.size)] for x in range(self.size)]
        plt.figure(figsize=(6,6))
        plt.title("World Terrain")
        plt.imshow(img)
        plt.axis("off")
        plt.show()

    # ── Action Handler (Natural Language) ─────────────────────────
    class ActionHandler:
        def __init__(self, bible: Bible, world: "World"):  # 使用字符串类型注释解决循环引用问题
            self.lock = asyncio.Lock()
            self.bible = bible
            self.world = world
            self.courtship_events = []  # 存储求偶事件
            self.dead_agents = []       # 存储死亡智能体ID
            self.buildings = []         # 存储建筑信息
            self.tools = []            # 存储工具信息
        
        async def resolve(self, action: str, agent: Agent, world: World) -> Dict:
            """Resolve natural language actions using LLM arbitration with robust JSON validation"""
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
                "示例输出: {\"inventory\": {\"apple\": -1}, \"attributes\": {\"hunger\": -10}, \"log\": \"吃了一个苹果\"}"
                "死亡示例: {\"log\": \"在野外遭遇中死亡\", \"dead\": true}"
                "\n\n重要: 必须返回严格有效的JSON，仅包含JSON对象，不要包含任何额外文本或注释!"
            )
            prompt = (
                f"智能体 {agent.aid} (属性: {agent.attributes}) 位于位置 {agent.pos} "
                f"背包: {agent.inventory} 想要执行行动: {action}\n"
                "请评估并返回严格有效的JSON结果:"
            )
            
            async with self.lock:  # Prevent race conditions
                async with aiohttp.ClientSession() as session:
                    # Try up to 3 times to get valid JSON
                    for attempt in range(3):
                        response = await adeepseek_chat(MODEL_AGENT, system, prompt, session)
                        
                        # First try parsing as-is
                        try:
                            outcome = json.loads(response) if response else {}
                            if self._validate_outcome(outcome, agent):
                                return self._process_outcome(outcome, agent)
                            continue
                        except json.JSONDecodeError:
                            pass
                        
                        # If first parse fails, try cleaning response
                        cleaned = self._clean_json_response(response)
                        try:
                            outcome = json.loads(cleaned) if cleaned else {}
                            if self._validate_outcome(outcome, agent):
                                return self._process_outcome(outcome, agent)
                        except json.JSONDecodeError:
                            logger.warning(f"Attempt {attempt+1}: Invalid JSON response")
                    
                    # If all attempts fail, return safe default outcome
                    logger.error(f"Failed to get valid JSON after 3 attempts for action: {action}")
                    return {
                        "log": f"行动失败: {action}",
                        "position": list(agent.pos)  # Stay in current position
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
            """Validate the structure of an action outcome"""
            if not isinstance(outcome, dict):
                return False
                
            # Validate position if present
            if "position" in outcome:
                pos = outcome["position"]
                if not (isinstance(pos, list) and len(pos) == 2 and 
                       all(isinstance(coord, int) for coord in pos)):
                    return False
                    
            # Validate inventory if present
            if "inventory" in outcome and not isinstance(outcome["inventory"], dict):
                return False
                
            # Validate attributes if present
            if "attributes" in outcome and not isinstance(outcome["attributes"], dict):
                return False
                
            return True

        def _process_outcome(self, outcome: Dict, agent: Agent) -> Dict:
            """Process and record special events from a validated outcome"""
            # Record courtship events
            if "courtship_target" in outcome:
                target_id = outcome["courtship_target"]
                self.courtship_events.append((agent.aid, target_id))
                
            # Record death events
            if outcome.get("dead", False):
                self.dead_agents.append(agent.aid)
                
            # Record building construction
            if "build" in outcome:
                building = outcome["build"]
                building["owner"] = agent.aid
                building["position"] = list(agent.pos)
                self.buildings.append(building)
                
            # Record tool creation
            if "create_tool" in outcome:
                tool = outcome["create_tool"]
                tool["creator"] = agent.aid
                self.tools.append(tool)
                
            return outcome
        
        def process_courtship_events(self):
            """处理求偶事件并返回新创建的代理列表"""
            new_agents = []
            # 找出相互求偶的配对 (A->B 且 B->A)
            mutual_pairs = set()
            for a, b in self.courtship_events:
                if (b, a) in self.courtship_events:
                    mutual_pairs.add(frozenset([a, b]))
            
            # 为每个相互配对的求偶事件创建新代理
            for pair in mutual_pairs:
                agent_ids = list(pair)
                agent1 = next((a for a in self.world.agents if a.aid == agent_ids[0]), None)
                agent2 = next((a for a in self.world.agents if a.aid == agent_ids[1]), None)
                
                if agent1 and agent2:
                    # 检查繁衍条件：健康且物品丰富
                    if (agent1.health > 70 and agent2.health > 70 and
                        sum(agent1.inventory.values()) > 5 and 
                        sum(agent2.inventory.values()) > 5):
                        
                        # 创建新代理 (后代)
                        new_aid = max(a.aid for a in self.world.agents) + 1 if self.world.agents else 0
                        # 位置在父母中间
                        new_pos = (
                            (agent1.pos[0] + agent2.pos[0]) // 2,
                            (agent1.pos[1] + agent2.pos[1]) // 2
                        )
                        # 属性遗传自父母
                        new_attr = {
                            "strength": (agent1.attributes.get("strength", 5) + agent2.attributes.get("strength", 5)) // 2,
                            "curiosity": (agent1.attributes.get("curiosity", 5) + agent2.attributes.get("curiosity", 5)) // 2
                        }
                        # 初始物品
                        new_inv = {"fruit": 1, "cloth": 1}
                        
                        new_agent = Agent(new_aid, new_pos, new_attr, new_inv, age=0)
                        new_agents.append(new_agent)
            
            return new_agents
        
        def process_death_events(self, turn_log: list):
            """处理死亡事件并广播死亡信息"""
            dead_agents = []
            for aid in self.dead_agents:
                agent = next((a for a in self.world.agents if a.aid == aid), None)
                if agent:
                    dead_agents.append(agent)
                    turn_log.append(f"Agent {agent.aid} died in the wild at age {agent.age}!")
                    
                    # 广播死亡信息给周围智能体
                    for other in self.world.agents:
                        if other.aid != aid and max(abs(other.pos[0]-agent.pos[0]), abs(other.pos[1]-agent.pos[1])) <= VISION_RADIUS:
                            other.log.append(f"看到智能体 {agent.aid} 在野外遭遇中死亡！")
            
            return dead_agents

    # ── Simulation Turn (Async) ───────────────────────────────────
    async def _check_agent_status(self, turn_log: List[str], action_handler):
        """Check agent status every 5 turns and generate report"""
        status_report = []
        for agent in self.agents:
            status = {
                "aid": agent.aid,
                "age": agent.age,
                "health": agent.health,
                "hunger": agent.hunger,
                "inventory": sum(agent.inventory.values()),
                "buildings": sum(1 for b in action_handler.buildings if b["owner"] == agent.aid),
                "tools": sum(1 for t in action_handler.tools if t["creator"] == agent.aid)
            }
            status_report.append(status)
        
        turn_log.append(f"Agent Status Report (Turn {self.trinity.turn}):")
        turn_log.extend([f"Agent {s['aid']}: age {s['age']}, health {s['health']}, hunger {s['hunger']}, items {s['inventory']}, buildings {s['buildings']}, tools {s['tools']}" 
                        for s in status_report])

    async def _check_era_change(self, session: aiohttp.ClientSession, turn_log: List[str]):
        """Check if era should change every 10 turns"""
        turn_log.append(f"Era change check at turn {self.trinity.turn}")
        # Trinity will handle era change in adjudicate() method
        # This just logs the check

    async def step(self, session: aiohttp.ClientSession):
        action_handler = self.ActionHandler(self.bible, self)
        turn_log = []
        
        # Every 5 turns, check agent status and generate new resources
        if self.trinity.turn % 5 == 0:
            await self._check_agent_status(turn_log, action_handler)
            self.place_resources()  # Regenerate resources
            
        # Every 10 turns, Trinity decides era change
        if self.trinity.turn % 10 == 0:
            await self._check_era_change(session, turn_log)
        
        # Process all agents asynchronously
        tasks = []
        for agent in self.agents:
            # Ensure agent has a goal
            if not agent.goal:
                await agent.decide_goal(self.era_prompt, session)
            task = agent.act(self, self.bible, self.era_prompt, session, action_handler)
            tasks.append(task)
        
        # Wait for all agents to complete with dynamic timeout
        timeout_per_agent = 15.0  # seconds per agent
        total_timeout = timeout_per_agent * len(tasks)
        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=total_timeout)
        except asyncio.TimeoutError:
            completed = sum(1 for task in tasks if task.done())
            logger.warning(f"Agent processing timed out - {completed}/{len(tasks)} agents completed")
        
        # 处理求偶事件并创建新代理
        new_agents = action_handler.process_courtship_events()
        for new_agent in new_agents:
            self.agents.append(new_agent)
            turn_log.append(f"New agent {new_agent.aid} born from parents!")
        
        # 处理野外死亡事件
        wild_deaths = action_handler.process_death_events(turn_log)
        for agent in wild_deaths:
            self.agents.remove(agent)
        
        # 更新年龄和健康
        dead_agents = []
        for agent in self.agents:
            # 增加年龄
            agent.age += 1
            
            # 增加饥饿值
            agent.hunger = min(100, agent.hunger + 8)
            
            # 饥饿时健康下降
            if agent.hunger > 70:
                agent.health = max(0, agent.health - 5)
                if agent.health == 0:
                    dead_agents.append(agent)
                    turn_log.append(f"Agent {agent.aid} starved to death at age {agent.age}!")
        
        # 移除饥饿死亡的代理
        for agent in dead_agents:
            self.agents.remove(agent)
            
            # 广播饥饿死亡信息给周围智能体
            for other in self.agents:
                if max(abs(other.pos[0]-agent.pos[0]), abs(other.pos[1]-agent.pos[1])) <= VISION_RADIUS:
                    other.log.append(f"看到智能体 {agent.aid} 饿死了！")
        
        # 收集日志
        for agent in self.agents:
            turn_log.extend([f"Agent {agent.aid} (age {agent.age}): {entry}" for entry in agent.log])
            agent.log.clear()
        
        await self.trinity.adjudicate(turn_log, session)

# ──────────────────────────── CLI ─────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run sociology simulation MVP")
    parser.add_argument("--size", type=int, default=64)
    parser.add_argument("--turns", type=int, default=10)
    parser.add_argument("--num-agents", type=int, default=20, help="Number of agents")
    parser.add_argument("--show-map-every", type=int, default=1, help="0 to disable display")
    parser.add_argument("--era", type=str, default="石器时代", help="时代提示词")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Logging verbosity")
    args = parser.parse_args()

    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=log_level)

    world = World(args.size, args.era, args.num_agents)
    if args.show_map_every and args.turns > 0:
        world.show_map()

    # Async main loop
    async def run_simulation():
        async with aiohttp.ClientSession() as session:
            # Initialize agent goals
            tasks = [agent.decide_goal(args.era, session) for agent in world.agents]
            await asyncio.gather(*tasks)
            
            for t in range(args.turns):
                logger.info(f"===== TURN {t} =====")
                await world.step(session)
                if args.show_map_every and (t+1) % args.show_map_every == 0:
                    world.show_map()
    
    asyncio.run(run_simulation())

if __name__ == "__main__":
    main()
