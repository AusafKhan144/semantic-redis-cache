class SemcacheError(Exception):
    pass

class RedisConnectionError(SemcacheError):
    pass

class EmbeddingError(SemcacheError):
    pass