# Agent API 参考

本页定义智能体模块的接口契约，用于并行开发时保持边界稳定。示例代码以类型注解和伪代码表达，不代表最终实现细节。

## 数据结构

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Protocol


@dataclass
class Position:
    x: int
    y: int


@dataclass
class Inventory:
    items: Dict[str, int] = field(default_factory=dict)

    def add(self, name: str, qty: int) -> None: ...
    def remove(self, name: str, qty: int) -> bool: ...  # 返回是否成功
    def count(self, name: str) -> int: ...


@dataclass
class DecisionContext:
    turn: int
    pos: Position
    visible_tiles: List[Tuple[Position, Dict[str, int]]]  # (位置, 资源)
    neighbors: List[int]  # 附近其他 agent id
    inventory: Inventory
    skills: Dict[str, Dict]
    world_signals: Dict[str, float]  # 稀缺度等


@dataclass
class Action:
    type: str  # "move"|"forage"|"craft"|"trade"|...
    payload: Dict[str, object] = field(default_factory=dict)


@dataclass
class BehaviorEvent:
    agent_id: int
    turn: int
    kind: str
    data: Dict[str, object] = field(default_factory=dict)


class WorldView(Protocol):
    """Agent 对世界的最小只读视图接口（用于测试与并行开发）"""

    def get_visible(self, pos: Position, radius: int) -> List[Tuple[Position, Dict[str, int]]]: ...
    def get_neighbors(self, pos: Position, radius: int) -> List[int]: ...
    def get_signals(self) -> Dict[str, float]: ...  # 如资源稀缺度


@dataclass
class Agent:
    aid: int
    pos: Position
    inventory: Inventory = field(default_factory=Inventory)
    skills: Dict[str, Dict] = field(default_factory=dict)

    def perceive(self, world: WorldView, *, turn: int, radius: int = 2) -> DecisionContext: ...
    def decide(self, ctx: DecisionContext) -> Action: ...  # 纯函数，无网络/IO
    def act(self, action: Action, world: WorldView) -> List[BehaviorEvent]: ...
    def get_behavior_data(self) -> Dict[str, object]: ...  # 提供给 Trinity 观察
```

约束：
- `decide` 必须是纯函数，不得直接访问网络或 LLM；需要的信号从 `DecisionContext` 提供。
- `act` 只通过世界暴露的受限接口修改状态（或返回事件再由 World 应用）。

## 行为伪代码

```python
def perceive(self, world: WorldView, *, turn: int, radius: int = 2) -> DecisionContext:
    tiles = world.get_visible(self.pos, radius)
    neighbors = world.get_neighbors(self.pos, radius)
    signals = world.get_signals()
    return DecisionContext(turn, self.pos, tiles, neighbors, self.inventory, self.skills, signals)


def decide(self, ctx: DecisionContext) -> Action:
    # 简单启发式：资源稀缺则觅食，否则探索
    scarcity = ctx.world_signals.get("resource_scarcity", 0.0)
    if scarcity > 0.7:
        return Action("forage", {"target": max(ctx.visible_tiles, key=lambda t: sum(t[1].values()), default=None)})
    # 否则随机移动
    return Action("move", {"dx": 1, "dy": 0})


def act(self, action: Action, world: WorldView) -> List[BehaviorEvent]:
    events: List[BehaviorEvent] = []
    if action.type == "move":
        # 位置更新的实际应用由 World 进行，这里只记录意图
        events.append(BehaviorEvent(self.aid, turn=0, kind="intent:move", data=action.payload))
    elif action.type == "forage":
        events.append(BehaviorEvent(self.aid, turn=0, kind="forage", data={"yield": 1}))
    return events
```

## 测试约定

- 使用 `WorldView` 假对象对 `perceive/decide` 进行纯单元测试。
- 使用行为事件断言副作用（不直接断言世界状态）。

