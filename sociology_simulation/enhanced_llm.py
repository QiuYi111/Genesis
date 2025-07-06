"""增强的LLM服务

专门解决JSON生成问题和提示词管理，提供：
1. 智能JSON生成和修复
2. 集成提示词管理
3. 自动重试机制
4. 详细的错误处理
5. 性能监控
"""

import asyncio
import os
import json
import re
import time
from typing import Dict, Any, Optional, Union, List, Tuple
import aiohttp
from loguru import logger
from dataclasses import dataclass

from .prompts import get_prompt_manager, PromptManager
from .config import get_config


@dataclass
class LLMResponse:
    """LLM响应封装类"""
    content: str
    success: bool
    parsed_data: Optional[Any] = None
    error_message: Optional[str] = None
    attempts: int = 1
    total_time: float = 0.0
    template_name: Optional[str] = None


class JSONRepairError(Exception):
    """JSON修复失败异常"""
    pass


class EnhancedLLMService:
    """增强的LLM服务
    
    主要功能：
    1. 集成提示词管理器
    2. 智能JSON生成和修复
    3. 自动重试机制
    4. 性能监控和错误统计
    """
    
    def __init__(self, prompt_manager: Optional[PromptManager] = None):
        self.prompt_manager = prompt_manager or get_prompt_manager()
        self.config = get_config()
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "json_requests": 0,
            "json_successes": 0,
            "json_repairs": 0,
            "average_response_time": 0.0,
            "template_usage": {},
            "error_counts": {}
        }
        
        # JSON修复正则表达式
        self.json_repair_patterns = [
            # 基础修复
            (r"'([^']*)':", r'"\1":'),  # 单引号转双引号
            (r",\s*}", r"}"),           # 移除尾随逗号
            (r",\s*]", r"]"),           # 移除数组尾随逗号
            (r":\s*'([^']*)'", r': "\1"'),  # 值的单引号转双引号
            (r'"\s*(\w+)\s*"', r'"\1"'),     # 清理多余空格
            (r"//.*", ""),              # 移除注释
            (r"/\*.*?\*/", ""),         # 移除块注释
            
            # 高级修复模式
            (r"```json\s*", ""),        # 移除markdown代码块
            (r"```\s*", ""),            # 移除代码块结束
            (r"(?<!:)\s*\n\s*", " "),   # 压缩多行到单行
            (r':\s*"([^"]*)"([^,}\]])', r': "\1"\2'),  # 修复缺失逗号
            (r"(\w+):", r'"\1":'),      # 无引号键名
            (r':\s*([^",}\[\]]+)(?=[,}\]])', r': "\1"'),  # 无引号字符串值
            (r':\s*(\d+\.?\d*)', r': \1'),  # 确保数字不加引号
            (r':\s*true\b', r': true'), # 确保布尔值正确
            (r':\s*false\b', r': false'),
            (r':\s*null\b', r': null'),
            (r"([^\\])\\(?![\"\\\/bfnrtu])", r"\1\\\\"),  # 修复转义字符
        ]
    
    async def generate(
        self,
        template_name: str,
        session: aiohttp.ClientSession,
        **kwargs
    ) -> LLMResponse:
        """使用模板生成LLM响应
        
        Args:
            template_name: 提示词模板名称
            session: aiohttp会话
            **kwargs: 模板参数
            
        Returns:
            LLMResponse对象
        """
        start_time = time.time()
        
        # 更新统计
        self.stats["total_requests"] += 1
        self.stats["template_usage"][template_name] = self.stats["template_usage"].get(template_name, 0) + 1
        
        try:
            # 获取模板和配置
            template = self.prompt_manager.get_template(template_name)
            if not template:
                raise ValueError(f"模板不存在: {template_name}")
            
            # 渲染提示词
            system, user, temperature = self.prompt_manager.render_prompt(template_name, **kwargs)
            config = self.prompt_manager.get_template_config(template_name)
            
            # 生成响应
            if config.get("json_mode", False):
                response = await self._generate_json_response(
                    system, user, temperature, session, config
                )
            else:
                response = await self._generate_text_response(
                    system, user, temperature, session, config
                )
            
            response.template_name = template_name
            response.total_time = time.time() - start_time
            
            # 更新统计
            if response.success:
                self.stats["successful_requests"] += 1
                if config.get("json_mode", False):
                    self.stats["json_successes"] += 1
            else:
                error_type = type(response.error_message).__name__ if response.error_message else "unknown"
                self.stats["error_counts"][error_type] = self.stats["error_counts"].get(error_type, 0) + 1
            
            # 更新平均响应时间
            total_time = self.stats["average_response_time"] * (self.stats["total_requests"] - 1)
            self.stats["average_response_time"] = (total_time + response.total_time) / self.stats["total_requests"]
            
            return response
            
        except Exception as e:
            logger.error(f"生成响应失败 - 模板: {template_name}, 错误: {e}")
            return LLMResponse(
                content="",
                success=False,
                error_message=str(e),
                total_time=time.time() - start_time,
                template_name=template_name
            )
    
    async def _generate_text_response(
        self,
        system: str,
        user: str,
        temperature: float,
        session: aiohttp.ClientSession,
        config: Dict[str, Any]
    ) -> LLMResponse:
        """生成文本响应"""
        max_retries = config.get("max_retries", 3)
        
        for attempt in range(max_retries):
            try:
                content = await self._call_llm(system, user, temperature, session)
                if content.strip():
                    return LLMResponse(
                        content=content,
                        success=True,
                        attempts=attempt + 1
                    )
                else:
                    logger.warning(f"空响应，重试 {attempt + 1}/{max_retries}")
                    
            except Exception as e:
                logger.warning(f"LLM调用失败，重试 {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # 指数退避
        
        return LLMResponse(
            content="",
            success=False,
            error_message=f"文本生成失败，已重试{max_retries}次",
            attempts=max_retries
        )
    
    async def _generate_json_response(
        self,
        system: str,
        user: str,
        temperature: float,
        session: aiohttp.ClientSession,
        config: Dict[str, Any]
    ) -> LLMResponse:
        """生成JSON响应（带智能修复）"""
        max_retries = config.get("max_retries", 3)
        self.stats["json_requests"] += 1
        
        for attempt in range(max_retries):
            try:
                # 调用LLM
                content = await self._call_llm(system, user, temperature, session)
                if not content.strip():
                    logger.warning(f"空响应，重试 {attempt + 1}/{max_retries}")
                    continue
                
                # 尝试解析JSON
                success, data = self._parse_json_response(content, config)
                if success:
                    return LLMResponse(
                        content=content,
                        success=True,
                        parsed_data=data,
                        attempts=attempt + 1
                    )
                
                # JSON解析失败，尝试修复
                logger.warning(f"JSON解析失败，尝试修复: {content[:100]}...")
                repaired_content = self._repair_json(content)
                
                if repaired_content:
                    success, data = self._parse_json_response(repaired_content, config)
                    if success:
                        self.stats["json_repairs"] += 1
                        logger.info(f"JSON修复成功")
                        return LLMResponse(
                            content=repaired_content,
                            success=True,
                            parsed_data=data,
                            attempts=attempt + 1
                        )
                
                # 修复失败，添加更严格的指令重试
                if attempt < max_retries - 1:
                    system = self._enhance_json_system_prompt(system)
                    logger.warning(f"JSON修复失败，使用增强提示词重试 {attempt + 2}/{max_retries}")
                    await asyncio.sleep(0.5 * (attempt + 1))
                    
            except Exception as e:
                logger.warning(f"JSON生成失败，重试 {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        return LLMResponse(
            content="{}",  # 返回空JSON对象作为fallback
            success=False,
            parsed_data={},
            error_message=f"JSON生成失败，已重试{max_retries}次",
            attempts=max_retries
        )
    
    def _parse_json_response(self, content: str, config: Dict[str, Any]) -> Tuple[bool, Any]:
        """解析JSON响应"""
        try:
            # 首先尝试直接解析
            data = json.loads(content)
            
            # 验证schema（如果有）
            validation_schema = config.get("validation_schema")
            if validation_schema:
                if not self._validate_json_schema(data, validation_schema):
                    return False, f"JSON不符合schema要求"
            
            # 额外验证：确保关键字段不为None
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in ["chat_request", "exchange_request"] and value is not None:
                        if not isinstance(value, dict):
                            logger.warning(f"Invalid {key} format: {value}")
                            data[key] = None
                        elif key == "chat_request":
                            if not all(k in value for k in ["target_id", "topic"]):
                                logger.warning(f"Incomplete chat_request: {value}")
                                data[key] = None
                        elif key == "exchange_request":
                            if not all(k in value for k in ["target_id", "offer", "request"]):
                                logger.warning(f"Incomplete exchange_request: {value}")
                                data[key] = None
            
            return True, data
            
        except json.JSONDecodeError as e:
            return False, f"JSON解析错误: {e}"
    
    def _repair_json(self, content: str) -> Optional[str]:
        """智能修复JSON格式"""
        # 尝试多种JSON提取策略
        json_candidates = []
        
        # 策略1: 查找完整的JSON对象 (improved pattern)
        json_match = re.search(r'\{(?:[^{}]|{[^{}]*})*\}', content, re.DOTALL)
        if json_match:
            json_candidates.append(json_match.group())
        
        # 策略2: 查找最后一个完整的JSON对象
        json_matches = re.findall(r'\{(?:[^{}]|{[^{}]*})*\}', content, re.DOTALL)
        if json_matches:
            json_candidates.extend(json_matches[-2:])  # Take last 2 matches
        
        # 策略3: 查找JSON代码块
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            json_candidates.append(code_block_match.group(1))
        
        # 策略4: 简单提取大括号内容（最后的备选）
        simple_match = re.search(r'\{.*\}', content, re.DOTALL)
        if simple_match:
            json_candidates.append(simple_match.group())
        
        # 优先处理较短的JSON候选，通常更准确
        json_candidates.sort(key=len)
        
        if not json_candidates:
            logger.warning("未找到JSON结构")
            return None
        
        # 尝试修复每个候选JSON
        for json_str in json_candidates:
            # 预处理
            json_str = json_str.strip()
            
            # 应用修复模式
            for pattern, replacement in self.json_repair_patterns:
                try:
                    json_str = re.sub(pattern, replacement, json_str)
                except Exception as e:
                    logger.debug(f"修复模式应用失败: {e}")
                    continue
            
            # 尝试解析修复后的JSON
            try:
                parsed = json.loads(json_str)
                # Post-process to convert string numbers to actual numbers
                parsed = self._convert_string_numbers(parsed)
                logger.debug(f"JSON修复成功，长度: {len(json_str)}")
                return json.dumps(parsed)  # Return the clean JSON string
            except json.JSONDecodeError as e:
                logger.debug(f"JSON修复失败: {e}")
                continue
        
        # 最后的尝试：创建最小有效JSON
        try:
            # 如果所有修复都失败，返回空对象
            fallback = "{}"
            json.loads(fallback)
            logger.warning("使用空JSON对象作为回退")
            return fallback
        except:
            logger.warning("JSON修复完全失败")
            return None
    
    def _convert_string_numbers(self, obj):
        """Convert string numbers to actual numbers in JSON data"""
        if isinstance(obj, dict):
            return {k: self._convert_string_numbers(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_string_numbers(item) for item in obj]
        elif isinstance(obj, str):
            # Try to convert string to number
            try:
                # Check if it's an integer
                if obj.isdigit() or (obj.startswith('-') and obj[1:].isdigit()):
                    return int(obj)
                # Check if it's a float
                elif '.' in obj:
                    return float(obj)
                else:
                    return obj
            except (ValueError, AttributeError):
                return obj
        else:
            return obj
    
    def _enhance_json_system_prompt(self, original_system: str) -> str:
        """增强JSON生成的系统提示词"""
        enhancement = """

**CRITICAL JSON REQUIREMENTS - READ CAREFULLY:**
1. You MUST return ONLY valid JSON - no explanations, no text before/after
2. Use double quotes (") for all strings, never single quotes (')
3. No trailing commas in objects or arrays
4. No comments or extra characters
5. Ensure all brackets/braces are properly closed
6. Numbers must be valid (no NaN, infinity, etc.)

EXAMPLE CORRECT FORMAT:
{"key": "value", "number": 1.0, "array": ["item1", "item2"]}

WRONG FORMATS TO AVOID:
- {'key': 'value'}  // Wrong: single quotes
- {"key": "value",}  // Wrong: trailing comma
- {"key": value}     // Wrong: unquoted value
- JSON with explanations before/after

IF YOU CANNOT GENERATE VALID JSON, RETURN: {}
"""
        return original_system + enhancement
    
    def _validate_json_schema(self, data: Any, schema: Dict[str, Any]) -> bool:
        """简单的JSON schema验证"""
        if schema.get("type") == "object" and not isinstance(data, dict):
            return False
        
        required_fields = schema.get("required", [])
        for field in required_fields:
            if field not in data:
                return False
        
        properties = schema.get("properties", {})
        for prop, prop_schema in properties.items():
            if prop in data:
                prop_type = prop_schema.get("type")
                if prop_type == "array" and not isinstance(data[prop], list):
                    return False
                elif prop_type == "object" and not isinstance(data[prop], dict):
                    return False
                elif prop_type == "string" and not isinstance(data[prop], str):
                    return False
                elif prop_type == "number" and not isinstance(data[prop], (int, float)):
                    return False
        
        return True
    
    async def _call_llm(
        self,
        system: str,
        user: str,
        temperature: float,
        session: aiohttp.ClientSession
    ) -> str:
        """调用LLM API"""
        url = self.config.model.base_url
        api_key = os.getenv(self.config.model.api_key_env)
        if not api_key:
            raise ValueError(f"API key not found in environment variable {self.config.model.api_key_env}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.debug(f"Making LLM request to {url}")
        if api_key:
            logger.debug(f"Using API key: {api_key[:5]}...{api_key[-5:]}")
        
        payload = {
            "model": self.config.model.agent_model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }
        
        async with session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
            
            if data.get("choices") and data["choices"][0].get("message", {}).get("content"):
                return data["choices"][0]["message"]["content"].strip()
            else:
                raise ValueError(f"API响应格式异常: {data}")
    
    # === 便捷方法 ===
    
    async def generate_agent_name(
        self,
        era: str,
        attributes: Dict,
        age: int,
        session: aiohttp.ClientSession,
        goal: str = "",
    ) -> str:
        """生成Agent名字"""
        response = await self.generate(
            "agent_generate_name",
            session,
            era=era,
            attributes=attributes,
            age=age,
            goal=goal,
        )
        return response.content if response.success else f"Agent{age}"
    
    async def generate_agent_goal(
        self,
        era_prompt: str,
        attributes: Dict,
        age: int,
        inventory: Dict,
        session: aiohttp.ClientSession
    ) -> str:
        """生成Agent目标"""
        response = await self.generate(
            "agent_decide_goal",
            session,
            era_prompt=era_prompt,
            attributes=attributes,
            age=age,
            inventory=inventory
        )
        return response.content if response.success else "在这个世界中生存下去"
    
    async def generate_agent_action(
        self,
        era_prompt: str,
        perception: Dict,
        memory_summary: Dict,
        goal: str,
        skills: Dict,
        session: aiohttp.ClientSession
    ) -> str:
        """生成Agent行动"""
        # Format skills for display
        skills_display = {}
        for skill_name, skill_data in skills.items():
            skills_display[skill_name] = f"Level {skill_data.get('level', 1)}"
        
        response = await self.generate(
            "agent_action",
            session,
            era_prompt=era_prompt,
            perception=json.dumps(perception, ensure_ascii=False, indent=2),
            memory_summary=json.dumps(memory_summary, ensure_ascii=False, indent=2),
            goal=goal,
            skills=json.dumps(skills_display, ensure_ascii=False, indent=2)
        )
        if response.success:
            return response.content
        else:
            # 提供更智能的fallback行动
            return self._generate_fallback_action(perception, goal)
    
    def _generate_fallback_action(self, perception: Dict, goal: str) -> str:
        """生成智能的fallback行动"""
        import random
        
        agent_info = perception.get("you", {})
        visible_tiles = perception.get("visible_tiles", [])
        visible_agents = perception.get("visible_agents", [])
        
        age = agent_info.get("age", 25)
        health = agent_info.get("health", 100)
        hunger = agent_info.get("hunger", 0)
        inventory = agent_info.get("inventory", {})
        attributes = agent_info.get("attributes", {})
        
        possible_actions = []
        
        # 基于生存需求的行动
        if hunger > 60:
            # 首先尝试吃库存中的食物
            food_in_inventory = [item for item in ["fish", "apple", "fruit", "berries", "bread", "meat"] 
                               if inventory.get(item, 0) > 0]
            if food_in_inventory:
                food = food_in_inventory[0]  # 吃第一个可用的食物
                possible_actions.append(f"吃{food}")
            else:
                # 寻找食物资源
                for tile in visible_tiles:
                    resources = tile.get("resource", {})
                    if any(food in resources for food in ["apple", "fish", "fruit", "berries"]):
                        x, y = tile["pos"]
                        possible_actions.append(f"移动到({x},{y})采集食物")
                if not possible_actions:
                    possible_actions.append("寻找食物")
        
        # 基于健康状况的行动
        if health < 70:
            possible_actions.extend([
                "休息恢复体力",
                "寻找安全的地方休息",
                "寻找治疗用的草药"
            ])
        
        # 资源收集行动
        strength = attributes.get("strength", 5)
        curiosity = attributes.get("curiosity", 5)
        
        for tile in visible_tiles:
            resources = tile.get("resource", {})
            x, y = tile["pos"]
            
            if "wood" in resources and strength >= 3:
                possible_actions.append(f"移动到({x},{y})砍伐木材")
            if "stone" in resources and strength >= 4:
                possible_actions.append(f"移动到({x},{y})采集石头")
            if "fish" in resources:
                possible_actions.append(f"移动到({x},{y})捕鱼")
            if any(mineral in resources for mineral in ["iron", "copper", "crystal", "magical_crystal"]):
                possible_actions.append(f"移动到({x},{y})开采矿物")
        
        # 工具制作行动（基于库存）
        wood_count = inventory.get("wood", 0)
        stone_count = inventory.get("stone", 0)
        
        if wood_count >= 2 and stone_count >= 1 and strength >= 5:
            possible_actions.extend([
                "制作石斧",
                "制作工具"
            ])
        
        if wood_count >= 5 and strength >= 3:
            possible_actions.extend([
                "建造简易住所",
                "制作木屋"
            ])
        
        # 社交行动（基于年龄和魅力）
        charm = attributes.get("charm", 5)
        if visible_agents and age >= 18:
            if charm >= 6:
                agent = random.choice(visible_agents)
                possible_actions.extend([
                    f"与智能体{agent['aid']}聊天交流",
                    f"向智能体{agent['aid']}求助"
                ])
                
                # 求偶行动（年龄合适且魅力高）
                if 18 <= age <= 50 and charm >= 7:
                    suitable_partners = [a for a in visible_agents 
                                       if a.get("age", 0) >= 18 and abs(a.get("age", 25) - age) <= 15]
                    if suitable_partners:
                        partner = random.choice(suitable_partners)
                        possible_actions.append(f"向智能体{partner['aid']}表示好感")
        
        # 探索行动（基于好奇心）
        if curiosity >= 6:
            possible_actions.extend([
                "探索附近区域",
                "寻找新的资源点",
                "研究周围环境"
            ])
        
        # 如果没有特殊行动，使用基础行动
        if not possible_actions:
            possible_actions = [
                "四处走动",
                "观察环境",
                "休息一下",
                "整理物品"
            ]
        
        return random.choice(possible_actions)
    
    async def trinity_generate_rules(self, era_prompt: str, session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
        """Trinity生成初始规则"""
        response = await self.generate(
            "trinity_generate_initial_rules",
            session,
            era_prompt=era_prompt
        )
        return response.parsed_data if response.success else {
            "terrain_types": ["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"],
            "resource_rules": {
                "wood": {"FOREST": 0.5},
                "fish": {"OCEAN": 0.4},
                "stone": {"MOUNTAIN": 0.6}
            }
        }
    
    async def trinity_adjudicate(
        self,
        era_prompt: str,
        turn: int,
        global_log: List[str],
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, Any]]:
        """Trinity事件裁决"""
        response = await self.generate(
            "trinity_adjudicate",
            session,
            era_prompt=era_prompt,
            turn=turn,
            global_log="\n".join(global_log)
        )
        return response.parsed_data if response.success else {}
    
    async def trinity_execute_actions(
        self,
        era_prompt: str,
        turn: int,
        agent_count: int,
        resource_rules: Dict,
        resource_status: Dict,
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, Any]]:
        """Trinity执行生态管理行动"""
        response = await self.generate(
            "trinity_execute_actions",
            session,
            era_prompt=era_prompt,
            turn=turn,
            agent_count=agent_count,
            resource_rules=json.dumps(resource_rules, ensure_ascii=False),
            resource_status=json.dumps(resource_status, ensure_ascii=False)
        )
        return response.parsed_data if response.success else {}
    
    async def resolve_action(
        self,
        bible_rules: str,
        agent_id: int,
        agent_age: int,
        agent_attributes: Dict,
        agent_position: List[int],
        agent_inventory: Dict,
        agent_health: int,
        agent_hunger: float,
        agent_skills: Dict,
        action: str,
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, Any]]:
        """解析Agent行动"""
        # Format skills for display
        skills_display = {}
        for skill_name, skill_data in agent_skills.items():
            skills_display[skill_name] = f"Level {skill_data.get('level', 1)}"
        
        response = await self.generate(
            "action_handler_resolve",
            session,
            bible_rules=bible_rules,
            agent_id=agent_id,
            agent_age=agent_age,
            agent_attributes=agent_attributes,
            agent_position=agent_position,
            agent_inventory=agent_inventory,
            agent_health=agent_health,
            agent_hunger=agent_hunger,
            agent_skills=json.dumps(skills_display, ensure_ascii=False, indent=2),
            action=action
        )
        if response.success:
            # Handle case where LLM returns a list instead of dict
            if isinstance(response.parsed_data, list):
                # If it's a list, merge all dictionaries in the list
                merged_data = {}
                for item in response.parsed_data:
                    if isinstance(item, dict):
                        merged_data.update(item)
                return merged_data if merged_data else self._resolve_action_fallback(
                    action, agent_attributes, agent_position, agent_inventory, agent_health, agent_hunger
                )
            elif isinstance(response.parsed_data, dict):
                return response.parsed_data
            else:
                # If it's neither dict nor list, use fallback
                return self._resolve_action_fallback(
                    action, agent_attributes, agent_position, agent_inventory, agent_health, agent_hunger
                )
        else:
            # 提供更智能的行动解析fallback
            return self._resolve_action_fallback(
                action, agent_attributes, agent_position, agent_inventory, agent_health, agent_hunger
            )
    
    def _resolve_action_fallback(self, action: str, agent_attributes: Dict, agent_position: List[int], 
                               agent_inventory: Dict, agent_health: int, agent_hunger: float) -> Dict:
        """智能的行动解析fallback"""
        import random
        import re
        
        action_lower = action.lower()
        x, y = agent_position
        strength = agent_attributes.get("strength", 5)
        curiosity = agent_attributes.get("curiosity", 5)
        charm = agent_attributes.get("charm", 5)
        
        # 移动行动
        move_match = re.search(r'移动到?\(?(\d+),?\s*(\d+)\)?', action)
        if move_match or "移动" in action_lower or "前往" in action_lower:
            if move_match:
                new_x, new_y = int(move_match.group(1)), int(move_match.group(2))
                # 限制移动距离
                max_distance = 3 if strength >= 5 else 2
                distance = abs(new_x - x) + abs(new_y - y)
                if distance <= max_distance:
                    return {
                        "position": [new_x, new_y],
                        "log": f"移动到了({new_x},{new_y})"
                    }
            
            # 随机移动
            dx, dy = random.choice([(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (1,1), (-1,1), (1,-1)])
            new_x, new_y = max(0, min(63, x + dx)), max(0, min(63, y + dy))
            return {
                "position": [new_x, new_y],
                "log": f"移动到了({new_x},{new_y})"
            }
        
        # 资源采集行动
        if any(word in action_lower for word in ["采集", "砍伐", "挖掘", "捕鱼", "收集", "开采"]):
            resource_gained = {}
            
            if "木材" in action or "wood" in action_lower or "砍伐" in action:
                if strength >= 3:
                    gained = random.randint(1, 3)
                    resource_gained["wood"] = gained
                    return {
                        "inventory": resource_gained,
                        "log": f"砍伐获得了{gained}个木材"
                    }
            
            elif "石头" in action or "stone" in action_lower or "开采" in action:
                if strength >= 4:
                    gained = random.randint(1, 2)
                    resource_gained["stone"] = gained
                    return {
                        "inventory": resource_gained,
                        "log": f"开采获得了{gained}个石头"
                    }
            
            elif "鱼" in action or "fish" in action_lower or "捕鱼" in action:
                gained = random.randint(1, 2)
                resource_gained["fish"] = gained
                return {
                    "inventory": resource_gained,
                    "log": f"捕鱼获得了{gained}条鱼",
                    "hunger": max(0, agent_hunger - 20)  # 吃鱼减少饥饿
                }
            
            elif any(fruit in action for fruit in ["苹果", "fruit", "berries", "浆果"]):
                gained = random.randint(1, 3)
                resource_gained["apple"] = gained
                return {
                    "inventory": resource_gained,
                    "log": f"采集获得了{gained}个苹果",
                    "hunger": max(0, agent_hunger - 15)
                }
            
            # 通用采集
            return {
                "inventory": {"wood": 1} if strength >= 3 else {},
                "log": "尝试采集了一些资源"
            }
        
        # 制作行动
        if any(word in action_lower for word in ["制作", "建造", "制造", "打造"]):
            wood_count = agent_inventory.get("wood", 0)
            stone_count = agent_inventory.get("stone", 0)
            
            if "斧" in action or "axe" in action_lower:
                if wood_count >= 2 and stone_count >= 1 and strength >= 5:
                    return {
                        "inventory": {"wood": -2, "stone": -1, "axe": 1},
                        "log": "成功制作了石斧!"
                    }
                else:
                    return {
                        "log": "材料不足，无法制作石斧"
                    }
            
            elif any(word in action for word in ["住所", "房屋", "木屋", "hut"]):
                if wood_count >= 5 and strength >= 3:
                    return {
                        "inventory": {"wood": -5},
                        "build": {
                            "type": "hut",
                            "materials": {"wood": 5}
                        },
                        "log": "成功建造了简易住所!"
                    }
                else:
                    return {
                        "log": "木材不足，无法建造住所"
                    }
            
            # 通用制作
            if wood_count >= 1:
                return {
                    "inventory": {"wood": -1},
                    "log": "制作了一些简单的工具"
                }
        
        # 社交行动
        if any(word in action_lower for word in ["聊天", "交流", "求助", "好感", "求偶"]):
            # 提取目标智能体ID
            agent_match = re.search(r'智能体(\d+)', action)
            if agent_match:
                target_id = int(agent_match.group(1))
                
                if "好感" in action or "求偶" in action:
                    if charm >= 7:
                        return {
                            "courtship_target": target_id,
                            "log": f"向智能体{target_id}表达了好感"
                        }
                    else:
                        return {
                            "log": "魅力不足，求偶失败"
                        }
                
                elif "聊天" in action or "交流" in action:
                    topic = "天气" if "天气" in action else "日常话题"
                    return {
                        "chat_request": {
                            "target_id": target_id,
                            "topic": topic
                        },
                        "log": f"向智能体{target_id}发起聊天"
                    }
        
        # 进食行动
        if any(word in action_lower for word in ["吃", "进食", "食用", "eat"]):
            # 尝试从库存中找到食物
            food_items = {"fish": 25, "apple": 20, "fruit": 20, "berries": 15, "bread": 30, "meat": 35}
            
            for food_type, nutrition in food_items.items():
                if agent_inventory.get(food_type, 0) > 0:
                    return {
                        "inventory": {food_type: -1},
                        "hunger": max(0, agent_hunger - nutrition),
                        "health": min(100, agent_health + 2),
                        "log": f"吃了{food_type}，减少了{nutrition}点饥饿"
                    }
            
            return {
                "log": "没有可食用的食物"
            }
        
        # 休息行动
        if any(word in action_lower for word in ["休息", "睡觉", "恢复"]):
            health_gain = random.randint(5, 15)
            hunger_gain = random.randint(3, 8)
            return {
                "health": min(100, agent_health + health_gain),
                "hunger": min(100, agent_hunger + hunger_gain),
                "log": f"休息恢复了{health_gain}点健康值"
            }
        
        # 探索行动
        if any(word in action_lower for word in ["探索", "寻找", "搜索", "研究"]):
            if curiosity >= 6:
                # 可能发现新资源点
                if random.random() < 0.3:
                    resource_type = random.choice(["wood", "stone", "apple"])
                    return {
                        "inventory": {resource_type: 1},
                        "log": f"探索中发现了{resource_type}!"
                    }
                else:
                    return {
                        "log": "探索了周围环境，但没有特别发现"
                    }
        
        # 默认fallback
        return {
            "log": f"尝试执行: {action}",
            "position": agent_position
        }
    
    async def generate_chat_response(
        self,
        era_prompt: str,
        agent_age: int,
        agent_attributes: Dict,
        agent_inventory: Dict,
        topic: str,
        session: aiohttp.ClientSession
    ) -> str:
        """生成聊天回复"""
        response = await self.generate(
            "action_handler_chat_response",
            session,
            era_prompt=era_prompt,
            agent_age=agent_age,
            agent_attributes=agent_attributes,
            agent_inventory=agent_inventory,
            topic=topic
        )
        return response.content if response.success else "嗯，我不太明白。"
    
    async def trinity_analyze_behaviors(
        self,
        era_prompt: str,
        turn: int,
        agent_behaviors: Dict,
        available_skills: Dict,
        unlock_conditions: Dict,
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, Any]]:
        """Trinity分析智能体行为并管理技能系统"""
        response = await self.generate(
            "trinity_analyze_behaviors",
            session,
            era_prompt=era_prompt,
            turn=turn,
            agent_behaviors=json.dumps(agent_behaviors, ensure_ascii=False, indent=2),
            available_skills=json.dumps(available_skills, ensure_ascii=False, indent=2),
            unlock_conditions=json.dumps(unlock_conditions, ensure_ascii=False, indent=2)
        )
        return response.parsed_data if response.success else {}
    
    async def trinity_natural_events(
        self,
        era_prompt: str,
        turn: int,
        agent_count: int,
        development_level: str,
        recent_activities: List[str],
        session: aiohttp.ClientSession
    ) -> Optional[Dict[str, Any]]:
        """Trinity生成自然事件"""
        response = await self.generate(
            "trinity_natural_events",
            session,
            era_prompt=era_prompt,
            turn=turn,
            agent_count=agent_count,
            development_level=development_level,
            recent_activities="\n".join(recent_activities)
        )
        return response.parsed_data if response.success else {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取LLM服务统计信息"""
        return self.stats.copy()
    
    def reset_statistics(self):
        """重置统计信息"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "json_requests": 0,
            "json_successes": 0,
            "json_repairs": 0,
            "average_response_time": 0.0,
            "template_usage": {},
            "error_counts": {}
        }


# 全局实例
_llm_service = None

def get_llm_service() -> EnhancedLLMService:
    """获取全局LLM服务实例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = EnhancedLLMService()
    return _llm_service

def init_llm_service(prompt_manager: Optional[PromptManager] = None) -> EnhancedLLMService:
    """初始化全局LLM服务"""
    global _llm_service
    _llm_service = EnhancedLLMService(prompt_manager)
    return _llm_service
