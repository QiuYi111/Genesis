# 性能分析与优化方案（针对超大规模 Agents）

> 目的：面向本仓库当前实现（`sociology_simulation/`）给出“定位 → 量化 → 优化”的可落地方案，解决随着 Agent 数量增长导致的显著变慢问题。

---

## 1. 症状与核心假设

- 症状：Agent 数量增大后，单回合（turn）耗时和整体内存占用快速上升，Web 导出与日志也明显拖慢。
- 核心假设：主要瓶颈来自（1）每回合大量 LLM 调用与无上限并发；（2）O(N²) 的邻居/可见性扫描；（3）多处对世界网格的全量遍历；（4）高频 I/O（日志、Web 数据）。

---

## 2. 代码级热点（按优先级）

- LLM 调用洪峰（高）：
  - 位置：`Agent.act()` → `enhanced_llm.generate_agent_action()`；回合内在 `World.step()` 用 `asyncio.gather` 对所有 Agents 同时触发。
  - 影响：N 个 Agent × 每回合 1 次以上 LLM；虽有 `LLMBatchProcessor` 与 `rate_limiter`，但任务数仍线性增长，内存和排队时间增大。

- 可见性/邻居扫描 O(N²)（高）：
  - 位置：`Agent.perceive()` 中对 `world.agents` 的线性遍历筛最近邻；当 Agents → 1k+ 时开销显著。

- 网格全量扫描（中-高）：
  - 位置：
    - `World.place_resources()`：双重循环遍历所有格子；
    - `Trinity._regenerate_resources()`：同样按地形全图扫描；
    - `Trinity._calculate_resource_status()`：为计算期望值每次再次全图统计地形数量。
  - 影响：复杂度接近 O(资源种类 × 地形种类 × size²)，在较大 `world.size` 下回合时间飙升。

- 回合内 I/O 与日志（中）：
  - 位置：
    - Web 导出：`save_turn_for_web()` + `export_incremental_web_data()` 每回合写文件；
    - 叙述总结：`turn_summary_llm` 为 True 时每回合额外一次 LLM；
    - 日志：`logger.info` 在多处高频打印，量随 Agents 增长线性上升。

---

## 3. 推荐的度量与画像方法（先量化再优化）

- 基线压测（cProfile）
  - 命令：
    - `uv run python -m cProfile -o prof.out -m sociology_simulation.main world.num_agents=200 runtime.turns=5 output.turn_summary_llm=false`
    - `uv run python - <<'PY'\nimport pstats; p=pstats.Stats('prof.out'); p.strip_dirs().sort_stats('tottime').print_stats(40)\nPY`

- 异步分段计时（建议临时插桩，不改外部接口）
  - 在 `World.step()` 关键阶段包裹 `time.perf_counter()`：
    - pending_interactions 处理
    - agents 行为阶段（`gather(*tasks)`）
    - 资源/地形处理
    - Trinity 裁决与行动
    - Web 导出与叙述总结

- LLM 服务指标
  - 在回合末读取 `get_llm_service().get_stats()`：总请求、缓存命中、平均延迟、失败率，用于检验调参与缓存效果。

- 内存画像（可选）
  - `tracemalloc` 快照比较回合前后对象增长；重点关注 `agent.log`、`world.resources`、临时大字典/列表。

---

## 4. 优化方案（按 ROI 排序）

1) 限流与分批执行 Agents 行为（强烈建议立即落地）
- 目标：避免一次性对所有 Agents 同时发起 LLM；将并发数控制在稳定值（如 64/128），降低峰值内存与尾延迟。
- 做法：在 `World.step()` 将
  - 现状：`tasks = [agent.act(...)]` + `await asyncio.gather(*tasks)`
  - 改为：用 `asyncio.Semaphore(K)` 包装 `agent.act`，或分批次（chunk）调度：每批 M 个，`await gather` 完进入下一批。
- 参考参数：`K ∈ [32, 128]`，依据 LLM RT 和机器内存压测确定。

2) 空间索引替代 O(N²) 近邻扫描（强烈建议）
- 目标：将 `Agent.perceive()` 的“可见 Agents”筛选从全量遍历降为按桶查询，复杂度降至 O(N + 邻居数)。
- 做法：
  - 在 `World` 维护 `grid: Dict[(x_cell,y_cell), Set[aid]]`（单/多分辨率桶）；
  - Agent 移动时更新所在桶；
  - 感知时只遍历相邻桶（覆盖 `VISION_RADIUS`）。
- 预计收益：当 N=5k、每桶几十个时，显著降低 CPU。

