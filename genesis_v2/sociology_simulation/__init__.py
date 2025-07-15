"""
Project Genesis v2 - Revolutionary LLM-driven sociology simulation engine.

A system where complex social structures emerge from simple agent behaviors
powered by Large Language Models and the Trinity observation system.
"""

__version__ = "0.1.0"
__author__ = "Jingyi Qiu"
__email__ = "j.qiu@example.com"

from .core.simulation import Simulation
from .core.world import World
from .agents.base import Agent

__all__ = ["Simulation", "World", "Agent"]