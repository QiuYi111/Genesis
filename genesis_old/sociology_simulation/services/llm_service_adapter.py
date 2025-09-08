"""Adapter layer to unify existing LLM services with the new provider interface."""

import asyncio
import json
import time
from typing import List, Optional, Dict, Any
import aiohttp
from loguru import logger

from .llm_provider import LLMProvider, Msg, ModelCfg, LLMProviderError, LLMTimeoutError, LLMRateLimitError, LLMAuthenticationError
from ..config import get_config


class LLMServiceAdapter(LLMProvider):
    """Adapter that wraps the existing EnhancedLLMService to implement LLMProvider protocol."""
    
    def __init__(self, enhanced_llm_service=None):
        """Initialize adapter with existing LLM service.
        
        Args:
            enhanced_llm_service: Existing EnhancedLLMService instance (optional)
        """
        # Import here to avoid circular imports
        from ..enhanced_llm import get_llm_service
        
        self.llm_service = enhanced_llm_service or get_llm_service()
        self.config = get_config()
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }
    
    async def generate(self, messages: List[Msg], cfg: ModelCfg) -> str:
        """Generate response using existing LLM service.
        
        Args:
            messages: List of messages in conversation format
            cfg: Model configuration
            
        Returns:
            Generated text response
            
        Raises:
            LLMProviderError: If generation fails
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            # Convert messages to system/user format expected by existing service
            system_content = ""
            user_content = ""
            
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                
                if role == "system":
                    system_content = content
                elif role == "user":
                    user_content = content
                elif role == "assistant":
                    # For assistant messages, treat as part of user context
                    if user_content:
                        user_content += f"\nAssistant: {content}"
                    else:
                        user_content = f"Assistant: {content}"
            
            # Ensure we have content
            if not user_content and not system_content:
                user_content = "Continue the conversation."
            
            # Create or reuse session
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            
            # Extract configuration parameters
            temperature = cfg.get("temperature", 0.7)
            model = cfg.get("model", self.config.model.agent_model)
            timeout = cfg.get("timeout", 30.0)
            
            # Use the existing service based on message content
            last_message = messages[-1]["content"].lower() if messages else ""
            
            response_content = "{}"
            
            # Route to appropriate existing method based on content
            if "trinity" in last_message and "rule" in last_message:
                # Trinity rule generation
                response = await self.llm_service.trinity_generate_rules(
                    era_prompt=user_content,
                    session=self._session
                )
                response_content = json.dumps(response) if isinstance(response, dict) else str(response)
                
            elif "action" in last_message and "agent" in last_message:
                # Agent action generation - this is more complex as it needs specific parameters
                # For now, use a simplified approach
                response = await self.llm_service.generate(
                    "agent_action",
                    self._session,
                    era_prompt=system_content,
                    perception=user_content
                )
                response_content = response.content if response.success else "{}"
                
            elif "name" in last_message and "agent" in last_message:
                # Agent name generation
                response = await self.llm_service.generate_agent_name(
                    era=system_content,
                    attributes={},
                    age=25,
                    session=self._session,
                    goal=user_content
                )
                response_content = response
                
            elif "goal" in last_message:
                # Agent goal generation
                response = await self.llm_service.generate_agent_goal(
                    era_prompt=system_content,
                    attributes={},
                    age=25,
                    inventory={},
                    session=self._session
                )
                response_content = response
                
            elif "chat" in last_message or "response" in last_message:
                # Chat response generation
                response = await self.llm_service.generate_chat_response(
                    era_prompt=system_content,
                    agent_age=25,
                    agent_attributes={},
                    agent_inventory={},
                    topic=user_content,
                    session=self._session
                )
                response_content = response
                
            elif "behavior" in last_message and "skill" in last_message:
                # Trinity behavior analysis
                response = await self.llm_service.trinity_analyze_behaviors(
                    era_prompt=system_content,
                    turn=1,
                    agent_behaviors={},
                    available_skills={},
                    unlock_conditions={},
                    session=self._session
                )
                response_content = json.dumps(response) if isinstance(response, dict) else str(response)
                
            elif "natural" in last_message and "event" in last_message:
                # Trinity natural events
                response = await self.llm_service.trinity_natural_events(
                    era_prompt=system_content,
                    turn=1,
                    agent_count=10,
                    development_level="basic",
                    recent_activities=[user_content],
                    session=self._session
                )
                response_content = json.dumps(response) if isinstance(response, dict) else str(response)
                
            else:
                # Generic generation using the enhanced LLM service
                # Determine template name based on content
                template_name = "generic_response"
                if "trinity" in last_message:
                    template_name = "trinity_generic"
                elif "agent" in last_message:
                    template_name = "agent_generic"
                else:
                    template_name = "generic_response"
                
                response = await self.llm_service.generate(
                    template_name,
                    self._session,
                    system=system_content,
                    user=user_content,
                    temperature=temperature
                )
                response_content = response.content if response.success else "{}"
            
            # Update statistics
            response_time = time.time() - start_time
            self.stats["successful_requests"] += 1
            
            # Update average response time
            total_time = self.stats["average_response_time"] * (self.stats["total_requests"] - 1)
            self.stats["average_response_time"] = (total_time + response_time) / self.stats["total_requests"]
            
            return response_content
            
        except aiohttp.ClientError as e:
            self.stats["failed_requests"] += 1
            if "timeout" in str(e).lower():
                raise LLMTimeoutError(f"LLM request timed out: {e}") from e
            else:
                raise LLMProviderError(f"LLM client error: {e}") from e
                
        except Exception as e:
            self.stats["failed_requests"] += 1
            error_msg = str(e).lower()
            
            if "rate limit" in error_msg or "too many requests" in error_msg:
                raise LLMRateLimitError(f"LLM rate limit exceeded: {e}") from e
            elif "authentication" in error_msg or "unauthorized" in error_msg:
                raise LLMAuthenticationError(f"LLM authentication error: {e}") from e
            elif "timeout" in error_msg:
                raise LLMTimeoutError(f"LLM request timed out: {e}") from e
            else:
                raise LLMProviderError(f"LLM generation failed: {e}") from e
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            **self.stats,
            "llm_service_stats": self.llm_service.get_statistics() if hasattr(self.llm_service, 'get_statistics') else {}
        }
    
    def reset_stats(self):
        """Reset adapter statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }
        if hasattr(self.llm_service, 'reset_statistics'):
            self.llm_service.reset_statistics()


