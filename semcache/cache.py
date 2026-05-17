import redis
import numpy as np
import json
import hashlib
from typing import Any, Callable, Optional
from datetime import datetime
from sentence_transformers import SentenceTransformer

from .models import CacheResult
from .exceptions import RedisConnectionError, EmbeddingError


class SemanticRedisCache:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        threshold: float = 0.85,
        ttl: int = 86400,
        model_name: str = "all-MiniLM-L6-v2",
        namespace: str = "semcache"
    ):
        self.threshold = threshold
        self.ttl = ttl
        self.namespace = namespace
        self._hits = 0
        self._misses = 0

        # connect to redis
        try:
            self.redis = redis.Redis(
                host=host,
                port=port,
                decode_responses=True
            )
            self.redis.ping()
        except redis.ConnectionError:
            raise RedisConnectionError(
                f"Could not connect to Redis at {host}:{port}"
            )

        # load embedding model
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            raise EmbeddingError(
                f"Could not load model {model_name}: {e}"
            )

    # ─────────────────────────────
    # Public Interface
    # ─────────────────────────────

    def get(self, query: str) -> CacheResult:
        embedding = self._embed(query)
        keys = self.redis.keys(f"{self.namespace}:*")

        best_score = 0.0
        best_entry = None

        for key in keys:
            raw = self.redis.get(key)
            if not raw:
                continue
            try:
                entry = json.loads(raw)
                score = self._similarity(
                    embedding,
                    entry["embedding"]
                )
                if score > best_score:
                    best_score = score
                    best_entry = entry
            except (json.JSONDecodeError, KeyError):
                continue

        if best_score >= self.threshold and best_entry:
            self._hits += 1
            return CacheResult(
                value=best_entry["response"],
                hit=True,
                similarity=round(best_score, 4),
                cached_at=best_entry.get("cached_at")
            )

        self._misses += 1
        return CacheResult(
            value=None,
            hit=False,
            similarity=round(best_score, 4)
        )

    def set(self, query: str, response: Any) -> None:
        embedding = self._embed(query)
        key = self._make_key(query)

        entry = {
            "query": query,
            "embedding": embedding,
            "response": response,
            "cached_at": datetime.utcnow().isoformat()
        }

        self.redis.setex(
            key,
            self.ttl,
            json.dumps(entry)
        )

    def get_or_set(
        self,
        query: str,
        func: Callable,
        *args,
        **kwargs
    ) -> CacheResult:
        result = self.get(query)

        if result.hit:
            return result

        response = func(*args, **kwargs)
        self.set(query, response)

        return CacheResult(
            value=response,
            hit=False,
            similarity=result.similarity
        )

    def delete(self, query: str) -> bool:
        key = self._make_key(query)
        return bool(self.redis.delete(key))

    def flush(self) -> None:
        keys = self.redis.keys(f"{self.namespace}:*")
        if keys:
            self.redis.delete(*keys)
        self._hits = 0
        self._misses = 0

    # ─────────────────────────────
    # Metrics
    # ─────────────────────────────

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return round(self._hits / total * 100, 2)

    @property
    def metrics(self) -> dict:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.hit_rate}%",
            "total_cached": len(
                self.redis.keys(f"{self.namespace}:*")
            )
        }

    # ─────────────────────────────
    # Private
    # ─────────────────────────────

    def _embed(self, text: str) -> list:
        return self.model.encode(text).tolist()

    def _similarity(self, a: list, b: list) -> float:
        a = np.array(a)
        b = np.array(b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm == 0:
            return 0.0
        return float(np.dot(a, b) / norm)

    def _make_key(self, query: str) -> str:
        hash_val = hashlib.md5(
            query.encode()
        ).hexdigest()
        return f"{self.namespace}:{hash_val}"