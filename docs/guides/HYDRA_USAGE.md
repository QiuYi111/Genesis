# Hydra Configuration Usage

The sociology simulation now supports Hydra for flexible configuration management. This allows you to easily switch between different simulation parameters, eras, models, and logging configurations.

## Quick Start

```bash
# Basic usage with default configuration (Stone Age, DeepSeek, 10 turns, 20 agents)
python -m sociology_simulation.main

# Override specific parameters
python -m sociology_simulation.main runtime.turns=5 world.num_agents=10

# Use Bronze Age configuration
python -m sociology_simulation.main simulation=bronze_age

# Use OpenAI instead of DeepSeek
python -m sociology_simulation.main model=openai

# Enable debug logging
python -m sociology_simulation.main logging=debug

# Show conversations
python -m sociology_simulation.main runtime.show_conversations=true
```

## Configuration Files

### Available Simulation Eras
- `simulation=stone_age` (default) - Stone Age with basic resources
- `simulation=bronze_age` - Bronze Age with metal working

### Available Models  
- `model=deepseek` (default) - Uses DeepSeek API
- `model=openai` - Uses OpenAI GPT models

### Available Logging Levels
- `logging=default` (default) - INFO level logging
- `logging=debug` - DEBUG level with detailed logs

## Configuration Structure

```
sociology_simulation/conf/
├── config.yaml              # Main configuration
├── simulation/
│   ├── stone_age.yaml       # Stone Age parameters
│   └── bronze_age.yaml      # Bronze Age parameters
├── model/
│   ├── deepseek.yaml        # DeepSeek API configuration
│   └── openai.yaml          # OpenAI API configuration
└── logging/
    ├── default.yaml         # Standard logging
    └── debug.yaml           # Debug logging
```

## Parameter Override Examples

```bash
# Change world size
python -m sociology_simulation.main world.size=32

# Run longer simulation with more agents
python -m sociology_simulation.main runtime.turns=50 world.num_agents=100

# Disable map display
python -m sociology_simulation.main runtime.show_map_every=0

# Custom era prompt
python -m sociology_simulation.main simulation.era_prompt="未来科幻时代"

# Adjust survival mechanics
python -m sociology_simulation.main simulation.survival.hunger_increase_per_turn=5
```

## Environment Variables

Set your API key before running:

```bash
# For DeepSeek
export DEEPSEEK_API_KEY="your-api-key"

# For OpenAI  
export OPENAI_API_KEY="your-api-key"
```

## Advanced Usage

### Create Custom Configurations

You can create new configuration files in the appropriate directories:

1. **Custom Era**: Create `sociology_simulation/conf/simulation/my_era.yaml`
2. **Custom Model**: Create `sociology_simulation/conf/model/my_model.yaml`
3. **Custom Logging**: Create `sociology_simulation/conf/logging/my_logging.yaml`

### Config Composition

Combine multiple configurations:

```bash
python -m sociology_simulation.main simulation=bronze_age model=openai logging=debug runtime.turns=20
```

### Output Directory

Hydra automatically creates output directories with timestamps for each run, storing logs and configuration used.

## Configuration Schema

All parameters are validated using dataclasses with type hints, ensuring configuration correctness at startup.