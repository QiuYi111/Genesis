# Trinity 系统设计

## 概述

Trinity 是 Project Genesis 的核心"神系统"，负责全局观察、规则创建和社会发展引导。作为全知全能的管理者，Trinity 通过分析智能体行为模式来动态创建技能、触发自然事件，并推动社会从原始时代向文明时代发展。

## 核心职责

### 1. 行为观察与分析
Trinity 持续监控所有智能体的行为，识别模式和趋势：

```python
async def analyze_agent_behaviors(self, world, session):
    # 收集所有智能体的行为数据
    agent_behaviors = {}
    for agent in world.agents:
        agent_behaviors[agent.aid] = agent.get_behavior_data()
    
    # 分析行为模式
    skill_analysis = await self._analyze_for_skills(agent_behaviors)
    
    # 应用技能变化
    self._apply_skill_changes(world, skill_analysis)
```

**分析维度**:
- **行为频率**: 智能体重复执行的行动
- **创新行为**: 尝试新的行动组合
- **社会互动**: 智能体间的合作模式
- **适应行为**: 对环境变化的反应

### 2. 动态技能创建
基于观察到的行为模式，Trinity 动态创建新技能：

**技能创建触发条件**:
- 智能体反复建造 → 创建 "建筑学" 技能
- 智能体调解冲突 → 创建 "外交" 技能
- 智能体发现新材料 → 创建 "材料学" 技能
- 群体合作狩猎 → 创建 "团队作战" 技能

**技能创建流程**:
```python
def create_skill_from_behavior(self, behavior_pattern):
    skill_name = self.generate_skill_name(behavior_pattern)
    skill_description = self.generate_skill_description(behavior_pattern)
    unlock_conditions = self.determine_unlock_conditions(behavior_pattern)
    
    new_skill = {
        "name": skill_name,
        "description": skill_description,
        "category": self.categorize_skill(behavior_pattern),
        "max_level": 10,
        "unlock_conditions": unlock_conditions
    }
    
    self.available_skills[skill_name] = new_skill
```

### 3. 自然事件生成
Trinity 作为自然力量的代表，生成推动社会发展的事件：

**事件类型**:
- **灾害事件**: 地震、洪水、干旱、瘟疫
- **资源事件**: 新资源发现、资源枯竭
- **生物事件**: 动物入侵、迁徙、疾病传播
- **气候事件**: 季节变化、极端天气

**事件生成逻辑**:
```python
async def generate_natural_event(self, world, turn):
    # 评估当前社会发展水平
    development_level = self.assess_development_level(world)
    
    # 根据发展水平选择合适的事件
    if development_level == "primitive":
        event_type = random.choice(["animal_invasion", "resource_discovery"])
    elif development_level == "developing":
        event_type = random.choice(["natural_disaster", "seasonal_change"])
    
    # 生成具体事件
    event = await self.create_event(event_type, world, turn)
    return event
```

### 4. 时代管理
Trinity 监控技术和社会发展，引导时代进步：

**时代进化条件**:
```python
def check_era_advancement(self, world):
    current_era = self.current_era
    next_era_requirements = self.eras[current_era + 1]
    
    # 检查技术要求
    tech_requirements_met = all(
        tech in self.discovered_techs 
        for tech in next_era_requirements["required_techs"]
    )
    
    # 检查社会发展要求
    social_requirements_met = (
        len(world.social_manager.groups) >= next_era_requirements["min_groups"] and
        world.tech_system.innovation_points >= next_era_requirements["innovation_threshold"]
    )
    
    if tech_requirements_met and social_requirements_met:
        self.advance_era()
        return True
    return False
```

## 决策机制

### LLM 驱动的智能决策
Trinity 使用大语言模型进行复杂决策：

```python
async def make_decision(self, context, decision_type):
    llm_service = get_llm_service()
    
    if decision_type == "skill_creation":
        response = await llm_service.trinity_analyze_behaviors(
            era_prompt=self.era_prompt,
            turn=self.turn,
            agent_behaviors=context["behaviors"],
            available_skills=self.available_skills,
            session=context["session"]
        )
    elif decision_type == "natural_event":
        response = await llm_service.trinity_natural_events(
            era_prompt=self.era_prompt,
            turn=self.turn,
            development_level=context["development_level"],
            recent_activities=context["activities"],
            session=context["session"]
        )
    
    return response
```

### 已落地的演化与繁衍机制（实现说明）

