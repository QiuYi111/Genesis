"""Economic and political systems"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from loguru import logger
import random

if TYPE_CHECKING:
    from .agent import Agent
    from .world import World
    from .social_structures import Group

@dataclass
class Market:
    """Represents a trading market or post"""
    market_id: str
    location: tuple  # (x, y)
    established_turn: int
    market_type: str  # "local", "regional", "specialized"
    active_traders: Set[int] = field(default_factory=set)
    trade_history: List[Dict] = field(default_factory=list)
    price_trends: Dict[str, List[float]] = field(default_factory=dict)  # resource -> price history
    specialization: Optional[str] = None  # What this market specializes in


@dataclass
class Economy:
    """Represents the overall economic state"""
    resource_values: Dict[str, float] = field(default_factory=dict)  # Base values
    supply_demand: Dict[str, Dict[str, int]] = field(default_factory=dict)  # resource -> {supply, demand}
    trade_volume: int = 0
    economic_health: float = 1.0  # Overall economic indicator
    specialization_bonuses: Dict[int, Dict[str, float]] = field(default_factory=dict)  # agent_id -> bonuses


@dataclass
class PoliticalEntity:
    """Represents a political organization"""
    entity_id: str
    name: str
    entity_type: str  # "council", "chiefdom", "tribe", "city_state"
    leader_id: Optional[int] = None
    members: Set[int] = field(default_factory=set)
    territory: Optional[Dict] = None  # {"center": [x,y], "radius": int}
    laws: List[str] = field(default_factory=list)
    established_turn: int = 0
    stability: float = 1.0
    resources: Dict[str, int] = field(default_factory=dict)  # Collected taxes/tributes


class EconomicSystem:
    """Manages economic activities and trade"""
    
    def __init__(self):
        self.economy = Economy()
        self.markets: Dict[str, Market] = {}
        self.trade_routes: List[tuple] = []  # (market1_id, market2_id)
        self.next_market_id = 1
        
        # Initialize basic resource values
        self._initialize_resource_values()
    
    def _initialize_resource_values(self):
        """Initialize basic resource values and supply/demand"""
        basic_resources = {
            "wood": 1.0,
            "stone": 1.2,
            "food": 1.5,
            "apple": 1.3,
            "fish": 1.8,
            "metal": 3.0,
            "tools": 5.0,
            "weapon": 8.0
        }
        
        self.economy.resource_values = basic_resources
        
        for resource in basic_resources:
            self.economy.supply_demand[resource] = {"supply": 0, "demand": 0}
    
    def calculate_resource_price(self, resource: str, location: tuple = None) -> float:
        """Calculate current price of a resource"""
        base_value = self.economy.resource_values.get(resource, 1.0)
        
        supply = self.economy.supply_demand[resource]["supply"]
        demand = self.economy.supply_demand[resource]["demand"]
        
        # Basic supply and demand economics
        if supply == 0:
            price_modifier = 2.0  # High price when no supply
        else:
            price_modifier = max(0.1, demand / supply)
        
        # Market location can affect prices (if near specialized markets)
        location_modifier = 1.0
        if location:
            for market in self.markets.values():
                distance = abs(market.location[0] - location[0]) + abs(market.location[1] - location[1])
                if distance <= 5 and market.specialization == resource:
                    location_modifier *= 0.8  # Cheaper near specialized markets
        
        return base_value * price_modifier * location_modifier
    
    def update_supply_demand(self, world: 'World'):
        """Update supply and demand based on agent inventories and needs"""
        # Reset supply and demand
        for resource in self.economy.supply_demand:
            self.economy.supply_demand[resource] = {"supply": 0, "demand": 0}
        
        for agent in world.agents:
            # Calculate supply (what agent has excess of)
            for resource, amount in agent.inventory.items():
                if amount > 2:  # Willing to trade if has more than 2
                    self.economy.supply_demand.setdefault(resource, {"supply": 0, "demand": 0})
                    self.economy.supply_demand[resource]["supply"] += amount - 2
            
            # Calculate demand (what agent needs)
            basic_needs = {"food": 3, "wood": 2, "tools": 1}
            for resource, needed in basic_needs.items():
                current = agent.inventory.get(resource, 0)
                if current < needed:
                    self.economy.supply_demand.setdefault(resource, {"supply": 0, "demand": 0})
                    self.economy.supply_demand[resource]["demand"] += needed - current
    
    def establish_market(self, location: tuple, turn: int, market_type: str = "local") -> Market:
        """Establish a new market at a location"""
        market_id = f"market_{self.next_market_id}"
        self.next_market_id += 1
        
        market = Market(
            market_id=market_id,
            location=location,
            established_turn=turn,
            market_type=market_type
        )
        
        self.markets[market_id] = market
        logger.success(f"New market established at {location}: {market_id}")
        
        return market
    
    def process_economic_activity(self, world: 'World', turn: int):
        """Process economic activities for the turn"""
        # Update supply and demand
        self.update_supply_demand(world)
        
        # Process agent specializations
        self._update_specializations(world)
        
        # Calculate economic health
        self._calculate_economic_health()
        
        # Suggest market establishment
        if turn % 10 == 0 and len(self.markets) < len(world.agents) // 5:
            self._suggest_market_locations(world, turn)
    
    def _update_specializations(self, world: 'World'):
        """Update agent economic specializations based on skills and behavior"""
        for agent in world.agents:
            specializations = {}
            
            # Skill-based specializations
            if hasattr(agent, 'skills'):
                for skill, data in agent.skills.items():
                    level = data.get("level", 1)
                    if level >= 4:  # High skill level
                        if skill == "crafting":
                            specializations["tools"] = level * 0.1
                            specializations["weapon"] = level * 0.1
                        elif skill == "survival":
                            specializations["food"] = level * 0.1
                            specializations["wood"] = level * 0.05
                        elif skill == "exploration":
                            specializations["rare_materials"] = level * 0.1
            
            # Inventory-based specializations (what they produce most)
            inventory_totals = {}
            for resource, amount in agent.inventory.items():
                if amount > 5:  # Significant amount
                    inventory_totals[resource] = amount
            
            if inventory_totals:
                main_resource = max(inventory_totals, key=inventory_totals.get)
                specializations[main_resource] = specializations.get(main_resource, 0) + 0.2
            
            self.economy.specialization_bonuses[agent.aid] = specializations
    
    def _calculate_economic_health(self):
        """Calculate overall economic health indicator"""
        # Based on trade volume, resource diversity, and market activity
        trade_factor = min(1.0, self.economy.trade_volume / 100)
        
        # Resource diversity
        active_resources = sum(1 for supply_info in self.economy.supply_demand.values() 
                             if supply_info["supply"] > 0 or supply_info["demand"] > 0)
        diversity_factor = min(1.0, active_resources / 10)
        
        # Market activity
        market_factor = min(1.0, len(self.markets) / 5)
        
        self.economy.economic_health = (trade_factor + diversity_factor + market_factor) / 3
    
    def _suggest_market_locations(self, world: 'World', turn: int):
        """Suggest locations for new markets based on agent concentrations"""
        # Find agent clusters
        agent_positions = [agent.pos for agent in world.agents]
        
        # Simple clustering: find areas with multiple agents
        clusters = {}
        for pos in agent_positions:
            cluster_key = (pos[0] // 5, pos[1] // 5)  # 5x5 grid clusters
            clusters[cluster_key] = clusters.get(cluster_key, 0) + 1
        
        # Find the best cluster for a new market
        best_cluster = max(clusters.items(), key=lambda x: x[1])
        if best_cluster[1] >= 3:  # At least 3 agents in the area
            center_x = best_cluster[0][0] * 5 + 2
            center_y = best_cluster[0][1] * 5 + 2
            
            # Check if there's already a market nearby
            for market in self.markets.values():
                distance = abs(market.location[0] - center_x) + abs(market.location[1] - center_y)
                if distance < 10:  # Too close to existing market
                    return
            
            # Establish new market
            self.establish_market((center_x, center_y), turn)


class PoliticalSystem:
    """Manages political entities and governance"""
    
    def __init__(self):
        self.political_entities: Dict[str, PoliticalEntity] = {}
        self.next_entity_id = 1
        
    def form_political_entity(self, founder_id: int, entity_type: str, 
                             name: str, turn: int, members: Set[int] = None) -> PoliticalEntity:
        """Form a new political entity"""
        entity_id = f"political_{self.next_entity_id}"
        self.next_entity_id += 1
        
        entity = PoliticalEntity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            leader_id=founder_id,
            established_turn=turn,
            members=members or {founder_id}
        )
        
        self.political_entities[entity_id] = entity
        logger.success(f"New political entity formed: {name} ({entity_type})")
        
        return entity
    
    def suggest_political_formations(self, world: 'World', turn: int) -> List[Dict]:
        """Suggest political entity formations based on social structures"""
        suggestions = []
        
        # Large groups might form councils
        for group in world.social_manager.groups.values():
            if (len(group.members) >= 8 and 
                group.group_type in ["tribe", "work_team"] and
                not any(group.leader_id in entity.members 
                       for entity in self.political_entities.values())):
                
                suggestions.append({
                    "type": "council",
                    "founder": group.leader_id,
                    "members": group.members,
                    "name": f"{group.name} Council",
                    "reason": "Large group governance"
                })
        
        # High leadership agents might form chiefdoms
        for agent in world.agents:
            if (agent.leadership_score > 80 and
                len(agent.social_connections) >= 10 and
                not any(agent.aid in entity.members 
                       for entity in self.political_entities.values())):
                
                # Find followers
                potential_followers = set()
                for conn_id, conn_data in agent.social_connections.items():
                    if conn_data["strength"] >= 7:  # Strong loyalty
                        potential_followers.add(conn_id)
                
                if len(potential_followers) >= 5:
                    suggestions.append({
                        "type": "chiefdom",
                        "founder": agent.aid,
                        "members": potential_followers | {agent.aid},
                        "name": f"{agent.name}'s Chiefdom",
                        "reason": "Strong leadership"
                    })
        
        return suggestions
    
    def process_political_activities(self, world: 'World', turn: int):
        """Process political activities and governance"""
        # Update entity stability
        for entity in self.political_entities.values():
            self._update_entity_stability(entity, world)
        
        # Process governance decisions
        if turn % 5 == 0:  # Every 5 turns
            for entity in self.political_entities.values():
                self._process_governance(entity, world, turn)
        
        # Suggest new political formations
        suggestions = self.suggest_political_formations(world, turn)
        for suggestion in suggestions:
            if random.random() < 0.2:  # 20% chance to form
                self.form_political_entity(
                    suggestion["founder"],
                    suggestion["type"],
                    suggestion["name"],
                    turn,
                    suggestion["members"]
                )
    
    def _update_entity_stability(self, entity: PoliticalEntity, world: 'World'):
        """Update political entity stability"""
        agents_dict = {agent.aid: agent for agent in world.agents}
        
        # Check member satisfaction
        member_satisfaction = []
        for member_id in list(entity.members):
            agent = agents_dict.get(member_id)
            if not agent:
                entity.members.remove(member_id)
                continue
            
            satisfaction = 0.5  # Base satisfaction
            
            # Health and survival affect satisfaction
            if agent.health > 70:
                satisfaction += 0.2
            if agent.hunger < 50:
                satisfaction += 0.2
            
            # Leader relationship affects satisfaction
            if (entity.leader_id and entity.leader_id in agent.social_connections):
                leader_relationship = agent.social_connections[entity.leader_id]["strength"]
                satisfaction += leader_relationship * 0.02
            
            member_satisfaction.append(satisfaction)
        
        if member_satisfaction:
            avg_satisfaction = sum(member_satisfaction) / len(member_satisfaction)
            entity.stability = entity.stability * 0.8 + avg_satisfaction * 0.2
            
            # Dissolve if too unstable
            if entity.stability < 0.3:
                logger.warning(f"Political entity {entity.name} dissolved due to instability")
                del self.political_entities[entity.entity_id]
    
    def _process_governance(self, entity: PoliticalEntity, world: 'World', turn: int):
        """Process governance decisions and actions"""
        agents_dict = {agent.aid: agent for agent in world.agents}
        leader = agents_dict.get(entity.leader_id)
        
        if not leader:
            return
        
        # Collect "taxes" or tributes
        if entity.entity_type in ["chiefdom", "city_state"]:
            for member_id in entity.members:
                member = agents_dict.get(member_id)
                if member and member_id != entity.leader_id:
                    # Small tribute
                    for resource in ["wood", "food", "stone"]:
                        if member.inventory.get(resource, 0) > 3:
                            tribute = 1
                            member.inventory[resource] -= tribute
                            entity.resources[resource] = entity.resources.get(resource, 0) + tribute
        
        # Redistribute resources in emergencies
        total_resources = sum(entity.resources.values())
        if total_resources > 10:
            # Find members in need
            for member_id in entity.members:
                member = agents_dict.get(member_id)
                if member and member.health < 50:
                    # Provide aid
                    if entity.resources.get("food", 0) > 0:
                        entity.resources["food"] -= 1
                        member.inventory["food"] = member.inventory.get("food", 0) + 1
                        member.log.append(f"从{entity.name}获得了紧急食物援助")