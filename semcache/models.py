from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class CacheResult:
    value: Any
    hit: bool
    similarity: float
    cached_at: Optional[str] = None

    def __repr__(self):
        status = "HIT" if self.hit else "MISS"
        return (
            f"CacheResult("
            f"status={status}, "
            f"similarity={self.similarity:.2f})"
        )