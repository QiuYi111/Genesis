"""
Trinity System - The omniscient observer and evolution engine.

The Trinity System observes agent behaviors, generates new skills, evolves rules,
and orchestrates world events based on collective behavior patterns.
"""

from .observer.observer import TrinityObserver
from .generator.skill_generator import SkillGenerator
from .generator.rule_evolution import RuleEvolution
from .events.event_orchestrator import EventOrchestrator
from .generator.age_progression import AgeProgression

__all__ = [
    'TrinityObserver',
    'SkillGenerator', 
    'RuleEvolution',
    'EventOrchestrator',
    'AgeProgression'
]