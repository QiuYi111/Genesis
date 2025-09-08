# 安装指南

## 系统要求

### 基础要求
- **Python**: 3.10 或更高版本
- **uv**: 现代 Python 包管理器
- **内存**: 至少 4GB RAM（推荐 8GB+）
- **存储**: 至少 1GB 可用空间
- **网络**: 稳定的互联网连接（用于 LLM API 调用）

### API 支持
- **DeepSeek API**: 主要推理引擎
- 其他兼容 OpenAI 格式的 API 服务

## 快速安装

### 1. 克隆项目
```bash
git clone https://github.com/your-repo/project-genesis.git
cd project-genesis
```

### 2. 安装 uv（如果未安装）
```bash
# 使用 pip 安装 uv
pip install uv

# 或使用 curl（推荐）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 brew（macOS）
brew install uv
```

### 3. 安装依赖
```bash
# uv 会自动创建虚拟环境并安装依赖
uv sync

# 或者手动创建虚拟环境
uv venv
source .venv/bin/activate  # Linux/Mac
# 或在 Windows 上
.venv\Scripts\activate

# 然后安装依赖
uv pip install -e .
```

### 4. 配置 API 密钥
```bash
# 方法1：环境变量
export DEEPSEEK_API_KEY="your-api-key-here"

# 方法2：配置文件
cp .env.example .env
# 编辑 .env 文件，添加你的 API 密钥
```

## 验证安装

### 运行测试
```bash
# 基础功能测试
uv run python -m pytest tests/

# 简单模拟测试
uv run python -m sociology_simulation.main \
    runtime.turns=5 \
    world.num_agents=3
```

### 检查依赖
```bash
# 验证所有依赖都已正确安装
uv run python -c "
import sociology_simulation
print('✓ 主模块导入成功')

from sociology_simulation.agent import Agent
from sociology_simulation.world import World
from sociology_simulation.trinity import Trinity
print('✓ 核心组件导入成功')

import aiohttp, loguru, hydra
print('✓ 第三方依赖导入成功')
"

# 或者检查项目信息
uv tree  # 查看依赖树
uv pip list  # 查看已安装包
```
```

## 常见问题

### API 密钥问题
**问题**: 获取 "API key not found" 错误
**解决**: 
1. 确认已设置正确的环境变量名称
2. 检查 API 密钥格式是否正确
3. 验证 API 密钥是否有效且有足够配额

### 依赖冲突
**问题**: 依赖安装时出现冲突
**解决**:
```bash
# 清理缓存重新安装
uv cache clean
uv sync --refresh

# 或者重新创建虚拟环境
rm -rf .venv
uv venv
uv sync
```

### 内存不足
**问题**: 大规模模拟时内存不足
**解决**:
1. 减少智能体数量：`world.num_agents=10`
2. 减少地图大小：`world.size=32`
3. 启用批处理模式：`runtime.batch_size=5`

## 高级安装选项

### Docker 安装
```bash
# 构建镜像
docker build -t project-genesis .

# 运行容器
docker run -e DEEPSEEK_API_KEY=your-key project-genesis
```

### 开发环境配置
```bash
# 安装开发依赖（如果有 dev 组）
uv sync --group dev

# 或者添加开发工具
uv add --dev black flake8 mypy pytest

# 安装预提交钩子
uv run pre-commit install
```

### 性能优化
```bash
# 安装性能增强包
uv add uvloop  # Linux/Mac 异步优化
uv add psutil  # 系统监控

# numpy 已在 pyproject.toml 中定义
```

## 下一步

安装完成后，建议阅读：
1. [配置说明](configuration.md) - 了解如何自定义模拟参数
2. [运行教程](running-simulations.md) - 学习如何运行你的第一个模拟
3. [基础示例](../examples/basic-simulation.md) - 查看实际使用案例