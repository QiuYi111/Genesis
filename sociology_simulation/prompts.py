"""统一的提示词管理系统

这个模块提供了一个集中化的提示词管理系统，解决以下问题：
1. 提示词散落在各个文件中
2. Trinity的JSON生成经常失败
3. 提示词难以维护和优化
4. 缺乏模板化和参数化支持
"""

import json
import yaml
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
from loguru import logger


@dataclass
class PromptTemplate:
    """提示词模板类"""
    name: str
    system: str
    user: str
    temperature: float = 0.7
    max_retries: int = 3
    json_mode: bool = False
    validation_schema: Optional[Dict] = None
    examples: Optional[List[str]] = None
    description: str = ""


class PromptManager:
    """统一的提示词管理器
    
    功能：
    - 集中管理所有提示词
    - 支持模板化和参数替换
    - 针对JSON生成优化
    - 支持配置文件加载
    - 提供验证和重试机制
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.templates: Dict[str, PromptTemplate] = {}
        self._initialize_default_templates()
        
        if config_path:
            self.load_from_config(config_path)
    
    def _initialize_default_templates(self):
        """初始化默认提示词模板"""
        
        # === Agent相关提示词 ===
        self.register_template(PromptTemplate(
            name="agent_generate_name",
            system="You are a name generator that creates appropriate names for characters in simulation worlds based on era background. Always generate English names that fit the era style.",
            user="Generate a suitable English name based on the following info:\nAttributes: {attributes}\nAge: {age}\nEra: {era}\n\nFor Stone Age era, use simple English names like: Rok, Flint, Ash, Reed, Clay, Storm, etc.\nOutput ONLY the name itself, no explanations or extra text.",
            temperature=0.8,
            description="Generate era-appropriate English names for Agents"
        ))
        
        self.register_template(PromptTemplate(
            name="agent_decide_goal",
            system="""You are an intelligent agent in a simulation world. Set a realistic long-term goal based on your attributes and era background.

Requirements:
1. Goal must match your attribute strengths
2. Goal must fit era limitations 
3. Goal must be specific and executable
4. Express in ONE clear sentence only
5. NO explanations, asterisks, or extra formatting""",
            user="""Era background: {era_prompt}
Your attributes: {attributes}
Your age: {age}
Your initial items: {inventory}

Set a personal long-term goal in one sentence:""",
            temperature=0.7,
            description="Agent personal goal setting"
        ))
        
        self.register_template(PromptTemplate(
            name="agent_action",
            system="""You control an intelligent agent in the simulation world. Strictly follow the given rules.

You need to:
1. Analyze current perception and memory
2. Consider your personal goal and attributes
3. Check your inventory for useful items
4. Describe your next action in natural language

Available action types:
- Movement: "move north/south/east/west"
- Collect resources: "collect nearby wood/stone/apples"
- Interact with other Agents: "chat with Agent X about Y topic", "trade items with Agent X"
- Craft items: "craft tool using wood and stone or other inventory items"
- Use items: "use torch to explore cave", "eat apple from backpack"
- Build: "build a hut"
- Rest/eat: "eat apple to restore energy", "rest to recover health"

Note: Be specific and concise. Make use of items in your inventory whenever helpful.""",
            user="""Era background: {era_prompt}

Current state:
{perception}

Memory summary:
{memory_summary}

Your inventory: {inventory}

Your goal: {goal}

Based on current state and memory, describe your next action:""",
            temperature=0.7,
            description="Agent action decision making"
        ))
        
        # === Trinity related prompts ===
        self.register_template(PromptTemplate(
            name="trinity_generate_initial_rules",
            system="""You are TRINITY - the world builder of sociological simulation. Generate appropriate terrain types and resource distribution rules based on era background.

Strict requirements:
1. Must return valid JSON format
2. Cannot contain any text outside JSON
3. All strings must use double quotes
4. Numbers must be valid floats (between 0.0-1.0)

JSON structure requirements:
{{
  "terrain_types": ["terrain1", "terrain2", "terrain3", "terrain4"],
  "resource_rules": {{
    "resource_name": {{
      "terrain_name": probability_value
    }}
  }}
}}

Example:
{{
  "terrain_types": ["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"],
  "resource_rules": {{
    "wood": {{"FOREST": 0.6, "GRASSLAND": 0.1}},
    "fish": {{"OCEAN": 0.4}},
    "stone": {{"MOUNTAIN": 0.7}}
  }}
}}""",
            user="""Era background: {era_prompt}

Generate for this era:
1. 4-6 terrain types (use English uppercase, like FOREST, OCEAN, etc.)
2. Resource distribution probability for each terrain (numbers between 0.0-1.0)

