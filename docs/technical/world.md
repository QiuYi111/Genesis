# World 世界系统（环境与回合引擎）

本章介绍 Project Genesis 的 World（世界）模块：负责初始化地形与资源、承载智能体与社会系统、推进回合并与 Trinity/Bible 协同驱动社会演化。

- 模块路径：`sociology_simulation/world.py`
- 主要参与者：`World`、`Agent`、`Trinity`、`Bible`、社会/技术/经济/政治/文化子系统
- 关联配置：`sociology_simulation/config.py`（Hydra 注入），`conf/`（提示词与运行参数）

## 概述

World 是模拟的“运行时容器”和“环境大脑”。它在初始化阶段构建地形与资源分布，创建智能体，并将各社会子系统（群体、文化记忆、技术、经济、政治、交互）接入。随后的每个回合由 World 驱动：收集/处理交互、分发行动、推进子系统、与 Trinity 协作裁决，并导出 Web 监控所需的数据。

```python
class World:
    def __init__(self, size: int, era_prompt: str, num_agents: int):
        self.bible = Bible()
        self.trinity = Trinity(self.bible, era_prompt)
        self.social_manager = SocialStructureManager()
        self.cultural_memory = CulturalMemorySystem()
        self.tech_system = TechnologySystem()
        self.economic_system = EconomicSystem()
        self.political_system = PoliticalSystem()
        self.interaction_system = InteractionSystem()
```

## 职责
- 环境构建：生成地形（多算法）、投放资源（基于 Trinity 规则，失败回退默认）。
- 个体容器：创建/维护智能体、处理移动/采集/消费等基本行为。
- 社会推进：驱动群体、文化、技术、经济、政治等子系统演化。
- 回合调度：并发执行智能体行动，聚合日志与事实指标，生成叙事摘要。
- 规则协作：调用 Trinity 进行裁决与行动执行；把新建造/制造固化到 Bible。
- 可观测性：导出 Web 监控 JSON，便于开发调试与演示。

## 生命周期与数据流

1) 初始化（`initialize(session)`）
- 调用 `Trinity._generate_initial_rules()` 获取地形类型与资源分布规则（异常与不合法时回退到 `DEFAULT_*`）。
- `generate_realistic_terrain()` 生成地形（支持 `simple | noise | voronoi | mixed`，不稳定时回退 simple）。
- `place_resources()` 按资源规则随机投放，若投放为空则回退到默认规则并重试。
- 创建智能体，初始化 Web 导出（`initialize_web_export()` + `save_world_for_web()`）。

2) 回合推进（`step(session)`）
- 处理 `pending_interactions`（聊天/交换等），清空队列。
- 让每个智能体决定/执行行动；超时保护；执行后处理（出生/死亡、饥饿与健康、冷却与体力等）。
- 推进社会/文化/技术/交互/经济/政治系统；根据启发式建议发起互动与组建群体。
- `Trinity.adjudicate()`、`Trinity.execute_actions()`；按建议概率处理繁衍。
- 生成事实指标（`_collect_turn_facts()`）与涌现报告（`_generate_emergent_behavior_report()`）。
- 可选 LLM 叙事（`turn_summary_llm`）；本地校验与清洗（`_validate_and_correct_summary()`）。
- 导出回合数据（`save_turn_for_web()`、`export_incremental_web_data()`）。

```text
Agents 行为 → World 汇总 → 子系统推进 → Trinity 裁决/行动
             ↑                                       ↓
       Bible 规则固化 ← 建造/制造/事件      Web 导出 ← 回合日志/事实/叙事
```

## 核心方法（精选）

- `initialize(session)`：一次性生成规则/地形/资源并创建智能体；初始化 Web 导出。
- `generate_realistic_terrain()`：按 `world.terrain_algorithm` 选择算法；异常/低多样性回退 `generate_simple_terrain()`。
- `place_resources()`：依据 Trinity 的 `resource_rules` 投放资源。
- `step(session)`：推进一回合，处理交互→行动→子系统→Trinity→导出→回合计数自增。
- `get_conversations()`：从智能体日志中提取标准化会话行（用于 UI）。
- `_collect_turn_facts(turn_log)`：计算事实指标（人口、群体/市场/政治体数、技能多样性、社交、经济健康、重要事件等）。
- `_generate_emergent_behavior_report()`：基于阈值的启发式涌现报告（不依赖 LLM）。
- `_validate_and_correct_summary(facts, json)`：叙事实体校验与清洗（移除与事实矛盾的语句，补充“新技能”高亮）。
- `_try_consume_food(agent)`：在高饥饿时自动择优消费食物，降低饥饿并小幅恢复健康。

