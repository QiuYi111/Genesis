# Trinity API 参考

## 概述

Trinity API 提供了与神系统交互的接口，允许开发者扩展和自定义 Trinity 的行为。Trinity 作为全局观察者和管理者，通过这些 API 实现智能决策和系统管理。

## 核心类

### Trinity 类

```python
class Trinity:
    """世界规则生成器和全局管理者"""
    
    def __init__(self, bible: Bible, era_prompt: str):
        """
        初始化 Trinity 系统
        
        Args:
            bible: Bible 实例，规则管理器
            era_prompt: 时代描述提示词
        """
        self.bible = bible
        self.era_prompt = era_prompt
        self.available_skills = {}
        self.skill_unlock_conditions = {}
        self.turn = 0
```

## 主要方法

### 规则生成

#### `_generate_initial_rules(session)`
```python
async def _generate_initial_rules(self, session: aiohttp.ClientSession) -> None:
    """
    基于时代背景生成初始规则
    
    Args:
        session: HTTP 会话对象
        
    Returns:
        None - 结果存储在实例属性中
        
    生成内容:
        - terrain_types: 地形类型列表
        - resource_rules: 资源分布规则
        - terrain_colors: 地形颜色映射
    """
```

**使用示例**:
```python
trinity = Trinity(bible, "石器时代部落")
async with aiohttp.ClientSession() as session:
    await trinity._generate_initial_rules(session)
    print(f"生成地形类型: {trinity.terrain_types}")
```

### 行为分析

#### `analyze_agent_behaviors(world, session)`
```python
async def analyze_agent_behaviors(
    self, 
    world: 'World', 
    session: aiohttp.ClientSession
) -> Dict[str, Any]:
    """
    分析智能体行为并管理技能系统
    
    Args:
        world: 世界实例
        session: HTTP 会话对象
        
    Returns:
        Dict: 技能分析结果
        {
            "agent_skill_changes": {
                "agent_id": {
                    "skill_name": {
                        "unlock": {"level": 1, "description": "解锁原因"},
                        "modify": {"level_change": 1, "exp_change": 10},
                        "remove": {"reason": "移除原因"}
                    }
                }
            },
            "global_skill_updates": {
                "new_skills": {
                    "skill_name": {
                        "description": "技能描述",
                        "category": "技能类别",
                        "unlock_conditions": ["条件1", "条件2"]
                    }
                }
            }
        }
    """
```

**使用示例**:
```python
# 分析智能体行为并创建新技能
skill_analysis = await trinity.analyze_agent_behaviors(world, session)

# 检查新创建的技能
new_skills = skill_analysis.get("global_skill_updates", {}).get("new_skills", {})
for skill_name, skill_data in new_skills.items():
    print(f"新技能: {skill_name} - {skill_data['description']}")
```

### 事件裁决

#### `adjudicate(global_log, session)`
```python
async def adjudicate(
    self, 
    global_log: List[str], 
    session: aiohttp.ClientSession
) -> None:
    """
    基于全局事件进行裁决并更新规则
    
    Args:
        global_log: 全局事件日志
        session: HTTP 会话对象
        
    副作用:
        - 更新 Bible 规则
        - 修改资源规则
        - 可能触发时代变迁
        - 创建新技能
    """
```

**返回的数据结构**:
```python
{
    "add_rules": {
        "rule_name": "规则描述"
    },
    "update_resource_rules": {
        "resource_name": {
            "terrain_type": new_probability
        }
    },
    "change_era": "新时代名称",
    "skill_updates": {
        "new_skills": {...},
        "update_unlock_conditions": {...}
    },
    "natural_events": {
        "type": "事件类型",
        "intensity": "强度",
        "description": "事件描述"
    }
}
```

### 生态管理

#### `execute_actions(world, session)`
```python
async def execute_actions(
    self, 
    world: 'World', 
    session: aiohttp.ClientSession
) -> None:
    """
    执行 Trinity 的生态管理行动
    
    Args:
        world: 世界实例
        session: HTTP 会话对象
        
    执行内容:
        - 分析智能体行为
        - 生态平衡管理
        - 资源再生
        - 环境调整
    """
```

**执行的行动类型**:
```python
{
    "update_resource_distribution": {
        "resource_name": {
            "terrain_type": new_probability
        }
    },
    "regenerate_resources": {
        "probability_multiplier": 1.5,
        "specific_resources": ["wood", "stone"]
    },
    "adjust_terrain": {
        "positions": [[x, y]],
        "new_terrain": "FOREST"
    },
    "environmental_influence": {
        "agent_ids": [1, 2, 3],
        "effect": "环境影响描述"
    },
    "climate_change": {
        "type": "drought",
        "effect": "干旱影响"
    }
}
```

## 技能系统 API

### 技能创建

#### `_process_skill_updates(skill_updates)`
```python
def _process_skill_updates(self, skill_updates: Dict) -> None:
    """
    处理技能系统更新
    
    Args:
        skill_updates: 技能更新数据
        {
            "new_skills": {
                "skill_name": {
                    "description": "技能描述",
                    "category": "技能类别"
                }
            },
            "update_unlock_conditions": {
                "skill_name": ["条件1", "条件2"]
            }
        }
    """
```

