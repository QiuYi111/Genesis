# Project Genesis v2

A revolutionary LLM-driven sociology simulation engine that creates emergent social complexity from simple agent behaviors.

## Overview

Project Genesis v2 is built from scratch as a sophisticated simulation system where intelligent agents make decisions using Large Language Models. The system features:

- **LLM-Native Design**: Every agent decision powered by language models
- **Advanced Memory System**: Context-aware memory with semantic retrieval
- **Dynamic Decision Making**: Function-call based interactions
- **Emergent Social Structures**: Complex behaviors arising from simple rules

## Quick Start

### Installation

```bash
# Install dependencies
uv sync

# Run basic simulation
uv run python -m sociology_simulation.main llm.provider=mock runtime.max_turns=10

# Run with DeepSeek
export DEEPSEEK_API_KEY="your-key"
uv run python -m sociology_simulation.main llm.provider=deepseek

# Run with OpenAI
export OPENAI_API_KEY="your-key"
uv run python -m sociology_simulation.main llm.provider=openai
```

### Configuration

Configuration is handled via Hydra in `sociology_simulation/conf/config.yaml`:

```yaml
simulation:
  era_prompt: "stone age tribes"
  seed: 42

world:
  width: 64
  height: 64

agents:
  count: 10

llm:
  provider: "mock"  # or "deepseek", "openai"
  model: "gpt-3.5-turbo"
```

## Architecture

### Core Components

- **World Engine**: 64×64 cellular world with realistic terrain and resources
- **Agent System**: Intelligent agents with attributes, inventory, memory, and goals
- **LLM Integration**: Multi-provider support with function calls
- **Memory System**: Semantic memory with context-aware retrieval
- **Decision Engine**: LLM-powered decision making

### Directory Structure

```
sociology_simulation/
├── core/
│   ├── world.py          # World simulation engine
│   └── simulation.py     # Main simulation loop
├── agents/
│   ├── base.py          # Agent base class
│   ├── memory.py        # Advanced memory system
│   └── decision_engine.py # LLM decision making
├── llm/
│   └── providers/       # LLM provider implementations
├── trinity/            # Trinity system (Phase 3)
├── world/              # World systems
├── social/             # Social systems
└── main.py            # Entry point
```

## Features

### Agent Capabilities
- **Physical Attributes**: Health, strength, intelligence, charisma
- **Inventory System**: Weight-limited item management
- **Memory System**: Context-aware memory with semantic search
- **Social Relationships**: Dynamic relationship tracking
- **Goal-Oriented**: Life goals and adaptive planning

### LLM Integration
- **Function Calls**: Native function calling for all interactions
- **Multi-Provider**: DeepSeek, OpenAI, and mock providers
- **Structured Responses**: Pydantic models for type safety
- **Context Management**: Memory-aware decision making

### World System
- **Realistic Terrain**: Perlin noise-based landscapes
- **Dynamic Resources**: Food, water, wood, stone, metal
- **Climate System**: Temperature and humidity affecting behavior
- **Building System**: Persistent structures and infrastructure

## Usage Examples

### Basic Simulation
```python
from sociology_simulation.core.simulation import Simulation
from omegaconf import OmegaConf

config = OmegaConf.create({
    "simulation": {
        "era_prompt": "stone age tribes",
        "seed": 42
    },
    "world": {"width": 32, "height": 32},
    "agents": {"count": 5},
    "llm": {"provider": "mock"},
    "runtime": {"max_turns": 50}
})

sim = Simulation(config)
asyncio.run(sim.run())
```

### Custom Configuration
```bash
# Run with custom parameters
uv run python -m sociology_simulation.main \
    simulation.era_prompt="bronze age civilization" \
    world.width=128 \
    world.height=128 \
    agents.count=20 \
    llm.provider=deepseek \
    runtime.max_turns=100
```

## Development

### Setup Development Environment
```bash
uv sync --dev
uv run pytest tests/
uv run black .
uv run mypy .
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_agents.py

# Run with coverage
uv run pytest --cov=sociology_simulation tests/
```

## Environment Variables

```bash
# LLM API Keys
export DEEPSEEK_API_KEY="your-deepseek-key"
export OPENAI_API_KEY="your-openai-key"

# Optional configuration
export GENESIS_LOG_LEVEL="DEBUG"
export GENESIS_OUTPUT_DIR="./outputs"
```

## License

MIT License - See LICENSE file for details

## Roadmap

- **Phase 3**: Trinity System with behavior observation and skill generation
- **Phase 4**: Social complexity with governance and economic systems
- **Phase 5**: Production optimization and web interface