## 内部 ActionHandler（确定性优先）

World 内置 `ActionHandler` 负责解析/执行行动。为保证可重复性与稳定性，优先使用本地确定性分发：

- 行为范畴：`move/gather/build/craft/trade/consume/chat`。
- 采集（`_dispatch_gather`）：就地检查 `world.resources` 并以确定性方式扣取/写回；无 LLM 依赖。
- 消费（`_dispatch_consume`）：根据营养表选择指定/最优食物；同步世界自动进食逻辑。
- 交换（`exchange`）/聊天（`chat`）：通过 `pending_interactions` 管道在回合初统一处理。
- 制造/建造：若 `attempt_create` 附带规则且合法则入库；成功后将“工具/建筑”写入世界，并更新 Bible 兼容层：

```python
self.bible.update({
    f"building_{building['type']}": f"Requires {building.get('materials', 'unknown')}"
})
```

当本地分发未覆盖或需要复杂推理时，ActionHandler 才会走 LLM 路径（通过 `enhanced_llm` 和 prompts 配置）。

## 与 Trinity/Bible 集成

- 初始化：`Trinity._generate_initial_rules()` 产出 `terrain_types/resource_rules`，World 做严格校验与失败回退。
- 回合：`Trinity.adjudicate(turn_log)` 进行裁决；`Trinity.execute_actions(world)` 执行建议（如自然事件、技能变化）。
- 繁衍建议：Trinity 提供候选对，World 按概率生成新智能体，属性为父母加噪融合。
- 规则固化：建造/制造会通过 `Bible.update({...})` 写入简要规则，便于后续 LLM 解析参考。

## Web 导出与监控

- 初始化：`initialize_web_export()` 注入世界尺寸/时代/规则，`save_world_for_web()` 保存初始地形与资源。
- 回合：`save_turn_for_web()` 写入智能体、会话、事件与日志；`export_incremental_web_data()` 定期导出增量 JSON。
- 前端：`web_ui/` 中的 `index.html` 和 `js/simulation-ui.js` 消费这些 JSON 渲染地图与状态。

## 相关配置键（实现版）

- `world.terrain_algorithm`：`simple | noise | voronoi | mixed`（默认 `mixed`）。
- `runtime.hunger_growth_rate`：饥饿增长速率；`runtime.auto_consume`：是否自动进食。
- `output.turn_summary_llm`：是否启用 LLM 叙事；`output.turn_summary_max_highlights`：叙事高亮上限。

以上键来自 `sociology_simulation/config.py`，由 Hydra 注入并在运行期可通过 CLI 覆盖。

## 事实驱动的回合摘要

- 先计算事实（`_collect_turn_facts`），再调用 `get_llm_service().trinity_turn_summary(...)` 生成 `summary/highlights/warnings`。
- 使用 `_validate_and_correct_summary` 做一致性防护：
  - 移除与事实冲突的语句（如“技能单一”但事实显示技能多样）。
  - 当有新技能时，默认在高亮中补充 “新技能: ...”。

## 使用示例

```python
import asyncio, aiohttp
from sociology_simulation.world import World

async def main():
    world = World(size=32, era_prompt="石器时代", num_agents=10)
    async with aiohttp.ClientSession() as session:
        await world.initialize(session)
        for _ in range(30):
            await world.step(session)

asyncio.run(main())
```

Web 演示（内置脚本）：
- `uv run python run_simple_web_simulation.py`
- 打开浏览器访问：`http://localhost:8081`

## 测试与验证

- 食物与生存：`test_food_consumption.py`（自动进食、最优食物选择、饥饿/健康变化）。
- Web 监控数据：`test_web_ui.py`（监控更新、日志导出、静态文件结构、WebSocket 启动）。
- Trinity 集成：参考 `docs/technical/trinity-system.md` 与 `docs/api/trinity-api.md` 的裁决/行为接口。

## 最佳实践与注意事项

- 失败回退优先：任何外部/LLM 步骤失败均需回退到稳定的默认路径（地形与资源规则、simple 地形）。
- 确定性优先：能本地确定执行的行动（采集/消费等）优先走确定性分发，减少不必要的 LLM 调用。
- 事实优先的叙事：叙事仅作为补充展示，必须以事实集为准并通过本地校验清洗。
- 渐进复杂：每回合限制新互动/发现数量（如最多 2 个新互动、3 次科技尝试）以保持节奏与可观测性。

## 相关文档
- Trinity 系统：`docs/technical/trinity-system.md`
- Bible 规则系统：`docs/technical/bible.md`
- 架构总览：`docs/technical/architecture.md`

