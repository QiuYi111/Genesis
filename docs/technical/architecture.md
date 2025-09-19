# 系统架构

## 概览

Project Genesis 采用分层架构设计，通过多个相互协作的子系统实现复杂的社会模拟。系统的核心理念是通过大量智能体的微观交互涌现出宏观的社会行为模式。

## 架构层次

```
┌─────────────────────────────────────┐
│           Trinity (神系统)            │
│        全局观察、规则创建、事件生成      │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│         社会结构层 (Social Layer)     │
│   群体、政治、经济、文化、技术系统       │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│        智能体层 (Agent Layer)        │
│    个体智能体、技能、社交网络、学习      │
└─────────────────────────────────────┘
                    │
┌─────────────────────────────────────┐
│        环境层 (Environment Layer)    │
│      地理、资源、自然事件、生态系统      │
└─────────────────────────────────────┘
```

## 核心组件

### Trinity 系统
**职责**: 全局管理和控制
- **行为观察**: 监控所有智能体行为模式
- **规则创建**: 基于观察到的行为动态创建新规则和技能
- **事件生成**: 创造自然灾害、环境变化等推动社会发展
- **时代管理**: 引导社会从原始时代向文明时代发展

**技术实现**:
```python
class Trinity:
    def __init__(self, bible: Bible, era_prompt: str):
        self.available_skills = {}          # 动态技能库
        self.skill_unlock_conditions = {}   # 技能解锁条件
        self.natural_events = []            # 自然事件队列
    
    async def analyze_agent_behaviors(self, world, session):
        # 分析智能体行为模式
        # 创建新技能和规则
        # 触发自然事件
```

### Bible 规则系统
**职责**: 动态规则管理
- **规则存储**: 维护所有交互规则的中央存储库
- **规则演化**: 根据 Trinity 的决策更新规则
- **规则查询**: 为智能体行动提供规则检索服务

更多细节与API请见：`docs/technical/bible.md`

### 智能体系统
**职责**: 个体行为和微观交互
- **动态技能**: 完全由 Trinity 根据行为创建的技能系统
- **社交网络**: 多维度的社会关系和声誉系统
- **学习机制**: 技能传授、知识获取、经验积累
- **适应行为**: 根据环境和社会压力调整行为策略

**核心数据结构**:
```python
@dataclass
class Agent:
    # 基础属性
    aid: int
    pos: Tuple[int, int]
    attributes: Dict[str, int]
    
    # 动态系统
    skills: Dict[str, Dict]              # Trinity创建的技能
    social_connections: Dict[int, Dict]  # 社交网络
    group_id: Optional[int]             # 所属群体
    reputation: Dict[str, int]          # 多维声誉
```

## 社会结构层

### 群体系统 (Social Structures)
**功能**: 社会组织的自然形成
- **动态组建**: 基于关系强度和共同目标形成群体
- **群体类型**: 家庭、工作团队、部落、行会等
- **集体行为**: 群体项目、资源共享、集体决策

### 文化记忆 (Cultural Memory)
**功能**: 知识和文化的传承
- **知识库**: 储存所有发现的知识和技术
- **传承机制**: 智能体间的知识传授系统
- **文化传统**: 习俗、仪式、社会规范的形成

### 技术系统 (Technology)
**功能**: 技术进步和创新
- **动态科技树**: 非预设的技术发展路径
- **创新机制**: 基于智能体行为的技术发现
- **时代进化**: 从石器时代到青铜时代的自然发展

### 经济系统 (Economics)
**功能**: 资源分配和贸易
- **市场形成**: 基于智能体聚集的自然市场
- **供需机制**: 动态价格和资源分配
- **专业化**: 基于技能优势的分工发展

### 政治系统 (Politics)
**功能**: 治理和权力结构
- **政治实体**: 议会、酋长制、城邦的自然形成
- **领导选择**: 基于影响力和能力的领导者产生
- **治理机制**: 资源分配、冲突解决、集体决策

## 数据流

### 向上数据流
```
环境状态 → 智能体感知 → 行为决策 → 社会互动 → 群体行为 → Trinity 观察
```

