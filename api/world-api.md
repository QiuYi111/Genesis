# World API 参考

本页定义世界模块的接口契约，确保核心循环与 Trinity、Agent 的解耦以便并行开发。

## 核心类型

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


Position = Tuple[int, int]


@dataclass
class TurnResult:
    turn: int
    events: List[Dict]
    metrics: Dict[str, float]


@dataclass
class TrinityActions:
    resource_regen_multiplier: float = 1.0
    terrain_adjustments: Optional[List[Tuple[Position, str]]] = None
    skill_updates: Optional[Dict[str, Dict]] = None


class World:
    size: int
    seed: int
    terrain: Dict[Position, str]
    resources: Dict[Position, Dict[str, int]]
    agents: Dict[int, object]  # 仅存引用，行为由 Agent 自身处理

    def __init__(self, size: int, seed: int) -> None: ...
    def add_agent(self, agent: object, pos: Position) -> None: ...
    def step(self, turn: int, *, trinity: Trinity) -> TurnResult: ...

    # 供 Agent 使用的最小世界视图
    def get_visible(self, pos: Position, radius: int) -> List[Tuple[Position, Dict[str, int]]]: ...
    def get_neighbors(self, pos: Position, radius: int) -> List[int]: ...
    def get_signals(self) -> Dict[str, float]: ...

    # Trinity 交互
    def apply_trinity_actions(self, actions: TrinityActions) -> None: ...
    def compute_resource_status(self) -> Dict[str, float]: ...

    # 其它
    def snapshot(self) -> Dict: ...  # 用于 Web 导出/监控
```

## Tick 循环伪代码

```python
def step(self, turn: int, *, trinity: Trinity) -> TurnResult:
    # 1) Agent 回合
    all_events: List[Dict] = []
    for agent in self.agents.values():
        ctx = agent.perceive(self, turn=turn)
        action = agent.decide(ctx)
        events = agent.act(action, self)
        # 实际状态变更由 World 应用（例如移动、资源采集结算）
        self._apply_agent_events(agent, events)
        all_events.extend(events)

    # 2) Trinity 观察与调整
    trinity.observe(all_events)
    ta = trinity.adjust(self)
    self.apply_trinity_actions(ta)

    # 3) 资源再生/环境演进
    self._regenerate_resources(multiplier=ta.resource_regen_multiplier)

    # 4) 统计指标
    metrics = self._compute_metrics()
    return TurnResult(turn=turn, events=all_events, metrics=metrics)
```

## 设计约束

- World 不直接依赖具体 LLM 实现；与 Trinity 交互通过方法契约与数据对象。
- Agent 的状态变更统一通过 World 的结算函数应用，避免分散副作用。
- `snapshot()` 输出为 Web/UI 的稳定 JSON Schema：
  - `world`: 尺寸、地形摘要、资源热力
  - `agents`: id、name、pos、inventory、skills、current_action
  - `logs`: level、message、turn（选）

