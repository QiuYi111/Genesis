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
from enum import Enum

from loguru import logger


class Era(Enum):
    """Simulation eras"""
    STONE_AGE = "stone_age"
    BRONZE_AGE = "bronze_age"
    IRON_AGE = "iron_age"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    FUTURE = "future"


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
        
        # Initialize basic components (will be enhanced in Phase 2)
        self.state = TrinityState(
            turn=0,
            patterns_detected=0,
            skills_generated=0,
            rules_evolved=0,
            events_triggered=0,
            current_era=Era.STONE_AGE.value,
            era_progress=0.0,
            last_analysis_turn=0
        )
        
        # Configuration
        self.analysis_interval = self.trinity_config.get('observation_frequency', 5)
        self.verbose_logging = self.trinity_config.get('verbose_logging', True)
        
        # Era progression thresholds
        self.era_thresholds = {
            Era.STONE_AGE.value: 100,
            Era.BRONZE_AGE.value: 250,
            Era.IRON_AGE.value: 500,
            Era.MEDIEVAL.value: 800,
            Era.RENAISSANCE.value: 1200,
            Era.INDUSTRIAL.value: 1800,
            Era.MODERN.value: 2500,
            Era.FUTURE.value: float('inf')
        }
        
        # Pattern tracking
        self.behavior_patterns = []
        self.skill_templates = []
        self.social_rules = []
        self.active_events = []
        
    async def analyze_turn(self, turn: int, simulation_state: Dict[str, Any], 
                          world_width: int, world_height: int) -> Dict[str, Any]:
        """Perform Trinity analysis for this simulation turn"""
        
        if turn - self.state.last_analysis_turn < self.analysis_interval:
            return {'action_taken': False, 'reason': 'interval_not_met'}
        
        self.state.last_analysis_turn = turn
        self.state.turn = turn
        
        results = {
            'turn': turn,
            'era': self.state.current_era,
            'actions': []
        }
        
        # 1. Analyze patterns from agent behaviors
        patterns = self._analyze_patterns(simulation_state)
        self.state.patterns_detected += len(patterns)
        
        if patterns and self.verbose_logging:
            logger.info(f"Trinity detected {len(patterns)} new patterns")
        
        # 2. Generate new skills based on patterns
        new_skills = self._generate_skills(patterns, simulation_state)
        self.state.skills_generated += len(new_skills)
        
        if new_skills:
            results['actions'].append({
                'type': 'skill_generation',
                'count': len(new_skills),
                'skills': new_skills
            })
            if self.verbose_logging:
                logger.info(f"Trinity generated {len(new_skills)} new skills")
        
        # 3. Evolve social rules based on patterns
        new_rules = self._evolve_rules(patterns, simulation_state)
        self.state.rules_evolved += len(new_rules)
        
        if new_rules:
            results['actions'].append({
                'type': 'rule_evolution',
                'new_rules': len(new_rules),
                'rules': new_rules
            })
        
        # 4. Generate world events based on simulation state
        events = self._generate_events(simulation_state, turn)
        self.state.events_triggered += len(events)
        
        if events:
            results['actions'].extend(events)
        
        # 5. Check era progression
        era_result = self._check_era_progression(simulation_state, turn)
        
        if era_result.get('ready', False):
            results['actions'].append({
                'type': 'era_progression',
                'old_era': era_result['old_era'],
                'new_era': era_result['new_era']
            })
            self.state.era_progress = 0.0
        else:
            # Update era progress
            self.state.era_progress = self._calculate_era_progress(simulation_state)
        
        return results
    
    def _analyze_patterns(self, simulation_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze patterns from agent behaviors"""
        patterns = []
        
        agents = simulation_state.get('agents', {})
        if not agents:
            return patterns
        
        # Count behaviors
        behavior_counts = {
            'gathering': 0,
            'exploring': 0,
            'socializing': 0,
            'building': 0,
            'fighting': 0,
            'resting': 0
        }
        
        total_agents = len(agents)
        
        # Analyze agent states and behaviors
        for agent_id, agent_data in agents.items():
            state = agent_data.get('state', 'idle')
            if 'gather' in str(state).lower():
                behavior_counts['gathering'] += 1
            elif 'explore' in str(state).lower():
                behavior_counts['exploring'] += 1
            elif 'social' in str(state).lower():
                behavior_counts['socializing'] += 1
            elif 'build' in str(state).lower():
                behavior_counts['building'] += 1
            elif 'fight' in str(state).lower():
                behavior_counts['fighting'] += 1
            elif 'rest' in str(state).lower():
                behavior_counts['resting'] += 1
        
        # Detect patterns based on behavior ratios
        for behavior, count in behavior_counts.items():
            ratio = count / max(total_agents, 1)
            if ratio > 0.3:  # 30% threshold
                patterns.append({
                    'type': f'high_{behavior}',
                    'ratio': ratio,
                    'count': count,
                    'description': f'High {behavior} activity detected'
                })
        
        # Analyze resource distribution
        total_resources = simulation_state.get('total_resources', {})
        if total_resources:
            resource_diversity = len([r for r in total_resources.values() if r > 0])
            if resource_diversity > 5:
                patterns.append({
                    'type': 'resource_diversity',
                    'diversity': resource_diversity,
                    'description': 'High resource diversity achieved'
                })
        
        # Analyze social connections
        social_connections = [a.get('social_connections', 0) for a in agents.values()]
        avg_connections = sum(social_connections) / max(len(social_connections), 1)
        if avg_connections > 3:
            patterns.append({
                'type': 'social_complexity',
                'avg_connections': avg_connections,
                'description': 'Complex social network detected'
            })
        
        return patterns
    
    def _generate_skills(self, patterns: List[Dict[str, Any]], 
                        simulation_state: Dict[str, Any]) -> List[str]:
        """Generate new skills based on detected patterns"""
        new_skills = []
        
        for pattern in patterns:
            pattern_type = pattern['type']
            
            if pattern_type == 'high_gathering' and pattern['ratio'] > 0.5:
                new_skills.append('efficient_gathering')
            elif pattern_type == 'high_exploring' and pattern['ratio'] > 0.4:
                new_skills.append('navigation')
            elif pattern_type == 'high_socializing' and pattern['ratio'] > 0.3:
                new_skills.append('leadership')
            elif pattern_type == 'high_building' and pattern['ratio'] > 0.2:
                new_skills.append('advanced_construction')
            elif pattern_type == 'resource_diversity':
                new_skills.append('resource_management')
            elif pattern_type == 'social_complexity':
                new_skills.append('diplomacy')
        
        return new_skills
    
    def _evolve_rules(self, patterns: List[Dict[str, Any]], 
                     simulation_state: Dict[str, Any]) -> List[str]:
        """Evolve social rules based on patterns"""
        new_rules = []
        
        for pattern in patterns:
            pattern_type = pattern['type']
            
            if pattern_type == 'high_gathering':
                new_rules.append('resource_sharing_protocol')
            elif pattern_type == 'high_socializing':
                new_rules.append('group_coordination')
            elif pattern_type == 'high_building':
                new_rules.append('construction_cooperation')
            elif pattern_type == 'social_complexity':
                new_rules.append('conflict_resolution')
        
        return new_rules
    
    def _generate_events(self, simulation_state: Dict[str, Any], turn: int) -> List[Dict[str, Any]]:
        """Generate world events based on simulation state"""
        events = []
        
        agents = simulation_state.get('agents', {})
        total_agents = len(agents)
        
        # Natural disaster events
        if turn > 50 and turn % 100 == 0:
            events.append({
                'type': 'natural_disaster',
                'name': 'storm',
                'severity': 'medium',
                'description': 'A storm passes through the area'
            })
        
        # Resource boom events
        if total_agents > 20 and turn % 75 == 0:
            events.append({
                'type': 'resource_boom',
                'name': 'abundant_season',
                'severity': 'positive',
                'description': 'Resources are particularly abundant'
            })
        
        # Social events
        avg_connections = 0
        if agents:
            connections = [a.get('social_connections', 0) for a in agents.values()]
            avg_connections = sum(connections) / len(connections)
        
        if avg_connections > 5 and turn % 50 == 0:
            events.append({
                'type': 'social_event',
                'name': 'community_gathering',
                'severity': 'positive',
                'description': 'A community gathering is organized'
            })
        
        return events
    
    def _check_era_progression(self, simulation_state: Dict[str, Any], 
                              turn: int) -> Dict[str, Any]:
        """Check if society is ready for era progression"""
        current_threshold = self.era_thresholds.get(self.state.current_era, 0)
        
        # Calculate progress based on various factors
        agents = simulation_state.get('agents', {})
        total_agents = len(agents)
        
        if total_agents == 0:
            return {'ready': False}
        
        # Progress factors
        skill_diversity = len(set())  # Would track discovered skills
        social_complexity = sum([a.get('social_connections', 0) for a in agents.values()]) / total_agents
        resource_utilization = len([r for r in simulation_state.get('total_resources', {}).values() if r > 0])
        
        # Simple progress calculation
        progress_score = (social_complexity + resource_utilization + (turn / 10)) / 3
        
        if progress_score >= current_threshold and turn > 50:
            # Find next era
            current_index = list(self.era_thresholds.keys()).index(self.state.current_era)
            if current_index + 1 < len(self.era_thresholds):
                next_era = list(self.era_thresholds.keys())[current_index + 1]
                return {
                    'ready': True,
                    'old_era': self.state.current_era,
                    'new_era': next_era
                }
        
        return {'ready': False}
    
    def _calculate_era_progress(self, simulation_state: Dict[str, Any]) -> float:
        """Calculate progress towards next era"""
        agents = simulation_state.get('agents', {})
        total_agents = len(agents)
        
        if total_agents == 0:
            return 0.0
        
        # Calculate progress based on multiple factors
        social_factor = min(1.0, sum([a.get('social_connections', 0) for a in agents.values()]) / (total_agents * 10))
        resource_factor = min(1.0, len([r for r in simulation_state.get('total_resources', {}).values() if r > 0]) / 10)
        
        return (social_factor + resource_factor) / 2
    
    def get_current_era(self) -> str:
        """Get current simulation era"""
        return self.state.current_era
    
    def get_era_context(self) -> str:
        """Get context description for current era"""
        era_descriptions = {
            Era.STONE_AGE.value: "You are in the Stone Age. Basic survival skills and simple tools are available.",
            Era.BRONZE_AGE.value: "You are in the Bronze Age. Metalworking and agriculture have been discovered.",
            Era.IRON_AGE.value: "You are in the Iron Age. Advanced tools and weapons are available.",
            Era.MEDIEVAL.value: "You are in the Medieval period. Complex social structures and technologies exist.",
            Era.RENAISSANCE.value: "You are in the Renaissance. Art, science, and culture are flourishing.",
            Era.INDUSTRIAL.value: "You are in the Industrial Age. Mechanization and mass production are possible.",
            Era.MODERN.value: "You are in the Modern Age. Advanced technology and global communication exist.",
            Era.FUTURE.value: "You are in the Future. Advanced technology and space exploration are possible."
        }
        
        return era_descriptions.get(self.state.current_era, "Unknown era")
    
    def get_era_specific_skills(self) -> List[str]:
        """Get skills specific to the current era"""
        era_skills = {
            Era.STONE_AGE.value: ["basic_gathering", "simple_tools", "fire_making"],
            Era.BRONZE_AGE.value: ["agriculture", "metalworking", "pottery", "trade"],
            Era.IRON_AGE.value: ["advanced_tools", "weapon_crafting", "fortification"],
            Era.MEDIEVAL.value: ["architecture", "governance", "commerce", "diplomacy"],
            Era.RENAISSANCE.value: ["artistry", "science", "navigation", "banking"],
            Era.INDUSTRIAL.value: ["mechanization", "mass_production", "transportation"],
            Era.MODERN.value: ["electronics", "communication", "automation"],
            Era.FUTURE.value: ["space_travel", "quantum_tech", "ai_integration"]
        }
        
        return era_skills.get(self.state.current_era, [])
    
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
        """
    
    def get_trinity_summary(self) -> Dict[str, Any]:
        """Get comprehensive Trinity system summary"""
        return {
            'state': self.state.to_dict(),
            'era_context': self.get_era_context(),
            'era_skills': self.get_era_specific_skills(),
            'patterns': len(self.behavior_patterns),
            'skills': len(self.skill_templates),
            'rules': len(self.social_rules),
            'events': len(self.active_events)
        }
    
    def observe_agent_action(self, turn: int, agent_id: str, action: Dict[str, Any], 
                           context: Dict[str, Any]):
        """Record an agent action for Trinity analysis"""
        # Store action for pattern analysis
        self.behavior_patterns.append({
            'turn': turn,
            'agent_id': agent_id,
            'action': action,
            'context': context
        })
        
        # Keep only recent patterns
        max_patterns = 1000
        if len(self.behavior_patterns) > max_patterns:
            self.behavior_patterns = self.behavior_patterns[-max_patterns:]
    
    def get_available_skills(self, agent_attributes: Dict[str, float], 
                           agent_skills: Dict[str, float], 
                           agent_inventory: Dict[str, float]) -> List[str]:
        """Get skills available to a specific agent"""
        available_skills = self.get_era_specific_skills()
        
        # Filter by agent capabilities
        filtered_skills = []
        for skill in available_skills:
            # Simple capability check
            intelligence = agent_attributes.get('intelligence', 0)
            if skill in ['basic_gathering', 'simple_tools'] or intelligence > 5:
                filtered_skills.append(skill)
        
        return filtered_skills
    
    def get_available_rules(self, agent_id: str, agent_context: Dict[str, Any]) -> List[str]:
        """Get social rules relevant to an agent's context"""
        # Return basic social rules based on era
        basic_rules = {
            Era.STONE_AGE.value: ["share_resources", "help_tribe"],
            Era.BRONZE_AGE.value: ["trade_fairly", "respect_leaders"],
            Era.IRON_AGE.value: ["defend_territory", "honor_agreements"],
        }
        
        return basic_rules.get(self.state.current_era, [])
    
    def get_available_recipes(self, agent_skills: Dict[str, float], 
                            agent_inventory: Dict[str, float]) -> List[str]:
        """Get crafting recipes available to an agent"""
        # Basic recipes by era
        basic_recipes = {
            Era.STONE_AGE.value: ["stone_axe", "wooden_shelter"],
            Era.BRONZE_AGE.value: ["bronze_tools", "pottery", "farm_plot"],
            Era.IRON_AGE.value: ["iron_weapons", "fortified_building"],
        }
        
        return basic_recipes.get(self.state.current_era, [])
    
    def get_event_effects(self, position: tuple, turn: int) -> Dict[str, Any]:
        """Get cumulative effects of active events at a position"""
        return {}  # Placeholder for event system
    
    def reset_trinity_system(self):
        """Reset all Trinity components (for testing purposes)"""
        self.state = TrinityState(
            turn=0,
            patterns_detected=0,
            skills_generated=0,
            rules_evolved=0,
            events_triggered=0,
            current_era=Era.STONE_AGE.value,
            era_progress=0.0,
            last_analysis_turn=0
        )
        self.behavior_patterns.clear()
        self.skill_templates.clear()
        self.social_rules.clear()
        self.active_events.clear()