"""
Base provider interface for LLM integration.
Defines the protocol for all LLM providers (DeepSeek, OpenAI, Mock, etc.).
"""

from typing import Protocol, TypeVar, Generic, Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
import json
import asyncio
import time
from dataclasses import dataclass


T = TypeVar('T', bound=BaseModel)


@dataclass
class LLMResponse:
    """Response wrapper for LLM calls"""
    content: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    latency: float  # seconds
    model: str
    success: bool
    error: Optional[str] = None


class LLMProvider(Protocol):
    """Protocol for LLM providers"""
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        response_schema: type[T],
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> T:
        """Generate structured response from LLM"""
        ...
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> str:
        """Generate free text response"""
        ...
    
    async def check_health(self) -> bool:
        """Check if provider is healthy"""
        ...


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, model: str, api_key: Optional[str] = None, **kwargs):
        self.model = model
        self.api_key = api_key
        self.kwargs = kwargs
        self._last_health_check = 0
    
    @abstractmethod
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Make actual API request - to be implemented by subclasses"""
        pass
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        response_schema: type[T],
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> T:
        """Generate structured response with schema validation"""
        try:
            response = await self._make_request(messages, temperature, max_tokens, **kwargs)
            
            if not response.success:
                raise Exception(f"LLM request failed: {response.error}")
            
            # Parse JSON response
            try:
                parsed = json.loads(response.content)
                return response_schema(**parsed)
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                raise Exception(f"Failed to parse response: {e}")
                
        except Exception as e:
            # Fallback to mock response if available
            if hasattr(self, '_get_mock_response'):
                return self._get_mock_response(response_schema)
            raise
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500,
        **kwargs
    ) -> str:
        """Generate free text response"""
        response = await self._make_request(messages, temperature, max_tokens, **kwargs)
        
        if not response.success:
            raise Exception(f"LLM request failed: {response.error}")
        
        return response.content
    
    async def check_health(self) -> bool:
        """Basic health check - can be overridden"""
        try:
            # Simple test prompt
            test_messages = [{"role": "user", "content": "Say 'hello'"}]
            response = await self.generate_text(test_messages, max_tokens=5)
            return "hello" in response.lower()
        except Exception:
            return False
    
    def _get_mock_response(self, response_schema: type[T]) -> T:
        """Generate mock response for testing"""
        # Create mock data based on schema
        mock_data = {}
        
        for field_name, field_info in response_schema.__fields__.items():
            field_type = field_info.type_
            
            if field_type == str:
                mock_data[field_name] = f"mock_{field_name}"
            elif field_type == int:
                mock_data[field_name] = 1
            elif field_type == float:
                mock_data[field_name] = 0.5
            elif field_type == bool:
                mock_data[field_name] = True
            elif hasattr(field_type, '__origin__') and field_type.__origin__ == list:
                mock_data[field_name] = []
            elif hasattr(field_type, '__origin__') and field_type.__origin__ == dict:
                mock_data[field_name] = {}
            else:
                mock_data[field_name] = None
        
        return response_schema(**mock_data)


# Response schemas for different types of agent decisions

class ActionDecision(BaseModel):
    """Schema for agent action decisions"""
    action: str = Field(description="The action to perform")
    target_position: Optional[Tuple[int, int]] = Field(None, description="Target position if movement is involved")
    target_agent: Optional[str] = Field(None, description="Target agent ID if interacting with another agent")
    resource_target: Optional[str] = Field(None, description="Target resource type if gathering")
    reasoning: str = Field(description="Detailed reasoning for this action")
    urgency: float = Field(ge=0.0, le=1.0, description="How urgent this action is")
    expected_outcome: str = Field(description="Expected outcome of this action")


class SocialInteraction(BaseModel):
    """Schema for social interactions"""
    interaction_type: str = Field(description="Type of interaction: greet, trade, share, conflict")
    target_agent: str = Field(description="ID of the target agent")
    message: str = Field(description="Message to send to the target agent")
    offer_items: Dict[str, float] = Field(default_factory=dict, description="Items to offer in trade")
    request_items: Dict[str, float] = Field(default_factory=dict, description="Items to request in trade")
    relationship_change: float = Field(ge=-1.0, le=1.0, description="Expected relationship change")


class GoalSetting(BaseModel):
    """Schema for goal setting decisions"""
    goal_type: str = Field(description="Type of goal: survival, exploration, social, achievement")
    description: str = Field(description="Detailed description of the goal")
    priority: float = Field(ge=0.0, le=1.0, description="Priority of this goal")
    expected_duration: int = Field(description="Expected duration in turns")
    target_resource: Optional[str] = Field(None, description="Target resource for gathering goals")
    target_position: Optional[Tuple[int, int]] = Field(None, description="Target position for movement goals")
    required_items: List[str] = Field(default_factory=list, description="Items required for this goal")


class CraftingDecision(BaseModel):
    """Schema for crafting decisions"""
    recipe_name: str = Field(description="Name of the recipe to craft")
    required_materials: Dict[str, float] = Field(description="Materials required")
    expected_result: Dict[str, Any] = Field(description="Expected properties of crafted item")
    crafting_time: int = Field(description="Time needed to craft")
    priority: float = Field(ge=0.0, le=1.0, description="Priority of this crafting task")


class BuildingDecision(BaseModel):
    """Schema for building decisions"""
    building_type: str = Field(description="Type of building to construct")
    target_position: Tuple[int, int] = Field(description="Where to build")
    required_materials: Dict[str, float] = Field(description="Materials required")
    building_purpose: str = Field(description="Why this building is needed")
    expected_benefit: str = Field(description="Expected benefit from this building")


class PerceptionReport(BaseModel):
    """Schema for agent's perception of the world"""
    visible_resources: Dict[str, List[Tuple[int, int]]] = Field(description="Resources visible and their positions")
    nearby_agents: List[Dict[str, Any]] = Field(description="Nearby agents and their states")
    immediate_threats: List[str] = Field(default_factory=list, description="Immediate threats or dangers")
    opportunities: List[str] = Field(default_factory=list, description="Visible opportunities")
    current_terrain: str = Field(description="Current terrain type")
    weather_conditions: Dict[str, float] = Field(description="Current weather affecting agent")


class TrinityReport(BaseModel):
    """Schema for Trinity system reports"""
    observed_behaviors: List[Dict[str, Any]] = Field(description="Behaviors observed in agents")
    patterns_detected: List[str] = Field(description="Patterns detected in agent behavior")
    skill_suggestions: List[Dict[str, Any]] = Field(description="Suggested new skills")
    rule_proposals: List[Dict[str, Any]] = Field(description="Proposed new rules")
    event_triggers: List[str] = Field(description="Events that should be triggered")
    age_progression_recommendations: List[str] = Field(description="Recommendations for age progression")