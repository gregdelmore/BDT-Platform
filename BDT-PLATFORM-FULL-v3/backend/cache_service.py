"""
Caching Service for BDT Platform
Implements Redis caching with fallback to in-memory cache
"""
import os
import json
import hashlib
import pickle
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
from functools import wraps
import logging

import redis
from redis import ConnectionPool
import redis.sentinel

logger = logging.getLogger(__name__)

class CacheService:
    """
    Production-grade caching service with Redis and in-memory fallback
    """
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = None
        self.in_memory_cache = {}
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection with retry logic"""
        try:
            # Parse Redis URL
            pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=50,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 1,  # TCP_KEEPINTVL
                    3: 3,  # TCP_KEEPCNT
                }
            )
            
            self.redis_client = redis.Redis(
                connection_pool=pool,
                decode_responses=False,  # Store binary data
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory cache: {e}")
            self.redis_client = None
    
    def _get_cache_key(self, prefix: str, key: str) -> str:
        """Generate standardized cache key"""
        return f"bdt:{prefix}:{key}"
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            # Try JSON first (faster)
            return json.dumps(value).encode('utf-8')
        except (TypeError, ValueError):
            # Fall back to pickle for complex objects
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if not data:
            return None
        
        try:
            # Try JSON first
            return json.loads(data.decode('utf-8'))
        except:
            # Fall back to pickle
            try:
                return pickle.loads(data)
            except:
                return None
    
    def get(self, key: str, prefix: str = "default") -> Optional[Any]:
        """
        Get value from cache
        """
        full_key = self._get_cache_key(prefix, key)
        
        try:
            # Try Redis first
            if self.redis_client:
                data = self.redis_client.get(full_key)
                if data:
                    self.cache_stats["hits"] += 1
                    return self._deserialize(data)
            
            # Fall back to in-memory cache
            if full_key in self.in_memory_cache:
                entry = self.in_memory_cache[full_key]
                if entry["expires"] > datetime.utcnow():
                    self.cache_stats["hits"] += 1
                    return entry["value"]
                else:
                    # Expired
                    del self.in_memory_cache[full_key]
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for {full_key}: {e}")
            self.cache_stats["errors"] += 1
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600,
        prefix: str = "default"
    ) -> bool:
        """
        Set value in cache with expiration
        """
        full_key = self._get_cache_key(prefix, key)
        
        try:
            serialized = self._serialize(value)
            
            # Try Redis first
            if self.redis_client:
                self.redis_client.setex(full_key, expire, serialized)
                return True
            
            # Fall back to in-memory cache
            self.in_memory_cache[full_key] = {
                "value": value,
                "expires": datetime.utcnow() + timedelta(seconds=expire)
            }
            
            # Limit in-memory cache size
            if len(self.in_memory_cache) > 1000:
                self._cleanup_memory_cache()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {full_key}: {e}")
            self.cache_stats["errors"] += 1
            return False
    
    def delete(self, key: str, prefix: str = "default") -> bool:
        """
        Delete value from cache
        """
        full_key = self._get_cache_key(prefix, key)
        
        try:
            # Try Redis
            if self.redis_client:
                self.redis_client.delete(full_key)
            
            # Also delete from in-memory cache
            if full_key in self.in_memory_cache:
                del self.in_memory_cache[full_key]
            
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for {full_key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str, prefix: str = "default") -> int:
        """
        Delete all keys matching pattern
        """
        full_pattern = self._get_cache_key(prefix, pattern)
        deleted = 0
        
        try:
            # Redis deletion
            if self.redis_client:
                cursor = 0
                while True:
                    cursor, keys = self.redis_client.scan(
                        cursor,
                        match=full_pattern,
                        count=100
                    )
                    if keys:
                        deleted += self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            
            # In-memory deletion
            keys_to_delete = [
                k for k in self.in_memory_cache.keys()
                if k.startswith(full_pattern.replace("*", ""))
            ]
            for key in keys_to_delete:
                del self.in_memory_cache[key]
                deleted += 1
            
            return deleted
            
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    def exists(self, key: str, prefix: str = "default") -> bool:
        """
        Check if key exists in cache
        """
        full_key = self._get_cache_key(prefix, key)
        
        try:
            # Check Redis
            if self.redis_client and self.redis_client.exists(full_key):
                return True
            
            # Check in-memory cache
            if full_key in self.in_memory_cache:
                entry = self.in_memory_cache[full_key]
                if entry["expires"] > datetime.utcnow():
                    return True
                else:
                    del self.in_memory_cache[full_key]
            
            return False
            
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1, prefix: str = "counters") -> int:
        """
        Increment a counter
        """
        full_key = self._get_cache_key(prefix, key)
        
        try:
            if self.redis_client:
                return self.redis_client.incrby(full_key, amount)
            
            # In-memory fallback
            if full_key not in self.in_memory_cache:
                self.in_memory_cache[full_key] = {
                    "value": 0,
                    "expires": datetime.utcnow() + timedelta(days=1)
                }
            
            self.in_memory_cache[full_key]["value"] += amount
            return self.in_memory_cache[full_key]["value"]
            
        except Exception as e:
            logger.error(f"Cache increment error: {e}")
            return 0
    
    def get_many(self, keys: List[str], prefix: str = "default") -> Dict[str, Any]:
        """
        Get multiple values at once
        """
        result = {}
        full_keys = [self._get_cache_key(prefix, k) for k in keys]
        
        try:
            # Try Redis
            if self.redis_client:
                values = self.redis_client.mget(full_keys)
                for key, value in zip(keys, values):
                    if value:
                        result[key] = self._deserialize(value)
            
            # Fill from in-memory cache
            for key, full_key in zip(keys, full_keys):
                if key not in result and full_key in self.in_memory_cache:
                    entry = self.in_memory_cache[full_key]
                    if entry["expires"] > datetime.utcnow():
                        result[key] = entry["value"]
            
            return result
            
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    def set_many(
        self,
        data: Dict[str, Any],
        expire: int = 3600,
        prefix: str = "default"
    ) -> bool:
        """
        Set multiple values at once
        """
        try:
            if self.redis_client:
                pipe = self.redis_client.pipeline()
                for key, value in data.items():
                    full_key = self._get_cache_key(prefix, key)
                    serialized = self._serialize(value)
                    pipe.setex(full_key, expire, serialized)
                pipe.execute()
            else:
                # In-memory fallback
                expires = datetime.utcnow() + timedelta(seconds=expire)
                for key, value in data.items():
                    full_key = self._get_cache_key(prefix, key)
                    self.in_memory_cache[full_key] = {
                        "value": value,
                        "expires": expires
                    }
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    def _cleanup_memory_cache(self):
        """
        Remove expired entries from in-memory cache
        """
        now = datetime.utcnow()
        expired_keys = [
            k for k, v in self.in_memory_cache.items()
            if v["expires"] <= now
        ]
        for key in expired_keys:
            del self.in_memory_cache[key]
        
        # If still too large, remove oldest entries
        if len(self.in_memory_cache) > 800:
            sorted_items = sorted(
                self.in_memory_cache.items(),
                key=lambda x: x[1]["expires"]
            )
            for key, _ in sorted_items[:200]:
                del self.in_memory_cache[key]
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics
        """
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (
            self.cache_stats["hits"] / total_requests * 100
            if total_requests > 0 else 0
        )
        
        stats = {
            **self.cache_stats,
            "hit_rate": f"{hit_rate:.2f}%",
            "redis_connected": self.redis_client is not None,
            "memory_cache_size": len(self.in_memory_cache)
        }
        
        # Add Redis info if connected
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_memory"] = info.get("used_memory_human", "N/A")
                stats["redis_keys"] = self.redis_client.dbsize()
            except:
                pass
        
        return stats
    
    def flush_all(self):
        """
        Clear all cache (use with caution!)
        """
        try:
            if self.redis_client:
                self.redis_client.flushdb()
            self.in_memory_cache.clear()
            logger.info("Cache flushed successfully")
        except Exception as e:
            logger.error(f"Cache flush error: {e}")

