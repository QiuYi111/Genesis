# Project Genesis — 系统重构计划书（工程落地版）

本文档面向工程团队，给出可执行的重构目标、边界、接口契约、伪代码、任务拆分、风险与验收标准，便于并行推进并确保最小回归。

## 目录
- 1. 背景与问题综述
- 2. 重构目标与不在范围
- 3. 目标架构与依赖规则
- 4. 模块契约（接口与伪代码）
- 5. 渐进式迁移策略（分阶段）
- 6. 测试策略与验收标准
- 7. 任务拆分与并行开发
- 8. 风险与缓解
- 9. 验收演示脚本
- 10. 附录：清单与术语

---

## 1. 背景与问题综述

现状问题（基于代码与文档审阅）：
- 核心域与 LLM 强耦合：`world.ActionHandler` 直接调用 `enhanced_llm.get_llm_service()` 与 `aiohttp`，导致核心不可预测、难以单测。
- LLM 服务重复与抽象不统一：`enhanced_llm.py` 与 `services/llm_service.py` 均提供能力，接口风格不一致，增加维护成本。
- Trinity 接口边界不稳：`World` 直接调用 `Trinity._generate_initial_rules` 等内部方法与属性，存在隐式契约与脆弱依赖。
- Agent 决策与副作用缺少统一模式：缺少最小 `WorldView` 接口与“事件→统一结算”的副作用模式，影响可测性与并行开发。
- 初始化职责过宽：`World.initialize` 同时承担地形/资源/导出装配，建议移至更上层 orchestrator/CLI。

影响：
- 并行开发困难，测试成本高，接口变更牵一发而动全身，功能回归风险大。

---

## 2. 重构目标与不在范围

目标（MVP）：
- 架构分层清晰、接口契约稳定、可替换的 LLM Provider、核心循环可单测。
- 以 NullProvider（离线确定性）为默认，DeepSeek/OpenAI 作为可选实现。
- World 与 Agent 在不依赖网络的前提下可完成 30 回合仿真；Web 导出/监控独立装配。

不在范围：
- 引入全新社会系统（政治/文化/经济）的大改动；仅做必要抽象与包边。
- 性能优化与分布式扩展（留在 Post‑MVP）。

---

## 3. 目标架构与依赖规则

分层与依赖（内向依赖，禁止环）：
- UI/Web → Services → Core（Agent/World）
- Trinity 使用 Provider 策略，依赖抽象接口不依赖具体实现

建议目录（演进式，不强制重命名）：
```
sociology_simulation/
  core/              # 领域：Agent, World, Actions, Events（逐步内聚）
  services/          # LLM Provider(s), WebSocket, Logging
  trinity/           # Trinity 引擎与 Planner（可先维持 trinity.py + 适配器）
  persistence/       # Exporter / Snapshot（逐步从 world 中抽出）
  conf/              # Hydra 配置
  cli/               # CLI 入口与装配
```
依赖规则：
- Core 不访问网络、不依赖具体 LLM；只与 `Trinity` 契约交互。
- Trinity 不依赖具体 HTTP 客户端；只依赖 `LLMProvider` 抽象。
- Web/Exporter 不内嵌在 World；通过 `snapshot()` 或事件流工作。

---

## 4. 模块契约（接口与伪代码）

4.1 Core — World/Agent/Actions/Events
- 稳定契约：
  - `World.step(turn:int, *, trinity:Trinity) -> TurnResult`
  - `Agent.decide(ctx:DecisionContext) -> Action` 必须纯函数（无网络/IO）
  - `Agent.act(action, world_view) -> list[BehaviorEvent]` 返回事件，副作用由 World 统一结算

