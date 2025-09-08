# Project Genesis - 社会学模拟引擎

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![uv](https://img.shields.io/badge/uv-managed-blueviolet)](https://github.com/astral-sh/uv)

欢迎来到 Project Genesis！这是一个基于大语言模型的社会学模拟引擎，能够从简单的智能体行为中涌现出复杂的社会结构和文化现象。

## 🚀 快速开始

### 安装和运行

```bash
# 克隆项目
git clone https://github.com/your-repo/project-genesis.git
cd project-genesis

# 安装依赖 (需要先安装 uv)
uv sync

# 配置 API 密钥
export DEEPSEEK_API_KEY="your-api-key-here"

# 运行第一个模拟
uv run python -m sociology_simulation.main \
    simulation.era_prompt="stone age with magic" \
    world.num_agents=10 \
    runtime.turns=30
```

### 运行 Web Demo（简易可视化）

```bash
uv run python run_simple_web_simulation.py
# 打开浏览器访问
# http://localhost:8081
```

> 提示：该入口会启动一个简易 HTTP + WebSocket 服务，用于实时查看地图与智能体状态。

### 核心特性预览

**智能涌现系统**

- 🧠 动态技能创建 - Trinity 根据智能体行为创建新技能
- 🏛️ 社会结构自生成 - 群体、市场、政府的自然形成
- 📚 文化演化 - 知识传承和社会规范的自然发展

**复杂环境系统**

- 🌍 动态地理 - 地形、资源、气候的实时变化
- ⚡ 自然事件 - 灾害和环境变化驱动社会发展
- 🔄 生态平衡 - 资源与人口的动态平衡

## 📚 文档导航

### 🆕 新用户起步

1. **[安装指南](docs/user-guide/installation.md)** - 系统要求、安装步骤、环境配置
2. **[基础模拟](docs/examples/basic-simulation.md)** - 第一个石器时代模拟
3. **[配置说明](docs/user-guide/configuration.md)** - 详细的配置选项和参数调优

### 🔬 研究人员

1. **[系统架构](docs/technical/architecture.md)** - 整体架构设计和组件关系
2. **[Trinity 系统](docs/technical/trinity-system.md)** - 神系统的设计和实现
3. **[高级场景](docs/examples/advanced-scenarios.md)** - 复杂社会模拟案例

### 💻 开发者

1. **[技术文档](docs/technical/)** - 了解实现细节
2. **[API 文档](docs/api/)** - 进行功能扩展
3. **[自定义时代](docs/examples/custom-eras.md)** - 创建新模块

## 🎯 系统架构

```
Trinity (神系统)
├── 行为观察 - 监控智能体行为模式
├── 技能创建 - 动态创建和分配技能  
├── 事件生成 - 自然灾害和环境变化
└── 时代管理 - 引导社会发展进程

智能体系统
├── 动态技能 - Trinity 控制的技能系统
├── 社交网络 - 复杂的关系和声誉
├── 学习机制 - 知识获取和技能传承
└── 适应行为 - 环境和社会压力响应

社会结构
├── 群体系统 - 家庭、部落、工作团队
├── 文化记忆 - 知识积累和传统形成
├── 经济系统 - 市场、贸易、专业化
└── 政治系统 - 治理结构和权力分配

环境系统
├── 地理系统 - 64x64 动态地形
├── 资源经济 - 供需动态和价格机制
├── 自然事件 - 灾害和环境变化
└── 生态平衡 - 可持续发展机制
```

## 🛠️ 技术栈

- **Python 3.10+** - 核心开发语言
- **uv** - 现代 Python 包管理器
- **aiohttp** - 异步 HTTP 客户端
- **Hydra** - 配置管理系统
- **DeepSeek/OpenAI API** - 大语言模型服务
- **matplotlib** - 数据可视化
- **loguru** - 高级日志系统

## 📁 仓库结构

```
.
├── sociology_simulation/           # 核心代码与 Hydra 配置（conf/）
├── scripts/                        # 可运行脚本与工具
│   ├── run_simple_web_simulation.py
│   ├── run_web_simulation.py
│   ├── run_with_web_export.py
│   └── reorg_repo.sh
├── web_ui/                         # Web UI 静态资源
│   ├── index.html                  # 监控面板主页面（测试依赖此路径）
│   ├── js/simulation-ui.js
│   ├── landing/index.html          # 项目 landing/demo 页面
│   └── experimental/               # 实验性页面
├── web_data/                       # 运行期导出 JSON（已 gitignore）
├── docs/                           # 文档（web-ui/、guides/、engineering/、plans/、agents/）
├── logs/  outputs/                 # 运行产物（已 gitignore）
├── test_*.py                       # 跨模块测试（可选下沉至包内 tests/）
├── pyproject.toml  uv.lock
└── README.md
```

> 说明：保留根级 `run_simple_web_simulation.py` 作为入口桩，内部委托到 `scripts/run_simple_web_simulation.py`，以保持既有使用习惯。

## 🔍 使用场景

### 📈 社会学研究

- 社会网络形成和演化分析
- 文化传播和社会分层研究
- 集体行为和群体动力学

### 🏛️ 人类学应用

- 技术发展和扩散模拟
- 社会组织演化研究
- 文化适应机制分析

### 💼 经济学建模

- 市场自发形成机制
- 分工和专业化发展
- 创新扩散和技术进步

### 🎮 游戏开发

- 动态世界生成
- NPC 行为和社会系统
- 玩家驱动的内容创作

## 📖 完整文档

### 用户指南

- **[安装指南](docs/user-guide/installation.md)** - 系统要求、安装步骤、环境配置
- **[配置说明](docs/user-guide/configuration.md)** - 详细的配置选项和参数调优
- **[运行教程](docs/user-guide/running-simulations.md)** - 如何运行和监控模拟

### 技术文档

- **[系统架构](docs/technical/architecture.md)** - 整体架构设计和组件关系
- **[智能体系统](docs/technical/agent-system.md)** - Agent 设计和行为机制
- **[Trinity 系统](docs/technical/trinity-system.md)** - 神系统的设计和实现
- **[技能系统](docs/technical/skill-system.md)** - 动态技能创建和管理

### 示例教程

- **[基础模拟](docs/examples/basic-simulation.md)** - 第一个石器时代模拟
- **[高级场景](docs/examples/advanced-scenarios.md)** - 复杂社会模拟案例
- **[自定义时代](docs/examples/custom-eras.md)** - 创建自定义时代和场景

### API 参考

- **[Agent API](docs/api/agent-api.md)** - 智能体接口文档
- **[World API](docs/api/world-api.md)** - 世界系统接口
- **[Trinity API](docs/api/trinity-api.md)** - Trinity 系统接口

## 🌟 项目亮点

### 1. 真正的智能涌现

- 不使用预设的社会规则，所有社会现象都从智能体互动中自然涌现
- Trinity 系统动态观察和创建技能，没有硬编码的能力限制

### 2. 多层次复杂性

- 个体认知 → 社会网络 → 群体行为 → 文化演化
- 从石器时代到现代文明的完整发展轨迹

### 3. 灵活的配置系统

- 基于 Hydra 的模块化配置
- 支持命令行覆盖和自定义场景

### 4. 现代化开发体验

- 使用 uv 进行依赖管理
- 异步架构提高性能
- 完整的类型提示和文档

## 🤝 贡献指南

我们欢迎所有形式的贡献！

1. **提交 Bug 报告** - 在 [Issues](https://github.com/your-repo/project-genesis/issues) 中报告问题
2. **功能请求** - 提出新功能建议
3. **代码贡献** - 提交 Pull Request
4. **文档改进** - 帮助完善文档

### 开发环境设置

```bash
# 克隆项目
git clone https://github.com/your-repo/project-genesis.git
cd project-genesis

# 安装开发依赖
uv sync --group dev

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run ruff check .
```

## 📞 获取帮助

### 🆘 常见问题

查看各文档的"常见问题"部分，或搜索 [Issues](https://github.com/your-repo/project-genesis/issues)

### 💬 社区支持

- [GitHub Discussions](https://github.com/your-repo/project-genesis/discussions)
- [社区论坛](https://community.project-genesis.org)

### 🐛 问题报告

- [提交 Bug 报告](https://github.com/your-repo/project-genesis/issues/new)
- [功能请求](https://github.com/your-repo/project-genesis/issues/new)

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 🔄 版本信息

- **当前版本**: v2.0.0
- **最后更新**: 2025年7月
- **Python 版本**: 3.10+
- **文档版本**: v2.0

---

**开始探索 Project Genesis，从解释社会到预测未来！** 🚀

> "社会的复杂性不是设计出来的，而是涌现出来的。" - Project Genesis 设计理念
