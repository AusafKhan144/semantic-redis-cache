# semcache

Semantic caching for Redis.
Stop paying for duplicate LLM calls.

## The Problem

Traditional caching misses similar queries:
"what is monthly revenue?"  → cache miss ❌
"show me monthly revenue"   → cache miss ❌
"monthly revenue figures?"  → cache miss ❌

All three mean the same thing.
You pay for 3 LLM calls instead of 1.

## The Solution

semcache uses sentence embeddings to find
semantically similar cached responses.
Zero cost embeddings — runs locally.

## Install

pip install semcache

## Quick Start

from semcache import SemanticRedisCache

cache = SemanticRedisCache(threshold=0.85)

result = cache.get_or_set(
    query="what is monthly revenue?",
    func=your_llm_function,
    question="what is monthly revenue?"
)

print(result.value)       # LLM response
print(result.hit)         # True/False
print(result.similarity)  # 0.91
print(cache.metrics)      # hit rate, counts

## Results

→ 65-70% cache hit rate on real workloads
→ Zero cost embeddings (local model)
→ Works with any LLM
→ Drop-in Redis wrapper

## Configuration

cache = SemanticRedisCache(
    host="localhost",       # Redis host
    port=6379,              # Redis port
    threshold=0.85,         # similarity threshold
    ttl=86400,              # cache TTL in seconds
    model_name="all-MiniLM-L6-v2",  # embedding model
    namespace="semcache"    # Redis key namespace
)

## How It Works

1. Query arrives
2. Convert to embedding (local, free)
3. Search Redis for similar embeddings
4. Similarity > threshold → return cached response
5. Miss → call your LLM → store → return

## Contributing

PRs welcome. See CONTRIBUTING.md.

## License

MIT