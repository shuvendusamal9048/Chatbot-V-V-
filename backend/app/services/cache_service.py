import hashlib
import json
import re
from typing import Any, Dict, Optional
from redis.asyncio import Redis

from app.core.config import settings

_redis_client: Optional[Redis] = None


async def get_redis_client() -> Optional[Redis]:
    global _redis_client
    if not settings.REDIS_ENABLED:
        return None

    if _redis_client is None:
        try:
            _redis_client = Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2.0
            )
            # Ping to verify connection
            await _redis_client.ping()
            print("[CACHE] Connected to Redis successfully.")
        except Exception as err:
            print(f"[CACHE] Failed to connect to Redis: {err}")
            _redis_client = None
            return None

    return _redis_client


def normalize_query(query: str) -> str:
    """Normalize query text by lowercasing, stripping extra whitespace, and removing extra punctuation."""
    if not query:
        return ""
    text = query.strip().lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def generate_cache_key(query: str, lang_code: str) -> str:
    """Generate MD5 hash-based Redis key for normalized query and language code."""
    normalized = normalize_query(query)
    raw_key = f"{lang_code}:{normalized}"
    key_hash = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
    return f"cache:chat:{key_hash}"


async def get_cached_response(query: str, lang_code: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached response object from Redis if hit, else return None."""
    try:
        redis = await get_redis_client()
        if not redis:
            return None

        cache_key = generate_cache_key(query, lang_code)
        cached_data = await redis.get(cache_key)

        if cached_data:
            print(f"[CACHE] HIT for query: '{query[:40]}...' (key: {cache_key})")
            return json.loads(cached_data)
        else:
            print(f"[CACHE] MISS for query: '{query[:40]}...' (key: {cache_key})")
            return None
    except Exception as exc:
        print(f"[CACHE] Error retrieving from Redis: {exc}")
        return None


async def set_cached_response(
    query: str,
    lang_code: str,
    answer: str,
    sources: list,
    ttl: Optional[int] = None
) -> bool:
    """Store generated LLM answer and sources into Redis cache with TTL."""
    if not answer or not answer.strip():
        return False

    try:
        redis = await get_redis_client()
        if not redis:
            return False

        cache_key = generate_cache_key(query, lang_code)
        payload = json.dumps({
            "answer": answer,
            "sources": sources,
            "language": lang_code
        }, ensure_ascii=False)

        expire_ttl = ttl if ttl is not None else settings.CACHE_TTL_SECONDS
        await redis.set(cache_key, payload, ex=expire_ttl)
        print(f"[CACHE] SAVED answer to Redis (key: {cache_key}, TTL: {expire_ttl}s)")
        return True
    except Exception as exc:
        print(f"[CACHE] Error setting cache in Redis: {exc}")
        return False


async def clear_chat_cache() -> bool:
    """Clear all chat cache keys from Redis."""
    try:
        redis = await get_redis_client()
        if not redis:
            return False

        keys = await redis.keys("cache:chat:*")
        if keys:
            await redis.delete(*keys)
            print(f"[CACHE] Cleared {len(keys)} chat cache keys from Redis.")
        return True
    except Exception as exc:
        print(f"[CACHE] Error clearing cache: {exc}")
        return False