数据与伪代码（节选）：
```python
# Agent 侧最小只读视图（Protocol）
class WorldView(Protocol):
    def get_visible(self, pos: Position, radius: int) -> list[tuple[Position, dict[str, int]]]: ...
    def get_neighbors(self, pos: Position, radius: int) -> list[int]: ...
    def get_signals(self) -> dict[str, float]: ...  # 稀缺度等

@dataclass
class Action:
    type: str  # "move"|"forage"|"craft"|"trade"|...
    payload: dict[str, object] = field(default_factory=dict)

@dataclass
class TurnResult:
    turn: int
    events: list[dict]
    metrics: dict[str, float]

# World.tick 伪代码
def step(self, turn: int, *, trinity: Trinity) -> TurnResult:
    all_events = []
    for agent in self.agents:
        ctx = agent.perceive(self, turn=turn)
        action = agent.decide(ctx)       # 纯函数
        events = agent.act(action, self) # 只产出事件
        self._apply_agent_events(agent, events)  # 统一结算副作用
        all_events.extend(events)

    trinity.observe(all_events)
    ta = trinity.adjust(self)
    self.apply_trinity_actions(ta)
    self._regenerate_resources(multiplier=ta.resource_regen_multiplier)
    metrics = self._compute_metrics()
    return TurnResult(turn, all_events, metrics)
```

4.2 Trinity — 观察/调整
```python
class Trinity:
    def observe(self, events: list[dict]) -> None: ...
    def adjust(self, world: World) -> TrinityActions: ...

@dataclass
class TrinityActions:
    resource_regen_multiplier: float = 1.0
    terrain_adjustments: Optional[list[tuple[Position, str]]] = None
    skill_updates: Optional[dict[str, dict]] = None
```
伪代码：
```python
def observe(self, events):
    self._stats.update(events)

def adjust(self, world: World) -> TrinityActions:
    signals = world.compute_resource_status()
    plan = self._planner.plan(signals)  # 可为 NullPlanner 或 LLMPlanner
    return TrinityActions(
        resource_regen_multiplier=plan.get("regen", 1.0),
        terrain_adjustments=plan.get("terrain"),
        skill_updates=plan.get("skills"),
    )
```

4.3 Services — LLM Provider 抽象
```python
class Msg(TypedDict):
    role: str  # system|user|assistant
    content: str

class ModelCfg(TypedDict, total=False):
    model: str
    temperature: float
    timeout: float

class LLMProvider(Protocol):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str: ...

class NullProvider:
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:
        return "{}"  # 确定性占位，便于测试
```

4.4 Web — Exporter / Monitor
```python
class Exporter(Protocol):
    def write_snapshot(self, snapshot: dict, *, turn: int) -> None: ...

class WebSocketMonitor:
    async def start(self, port: int) -> None: ...
    async def broadcast(self, snapshot: dict) -> None: ...
```

4.5 CLI — 装配
```python
def main(cfg) -> None:
    world = World(size=cfg.world.size, seed=cfg.runtime.seed)
    provider = NullProvider() if cfg.model.provider=="null" else OpenAIProvider(...)
    trinity = Trinity(..., provider=provider)
    monitor = WebSocketMonitor(cfg.web.port)
    asyncio.run(simulation_loop(world, trinity, monitor, cfg.runtime.turns))
```

---

## 5. 渐进式迁移策略（分阶段）

阶段 0（当日）：文档与契约
- 本计划书与接口契约落地；确定验收口径与覆盖范围。

阶段 1（1–2 天）：抽象与去耦
- 引入 `WorldView` 与 `LLMProvider` Protocol；实现 `NullProvider`。
- 将 `World` 中副作用统一结算；为 `Agent.decide()` 提供纯上下文。
- 保持现有功能跑通：默认使用 NullProvider，避免网络依赖。

阶段 2（2–3 天）：统一 LLM 通道
- 以 `services/llm_service.py` 为中心，提供 Provider 适配层；逐步收口 `enhanced_llm.py` 能力（保留向后兼容函数，内部委托新通道）。
- Trinity 仅依赖 Provider 抽象；LLM 细节隐藏在服务层。

阶段 3（2 天）：初始化与导出解耦
- 将 Web 导出/监控装配移至 CLI/Orchestrator；`World` 暴露 `snapshot()`。
- 输出稳定 JSON Schema 供前端消费。

阶段 4（2–3 天）：测试与稳定
- 单元测试完善；集成测试 30 回合；WebSocket 连接/心跳；快照存档。
- 清理技术债与文档更新；准备演示脚本与 README 对齐。

---

## 6. 测试策略与验收标准

