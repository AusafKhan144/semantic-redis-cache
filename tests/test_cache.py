# tests/test_cache.py
import pytest
from semcache import SemanticRedisCache

@pytest.fixture
def cache():
    c = SemanticRedisCache(
        threshold=0.85,
        namespace="test"
    )
    c.flush()
    yield c
    c.flush()

def test_exact_hit(cache):
    cache.set("what is revenue?", "Revenue is $50k")
    result = cache.get("what is revenue?")
    assert result.hit == True
    assert result.value == "Revenue is $50k"
    assert result.similarity == 1.0

def test_semantic_hit(cache):
    cache.set(
        "what is the total revenue?",
        "Revenue is $50k"
    )
    # more semantically similar sentence
    result = cache.get("what is the revenue total?")
    assert result.hit == True
    assert result.similarity >= 0.85

def test_cache_miss(cache):
    cache.set("what is revenue?", "Revenue is $50k")
    result = cache.get("what is the weather today?")
    assert result.hit == False

def test_get_or_set(cache):
    call_count = 0

    def mock_llm(question):
        nonlocal call_count
        call_count += 1
        return "mocked response"

    result = cache.get_or_set(
        "what is the total revenue?",
        mock_llm,
        question="what is the total revenue?"
    )
    assert call_count == 1
    assert result.hit == False

    # use very similar sentence
    result = cache.get_or_set(
        "what is the revenue total?",
        mock_llm,
        question="what is the revenue total?"
    )
    assert call_count == 1  # not called again
    assert result.hit == True
    
def test_metrics(cache):
    cache.set("question", "answer")
    cache.get("question")
    cache.get("something else entirely")

    assert cache.metrics["hits"] == 1
    assert cache.metrics["misses"] == 1
    assert cache.metrics["hit_rate"] == "50.0%"

def test_flush(cache):
    cache.set("q1", "a1")
    cache.set("q2", "a2")
    cache.flush()
    assert cache.metrics["total_cached"] == 0

def test_delete(cache):
    cache.set("question", "answer")
    cache.delete("question")
    result = cache.get("question")
    assert result.hit == False