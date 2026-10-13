# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Genesis is a sociology simulation engine based on large language models that simulates the emergence of complex social structures and cultural phenomena from simple agent behaviors. The system uses a "Trinity" (god system) to dynamically create skills and guide social development.

## Development Commands

### Environment Setup
```bash
# Install dependencies using uv (preferred)
uv sync

# Run the simulation
uv run python -m sociology_simulation.main \
    simulation.era_prompt="石器时代的原始部落" \
    world.num_agents=10 \
    runtime.turns=30

# Run individual test files
uv run python test_trinity_simple.py
uv run python test_food_consumption.py
uv run python test_web_ui.py
```

### Key Configuration
- **API Key**: Set `DEEPSEEK_API_KEY` environment variable before running
- **Python Version**: Requires Python 3.10+ (managed via `.python-version`)
- **Package Manager**: Uses `uv` for dependency management

## Architecture Overview

### Core Components

**Trinity System** (`sociology_simulation/trinity.py`)
- Omniscient adjudicator that controls skill creation and world rules
- Generates terrain, resource rules, and unlocks skills based on era context
- Key method: `_calculate_resource_status()` for resource management logic

**Agent System** (`sociology_simulation/agent.py`)
- Intelligent agents with dynamic skills, social connections, and memory
- Attributes: position, inventory, skills, experience, social connections
- Core behaviors: movement, interaction, learning, adaptation

**World System** (`sociology_simulation/world.py`)
- 64x64 dynamic terrain with resource management
- Agent management and interaction orchestration
- Event handling and state persistence

**Configuration System** (`sociology_simulation/config.py`)
- Hydra-based configuration management
- Structured configs for model, simulation, world, runtime, perception, logging
- Global config access via `get_config()` and `set_config()`

### Key Subsystems

**Enhanced LLM** (`sociology_simulation/enhanced_llm.py`)
- Centralized LLM service with retry logic and error handling
- Supports both DeepSeek and OpenAI APIs
- Key methods: `trinity_generate_rules()`, `generate_agent_action()`

**Interaction System** (`sociology_simulation/interaction_system.py`)
- Manages agent-to-agent interactions and social dynamics
- Handles trade, cooperation, conflict resolution

**Cultural Memory** (`sociology_simulation/cultural_memory.py`)
- Knowledge accumulation and tradition formation
- Skill inheritance and cultural transmission

**Technology System** (`sociology_simulation/technology_system.py`)
- Dynamic technology discovery and advancement
- Technology trees and prerequisites

### Web Interface
- **Main UI**: `sociology_simulation_web_ui.html` - Interactive web interface
- **Export System**: `sociology_simulation/web_export.py` - Real-time data export for web UI
- **Monitor**: `sociology_simulation/web_monitor.py` - WebSocket-based monitoring

## Important Implementation Details

### Error Handling Pattern
The codebase uses extensive try-catch blocks with detailed logging via `loguru`. Key pattern:
```python
try:
    # operation
except Exception as e:
    logger.error(f"[Component] Error in operation: {e}")
    # fallback or re-raise
```

### Async Operations
Most LLM interactions are async using `aiohttp`. Ensure proper async/await usage when calling:
- `llm_service.generate_agent_action()`
- `llm_service.trinity_generate_rules()`
- Any web export or monitoring functions

### Resource Management
Resource calculations use terrain-based multipliers defined in `DEFAULT_RESOURCE_RULES`. The system tracks resource abundance/scarcity to drive agent behavior and Trinity interventions.

### Testing Approach
- Unit tests focus on core logic without external API dependencies
- Mock objects used for World and LLM services in tests
- Test files follow `test_*.py` naming convention in root directory

### Logging Strategy
- Use `loguru` for all logging with component prefixes: `[Component] message`
- Different log levels for different simulation aspects
- File logging configured via Hydra config with rotation and retention

## Common Development Tasks

### Adding New Skills
1. Define skill in Trinity's `available_skills` dictionary
2. Set unlock conditions in `skill_unlock_conditions`
3. Update agent skill processing in `agent.py`

### Modifying Agent Behavior
1. Update `Agent` dataclass in `agent.py` if adding attributes
2. Modify `decide_action()` method for decision logic
3. Update interaction handlers in `interaction_system.py`

### Creating New Simulation Scenarios
1. Update era prompts in configuration files
2. Modify terrain generation in `terrain_generator.py`
3. Adjust resource rules in Trinity system

### Debugging Simulation Issues
1. Check logs in `logs/` directory with appropriate log level
2. Use `test_trinity_simple.py` for isolated Trinity testing
3. Monitor web interface for real-time simulation state