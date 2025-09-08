# Project Genesis — 三人工程团队任务拆解（架构/契约/伪代码/任务卡）

本文件在《rewrite_implementation_plan》基础上，为三位工程师（A: Core，B: Trinity/LLM，C: Platform）提供清晰的架构边界、接口契约、伪代码骨架与可执行任务卡（含验收与预估工时）。

—

## 0. 统一约束（对三位工程师生效）
- 目录结构（建议）：
```
sociology_simulation/
  core/              # A 负责：Agent/World/Actions/Events（纯域层）
  trinity/           # B 负责：Trinity 引擎 + Planner（Null/LLM）
  services/
    llm/             # B 负责：LLM Providers（Null/DeepSeek/OpenAI）
    web/             # C 负责：WebSocket 广播
  persistence/       # C 负责：Exporter（快照持久化，可选）
  conf/              # C 负责：Hydra 配置组（runtime/world/model/logging）
  cli/               # C 负责：装配与演示入口
  main.py            # C 负责：orchestrator 入口（保持 -m 可运行）
```
- 依赖规则：UI/Web → Services → Trinity → Core（禁止向外逆向依赖与环依赖）。
- 测试：公共 API 全量类型注解；变更行覆盖率 ≥80%；网络/WS 测试走随机可用端口，具备超时与跳过策略。
- 默认 Provider：`null`（离线、确定性），任何 LLM 不可用时须自动回退 null。

—

## 1) 工程师 A — Core（World/Agent/Actions/Events）

职责与边界
- 提供纯领域循环：`perceive → decide(纯函数) → act(产事件) → 世界统一结算`。
- 输出只读 `WorldView` 给 Agent；`World.snapshot()` 提供观测数据给 Platform；不访问网络。

接口契约（Python 类型签名）
```python
# sociology_simulation/core/types.py
from dataclasses import dataclass, field
from typing import Protocol, TypedDict, Optional

@dataclass(frozen=True)
class Position:
    x: int
    y: int

class Inventory(TypedDict, total=False):
    wood: int
    flint: int
    spear: int
    food: int

class ActionType:
    MOVE = "move"
    FORAGE = "forage"
    CRAFT = "craft"
    TRADE = "trade"

@dataclass
class Action:
    type: str
    payload: dict[str, object] = field(default_factory=dict)

class BehaviorEvent(TypedDict):
    agent_id: int
    name: str
    turn: int
    data: dict[str, object]

class DecisionContext(TypedDict):
    pos: Position
    visible: list[tuple[Position, dict[str, int]]]
    neighbors: list[int]
    signals: dict[str, float]

class WorldView(Protocol):
    def get_visible(self, pos: Position, radius: int) -> list[tuple[Position, dict[str, int]]]: ...
    def get_neighbors(self, pos: Position, radius: int) -> list[int]: ...
    def get_signals(self) -> dict[str, float]: ...

class TurnResult(TypedDict):
    turn: int
    events: list[BehaviorEvent]
    metrics: dict[str, float]
```

```python
# sociology_simulation/core/agent.py
from .types import DecisionContext, Action

class Agent:
    id: int
    name: str
    pos: "Position"
    inventory: "Inventory"

    def perceive(self, world: "World", *, turn: int) -> DecisionContext: ...
    def decide(self, ctx: DecisionContext) -> Action: ...  # 纯函数（无 I/O/网络）
    def act(self, action: Action, world_view: "WorldView") -> list["BehaviorEvent"]: ...
```

```python
# sociology_simulation/core/world.py（关键公开方法）
from .types import TurnResult

class World:
    def __init__(self, size: int, seed: int) -> None: ...
    def step(self, turn: int, *, trinity: "Trinity") -> TurnResult: ...
    def snapshot(self) -> dict: ...
```

伪代码（结算循环）
```python
def step(self, turn: int, *, trinity: "Trinity") -> TurnResult:
    events: list[BehaviorEvent] = []
    for agent in self.agents:
        ctx = agent.perceive(self, turn=turn)
        act = agent.decide(ctx)                 # 纯函数
        evs = agent.act(act, self._world_view)  # 仅产事件
        self._apply_agent_events(agent, evs)    # 统一结算副作用
        events.extend(evs)

    trinity.observe(events)
    ta = trinity.adjust(self)
    self._apply_trinity_actions(ta)
    self._regenerate_resources(multiplier=ta.resource_regen_multiplier)
    metrics = self._compute_metrics()
    return {"turn": turn, "events": events, "metrics": metrics}
```

关键结算点（示意）
```python
def _apply_agent_events(self, agent: Agent, evs: list[BehaviorEvent]) -> None:
    for e in evs:
        if e["name"] == "move":
            agent.pos = e["data"]["to"]
        elif e["name"] == "forage":
            # 扣减资源网格，增加 agent.inventory
            ...
        elif e["name"] == "craft":
            # wood+flint → spear
            ...
        elif e["name"] == "trade":
            # 直接调整双方 inventory
            ...
```

