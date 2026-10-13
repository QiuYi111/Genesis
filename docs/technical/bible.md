# Bible 规则系统（Simulation Rulebook）

本系统中的 “Bible” 不是宗教文本，而是模拟世界的动态“规则总库”。它集中存储并对外提供所有可被智能体与LLM遵循的规则，且可在运行时由 Trinity 生成与演化。

- 模块路径：`sociology_simulation/bible.py`
- 主要参与者：`World`、`Trinity`、`ActionHandler(LLM)`
- 关联配置：`sociology_simulation/conf/prompts.yaml`（注入 Bible 规则到提示词）

## 职责
- 规则存储：集中管理规则集（RuleSet）与规则（Rule）。
- 规则演化：接收 Trinity 或世界事件的更新，形成版本化历史。
- 规则查询：为智能体感知与 LLM 动作解析提供结构化规则视图。
- 冲突治理：支持优先级、依赖与冲突处理策略。
- 可观测性：记录规则使用情况与成功率，便于调优。

## 核心数据结构
```python
# sociology_simulation/bible.py
class RuleCategory(Enum):
    PHYSICS = "physics"        # 物理规律
    RESOURCES = "resources"    # 资源规则
    SKILLS = "skills"          # 技能系统
    ACTIONS = "actions"        # 行为规则
    ITEMS = "items"            # 物品系统
    ATTRIBUTES = "attributes"  # 属性系统
    SOCIAL = "social"          # 社会规则
    INTERACTIONS = "interactions" # 交互规则
    ECONOMICS = "economics"    # 经济规则
    CULTURE = "culture"        # 文化规范
    MAGIC = "magic"            # 超自然规则
    TECHNOLOGY = "technology"  # 科技规则

@dataclass
class Rule:
    id: str
    name: str
    category: RuleCategory
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)
    effects: List[str] = field(default_factory=list)
    priority: int = 1  # 1-10
    version: int = 1
    created_time: float = field(default_factory=time.time)
    active: bool = True
    conflicts_with: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    usage_count: int = 0
    success_rate: float = 1.0

@dataclass
class RuleSet:
    name: str
    description: str
    rules: Dict[str, Rule] = field(default_factory=dict)
    era_context: str = ""
    version: int = 1
```

## 关键 API（精选）
- `add_rule(rule, rule_set_name=None) -> bool`：添加规则，含冲突检测与历史记录。
- `update_rule(rule_id, updates, rule_set_name=None) -> bool`：更新规则并自增版本。
- `deactivate_rule(rule_id, reason="", rule_set_name=None) -> bool`：停用规则但保留。
- `get_active_rules(category: Optional[RuleCategory]=None, ...) -> List[Rule]`：按类过滤活动规则。
- `apply_to_perception(perception: Dict) -> Dict`：为智能体感知附加分类规则。
- `get_rules_for_action_handler(action_type: str=None) -> Dict`：为 LLM 动作解析提供结构化快照（含分类、高优先级、冲突策略、依赖、元信息）。
- `record_rule_usage(rule_id, success, context=None)`：记录规则使用统计，更新成功率。
- 兼容层：`update(new_rules: Dict[str,str])` 将 name→desc 快速注入为 `SOCIAL` 类规则；`apply(...)` 为 `apply_to_perception` 别名。

## 生命周期与数据流
1. World 初始化：
   - `world = World(...)` 创建 `Bible()` 与 `Trinity(bible, era_prompt)`。
   - Trinity 生成初始地形/资源规则（失败回退到默认）。
2. 回合推进：
   - Trinity 根据日志与世界状态裁决：`Trinity.adjudicate(...)` → `bible.update(...)` 或结构化 `add_rule(...)`。
   - 世界事件（如建造/制造）也会 `bible.update({...})` 将新约束固化为规则。
3. 动作解析：
   - `ActionHandler.resolve(...)` 在向 LLM 发出请求前，调用 `bible.get_rules_for_action_handler()` 注入“Bible Rules”。
4. 统计与演化：
   - 执行结果可调用 `record_rule_usage(...)`，为后续裁决与调参提供依据。

```text
Agents → 行为/事件 → Trinity 观察与裁决 → Bible 更新
            ↑                             ↓
        LLM 解析 ← 注入 Bible 规则 ← ActionHandler
```

## 与 Trinity 集成
- Trinity 产生/调整规则（如资源分布、技能解锁、社会规范），写入 Bible：
```python
# sociology_simulation/trinity.py
if "add_rules" in data:
    self.bible.update(data["add_rules"])  # 兼容层：快速注入描述性规则
# 建议：在需要精细管理时，构造 Rule 并使用 bible.add_rule(rule)
```
- 世界事件也会将建造/工具制造固化为规则：
```python
# sociology_simulation/world.py（片段）
self.bible.update({
    f"building_{building['type']}": f"Requires {building.get('materials', 'unknown')}"
})
```