测试策略：
- 单元测试
  - Agent：`decide()` 纯函数，使用 `WorldView` 假对象
  - World：资源结算、再生、指标计算
  - Trinity：`observe/adjust` 在 NullProvider 下确定性
  - Services：Provider 超时/重试/缓存（如保留）
- 集成测试
  - CLI：5–30 回合跑通，日志与指标合理
  - Web：WS 启动、连接、广播一帧快照
- 覆盖率：变更行 ≥ 80%

验收标准（MVP）：
- `uv run python -m sociology_simulation.main world.num_agents=10 runtime.turns=30 model.provider=null` 跑通；无网络也稳定
- `uv run pytest -q` 全绿
- Web 演示可显示地图与 Agent 基本状态（WS 可选）

---

## 7. 任务拆分与并行开发

工作流与所有者（建议）：
- Core（A）：World/Agent/Actions/Events，Tick 循环与结算
- Trinity（B）：observe/adjust + Planner（Null→LLM）
- Services（C）：LLMProvider & 适配；统一 LLM 通道
- Web（D）：Exporter/Monitor；快照 Schema
- CLI/Config（E）：装配、Hydra 参数与运行脚本
- QA（F）：测试框架、数据构造器与覆盖率

关键边界（可立即并行）：
- A 可直接按 4.1 契约实现/重构，不依赖网络
- B 使用 NullProvider 先跑通，再接 Services 的真实 Provider
- C 独立完成 Provider 抽象与适配；对外仅 `generate(messages, cfg)`
- D 基于 `world.snapshot()` 开发，不需介入核心循环
- E 负责 orchestrator 装配与运行参数

---

## 8. 风险与缓解
- 既有行为回归 → 保留向后兼容函数；引入集成冒烟用例；灰度切换 Provider
- LLM 不稳定 → 默认 NullProvider；网络超时与重试落在适配层
- 并行冲突 → 严格接口契约；PR 检查表与小步合并

---

## 9. 验收演示脚本
- `uv sync`
- `uv run python -m sociology_simulation.main world.size=32 world.num_agents=10 runtime.turns=30 model.provider=null`
- 打开 `web_ui/index.html` 连接 `ws://localhost:8081`（可选）
- `uv run pytest -q` → 全绿

---

## 10. 附录：清单与术语

实施清单（DoD）：
- [ ] 引入 `WorldView` 与 `LLMProvider` Protocol
- [ ] 实现 `NullProvider` 并设为默认
- [ ] World 统一事件结算；`snapshot()` 可用
- [ ] Trinity 只依赖 Provider 抽象；`observe/adjust` 可测
- [ ] Web/Exporter/Monitor 与 World 解耦
- [ ] CLI 装配可运行 30 回合
- [ ] 单元/集成测试就绪，覆盖率达标
- [ ] 文档更新（本计划书、README 命令对齐）

术语：
- Provider：LLM 提供者策略（Null/DeepSeek/OpenAI）
- WorldView：Agent 的最小只读世界接口
- 事件结算：统一在 World 中应用副作用，避免副作用分散

— 结束 —

---

## 11. 角色分工与时间规划（分阶段并行）

说明：以下为工程角色 A–F 的分工建议。每个阶段内的任务互相解耦，可并行推进；仅在阶段间存在轻量依赖（见每阶段“先决条件/交付物”）。时间为净工作日估算，可并行压缩总体历时。

阶段 1（1–2 天）：抽象与去耦（可并行）
- A（Core）
  - 引入 `WorldView` Protocol；在 `World` 内部提供最小只读实现用于 Agent 感知
  - 建立“事件→统一结算”路径：实现 `_apply_agent_events()` 处理 move/forage/craft/trade
  - 输出：可在 NullProvider 下跑 5–10 回合的最小 tick 循环（无网络）
- B（Trinity）
  - 定义 `observe(events)`、`adjust(world) -> TrinityActions` 外部契约（不改内部复杂逻辑）
  - 实现 `NullPlanner` 返回确定性 `TrinityActions`
  - 输出：`adjust()` 在没有 LLM 的情况下返回稳定建议（默认为 1.0 regen）
- C（Services）
  - 定义 `LLMProvider` 接口与 `NullProvider`
  - 若保留现有 `services/llm_service.py`，提供到 Provider 的适配薄层；保留向后兼容 shim
  - 输出：`NullProvider.generate()` 可直接返回 `{}`
