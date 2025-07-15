"""
Trinity System - The central intelligence that observes, learns, and evolves the simulation.

This is the main orchestrator that coordinates all Trinity components:
- TrinityObserver: Behavior monitoring and pattern recognition
- SkillGenerator: Dynamic skill creation
- RuleEvolution: Social rule and recipe evolution  
- EventOrchestrator: World event management
- AgeProgression: Era transitions
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from .observer.observer import TrinityObserver
from .generator.skill_generator import SkillGenerator
from .generator.rule_evolution import RuleEvolution
from .events.event_orchestrator import EventOrchestrator
from .generator.age_progression import AgeProgression


@dataclass
class TrinityState:
    """Complete state of the Trinity system"""
    turn: int
    patterns_detected: int
    skills_generated: int
    rules_evolved: int
    events_triggered: int
    current_era: str
    era_progress: float
    last_analysis_turn: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'turn': self.turn,
            'patterns_detected': self.patterns_detected,
            'skills_generated': self.skills_generated,
            'rules_evolved': self.rules_evolved,
            'events_triggered': self.events_triggered,
            'current_era': self.current_era,
            'era_progress': self.era_progress,
            'last_analysis_turn': self.last_analysis_turn
        }


class TrinitySystem:
    """
    The Trinity System - Central intelligence that drives simulation evolution.
    
    This system observes agent behaviors, generates new capabilities, evolves rules,
    triggers events, and manages era progression based on collective development.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.trinity_config = config.get('trinity', {})
        
        # Initialize Trinity components
        self.observer = TrinityObserver(self.trinity_config)
        self.skill_generator = SkillGenerator(self.trinity_config)
        self.rule_evolution = RuleEvolution(self.trinity_config)
        self.event_orchestrator = EventOrchestrator(self.trinity_config)
        self.age_progression = AgeProgression(self.trinity_config)
        
        # System state
        self.state = TrinityState(
            turn=0,
            patterns_detected=0,
            skills_generated=0,
            rules_evolved=0,
            events_triggered=0,
            current_era=self.age_progression.get_current_era().value,
            era_progress=0.0,
            last_analysis_turn=0
        )
        
        # Configuration
        self.analysis_interval = self.trinity_config.get('observation_interval', 10)
        self.verbose_logging = self.trinity_config.get('verbose_logging', True)
        
    async def analyze_turn(self, turn: int, simulation_state: Dict[str, Any], 
                          world_width: int, world_height: int) -> Dict[str, Any]:
        """Perform Trinity analysis for this simulation turn"""
        
        if turn - self.state.last_analysis_turn < self.analysis_interval:
            return {'action_taken': False, 'reason': 'interval_not_met'}
        
        self.state.last_analysis_turn = turn
        self.state.turn = turn
        
        # Update era context
        self.state.current_era = self.age_progression.get_current_era().value
        
        results = {
            'turn': turn,
            'era': self.state.current_era,
            'actions': []
        }
        
        # 1. Analyze patterns from recent behavior
        patterns = self.observer.analyze_patterns(turn)
        self.state.patterns_detected += len(patterns)
        
        if patterns and self.verbose_logging:
            logger.info(f"Trinity detected {len(patterns)} new patterns")
        
        # 2. Generate new skills based on patterns
        new_skills = self.skill_generator.generate_skills_from_patterns(patterns, turn)
        self.state.skills_generated += len(new_skills)
        
        if new_skills:
            results['actions'].append({
                'type': 'skill_generation',
                'count': len(new_skills),
                'skills': [skill.name for skill in new_skills]
            })
            if self.verbose_logging:
                logger.info(f"Trinity generated {len(new_skills)} new skills")
        
        # 3. Evolve rules and recipes based on patterns
        evolution_results = self.rule_evolution.evolve_rules_from_patterns(patterns, turn)
        new_rules = evolution_results.get('new_rules', [])
        new_recipes = evolution_results.get('new_recipes', [])
        
        self.state.rules_evolved += len(new_rules) + len(new_recipes)
        
        if new_rules or new_recipes:
            results['actions'].append({
                'type': 'rule_evolution',
                'new_rules': len(new_rules),
                'new_recipes': len(new_recipes)
            })
        
        # 4. Generate world events based on patterns and state
        event = self.event_orchestrator.generate_event(
            turn, patterns, simulation_state, world_width, world_height
        )
        
        if event:
            self.state.events_triggered += 1
            results['actions'].append({
                'type': 'event_triggered',
                'event_name': event.name,
                'severity': event.severity
            })
        
        # 5. Update active events
        self.event_orchestrator.update_events(turn)
        
        # 6. Check era progression
        era_result = self.age_progression.check_era_progression(turn, simulation_state)
        
        if era_result.get('ready', False):
            results['actions'].append({
                'type': 'era_progression',
                'old_era': era_result['old_era'],
                'new_era': era_result['new_era']
            })
            self.state.era_progress = 0.0  # Reset for new era
        else:
            # Update era progress
            self.state.era_progress = self.age_progression.era_progress.progress_score
        
        # 7. Update Trinity state
        self.state.turn = turn
        
        return results
    
    def observe_agent_action(self, turn: int, agent_id: str, action: Dict[str, Any], 
                           context: Dict[str, Any]):
        """Record an agent action for Trinity analysis"""
        self.observer.observe_agent_action(turn, agent_id, action, context)
    
    def get_available_skills(self, agent_attributes: Dict[str, float], 
                           agent_skills: Dict[str, float], 
                           agent_inventory: Dict[str, float]) -> List[Any]:
        """Get skills available to a specific agent"""
        return self.skill_generator.get_available_skills(
            agent_attributes, agent_skills, agent_inventory
        )
    
    def get_available_rules(self, agent_id: str, agent_context: Dict[str, Any]) -> List[Any]:
        """Get social rules relevant to an agent's context"""
        return self.rule_evolution.get_available_rules(agent_id, agent_context)
    
    def get_available_recipes(self, agent_skills: Dict[str, float], 
                            agent_inventory: Dict[str, float]) -> List[Any]:
        """Get crafting recipes available to an agent"""
        return self.rule_evolution.get_available_recipes(agent_skills, agent_inventory)
    
    def get_event_effects(self, position: tuple, turn: int) -> Dict[str, Any]:
        """Get cumulative effects of active events at a position"""
        return self.event_orchestrator.get_event_effects(position, turn)
    
    def get_era_context(self) -> str:
        """Get context description for current era"""
        return self.age_progression.get_era_context_prompt()
    
    def get_era_specific_skills(self) -> List[str]:
        """Get skills specific to the current era"""
        return self.age_progression.get_era_specific_skills()
    
    def get_trinity_summary(self) -> Dict[str, Any]:
        """Get comprehensive Trinity system summary"""
        return {
            'state': self.state.to_dict(),
            'observer_summary': self.observer.get_behavior_summary(self.state.turn),
            'skill_summary': self.skill_generator.get_skill_summary(),
            'rule_summary': self.rule_evolution.get_evolution_summary(),
            'event_summary': self.event_orchestrator.get_active_events_summary(),
            'era_summary': self.age_progression.get_progress_summary(),
            'era_context': self.get_era_context(),
            'era_skills': self.get_era_specific_skills()
        }
    
    def reset_trinity_system(self):
        """Reset all Trinity components (for testing purposes)"""
        self.observer.reset_observations()
        self.skill_generator.reset_skills()
        self.rule_evolution.reset_rules()
        self.event_orchestrator.reset_events()
        self.age_progression.reset_era_progression()
        
        self.state = TrinityState(
            turn=0,
            patterns_detected=0,
            skills_generated=0,
            rules_evolved=0,
            events_triggered=0,
            current_era=self.age_progression.get_current_era().value,
            era_progress=0.0,
            last_analysis_turn=0
        )
    
    def get_trinity_context_for_llm(self) -> str:
        """Generate context for LLM prompts about Trinity system state"""
        era_context = self.get_era_context()
        era_skills = self.get_era_specific_skills()
        
        return f"""
        Trinity System Context:
        - Current Era: {self.state.current_era.replace('_', ' ').title()}
        - Era Progress: {self.state.era_progress:.0%}
        - Skills Generated: {self.state.skills_generated}
        - Rules Evolved: {self.state.rules_evolved}
        - Events Triggered: {self.state.events_triggered}
        
        Era Context: {era_context}
        
        Era-Specific Skills Available: {', '.join(era_skills)}
        
        The Trinity system continuously observes your collective behavior and may:
        - Generate new skills based on your actions
        - Create social rules and crafting recipes
        - Trigger world events
        - Advance the era when society develops sufficiently
        """"