- 基线技能注入：Trinity 在初始化即注入核心技能集 `move/gather/consume/trade/craft/build`，保证基础行动稳定可用。
- 演化回退路径：当某回合没有可执行的 LLM 输出时，每 3 回合触发一次温和资源再生与轻微气候影响，确保系统稳态推进而非停滞。
- 繁衍建议：基于健康、年龄、物资与邻近度的启发式配对，交由 World 以一定概率生成后代，属性为父母混合并带少量扰动。

### 事实驱动的回合摘要

- 事实收集：World 先计算回合事实（人口、群体、市场、政治实体、技术数、技能多样性、社交连边、经济健康、重要事件等）。
- 叙事生成：通过 `trinity_turn_summary` 提示词生成 JSON 叙事（`summary/highlights/warnings`），并在本地进行一致性校验与清洗，避免出现与事实相矛盾的表述（例如“技能单一”但指标显示技能多样）。

### 相关配置键（实现版）

- `world.terrain_algorithm`: 地形算法选择，`simple | noise | voronoi | mixed`。
- `runtime.hunger_growth_rate`: 饥饿增长速率；`runtime.auto_consume`: 是否自动进食。
- `output.turn_summary_llm`: 是否启用 LLM 叙事；`output.turn_summary_max_highlights`: 高亮数量上限。

### 决策平衡机制
Trinity 需要在干预和自然发展之间保持平衡：

**干预原则**:
- **最小干预**: 只在必要时进行干预
- **自然引导**: 通过环境事件而非直接命令引导发展
- **平衡发展**: 防止某一方面发展过快或过慢
- **危机响应**: 在社会面临崩溃时提供帮助

## 提示词系统

### 技能分析提示词
```yaml
trinity_analyze_behaviors:
  system: |
    你是 TRINITY - 模拟世界的技能系统管理者。分析智能体行为并决定技能解锁、创建和修改。
    
    你的职责：
    1. 分析智能体行为寻找技能解锁模式
    2. 当智能体展现创新行为时创建新技能
    3. 基于使用模式修改现有技能
    4. 平衡整个群体的技能发展
    
    技能创建原则：
    - 基于重复的智能体行为创建技能
    - 技能应该符合时代背景
    - 新技能解锁新的行动可能性
    - 平衡个体专业化与合作需求
```

### 自然事件提示词
```yaml
trinity_natural_events:
  system: |
    你是 TRINITY - 模拟世界的自然力量控制者。生成推动社会发展和合作的自然事件。
    
    事件设计原则：
    - 事件应该迫使智能体合作或适应
    - 创造新技能和技术的机会
    - 匹配时代背景（石器时代不会有现代灾害）
    - 平衡挑战与生存可能性
    - 事件可以揭示隐藏资源或创造新需求
```

## 反馈循环

### 社会发展反馈
Trinity 创建的技能和事件会影响智能体行为，进而影响社会发展：

```
智能体行为 → Trinity 观察 → 技能创建 → 新行为可能性 → 更复杂的社会结构
```

### 环境适应反馈
自然事件迫使社会适应，推动技术和社会创新：

```
自然事件 → 生存压力 → 合作需求 → 新技能发展 → 社会复杂化
```

### 知识积累反馈
技能和知识的积累加速社会发展：

```
技能积累 → 知识传承 → 创新能力提升 → 更快的技术进步 → 时代进步
```

## 性能优化

### 批量处理
Trinity 批量处理智能体行为分析：

```python
async def batch_analyze_behaviors(self, world):
    # 每3回合进行一次深度分析
    if self.turn % 3 == 0:
        await self.deep_behavior_analysis(world)
    else:
        # 轻量级日常监控
        await self.light_monitoring(world)
```

### 缓存机制
缓存频繁使用的决策结果：

```python
class TrinityCache:
    def __init__(self):
        self.skill_creation_cache = {}
        self.event_generation_cache = {}
    
    def get_cached_decision(self, context_hash):
        return self.skill_creation_cache.get(context_hash)
```

### 渐进式处理
将复杂决策分解为多个步骤：

```python
async def progressive_decision_making(self, world):
    # 第一步：快速模式识别
    patterns = self.identify_patterns(world)
    
    # 第二步：候选技能生成
    candidates = self.generate_skill_candidates(patterns)
    
    # 第三步：详细评估和创建
    for candidate in candidates:
        if self.evaluate_skill_candidate(candidate):
            await self.create_skill(candidate)
```

Trinity 系统通过这种设计实现了真正的动态和智能化社会管理，确保模拟社会能够自然地发展出复杂的结构和行为模式。
