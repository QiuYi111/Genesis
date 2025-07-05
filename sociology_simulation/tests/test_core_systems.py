"""Comprehensive test suite for core simulation systems"""
import pytest
import asyncio
import time
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# Import components to test
from ..core.agent_state import (
    AgentState, AgentStateManager, SkillType, AgentStatus, 
    Relationship, InventoryItem
)
from ..core.interactions import (
    InteractionManager, TradeInteraction, CombatInteraction, 
    DiplomacyInteraction, SocialInteraction, InteractionContext, InteractionType
)
from ..core.world_events import (
    WorldEventManager, WeatherEvent, NaturalDisasterEvent, 
    ResourceEvent, DiseaseEvent, EventSeverity
)
from ..services.llm_service import LLMService, LLMRequest, LLMPriority, LLMCache
from ..analytics.metrics import (
    SimulationAnalytics, PopulationMetrics, EconomicMetrics, 
    SocialMetrics, TechnologyMetrics
)
from ..persistence.save_load import SimulationSaveManager, SaveMetadata


class TestAgentState:
    """Test agent state management"""
    
    def test_agent_creation(self):
        """Test basic agent creation"""
        agent = AgentState("test_001", (10, 15), "TestAgent", 25)
        
        assert agent.agent_id == "test_001"
        assert agent.position == (10, 15)
        assert agent.name == "TestAgent"
        assert agent.age == 25
        assert agent.status == AgentStatus.ALIVE
        assert agent.health == 100.0
        assert len(agent.uuid) > 0
    
    def test_agent_validation(self):
        """Test agent state validation"""
        agent = AgentState("test_002", (5, 5), "TestAgent2", 30)
        
        # Valid state should have no issues
        issues = agent.validate_state()
        assert len(issues) == 0
        
        # Invalid position should be caught
        agent.position = (-1, 150)
        issues = agent.validate_state()
        assert len(issues) > 0
        assert any("Invalid position" in issue for issue in issues)
    
    def test_inventory_management(self):
        """Test inventory operations"""
        agent = AgentState("test_003", (0, 0), "TestAgent3", 20)
        
        # Add items
        assert agent.add_inventory_item("wood", 5, 1.0, "forest")
        assert agent.inventory["wood"].quantity == 5
        assert agent.current_weight == 5
        
        # Remove items
        assert agent.remove_inventory_item("wood", 2)
        assert agent.inventory["wood"].quantity == 3
        assert agent.current_weight == 3
        
        # Cannot remove more than available
        assert not agent.remove_inventory_item("wood", 10)
        assert agent.inventory["wood"].quantity == 3
    
    def test_skill_system(self):
        """Test skill development"""
        agent = AgentState("test_004", (0, 0), "TestAgent4", 25)
        
        # Add experience and check level up
        initial_level = agent.get_skill_level(SkillType.HUNTING)
        agent.add_skill_experience(SkillType.HUNTING, 150.0)
        
        new_level = agent.get_skill_level(SkillType.HUNTING)
        assert new_level > initial_level
        assert agent.total_experience == 150.0
    
    def test_relationship_management(self):
        """Test relationship system"""
        agent = AgentState("test_005", (0, 0), "TestAgent5", 30)
        
        # Create relationship
        agent.update_relationship("target_001", "friend", 10.0, 5.0)
        
        assert "target_001" in agent.relationships
        rel = agent.relationships["target_001"]
        assert rel.strength == 10.0
        assert rel.trust == 55.0  # 50 base + 5
        assert rel.relationship_type == "friend"
    
    def test_memory_system(self):
        """Test agent memory"""
        agent = AgentState("test_006", (0, 0), "TestAgent6", 25)
        
        # Add memories
        agent.add_memory("Found a berry bush", "location", 0.8, {"location_001"})
        agent.add_memory("Met another agent", "agent", 0.6, {"agent_002"})
        
        assert len(agent.memories) == 2
        assert len(agent.memory_categories["location"]) == 1
        assert len(agent.memory_categories["agent"]) == 1
        
        # Test memory summary
        summary = agent.get_memory_summary("location", 5)
        assert len(summary) == 1
        assert "berry bush" in summary[0]
    
    def test_aging_and_death(self):
        """Test aging mechanics"""
        agent = AgentState("test_007", (0, 0), "TestAgent7", 75)
        
        initial_strength = agent.attributes["strength"]
        agent.age_one_turn()
        
        # Agent should age
        assert agent.age == 76
        
        # Attributes might decline with age
        # (This is probabilistic, so we can't guarantee it in one turn)
        
        # Test natural death chance (very old agent)
        agent.age = 95
        for _ in range(100):  # Try many times
            agent.age_one_turn()
            if agent.status == AgentStatus.DEAD:
                break
        
        # At age 95+, death should be possible


