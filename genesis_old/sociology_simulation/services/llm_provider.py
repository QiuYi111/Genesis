"""LLM Provider abstraction layer."""

from typing import Protocol, TypedDict, Optional, List, Tuple, Dict
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Msg(TypedDict):
    """Standard message format for LLM requests."""
    role: str  # system|user|assistant
    content: str


class ModelCfg(TypedDict, total=False):
    """Model configuration with optional parameters."""
    model: str
    temperature: float
    timeout: float
    max_tokens: int
    top_p: float
    frequency_penalty: float
    presence_penalty: float


class LLMProvider(Protocol):
    """Protocol for LLM providers - defines the contract for all LLM implementations."""
    
    async def generate(self, messages: List[Msg], cfg: ModelCfg) -> str:
        """Generate response from LLM.
        
        Args:
            messages: List of messages in conversation format
            cfg: Model configuration parameters
            
        Returns:
            Generated text response
            
        Raises:
            LLMProviderError: If generation fails
        """
        ...


@dataclass
class TrinityActions:
    """Actions that Trinity can take to adjust the world."""
    resource_regen_multiplier: float = 1.0
    terrain_adjustments: Optional[List[Tuple[Tuple[int, int], str]]] = None
    skill_updates: Optional[Dict[str, dict]] = None


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMTimeoutError(LLMProviderError):
    """LLM request timeout error."""
    pass


class LLMRateLimitError(LLMProviderError):
    """LLM rate limit exceeded error."""
    pass


class LLMAuthenticationError(LLMProviderError):
    """LLM authentication error."""
    pass


class NullProvider:
    """Null/Offline LLM provider for testing and deterministic execution."""
    
    def __init__(self, default_response: str = "{}"):
        """Initialize NullProvider with default response.
        
        Args:
            default_response: Default response to return for all requests
        """
        self.default_response = default_response
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "cached_responses": 0
        }
    
    async def generate(self, messages: List[Msg], cfg: ModelCfg) -> str:
        """Return deterministic default response.
        
        Args:
            messages: Messages (ignored for null provider)
            cfg: Configuration (ignored for null provider)
            
        Returns:
            Default response string
        """
        self.stats["total_requests"] += 1
        self.stats["successful_requests"] += 1
        
        # Simple content-based response for different message types
        if not messages:
            return self.default_response
        
        last_message = messages[-1]["content"].lower() if messages else ""
        
        # Return different deterministic responses based on message content
        if "trinity" in last_message and "rule" in last_message:
            return '{"terrain_types": ["FOREST", "OCEAN", "MOUNTAIN", "GRASSLAND"], "resource_rules": {"wood": {"FOREST": 0.5}, "fish": {"OCEAN": 0.4}, "stone": {"MOUNTAIN": 0.6}}}'
        elif "action" in last_message and "agent" in last_message:
            return '{"position": [1, 1], "inventory": {"wood": 1}, "log": "移动并采集了木材"}'
        elif "name" in last_message and "agent" in last_message:
            return "猎人" + str(hash(last_message) % 1000)
        elif "goal" in last_message:
            return "寻找食物和安全的住所"
        elif "chat" in last_message or "response" in last_message:
            return "这是一个不错的建议。"
        elif "behavior" in last_message and "skill" in last_message:
            return '{"new_skills": ["hunting", "fishing"], "skill_updates": {"foraging": {"level": 2}}}'
        elif "natural" in last_message and "event" in last_message:
            return '{"event_type": "rain", "duration": 3, "effects": {"regeneration_multiplier": 1.2}}'
        else:
            return self.default_response
    
    def get_stats(self) -> dict:
        """Get provider statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset provider statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "cached_responses": 0
        }


class Planner:
    """Base planner interface for Trinity decision making."""
    
    def plan(self, signals: dict) -> dict:
        """Plan actions based on world signals.
        
        Args:
            signals: World state signals (resource status, etc.)
            
        Returns:
            Plan dictionary with keys: regen, terrain, skills
        """
        ...


class NullPlanner(Planner):
    """Deterministic planner for testing and offline mode."""
    
    def plan(self, signals: dict) -> dict:
        """Return stable default plan.
        
        Args:
            signals: World state signals (ignored for null planner)
            
        Returns:
            Default plan with stable regen multiplier
        """
        return {
            "regen": 1.0,  # Default stable state
            "terrain": None,
            "skills": None
        }