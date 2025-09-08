# Project Genesis — 三人工程团队重写实施计划书（依据目标/架构与 refactor 规范）

本计划书整合仓库既定目标、架构约束与 `refactor/` 内的契约与交付清单，面向三人工程团队（Core、Trinity/LLM、Platform）给出可并行推进的实施方案、接口契约、里程碑与验收标准。默认以离线可复现的 MVP 为首要交付，逐步替换旧入口脚本与耦合代码，保留必要的向后兼容层以控制回归风险。

—

## 1. 目标与范围（MVP）
- 可复现、可测试、可维护：核心循环纯净（无网络/IO），LLM 通过 Provider 策略解耦；默认 NullProvider 离线确定性。
- 最小世界：32×32、10 agents、30 turns、可配置种子；基础行动：move/forage/craft/trade；基础资源再生与指标。
- Web 观测：WebSocket 广播与 JSON 导出（最小 Schema）；Hydra 配置可覆盖关键参数。
- 成功标准：
  - `uv run python -m sociology_simulation.main world.num_agents=10 runtime.turns=30 model.provider=null` 正常运行；
  - `uv run pytest -q` 全绿；`uv run ruff check . && uv run black --check .` 通过；
  - 文档（README/technical/architecture.md）与行为一致，新人 <15 分钟拉起环境与演示。

不在范围（MVP）：大规模社会系统新增（政治/文化/经济深水区）、大规模性能优化与分布式；可在 Post‑MVP 路线完成。

—

## 2. 目标架构与目录（内向依赖，无环）
- 分层：`UI/Web → Services → Trinity → Core`；Core 不访问网络；Trinity 仅依赖 `LLMProvider` 抽象。
- 建议目录（与 refactor/REFACTORING_DELIVERY_PLAN.md 一致）：
```
sociology_simulation/
  core/              # Agent, World, Actions, Events（纯域层）
  trinity/           # Trinity 引擎与 Planner（Null/LLM）
  services/          # LLM Provider（Null/DeepSeek/OpenAI）、WebSocket、日志
  persistence/       # Exporter/Snapshot（可选）
  conf/              # Hydra 配置
  cli/               # CLI 装配与演示入口
  main.py            # 组合式 orchestrator（保持模块入口）
web_ui/              # 静态前端
docs/                # 架构与 API 文档（已存在）
```

原则：
- Core 侧行为以“事件→统一结算”为准则；Agent 决策纯函数；World 提供 `snapshot()` 给 Web/Exporter。
- Trinity 通过 Planner 策略（Null/LLM）产出 `TrinityActions`（如再生倍率、地形调整、技能更新）。
- Services 封装 LLM 细节，统一 `generate(messages, cfg)` 入口；提供 NullProvider 作默认实现。

—

## 3. 关键接口契约（参考 refactor/REFACTOR_PLAN.md 第 4 章）
- Core
  - `World.step(turn:int, *, trinity:Trinity) -> TurnResult`
  - `Agent.decide(ctx:DecisionContext) -> Action`（纯函数，无 IO/网络）
  - `Agent.act(action, world_view) -> list[BehaviorEvent]`（仅产出事件，副作用统一结算）
  - `World.snapshot() -> dict`（供导出/广播）
- Trinity
  - `Trinity.observe(events: list[dict]) -> None`
  - `Trinity.adjust(world: World) -> TrinityActions`
- Services（LLM Provider）
  - `LLMProvider.generate(messages: list[Msg], cfg: ModelCfg) -> str`
  - 默认 `NullProvider` 返回确定性占位结果（便于测试）

—

## 4. 三人角色与职责划分
- 工程师 A（Core Lead）
  - 负责 `core/` 域层：World/Agent/Action/Event、Tick 循环、资源与指标、事件结算、`snapshot()`。
  - 与 B 定义 `TrinityActions` 对 World 的影响点；与 C 定义快照最小 JSON Schema。
- 工程师 B（Trinity/LLM Lead）
  - 负责 `trinity/`：`observe/adjust` 契约、NullPlanner、LLMPlanner；
  - 负责 `services/llm/`：`LLMProvider` 抽象、`NullProvider`、DeepSeek/OpenAI 适配；统一 `generate()` 入口与超时/重试策略。
- 工程师 C（Platform Lead：CLI/Config/Web/QA）
  - 负责 `cli/` 装配、Hydra 配置组（runtime/world/model/logging）、WebSocket 监控与导出器；
  - 负责测试框架与覆盖率门槛、基本 CI 本地脚本（如无 CI 亦需保证命令可跑）。

—

## 5. 里程碑与时间线（2–3 周，可并行压缩）
里程碑 0（当日）：对齐契约与计划
- 输出：本计划书确认；以 `refactor/REFACTOR_PLAN.md` 的接口为基线，不破坏契约。

里程碑 1（第 1 周）：抽象与去耦（MVP 可运行雏形）
- A（Core）
  - 引入 `WorldView` 与事件统一结算；实现行动 move/forage/craft/trade；基础资源再生与指标；`snapshot()` 最小实现。
  - 以 NullProvider 跑通 10 回合冒烟（无网络）。