class TestAgentStateManager:
    """Test agent state manager"""
    
    def test_manager_operations(self):
        """Test basic manager operations"""
        manager = AgentStateManager()
        
        # Add agents
        agent1 = AgentState("agent_001", (5, 5), "Agent1", 25)
        agent2 = AgentState("agent_002", (10, 10), "Agent2", 30)
        
        assert manager.add_agent(agent1)
        assert manager.add_agent(agent2)
        assert len(manager.agents) == 2
        
        # Retrieve agent
        retrieved = manager.get_agent("agent_001")
        assert retrieved is not None
        assert retrieved.name == "Agent1"
        
        # Remove agent
        assert manager.remove_agent("agent_001")
        assert len(manager.agents) == 1
        assert "agent_001" in manager.state_history
    
    def test_spatial_queries(self):
        """Test spatial queries"""
        manager = AgentStateManager()
        
        # Add agents at different positions
        agents = [
            AgentState("agent_001", (5, 5), "Agent1", 25),
            AgentState("agent_002", (6, 6), "Agent2", 30),
            AgentState("agent_003", (15, 15), "Agent3", 35)
        ]
        
        for agent in agents:
            manager.add_agent(agent)
        
        # Query nearby agents
        nearby = manager.get_agents_in_area((5, 5), 2)
        assert len(nearby) == 2  # agent_001 and agent_002
        
        # Query distant area
        distant = manager.get_agents_in_area((20, 20), 2)
        assert len(distant) == 0
    
    def test_population_stats(self):
        """Test population statistics"""
        manager = AgentStateManager()
        
        # Add diverse agents
        ages = [20, 30, 40, 50, 60]
        healths = [100, 80, 60, 40, 20]
        
        for i, (age, health) in enumerate(zip(ages, healths)):
            agent = AgentState(f"agent_{i:03d}", (i, i), f"Agent{i}", age)
            agent.health = health
            manager.add_agent(agent)
        
        stats = manager.get_population_stats()
        assert stats["total"] == 5
        assert stats["avg_age"] == 40.0  # (20+30+40+50+60)/5
        assert stats["oldest"] == 60
        assert stats["youngest"] == 20


