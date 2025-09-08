"""Async LLM wrapper for DeepSeek API"""
import json
import aiohttp
from loguru import logger
from typing import Dict, Any

from .config import OPENAI_API_KEY, MODEL_AGENT, MODEL_TRINITY

async def adeepseek_chat(
    model: str, 
    system: str, 
    user: str, 
    session: aiohttp.ClientSession, 
    temperature: float = 0.7
) -> str:
    """Async chat completion using direct aiohttp calls to DeepSeek API
    
    Args:
        model: Model name (e.g. 'deepseek-chat')
        system: System prompt
        user: User prompt
        session: aiohttp session
        temperature: Sampling temperature
        
    Returns:
        Generated response text
    """
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    }
    
    try:
        async with session.post(url, headers=headers, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
            if data.get("choices") and data["choices"][0].get("message", {}).get("content"):
                return data["choices"][0]["message"]["content"].strip()
            logger.error(f"Unexpected response format: {data}")
            return "{}"
    except aiohttp.ClientResponseError as e:
        logger.error(f"API request failed: {e.status} - {e.message}")
        return "{}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "{}"