class DeepSeekProvider(LLMProvider):
    """DeepSeek API provider implementation."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        """Initialize DeepSeek provider.
        
        Args:
            api_key: DeepSeek API key
            base_url: API base URL
            model: Model name
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }
    
    async def generate(self, messages: List[Msg], cfg: ModelCfg) -> str:
        """Generate response using DeepSeek API.
        
        Args:
            messages: List of messages
            cfg: Model configuration
            
        Returns:
            Generated response
            
        Raises:
            LLMProviderError: If generation fails
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            # Create or reuse session
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            
            # Prepare request payload
            model = cfg.get("model", self.model)
            temperature = cfg.get("temperature", 0.7)
            max_tokens = cfg.get("max_tokens", 2048)
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add optional parameters
            if "top_p" in cfg:
                payload["top_p"] = cfg["top_p"]
            if "frequency_penalty" in cfg:
                payload["frequency_penalty"] = cfg["frequency_penalty"]
            if "presence_penalty" in cfg:
                payload["presence_penalty"] = cfg["presence_penalty"]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            timeout = cfg.get("timeout", 30.0)
            
            async with self._session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Update statistics
                    response_time = time.time() - start_time
                    self.stats["successful_requests"] += 1
                    
                    total_time = self.stats["average_response_time"] * (self.stats["total_requests"] - 1)
                    self.stats["average_response_time"] = (total_time + response_time) / self.stats["total_requests"]
                    
                    return content.strip()
                elif response.status == 401:
                    raise LLMAuthenticationError("Invalid DeepSeek API key")
                elif response.status == 429:
                    raise LLMRateLimitError("DeepSeek rate limit exceeded")
                elif response.status == 408 or response.status == 504:
                    raise LLMTimeoutError("DeepSeek request timed out")
                else:
                    error_text = await response.text()
                    raise LLMProviderError(f"DeepSeek API error {response.status}: {error_text}")
                    
        except asyncio.TimeoutError as e:
            self.stats["failed_requests"] += 1
            raise LLMTimeoutError(f"DeepSeek request timed out: {e}") from e
        except Exception as e:
            self.stats["failed_requests"] += 1
            if isinstance(e, LLMProviderError):
                raise
            else:
                raise LLMProviderError(f"DeepSeek generation failed: {e}") from e
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset provider statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }


class OpenAIProvider(LLMProvider):
    """OpenAI API provider implementation."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-3.5-turbo"):
        """Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            base_url: API base URL
            model: Model name
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }
    
    async def generate(self, messages: List[Msg], cfg: ModelCfg) -> str:
        """Generate response using OpenAI API.
        
        Args:
            messages: List of messages
            cfg: Model configuration
            
        Returns:
            Generated response
            
        Raises:
            LLMProviderError: If generation fails
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            # Create or reuse session
            if self._session is None or self._session.closed:
                self._session = aiohttp.ClientSession()
            
            # Prepare request payload
            model = cfg.get("model", self.model)
            temperature = cfg.get("temperature", 0.7)
            max_tokens = cfg.get("max_tokens", 2048)
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            # Add optional parameters
            if "top_p" in cfg:
                payload["top_p"] = cfg["top_p"]
            if "frequency_penalty" in cfg:
                payload["frequency_penalty"] = cfg["frequency_penalty"]
            if "presence_penalty" in cfg:
                payload["presence_penalty"] = cfg["presence_penalty"]
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            timeout = cfg.get("timeout", 30.0)
            
            async with self._session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    # Update statistics
                    response_time = time.time() - start_time
                    self.stats["successful_requests"] += 1
                    
                    total_time = self.stats["average_response_time"] * (self.stats["total_requests"] - 1)
                    self.stats["average_response_time"] = (total_time + response_time) / self.stats["total_requests"]
                    
                    return content.strip()
                elif response.status == 401:
                    raise LLMAuthenticationError("Invalid OpenAI API key")
                elif response.status == 429:
                    raise LLMRateLimitError("OpenAI rate limit exceeded")
                elif response.status == 408 or response.status == 504:
                    raise LLMTimeoutError("OpenAI request timed out")
                else:
                    error_text = await response.text()
                    raise LLMProviderError(f"OpenAI API error {response.status}: {error_text}")
                    
        except asyncio.TimeoutError as e:
            self.stats["failed_requests"] += 1
            raise LLMTimeoutError(f"OpenAI request timed out: {e}") from e
        except Exception as e:
            self.stats["failed_requests"] += 1
            if isinstance(e, LLMProviderError):
                raise
            else:
                raise LLMProviderError(f"OpenAI generation failed: {e}") from e
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset provider statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }


