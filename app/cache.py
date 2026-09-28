import json
from typing import Any

import redis

from app.config import get_settings


_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def cache_get(key: str) -> Any | None:
    try:
        raw = get_redis().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except redis.RedisError:
        return None


def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    settings = get_settings()
    try:
        get_redis().setex(key, ttl or settings.cache_ttl_seconds, json.dumps(value))
    except redis.RedisError:
        pass


def cache_delete_pattern(pattern: str) -> None:
    try:
        client = get_redis()
        for key in client.scan_iter(match=pattern):
            client.delete(key)
    except redis.RedisError:
        pass