任务卡与验收（A）
- A-1 核心类型与只读 WorldView（0.5d）
  - 交付：`core/types.py`、`WorldView` 协议与最小实现。
  - 验收：`Agent.decide()` 单测可用；无网络依赖。
- A-2 地形/资源初始化（1d）
  - 交付：seeded 地形与资源网格、基础再生参数。
  - 验收：同 seed 下生成一致；`_regenerate_resources()` 单测通过。
- A-3 行为与事件（1.5d）
  - 交付：move/forage/craft/trade 事件产出与结算。
  - 验收：变更库存与位置符合预期；配方 wood+flint→spear。
- A-4 Tick 循环与指标（1d）
  - 交付：`World.step()` 与 `_compute_metrics()`（如 actions/turn、scarcity）。
  - 验收：10/30 回合稳定运行，指标非空且合理。
- A-5 快照导出（0.5d）
  - 交付：`World.snapshot()`（world/agents/metrics 字段齐备）。
  - 验收：与 C 约定的 JSON Schema v1 通过测试。
- A-6 单测与边界用例（1d）
  - 交付：无 Agent/资源极端/满载场景单测。
  - 验收：覆盖率（变更行）≥80%。

—

## 2) 工程师 B — Trinity/LLM（Planner + Providers）

职责与边界
- 将核心与 LLM 解耦：Trinity 仅依赖 `LLMProvider` 抽象；默认 NullPlanner/NullProvider。
- 规划信号输入：基于世界稀缺度等信号输出 `TrinityActions`（再生倍数、技能与地形可选）。

接口契约（Python 类型签名）
```python
# sociology_simulation/trinity/contracts.py
from dataclasses import dataclass
from typing import Optional, TypedDict, Protocol

class Msg(TypedDict):
    role: str  # system|user|assistant
    content: str

class ModelCfg(TypedDict, total=False):
    model: str
    temperature: float
    timeout: float

class LLMProvider(Protocol):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str: ...

@dataclass
class TrinityActions:
    resource_regen_multiplier: float = 1.0
    terrain_adjustments: Optional[list[tuple["Position", str]]] = None
    skill_updates: Optional[dict[str, dict]] = None
```

```python
# sociology_simulation/trinity/trinity.py
class Trinity:
    def __init__(self, planner: "Planner") -> None: ...
    def observe(self, events: list[dict]) -> None: ...
    def adjust(self, world: "World") -> "TrinityActions": ...

class Planner(Protocol):
    def plan(self, signals: dict[str, float]) -> dict: ...
```

伪代码（Null/LLM Planner 与 Provider 回退）
```python
def adjust(self, world: "World") -> TrinityActions:
    signals = world.compute_resource_status()
    try:
        plan = self._planner.plan(signals)
    except Exception:
        plan = {"regen": 1.0}
    return TrinityActions(
        resource_regen_multiplier=float(plan.get("regen", 1.0)),
        terrain_adjustments=plan.get("terrain"),
        skill_updates=plan.get("skills"),
    )

class NullPlanner:
    def plan(self, signals: dict[str, float]) -> dict:
        return {"regen": 1.0}

class LLMPlanner:
    def __init__(self, provider: LLMProvider, cfg: ModelCfg) -> None:
        self.provider, self.cfg = provider, cfg
    def plan(self, signals: dict[str, float]) -> dict:
        messages = [
            {"role": "system", "content": "You are an ecosystem tuner."},
            {"role": "user", "content": f"signals={signals}"},
        ]
        # 同步封装或在上层以 asyncio.run 调用（测试中采用同步包装）
        text = run_async(self.provider.generate(messages, self.cfg), timeout=self.cfg.get("timeout", 5.0))
        return safe_json_loads(text) or {"regen": 1.0}
```

Providers（抽象与实现）
```python
# sociology_simulation/services/llm/base.py
class BaseProvider(LLMProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str: ...

# null.py
class NullProvider(BaseProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str:
        return "{}"  # 确定性

# deepseek.py / openai.py（占位接口，细节隐藏）
class DeepSeekProvider(BaseProvider):
    async def generate(self, messages: list[Msg], cfg: ModelCfg) -> str: ...
```

任务卡与验收（B）
- B-1 契约与骨架（0.5d）
  - 交付：contracts.py（Msg/ModelCfg/Provider/TrinityActions）、Trinity/Planner 接口。
  - 验收：可被 A/C 引用，无循环依赖。
- B-2 NullPlanner + NullProvider（0.5d）
  - 交付：稳定确定性输出；异常时返回 `{}` 或默认计划。
  - 验收：`adjust()` 在无网络环境稳定返回 regen=1.0。
- B-3 LLMPlanner 同步封装（1d）
  - 交付：`LLMPlanner` 使用 Provider；提供 `run_async()` 超时回退。
  - 验收：超时/异常→默认计划；单元测试覆盖。
- B-4 Provider 适配（1.5d）
  - 交付：DeepSeek/OpenAI 适配，读取 env；统一 `generate()` 入口。
  - 验收：Hydra 切换 `model.provider` 可替换；无泄密与硬编码 key。