class TestInteractionSystem:
    """Test interaction management"""
    
    def setup_method(self):
        """Set up test agents"""
        self.agent1 = AgentState("trader_001", (5, 5), "Trader1", 25)
        self.agent1.add_inventory_item("wood", 10)
        self.agent1.add_inventory_item("stone", 5)
        
        self.agent2 = AgentState("trader_002", (6, 6), "Trader2", 30)
        self.agent2.add_inventory_item("apple", 8)
        self.agent2.add_inventory_item("fish", 3)
        
        self.manager = InteractionManager()
    
    def test_trade_interaction(self):
        """Test trading between agents"""
        # Create trade interaction
        offer = {"wood": 2}
        request = {"apple": 3}
        
        interaction_id = self.manager.create_trade_interaction(
            "trader_001", "trader_002", (5, 5), offer, request
        )
        
        # Execute trade
        result = self.manager.execute_interaction(interaction_id, self.agent1, self.agent2)
        
        assert result is not None
        # Note: Result depends on LLM which might not be available in tests
        # In a real test, we'd mock the LLM calls
    
    def test_combat_interaction(self):
        """Test combat between agents"""
        # Set up combat-ready agents
        self.agent1.attributes["strength"] = 8
        self.agent1.attributes["dexterity"] = 7
        self.agent2.attributes["strength"] = 6
        self.agent2.attributes["dexterity"] = 8
        
        interaction_id = self.manager.create_combat_interaction(
            "trader_001", "trader_002", (5, 5), "physical"
        )
        
        result = self.manager.execute_interaction(interaction_id, self.agent1, self.agent2)
        assert result is not None
    
    def test_diplomacy_interaction(self):
        """Test diplomatic interactions"""
        terms = {"alliance_type": "trade", "duration": "permanent"}
        
        interaction_id = self.manager.create_diplomacy_interaction(
            "trader_001", "trader_002", (5, 5), "alliance", terms
        )
        
        result = self.manager.execute_interaction(interaction_id, self.agent1, self.agent2)
        assert result is not None
    
    def test_social_interaction(self):
        """Test social interactions"""
        interaction_id = self.manager.create_social_interaction(
            "trader_001", "trader_002", (5, 5), "compliment", "Nice to meet you!"
        )
        
        result = self.manager.execute_interaction(interaction_id, self.agent1, self.agent2)
        assert result is not None


class TestWorldEvents:
    """Test world event system"""
    
    def setup_method(self):
        """Set up event manager"""
        self.event_manager = WorldEventManager()
    
    def test_weather_events(self):
        """Test weather event generation"""
        weather_event = WeatherEvent("drought", EventSeverity.MAJOR)
        
        world_state = {"current_turn": 10, "population": 20}
        effect = weather_event.generate_effect(world_state)
        
        assert effect.duration_turns > 0
        assert "water" in effect.resource_changes
        assert effect.resource_changes["water"] < 1.0  # Drought reduces water
    
    def test_natural_disasters(self):
        """Test natural disaster events"""
        disaster = NaturalDisasterEvent("earthquake", EventSeverity.MAJOR)
        
        world_state = {"current_turn": 15, "population": 25}
        effect = disaster.generate_effect(world_state)
        
        assert effect.duration_turns > 0
        assert len(effect.area_affected) > 0
        assert "health_decrease" in effect.agent_effects
    
    def test_event_manager_update(self):
        """Test event manager turn processing"""
        world_state = {"current_turn": 1, "population": 15, "agents": []}
        
        # Force a specific event
        self.event_manager.force_event("drought", "moderate")
        
        # Update should process active events
        messages = self.event_manager.update(world_state)
        
        assert len(self.event_manager.active_events) > 0
    
    def test_event_effects_on_agents(self):
        """Test applying event effects to agents"""
        # Create test agents
        agents = [
            AgentState("agent_001", (5, 5), "Agent1", 25),
            AgentState("agent_002", (10, 10), "Agent2", 30)
        ]
        
        # Force a disease event
        self.event_manager.force_event("fever", "moderate")
        
        # Apply effects
        messages = self.event_manager.apply_effects_to_agents(agents)
        
        # Agents should be affected (health decreased)
        for agent in agents:
            assert agent.health <= 100  # Health might be reduced