# Cache decorator for functions
def cached(expire: int = 3600, prefix: str = "func"):
    """
    Decorator to cache function results
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function and arguments
            cache_key = f"{func.__name__}:{hashlib.md5(str((args, kwargs)).encode()).hexdigest()}"
            
            # Try to get from cache
            result = cache.get(cache_key, prefix=prefix)
            if result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, expire=expire, prefix=prefix)
            
            return result
        
        # Add cache control methods
        wrapper.cache_clear = lambda: cache.delete_pattern(f"{func.__name__}:*", prefix=prefix)
        wrapper.cache_key = lambda *a, **kw: f"{func.__name__}:{hashlib.md5(str((a, kw)).encode()).hexdigest()}"
        
        return wrapper
    return decorator

# Singleton cache instance
cache = CacheService()

# Query result caching
class QueryCache:
    """
    Specialized cache for ChromaDB query results
    """
    
    @staticmethod
    def cache_query_result(
        twin_id: str,
        query: str,
        sources: List[str],
        results: Dict,
        expire: int = 1800
    ):
        """Cache query results"""
        key = QueryCache._get_query_key(twin_id, query, sources)
        cache.set(key, results, expire=expire, prefix="queries")
    
    @staticmethod
    def get_cached_query(
        twin_id: str,
        query: str,
        sources: List[str]
    ) -> Optional[Dict]:
        """Get cached query results"""
        key = QueryCache._get_query_key(twin_id, query, sources)
        return cache.get(key, prefix="queries")
    
    @staticmethod
    def invalidate_twin_queries(twin_id: str):
        """Invalidate all queries for a twin"""
        cache.delete_pattern(f"{twin_id}:*", prefix="queries")
    
    @staticmethod
    def _get_query_key(twin_id: str, query: str, sources: List[str]) -> str:
        """Generate cache key for query"""
        sources_str = ",".join(sorted(sources))
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"{twin_id}:{sources_str}:{query_hash}"

# User session caching
class SessionCache:
    """
    Cache for user session data
    """
    
    @staticmethod
    def set_session(user_id: str, data: Dict, expire: int = 3600):
        """Store session data"""
        cache.set(user_id, data, expire=expire, prefix="sessions")
    
    @staticmethod
    def get_session(user_id: str) -> Optional[Dict]:
        """Get session data"""
        return cache.get(user_id, prefix="sessions")
    
    @staticmethod
    def extend_session(user_id: str, additional_seconds: int = 1800):
        """Extend session expiration"""
        data = SessionCache.get_session(user_id)
        if data:
            cache.set(user_id, data, expire=additional_seconds, prefix="sessions")
    
    @staticmethod
    def invalidate_session(user_id: str):
        """Invalidate user session"""
        cache.delete(user_id, prefix="sessions")

# Rate limiting using cache
class RateLimiter:
    """
    API rate limiting using cache
    """
    
    @staticmethod
    def check_rate_limit(
        identifier: str,
        limit: int = 100,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded
        Returns (allowed, remaining_requests)
        """
        key = f"{identifier}:{datetime.utcnow().minute}"
        count = cache.increment(key, prefix="ratelimit")
        
        if count == 1:
            # First request in this window
            cache.set(key, count, expire=window, prefix="ratelimit")
        
        remaining = max(0, limit - count)
        return count <= limit, remaining
    
    @staticmethod
    def reset_rate_limit(identifier: str):
        """Reset rate limit for identifier"""
        key = f"{identifier}:{datetime.utcnow().minute}"
        cache.delete(key, prefix="ratelimit")
