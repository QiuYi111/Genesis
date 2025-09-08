"""Provider manager for creating and managing LLM providers based on configuration."""

import os
from typing import Optional, Dict, Any
from loguru import logger

from .llm_provider import LLMProvider, NullProvider
from .llm_service_adapter import LLMServiceAdapter, DeepSeekProvider, OpenAIProvider


class ProviderManager:
    """Manager for creating and configuring LLM providers based on application config."""
    
    def __init__(self):
        """Initialize provider manager."""
        self._current_provider: Optional[LLMProvider] = None
        self._provider_type: str = "null"
        self._provider_config: Dict[str, Any] = {}
    
    def create_provider(self, provider_type: str, config: Dict[str, Any]) -> LLMProvider:
        """Create LLM provider based on type and configuration.
        
        Args:
            provider_type: Type of provider ('null', 'deepseek', 'openai', 'adapter')
            config: Provider configuration from ModelConfig
            
        Returns:
            Configured LLMProvider instance
            
        Raises:
            ValueError: If provider type is not supported or configuration is invalid
        """
        logger.info(f"Creating {provider_type} provider with config: {config}")
        
        if provider_type == "null":
            # Null provider for offline/deterministic execution
            default_response = config.get("default_response", "{}")
            return NullProvider(default_response)
        
        elif provider_type == "deepseek":
            # DeepSeek provider
            api_key = self._get_api_key("DEEPSEEK_API_KEY", config)
            if not api_key:
                logger.warning("DEEPSEEK_API_KEY not found, falling back to null provider")
                return NullProvider()
            
            base_url = config.get("base_url", "https://api.deepseek.com/v1")
            model = config.get("model", "deepseek-chat")
            
            return DeepSeekProvider(api_key, base_url, model)
        
        elif provider_type == "openai":
            # OpenAI provider
            api_key = self._get_api_key("OPENAI_API_KEY", config)
            if not api_key:
                logger.warning("OPENAI_API_KEY not found, falling back to null provider")
                return NullProvider()
            
            base_url = config.get("base_url", "https://api.openai.com/v1")
            model = config.get("model", "gpt-3.5-turbo")
            
            return OpenAIProvider(api_key, base_url, model)
        
        elif provider_type == "adapter":
            # Adapter provider that wraps existing EnhancedLLMService
            # This maintains backward compatibility
            return LLMServiceAdapter()
        
        else:
            raise ValueError(f"Unsupported provider type: {provider_type}")
    
    def create_provider_from_config(self, model_config) -> LLMProvider:
        """Create provider from ModelConfig instance.
        
        Args:
            model_config: ModelConfig instance from Hydra
            
        Returns:
            Configured LLMProvider instance
        """
        provider_type = model_config.provider
        
        # Get provider-specific configuration
        provider_config = model_config.provider_config.get(provider_type, {})
        
        # Merge with base model configuration
        full_config = {
            **provider_config,
            "agent_model": model_config.agent_model,
            "trinity_model": model_config.trinity_model,
            "base_url": model_config.base_url,
            "timeout": model_config.timeout,
            "max_tokens": model_config.max_tokens,
            "max_retries": model_config.max_retries,
            "retry_delay": model_config.retry_delay,
        }
        
        return self.create_provider(provider_type, full_config)
    
    def _get_api_key(self, env_var: str, config: Dict[str, Any]) -> Optional[str]:
        """Get API key from environment or configuration.
        
        Args:
            env_var: Environment variable name
            config: Configuration dict
            
        Returns:
            API key or None if not found
        """
        # Try environment variable first
        api_key = os.getenv(env_var)
        if api_key:
            return api_key
        
        # Try configuration
        api_key = config.get("api_key")
        if api_key:
            return api_key
        
        # Try legacy environment variable (backward compatibility)
        if env_var == "DEEPSEEK_API_KEY":
            return os.getenv("DEEPSEEK_API_KEY")
        elif env_var == "OPENAI_API_KEY":
            return os.getenv("OPENAI_API_KEY")
        
        return None
    
    def get_current_provider(self) -> Optional[LLMProvider]:
        """Get current provider instance.
        
        Returns:
            Current provider or None if not set
        """
        return self._current_provider
    
    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics from current provider.
        
        Returns:
            Provider statistics or empty dict if no provider
        """
        if self._current_provider and hasattr(self._current_provider, 'get_stats'):
            return self._current_provider.get_stats()
        return {}
    
    def close_current_provider(self):
        """Close current provider and cleanup resources."""
        if self._current_provider and hasattr(self._current_provider, 'close'):
            try:
                # For async close methods, we need to handle this properly
                if asyncio.iscoroutinefunction(self._current_provider.close):
                    # This should be called from an async context
                    logger.warning("Async close method detected - should be called from async context")
                else:
                    self._current_provider.close()
            except Exception as e:
                logger.error(f"Error closing provider: {e}")
        
        self._current_provider = None


# Global provider manager instance
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Get global provider manager instance.
    
    Returns:
        ProviderManager instance
    """
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def create_provider_from_config(model_config) -> LLMProvider:
    """Convenience function to create provider from config.
    
    Args:
        model_config: ModelConfig instance
        
    Returns:
        LLMProvider instance
    """
    manager = get_provider_manager()
    return manager.create_provider_from_config(model_config)


def setup_provider(model_config) -> LLMProvider:
    """Setup provider and return instance.
    
    This is the main entry point for configuring the LLM provider.
    
    Args:
        model_config: ModelConfig instance from Hydra
        
    Returns:
        Configured LLMProvider instance
    """
    manager = get_provider_manager()
    provider = manager.create_provider_from_config(model_config)
    manager._current_provider = provider
    manager._provider_type = model_config.provider
    manager._provider_config = model_config.provider_config
    
    logger.info(f"Provider setup complete: {model_config.provider}")
    return provider