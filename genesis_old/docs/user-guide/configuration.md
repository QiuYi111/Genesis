# 配置说明

## 配置系统概述

Project Genesis 使用 [Hydra](https://hydra.cc/) 作为配置管理系统，提供灵活的参数配置和覆盖机制。所有配置文件位于 `sociology_simulation/conf/` 目录下。

## 配置文件结构

```
conf/
├── config.yaml          # 主配置文件
├── prompts.yaml         # 提示词配置
├── model/
│   ├── deepseek.yaml    # DeepSeek 模型配置
│   └── openai.yaml      # OpenAI 模型配置
├── simulation/
│   ├── stone_age.yaml   # 石器时代配置
│   ├── bronze_age.yaml  # 青铜时代配置
│   └── medieval.yaml    # 中世纪配置
└── world/
    ├── small.yaml       # 小世界配置
    ├── medium.yaml      # 中等世界配置
    └── large.yaml       # 大世界配置
```

## 主配置文件 (config.yaml)

### 完整配置示例

```yaml
defaults:
  - model: deepseek
  - simulation: stone_age
  - world: medium
  - _self_

# 模型配置
model:
  base_url: "https://api.deepseek.com/chat/completions"
  agent_model: "deepseek-chat"
  api_key_env: "DEEPSEEK_API_KEY"
  timeout: 30
  max_retries: 3

# 模拟配置
simulation:
  era_prompt: "石器时代的原始部落，刚刚学会使用简单的石制工具"
  
# 世界配置
world:
  size: 64
  num_agents: 15

# 运行时配置
runtime:
  turns: 50
  show_map_every: 10
  show_conversations: true
  batch_processing: false
  timeout_per_agent: 15.0

# 感知配置
perception:
  vision_radius: 3
  interaction_radius: 2
  memory_depth: 10

# 日志配置
logging:
  level: "INFO"
  format: "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
  console:
    enabled: true
    level: "INFO"
    format: "{time:HH:mm:ss} | {level: <8} | {message}"
  file:
    enabled: true
    path: "logs/sociology_simulation_{time:YYYY-MM-DD_HH-mm-ss}_{extra}.log"
    rotation: "100 MB"
    retention: "7 days"
    compression: "zip"

# 输出配置
output:
  save_state: true
  export_web_data: true
  export_interval: 5
  output_dir: "outputs"

# Trinity 配置
trinity:
  skill_creation_threshold: 0.7
  natural_event_frequency: 0.1
  intervention_threshold: 0.5
  max_skills_per_turn: 3
  era_advancement_threshold: 100

# 智能体配置
agents:
  learning_rate: 0.3
  social_connection_threshold: 5
  reputation_decay: 0.95
  skill_transfer_rate: 0.2

# 经济配置
economy:
  enable_markets: true
  price_volatility: 0.1
  trade_frequency: 0.3
  specialization_bonus: 1.5

# 社会配置
social:
  group_formation_threshold: 3
  leadership_threshold: 50
  group_stability_decay: 0.02
  max_group_size: 12
```

## 配置组详解

### 模型配置 (model)

```yaml
# DeepSeek 配置
model:
  base_url: "https://api.deepseek.com/chat/completions"
  agent_model: "deepseek-chat"
  api_key_env: "DEEPSEEK_API_KEY"
  timeout: 30
  max_retries: 3
  temperature: 0.7
  max_tokens: 2048

# OpenAI 配置
model:
  base_url: "https://api.openai.com/v1/chat/completions"
  agent_model: "gpt-4"
  api_key_env: "OPENAI_API_KEY"
  timeout: 60
  max_retries: 5
  temperature: 0.8
  max_tokens: 4096
```

### 模拟场景配置 (simulation)

```yaml
# 石器时代配置
simulation:
  era_prompt: "石器时代的原始部落，刚刚学会使用简单的石制工具"
  initial_technologies: ["fire_making", "stone_knapping"]
  available_resources: ["wood", "stone", "fruit", "water"]
  climate: "temperate"
  difficulty: "normal"

# 青铜时代配置
simulation:
  era_prompt: "青铜时代文明，掌握了金属冶炼技术"
  initial_technologies: ["metallurgy", "agriculture", "writing"]
  available_resources: ["copper", "tin", "grain", "livestock"]
  climate: "mediterranean"
  difficulty: "hard"

# 灾后重建配置
simulation:
  era_prompt: "大灾难后的幸存者，需要重建文明"
  initial_technologies: []
  available_resources: ["scrap_metal", "ruins", "wild_plants"]
  climate: "harsh"
  difficulty: "extreme"
```

### 世界大小配置 (world)

```yaml
# 小世界 (测试用)
world:
  size: 16
  num_agents: 5
  resource_density: 1.5
  terrain_diversity: 0.6

# 中等世界 (标准)
world:
  size: 64
  num_agents: 15
  resource_density: 1.0
  terrain_diversity: 0.8

# 大世界 (长期模拟)
world:
  size: 128
  num_agents: 30
  resource_density: 0.8
  terrain_diversity: 1.0
```

## 命令行覆盖

Hydra 支持通过命令行覆盖任何配置参数：

### 基础覆盖
```bash
# 修改世界大小和智能体数量
python -m sociology_simulation.main \
    world.size=32 \
    world.num_agents=10

# 修改运行回合数
python -m sociology_simulation.main \
    runtime.turns=100

# 启用详细日志
python -m sociology_simulation.main \
    logging.level=DEBUG
```

### 配置组切换
```bash
# 使用不同的模型
python -m sociology_simulation.main \
    model=openai

# 切换到青铜时代场景
python -m sociology_simulation.main \
    simulation=bronze_age

# 使用大世界配置
python -m sociology_simulation.main \
    world=large
```

### 复杂覆盖
```bash
# 自定义时代和参数
python -m sociology_simulation.main \
    simulation.era_prompt="中世纪欧洲，黑死病刚刚结束" \
    world.num_agents=20 \
    trinity.natural_event_frequency=0.2 \
    agents.learning_rate=0.4
```

## 环境变量配置

### API 密钥配置
```bash
# DeepSeek API
export DEEPSEEK_API_KEY="your-deepseek-api-key"

# OpenAI API  
export OPENAI_API_KEY="your-openai-api-key"

# 自定义 API
export CUSTOM_API_KEY="your-custom-api-key"
export CUSTOM_API_URL="https://your-api-endpoint.com"
```

### 系统配置
```bash
# 输出目录
export GENESIS_OUTPUT_DIR="/path/to/outputs"

# 日志级别
export GENESIS_LOG_LEVEL="DEBUG"

# 性能调优
export GENESIS_PARALLEL_AGENTS="true"
export GENESIS_BATCH_SIZE="5"
```

## 性能调优配置

### 高性能配置
```yaml
# 适用于高性能服务器
runtime:
  batch_processing: true
  parallel_agents: true
  timeout_per_agent: 30.0
  max_concurrent_requests: 10

model:
  timeout: 60
  max_retries: 5
  
trinity:
  analysis_interval: 3  # 每3回合分析一次
  cache_decisions: true
```

### 低资源配置
```yaml
# 适用于资源受限环境
world:
  size: 32
  num_agents: 8

runtime:
  batch_processing: false
  timeout_per_agent: 10.0
  max_concurrent_requests: 2

model:
  timeout: 20
  max_retries: 2

trinity:
  analysis_interval: 5  # 减少分析频率
  skill_creation_threshold: 0.8  # 提高创建阈值
```

### 调试配置
```yaml
# 用于开发和调试
logging:
  level: "DEBUG"
  console:
    enabled: true
    level: "DEBUG"

runtime:
  turns: 10
  show_conversations: true
  show_map_every: 1

world:
  num_agents: 3
  
trinity:
  intervention_threshold: 0.3  # 更频繁的干预
  natural_event_frequency: 0.3
```

## 自定义配置

### 创建自定义配置组

1. 创建配置文件：
```bash
mkdir -p conf/custom
```

2. 编写自定义配置：
```yaml
# conf/custom/my_scenario.yaml
simulation:
  era_prompt: "我的自定义场景描述"
  initial_technologies: ["custom_tech1", "custom_tech2"]
  
world:
  size: 48
  num_agents: 12
  
trinity:
  custom_parameter: "custom_value"
```

3. 使用自定义配置：
```bash
uv run python -m sociology_simulation.main \
    +custom=my_scenario
```

### 配置验证

创建配置验证器：
```python
# conf/schema.py
from omegaconf import DictConfig
from hydra.core.config_store import ConfigStore

@dataclass
class ModelConfig:
    base_url: str
    agent_model: str
    api_key_env: str
    timeout: int = 30

@dataclass
class Config:
    model: ModelConfig
    # ... 其他配置类

cs = ConfigStore.instance()
cs.store(name="config_schema", node=Config)
```

## 配置最佳实践

### 1. 环境分离
```yaml
# 开发环境
defaults:
  - model: deepseek
  - simulation: stone_age
  - world: small

# 生产环境  
defaults:
  - model: openai
  - simulation: bronze_age
  - world: large
```

### 2. 参数化配置
```yaml
# 使用变量引用
world:
  size: ${world_size:64}
  num_agents: ${num_agents:15}
  
runtime:
  turns: ${simulation_length:50}
```

### 3. 条件配置
```yaml
# 基于环境的条件配置
defaults:
  - model: deepseek
  - simulation: stone_age
  - world: ${oc.env:WORLD_SIZE,medium}
  - override hydra/launcher: ${oc.env:LAUNCHER,basic}
```

### 4. 配置继承
```yaml
# base_config.yaml
defaults:
  - _self_
  
base_params:
  timeout: 30
  retries: 3

# specialized_config.yaml  
defaults:
  - base_config
  
base_params:
  timeout: 60  # 覆盖基础配置
```

通过合理使用这些配置选项，你可以为不同的实验场景、性能要求和开发环境定制最适合的设置。