# Runtime Snapshot v1

简要说明当前 `World.snapshot()` 的稳定输出 Schema（v1），用于 WebSocket 广播与文件导出。

## 字段说明

- `turn` (int)
  - 当前回合编号（从 0 开始）。
- `world` (object)
  - `size` (int): 世界边长（方格地图，size × size）。
- `agents` (array<object>)
  - `id` (int), `x` (int), `y` (int)
  - `inventory` (object): 物品清单（如 `wood/flint/food/spear`，缺省时视作 0）。
- `metrics` (object，均为 float)
  - `actions_per_turn`: 本回合产生的事件数（近似动作数）。
  - `resource_food`, `resource_wood`, `resource_flint`: 地图上对应资源总量。
  - `inv_spear`: 所有智能体持有的 `spear` 总数。
  - `scarcity`: 简单稀缺度指标（资源总量的单调递减函数）。
- `resources_heat` (array<array<int>>)
  - 资源热力图矩阵，大小为 `size × size`，元素为该格子的资源和（`food+wood+flint`）。

以上字段在 W2 冻结为 v1，后续演进将通过新增字段或 v2 版本号来兼容。

## 示例（截断）

```json
{
  "turn": 9,
  "world": { "size": 32 },
  "agents": [
    { "id": 0, "x": 12, "y": 7, "inventory": { "food": 1, "flint": 0, "wood": 0 } },
    { "id": 1, "x": 13, "y": 7, "inventory": { "spear": 1 } }
  ],
  "metrics": {
    "actions_per_turn": 10.0,
    "resource_food": 502.0,
    "resource_wood": 537.0,
    "resource_flint": 464.0,
    "inv_spear": 10.0,
    "scarcity": 0.000665
  },
  "resources_heat": [[0,1,0,...],[...],...]
}
```

## 导出与落盘

- CLI 运行时可开启导出，将每帧快照写入 `web_data/`：
  - `uv run python -m sociology_simulation.main world.num_agents=10 runtime.turns=10 web.export=true web.export_dir=web_data`
  - 生成文件：`web_data/snapshot_0000.json` ... `snapshot_0009.json`
- 相关实现：
  - `sociology_simulation/core/world.py::snapshot()`
  - `sociology_simulation/services/web/monitor.py::Exporter`
  - 可选：`sociology_simulation/services/web/exporter.py::FileExporter`

## 兼容性与演进

- v1 以离线演示与最小 Web 联调为目标；字段保持稳定。
- 新增字段将尽量保持向后兼容；破坏性调整会引入 `v2` 并提供迁移说明。