## 与 ActionHandler/Prompt 集成
- 提示词中有显式要求：“Strictly follow bible rules”。
- 注入点：
```python
bible_rules = json.dumps(self.bible.get_rules_for_action_handler(), ensure_ascii=False)
```
- `conf/prompts.yaml` 相关片段：
```yaml
# action_handler_resolve.system
1. Strictly follow bible rules
...
# action_handler_resolve.user
=== Bible Rules ===
{bible_rules}
```

### `get_rules_for_action_handler()` 输出示例（简）
```json
{
  "all_rules": [{"id": "basic_physics", "category": "physics", "priority": 10, ...}],
  "by_category": {"physics": [...], "social": [...]},
  "high_priority": [{"id": "basic_physics", ...}],
  "conflict_resolution": [
    {"type": "priority_override", "description": "Higher priority rules override lower priority ones"},
    {"type": "context_specific", "description": "More specific conditions win"},
    {"type": "newer_version", "description": "Newer overrides older"}
  ],
  "rule_dependencies": {"rule_x": ["rule_a", "rule_b"]},
  "meta": {"rule_set_name": "default", "era_context": "generic", "total_active_rules": 5, "last_update": 1710000000}
}
```

## 规则类别与组织建议
- 物理/资源：位移、碰撞、资源刷新与分布等硬约束。
- 行为/交互：动作合法性、冷却、消耗、失败原因。
- 技能/科技：技能创建、解锁条件、科技前置与效果。
- 社会/文化/经济/政治：声誉、交易、治理、规范与处罚。
- 物品/属性：物品制作、耐久、属性上下限与变更规则。

命名规范：
- `id` 使用稳定、可追踪的键：`physics.movement.v1`、`skill.craft.basics`。
- `priority` 用于冲突裁决；高优先级覆盖低优先级。
- `conditions` 与 `parameters` 结构化表达触发条件与参数。

## 使用示例
```python
from sociology_simulation.bible import Bible, Rule, RuleCategory

bible = Bible()

rule = Rule(
    id="actions.build.hut",
    name="建造茅屋",
    category=RuleCategory.ACTIONS,
    description="建造 hut 需要木材与最小年龄限制",
    parameters={"materials": {"wood": 5}, "min_age": 16},
    conditions=["terrain in ['FOREST','PLAIN']"],
    effects=["adds shelter", "improves health recovery"],
    priority=6,
)

bible.add_rule(rule)

# 更新规则参数
bible.update_rule("actions.build.hut", {"parameters": {"materials": {"wood": 4}}})

# 某次解析后记录使用情况
bible.record_rule_usage("actions.build.hut", success=True, context={"agent": 3, "era": "石器时代"})

# 向 LLM 提供规则快照
payload = bible.get_rules_for_action_handler()
```

## 冲突与依赖
- 冲突：`conflicts_with` 明确互斥关系，或依赖通用冲突策略：
  - priority_override（高优先级覆盖）
  - context_specific（更具体条件优先）
  - newer_version（新版本覆盖旧版本）
- 依赖：`dependencies` 指明前置规则；`get_rules_for_action_handler()` 会暴露依赖图以供 LLM 参考。

## 统计与可观测性
- `record_rule_usage()` 持续累积 `usage_count/success_rate`，并写回到规则对象。
- `get_rule_statistics()` 汇总总数、各类规则平均使用/成功率、Top 规则等，便于诊断。

## 兼容层（Legacy）
- `update({name: desc})` 将键值对快速转为 `SOCIAL` 规则，适合简单文本性约束。
- `apply(perception)` 是 `apply_to_perception` 的别名，兼容旧接口。

## 最佳实践
- 小而清晰：倾向于“细粒度、可组合”的规则，便于裁决与冲突处理。
- 显式条件：将关键前置条件写入 `conditions/parameters`，避免隐性假设。
- 版本化与优先级：重大语义变化请提升 `version/priority`。
- 数据闭环：在 ActionHandler 或世界逻辑中调用 `record_rule_usage()` 形成度量闭环。
- 与 Trinity 解耦：Trinity 负责生成与裁决，Bible 负责存储与对外展示。

## 相关文档
- 架构总览：`docs/technical/architecture.md`（见 “Bible 规则系统” 与 Trinity 流程）
- 提示词配置：`sociology_simulation/conf/prompts.yaml`

