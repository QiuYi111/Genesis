#!/usr/bin/env python3
"""
Entry stub that delegates to scripts/run_simple_web_simulation.py
Keeps command: `uv run python run_simple_web_simulation.py` working.
"""
from pathlib import Path
import sys

# Add scripts directory to path and delegate
root = Path(__file__).parent
scripts_dir = root / 'scripts'
sys.path.insert(0, str(scripts_dir))

# Import and run main from the scripts module
import run_simple_web_simulation as _runner

if __name__ == '__main__':
    _runner.main()
