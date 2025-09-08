# Project Genesis 文档中心

欢迎来到 Project Genesis 的文档中心！这里包含了使用、开发和扩展社会学模拟引擎所需的所有信息。

## 📚 文档导航

### 🚀 用户指南

开始使用 Project Genesis 的必备文档

- **[安装指南](/docs/user-guide/installation.md)** - 系统要求、安装步骤、环境配置
- **[配置说明](user-guide/configuration.md)** - 详细的配置选项和参数调优
- **[运行教程](user-guide/running-simulations.md)** - 如何运行和监控模拟

### 🔧 技术文档

深入了解系统架构和核心技术

- **[系统架构](technical/architecture.md)** - 整体架构设计和组件关系
- **[智能体系统](technical/agent-system.md)** - Agent 设计和行为机制
- **[Trinity 系统](technical/trinity-system.md)** - 神系统的设计和实现
- **[技能系统](technical/skill-system.md)** - 动态技能创建和管理
 - 运行时快照 Schema：见 [Runtime Snapshot v1](snapshot_v1.md)
 - WebSocket 监控：见 [WebSocket Monitor](websocket_monitor.md)

### 💡 示例教程

实践案例和使用示例

- **[基础模拟](examples/basic-simulation.md)** - 第一个石器时代模拟
- **[高级场景](examples/advanced-scenarios.md)** - 复杂社会模拟案例
- **[自定义时代](examples/custom-eras.md)** - 创建自定义时代和场景

### 📖 API 参考

完整的 API 文档和接口说明

- **[Agent API](api/agent-api.md)** - 智能体接口文档（新增契约与伪代码）
- **[World API](api/world-api.md)** - 世界系统接口（新增契约与伪代码）
- **[Trinity API](api/trinity-api.md)** - Trinity 系统接口

### 🧩 并行开发

- **[模块契约与并行开发指引](technical/module-contracts.md)** - 稳定接口、伪代码与装配示例

## 🎯 快速导航

### 🆕 新用户起步

1. 阅读 [安装指南](user-guide/installation.md) 设置环境
2. 查看 [基础模拟](examples/basic-simulation.md) 运行第一个示例
3. 学习 [配置说明](user-guide/configuration.md) 自定义参数

### 🔬 研究人员

1. 了解 [系统架构](technical/architecture.md) 掌握整体设计
2. 研究 [Trinity 系统](technical/trinity-system.md) 理解核心机制
3. 探索 [高级场景](examples/advanced-scenarios.md) 进行深入实验

### 💻 开发者

1. 查看 [技术文档](technical/) 了解实现细节
2. 参考 [API 文档](api/) 进行功能扩展
3. 学习 [自定义时代](examples/custom-eras.md) 创建新模块

## 🔥 核心特性

### 🧠 智能涌现系统

- **动态技能创建** - Trinity 根据智能体行为创建新技能
- **社会结构自生成** - 群体、市场、政府的自然形成
- **文化演化** - 知识传承和社会规范的自然发展

### 🌍 复杂环境系统

- **动态地理** - 地形、资源、气候的实时变化
- **自然事件** - 灾害和环境变化驱动社会发展
- **生态平衡** - 资源与人口的动态平衡

### 🤝 多层次交互

- **个体智能** - 复杂的认知和学习机制
- **社会网络** - 多维度的关系和影响力系统
- **集体行为** - 群体决策和协作机制

## 📊 系统组件概览

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

## 🛠️ 技术栈（本仓 MVP）

- Python 3.10+
- uv（依赖与运行）
- websockets（可选，未安装时 Monitor 自动降级）
- pytest / ruff / black（开发工具）

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

## 📞 获取帮助

### 🆘 常见问题

- 查看各文档的"常见问题"部分
- 搜索 [Issues](https://github.com/your-repo/project-genesis/issues)

### 💬 社区支持

- [GitHub Discussions](https://github.com/your-repo/project-genesis/discussions)
- [社区论坛](https://community.project-genesis.org)

### 🐛 问题报告

- [提交 Bug 报告](https://github.com/your-repo/project-genesis/issues/new)
- [功能请求](https://github.com/your-repo/project-genesis/issues/new)

### 📧 联系我们

- 项目主页: [Project Genesis](https://github.com/your-repo/project-genesis)
- 文档反馈: [documentation@project-genesis.org](mailto:documentation@project-genesis.org)

## 🔄 文档更新

本文档随项目持续更新。主要版本发布时会同步更新所有相关文档。

**最后更新**: 2025-09
**文档版本**: v0.2（W2）
**对应代码版本**: main（W2 完成）

---

**开始探索 Project Genesis，从解释社会到预测未来！** 🚀
