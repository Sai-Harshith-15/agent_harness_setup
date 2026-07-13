"""Headroom manager: track context budget and decide when the compactor must run."""
import os
from dataclasses import dataclass


@dataclass
class Headroom:
    max_tokens: int = int(os.environ.get("HEADROOM_MAX_TOKENS", "128000"))
    reserve: int = int(os.environ.get("HEADROOM_RESERVE", "8000"))

    def remaining(self, used: int) -> int:
        return self.max_tokens - self.reserve - used

    def must_compact(self, used: int, incoming: int) -> bool:
        return self.remaining(used) < incoming