3) 资源/地形的预计算与增量维护（高性价比）
- 预计算：
  - `terrain_positions: Dict[str, List[(x,y)]]` — 初始化一次；
  - `terrain_counts: Dict[str, int]` — 用于 `_calculate_resource_status()` 的期望值无需每次遍历全图；
- 放置与再生：
  - `place_resources()` 与 `_regenerate_resources()` 从对应地形的 positions 列表随机抽样，避免 size² 双循环；
  - 对 `world.resources` 做增量更新而非每回合重扫。

4) LLM 访问层的削峰与去冗（易实现）
- 批处理调参：
  - `LLMBatchProcessor(batch_size, batch_timeout)`：适当增大 `batch_size`（如 8~16），稍增 `batch_timeout`（0.5~1.5s）换更高的合并率。
- 缓存策略：
  - 对 `generate_agent_action` 设置 `cache_key`：可由感知摘要（地形/邻居哈希 + 目标 + 年龄）构造；重复情景可命中缓存。
- 降级开关：
  - 规模压测关闭 `output.turn_summary_llm`；
  - 为 `Agent.act` 增加“规则优先、LLM 兜底”模式：部分常见行动走确定性规则（本仓库已有部分规则化处理入口：`World.ActionHandler._try_dispatch`）。

5) I/O 限速与批量化（低成本）
- Web 导出：
  - 仅每 N 回合导出一次（比如每 5/10 回合），或将 `export_incremental_web_data()` 的触发条件外置到配置；
  - 导出时控制 JSON 体积（裁剪 `agent.log` 最近 K 条）。
- 日志：
  - 将多数 `logger.info` 调整为 `logger.debug`，默认配置仅输出 `WARNING+`；
  - 结构化统计（每回合一行）优先于逐条事件打印。

6) 数据结构与小优化（按需）
- `world.resources` 的 key 由 `(x,y)` tuple → 整型偏移 `x*size+y`，可减小哈希与内存占用；
- 对多次使用的大字符串拼接改为 `join` 或累加 list 后一次性输出；
- 临界循环避免频繁属性查找（局部变量缓存）。

---

## 5. 配置与运行建议（直接可用）

- 大规模压测建议启动参数：
  - `uv run python -m sociology_simulation.main world.num_agents=2000 runtime.turns=10 output.turn_summary_llm=false logging.console.level="WARNING"`
- LLM 合并/限速（需代码里暴露成 Hydra 配置项）：
  - `model.batch_size=12 model.batch_timeout=1.0 model.max_concurrency=64`
- Web 导出节流（建议新增配置项并在导出点读取）：
  - `output.web_export_every=5 output.max_agent_log_entries=3`

---

## 6. 验收指标与目标

- 吞吐：回合平均时长随 Agents 数从 O(N²) 降为近似线性或亚线性；
- 稳定性：P99 回合时长 < 2 × P50；
- 资源：内存峰值随 N 的增长斜率显著降低；
- 费用：LLM 请求总量在相同 N、T 下下降 30%+（靠批处理与缓存）。

---

## 7. 建议的最小改动清单（落地顺序）

1. 在 `World.step()` 对 Agents 行为执行加并发上限（Semaphore 或分批）。
2. 在 `World` 新增网格桶索引；在 `Agent.perceive()` 改为按桶查询邻居。
3. 初始化构建 `terrain_positions`/`terrain_counts`，改写资源放置/再生与状态计算逻辑为抽样/增量。
4. 在 LLM 层增加 `cache_key` 与批处理参数读取，默认关闭回合叙述 LLM。
5. Web 导出与日志节流，添加配置。

以上 1–3 项通常即可带来数量级的性能改善（>3–10×）。

---

## 8. 后续路线（可选）

- 进程级并行：在不引入外部框架的前提下，可用多进程跑多个世界分片或批回合，再合并导出数据。
- 若引入分布式：可参考仓库已有的 `performance.md` 白皮书思路（Ray + asyncio + 连接复用），逐步演进到更高并发能力。

---

## 9. 附：定位到具体函数的速查表

- 行为调度：`World.step()`（并发上限、回合阶段计时）
- 感知开销：`Agent.perceive()`（邻居查询 O(N²) → 网格桶）
- 资源放置/再生：`World.place_resources()`；`Trinity._regenerate_resources()`（全图扫描 → 抽样）
- 资源状态：`Trinity._calculate_resource_status()`（预存地形计数）
- LLM 管理：`services/llm_service.py`（`LLMBatchProcessor`、`LLMCache`、并发信号量）
- Web 导出：`web_export.py`（导出频率与数据裁剪）

如需，我可以按以上清单逐项提交最小代码改动 PR（先并发上限与网格索引）。