def create_provider(provider_type: str, **kwargs) -> LLMProvider:
    """Factory function to create LLM providers.
    
    Args:
        provider_type: Type of provider ('null', 'deepseek', 'openai', 'adapter')
        **kwargs: Provider-specific configuration
        
    Returns:
        LLMProvider instance
        
    Raises:
        ValueError: If provider type is not supported
    """
    if provider_type == "null":
        default_response = kwargs.get("default_response", "{}")
        return NullProvider(default_response)
    
    elif provider_type == "deepseek":
        api_key = kwargs.get("api_key") or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DeepSeek API key is required")
        
        base_url = kwargs.get("base_url", "https://api.deepseek.com/v1")
        model = kwargs.get("model", "deepseek-chat")
        return DeepSeekProvider(api_key, base_url, model)
    
    elif provider_type == "openai":
        api_key = kwargs.get("api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required")
        
        base_url = kwargs.get("base_url", "https://api.openai.com/v1")
        model = kwargs.get("model", "gpt-3.5-turbo")
        return OpenAIProvider(api_key, base_url, model)
    
    elif provider_type == "adapter":
        # Use existing LLM service via adapter
        enhanced_llm_service = kwargs.get("enhanced_llm_service")
        return LLMServiceAdapter(enhanced_llm_service)
    
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")


import os  # Import at the end to avoid circular imports