- B-5 Trinity 统计与日志（0.5d）
  - 交付：`observe()` 聚合统计；日志分级。
  - 验收：统计字段随事件增长；日志结构化。
- B-6 单测与回退策略（0.5d）
  - 交付：异常路径、回退 Null 的用例。
  - 验收：覆盖率（变更行）≥80%。

—

## 3) 工程师 C — Platform（CLI/Config/Web/QA）

职责与边界
- 装配与运行体验：Hydra 配置、CLI 入口、Web 观测（WS 广播）、Exporter（可选）。
- 测试工具与覆盖率门槛；本地命令与文档一致。

接口契约（Python 类型签名）
```python
# sociology_simulation/services/web/monitor.py
from typing import Protocol

class Exporter(Protocol):
    def write_snapshot(self, snapshot: dict, *, turn: int) -> None: ...

class WebSocketMonitor:
    async def start(self, port: int) -> None: ...
    async def broadcast(self, snapshot: dict) -> None: ...
```

```python
# sociology_simulation/cli/main.py（装配伪代码）
def main(cfg) -> None:
    world = World(size=cfg.world.size, seed=cfg.runtime.seed)
    provider = make_provider(cfg.model)  # null/deepseek/openai
    planner = NullPlanner() if cfg.model.provider == "null" else LLMPlanner(provider, cfg.model)
    trinity = Trinity(planner)
    monitor = WebSocketMonitor()
    async_run(simulation_loop(world, trinity, monitor, turns=cfg.runtime.turns, port=cfg.web.port))

async def simulation_loop(world, trinity, monitor, *, turns: int, port: int):
    await monitor.start(port)
    for t in range(turns):
        result = world.step(t, trinity=trinity)
        await monitor.broadcast(world.snapshot())
```

Hydra 配置关键字段
- `runtime.yaml`: `turns`, `seed`
- `world.yaml`: `size`, `num_agents`, `regen.base`
- `model/{null,deepseek,openai}.yaml`: `provider`, `model`, `temperature`, `timeout`
- `logging.yaml`: 结构化日志级别与输出路径

任务卡与验收（C）
- C-1 CLI 入口与参数（0.5d）
  - 交付：`python -m sociology_simulation.main` 可运行；读取 Hydra 配置。
  - 验收：`world.num_agents=10 runtime.turns=30 model.provider=null` 跑通。
- C-2 配置组与示例（0.5d）
  - 交付：`conf/` 组建与 README 片段。
  - 验收：三种 Provider 的配置可解析；默认 null。
- C-3 WebSocketMonitor 骨架（1d）
  - 交付：`start()/broadcast()`；随机端口占用处理、心跳。
  - 验收：集成测试可启动、连接并广播 1 帧。
- C-4 Exporter（可选，0.5d）
  - 交付：写入 `web_data/` 快照文件；回滚策略。
  - 验收：文件存在且字段齐备。
- C-5 测试基建与覆盖率（1d）
  - 交付：pytest 配置、随机端口 fixture、异步测试示例。
  - 验收：核心与集成冒烟全绿；覆盖率报告出具。
- C-6 文档与命令对齐（0.5d）
  - 交付：README/WEB_UI_* 对齐；演示脚本固化。
  - 验收：新人 <15 分钟完成安装与演示。

—

## 4) 里程碑与依赖映射
- 里程碑 1（W1）：A-1..A-3、B-1..B-2、C-1..C-2 完成 → 本地 10 回合冒烟。
- 里程碑 2（W2）：A-4..A-5、B-3..B-4、C-3..C-4 完成 → 30 回合 + WS 1 帧广播。
- 里程碑 3（W3）：A-6、B-5..B-6、C-5..C-6 完成 → 覆盖率达标、文档齐备、演示脚本通过。

依赖关系（摘录）
- C-1 仅依赖 B-1 契约存在（无需实现）与 A-1 的类型定义。
- B-3 依赖 C-2 提供的 `model.*` 配置键。
- C-3 依赖 A-5 的 `snapshot()` Schema 冻结（可先以占位字段联调）。

—

## 5) 风险与对策（按角色）
- A：事件结算分散 → 统一 `_apply_agent_events()`；以参数化表驱动减少分支。
- B：LLM 不稳定 → Provider 超时/重试/回退 Null；提示词与解析严格受限（JSON 期望）。
- C：WS 脆弱 → 随机端口与超时、测试使用本地循环与小数据帧；快照 Schema 锁定 v1。

—

## 6) 交付检查清单（DoD）
- 入口命令：`uv run python -m sociology_simulation.main world.size=32 world.num_agents=10 runtime.turns=30 model.provider=null`。
- 测试：`uv run pytest -q` 全绿，变更行 ≥80% 覆盖。
- 规范：`uv run ruff check .`、`uv run black --check .` 通过。
- 可观测：`snapshot()` 字段齐备；WS 广播至少 1 帧；结构化日志。

— 完 —

