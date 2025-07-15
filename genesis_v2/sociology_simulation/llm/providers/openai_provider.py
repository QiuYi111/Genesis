"""
OpenAI LLM provider implementation.
Handles real API calls to OpenAI's GPT models.
"""

import aiohttp
import json
import time
from typing import List, Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel
import os

from .base import BaseLLMProvider, LLMResponse

T = TypeVar('T', bound=BaseModel)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API provider for real LLM integration"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo", base_url: str = "https://api.openai.com/v1"):
        super().__init__(model=model, api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        **kwargs
    ) -> LLMResponse:
        """Make actual API request to OpenAI"""
        
        start_time = time.time()
        
        try:
            # Check if we need structured output
            response_schema = kwargs.get('response_schema')
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "stream": False
                }
                
                # Add structured output if schema provided
                if response_schema:
                    payload["response_format"] = {
                        "type": "json_object",
                        "schema": response_schema.model_json_schema()
                    }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        return LLMResponse(
                            content="",
                            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                            latency=time.time() - start_time,
                            model=self.model,
                            success=False,
                            error=f"API error {response.status}: {error_text}"
                        )
                    
                    result = await response.json()
                    
                    return LLMResponse(
                        content=result["choices"][0]["message"]["content"],
                        usage=result["usage"],
                        latency=time.time() - start_time,
                        model=result["model"],
                        success=True
                    )
        
        except Exception as e:
            return LLMResponse(
                content="",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                latency=time.time() - start_time,
                model=self.model,
                success=False,
                error=str(e)
            )
    
    async def check_health(self) -> bool:
        """Check OpenAI API health"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5
                }
                
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    return response.status == 200
        
        except Exception:
            return False