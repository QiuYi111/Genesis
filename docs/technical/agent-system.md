# Agent 系统设计（个体行为与感知）

本章介绍 Project Genesis 中的 Agent（智能体）系统：个体的数据模型、感知与记忆、行动选择、数值状态（饥饿/健康/体力/冷却）、社交连接与技能成长，以及与 World/Trinity/Bible 的协同数据流。

- 模块路径：`sociology_simulation/agent.py`
- 行动执行：`World.ActionHandler`（确定性优先，位于 `sociology_simulation/world.py`）
- 关联系统：`World`（环境/调度）、`Trinity`（技能与规则）、`Bible`（规则总库）

## 概述

Agent 是模拟世界中的“个体实体”。每个 Agent 具备位置、背包、属性、技能与经验、社交关系、记忆和若干数值状态。每回合，Agent 感知环境与规则、按目标与技能选择行动、更新自身状态，并把行动日志反馈给 World 与 Trinity 形成闭环。

```python
@dataclass
class Agent:
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
    skills: Dict[str, Dict] = field(default_factory=dict)
    experience: Dict[str, int] = field(default_factory=dict)
    social_connections: Dict[int, Dict] = field(default_factory=dict)
    group_id: Optional[int] = None
    leadership_score: int = 0
    reputation: Dict[str, int] = field(default_factory=dict)
    numeric_states: Dict[str, float] = field(default_factory=dict)
    action_cooldowns: Dict[str, int] = field(default_factory=dict)
```

## 核心职责
- 感知环境：采集可视地块、邻近智能体以及 `Bible` 规则快照。
- 形成记忆：缓存遇到的智能体与位置信息，为后续决策提供上下文。
- 目标与行动：LLM 生成目标与自然语言行动；由 `ActionHandler` 解析、优先走本地确定性分发。
- 状态更新：根据行动结果与世界反馈更新背包、属性、技能经验、数值状态与日志。
- 社交互动：建立/强化社交连接，支撑群体/经济/政治子系统演化。

## 生命周期与数据流（每回合）

1) 感知（`perceive(world, bible)`）
- 以 `VISION_RADIUS` 采集可见地块与邻近智能体；从世界队列读取针对本体的 `pending_interactions`。
- 通过 `Bible.apply(...)` 注入结构化规则视图（物理/资源/行为/技能/社会等）。

2) 决策（`act(world, bible, era_prompt, session, action_handler)`）
- 汇总短期记忆（已知智能体与位置）；调用 LLM 产出自然语言行动。
- 交由 `ActionHandler.resolve(...)` 解析并执行；优先走确定性分发（如采集/消费）。

3) 应用结果（`apply_outcome(outcome)`）
- 合法性校验后写回 `inventory/attributes/position/health/hunger/skill_experience/skill_changes/log` 等字段。

4) 世界后处理（由 `World.step` 驱动）
- 年龄增长、饥饿/健康调整、自动进食（可配置）、冷却衰减。
- 社会/技术/经济/政治/交互子系统推进；Trinity 裁决与行动；Web 导出。

```text
感知 → LLM行动建议 → ActionHandler 解析/执行 → Agent 应用结果
  ↑               Bible 规则注入        ↓          ↑
World 回合推进 ← 日志/事实聚合 ← 子系统处理 ← Trinity 裁决/演化
```

## 感知与记忆（Perception & Memory）

- 感知范围：Chebyshev 距离 ≤ `VISION_RADIUS`；采集地形、地块资源与邻近智能体概览。
- 规则注入：`Bible.apply_to_perception` 将分门别类的规则附加到感知载荷中。
- 记忆内容：
  - `memory["agents"]`：遇见过的智能体（id/name/attributes/last_seen/last_pos/简易互动轨迹）。
  - `memory["locations"]`：到访过的位置（pos/terrain/resources/last_visited）。
- 决策摘要：`act` 时将记忆压缩成 `known_agents/known_locations` 作为 LLM 提示上下文。

## 行动决策与确定性分发

- 决策入口：`generate_agent_action(...)` 产出自然语言；`ActionHandler.resolve(...)` 解析执行。
- 确定性分发（无需 LLM）：
  - 采集（`gather`）就地扣取 `world.resources[(x,y)]`，写回 `agent.inventory`。
  - 消费（`consume`）依据营养表择优/按指定食物扣减背包、降低饥饿并小幅恢复健康。
  - 聊天/交换（`chat/exchange`）通过 `pending_interactions` 在回合初统一撮合。
- 其它复杂动作用 LLM 路径，且受 `Bible.get_rules_for_action_handler()` 提供的规则快照约束。