- B（Trinity/LLM）
  - 定义 `TrinityActions`，实现 `NullPlanner`；`observe/adjust` 通路打通；
  - `services/llm` 建立 `LLMProvider` 与 `NullProvider`。
- C（Platform）
  - 建立 Hydra 组：`runtime.yaml`, `world.yaml`, `model/{null,deepseek,openai}.yaml`, `logging.yaml`；
  - `cli/main.py` 装配运行：`model.provider=null` 可跑 10 回合；Web 导出器文件落盘一帧。

里程碑 2（第 2 周）：统一 LLM 通道与 Web 观测
- A：补齐 `compute_resource_status()`、完善 `snapshot()` 字段；30 回合稳定运行。
- B：接入真实 Provider（DeepSeek/OpenAI），通过 Hydra 可切换；封装重试/超时；保持 Null 为默认。
- C：WebSocket 监控（随机可用端口以便测试）；前端最小联调（地图/Agent/日志）。

里程碑 3（第 3 周）：测试与稳定化、文档与演示
- A：边界用例（无 Agent/资源极端/满载）；
- B：LLMPlanner 健壮性与回退路径（异常走 Null）；
- C：测试覆盖率 ≥80%（变更行），README/指南更新；演示脚本固化。

—

## 6. 任务分解（可并行 Backlog）
Core（A）
- 数据类型：`Position/Inventory/Action/TurnResult`；
- 行为：move、forage、craft（wood+flint→spear）、trade（barter）；
- Tick：perceive→decide（纯）→act（产事件）→World 统一结算；
- 资源：seeded 地形/资源网格、简单再生、多轮指标；
- 观测：`snapshot()` 导出 world/agents/metrics；
- 指标：actions per turn、scarcity ratio 等；

Trinity/LLM（B）
- Telemetry：定义事件 schema；
- Planner：`NullPlanner`（确定性）与 `LLMPlanner`（调用 Provider）；
- Provider：`LLMProvider` 抽象；`NullProvider`、`DeepSeek/OpenAI` 适配（env 读取）；
- 输出：`TrinityActions`（资源再生倍率/技能更新/地形调整）。

Platform（C）
- 配置：Hydra 组与 CLI 覆盖；`uv run python -m sociology_simulation.main ...`；
- Web：WebSocket 广播器，最小 JSON Schema v1（世界尺寸、资源热力、agents 基本状态、日志）；
- 工具：本地脚本 `uv run ruff check . && uv run black . && uv run pytest -q`；
- 文档：README 更新、技术架构对齐、运行演示脚本；

—

## 7. 验收与质量门槛
- 命令验收：
  - 安装：`uv sync`（Python 3.10+ 与 uv）
  - 运行：`uv run python -m sociology_simulation.main world.size=32 world.num_agents=10 runtime.turns=30 model.provider=null`
  - 测试：`uv run pytest -q` 全绿；
  - 规范：`uv run ruff check .` 通过；`uv run black --check .` 通过。
- 覆盖率：变更行 ≥80%。
- 可观测性：WebSocket 或文件导出可读取且字段齐备；日志为结构化 JSON 行。
- 稳定性：无网络时默认 NullProvider 可完整运行；LLM 不可用时自动回退 Null。

—

## 8. 风险与对策
- 行为回归：保留旧入口的薄适配（shim）在内部委派至新通路；新增集成冒烟；灰度切换 Provider。
- LLM 不稳定/超时：默认 NullProvider；在 Provider 层统一超时/重试/失败回退。
- 前后端数据不一致：冻结最小 JSON Schema；变更需经评审与版本号（v1）。
- 并行冲突：接口契约先行；小步合并；每日 15 分钟站会同步边界变更。

—

## 9. 每周节奏与沟通机制
- 每日站会（15 分钟）：接口变更、阻塞点、当日目标；
- 看板列：Backlog / In‑Progress / Review / Done；
- 代码规范：Black/Ruff，公共 API 带类型注解与 docstring；绝对导入 `sociology_simulation.*`；
- PR 准入：说明动机、范围与测试步骤；小而频。

—

## 10. 演示脚本（交付时现场操作）
1) `uv sync`
2) `uv run python -m sociology_simulation.main world.size=32 world.num_agents=10 runtime.turns=30 model.provider=null`
3) （可选）启动 Web 监控 `python -m sociology_simulation.cli.web_demo`，浏览器打开 `http://localhost:8081`
4) `uv run pytest -q`

—

## 11. 与 refactor/ 规范的对应关系
- 接口契约与层次：对齐 `refactor/REFACTOR_PLAN.md` 第 3/4 章；
- 任务与并行拆分：映射 `refactor/REFACTORING_DELIVERY_PLAN.md` 的工作流/Backlog，但收敛为三人角色；
- 成功标准与命令：与根目录 `README.md`、仓库指南保持一致，并以 NullProvider 为默认路径保证可复现性。

— 完 —

