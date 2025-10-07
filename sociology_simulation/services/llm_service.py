"""Advanced LLM service with caching, batching, and robust error handling"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import aiohttp
from loguru import logger

from ..config import get_config
import os


class LLMPriority(Enum):
    """Priority levels for LLM requests"""
    CRITICAL = "critical"  # Trinity adjudication, world events
    HIGH = "high"         # Agent actions, goal setting
    MEDIUM = "medium"     # Chat responses, negotiations
    LOW = "low"          # Flavor text, descriptions


@dataclass
class LLMRequest:
    """Structured LLM request with metadata"""
    system: str
    user: str
    temperature: float = 0.7
    priority: LLMPriority = LLMPriority.MEDIUM
    model_override: Optional[str] = None
    cache_key: Optional[str] = None
    max_retries: int = 3
    timeout: float = 30.0
    request_id: str = field(default_factory=lambda: str(time.time()))


@dataclass
class LLMResponse:
    """Structured LLM response with metadata"""
    content: str
    success: bool
    cached: bool = False
    attempts: int = 1
    latency: float = 0.0
    model_used: str = ""
    error: Optional[str] = None


class LLMCache:
    """Simple in-memory cache for LLM responses"""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache: Dict[str, Tuple[LLMResponse, float]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, request: LLMRequest) -> str:
        """Generate cache key from request"""
        if request.cache_key:
            return request.cache_key
        
        # Create hash from system + user prompt + temperature
        content = f"{request.system}|{request.user}|{request.temperature}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, request: LLMRequest) -> Optional[LLMResponse]:
        """Get cached response if available and not expired"""
        key = self._generate_key(request)
        
        if key in self.cache:
            response, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                response.cached = True
                return response
            else:
                # Expired, remove from cache
                del self.cache[key]
        
        return None
    
    def set(self, request: LLMRequest, response: LLMResponse):
        """Store response in cache"""
        if not response.success:
            return  # Don't cache failed responses
        
        key = self._generate_key(request)
        
        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (response, time.time())
    
    def clear(self):
        """Clear all cached responses"""
        self.cache.clear()


class LLMBatchProcessor:
    """Batches LLM requests for improved performance"""
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests: List[Tuple[LLMRequest, asyncio.Future]] = []
        self.processing = False
    
    async def add_request(self, request: LLMRequest) -> LLMResponse:
        """Add request to batch and return future response"""
        future = asyncio.Future()
        self.pending_requests.append((request, future))
        
        # Start batch processing if not already running
        if not self.processing:
            asyncio.create_task(self._process_batch())
        
        return await future
    
    async def _process_batch(self):
        """Process batched requests"""
        self.processing = True
        
        try:
            # Wait for batch to fill or timeout
            await asyncio.sleep(self.batch_timeout)
            
            if not self.pending_requests:
                return
            
            # Process requests by priority
            requests_to_process = self.pending_requests[:self.batch_size]
            self.pending_requests = self.pending_requests[self.batch_size:]
            
            # Sort by priority
            requests_to_process.sort(key=lambda x: x[0].priority.value)
            
            # Process requests in parallel
            tasks = []
            for request, future in requests_to_process:
                task = asyncio.create_task(self._process_single_request(request, future))
                tasks.append(task)
            
            await asyncio.gather(*tasks, return_exceptions=True)
            
        finally:
            self.processing = False
            
            # Continue processing if more requests pending
            if self.pending_requests:
                asyncio.create_task(self._process_batch())
    
    async def _process_single_request(self, request: LLMRequest, future: asyncio.Future):
        """Process a single request"""
        try:
            # This would be replaced with actual LLM call
            response = await LLMService._make_api_call(request)
            future.set_result(response)
        except Exception as e:
            future.set_exception(e)


class LLMService:
    """Advanced LLM service with caching, batching, and error handling"""
    
    def __init__(self):
        self.cache = LLMCache()
        self.batch_processor = LLMBatchProcessor()
        self.rate_limiter = asyncio.Semaphore(10)  # Max 10 concurrent requests
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failures": 0,
            "total_latency": 0.0
        }
    
    async def request(self, 
                     system: str, 
                     user: str, 
                     temperature: float = 0.7,
                     priority: LLMPriority = LLMPriority.MEDIUM,
                     cache_key: Optional[str] = None,
                     use_batch: bool = True) -> LLMResponse:
        """Make an LLM request with all advanced features"""
        
        request = LLMRequest(
            system=system,
            user=user,
            temperature=temperature,
            priority=priority,
            cache_key=cache_key
        )
        
        self.stats["total_requests"] += 1
        
        # Check cache first
        cached_response = self.cache.get(request)
        if cached_response:
            self.stats["cache_hits"] += 1
            logger.debug(f"Cache hit for request {request.request_id}")
            return cached_response
        
        self.stats["cache_misses"] += 1
        
        # Process request
        try:
            if use_batch and priority != LLMPriority.CRITICAL:
                response = await self.batch_processor.add_request(request)
            else:
                response = await self._make_api_call(request)
            
            # Cache successful responses
            if response.success:
                self.cache.set(request, response)
            else:
                self.stats["failures"] += 1
            
            self.stats["total_latency"] += response.latency
            return response
            
        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            self.stats["failures"] += 1
            return LLMResponse(
                content="{}",
                success=False,
                error=str(e)
            )
    
    @staticmethod
    async def _make_api_call(request: LLMRequest) -> LLMResponse:
        """Make actual API call with robust error handling"""
        config = get_config()
        start_time = time.time()
        
        model = request.model_override or config.model.agent_model
        
        # Resolve API key from the environment variable named by config.model.api_key_env
        api_key = os.getenv(config.model.api_key_env, "")
        if not api_key:
            raise ValueError(
                f"API key not found in environment variable {config.model.api_key_env}"
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "temperature": request.temperature,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user}
            ]
        }
        
        last_error = None
        
        for attempt in range(request.max_retries):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=request.timeout)) as session:
                    async with session.post(config.model.base_url, headers=headers, json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                            
                            latency = time.time() - start_time
                            
                            return LLMResponse(
                                content=content.strip(),
                                success=True,
                                attempts=attempt + 1,
                                latency=latency,
                                model_used=model
                            )
                        else:
                            last_error = f"HTTP {response.status}: {await response.text()}"
                            
            except asyncio.TimeoutError:
                last_error = "Request timeout"
            except Exception as e:
                last_error = str(e)
            
            if attempt < request.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        # All attempts failed
        return LLMResponse(
            content="{}",
            success=False,
            attempts=request.max_retries,
            latency=time.time() - start_time,
            error=last_error
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            **self.stats,
            "cache_hit_rate": self.stats["cache_hits"] / max(self.stats["total_requests"], 1),
            "failure_rate": self.stats["failures"] / max(self.stats["total_requests"], 1),
            "avg_latency": self.stats["total_latency"] / max(self.stats["cache_misses"], 1),
            "cache_size": len(self.cache.cache)
        }
    
    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()


# Global LLM service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


# Convenience functions for backward compatibility
async def adeepseek_chat(model: str, system: str, user: str, session: aiohttp.ClientSession, temperature: float = 0.7) -> str:
    """Backward compatibility function"""
    service = get_llm_service()
    response = await service.request(system, user, temperature)
    return response.content