- D（Web）
  - 约定 `world.snapshot()` 最小 JSON Schema；实现最小导出器（文件写入占位即可）
  - 输出：在本地磁盘导出 1 帧快照（供后续集成）
- E（CLI/Config）
  - 增加运行参数 `model.provider=null`；装配 `NullProvider` 与新 Trinity 契约
  - 输出：`uv run python -m sociology_simulation.main ... model.provider=null` 可跑 5–10 回合
- F（QA）
  - 准备 WorldView 假对象；为 `Agent.decide()` 添加纯函数单测模板
  - 输出：单测基线、覆盖率统计初版

阶段 2（2–3 天）：统一 LLM 通道（可并行）
- A（Core）
  - 扩充分支事件结算与资源再生，补充 `compute_resource_status()` 与 `snapshot()`
  - 输出：30 回合本地稳定运行（仍可在 NullProvider）
- B（Trinity）
  - 接入 `LLMProvider`（保持可切换）；`adjust()` 内部改为 Planner 策略（Null/LLM）
  - 输出：在 Null 与真实 Provider 间可通过配置热切换
- C（Services）
  - 统一 `enhanced_llm.py` 与 `services/llm_service.py` 的入口：保留兼容函数，内部委派新 Provider 管理器
  - 实现 Provider 超时/重试/缓存（如已存在则封装为可选策略）
  - 输出：`generate(messages, cfg)` 单一入口；回归通过
- D（Web）
  - 将导出/监控与 World 解耦；对 `snapshot()` 做增量/全量策略（可先固定全量）
  - 输出：WebSocket 监控可选启动，能广播 1 帧
- E（CLI/Config）
  - 配置 Hydra 模块化：`model/{null,deepseek,openai}.yaml`
  - 输出：不同 Provider 选择通过 CLI 覆盖
- F（QA）
  - 增加 Trinity 在 NullProvider 下的确定性用例；Provider 切换的集成冒烟
  - 输出：集成冒烟脚本与断言

阶段 3（2 天）：初始化与导出解耦（可并行）
- A（Core）
  - 从 `World.initialize` 移除 Web 导出装配，保留纯状态初始化
  - 输出：核心不含 I/O/网络装配
- B（Trinity）
  - 对 `observe/adjust` 添加输入输出校验（schema 简检）与日志分级
  - 输出：更稳健的边界日志
- C（Services）
  - 完成 Provider 适配清理与文档化；补充 metrics/stats 接口（如已存在则统一）
  - 输出：`services` 文档与示例
- D（Web）
  - 完成导出器与监控服务化；增加最小心跳
  - 输出：WS 连接/心跳测试通过
- E（CLI/Config）
  - Orchestrator 汇总：World + Trinity + Monitor，端口可配置
  - 输出：一键跑通脚本
- F（QA）
  - 扩充集成测试：30 回合，快照存在与基本字段断言
  - 输出：CI 绿灯基线

阶段 4（2–3 天）：测试与稳定（可并行）
- A（Core）
  - 补齐边界用例：资源极端、无 Agent、满 Agent
  - 输出：Core 单测 ≥80% 变更行覆盖
- B（Trinity）
  - 对 Planner 的提示词/输出做健壮性测试（LLMProvider on/off）
  - 输出：稳定度报告与回退策略
- C（Services）
  - 压测/限流与缓存命中率统计（可选）
  - 输出：服务统计可读
- D（Web）
  - 导出 schema 锁定与最小前端联调
  - 输出：浏览器可见数据帧
- E（CLI/Config）
  - README/命令更新，与文档交叉验证
  - 输出：新手 15 分钟起步自测脚本
- F（QA）
  - 全量回归与覆盖率报告；缺陷收敛
  - 输出：发布签字

并行注意事项
- 契约先行：任何实现变更不得破坏 4 章的接口契约；如需调整，先开 PR 更新契约再实现
- 流水线：阶段 N 的产物不阻塞阶段 N+1 的不同角色（例如 D 可在 A 尚未完结时基于 `snapshot()` 协议先行）
- 站会节奏：每日 15 分钟同步接口变更与阻塞项；采用小步合并
