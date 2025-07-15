"""
Mock LLM provider for testing and development.
Provides deterministic responses without making actual API calls.
"""

import random
import json
from typing import List, Dict, Any, Optional, Type, TypeVar
from .base import BaseLLMProvider, LLMResponse, ActionDecision, SocialInteraction, GoalSetting, CraftingDecision, BuildingDecision, PerceptionReport, TrinityReport

T = TypeVar('T')


class MockLLMProvider(BaseLLMProvider):
    """Mock provider that generates realistic responses for testing"""
    
    def __init__(self, **kwargs):
        super().__init__(model="mock-model", **kwargs)
        self.rng = random.Random(kwargs.get('seed', 42))
    
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Generate mock responses based on context"""
        
        # Extract the last message content
        last_message = messages[-1]["content"] if messages else ""
        
        # Determine response type based on context
        response_content = self._generate_mock_response(last_message)
        
        return LLMResponse(
            content=response_content,
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            latency=0.1 + self.rng.random() * 0.2,
            model=self.model,
            success=True
        )
    
    def _generate_mock_response(self, context: str) -> str:
        """Generate appropriate mock response based on context"""
        
        # Action decision context
        if "action" in context.lower() and "decide" in context.lower():
            actions = ["move", "gather", "explore", "rest", "socialize", "craft", "build"]
            action = self.rng.choice(actions)
            
            if action == "move":
                return json.dumps({
                    "action": "move",
                    "target_position": [self.rng.randint(-5, 5), self.rng.randint(-5, 5)],
                    "reasoning": f"Moving to explore new area and find {self.rng.choice(['food', 'water', 'resources'])}",
                    "urgency": self.rng.random(),
                    "expected_outcome": "Discover new resources or areas"
                })
            elif action == "gather":
                resources = ["food", "water", "wood", "stone"]
                return json.dumps({
                    "action": "gather",
                    "resource_target": self.rng.choice(resources),
                    "reasoning": f"Need to gather {self.rng.choice(resources)} for survival",
                    "urgency": 0.7 + self.rng.random() * 0.3,
                    "expected_outcome": f"Collect enough {self.rng.choice(resources)}"
                })
            else:
                return json.dumps({
                    "action": action,
                    "reasoning": f"Decided to {action} based on current needs",
                    "urgency": self.rng.random(),
                    "expected_outcome": f"Benefit from {action}"
                })
        
        # Social interaction context
        elif "social" in context.lower() or "interact" in context.lower():
            interaction_types = ["greet", "trade", "share", "cooperate"]
            return json.dumps({
                "interaction_type": self.rng.choice(interaction_types),
                "target_agent": f"agent_{self.rng.randint(1, 10)}",
                "message": f"Hello! Let's {self.rng.choice(['work together', 'trade items', 'share resources'])}",
                "offer_items": {"food": self.rng.randint(1, 3)} if self.rng.random() > 0.5 else {},
                "request_items": {"water": self.rng.randint(1, 2)} if self.rng.random() > 0.5 else {},
                "relationship_change": self.rng.uniform(-0.2, 0.8)
            })
        
        # Goal setting context
        elif "goal" in context.lower():
            goal_types = ["survival", "exploration", "social", "achievement"]
            return json.dumps({
                "goal_type": self.rng.choice(goal_types),
                "description": f"Focus on {self.rng.choice(['finding food', 'exploring new areas', 'building relationships', 'improving skills'])}",
                "priority": self.rng.random(),
                "expected_duration": self.rng.randint(5, 20),
                "target_resource": self.rng.choice(["food", "water", "wood", None]),
                "required_items": [self.rng.choice(["tool", "food", "water"])] if self.rng.random() > 0.5 else []
            })
        
        # Crafting context
        elif "craft" in context.lower():
            recipes = ["stone_axe", "wooden_shelter", "simple_tool", "campfire"]
            return json.dumps({
                "recipe_name": self.rng.choice(recipes),
                "required_materials": {
                    "stone": self.rng.randint(2, 5),
                    "wood": self.rng.randint(3, 8)
                },
                "expected_result": {"durability": self.rng.randint(50, 100), "efficiency": self.rng.uniform(0.5, 1.0)},
                "crafting_time": self.rng.randint(2, 5),
                "priority": self.rng.uniform(0.3, 0.9)
            })
        
        # Building context
        elif "build" in context.lower():
            building_types = ["shelter", "storage", "workshop", "social_area"]
            return json.dumps({
                "building_type": self.rng.choice(building_types),
                "target_position": [self.rng.randint(-3, 3), self.rng.randint(-3, 3)],
                "required_materials": {
                    "wood": self.rng.randint(5, 15),
                    "stone": self.rng.randint(3, 8)
                },
                "building_purpose": f"Create a {self.rng.choice(['safe space', 'resource storage', 'social gathering area'])}",
                "expected_benefit": f"{self.rng.choice(['protection', 'efficiency', 'social cohesion'])}"
            })
        
        # Perception context
        elif "perceive" in context.lower() or "observe" in context.lower():
            resources = ["food", "water", "wood", "stone"]
            return json.dumps({
                "visible_resources": {
                    res: [[self.rng.randint(-5, 5), self.rng.randint(-5, 5)] for _ in range(self.rng.randint(0, 3))]
                    for res in resources
                },
                "nearby_agents": [
                    {
                        "id": f"agent_{i}",
                        "position": [self.rng.randint(-10, 10), self.rng.randint(-10, 10)],
                        "relationship": self.rng.uniform(-0.5, 1.0)
                    }
                    for i in range(self.rng.randint(0, 3))
                ],
                "immediate_threats": ["predator", "hostile_agent"] if self.rng.random() < 0.1 else [],
                "opportunities": ["resource_rich_area", "friendly_agent"] if self.rng.random() < 0.3 else [],
                "current_terrain": self.rng.choice(["grassland", "forest", "mountain", "desert"]),
                "weather_conditions": {
                    "temperature": self.rng.randint(10, 30),
                    "humidity": self.rng.randint(20, 80)
                }
            })
        
        # Trinity context
        elif "trinity" in context.lower() or "observe" in context.lower():
            return json.dumps({
                "observed_behaviors": [
                    {
                        "agent_id": f"agent_{i}",
                        "behavior": self.rng.choice(["gathering", "socializing", "exploring", "building"]),
                        "frequency": self.rng.randint(1, 10),
                        "success_rate": self.rng.uniform(0.3, 1.0)
                    }
                    for i in range(self.rng.randint(2, 5))
                ],
                "patterns_detected": [
                    "group_formation", "resource_sharing", "skill_improvement"
                ] if self.rng.random() > 0.5 else ["individual_behavior"],
                "skill_suggestions": [
                    {
                        "skill_name": self.rng.choice(["advanced_gathering", "social_cooperation", "tool_crafting"]),
                        "trigger_condition": self.rng.choice(["high_resource_need", "social_interaction", "tool_usage"]),
                        "difficulty": self.rng.uniform(0.2, 0.8)
                    }
                ],
                "rule_proposals": [
                    {
                        "rule_type": self.rng.choice(["resource_sharing", "territory", "cooperation"]),
                        "description": f"New {self.rng.choice(['social', 'economic', 'territorial'])} rule",
                        "acceptance_threshold": self.rng.uniform(0.5, 0.9)
                    }
                ],
                "event_triggers": ["resource_scarcity", "population_growth"] if self.rng.random() > 0.7 else [],
                "age_progression_recommendations": [
                    "advance_to_bronze_age",
                    "develop_agriculture"
                ] if self.rng.random() > 0.8 else ["maintain_stone_age"]
            })
        
        # Default response
        else:
            return json.dumps({
                "response": "I understand the situation and will act accordingly",
                "confidence": self.rng.uniform(0.7, 1.0),
                "reasoning": "Based on my current knowledge and needs"
            })
    
    def _get_mock_response(self, response_schema: type[T]) -> T:
        """Override to provide schema-specific mock responses"""
        schema_name = response_schema.__name__
        
        if schema_name == "ActionDecision":
            return ActionDecision(
                action=self.rng.choice(["move", "gather", "explore", "rest"]),
                reasoning="Mock reasoning for action",
                urgency=self.rng.random(),
                expected_outcome="Expected positive outcome"
            )
        
        elif schema_name == "SocialInteraction":
            return SocialInteraction(
                interaction_type="greet",
                target_agent="mock_agent_1",
                message="Hello!",
                relationship_change=0.1
            )
        
        elif schema_name == "GoalSetting":
            return GoalSetting(
                goal_type="survival",
                description="Find food and water",
                priority=0.8,
                expected_duration=10
            )
        
        elif schema_name == "CraftingDecision":
            return CraftingDecision(
                recipe_name="stone_axe",
                required_materials={"stone": 3, "wood": 2},
                expected_result={"durability": 75, "efficiency": 0.8},
                crafting_time=3,
                priority=0.7
            )
        
        elif schema_name == "BuildingDecision":
            return BuildingDecision(
                building_type="shelter",
                target_position=(0, 0),
                required_materials={"wood": 10, "stone": 5},
                building_purpose="Create safe space",
                expected_benefit="Protection from elements"
            )
        
        elif schema_name == "PerceptionReport":
            return PerceptionReport(
                visible_resources={"food": [(1, 1)], "water": [(2, 2)]},
                nearby_agents=[{"id": "agent_1", "position": (3, 3), "relationship": 0.5}],
                current_terrain="grassland",
                weather_conditions={"temperature": 20, "humidity": 50}
            )
        
        elif schema_name == "TrinityReport":
            return TrinityReport(
                observed_behaviors=[{"agent_id": "agent_1", "behavior": "gathering", "frequency": 5}],
                patterns_detected=["resource_sharing"],
                skill_suggestions=[{"skill_name": "advanced_gathering", "trigger_condition": "high_resource_need", "difficulty": 0.5}],
                rule_proposals=[{"rule_type": "resource_sharing", "description": "Share excess resources", "acceptance_threshold": 0.7}]
            )
        
        else:
            # Generic mock for any schema
            return super()._get_mock_response(response_schema)


# Test the mock provider
if __name__ == "__main__":
    import asyncio
    
    async def test_mock_provider():
        provider = MockLLMProvider(seed=42)
        
        # Test action decision
        messages = [{"role": "user", "content": "Decide what action to take"}]
        response = await provider.generate_response(messages, ActionDecision)
        print("Action Decision:", response)
        
        # Test social interaction
        messages = [{"role": "user", "content": "Plan social interaction"}]
        response = await provider.generate_response(messages, SocialInteraction)
        print("Social Interaction:", response)
    
    asyncio.run(test_mock_provider())