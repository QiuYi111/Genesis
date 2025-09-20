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

---

## 10. 实验与结果（离线基准）

- 目的：在“无真实 LLM 调用”的前提下，隔离并量化内核热点（邻居感知、全图扫描、Web 导出与日志），观察随 Agents 数的扩展趋势。
- 方法：
  - 新增 `scripts/bench_offline.py`，对 `EnhancedLLMService.generate` 进行本地 stub，避免网络与重试；以最小配置构造 `World` 并运行指定回合。
  - 记录每回合耗时（`time.perf_counter()`）。
  - 关闭叙述 LLM；日志为 WARNING 级，减少 I/O 干扰；地形算法设为 `simple` 保障可重复性。
  - 命令示例：`uv run -q python scripts/bench_offline.py --agents 300 --turns 5 --size 64`

- 结果（优化前 → 优化后，macOS aarch64，本地环境，size=64，单位：秒/回合）：

  - 100 agents × 5 turns → 0.218（基线，仅采样一次）
  - 300 agents × 5 turns → 0.730 → 0.696 → 0.702（采样后方差内波动，整体与上一版持平）
  - 600 agents × 3 turns → 1.693 → 1.626 → 1.628（采样后基本持平）

- 观察：
  - 优化项（已落地）：
    - 新增空间网格（cell=VISION_RADIUS），`perceive()` 邻居查询从全量遍历改为遍历相邻桶并按半径过滤；
    - 预生成 `terrain_positions`/`terrain_counts`，资源再生/期望值估算改为按索引遍历；
  - 效果：空间网格与地形索引带来 4–5% 降幅；资源“抽样化”在本参数（p≈0.1、地图 64×64）下对回合耗时影响较小（已避免逐格判定，但抽样选位与赋值仍与期望数量同阶）。在更大地图或更多资源种类时，抽样法可显著缩短资源阶段时间。

- 结论与行动项映射：
  - 先落地“网格桶索引 + 分批/限流”两项，预计对 300~600 规模的回合时长带来 2× 以上改善；
  - 将资源放置/再生改为“按地形 positions 抽样 + 预存 terrain_counts”，在大尺寸地图时收益更显著；
  - Web 导出和日志维持节流策略，仅在里程碑回合输出。

---

## 11. 在线测试（真实 LLM）

- 测试命令：
  - `uv run python scripts/bench_online.py --agents 10 --turns 1 --api-key '<KEY>' --cap-calls -1 --turn-timeout 10`

- 结果（10 agents × 1 turn）：
  - 初始化：`init_time ≈ 14.41 s`
  - 回合：`turn_time ≈ 125.20 s`
  - LLM 统计：
    - `total_requests=29`，`successful=28`，`avg_response_time≈4.98 s`
    - 模板使用：`resolve_action=10`、`agent_decide_goal=8`、`agent_generate_name=7`、`trinity_* 合计=3`、`initial_rules=1`

- 诊断（瓶颈归因）：
  - 行动解析串行：`World.ActionHandler.resolve()` 使用了 `asyncio.Lock` 对“行动解析（resolve_action）”做全局串行，导致 10 次解析近似串行执行（≈ 10 × 5s ≈ 50s），显著抬高回合时间。
  - 冗余调用路径：每个 agent 通常触发两次昂贵调用（`agent_action` 生成自然语句 + `resolve_action` 解析为 JSON 结果）。
  - 会话复用不足：`resolve()` 内为每次解析新建 `aiohttp.ClientSession`，缺少共享会话复用，造成额外握手/连接开销。
  - 其余：Trinity 每回合 ~3 次；名字/目标仅初始化阶段触发（本次 7/8 次）。

- 优先级修复（预计收益）
  - P0 解除串行锁：将 `ActionHandler` 的 `Lock` 改为“有界 Semaphore（如 8）”或移除，允许并行解析；预计对 10 agents 回合减少 30–50s+（按请求平均 5s 估计）。
  - P0 复用会话：`resolve()` 改为复用 `World.step()` 的 `ClientSession`（由 step 注入到 `ActionHandler`），避免每次重建会话；通常可减少 5–15% 调用开销。
  - P1 合并生成与解析：让 `agent_action` 直接输出结构化 JSON（含 position/inventory/log 等），能解析时跳过 `resolve_action`；保留 `_try_dispatch` 与 fallback；有望减少每 agent 1 次昂贵调用。
  - P1 轻量缓存：
    - 对 `resolve_action` 增加基于 `(action, bible_hash, agent_state_hash)` 的短期缓存；
    - 对 `agent_generate_name/goal` 做一次性缓存（当前已基本一次性）。
  - P2 降频 Trinity：将 `trinity_analyze_behaviors/execute_actions` 改为每 N 回合执行（如 N=3–5），降低后台管理调用频次。

- 最小改动清单（不破坏外部接口）：
  - `world.py`：
    - 在 `World.step()` 创建 `ActionHandler` 后注入当前 `session`（如 `action_handler.session = session`）。
    - 将 `ActionHandler.__init__` 中的 `Lock` 改为 `asyncio.Semaphore(k)`（或移除），`resolve()` 使用该信号量；用注入的 `session` 进行 LLM 调用。
  - `enhanced_llm.py`：
    - 支持 `agent_action` 返回 JSON 时直接作为 outcome；否则回退到 `resolve_action`。
  - 可选：在 `EnhancedLLMService.generate` 增加简单内存缓存（模板名+参数哈希）。

- 后续验证：
  - 复跑在线基准（10×1），期待回合时长显著下降；
  - 扩大到 `20×1`、`50×1`，检查平均与 P95；
  - 将结果补入本文档以指导下一轮参数与架构调整。