Requirements:
- Terrain types must match era characteristics
- Resource distribution must be reasonable
- If magical era, can include rare/magical resources
- Probability values should be balanced, not too high or low

Return only JSON, no other text:""",
            temperature=0.3,
            json_mode=True,
            validation_schema={
                "type": "object",
                "required": ["terrain_types", "resource_rules"],
                "properties": {
                    "terrain_types": {
                        "type": "array",
                        "minItems": 3,
                        "maxItems": 8
                    },
                    "resource_rules": {
                        "type": "object"
                    }
                }
            },
            examples=[
                '{"terrain_types": ["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"], "resource_rules": {"wood": {"FOREST": 0.5}, "fish": {"OCEAN": 0.4}}}',
                '{"terrain_types": ["DESERT", "OASIS", "ROCK", "CAVE"], "resource_rules": {"water": {"OASIS": 0.8}, "gems": {"CAVE": 0.2}}}'
            ],
            description="Trinity generates initial world rules"
        ))
        
        self.register_template(PromptTemplate(
            name="trinity_adjudicate",
            system="""You are TRINITY - the omniscient adjudicator of sociological simulation. Based on this round's global events, decide whether to:

1. Add new rules
2. Update resource distribution  
3. Change era (only on multiples of 10 rounds)

Requirements:
- Must return valid JSON
- Make fair and impartial decisions
- Consider era background
- No text outside JSON

Valid JSON formats:
1. Add rules: {{"add_rules": {{"rule_name": "description"}}}}
2. Update resources: {{"update_resource_rules": {{"resource_name": {{"terrain": probability}}}}}}
3. Change era: {{"change_era": "new_era_name"}}
4. Multiple actions: {{"add_rules": {{...}}, "update_resource_rules": {{...}}}}
5. No changes: {{}}""",
            user="""Era background: {era_prompt}
Current turn: {turn}

This round's global events:
{global_log}

Based on these events, decide if rules or era need adjustment. Return JSON decision:""",
            temperature=0.2,
            json_mode=True,
            max_retries=5,
            description="Trinity global event adjudication"
        ))
        
        self.register_template(PromptTemplate(
            name="trinity_execute_actions",
            system="""You are TRINITY - the manager maintaining world balance. Decide what actions to execute based on current world state.

Executable actions (legacy actions like "spawn_resources" are forbidden):
1. Regenerate resources: {{"regenerate_resources": {{"probability_multiplier": 1.0, "specific_resources": ["resource_name"]}}}}
2. Adjust terrain: {{"adjust_terrain": {{"positions": [[x,y]], "new_terrain": "type"}}}}
3. Influence agents: {{"environmental_influence": {{"agent_ids": [id], "effect": "description"}}}}
4. Add resource rules: {{"add_resource_rules": {{"resource": {{"terrain": probability}}}}}}
5. Climate change: {{"climate_change": {{"type": "climate_type", "effect": "effect_description"}}}}
6. No action: {{}}

Requirements:
- Must return valid JSON
- Actions must be reasonable and balanced
- Don't over-intervene
- Never use legacy actions like "spawn_resources"; only use the actions listed above""",
            user="""Current era: {era_prompt}
Turn: {turn}
Agent count: {agent_count}
Current resource rules: {resource_rules}
Resource status: {resource_status}

Decide what actions TRINITY should execute this turn:""",
            temperature=0.3,
            json_mode=True,
            description="Trinity executes balancing actions"
        ))
        
        # === ActionHandler相关提示词 ===
        self.register_template(PromptTemplate(
            name="action_handler_resolve",
            system="""You are the action resolution system that converts Agent natural language actions into game results.

Resolution principles:
1. Strictly follow bible rules
2. Consider agent attributes and capabilities  
3. Results must be realistic
4. Age restrictions must be enforced

Must return valid JSON with these fields:
- "inventory": inventory changes {{item_name: ±quantity}}
- "attributes": attribute changes {{attribute_name: ±value}}
- "position": new position [x, y] (optional)
- "log": action result description
- "chat_request": chat request (optional)
- "exchange_request": exchange request (optional) 
- "dead": whether dead (optional)

Example:
{{"inventory": {{"apple": -1}}, "attributes": {{"hunger": -10}}, "log": "Ate an apple, hunger decreased"}}""",
            user="""Bible rules: {bible_rules}

Agent info:
- ID: {agent_id}
- Attributes: {agent_attributes}
- Age: {agent_age} 
- Position: {agent_position}
- Inventory: {agent_inventory}
- Health: {agent_health}
- Hunger: {agent_hunger}