### 技能应用

#### `_apply_skill_changes_to_agent(agent, skill_changes)`
```python
def _apply_skill_changes_to_agent(
    self, 
    agent: 'Agent', 
    skill_changes: Dict
) -> None:
    """
    将技能变化应用到特定智能体
    
    Args:
        agent: 目标智能体
        skill_changes: 技能变化数据
        {
            "skill_name": {
                "unlock": {"level": 1, "description": "原因"},
                "modify": {"level_change": 1, "exp_change": 10},
                "remove": {"reason": "移除原因"}
            }
        }
    """
```

## 事件系统 API

### 自然事件生成

#### `generate_natural_event(world, turn)`
```python
async def generate_natural_event(
    self, 
    world: 'World', 
    turn: int
) -> Optional[Dict]:
    """
    生成自然事件
    
    Args:
        world: 世界实例
        turn: 当前回合数
        
    Returns:
        Optional[Dict]: 生成的事件数据
        {
            "event_type": "disaster/invasion/seasonal",
            "specific_event": "earthquake/flood/wolf_pack",
            "intensity": "low/medium/high",
            "duration": 3,
            "affected_area": {
                "center": [x, y],
                "radius": 5
            },
            "effects": {
                "terrain_changes": {...},
                "resource_changes": {...},
                "agent_effects": {...}
            },
            "description": "详细事件描述"
        }
    """
```

## 扩展 API

### 自定义技能创建器

```python
class CustomSkillCreator:
    """自定义技能创建器基类"""
    
    def analyze_behavior_pattern(
        self, 
        agent_behaviors: Dict
    ) -> List[Dict]:
        """
        分析行为模式并提出技能建议
        
        Args:
            agent_behaviors: 智能体行为数据
            
        Returns:
            List[Dict]: 技能建议列表
        """
        raise NotImplementedError
    
    def create_skill_definition(
        self, 
        behavior_pattern: Dict
    ) -> Dict:
        """
        基于行为模式创建技能定义
        
        Args:
            behavior_pattern: 行为模式数据
            
        Returns:
            Dict: 技能定义
        """
        raise NotImplementedError
```

### 自定义事件生成器

```python
class CustomEventGenerator:
    """自定义事件生成器基类"""
    
    def should_trigger_event(
        self, 
        world: 'World', 
        turn: int
    ) -> bool:
        """
        判断是否应该触发事件
        
        Args:
            world: 世界实例
            turn: 当前回合
            
        Returns:
            bool: 是否触发事件
        """
        raise NotImplementedError
    
    def generate_event(
        self, 
        world: 'World', 
        context: Dict
    ) -> Dict:
        """
        生成具体事件
        
        Args:
            world: 世界实例
            context: 事件上下文
            
        Returns:
            Dict: 事件数据
        """
        raise NotImplementedError
```

## 配置选项

### Trinity 配置参数

```yaml
trinity:
  # 技能系统配置
  skill_creation_threshold: 0.7      # 技能创建阈值
  max_skills_per_turn: 3             # 每回合最大技能创建数
  skill_spread_rate: 0.2             # 技能传播速率
  
  # 事件系统配置
  natural_event_frequency: 0.1       # 自然事件频率
  event_intensity_scaling: 1.0       # 事件强度缩放
  
  # 干预控制
  intervention_threshold: 0.5        # 干预阈值
  max_interventions_per_turn: 2      # 每回合最大干预次数
  
  # 时代管理
  era_advancement_threshold: 100     # 时代进步阈值
  innovation_point_scaling: 1.5     # 创新点数缩放
```

## 错误处理

### 常见异常

```python
class TrinityError(Exception):
    """Trinity 系统基础异常"""
    pass

class SkillCreationError(TrinityError):
    """技能创建失败异常"""
    pass

class EventGenerationError(TrinityError):
    """事件生成失败异常"""
    pass

class EraAdvancementError(TrinityError):
    """时代进步失败异常"""
    pass
```

### 异常处理示例

```python
try:
    await trinity.analyze_agent_behaviors(world, session)
except SkillCreationError as e:
    logger.error(f"技能创建失败: {e}")
    # 使用默认技能配置
    trinity.apply_default_skills()
except EventGenerationError as e:
    logger.warning(f"事件生成失败: {e}")
    # 跳过本回合事件生成
    pass
```

## 性能考虑

### 批量操作
```python
# 批量处理智能体行为分析
behaviors = trinity.collect_behaviors_batch(world.agents)
skill_updates = await trinity.analyze_behaviors_batch(behaviors, session)
trinity.apply_skill_updates_batch(skill_updates)
```

### 缓存机制
```python
# 启用 Trinity 决策缓存
trinity.enable_decision_cache(max_size=1000, ttl=300)

# 清理缓存
trinity.clear_decision_cache()
```

这个 API 参考提供了与 Trinity 系统交互的完整接口，支持自定义扩展和高级功能开发。