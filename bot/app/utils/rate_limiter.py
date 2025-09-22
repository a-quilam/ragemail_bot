"""
Rate Limiter utility for protecting against overload
"""
import time
import asyncio
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_requests: int = 10
    time_window: int = 60  # seconds
    burst_limit: int = 5
    cooldown_period: int = 30  # seconds


class RateLimiter:
    """Rate limiter with sliding window and burst protection"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.burst_timestamps: Dict[str, deque] = defaultdict(deque)
        self.cooldowns: Dict[str, float] = {}
        self._lock = asyncio.Lock()
    
    async def is_allowed(self, key: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is allowed for the given key
        
        Returns:
            tuple: (is_allowed, reason_if_not_allowed)
        """
        async with self._lock:
            current_time = time.time()
            
            # Check cooldown period
            if key in self.cooldowns:
                if current_time - self.cooldowns[key] < self.config.cooldown_period:
                    remaining = self.config.cooldown_period - (current_time - self.cooldowns[key])
                    return False, f"Rate limit cooldown active, {remaining:.1f}s remaining"
            
            # Clean old requests
            self._clean_old_requests(key, current_time)
            
            # Check burst limit
            if not self._check_burst_limit(key, current_time):
                self.cooldowns[key] = current_time
                return False, "Burst limit exceeded"
            
            # Check rate limit
            if not self._check_rate_limit(key, current_time):
                self.cooldowns[key] = current_time
                return False, "Rate limit exceeded"
            
            # Record request
            self.requests[key].append(current_time)
            self.burst_timestamps[key].append(current_time)
            
            return True, None
    
    def _clean_old_requests(self, key: str, current_time: float):
        """Remove requests older than time window"""
        cutoff_time = current_time - self.config.time_window
        
        # Clean rate limit requests
        while self.requests[key] and self.requests[key][0] < cutoff_time:
            self.requests[key].popleft()
        
        # Clean burst requests (keep only last 5 seconds)
        burst_cutoff = current_time - 5
        while self.burst_timestamps[key] and self.burst_timestamps[key][0] < burst_cutoff:
            self.burst_timestamps[key].popleft()
    
    def _check_rate_limit(self, key: str, current_time: float) -> bool:
        """Check if rate limit is exceeded"""
        return len(self.requests[key]) < self.config.max_requests
    
    def _check_burst_limit(self, key: str, current_time: float) -> bool:
        """Check if burst limit is exceeded"""
        return len(self.burst_timestamps[key]) < self.config.burst_limit
    
    async def get_stats(self, key: str) -> dict:
        """Get rate limiting stats for a key"""
        async with self._lock:
            current_time = time.time()
            self._clean_old_requests(key, current_time)
            
            return {
                "key": key,
                "current_requests": len(self.requests[key]),
                "current_burst": len(self.burst_timestamps[key]),
                "max_requests": self.config.max_requests,
                "max_burst": self.config.burst_limit,
                "time_window": self.config.time_window,
                "cooldown_active": key in self.cooldowns and (current_time - self.cooldowns[key]) < self.config.cooldown_period,
                "cooldown_remaining": max(0, self.config.cooldown_period - (current_time - self.cooldowns.get(key, 0))) if key in self.cooldowns else 0
            }


# Global rate limiters for different operations
_admin_operations_limiter = RateLimiter(RateLimitConfig(
    max_requests=5,
    time_window=60,
    burst_limit=2,
    cooldown_period=30
))

_stats_operations_limiter = RateLimiter(RateLimitConfig(
    max_requests=20,
    time_window=60,
    burst_limit=5,
    cooldown_period=15
))

_db_operations_limiter = RateLimiter(RateLimitConfig(
    max_requests=100,
    time_window=60,
    burst_limit=20,
    cooldown_period=10
))


def get_admin_limiter() -> RateLimiter:
    """Get rate limiter for admin operations"""
    return _admin_operations_limiter


def get_stats_limiter() -> RateLimiter:
    """Get rate limiter for stats operations"""
    return _stats_operations_limiter


def get_db_limiter() -> RateLimiter:
    """Get rate limiter for database operations"""
    return _db_operations_limiter


async def check_rate_limit(limiter: RateLimiter, key: str, operation: str) -> tuple[bool, Optional[str]]:
    """
    Check rate limit and log if exceeded
    
    Args:
        limiter: Rate limiter instance
        key: Unique key for rate limiting (usually user_id)
        operation: Operation name for logging
    
    Returns:
        tuple: (is_allowed, reason_if_not_allowed)
    """
    is_allowed, reason = await limiter.is_allowed(key)
    
    if not is_allowed:
        logging.warning(f"Rate limit exceeded for {operation} by user {key}: {reason}")
        
        # Log stats for monitoring
        stats = await limiter.get_stats(key)
        logging.info(f"Rate limit stats for {key}: {stats}")
    
    return is_allowed, reason
