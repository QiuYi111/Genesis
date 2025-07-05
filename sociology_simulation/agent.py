"""Agent class for sociology simulation"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, TYPE_CHECKING
import json
import random
import aiohttp
from loguru import logger

if TYPE_CHECKING:
    from .world import World
    from .bible import Bible

from .config import VISION_RADIUS
from .llm import adeepseek_chat

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

    async def generate_name(self, session: aiohttp.ClientSession):
        """Generate agent name using LLM"""
        system = "你是一个名字生成器，请为模拟世界中的角色生成一个英文名"
        user = f"根据以下属性生成名字:\n属性: {self.attributes}\n年龄: {self.age}。你只能输出名字本身，不要包含任何其他文本。"
        self.name = await adeepseek_chat("deepseek-chat", system, user, session)

    async def decide_goal(self, era_prompt: str, session: aiohttp.ClientSession):
        """Determine agent's personal goal using LLM"""
        if self.goal:
            return
        
        if not self.name:
            await self.generate_name(session)
            
        system = (
            "You are a simulated person in a large‑scale sociological experiment. "
            "Be realistic (实事求是) and strive for a personal goal that aligns with your innate attributes."
        )
        user = (
            f"时代背景: {era_prompt}\n"
            f"你的初始属性: {json.dumps(self.attributes, ensure_ascii=False)}\n"
            "请用一句话 (简体中文) 给出你的个人长期目标。"
        )
        self.goal = await adeepseek_chat("deepseek-chat", system, user, session, temperature=0.9)
        logger.info(f"{self.name}({self.aid}) personal goal ➜ {self.goal}")

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
                    "health": self.health
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
            existing = next((l for l in self.memory["locations"] if l["pos"] == tile["pos"]), None)
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
                "health": self.health
            },
            "visible_tiles": vis_tiles,
            "visible_agents": vis_agents,
        }
        return bible.apply(perception)

    def apply_outcome(self, outcome: Dict):
        """Apply action outcome to agent"""
        if "inventory" in outcome:
            for item, qty in outcome["inventory"].items():
                self.inventory[item] = self.inventory.get(item, 0) + qty
        
        if "attributes" in outcome:
            for attr, val in outcome["attributes"].items():
                self.attributes[attr] = self.attributes.get(attr, 0) + val
        
        if "position" in outcome:
            new_pos = outcome["position"]
            if (isinstance(new_pos, list) and len(new_pos) == 2 and 
                all(isinstance(coord, int) for coord in new_pos)):
                self.pos = tuple(new_pos)
        
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
        system = (
            "你控制着模拟世界中的智能体。请始终遵守给定的规则。"
            "根据你的感知、记忆、属性和目标，用自然语言描述你的下一步行动。"
            "你可以参考以下记忆信息来做出更明智的决定:\n"
            "1. 你之前遇到过的人和他们的位置\n"
            "2. 你知道的资源位置\n"
            "3. 你与其他人之前的互动历史\n\n"
            "行动示例: '我想和3号交易木材','我想向y号询问关于xx的问题，发起聊天请求', '我饿了，要摘苹果吃', '收集附近的石头'，'请求制造工具，我想制造xx', '建造建筑'\n"
            "制造工具示例: '用1木头和1石头制作斧头'\n"
            "建造建筑示例: '想用木头建造一个小屋'"
        )
        
        # Prepare memory information summary
        memory_summary = {
            "known_agents": [{"id": a["aid"], "name": a["name"], "last_seen": a["last_seen"]} 
                            for a in self.memory.get("agents", [])],
            "known_locations": [{"pos": l["pos"], "terrain": l["terrain"], "last_visited": l["last_visited"]}
                              for l in self.memory.get("locations", [])]
        }
        
        user = (
            f"时代背景: {era_prompt}\n"
            f"当前状态(JSON):\n{json.dumps(perception, ensure_ascii=False, indent=2)}\n"
            f"记忆摘要(JSON):\n{json.dumps(memory_summary, ensure_ascii=False, indent=2)}\n"
            "请综合考虑当前状态和记忆信息，用一句话描述你的下一步行动:"
        )
        
        natural_language_action = await adeepseek_chat("deepseek-chat", system, user, session)
        outcome = await action_handler.resolve(natural_language_action, self, world, era_prompt)
        self.apply_outcome(outcome)
        logger.info(f"{self.name}({self.aid}) 行动 → {natural_language_action}")
