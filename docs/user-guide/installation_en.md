# Installation Guide

## System Requirements

### Basic Requirements
- **Python**: 3.10 or higher
- **uv**: Modern Python package manager
- **Memory**: At least 4GB RAM (8GB+ recommended)
- **Storage**: At least 1GB available space
- **Network**: Stable internet connection (for LLM API calls)

### API Support
- **DeepSeek API**: Primary inference engine
- Other OpenAI-compatible API services

## Quick Installation

### 1. Clone the Project
```bash
git clone https://github.com/your-repo/project-genesis.git
cd project-genesis
```

### 2. Install uv (if not already installed)
```bash
# Install uv via pip
pip install uv

# Or use curl (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or use brew (macOS)
brew install uv
```

### 3. Install Dependencies
```bash
# uv automatically creates virtual environment and installs dependencies
uv sync

# Or manually create virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# Or on Windows
.venv\Scripts\activate

# Then install dependencies
uv pip install -e .
```

### 4. Configure API Keys
```bash
# Method 1: Environment variables
export DEEPSEEK_API_KEY="your-api-key-here"

# Method 2: Configuration file
cp .env.example .env
# Edit .env file to add your API keys
```

## Verify Installation

### Run Tests
```bash
# Basic functionality tests
uv run python -m pytest tests/

# Simple simulation test
uv run python -m sociology_simulation.main \
    runtime.turns=5 \
    world.num_agents=3
```

### Check Dependencies
```bash
# Verify all dependencies are correctly installed
uv run python -c "
import sociology_simulation
print('✓ Main module imported successfully')

from sociology_simulation.agent import Agent
from sociology_simulation.world import World
from sociology_simulation.trinity import Trinity
print('✓ Core components imported successfully')

import aiohttp, loguru, hydra
print('✓ Third-party dependencies imported successfully')
"

# Or check project information
uv tree  # View dependency tree
uv pip list  # View installed packages
```

## Common Issues

### API Key Issues
**Problem**: Getting "API key not found" error
**Solution**: 
1. Confirm the correct environment variable name is set
2. Check that API key format is correct
3. Verify API key is valid and has sufficient quota

### Dependency Conflicts
**Problem**: Conflicts during dependency installation
**Solution**:
```bash
# Clear cache and reinstall
uv cache clean
uv sync --refresh

# Or recreate virtual environment
rm -rf .venv
uv venv
uv sync
```

### Memory Issues
**Problem**: Out of memory during large simulations
**Solution**:
1. Reduce agent count: `world.num_agents=10`
2. Reduce map size: `world.size=32`
3. Enable batch processing: `runtime.batch_size=5`

## Advanced Installation Options

### Docker Installation
```bash
# Build image
docker build -t project-genesis .

# Run container
docker run -e DEEPSEEK_API_KEY=your-key project-genesis
```

### Development Environment Setup
```bash
# Install development dependencies (if dev group exists)
uv sync --group dev

# Or add development tools
uv add --dev black flake8 mypy pytest

# Install pre-commit hooks
uv run pre-commit install
```

### Performance Optimization
```bash
# Install performance enhancement packages
uv add uvloop  # Linux/Mac async optimization
uv add psutil  # System monitoring

# numpy is already defined in pyproject.toml
```

## Next Steps

After installation, we recommend reading:
1. [Configuration Guide](configuration.md) - Learn how to customize simulation parameters
2. [Running Simulations](running-simulations.md) - Learn how to run your first simulation
3. [Basic Examples](../examples/basic-simulation.md) - View practical use cases