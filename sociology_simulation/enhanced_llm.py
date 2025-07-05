"""增强的LLM服务

专门解决JSON生成问题和提示词管理，提供：
1. 智能JSON生成和修复
2. 集成提示词管理
3. 自动重试机制
4. 详细的错误处理
5. 性能监控
"""

import asyncio
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
            (r"'([^']*)':", r'"\1":'),  # 单引号转双引号
            (r",\s*}", r"}"),           # 移除尾随逗号
            (r",\s*]", r"]"),           # 移除数组尾随逗号
            (r":\s*'([^']*)'", r': "\1"'),  # 值的单引号转双引号
            (r'"\s*(\w+)\s*"', r'"\1"'),     # 清理多余空格
            (r"\n|\r", ""),             # 移除换行符
            (r"//.*", ""),              # 移除注释
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
            
            return True, data
            
        except json.JSONDecodeError as e:
            return False, f"JSON解析错误: {e}"
    
    def _repair_json(self, content: str) -> Optional[str]:
        """智能修复JSON格式"""
        # 提取JSON部分
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if not json_match:
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
        
        if not json_match:
            logger.warning("未找到JSON结构")
            return None
        
        json_str = json_match.group()
        
        # 应用修复模式
        for pattern, replacement in self.json_repair_patterns:
            json_str = re.sub(pattern, replacement, json_str)
        
        # 尝试解析修复后的JSON
        try:
            json.loads(json_str)
            return json_str
        except json.JSONDecodeError:
            logger.warning("JSON修复失败")
            return None
    
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
        url = self.config.model.base_url.rstrip('/') + '/v1/chat/completions'
        headers = {
            "Authorization": f"Bearer {self.config.model.api_key_env}",
            "Content-Type": "application/json"
        }
        
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
    
    async def generate_agent_name(self, era: str, attributes: Dict, age: int, session: aiohttp.ClientSession) -> str:
        """生成Agent名字"""
        response = await self.generate(
            "agent_generate_name",
            session,
            era=era,
            attributes=attributes,
            age=age
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
        session: aiohttp.ClientSession
    ) -> str:
        """生成Agent行动"""
        response = await self.generate(
            "agent_action",
            session,
            era_prompt=era_prompt,
            perception=json.dumps(perception, ensure_ascii=False, indent=2),
            memory_summary=json.dumps(memory_summary, ensure_ascii=False, indent=2),
            goal=goal
        )
        return response.content if response.success else "休息一下"
    
    async def trinity_generate_rules(self, era_prompt: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
        action: str,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """解析Agent行动"""
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
            action=action
        )
        return response.parsed_data if response.success else {
            "log": f"行动失败: {action}",
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