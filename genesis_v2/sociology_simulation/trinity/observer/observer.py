"""
Trinity Observer - The omniscient system that monitors all agent behaviors.

This system observes agent actions, interactions, and patterns to understand
the emerging social complexity and provide insights for skill generation.
"""

import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, Counter
import networkx as nx

from loguru import logger


@dataclass
class BehaviorPattern:
    """Represents a detected behavioral pattern"""
    pattern_id: str
    pattern_type: str  # 'individual', 'social', 'collective', 'resource_usage', 'movement'
    description: str
    frequency: int
    agents_involved: List[str]
    context: Dict[str, Any]
    confidence: float  # 0-1 confidence score
    first_observed: int  # simulation turn
    last_observed: int  # simulation turn
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type,
            'description': self.description,
            'frequency': self.frequency,
            'agents_involved': self.agents_involved,
            'context': self.context,
            'confidence': self.confidence,
            'first_observed': self.first_observed,
            'last_observed': self.last_observed
        }


@dataclass
class SocialNetworkMetrics:
    """Social network analysis metrics"""
    clustering_coefficient: float
    average_path_length: float
    network_density: float
    central_agents: List[str]
    isolated_agents: List[str]
    communities: List[List[str]]


class TrinityObserver:
    """
    The Trinity Observer monitors all agent behaviors and extracts patterns.
    
    This system acts as the collective consciousness that observes and learns
    from agent interactions to guide the evolution of the simulation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.observation_interval = config.get('observation_interval', 10)
        self.behavior_log: List[Dict[str, Any]] = []
        self.detected_patterns: List[BehaviorPattern] = []
        self.social_network = nx.Graph()
        self.resource_usage_history = defaultdict(list)
        self.movement_patterns = defaultdict(list)
        self.interaction_history = defaultdict(list)
        
        # Analysis thresholds
        self.pattern_threshold = config.get('pattern_threshold', 3)
        self.confidence_threshold = config.get('confidence_threshold', 0.7)
        
    def observe_agent_action(self, turn: int, agent_id: str, action: Dict[str, Any], 
                           context: Dict[str, Any]):
        """Record an agent's action for pattern analysis"""
        observation = {
            'turn': turn,
            'agent_id': agent_id,
            'action_type': action.get('type', 'unknown'),
            'action_details': action,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        self.behavior_log.append(observation)
        
        # Update social network if interaction
        if action.get('type') == 'interact' and 'target_agent' in action:
            self._update_social_network(agent_id, action['target_agent'], action)
            
        # Track resource usage
        if action.get('type') in ['gather', 'consume', 'craft']:
            self._track_resource_usage(agent_id, action, turn)
            
        # Track movement
        if action.get('type') == 'move':
            self._track_movement(agent_id, action.get('from_position'), 
                               action.get('to_position'), turn)
    
    def _update_social_network(self, agent1: str, agent2: str, action: Dict[str, Any]):
        """Update the social network graph with new interaction"""
        # Add edge if not exists, or update weight
        if self.social_network.has_edge(agent1, agent2):
            self.social_network[agent1][agent2]['weight'] += 1
        else:
            self.social_network.add_edge(agent1, agent2, weight=1, 
                                       interaction_type=action.get('interaction_type', 'general'))
        
        # Record interaction
        self.interaction_history[(agent1, agent2)].append({
            'turn': len(self.behavior_log),
            'action': action,
            'intensity': action.get('intensity', 1.0)
        })
    
    def _track_resource_usage(self, agent_id: str, action: Dict[str, Any], turn: int):
        """Track how agents use resources"""
        resource_info = {
            'turn': turn,
            'agent_id': agent_id,
            'resource_type': action.get('resource_type', 'unknown'),
            'amount': action.get('amount', 0),
            'action_type': action.get('type', 'unknown')
        }
        
        self.resource_usage_history[agent_id].append(resource_info)
    
    def _track_movement(self, agent_id: str, from_pos: Tuple[int, int], 
                       to_pos: Tuple[int, int], turn: int):
        """Track agent movement patterns"""
        movement_info = {
            'turn': turn,
            'from': from_pos,
            'to': to_pos,
            'distance': abs(to_pos[0] - from_pos[0]) + abs(to_pos[1] - from_pos[1])
        }
        
        self.movement_patterns[agent_id].append(movement_info)
    
    def analyze_patterns(self, turn: int) -> List[BehaviorPattern]:
        """Analyze collected data to detect behavioral patterns"""
        new_patterns = []
        
        # Analyze individual behavior patterns
        new_patterns.extend(self._analyze_individual_patterns(turn))
        
        # Analyze social patterns
        new_patterns.extend(self._analyze_social_patterns(turn))
        
        # Analyze collective patterns
        new_patterns.extend(self._analyze_collective_patterns(turn))
        
        # Analyze resource usage patterns
        new_patterns.extend(self._analyze_resource_patterns(turn))
        
        # Analyze movement patterns
        new_patterns.extend(self._analyze_movement_patterns(turn))
        
        # Filter and merge patterns
        filtered_patterns = self._filter_patterns(new_patterns)
        
        # Update detected patterns
        self.detected_patterns.extend(filtered_patterns)
        
        return filtered_patterns
    
    def _analyze_individual_patterns(self, turn: int) -> List[BehaviorPattern]:
        """Analyze individual agent behavior patterns"""
        patterns = []
        
        # Group actions by agent
        agent_actions = defaultdict(list)
        for obs in self.behavior_log[-100:]:  # Last 100 observations
            agent_actions[obs['agent_id']].append(obs)
        
        for agent_id, actions in agent_actions.items():
            if len(actions) >= self.pattern_threshold:
                # Analyze action sequences
                action_types = [a['action_type'] for a in actions]
                action_counts = Counter(action_types)
                
                # Detect repetitive patterns
                for action_type, count in action_counts.items():
                    if count >= self.pattern_threshold:
                        pattern = BehaviorPattern(
                            pattern_id=f"individual_{agent_id}_{action_type}_{turn}",
                            pattern_type="individual",
                            description=f"Agent {agent_id} repeatedly performs {action_type}",
                            frequency=count,
                            agents_involved=[agent_id],
                            context={"action_type": action_type, "ratio": count/len(actions)},
                            confidence=min(1.0, count/len(actions)),
                            first_observed=actions[0]['turn'],
                            last_observed=actions[-1]['turn']
                        )
                        patterns.append(pattern)
        
        return patterns
    
    def _analyze_social_patterns(self, turn: int) -> List[BehaviorPattern]:
        """Analyze social interaction patterns"""
        patterns = []
        
        # Calculate social network metrics
        if len(self.social_network.nodes()) >= 2:
            metrics = self._calculate_social_metrics()
            
            # Detect social clustering
            if metrics.clustering_coefficient > 0.5:
                pattern = BehaviorPattern(
                    pattern_id=f"social_clustering_{turn}",
                    pattern_type="social",
                    description="Agents are forming tight-knit social clusters",
                    frequency=int(metrics.clustering_coefficient * 100),
                    agents_involved=metrics.central_agents,
                    context={"clustering_coefficient": metrics.clustering_coefficient},
                    confidence=metrics.clustering_coefficient,
                    first_observed=turn - 10,
                    last_observed=turn
                )
                patterns.append(pattern)
            
            # Detect isolated agents
            if len(metrics.isolated_agents) > 0:
                pattern = BehaviorPattern(
                    pattern_id=f"isolated_agents_{turn}",
                    pattern_type="social",
                    description=f"{len(metrics.isolated_agents)} agents are socially isolated",
                    frequency=len(metrics.isolated_agents),
                    agents_involved=metrics.isolated_agents,
                    context={"isolation_ratio": len(metrics.isolated_agents)/len(self.social_network.nodes())},
                    confidence=0.8,
                    first_observed=turn - 10,
                    last_observed=turn
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_collective_patterns(self, turn: int) -> List[BehaviorPattern]:
        """Analyze collective behavior patterns across agents"""
        patterns = []
        
        # Analyze synchronized behaviors
        recent_actions = [obs for obs in self.behavior_log[-50:] 
                         if obs['turn'] >= turn - 5]
        
        if len(recent_actions) >= self.pattern_threshold:
            action_types = [obs['action_type'] for obs in recent_actions]
            action_counts = Counter(action_types)
            
            # Find most common action
            if action_counts:
                most_common_action, count = action_counts.most_common(1)[0]
                
                # Calculate synchronization ratio
                total_agents = len(set(obs['agent_id'] for obs in recent_actions))
                sync_ratio = count / total_agents if total_agents > 0 else 0
                
                if sync_ratio > 0.3:  # 30% of agents doing same action
                    pattern = BehaviorPattern(
                        pattern_id=f"collective_sync_{most_common_action}_{turn}",
                        pattern_type="collective",
                        description=f"Collective synchronization: {most_common_action}",
                        frequency=count,
                        agents_involved=list(set(obs['agent_id'] for obs in recent_actions 
                                               if obs['action_type'] == most_common_action)),
                        context={"sync_ratio": sync_ratio, "action": most_common_action},
                        confidence=sync_ratio,
                        first_observed=recent_actions[0]['turn'],
                        last_observed=recent_actions[-1]['turn']
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_resource_patterns(self, turn: int) -> List[BehaviorPattern]:
        """Analyze resource usage and sharing patterns"""
        patterns = []
        
        # Analyze resource usage by multiple agents
        resource_usage = defaultdict(lambda: defaultdict(int))
        
        for agent_id, usage_list in self.resource_usage_history.items():
            for usage in usage_list[-20:]:  # Recent usage
                if usage['turn'] >= turn - 10:
                    resource_usage[usage['resource_type']][agent_id] += usage['amount']
        
        # Detect resource competition
        for resource_type, agent_usage in resource_usage.items():
            if len(agent_usage) >= self.pattern_threshold:
                total_usage = sum(agent_usage.values())
                
                pattern = BehaviorPattern(
                    pattern_id=f"resource_competition_{resource_type}_{turn}",
                    pattern_type="resource_usage",
                    description=f"Multiple agents competing for {resource_type}",
                    frequency=len(agent_usage),
                    agents_involved=list(agent_usage.keys()),
                    context={"resource_type": resource_type, "total_usage": total_usage},
                    confidence=min(1.0, len(agent_usage)/5),
                    first_observed=turn - 10,
                    last_observed=turn
                )
                patterns.append(pattern)
        
        return patterns
    
    def _analyze_movement_patterns(self, turn: int) -> List[BehaviorPattern]:
        """Analyze agent movement patterns"""
        patterns = []
        
        # Analyze collective movement
        recent_movements = []
        for agent_id, movements in self.movement_patterns.items():
            recent = [m for m in movements[-10:] if m['turn'] >= turn - 5]
            recent_movements.extend(recent)
        
        if len(recent_movements) >= self.pattern_threshold:
            # Calculate movement vectors
            destinations = [m['to'] for m in recent_movements]
            
            # Detect if agents are moving toward similar areas
            if destinations:
                # Simple clustering of destinations
                unique_dests = list(set(destinations))
                if len(unique_dests) < len(destinations) * 0.5:  # High clustering
                    pattern = BehaviorPattern(
                        pattern_id=f"collective_movement_{turn}",
                        pattern_type="movement",
                        description="Agents are moving toward similar destinations",
                        frequency=len(recent_movements),
                        agents_involved=list(set(m['agent_id'] for m in recent_movements)),
                        context={"unique_destinations": len(unique_dests), "total_movements": len(destinations)},
                        confidence=0.7,
                        first_observed=turn - 5,
                        last_observed=turn
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _calculate_social_metrics(self) -> SocialNetworkMetrics:
        """Calculate social network analysis metrics"""
        G = self.social_network
        
        try:
            clustering = nx.average_clustering(G) if G.number_of_edges() > 0 else 0.0
            avg_path_length = nx.average_shortest_path_length(G) if nx.is_connected(G) else float('inf')
            density = nx.density(G)
            
            # Find central agents (high degree)
            degrees = dict(G.degree())
            central_agents = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:3]
            central_agents = [agent[0] for agent in central_agents]
            
            # Find isolated agents (degree 0)
            isolated_agents = [node for node in G.nodes() if G.degree(node) == 0]
            
            # Detect communities
            communities = list(nx.community.greedy_modularity_communities(G)) if G.number_of_edges() > 0 else []
            communities = [list(community) for community in communities]
            
            return SocialNetworkMetrics(
                clustering_coefficient=clustering,
                average_path_length=avg_path_length,
                network_density=density,
                central_agents=central_agents,
                isolated_agents=isolated_agents,
                communities=communities
            )
        except Exception as e:
            logger.warning(f"Error calculating social metrics: {e}")
            return SocialNetworkMetrics(0.0, float('inf'), 0.0, [], [], [])
    
    def _filter_patterns(self, patterns: List[BehaviorPattern]) -> List[BehaviorPattern]:
        """Filter and deduplicate patterns"""
        filtered = []
        
        # Group by pattern type and description
        pattern_groups = defaultdict(list)
        for pattern in patterns:
            key = (pattern.pattern_type, pattern.description)
            pattern_groups[key].append(pattern)
        
        # Keep highest confidence pattern from each group
        for group_patterns in pattern_groups.values():
            best_pattern = max(group_patterns, key=lambda p: p.confidence)
            if best_pattern.confidence >= self.confidence_threshold:
                filtered.append(best_pattern)
        
        return filtered
    
    def get_behavior_summary(self, turn: int) -> Dict[str, Any]:
        """Get comprehensive behavior summary for Trinity system"""
        recent_patterns = [p for p in self.detected_patterns 
                          if p.last_observed >= turn - 50]
        
        return {
            'total_observations': len(self.behavior_log),
            'detected_patterns': len(recent_patterns),
            'pattern_types': list(set(p.pattern_type for p in recent_patterns)),
            'social_network': {
                'total_agents': len(self.social_network.nodes()),
                'total_interactions': len(self.social_network.edges()),
                'avg_clustering': nx.average_clustering(self.social_network) if self.social_network.number_of_edges() > 0 else 0.0
            },
            'resource_usage': dict(self.resource_usage_history),
            'recent_patterns': [p.to_dict() for p in recent_patterns[-10:]]
        }
    
    def reset_observations(self):
        """Reset observations (for testing purposes)"""
        self.behavior_log.clear()
        self.detected_patterns.clear()
        self.social_network.clear()
        self.resource_usage_history.clear()
        self.movement_patterns.clear()
        self.interaction_history.clear()