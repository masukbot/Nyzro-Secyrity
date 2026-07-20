"""
Rinox Sentinel - Cache Manager
Redis-based caching with fallback to in-memory
"""

import json
import hashlib
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

logger = logging.getLogger("Rinox.Cache")


class CacheManager:
    """Manages caching for AI responses and security data"""
    
    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._memory_cache: Dict[str, Any] = {}
        self._memory_expiry: Dict[str, datetime] = {}
        
    def _make_key(self, *args) -> str:
        """Create a cache key from arguments"""
        key_string = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_string.encode()).hexdigest()
        
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        # Try Redis first
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
                
        # Fallback to memory cache
        if key in self._memory_cache:
            if datetime.utcnow() < self._memory_expiry.get(key, datetime.min):
                return self._memory_cache[key]
            else:
                del self._memory_cache[key]
                del self._memory_expiry[key]
                
        return None
        
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL (seconds)"""
        serialized = json.dumps(value, default=str)
        
        # Try Redis first
        if self.redis:
            try:
                await self.redis.setex(key, ttl, serialized)
                return
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
                
        # Fallback to memory cache
        self._memory_cache[key] = value
        self._memory_expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
        
    async def delete(self, key: str):
        """Delete a key from cache"""
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
                
        if key in self._memory_cache:
            del self._memory_cache[key]
            del self._memory_expiry[key]
            
    async def get_ai_response(self, prompt_hash: str, provider: str, model: str) -> Optional[Dict]:
        """Get cached AI response"""
        key = self._make_key("ai", provider, model, prompt_hash)
        return await self.get(key)
        
    async def set_ai_response(self, prompt_hash: str, provider: str, 
                            model: str, response: Dict, ttl: int = 1800):
        """Cache AI response"""
        key = self._make_key("ai", provider, model, prompt_hash)
        await self.set(key, response, ttl)
        
    async def get_url_reputation(self, url: str) -> Optional[Dict]:
        """Get cached URL reputation"""
        key = self._make_key("url", url)
        return await self.get(key)
        
    async def set_url_reputation(self, url: str, data: Dict, ttl: int = 86400):
        """Cache URL reputation"""
        key = self._make_key("url", url)
        await self.set(key, data, ttl)
        
    async def get_user_risk(self, guild_id: int, user_id: int) -> Optional[Dict]:
        """Get cached user risk score"""
        key = self._make_key("risk", guild_id, user_id)
        return await self.get(key)
        
    async def set_user_risk(self, guild_id: int, user_id: int, 
                          data: Dict, ttl: int = 3600):
        """Cache user risk score"""
        key = self._make_key("risk", guild_id, user_id)
        await self.set(key, data, ttl)
        
    async def increment_counter(self, key: str, amount: int = 1, ttl: int = 300) -> int:
        """Increment a counter (for rate limiting)"""
        if self.redis:
            try:
                new_val = await self.redis.incrby(key, amount)
                if isinstance(new_val, str):
                    new_val = int(new_val)
                await self.redis.expire(key, ttl)
                return new_val
            except Exception as e:
                logger.warning(f"Redis incr error: {e}")
                
        # Memory fallback
        current = self._memory_cache.get(key, 0)
        current += amount
        self._memory_cache[key] = current
        self._memory_expiry[key] = datetime.utcnow() + timedelta(seconds=ttl)
        return current
        
    async def get_counter(self, key: str) -> int:
        """Get counter value"""
        if self.redis:
            try:
                val = await self.redis.get(key)
                return int(val) if val else 0
            except Exception:
                pass
        return self._memory_cache.get(key, 0)
        
    async def cleanup(self):
        """Clean expired memory cache entries"""
        now = datetime.utcnow()
        expired = [
            key for key, expiry in self._memory_expiry.items()
            if now >= expiry
        ]
        for key in expired:
            del self._memory_cache[key]
            del self._memory_expiry[key]
            
        logger.info(f"🧹 Cleaned {len(expired)} expired cache entries")
        
    async def close(self):
        """Close cache connections"""
        if self.redis:
            await self.redis.close()
