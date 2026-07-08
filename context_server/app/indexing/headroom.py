"""Headroom manager: track context budget and decide when the compactor must run."""
from dataclasses import dataclass


@dataclass
class Headroom:
    max_tokens: int = 128_000
    reserve: int = 8_000          # keep this much free for the model's reply

    def remaining(self, used: int) -> int:
        return self.max_tokens - self.reserve - used

    def must_compact(self, used: int, incoming: int) -> bool:
        return self.remaining(used) < incoming
