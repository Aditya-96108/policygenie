"""
Advanced Caching Service for Performance Optimization
Supports in-memory and Redis caching with intelligent TTL
"""
import logging
import asyncio
import json
import hashlib
from typing import Optional, Any
from datetime import timedelta
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Hybrid caching system with:
    1. In-memory cache for hot data (fast access)
    2. Redis cache for distributed caching (optional)
    3. Intelligent cache invalidation
    """
    
    def __init__(self):
        # In-memory cache (1000 items, 1 hour TTL)
        self._memory_cache = TTLCache(maxsize=1000, ttl=3600)
        self._redis_client = None
        self._redis_enabled = False
        
    async def initialize_redis(self):
        """Initialize Redis connection if available"""
        try:
            from app.config import settings
            if settings.enable_caching:
                import aioredis
                self._redis_client = await aioredis.from_url(
                    f"redis://{settings.redis_host}:{settings.redis_port}",
                    encoding="utf-8",
                    decode_responses=True
                )
                self._redis_enabled = True
                logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Redis not available, using memory cache only: {str(e)}")
            self._redis_enabled = False
    
    def _generate_key(self, key: str, namespace: str = "default") -> str:
        """Generate namespaced cache key"""
        return f"{namespace}:{key}"
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Get value from cache (memory first, then Redis)"""
        cache_key = self._generate_key(key, namespace)
        
        # Try memory cache first
        if cache_key in self._memory_cache:
            logger.debug(f"Memory cache hit: {cache_key}")
            return self._memory_cache[cache_key]
        
        # Try Redis if enabled
        if self._redis_enabled and self._redis_client:
            try:
                value = await self._redis_client.get(cache_key)
                if value:
                    logger.debug(f"Redis cache hit: {cache_key}")
                    # Deserialize and update memory cache
                    deserialized = json.loads(value)
                    self._memory_cache[cache_key] = deserialized
                    return deserialized
            except Exception as e:
                logger.error(f"Redis get error: {str(e)}")
        
        logger.debug(f"Cache miss: {cache_key}")
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        namespace: str = "default"
    ) -> bool:
        """Set value in cache (both memory and Redis)"""
        cache_key = self._generate_key(key, namespace)
        
        try:
            # Set in memory cache
            self._memory_cache[cache_key] = value
            
            # Set in Redis if enabled
            if self._redis_enabled and self._redis_client:
                try:
                    serialized = json.dumps(value)
                    await self._redis_client.setex(
                        cache_key,
                        ttl,
                        serialized
                    )
                except Exception as e:
                    logger.error(f"Redis set error: {str(e)}")
            
            logger.debug(f"Cache set: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    async def delete(self, key: str, namespace: str = "default") -> bool:
        """Delete value from cache"""
        cache_key = self._generate_key(key, namespace)
        
        # Delete from memory
        if cache_key in self._memory_cache:
            del self._memory_cache[cache_key]
        
        # Delete from Redis if enabled
        if self._redis_enabled and self._redis_client:
            try:
                await self._redis_client.delete(cache_key)
            except Exception as e:
                logger.error(f"Redis delete error: {str(e)}")
        
        return True
    
    async def clear_namespace(self, namespace: str) -> bool:
        """Clear all keys in a namespace"""
        try:
            # Clear memory cache
            keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(f"{namespace}:")]
            for key in keys_to_delete:
                del self._memory_cache[key]
            
            # Clear Redis if enabled
            if self._redis_enabled and self._redis_client:
                pattern = f"{namespace}:*"
                async for key in self._redis_client.scan_iter(match=pattern):
                    await self._redis_client.delete(key)
            
            logger.info(f"Cleared cache namespace: {namespace}")
            return True
        except Exception as e:
            logger.error(f"Clear namespace error: {str(e)}")
            return False
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "memory_cache_size": len(self._memory_cache),
            "memory_cache_maxsize": self._memory_cache.maxsize,
            "redis_enabled": self._redis_enabled,
        }


# Singleton instance
cache_manager = CacheManager()
