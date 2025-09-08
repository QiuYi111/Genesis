# 模块契约与并行开发指引

本页将 REFACTORING_DELIVERY_PLAN 中的接口清单细化为可并行落地的契约与伪代码，覆盖核心模块：Core(World/Agent)、Trinity、LLMService、Web 导出/监控与 CLI。

## 目录
- Core: World / Agent / Actions / Events
- Trinity: observe / adjust 协议
- Services: LLMService Provider 接口
- Web: Exporter / WebSocket Monitor
- CLI: 入口与配置装配

---

## Core

稳定契约：
- `World.step(turn:int, trinity:Trinity) -> TurnResult`
- `Agent.decide(ctx:DecisionContext) -> Action` 必须纯函数
- 事件优先：`Agent.act()` 返回事件，由 `World` 统一结算副作用

关键伪代码：

```python
class Actions:
    MOVE = "move"; FORAGE = "forage"; CRAFT = "craft"; TRADE = "trade"


class World:
    def _apply_agent_events(self, agent: Agent, events: list[BehaviorEvent]) -> None:
        for e in events:
            if e.kind == "intent:move":
                self._move_agent(agent, e.data)
            elif e.kind == "forage":
                yield_ = e.data.get("yield", 0)
                agent.inventory.add("food", yield_)

    def _regenerate_resources(self, multiplier: float = 1.0) -> None: ...
    def _compute_metrics(self) -> dict[str, float]: ...
```

并行开发边界：
- Core 团队可在不依赖 LLM 的前提下完成 Tick 循环、资源结算与指标。
- 提供 `WorldView` 假对象，Agent 团队即可完成 `perceive/decide` 的单元测试。

---

## Trinity

契约：

```python
class Trinity:
    def observe(self, events: list[dict]) -> None: ...
    def adjust(self, world: World) -> TrinityActions: ...
```

伪代码：

```python
def observe(self, events: list[dict]) -> None:
    # 累积行为统计，为下一步调整做准备
    self._stats.update(events)


def adjust(self, world: World) -> TrinityActions:
    signals = world.compute_resource_status()
    # 使用 LLM 或启发式生成调整建议
    actions = self._planner.plan(signals)
    return TrinityActions(
        resource_regen_multiplier=actions.get("regen", 1.0),
        terrain_adjustments=actions.get("terrain"),
        skill_updates=actions.get("skills"),
    )
```

并行开发边界：
- 提供 `NullPlanner`（确定性），后续可替换为基于 `LLMService` 的 Planner。

---

## Services: LLMService Provider

契约（Provider 无状态/可换）：

```python
from typing import Protocol, TypedDict


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
        return "{}"  # 可预测占位
```

并行开发边界：
- Trinity 使用 `LLMProvider` 抽象，不直接依赖 `aiohttp`/网络。
- Core/World 可完全在 NullProvider 下运行。

---

## Web: Exporter / Monitor

契约：

```python
class Exporter(Protocol):
    def write_snapshot(self, snapshot: dict, *, turn: int) -> None: ...


class WebSocketMonitor:
    async def start(self, port: int) -> None: ...
    async def broadcast(self, snapshot: dict) -> None: ...
```

伪代码：

```python
async def simulation_loop(world: World, trinity: Trinity, monitor: WebSocketMonitor, turns: int):
    await monitor.start(port=8081)
    for t in range(turns):
        result = world.step(t, trinity=trinity)
        await monitor.broadcast(world.snapshot())
```

---

## CLI 装配

契约与伪代码：

```python
def main(cfg) -> None:
    world = World(size=cfg.world.size, seed=cfg.runtime.seed)
    trinity = Trinity(..., provider=NullProvider() if cfg.model.provider=="null" else OpenAIProvider(...))
    monitor = WebSocketMonitor(cfg.web.port)
    asyncio.run(simulation_loop(world, trinity, monitor, cfg.runtime.turns))
```

---

## 验收清单（并行开发）
- Agent：`decide()` 纯函数单测通过；动作事件覆盖 `move/forage/craft/trade`。
- World：`step()` 集成测试 30 turns 稳定；指标产出；资源再生可控。
- Trinity：在 NullProvider 下输出确定性 `TrinityActions`；可切换 Provider。
- Web：`snapshot()` JSON schema 稳定；WS 连接和心跳测试通过。
- CLI：Hydra 覆盖运行参数，`uv run pytest -q` 绿。

