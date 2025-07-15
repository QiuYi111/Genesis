"""
Age Progression System - Manages era transitions and technological development.

This system determines when the society has developed sufficiently to advance to the next era,
tracking technological progress, social complexity, and cultural evolution.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from loguru import logger


class EraType(Enum):
    """Different eras of societal development"""
    STONE_AGE = "stone_age"
    BRONZE_AGE = "bronze_age"
    IRON_AGE = "iron_age"
    MEDIEVAL = "medieval"
    RENAISSANCE = "renaissance"
    INDUSTRIAL = "industrial"
    MODERN = "modern"
    INFORMATION = "information"


@dataclass
class EraDefinition:
    """Defines the characteristics and requirements for an era"""
    era_type: EraType
    name: str
    description: str
    required_technologies: List[str]
    required_social_complexity: float  # 0-1 scale
    required_population: int
    required_skills: Dict[str, float]  # skill_name: minimum_level
    required_buildings: List[str]
    max_duration: int  # maximum turns before automatic progression
    triggers: List[str]  # specific triggers that can cause progression
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'era_type': self.era_type.value,
            'name': self.name,
            'description': self.description,
            'required_technologies': self.required_technologies,
            'required_social_complexity': self.required_social_complexity,
            'required_population': self.required_population,
            'required_skills': self.required_skills,
            'required_buildings': self.required_buildings,
            'max_duration': self.max_duration,
            'triggers': self.triggers
        }


@dataclass
class EraProgress:
    """Tracks progress toward the next era"""
    current_era: EraType
    next_era: EraType
    progress_score: float  # 0-1 progress toward next era
    technology_progress: Dict[str, float]
    social_complexity_score: float
    population_score: float
    skills_progress: Dict[str, float]
    buildings_progress: Dict[str, int]
    era_duration: int
    last_check_turn: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'current_era': self.current_era.value,
            'next_era': self.next_era.value,
            'progress_score': self.progress_score,
            'technology_progress': self.technology_progress,
            'social_complexity_score': self.social_complexity_score,
            'population_score': self.population_score,
            'skills_progress': self.skills_progress,
            'buildings_progress': self.buildings_progress,
            'era_duration': self.era_duration,
            'last_check_turn': self.last_check_turn
        }


class AgeProgression:
    """
    Manages era transitions based on societal development indicators.
    
    This system continuously evaluates the society's readiness for advancement
    to the next era based on technological, social, and cultural criteria.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.era_progression_threshold = config.get('age_progression_threshold', 0.8)
        self.check_interval = config.get('era_check_interval', 50)
        
        # Era definitions
        self.era_definitions = self._initialize_era_definitions()
        self.current_era = EraType.STONE_AGE
        self.era_progress = self._initialize_era_progress()
        
        # Progress tracking
        self.progression_history: List[Dict[str, Any]] = []
        self.era_start_turn = 0
        
    def _initialize_era_definitions(self) -> Dict[EraType, EraDefinition]:
        """Initialize era definitions with specific requirements"""
        return {
            EraType.STONE_AGE: EraDefinition(
                era_type=EraType.STONE_AGE,
                name="Stone Age",
                description="Basic survival and tool-making era",
                required_technologies=["fire_making", "stone_tools", "basic_shelter"],
                required_social_complexity=0.3,
                required_population=5,
                required_skills={"gathering": 0.5, "tool_making": 0.4},
                required_buildings=["basic_shelter"],
                max_duration=200,
                triggers=["tool_mastery", "fire_mastery", "social_cooperation"]
            ),
            EraType.BRONZE_AGE: EraDefinition(
                era_type=EraType.BRONZE_AGE,
                name="Bronze Age",
                description="Metalworking and agriculture development",
                required_technologies=["bronze_making", "agriculture", "permanent_shelter"],
                required_social_complexity=0.5,
                required_population=15,
                required_skills={"mining": 0.6, "agriculture": 0.5, "metalworking": 0.4},
                required_buildings=["permanent_shelter", "storage", "workshop"],
                max_duration=300,
                triggers=["metal_discovery", "agriculture_development", "trade_establishment"]
            ),
            EraType.IRON_AGE: EraDefinition(
                era_type=EraType.IRON_AGE,
                name="Iron Age",
                description="Advanced metallurgy and social organization",
                required_technologies=["iron_smelting", "advanced_agriculture", "writing"],
                required_social_complexity=0.7,
                required_population=30,
                required_skills={"advanced_mining": 0.7, "advanced_metalworking": 0.6, "governance": 0.5},
                required_buildings=["fortress", "granary", "temple", "market"],
                max_duration=400,
                triggers=["iron_mastery", "governance_system", "trade_networks"]
            ),
            EraType.MEDIEVAL: EraDefinition(
                era_type=EraType.MEDIEVAL,
                name="Medieval Period",
                description="Feudalism and advanced architecture",
                required_technologies=["castle_construction", "feudalism", "advanced_writing"],
                required_social_complexity=0.8,
                required_population=50,
                required_skills={"architecture": 0.8, "governance": 0.7, "engineering": 0.6},
                required_buildings=["castle", "cathedral", "guild_hall", "university"],
                max_duration=500,
                triggers=["feudal_establishment", "advanced_architecture", "education_system"]
            ),
            EraType.RENAISSANCE: EraDefinition(
                era_type=EraType.RENAISSANCE,
                name="Renaissance",
                description="Cultural and scientific awakening",
                required_technologies=["printing_press", "scientific_method", "banking"],
                required_social_complexity=0.85,
                required_population=75,
                required_skills={"science": 0.8, "art": 0.7, "commerce": 0.8},
                required_buildings=["library", "bank", "observatory", "art_gallery"],
                max_duration=600,
                triggers=["cultural_awakening", "scientific_revolution", "commercial_expansion"]
            ),
            EraType.INDUSTRIAL: EraDefinition(
                era_type=EraType.INDUSTRIAL,
                name="Industrial Age",
                description="Mechanization and mass production",
                required_technologies=["steam_power", "factory_system", "railway"],
                required_social_complexity=0.9,
                required_population=100,
                required_skills={"engineering": 0.9, "manufacturing": 0.8, "transportation": 0.7},
                required_buildings=["factory", "railway_station", "power_plant", "warehouse"],
                max_duration=800,
                triggers=["industrial_machinery", "mass_production", "transportation_network"]
            ),
            EraType.MODERN: EraDefinition(
                era_type=EraType.MODERN,
                name="Modern Era",
                description="Electricity and global communication",
                required_technologies=["electricity", "telecommunications", "computers"],
                required_social_complexity=0.95,
                required_population=150,
                required_skills={"technology": 0.9, "communication": 0.8, "globalization": 0.7},
                required_buildings=["laboratory", "telecom_tower", "research_center", "hospital"],
                max_duration=1000,
                triggers=["digital_revolution", "global_communication", "scientific_breakthrough"]
            ),
            EraType.INFORMATION: EraDefinition(
                era_type=EraType.INFORMATION,
                name="Information Age",
                description="Digital revolution and AI development",
                required_technologies=["internet", "artificial_intelligence", "quantum_computing"],
                required_social_complexity=1.0,
                required_population=200,
                required_skills={"ai_development": 0.9, "data_science": 0.8, "cyber_security": 0.7},
                required_buildings=["data_center", "ai_facility", "quantum_lab", "space_station"],
                max_duration=1200,
                triggers=["ai_mastery", "global_connectivity", "space_exploration"]
            )
        }
    
    def _initialize_era_progress(self) -> EraProgress:
        """Initialize era progress tracking"""
        next_era = self._get_next_era(self.current_era)
        
        return EraProgress(
            current_era=self.current_era,
            next_era=next_era,
            progress_score=0.0,
            technology_progress={},
            social_complexity_score=0.0,
            population_score=0.0,
            skills_progress={},
            buildings_progress={},
            era_duration=0,
            last_check_turn=0
        )
    
    def _get_next_era(self, current_era: EraType) -> EraType:
        """Get the next era in the progression sequence"""
        era_order = list(EraType)
        current_index = era_order.index(current_era)
        
        if current_index + 1 < len(era_order):
            return era_order[current_index + 1]
        else:
            return current_era  # Stay in final era
    
    def check_era_progression(self, turn: int, simulation_state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if society is ready to advance to the next era"""
        
        if turn - self.era_progress.last_check_turn < self.check_interval:
            return {'ready': False, 'reason': 'check_interval_not_met'}
        
        self.era_progress.last_check_turn = turn
        self.era_progress.era_duration = turn - self.era_start_turn
        
        # Calculate progress toward next era
        progress_score = self._calculate_era_progress(simulation_state)
        self.era_progress.progress_score = progress_score
        
        # Check if ready to progress
        era_def = self.era_definitions[self.current_era]
        next_era = self.era_progress.next_era
        
        if next_era == self.current_era:
            return {'ready': False, 'reason': 'final_era_reached'}
        
        ready, reason = self._check_progression_requirements(
            simulation_state, era_def, next_era
        )
        
        if ready:
            return self._trigger_era_progression(turn, simulation_state)
        
        return {
            'ready': False,
            'reason': reason,
            'progress_score': progress_score,
            'current_era': self.current_era.value,
            'next_era': next_era.value
        }
    
    def _calculate_era_progress(self, simulation_state: Dict[str, Any]) -> float:
        """Calculate overall progress toward the next era"""
        era_def = self.era_definitions[self.current_era]
        
        # Calculate technology progress
        tech_progress = self._calculate_technology_progress(simulation_state, era_def)
        
        # Calculate social complexity
        social_complexity = self._calculate_social_complexity(simulation_state)
        
        # Calculate population score
        population_score = self._calculate_population_score(simulation_state, era_def)
        
        # Calculate skills progress
        skills_progress = self._calculate_skills_progress(simulation_state, era_def)
        
        # Calculate buildings progress
        buildings_progress = self._calculate_buildings_progress(simulation_state, era_def)
        
        # Calculate weighted average
        weights = {
            'technology': 0.25,
            'social_complexity': 0.25,
            'population': 0.2,
            'skills': 0.15,
            'buildings': 0.15
        }
        
        progress = (
            tech_progress * weights['technology'] +
            social_complexity * weights['social_complexity'] +
            population_score * weights['population'] +
            skills_progress * weights['skills'] +
            buildings_progress * weights['buildings']
        )
        
        # Update progress tracking
        self.era_progress.technology_progress = self._get_technology_scores(simulation_state, era_def)
        self.era_progress.social_complexity_score = social_complexity
        self.era_progress.population_score = population_score
        self.era_progress.skills_progress = self._get_skills_scores(simulation_state, era_def)
        self.era_progress.buildings_progress = self._get_buildings_counts(simulation_state, era_def)
        
        return progress
    
    def _calculate_technology_progress(self, simulation_state: Dict[str, Any], 
                                     era_def: EraDefinition) -> float:
        """Calculate technology progress toward era requirements"""
        discovered_techs = set(simulation_state.get('discovered_technologies', []))
        required_techs = set(era_def.required_technologies)
        
        if not required_techs:
            return 1.0
        
        discovered_required = len(discovered_techs.intersection(required_techs))
        return discovered_required / len(required_techs)
    
    def _calculate_social_complexity(self, simulation_state: Dict[str, Any]) -> float:
        """Calculate social complexity score based on agent interactions"""
        agent_states = simulation_state.get('agent_states', {})
        
        if not agent_states:
            return 0.0
        
        # Calculate based on social connections, group formation, rule adoption
        total_connections = 0
        total_agents = len(agent_states)
        
        for agent_data in agent_states.values():
            social_connections = agent_data.get('social_connections', 0)
            total_connections += social_connections
        
        # Normalize by expected connections
        max_possible_connections = total_agents * (total_agents - 1) / 2
        if max_possible_connections > 0:
            connection_ratio = total_connections / max_possible_connections
        else:
            connection_ratio = 0.0
        
        # Factor in rule adoption and group complexity
        rule_adoption = simulation_state.get('rule_adoption_rate', 0.0)
        group_complexity = min(1.0, total_agents / 20)  # More agents = more complexity
        
        return min(1.0, (connection_ratio + rule_adoption + group_complexity) / 3)
    
    def _calculate_population_score(self, simulation_state: Dict[str, Any], 
                                  era_def: EraDefinition) -> float:
        """Calculate population score based on era requirements"""
        agent_states = simulation_state.get('agent_states', {})
        current_population = len(agent_states)
        required_population = era_def.required_population
        
        if required_population == 0:
            return 1.0
        
        return min(1.0, current_population / required_population)
    
    def _calculate_skills_progress(self, simulation_state: Dict[str, Any], 
                                 era_def: EraDefinition) -> float:
        """Calculate skills progress toward era requirements"""
        agent_states = simulation_state.get('agent_states', {})
        
        if not agent_states:
            return 0.0
        
        total_progress = 0.0
        required_skills = era_def.required_skills
        
        for skill_name, required_level in required_skills.items():
            skill_total = 0.0
            skill_count = 0
            
            for agent_data in agent_states.values():
                skills = agent_data.get('skills', {})
                if skill_name in skills:
                    skill_total += skills[skill_name]
                    skill_count += 1
            
            if skill_count > 0:
                average_skill = skill_total / skill_count
                skill_progress = min(1.0, average_skill / required_level)
                total_progress += skill_progress
        
        return total_progress / len(required_skills) if required_skills else 1.0
    
    def _calculate_buildings_progress(self, simulation_state: Dict[str, Any], 
                                    era_def: EraDefinition) -> float:
        """Calculate buildings progress toward era requirements"""
        world_summary = simulation_state.get('world_summary', {})
        built_buildings = world_summary.get('buildings', [])
        required_buildings = era_def.required_buildings
        
        if not required_buildings:
            return 1.0
        
        built_set = set(built_buildings)
        required_set = set(required_buildings)
        
        built_required = len(built_set.intersection(required_set))
        return built_required / len(required_set)
    
    def _get_technology_scores(self, simulation_state: Dict[str, Any], 
                             era_def: EraDefinition) -> Dict[str, float]:
        """Get individual technology scores"""
        discovered_techs = set(simulation_state.get('discovered_technologies', []))
        
        tech_scores = {}
        for tech in era_def.required_technologies:
            tech_scores[tech] = 1.0 if tech in discovered_techs else 0.0
        
        return tech_scores
    
    def _get_skills_scores(self, simulation_state: Dict[str, Any], 
                         era_def: EraDefinition) -> Dict[str, float]:
        """Get individual skills scores"""
        agent_states = simulation_state.get('agent_states', {})
        skills_scores = {}
        
        for skill_name, required_level in era_def.required_skills.items():
            skill_total = 0.0
            skill_count = 0
            
            for agent_data in agent_states.values():
                skills = agent_data.get('skills', {})
                if skill_name in skills:
                    skill_total += skills[skill_name]
                    skill_count += 1
            
            if skill_count > 0:
                average_skill = skill_total / skill_count
                skills_scores[skill_name] = min(1.0, average_skill / required_level)
            else:
                skills_scores[skill_name] = 0.0
        
        return skills_scores
    
    def _get_buildings_counts(self, simulation_state: Dict[str, Any], 
                            era_def: EraDefinition) -> Dict[str, int]:
        """Get buildings counts"""
        world_summary = simulation_state.get('world_summary', {})
        all_buildings = world_summary.get('buildings', [])
        
        buildings_counts = {}
        for building in era_def.required_buildings:
            buildings_counts[building] = all_buildings.count(building)
        
        return buildings_counts
    
    def _check_progression_requirements(self, simulation_state: Dict[str, Any], 
                                      current_era_def: EraDefinition, 
                                      next_era: EraType) -> tuple[bool, str]:
        """Check if all progression requirements are met"""
        
        # Check max duration
        if self.era_progress.era_duration >= current_era_def.max_duration:
            return True, "max_duration_reached"
        
        # Check technology requirements
        tech_progress = self._calculate_technology_progress(simulation_state, current_era_def)
        if tech_progress < 0.8:
            return False, f"insufficient_technology: {tech_progress:.2f}"
        
        # Check social complexity
        social_complexity = self._calculate_social_complexity(simulation_state)
        if social_complexity < current_era_def.required_social_complexity * 0.9:
            return False, f"insufficient_social_complexity: {social_complexity:.2f}"
        
        # Check population
        population_score = self._calculate_population_score(simulation_state, current_era_def)
        if population_score < 0.8:
            return False, f"insufficient_population: {population_score:.2f}"
        
        # Check skills
        skills_progress = self._calculate_skills_progress(simulation_state, current_era_def)
        if skills_progress < 0.8:
            return False, f"insufficient_skills: {skills_progress:.2f}"
        
        # Check buildings
        buildings_progress = self._calculate_buildings_progress(simulation_state, current_era_def)
        if buildings_progress < 0.8:
            return False, f"insufficient_buildings: {buildings_progress:.2f}"
        
        # Check overall progress
        if self.era_progress.progress_score < self.era_progression_threshold:
            return False, f"insufficient_overall_progress: {self.era_progress.progress_score:.2f}"
        
        return True, "requirements_met"
    
    def _trigger_era_progression(self, turn: int, simulation_state: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger era progression"""
        old_era = self.current_era
        new_era = self.era_progress.next_era
        
        # Update era
        self.current_era = new_era
        self.era_start_turn = turn
        
        # Reset progress tracking for new era
        self.era_progress = self._initialize_era_progress()
        
        # Record progression
        progression_record = {
            'turn': turn,
            'old_era': old_era.value,
            'new_era': new_era.value,
            'era_duration': turn - self.era_start_turn,
            'progress_score': self.era_progress.progress_score,
            'simulation_state': simulation_state
        }
        
        self.progression_history.append(progression_record)
        
        logger.info(f"Era progression: {old_era.value} → {new_era.value} at turn {turn}")
        
        return {
            'ready': True,
            'old_era': old_era.value,
            'new_era': new_era.value,
            'progression_record': progression_record
        }
    
    def get_current_era(self) -> EraType:
        """Get the current era"""
        return self.current_era
    
    def get_era_description(self) -> str:
        """Get description of current era"""
        era_def = self.era_definitions[self.current_era]
        return era_def.description
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get comprehensive progress summary"""
        return {
            'current_era': self.current_era.value,
            'current_era_name': self.era_definitions[self.current_era].name,
            'current_era_description': self.era_definitions[self.current_era].description,
            'next_era': self.era_progress.next_era.value if self.era_progress.next_era != self.current_era else None,
            'progress_score': self.era_progress.progress_score,
            'technology_progress': self.era_progress.technology_progress,
            'social_complexity_score': self.era_progress.social_complexity_score,
            'population_score': self.era_progress.population_score,
            'skills_progress': self.era_progress.skills_progress,
            'buildings_progress': self.era_progress.buildings_progress,
            'era_duration': self.era_progress.era_duration,
            'era_definitions': {era.value: era_def.to_dict() for era, era_def in self.era_definitions.items()},
            'progression_history': self.progression_history
        }
    
    def reset_era_progression(self):
        """Reset era progression (for testing purposes)"""
        self.current_era = EraType.STONE_AGE
        self.era_progress = self._initialize_era_progress()
        self.era_start_turn = 0
        self.progression_history.clear()
    
    def get_era_context_prompt(self) -> str:
        """Get context prompt for current era to guide agent behavior"""
        era_contexts = {
            EraType.STONE_AGE: "You live in the Stone Age. Focus on basic survival: finding food, water, and shelter. Work with simple stone tools and basic cooperation.",
            EraType.BRONZE_AGE: "You live in the Bronze Age. Agriculture and metalworking are developing. Build permanent settlements and establish trade networks.",
            EraType.IRON_AGE: "You live in the Iron Age. Advanced metallurgy and social organization. Develop complex societies with governance and specialized roles.",
            EraType.MEDIEVAL: "You live in the Medieval period. Feudal systems and advanced architecture. Build castles, establish kingdoms, and develop education.",
            EraType.RENAISSANCE: "You live in the Renaissance. Cultural and scientific awakening. Pursue art, science, and global exploration.",
            EraType.INDUSTRIAL: "You live in the Industrial Age. Mechanization and mass production. Build factories and transportation networks.",
            EraType.MODERN: "You live in the Modern Era. Electricity and global communication. Develop advanced technology and international cooperation.",
            EraType.INFORMATION: "You live in the Information Age. Digital revolution and AI development. Create advanced technology and explore space."
        }
        
        return era_contexts.get(self.current_era, "Unknown era")
    
    def get_era_specific_skills(self) -> List[str]:
        """Get skills specific to the current era"""
        era_skills = {
            EraType.STONE_AGE: ["gathering", "stone_tools", "basic_shelter", "fire_making"],
            EraType.BRONZE_AGE: ["agriculture", "bronze_making", "permanent_shelter", "trade"],
            EraType.IRON_AGE: ["iron_smelting", "advanced_agriculture", "governance", "writing"],
            EraType.MEDIEVAL: ["architecture", "feudalism", "education", "commerce"],
            EraType.RENAISSANCE: ["science", "art", "exploration", "banking"],
            EraType.INDUSTRIAL: ["engineering", "manufacturing", "transportation", "mass_production"],
            EraType.MODERN: ["technology", "communication", "globalization", "medicine"],
            EraType.INFORMATION: ["ai_development", "data_science", "cyber_security", "space_exploration"]
        }
        
        return era_skills.get(self.current_era, [])