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
            system="你是一个名字生成器，专门为模拟世界中的角色生成符合时代背景的名字。",
            user="根据以下信息生成一个合适的名字：\n属性: {attributes}\n年龄: {age}\n时代背景: {era}\n\n请只输出名字本身，不要包含任何解释或额外文本。",
            temperature=0.8,
            description="为Agent生成符合时代背景的名字"
        ))
        
        self.register_template(PromptTemplate(
            name="agent_decide_goal",
            system="""你是模拟世界中的一个智能体，需要根据自己的属性和时代背景制定一个现实可行的长期目标。

要求：
1. 目标要符合你的属性特点
2. 目标要符合时代背景的限制
3. 目标要具体、可执行
4. 用简体中文表达，一句话内完成""",
            user="""时代背景: {era_prompt}
你的属性: {attributes}
你的年龄: {age}
你的初始物品: {inventory}

请根据以上信息，制定一个符合你属性和时代背景的个人长期目标：""",
            temperature=0.9,
            description="为Agent制定个人长期目标"
        ))
        
        self.register_template(PromptTemplate(
            name="agent_action",
            system="""你控制着模拟世界中的智能体。请严格遵守给定的规则。

你需要：
1. 分析当前感知信息和记忆
2. 考虑你的个人目标和属性
3. 用自然语言描述你的下一步行动

可用行动类型：
- 移动: "向北/南/东/西移动"
- 收集资源: "收集附近的木材/石头/苹果"
- 与其他Agent交互: "和Agent X交谈关于Y话题", "向Agent X交易物品"
- 制造物品: "用木头和石头制作工具"
- 建造: "建造一个小屋"
- 休息/吃东西: "吃苹果恢复体力", "休息恢复健康"

注意：描述要具体、简洁，一句话说明你要做什么。""",
            user="""时代背景: {era_prompt}

当前状态:
{perception}

记忆摘要:
{memory_summary}

你的目标: {goal}

请根据当前状态和记忆，描述你的下一步行动：""",
            temperature=0.7,
            description="Agent执行行动的决策"
        ))
        
        # === Trinity相关提示词 ===
        self.register_template(PromptTemplate(
            name="trinity_generate_initial_rules",
            system="""你是TRINITY - 社会学模拟的世界构建者。你需要根据时代背景生成合适的地形类型和资源分布规则。

严格要求：
1. 必须返回有效的JSON格式
2. 不能包含任何JSON之外的文本
3. 所有字符串必须用双引号
4. 数字必须是有效的浮点数（0.0-1.0之间）

JSON结构要求：
{
  "terrain_types": ["地形1", "地形2", "地形3", "地形4"],
  "resource_rules": {
    "资源名": {
      "地形名": 概率值
    }
  }
}

示例：
{
  "terrain_types": ["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"],
  "resource_rules": {
    "wood": {"FOREST": 0.6, "GRASSLAND": 0.1},
    "fish": {"OCEAN": 0.4},
    "stone": {"MOUNTAIN": 0.7}
  }
}""",
            user="""时代背景: {era_prompt}

请为这个时代生成：
1. 4-6种地形类型（用英文大写，如FOREST, OCEAN等）
2. 每种地形的资源分布概率（0.0-1.0之间的数字）

要求：
- 地形类型要符合时代特征
- 资源分布要合理
- 如果是魔法时代，可以包含稀有/魔法资源
- 概率值要平衡，不要过高或过低

请只返回JSON，不要任何其他文本：""",
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
            description="Trinity生成初始世界规则"
        ))
        
        self.register_template(PromptTemplate(
            name="trinity_adjudicate",
            system="""你是TRINITY - 社会学模拟的全知裁判者。根据这一轮的全局事件，决定是否需要：

1. 添加新规则
2. 更新资源分布
3. 改变时代（仅在第10轮的倍数时）

要求：
- 必须返回有效JSON
- 公正公平地做出决定
- 考虑时代背景
- 不要任何JSON外的文本

有效的JSON格式：
1. 添加规则: {"add_rules": {"规则名": "描述"}}
2. 更新资源: {"update_resource_rules": {"资源名": {"地形": 概率}}}
3. 改变时代: {"change_era": "新时代名称"}
4. 组合多个: {"add_rules": {...}, "update_resource_rules": {...}}
5. 无变化: {}""",
            user="""时代背景: {era_prompt}
当前轮次: {turn}

本轮全局事件：
{global_log}

请根据这些事件，判断是否需要调整规则或时代。返回JSON格式的决定：""",
            temperature=0.2,
            json_mode=True,
            max_retries=5,
            description="Trinity对全局事件的裁决"
        ))
        
        self.register_template(PromptTemplate(
            name="trinity_execute_actions",
            system="""你是TRINITY - 维持世界平衡的管理者。根据当前世界状态决定执行什么行动。

可执行的行动：
1. 生成资源: {"spawn_resources": {"资源名": 数量}}
2. 调整地形: {"adjust_terrain": {"positions": [[x,y]], "new_terrain": "类型"}}
3. 影响Agent: {"influence_agents": {"agent_ids": [id], "effect": "描述"}}
4. 添加资源规则: {"add_resource_rules": {"资源": {"地形": 概率}}}
5. 无行动: {}

要求：
- 必须返回有效JSON
- 动作要合理且平衡
- 不要过度干预""",
            user="""当前时代: {era_prompt}
轮次: {turn}
Agent数量: {agent_count}
当前资源规则: {resource_rules}

请决定TRINITY这轮要执行的行动：""",
            temperature=0.3,
            json_mode=True,
            description="Trinity执行平衡行动"
        ))
        
        # === ActionHandler相关提示词 ===
        self.register_template(PromptTemplate(
            name="action_handler_resolve",
            system="""你是行动裁决系统，负责将Agent的自然语言行动转化为游戏结果。

裁决原则：
1. 严格遵守圣经规则
2. 考虑Agent属性和能力
3. 结果要现实合理
4. 年龄限制要严格执行

必须返回有效JSON，包含以下字段：
- "inventory": 背包变化 {物品: ±数量}
- "attributes": 属性变化 {属性: ±数值}
- "position": 新位置 [x, y] (可选)
- "log": 行动结果描述
- "chat_request": 聊天请求 (可选)
- "exchange_request": 交换请求 (可选)
- "dead": 是否死亡 (可选)

示例：
{"inventory": {"apple": -1}, "attributes": {"hunger": -10}, "log": "吃了一个苹果，饥饿度降低"}""",
            user="""圣经规则: {bible_rules}

Agent信息：
- ID: {agent_id}
- 属性: {agent_attributes} 
- 年龄: {agent_age}
- 位置: {agent_position}
- 背包: {agent_inventory}

行动: {action}

请裁决这个行动的结果，返回JSON：""",
            temperature=0.4,
            json_mode=True,
            description="行动裁决系统"
        ))
        
        self.register_template(PromptTemplate(
            name="action_handler_chat_response",
            system="""你是模拟世界中的智能体，另一个Agent向你提出了问题或请求。

回复原则：
1. 基于你的属性和知识
2. 符合时代背景
3. 简洁明了，一句话回答
4. 保持角色一致性""",
            user="""时代背景: {era_prompt}
你的属性: {agent_attributes}
你的背包: {agent_inventory}
你的年龄: {agent_age}

对方的问题/请求: {topic}

请简洁回答：""",
            temperature=0.8,
            description="Agent间对话回复生成"
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