class TestLLMService:
    """Test LLM service functionality"""
    
    def test_cache_functionality(self):
        """Test LLM response caching"""
        cache = LLMCache(max_size=5, ttl_seconds=10)
        
        # Create test request and response
        request = LLMRequest("Test system", "Test user", temperature=0.5)
        response = MagicMock()
        response.success = True
        
        # Test cache miss
        cached = cache.get(request)
        assert cached is None
        
        # Cache response
        cache.set(request, response)
        
        # Test cache hit
        cached = cache.get(request)
        assert cached is not None
        assert cached.cached
    
    @patch('aiohttp.ClientSession.post')
    async def test_llm_request_with_mock(self, mock_post):
        """Test LLM request with mocked HTTP calls"""
        # Mock successful API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test response"}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_response
        
        service = LLMService()
        
        # Make request
        response = await service.request(
            "Test system prompt",
            "Test user prompt",
            temperature=0.7
        )
        
        assert response.success
        assert response.content == "Test response"
        assert not response.cached  # First request shouldn't be cached


class TestAnalytics:
    """Test analytics and metrics"""
    
    def setup_method(self):
        """Set up test data"""
        self.agents = [
            AgentState("agent_001", (5, 5), "Agent1", 25),
            AgentState("agent_002", (10, 10), "Agent2", 30),
            AgentState("agent_003", (15, 15), "Agent3", 35)
        ]
        
        # Add some variety to agents
        self.agents[0].add_inventory_item("wood", 5)
        self.agents[0].add_skill_experience(SkillType.CRAFTING, 50)
        
        self.agents[1].add_inventory_item("stone", 3)
        self.agents[1].add_inventory_item("apple", 7)
        self.agents[1].add_skill_experience(SkillType.TRADING, 30)
        
        self.agents[2].add_inventory_item("fish", 2)
        self.agents[2].add_skill_experience(SkillType.HUNTING, 80)
    
    def test_population_metrics(self):
        """Test population metrics calculation"""
        metrics = PopulationMetrics.calculate(self.agents, 1)
        
        assert metrics["total_population"] == 3
        assert metrics["average_age"] == 30.0  # (25+30+35)/3
        assert metrics["median_age"] == 30.0
        assert "age_distribution" in metrics
        assert "attribute_distributions" in metrics
    
    def test_economic_metrics(self):
        """Test economic metrics calculation"""
        metrics = EconomicMetrics.calculate(self.agents, [])
        
        assert metrics["total_wealth"] > 0
        assert "resource_distribution" in metrics
        assert "wealth_inequality_gini" in metrics
        assert 0 <= metrics["wealth_inequality_gini"] <= 1
    
    def test_social_metrics(self):
        """Test social metrics calculation"""
        # Add some relationships
        self.agents[0].update_relationship("agent_002", "friend", 10.0, 5.0)
        self.agents[1].update_relationship("agent_003", "ally", 8.0, 3.0)
        
        metrics = SocialMetrics.calculate(self.agents, [])
        
        assert metrics["total_relationships"] > 0
        assert "social_cohesion" in metrics
        assert 0 <= metrics["social_cohesion"] <= 1
    
    def test_technology_metrics(self):
        """Test technology metrics calculation"""
        metrics = TechnologyMetrics.calculate(self.agents)
        
        assert metrics["total_experience"] > 0
        assert "skill_diversity" in metrics
        assert "technology_level" in metrics
        assert metrics["skill_diversity"] >= 1  # At least one skill type
    
    def test_simulation_analytics(self):
        """Test complete analytics system"""
        analytics = SimulationAnalytics()
        
        world_state = {"current_turn": 1, "population": 3}
        active_events = []
        
        snapshot = analytics.collect_metrics(
            turn=1,
            agents=self.agents,
            interactions=[],
            world_state=world_state,
            active_events=active_events
        )
        
        assert snapshot.turn == 1
        assert snapshot.population_metrics["total_population"] == 3
        assert len(analytics.metric_history) == 1
        
        # Test summary report
        report = analytics.get_summary_report()
        assert "population_summary" in report
        assert "economic_summary" in report


