"""Educational in-memory string store built from custom data structures."""

from .store import MiniRedis, OutOfMemoryError

__all__ = ["MiniRedis", "OutOfMemoryError"]
__version__ = "1.0.0"
