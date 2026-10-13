"""Comprehensive metrics and analytics system for sociology simulation"""
import time
import json
import statistics
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from enum import Enum
import math
from loguru import logger

from ..core.agent_state import AgentState, AgentStatus, SkillType, Relationship
from ..core.interactions import InteractionResult, InteractionType
from ..core.world_events import ActiveEvent, EventType


class MetricType(Enum):
    """Types of metrics to track"""
    POPULATION = "population"
    ECONOMICS = "economics"
    SOCIAL = "social"
    TECHNOLOGY = "technology"
    ENVIRONMENT = "environment"
    PERFORMANCE = "performance"
    EMERGENT = "emergent"


@dataclass
class MetricSnapshot:
    """Single snapshot of simulation metrics"""
    turn: int
    timestamp: float
    population_metrics: Dict[str, Any] = field(default_factory=dict)
    economic_metrics: Dict[str, Any] = field(default_factory=dict)
    social_metrics: Dict[str, Any] = field(default_factory=dict)
    technology_metrics: Dict[str, Any] = field(default_factory=dict)
    environment_metrics: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    emergent_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Analysis of trends over time"""
    metric_name: str
    values: List[float]
    trend_direction: str  # "increasing", "decreasing", "stable", "volatile"
    trend_strength: float  # 0-1, how strong the trend is
    rate_of_change: float
    volatility: float
    predictions: List[float] = field(default_factory=list)


class PopulationMetrics:
    """Tracks population-related metrics"""
    
    @staticmethod
    def calculate(agents: List[AgentState], turn: int) -> Dict[str, Any]:
        """Calculate population metrics"""
        if not agents:
            return {"total_population": 0}
        
        living_agents = [a for a in agents if a.status == AgentStatus.ALIVE]
        
        # Basic demographics
        ages = [a.age for a in living_agents]
        healths = [a.health for a in living_agents]
        
        # Age distribution
        age_groups = {
            "children": len([a for a in living_agents if a.age < 18]),
            "adults": len([a for a in living_agents if 18 <= a.age < 60]),
            "elderly": len([a for a in living_agents if a.age >= 60])
        }
        
        # Health distribution
        health_groups = {
            "healthy": len([a for a in living_agents if a.health >= 80]),
            "injured": len([a for a in living_agents if 50 <= a.health < 80]),
            "critical": len([a for a in living_agents if a.health < 50])
        }
        
        # Attribute distribution
        attributes = {}
        for attr in ["strength", "intelligence", "charisma", "dexterity", "constitution", "wisdom"]:
            values = [a.attributes.get(attr, 5) for a in living_agents]
            attributes[attr] = {
                "mean": statistics.mean(values) if values else 0,
                "median": statistics.median(values) if values else 0,
                "std": statistics.stdev(values) if len(values) > 1 else 0
            }
        
        return {
            "total_population": len(living_agents),
            "population_change": 0,  # Will be calculated by comparing to previous turn
            "average_age": statistics.mean(ages) if ages else 0,
            "median_age": statistics.median(ages) if ages else 0,
            "average_health": statistics.mean(healths) if healths else 0,
            "age_distribution": age_groups,
            "health_distribution": health_groups,
            "attribute_distributions": attributes,
            "birth_rate": 0,  # Calculated externally
            "death_rate": 0   # Calculated externally
        }


class EconomicMetrics:
    """Tracks economic-related metrics"""
    
    @staticmethod
    def calculate(agents: List[AgentState], interactions: List[InteractionResult]) -> Dict[str, Any]:
        """Calculate economic metrics"""
        living_agents = [a for a in agents if a.status == AgentStatus.ALIVE]
        
        if not living_agents:
            return {"total_wealth": 0}
        
        # Wealth distribution (total inventory value)
        wealth_values = []
        resource_totals = defaultdict(int)
        
        for agent in living_agents:
            agent_wealth = sum(item.quantity for item in agent.inventory.values())
            wealth_values.append(agent_wealth)
            
            for item_name, item in agent.inventory.items():
                resource_totals[item_name] += item.quantity
        
        # Gini coefficient for wealth inequality
        gini = EconomicMetrics._calculate_gini(wealth_values) if wealth_values else 0
        
        # Trade metrics from recent interactions
        trade_interactions = [i for i in interactions 
                            if hasattr(i, 'interaction_type') and 
                            getattr(i, 'interaction_type', None) == InteractionType.TRADE]
        
        trade_volume = len(trade_interactions)
        successful_trades = len([i for i in trade_interactions if i.outcome.value == "success"])
        
        return {
            "total_wealth": sum(wealth_values),
            "average_wealth": statistics.mean(wealth_values) if wealth_values else 0,
            "median_wealth": statistics.median(wealth_values) if wealth_values else 0,
            "wealth_inequality_gini": gini,
            "resource_distribution": dict(resource_totals),
            "trade_volume": trade_volume,
            "trade_success_rate": successful_trades / max(trade_volume, 1),
            "economic_diversity": len(resource_totals)  # Number of different resources in circulation
        }
    
    @staticmethod
    def _calculate_gini(values: List[float]) -> float:
        """Calculate Gini coefficient for inequality measurement"""
        if not values or len(values) < 2:
            return 0.0
        
        values = sorted(values)
        n = len(values)
        cumsum = sum(values)
        
        if cumsum == 0:
            return 0.0
        
        gini = (2 * sum((i + 1) * val for i, val in enumerate(values))) / (n * cumsum) - (n + 1) / n
        return gini


class SocialMetrics:
    """Tracks social-related metrics"""
    
    @staticmethod
    def calculate(agents: List[AgentState], interactions: List[InteractionResult]) -> Dict[str, Any]:
        """Calculate social metrics"""
        living_agents = [a for a in agents if a.status == AgentStatus.ALIVE]
        
        if not living_agents:
            return {"social_cohesion": 0}
        
        # Relationship metrics
        total_relationships = 0
        positive_relationships = 0
        relationship_strengths = []
        trust_levels = []
        
        for agent in living_agents:
            total_relationships += len(agent.relationships)
            for rel in agent.relationships.values():
                relationship_strengths.append(rel.strength)
                trust_levels.append(rel.trust)
                if rel.strength > 0:
                    positive_relationships += 1
        
        # Group metrics
        all_groups = set()
        for agent in living_agents:
            all_groups.update(agent.group_memberships)
        
        # Family connections
        family_connections = 0
        for agent in living_agents:
            family_connections += len(agent.family_members)
        
        # Conflict metrics
        conflict_interactions = [i for i in interactions 
                               if hasattr(i, 'interaction_type') and 
                               getattr(i, 'interaction_type', None) == InteractionType.COMBAT]
        
        social_interactions = [i for i in interactions 
                             if hasattr(i, 'interaction_type') and 
                             getattr(i, 'interaction_type', None) == InteractionType.SOCIAL]
        
        return {
            "total_relationships": total_relationships,
            "positive_relationship_ratio": positive_relationships / max(total_relationships, 1),
            "average_relationship_strength": statistics.mean(relationship_strengths) if relationship_strengths else 0,
            "average_trust_level": statistics.mean(trust_levels) if trust_levels else 0,
            "social_cohesion": SocialMetrics._calculate_social_cohesion(living_agents),
            "number_of_groups": len(all_groups),
            "family_connections": family_connections,
            "conflict_rate": len(conflict_interactions),
            "social_interaction_rate": len(social_interactions),
            "cooperation_index": SocialMetrics._calculate_cooperation_index(interactions)
        }
    
    @staticmethod
    def _calculate_social_cohesion(agents: List[AgentState]) -> float:
        """Calculate overall social cohesion"""
        if len(agents) < 2:
            return 1.0
        
        total_possible_connections = len(agents) * (len(agents) - 1)
        actual_connections = sum(len(agent.relationships) for agent in agents)
        
        connection_density = actual_connections / total_possible_connections
        
        # Factor in relationship quality
        positive_strength_sum = 0
        total_strength_sum = 0
        
        for agent in agents:
            for rel in agent.relationships.values():
                total_strength_sum += abs(rel.strength)
                if rel.strength > 0:
                    positive_strength_sum += rel.strength
        
        quality_factor = positive_strength_sum / max(total_strength_sum, 1)
        
        return (connection_density + quality_factor) / 2
    
    @staticmethod
    def _calculate_cooperation_index(interactions: List[InteractionResult]) -> float:
        """Calculate cooperation vs competition index"""
        if not interactions:
            return 0.5
        
        cooperative_actions = 0
        competitive_actions = 0
        
        for interaction in interactions:
            if hasattr(interaction, 'interaction_type'):
                if interaction.interaction_type in [InteractionType.TRADE, InteractionType.DIPLOMACY, 
                                                   InteractionType.COOPERATION, InteractionType.SOCIAL]:
                    cooperative_actions += 1
                elif interaction.interaction_type in [InteractionType.COMBAT, InteractionType.COMPETITION]:
                    competitive_actions += 1
        
        total_actions = cooperative_actions + competitive_actions
        return cooperative_actions / max(total_actions, 1)


class TechnologyMetrics:
    """Tracks technology and skill development"""
    
    @staticmethod
    def calculate(agents: List[AgentState]) -> Dict[str, Any]:
        """Calculate technology metrics"""
        living_agents = [a for a in agents if a.status == AgentStatus.ALIVE]
        
        if not living_agents:
            return {"technology_level": 0}
        
        # Skill development
        skill_levels = defaultdict(list)
        total_experience = 0
        
        for agent in living_agents:
            total_experience += agent.total_experience
            for skill_type, skill in agent.skills.items():
                skill_levels[skill_type].append(skill.level)
        
        # Average skill levels
        avg_skill_levels = {}
        max_skill_levels = {}
        for skill_type, levels in skill_levels.items():
            avg_skill_levels[skill_type] = statistics.mean(levels)
            max_skill_levels[skill_type] = max(levels)
        
        # Technology diversity (number of different skills)
        skill_diversity = len(skill_levels)
        
        # Innovation rate (new tools/techniques discovered)
        # This would be tracked separately in actual implementation
        
        return {
            "total_experience": total_experience,
            "average_experience_per_agent": total_experience / len(living_agents),
            "skill_diversity": skill_diversity,
            "average_skill_levels": avg_skill_levels,
            "maximum_skill_levels": max_skill_levels,
            "technology_level": TechnologyMetrics._calculate_technology_level(avg_skill_levels),
            "skill_specialization": TechnologyMetrics._calculate_specialization(living_agents)
        }
    
    @staticmethod
    def _calculate_technology_level(avg_skills: Dict[SkillType, float]) -> float:
        """Calculate overall technology level"""
        if not avg_skills:
            return 0.0
        
        # Weight different skills differently
        skill_weights = {
            SkillType.CRAFTING: 0.3,
            SkillType.BUILDING: 0.2,
            SkillType.FARMING: 0.2,
            SkillType.HUNTING: 0.1,
            SkillType.MEDICINE: 0.1,
            SkillType.TRADING: 0.05,
            SkillType.LEADERSHIP: 0.05
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for skill_type, avg_level in avg_skills.items():
            weight = skill_weights.get(skill_type, 0.1)
            weighted_sum += avg_level * weight
            total_weight += weight
        
        return weighted_sum / max(total_weight, 1)
    
    @staticmethod
    def _calculate_specialization(agents: List[AgentState]) -> float:
        """Calculate how specialized agents are (vs generalists)"""
        if not agents:
            return 0.0
        
        specialization_scores = []
        
        for agent in agents:
            if not agent.skills:
                specialization_scores.append(0.0)
                continue
            
            skill_levels = [skill.level for skill in agent.skills.values()]
            if len(skill_levels) < 2:
                specialization_scores.append(0.0)
                continue
            
            # Higher standard deviation means more specialization
            std_dev = statistics.stdev(skill_levels)
            max_possible_std = statistics.stdev([1, 20])  # Min and max skill levels
            specialization = std_dev / max_possible_std
            specialization_scores.append(min(1.0, specialization))
        
        return statistics.mean(specialization_scores)


class EnvironmentMetrics:
    """Tracks environmental metrics"""
    
    @staticmethod
    def calculate(world_state: Dict[str, Any], active_events: List[ActiveEvent]) -> Dict[str, Any]:
        """Calculate environment metrics"""
        resource_availability = world_state.get("resource_totals", {})
        resource_diversity = len(resource_availability)
        
        # Environmental stress from active events
        environmental_stress = 0
        for event in active_events:
            if event.event_type in [EventType.NATURAL_DISASTER, EventType.WEATHER]:
                environmental_stress += {"minor": 1, "moderate": 2, "major": 3, "catastrophic": 5}.get(
                    event.severity.value, 0
                )
        
        # Resource sustainability (would need historical data)
        resource_trends = {}  # Would be calculated from historical data
        
        return {
            "resource_diversity": resource_diversity,
            "resource_availability": resource_availability,
            "environmental_stress": environmental_stress,
            "active_events_count": len(active_events),
            "resource_sustainability": resource_trends,
            "carrying_capacity_pressure": EnvironmentMetrics._calculate_carrying_capacity_pressure(world_state)
        }
    
    @staticmethod
    def _calculate_carrying_capacity_pressure(world_state: Dict[str, Any]) -> float:
        """Calculate pressure on environment carrying capacity"""
        population = world_state.get("population", 0)
        world_size = world_state.get("world_size", 64)
        resource_total = sum(world_state.get("resource_totals", {}).values())
        
        # Simple heuristic for carrying capacity
        theoretical_capacity = world_size * world_size * 0.1  # 10% of tiles can support 1 person
        resource_capacity = resource_total / max(population * 10, 1)  # 10 resources per person needed
        
        capacity_usage = population / min(theoretical_capacity, resource_capacity * 10)
        return min(1.0, capacity_usage)


class PerformanceMetrics:
    """Tracks simulation performance metrics"""
    
    def __init__(self):
        self.turn_times = deque(maxlen=100)  # Last 100 turn processing times
        self.llm_call_times = deque(maxlen=1000)  # Last 1000 LLM call times
        self.memory_usage = deque(maxlen=100)  # Memory usage samples
    
    def record_turn_time(self, duration: float):
        """Record time taken to process a turn"""
        self.turn_times.append(duration)
    
    def record_llm_call_time(self, duration: float):
        """Record time taken for an LLM call"""
        self.llm_call_times.append(duration)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            "average_turn_time": statistics.mean(self.turn_times) if self.turn_times else 0,
            "turn_time_std": statistics.stdev(self.turn_times) if len(self.turn_times) > 1 else 0,
            "average_llm_time": statistics.mean(self.llm_call_times) if self.llm_call_times else 0,
            "llm_time_std": statistics.stdev(self.llm_call_times) if len(self.llm_call_times) > 1 else 0,
            "turns_processed": len(self.turn_times),
            "llm_calls_made": len(self.llm_call_times)
        }


class EmergentBehaviorDetector:
    """Detects emergent behaviors and patterns"""
    
    def __init__(self):
        self.behavior_patterns = []
        self.pattern_history = deque(maxlen=1000)
    
    def analyze_emergent_behaviors(self, agents: List[AgentState], 
                                 interactions: List[InteractionResult],
                                 world_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze for emergent behaviors"""
        
        behaviors = {
            "clustering_detected": self._detect_spatial_clustering(agents),
            "specialization_emergence": self._detect_specialization_emergence(agents),
            "trade_networks": self._detect_trade_networks(interactions),
            "social_hierarchies": self._detect_social_hierarchies(agents),
            "cultural_patterns": self._detect_cultural_patterns(agents),
            "collective_behaviors": self._detect_collective_behaviors(agents, world_state)
        }
        
        return behaviors
    
    def _detect_spatial_clustering(self, agents: List[AgentState]) -> bool:
        """Detect if agents are clustering spatially"""
        if len(agents) < 5:
            return False
        
        positions = [agent.position for agent in agents]
        
        # Calculate average distance to nearest neighbors
        distances = []
        for i, pos1 in enumerate(positions):
            min_dist = float('inf')
            for j, pos2 in enumerate(positions):
                if i != j:
                    dist = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
                    min_dist = min(min_dist, dist)
            distances.append(min_dist)
        
        avg_distance = statistics.mean(distances)
        
        # Compare to random distribution
        # In random distribution, average nearest neighbor distance would be higher
        world_size = 64  # Should get from config
        expected_random_distance = 0.5 * (world_size / math.sqrt(len(agents)))
        
        return avg_distance < expected_random_distance * 0.7  # Clustering if 30% closer than random
    
    def _detect_specialization_emergence(self, agents: List[AgentState]) -> bool:
        """Detect if specialization is emerging"""
        if len(agents) < 3:
            return False
        
        # Check if different agents are developing different primary skills
        primary_skills = []
        for agent in agents:
            if agent.skills:
                best_skill = max(agent.skills.items(), key=lambda x: x[1].level)
                primary_skills.append(best_skill[0])
        
        # Specialization if we have at least 3 different primary skills
        unique_specializations = len(set(primary_skills))
        return unique_specializations >= min(3, len(agents) // 2)
    
    def _detect_trade_networks(self, interactions: List[InteractionResult]) -> bool:
        """Detect if trade networks are forming"""
        # Look for repeated trading partners
        trade_pairs = defaultdict(int)
        
        for interaction in interactions:
            if (hasattr(interaction, 'interaction_type') and 
                interaction.interaction_type == InteractionType.TRADE):
                # Would need to extract agent IDs from interaction
                pass  # Simplified for now
        
        return len(trade_pairs) > 2  # Multiple trading relationships
    
    def _detect_social_hierarchies(self, agents: List[AgentState]) -> bool:
        """Detect if social hierarchies are forming"""
        if len(agents) < 4:
            return False
        
        # Look for agents with significantly more positive relationships
        relationship_counts = []
        for agent in agents:
            positive_rels = sum(1 for rel in agent.relationships.values() if rel.strength > 10)
            relationship_counts.append(positive_rels)
        
        if not relationship_counts:
            return False
        
        max_rels = max(relationship_counts)
        avg_rels = statistics.mean(relationship_counts)
        
        # Hierarchy if top agent has significantly more relationships
        return max_rels > avg_rels * 2
    
    def _detect_cultural_patterns(self, agents: List[AgentState]) -> bool:
        """Detect if cultural patterns are emerging"""
        # Look for shared memories or behaviors
        # This would need more sophisticated analysis
        return False  # Simplified for now
    
    def _detect_collective_behaviors(self, agents: List[AgentState], 
                                   world_state: Dict[str, Any]) -> bool:
        """Detect collective behaviors like migration, cooperation"""
        # Look for coordinated movements or actions
        # This would need historical tracking
        return False  # Simplified for now


class SimulationAnalytics:
    """Main analytics controller"""
    
    def __init__(self):
        self.metric_history: List[MetricSnapshot] = []
        self.performance_metrics = PerformanceMetrics()
        self.emergent_detector = EmergentBehaviorDetector()
        self.trend_analyses: Dict[str, TrendAnalysis] = {}
        self.alerts: List[str] = []
    
    def collect_metrics(self, turn: int, agents: List[AgentState], 
                       interactions: List[InteractionResult],
                       world_state: Dict[str, Any],
                       active_events: List[ActiveEvent]) -> MetricSnapshot:
        """Collect all metrics for current turn"""
        
        snapshot = MetricSnapshot(
            turn=turn,
            timestamp=time.time(),
            population_metrics=PopulationMetrics.calculate(agents, turn),
            economic_metrics=EconomicMetrics.calculate(agents, interactions),
            social_metrics=SocialMetrics.calculate(agents, interactions),
            technology_metrics=TechnologyMetrics.calculate(agents),
            environment_metrics=EnvironmentMetrics.calculate(world_state, active_events),
            performance_metrics=self.performance_metrics.get_metrics(),
            emergent_metrics=self.emergent_detector.analyze_emergent_behaviors(agents, interactions, world_state)
        )
        
        # Calculate population change if we have history
        if self.metric_history:
            prev_pop = self.metric_history[-1].population_metrics.get("total_population", 0)
            current_pop = snapshot.population_metrics.get("total_population", 0)
            snapshot.population_metrics["population_change"] = current_pop - prev_pop
        
        self.metric_history.append(snapshot)
        
        # Limit history size
        if len(self.metric_history) > 1000:
            self.metric_history = self.metric_history[-1000:]
        
        # Update trend analyses
        self._update_trend_analyses()
        
        # Check for alerts
        self._check_alerts(snapshot)
        
        return snapshot
    
    def _update_trend_analyses(self):
        """Update trend analyses for key metrics"""
        if len(self.metric_history) < 5:
            return
        
        # Analyze trends for key metrics
        key_metrics = [
            ("population", "total_population"),
            ("wealth", "total_wealth"),
            ("social_cohesion", "social_cohesion"),
            ("technology_level", "technology_level"),
            ("environmental_stress", "environmental_stress")
        ]
        
        for metric_name, metric_path in key_metrics:
            values = []
            for snapshot in self.metric_history[-20:]:  # Last 20 turns
                value = self._extract_metric_value(snapshot, metric_path)
                if value is not None:
                    values.append(value)
            
            if len(values) >= 3:
                trend = self._analyze_trend(metric_name, values)
                self.trend_analyses[metric_name] = trend
    
    def _extract_metric_value(self, snapshot: MetricSnapshot, metric_path: str) -> Optional[float]:
        """Extract metric value from snapshot"""
        # Simplified extraction - in real implementation would be more sophisticated
        if metric_path == "total_population":
            return snapshot.population_metrics.get("total_population")
        elif metric_path == "total_wealth":
            return snapshot.economic_metrics.get("total_wealth")
        elif metric_path == "social_cohesion":
            return snapshot.social_metrics.get("social_cohesion")
        elif metric_path == "technology_level":
            return snapshot.technology_metrics.get("technology_level")
        elif metric_path == "environmental_stress":
            return snapshot.environment_metrics.get("environmental_stress")
        return None
    
    def _analyze_trend(self, metric_name: str, values: List[float]) -> TrendAnalysis:
        """Analyze trend in metric values"""
        if len(values) < 3:
            return TrendAnalysis(metric_name, values, "stable", 0.0, 0.0, 0.0)
        
        # Calculate trend direction and strength
        # Simple linear regression slope
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = statistics.mean(values)
        
        numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Determine trend direction
        if abs(slope) < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # Calculate volatility
        if len(values) > 1:
            volatility = statistics.stdev(values) / max(abs(statistics.mean(values)), 1)
        else:
            volatility = 0
        
        if volatility > 0.5:
            direction = "volatile"
        
        trend_strength = min(1.0, abs(slope) / max(abs(y_mean), 1))
        
        return TrendAnalysis(
            metric_name=metric_name,
            values=values,
            trend_direction=direction,
            trend_strength=trend_strength,
            rate_of_change=slope,
            volatility=volatility
        )
    
    def _check_alerts(self, snapshot: MetricSnapshot):
        """Check for alert conditions"""
        alerts = []
        
        # Population alerts
        pop = snapshot.population_metrics.get("total_population", 0)
        if pop == 0:
            alerts.append("CRITICAL: Population extinct!")
        elif pop < 5:
            alerts.append("WARNING: Population critically low")
        
        # Health alerts
        avg_health = snapshot.population_metrics.get("average_health", 100)
        if avg_health < 30:
            alerts.append("WARNING: Population health critical")
        
        # Social alerts
        cohesion = snapshot.social_metrics.get("social_cohesion", 0)
        if cohesion < 0.2:
            alerts.append("WARNING: Social cohesion breakdown")
        
        # Environmental alerts
        env_stress = snapshot.environment_metrics.get("environmental_stress", 0)
        if env_stress > 10:
            alerts.append("WARNING: High environmental stress")
        
        self.alerts.extend(alerts)
        
        # Keep only recent alerts
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Get comprehensive summary report"""
        if not self.metric_history:
            return {"error": "No metrics collected yet"}
        
        latest = self.metric_history[-1]
        
        return {
            "current_turn": latest.turn,
            "population_summary": latest.population_metrics,
            "economic_summary": latest.economic_metrics,
            "social_summary": latest.social_metrics,
            "technology_summary": latest.technology_metrics,
            "environment_summary": latest.environment_metrics,
            "emergent_behaviors": latest.emergent_metrics,
            "trends": {name: {"direction": trend.trend_direction, 
                             "strength": trend.trend_strength}
                      for name, trend in self.trend_analyses.items()},
            "recent_alerts": self.alerts[-10:],
            "performance": latest.performance_metrics
        }
    
    def export_data(self, filename: str):
        """Export metrics data to JSON file"""
        data = {
            "metrics_history": [asdict(snapshot) for snapshot in self.metric_history],
            "trend_analyses": {name: asdict(trend) for name, trend in self.trend_analyses.items()},
            "alerts": self.alerts
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Analytics data exported to {filename}")
    
    def get_metric_history(self, metric_name: str, limit: int = 100) -> List[float]:
        """Get history of a specific metric"""
        values = []
        for snapshot in self.metric_history[-limit:]:
            value = self._extract_metric_value(snapshot, metric_name)
            if value is not None:
                values.append(value)
        return values