### 向下控制流
```
Trinity 决策 → 规则更新 → 技能创建 → 事件触发 → 环境变化 → 智能体适应
```

## 关键设计模式

### 1. 观察者模式
Trinity 作为全局观察者，监控所有子系统的状态变化：
```python
class Trinity:
    async def observe_behaviors(self, world):
        for agent in world.agents:
            behaviors = agent.get_behavior_data()
            self.analyze_for_skill_creation(behaviors)
```

### 2. 策略模式
不同类型的交互使用不同的处理策略：
```python
class InteractionSystem:
    def process_interaction(self, interaction_type, context):
        strategy = self.get_strategy(interaction_type)
        return strategy.execute(context)
```

### 3. 工厂模式
动态创建技能、群体、政治实体：
```python
class SkillFactory:
    @staticmethod
    def create_skill(skill_type, parameters):
        return Skill(
            name=parameters['name'],
            category=skill_type,
            unlock_conditions=parameters['conditions']
        )
```

## 扩展性设计

### 模块化结构
每个子系统都是独立的模块，可以单独开发和测试：
```
sociology_simulation/
├── agent.py              # 智能体系统
├── trinity.py            # Trinity 核心
├── social_structures.py  # 社会结构
├── cultural_memory.py    # 文化记忆
├── technology_system.py  # 技术系统
├── economic_system.py    # 经济系统
└── interaction_system.py # 交互系统
```

### 插件机制
支持第三方扩展和自定义模块：
```python
class PluginManager:
    def load_plugin(self, plugin_name):
        module = importlib.import_module(f"plugins.{plugin_name}")
        return module.initialize()
```

### 配置驱动
所有行为都可以通过配置文件调整：
```yaml
trinity:
  skill_creation_threshold: 0.7
  natural_event_frequency: 0.1
  
agents:
  learning_rate: 0.3
  social_connection_threshold: 5
```

## 实现要点与配置（对齐开发计划）

- 初始化与环境多样性（A）
  - 一次性规则生成 + 失败安全回退（保持默认地形/资源规则）。
  - 地形算法键：`world.terrain_algorithm`，支持 `simple | noise | voronoi | mixed`，并带进程内缓存（按尺寸/种子/算法/地形类型）。
  - 多样性校验：不足则回退至简化地形，资源为空则回退至默认规则重放置。

- 资源交互与可靠性（B）
  - `gather/consume` 进入本地分发逻辑，确定性、无 LLM 依赖；营养表与自动进食保持向后兼容。
  - 运行时配置：`runtime.hunger_growth_rate`、`runtime.auto_consume`（默认 true）。
  - Trinity 基线技能开局注入，避免 LLM 失败导致技能缺失。

- 演化与繁衍（C）
  - 每 3 回合在无动作时执行温和资源再生与轻微气候影响（演化回退）。
  - `Agent.numeric_states` 含 `stamina`，按行动施加体力消耗与冷却（启发式推断行动类型）。
  - Trinity 给出繁衍建议，World 以概率生成后代（属性混合并扰动）。

- 回合摘要与分析（D）
  - 先算事实（人口/群体/市场/政治/技术/技能多样性/社交/经济/事件），再请求 `trinity_turn_summary` 叙事。
  - 本地一致性守卫：清理与事实矛盾的描述（如“技能单一”在技能多样时被移除），补充“新技能”高亮。
  - 相关输出配置：`output.turn_summary_llm`、`output.turn_summary_max_highlights`。

说明：以上为当前实现采用的实际配置键名；若历史文档存在 `world.terrain.algorithm` 等嵌套命名，请以本节为准。

## 性能考虑

### 异步处理
大量智能体的并发处理：
```python
async def process_agents_parallel(agents):
    tasks = [agent.act() for agent in agents]
    await asyncio.gather(*tasks)
```

### 内存优化
- 延迟加载：只在需要时加载数据
- 对象池：重用频繁创建的对象
- 增量更新：只处理变化的部分

### 可扩展性
- 分布式处理：支持多进程/多机器扩展
- 数据分区：按地理区域分割处理
- 缓存策略：缓存频繁访问的数据

这种架构设计确保了系统的灵活性、可扩展性和可维护性，同时支持复杂的社会行为涌现。
