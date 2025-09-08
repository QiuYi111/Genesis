"""LLM providers (skeleton).

Exports common provider classes for convenient imports.
"""

from .deepseek import DeepSeekProvider
from .null import NullProvider
from .openai import OpenAIProvider

# Ensure an event loop exists for environments where asyncio policy requires explicit setup
# (used by tests calling get_event_loop().run_until_complete()).
try:  # pragma: no cover - environment guard
    import asyncio

    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
except Exception:
    pass

__all__ = ["NullProvider", "DeepSeekProvider", "OpenAIProvider"]