Action: {action}

Please resolve this action and return JSON:""",
            temperature=0.4,
            json_mode=True,
            description="Action resolution system"
        ))
        
        self.register_template(PromptTemplate(
            name="action_handler_chat_response",
            system="""You are an intelligent agent in a simulation world. Another Agent has asked you a question or made a request.

Response principles:
1. Based on your attributes and knowledge
2. Fit the era background
3. Concise and clear, one sentence answer
4. Maintain character consistency""",
            user="""Era background: {era_prompt}
Your attributes: {agent_attributes}
Your inventory: {agent_inventory}
Your age: {agent_age}

Other agent's question/request: {topic}

Please respond concisely:""",
            temperature=0.8,
            description="Agent chat response generation"
        ))
    
    def register_template(self, template: PromptTemplate):
        """注册新的提示词模板"""
        self.templates[template.name] = template
        logger.debug(f"注册提示词模板: {template.name}")
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """获取提示词模板"""
        return self.templates.get(name)
    
    def render_prompt(self, template_name: str, **kwargs) -> tuple[str, str, float]:
        """渲染提示词模板
        
        Returns:
            (system_prompt, user_prompt, temperature)
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"提示词模板不存在: {template_name}")
        
        try:
            system = template.system.format(**kwargs)
            user = template.user.format(**kwargs)
            return system, user, template.temperature
        except KeyError as e:
            raise ValueError(f"提示词模板 {template_name} 缺少参数: {e}")
    
    def get_template_config(self, template_name: str) -> Dict[str, Any]:
        """获取模板配置信息"""
        template = self.get_template(template_name)
        if not template:
            return {}
        
        return {
            "temperature": template.temperature,
            "max_retries": template.max_retries,
            "json_mode": template.json_mode,
            "validation_schema": template.validation_schema,
            "examples": template.examples
        }
    
    def validate_json_response(self, template_name: str, response: str) -> tuple[bool, Any]:
        """验证JSON响应"""
        template = self.get_template(template_name)
        if not template or not template.json_mode:
            return True, response
        
        try:
            data = json.loads(response)
            
            # 如果有验证schema，进行验证
            if template.validation_schema:
                # 简单的结构验证
                schema = template.validation_schema
                if schema.get("required"):
                    for field in schema["required"]:
                        if field not in data:
                            return False, f"缺少必需字段: {field}"
            
            return True, data
        except json.JSONDecodeError as e:
            return False, f"JSON解析错误: {e}"
    
    def load_from_config(self, config_path: str):
        """从配置文件加载提示词"""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.warning(f"配置文件不存在: {config_path}")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
            
            for name, template_data in config.get('templates', {}).items():
                template = PromptTemplate(
                    name=name,
                    system=template_data['system'],
                    user=template_data['user'],
                    temperature=template_data.get('temperature', 0.7),
                    max_retries=template_data.get('max_retries', 3),
                    json_mode=template_data.get('json_mode', False),
                    validation_schema=template_data.get('validation_schema'),
                    examples=template_data.get('examples'),
                    description=template_data.get('description', '')
                )
                self.register_template(template)
            
            logger.success(f"从 {config_path} 加载了 {len(config.get('templates', {}))} 个提示词模板")
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
    
    def save_to_config(self, config_path: str):
        """保存提示词到配置文件"""
        config = {
            "templates": {}
        }
        
        for name, template in self.templates.items():
            config["templates"][name] = {
                "system": template.system,
                "user": template.user,
                "temperature": template.temperature,
                "max_retries": template.max_retries,
                "json_mode": template.json_mode,
                "validation_schema": template.validation_schema,
                "examples": template.examples,
                "description": template.description
            }
        
        config_file = Path(config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            if config_file.suffix in ['.yaml', '.yml']:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            else:
                json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.success(f"提示词配置已保存到: {config_path}")
    
    def list_templates(self) -> List[str]:
        """列出所有可用的模板名称"""
        return list(self.templates.keys())
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取提示词统计信息"""
        stats = {
            "total_templates": len(self.templates),
            "json_templates": sum(1 for t in self.templates.values() if t.json_mode),
            "categories": {}
        }
        
        # 按前缀分类统计
        for name in self.templates.keys():
            prefix = name.split('_')[0]
            stats["categories"][prefix] = stats["categories"].get(prefix, 0) + 1
        
        return stats


# 全局提示词管理器实例
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager

def init_prompt_manager(config_path: Optional[str] = None) -> PromptManager:
    """初始化全局提示词管理器"""
    global _prompt_manager
    _prompt_manager = PromptManager(config_path)
    return _prompt_manager