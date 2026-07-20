"""
Rinox Sentinel - Rate Limiter
Per-user cooldown tracking using cache
"""

import time
import logging
from typing import Dict, Optional

logger = logging.getLogger("Rinox.RateLimiter")


class RateLimiter:
    """Simple token-bucket rate limiter"""

    def __init__(self, cache=None, default_rate: int = 5, default_period: int = 10):
        self.cache = cache
        self.default_rate = default_rate
        self.default_period = default_period
        self._memory: Dict[str, list] = {}

    async def check(self, key: str, rate: int = None, period: int = None) -> bool:
        """Check if action is allowed. Returns True if allowed."""
        rate = rate or self.default_rate
        period = period or self.default_period
        now = time.time()

        if self.cache:
            count = await self.cache.get_counter(f"ratelimit:{key}")
            if count >= rate:
                return False
            await self.cache.increment_counter(f"ratelimit:{key}", 1, period)
            return True

        if key not in self._memory:
            self._memory[key] = []

        self._memory[key] = [t for t in self._memory[key] if now - t < period]

        if len(self._memory[key]) >= rate:
            return False

        self._memory[key].append(now)
        return True

    async def get_remaining(self, key: str, rate: int = None, period: int = None) -> int:
        """Get remaining allowed actions"""
        rate = rate or self.default_rate
        period = period or self.default_period
        now = time.time()

        if self.cache:
            count = await self.cache.get_counter(f"ratelimit:{key}")
            return max(0, rate - count)

        if key not in self._memory:
            return rate

        self._memory[key] = [t for t in self._memory[key] if now - t < period]
        return max(0, rate - len(self._memory[key]))

    async def reset(self, key: str):
        """Reset rate limit for a key"""
        if self.cache:
            await self.cache.delete(f"ratelimit:{key}")
        self._memory.pop(key, None)