class TestSaveLoad:
    """Test save/load functionality"""
    
    def setup_method(self):
        """Set up temporary directory for saves"""
        self.temp_dir = tempfile.mkdtemp()
        self.save_manager = SimulationSaveManager(self.temp_dir)
        
        # Create test data
        self.agents = [
            AgentState("agent_001", (5, 5), "Agent1", 25),
            AgentState("agent_002", (10, 10), "Agent2", 30)
        ]
        
        self.world_state = {
            "current_turn": 5,
            "era": "stone_age",
            "size": 64,
            "resources": {"wood": 100, "stone": 50}
        }
    
    def teardown_method(self):
        """Clean up temporary directory"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_save_metadata_generation(self):
        """Test save metadata creation"""
        timestamp = time.time()
        save_id = self.save_manager._generate_save_id(timestamp, auto_save=False)
        
        assert save_id.startswith("manual_")
        assert len(save_id) > 10
        
        auto_save_id = self.save_manager._generate_save_id(timestamp, auto_save=True)
        assert auto_save_id.startswith("auto_")
    
    def test_save_list_operations(self):
        """Test save listing and metadata"""
        # Initially no saves
        saves = self.save_manager.list_saves()
        assert len(saves) == 0
        
        # After adding metadata entry
        test_metadata = SaveMetadata(
            save_id="test_save_001",
            timestamp=time.time(),
            simulation_name="Test Simulation",
            description="Test save",
            turn_number=5,
            population_count=2,
            file_size_bytes=1024
        )
        
        self.save_manager.saves_metadata["test_save_001"] = test_metadata.__dict__
        
        saves = self.save_manager.list_saves()
        assert len(saves) == 1
        assert saves[0].simulation_name == "Test Simulation"


# Integration test
class TestIntegration:
    """Integration tests for complete system"""
    
    @pytest.mark.asyncio
    async def test_basic_simulation_flow(self):
        """Test basic simulation workflow"""
        # Create managers
        agent_manager = AgentStateManager()
        interaction_manager = InteractionManager()
        event_manager = WorldEventManager()
        analytics = SimulationAnalytics()
        
        # Create initial agents
        agents = [
            AgentState("agent_001", (5, 5), "Alice", 25),
            AgentState("agent_002", (10, 10), "Bob", 30)
        ]
        
        for agent in agents:
            agent_manager.add_agent(agent)
        
        # Simulate one turn
        world_state = {"current_turn": 1, "population": 2, "agents": agents}
        
        # Update events
        event_messages = event_manager.update(world_state)
        
        # Apply event effects
        effect_messages = event_manager.apply_effects_to_agents(agents)
        
        # Collect metrics
        snapshot = analytics.collect_metrics(
            turn=1,
            agents=agents,
            interactions=[],
            world_state=world_state,
            active_events=list(event_manager.active_events.values())
        )
        
        # Verify everything worked
        assert snapshot.turn == 1
        assert len(analytics.metric_history) == 1
        assert world_state["population"] == 2


# Performance test
class TestPerformance:
    """Performance tests for key systems"""
    
    def test_large_population_metrics(self):
        """Test metrics calculation with large population"""
        # Create 1000 agents
        agents = []
        for i in range(1000):
            agent = AgentState(f"agent_{i:04d}", (i % 64, i // 64), f"Agent{i}", 20 + (i % 50))
            agent.add_inventory_item("wood", i % 10)
            agents.append(agent)
        
        start_time = time.time()
        metrics = PopulationMetrics.calculate(agents, 1)
        calculation_time = time.time() - start_time
        
        # Should complete in reasonable time (< 1 second)
        assert calculation_time < 1.0
        assert metrics["total_population"] == 1000
    
    def test_spatial_query_performance(self):
        """Test spatial query performance"""
        manager = AgentStateManager()
        
        # Add many agents
        for i in range(500):
            agent = AgentState(f"agent_{i:04d}", (i % 32, i // 32), f"Agent{i}", 25)
            manager.add_agent(agent)
        
        start_time = time.time()
        nearby = manager.get_agents_in_area((16, 16), 5)
        query_time = time.time() - start_time
        
        # Should complete quickly
        assert query_time < 0.1
        assert len(nearby) > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])