采集与消费（节选）：
```python
# world.ActionHandler._dispatch_gather()
pos = agent.pos
tile_resources = self.world.resources.get(pos, {})
# 解析“gather 2 wood”数量/品类，扣减地块资源，累计 inventory 变更

# world.ActionHandler._dispatch_consume()
nutrition = {"fish":25, "apple":20, "fruit":20, ...}
# 指定食物则优先消耗；否则选择营养最高项，降低 hunger 并 +health
```

## 数值状态与生存

- 内建字段：`hunger(0..100)`、`health(0..100)`；世界按回合增长饥饿、在高饥饿时扣减健康；饱食时小幅恢复健康。
- 自动进食：当 `runtime.auto_consume=True` 且饥饿 > 50，世界尝试用最优食物自动进食。
- 自定义数值：通过 `numeric_states` 支持拓展（如 `stamina` 等），Trinity 可批量更新：
```python
# Trinity.update_agent_numeric_state(...)
updates={"stamina": 80}, deltas={"stamina": -10}, remove=["fatigue"]
```
- 冷却与体力：`world.ActionHandler.action_costs` 提供行动体力消耗/冷却基线（可被规则/时代调整）。

## 技能与经验（由 Trinity 主导）

- 初始注入：Trinity 在构造时注入核心技能 `move/gather/consume/trade/craft/build` 保证基础行动稳定可用。
- Agent 侧 API：
  - `add_skill/modify_skill/remove_skill`：由 Trinity 或行动结果触发。
  - `get_skill_level/has_skill`：行为判定与 UI 展示辅助。
- 行为分析与解锁：`Trinity.analyze_agent_behaviors(...)` 汇总各体 `get_behavior_data()`，由 LLM 分析输出解锁/升级，统一应用回写。

## 社交连接与影响力

- 连接结构：`social_connections[target_id] = {relationship_type, strength, interactions, last_interaction_turn}`。
- 增强连接：`add_social_connection()` 可新建或增强强度，并累计交互次数。
- 影响力：`get_social_influence()` 综合连接强度、声誉与社交/领导技能得分，用于群体形成与政治/经济系统。

## 与 Trinity/Bible/World 集成

- Bible：
  - 感知阶段注入规则（`apply_to_perception`）。
  - 行为/建造/制造产生的“事实规则”通过 `Bible.update(...)` 固化，供后续 LLM 参考。
- Trinity：
  - 初始规则与技能注入、回合裁决（资源再生、气候效应、技能更新、繁衍建议）。
  - 数值状态批量调整（`update_agent_numeric_state`）。
- World：
  - 调度执行、并发保护、结果校验与清洗、死亡/出生、群体/技术/经济/政治/交互子系统推进与 Web 数据导出。

## Web UI 数据（简述）

- Agent 基本信息：`aid/name/pos/age/inventory/skills/hunger/health/social_connections`。
- 回合日志：`agent.log` 持续累积，UI 做摘要呈现；会话由 `World.get_conversations()` 标准化。
- 列表与选中详情：见 `docs/web-ui/` 文档与 `web_ui/js/simulation-ui.js`。

## 相关配置键（实现版）

- `runtime.hunger_growth_rate`：每回合饥饿增长基线（默认 3.0）。
- `runtime.auto_consume`：是否启用自动进食（默认 True）。
- `world.terrain_algorithm`：间接影响可采资源与生存压力。

## 使用示例

```python
import asyncio, aiohttp
from sociology_simulation.world import World

async def main():
    world = World(size=32, era_prompt="石器时代", num_agents=10)
    async with aiohttp.ClientSession() as session:
        await world.initialize(session)
        for _ in range(10):
            await world.step(session)

asyncio.run(main())
```

## 测试与验证

- 行动分发（确定性）：`sociology_simulation/tests/test_action_dispatch.py`（采集/消费）。
- 数值状态：`sociology_simulation/tests/test_numeric_state.py`（自定义状态与 Trinity 更新）。
- 背包与交互：`sociology_simulation/tests/test_core_systems.py`（库存操作、交易/群体相关）。
- Trinity 集成：`test_trinity_simple.py` 与 `docs/technical/trinity-system.md` 对照规则演化与回退路径。

## 最佳实践

- 确定性优先：能用本地逻辑完成的行动（采集/消费）优先，不依赖 LLM 确保可重复性。
- 事实闭环：将建造/制造等事实写入 `Bible.update(...)`，为后续提示与裁决提供依据。
- 渐进复杂：限制每回合的互动/发现量，保持系统节奏与观测性。
- 数值解耦：将可扩展的状态放入 `numeric_states`，由 Trinity 统一调整，避免散落在行动分支里。

## 相关文档
- Trinity 系统：`docs/technical/trinity-system.md`
- Bible 规则系统：`docs/technical/bible.md`
- World 回合引擎：`docs/technical/world.md`
