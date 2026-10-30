"""String storage, UTF-8 byte accounting, LRU eviction and heap-based TTL."""

import time
from dataclasses import dataclass
from typing import Callable, List, Optional

from .structures.hash_map import HashMap
from .structures.linked_list import DoublyLinkedList, Node
from .structures.min_heap import MinHeap


class OutOfMemoryError(Exception):
    """An individual entry cannot fit within the configured byte limit."""


@dataclass
class Entry:
    """A value and its direct handles into the LRU and expiration structures."""

    value: str
    byte_size: int
    lru_node: Node
    expires_at: Optional[int] = None


class MiniRedis:
    """Single-threaded store; only successful GET/SET update recency.

    The clock is injectable so expiration tests need no waiting. Monotonic
    time avoids expiration changes when the operating system clock changes.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._data = HashMap()
        self._lru = DoublyLinkedList()
        self._expiry = MinHeap()
        self.used_memory = 0
        self.maxmemory = 0
        self.evicted_keys = 0

    def _now_ns(self) -> int:
        """Convert the injected seconds clock to integral nanoseconds.

        Deadlines then add integer durations exactly, including large valid
        EXPIRE arguments that would lose whole seconds in a float deadline.
        """
        return int(self._clock() * 1_000_000_000)

    def _remove_entry(self, key: str) -> bool:
        """Remove the same key from data, LRU and TTL, updating bytes once."""
        entry = self._data.get(key)
        if entry is None:
            return False
        self._expiry.remove(key)
        self._lru.remove_node(entry.lru_node)
        self._data.remove(key)
        self.used_memory -= entry.byte_size
        return True

    def _purge_at(self, now: int) -> int:
        """Repeatedly remove the earliest due timer; future timers are untouched."""
        removed = 0
        while self._expiry.size():
            deadline, key = self._expiry.peek()
            if deadline > now:
                break
            self._expiry.pop()
            if self._remove_entry(key):
                removed += 1
        return removed

    def purge_expired(self) -> int:
        """Delete all keys that have expired at this operation's start."""
        return self._purge_at(self._now_ns())

    def _evict_to_limit(self) -> None:
        """Evict the least recently used entries until the byte limit is met."""
        while self.maxmemory > 0 and self.used_memory > self.maxmemory:
            oldest = self._lru.back
            if oldest is None:
                break
            self._remove_entry(oldest.data)
            self.evicted_keys += 1

    def set(self, key: str, value: str) -> None:
        """Store a string, clear its old TTL and enforce the LRU byte budget.

        Oversized writes fail before changing the existing value, TTL or LRU.
        Expired keys are still cleaned before considering a write.
        """
        self.purge_expired()
        byte_size = len(key.encode("utf-8")) + len(value.encode("utf-8"))
        if self.maxmemory > 0 and byte_size > self.maxmemory:
            raise OutOfMemoryError("entry exceeds maxmemory")
        entry = self._data.get(key)
        if entry is None:
            node = self._lru.insert_front(key)
            self._data.put(key, Entry(value, byte_size, node))
            self.used_memory += byte_size
        else:
            self.used_memory += byte_size - entry.byte_size
            entry.value = value
            entry.byte_size = byte_size
            entry.expires_at = None
            self._expiry.remove(key)
            self._lru.move_to_front(entry.lru_node)
        self._evict_to_limit()

    def get(self, key: str) -> Optional[str]:
        """Return a live value and mark it most recently used."""
        self.purge_expired()
        entry = self._data.get(key)
        if entry is None:
            return None
        self._lru.move_to_front(entry.lru_node)
        return entry.value

    def delete(self, key: str) -> bool:
        """Delete a live key and all associated bookkeeping."""
        self.purge_expired()
        return self._remove_entry(key)

    def exists(self, key: str) -> bool:
        """Check existence without updating LRU recency."""
        self.purge_expired()
        return self._data.contains(key)

    def dbsize(self) -> int:
        """Return the number of live keys after heap-driven cleanup."""
        self.purge_expired()
        return self._data.size()

    def keys(self) -> List[str]:
        """Return all live keys, with no ordering or pattern matching guarantee."""
        self.purge_expired()
        return list(self._data.keys())

    def config_set_maxmemory(self, byte_limit: int) -> None:
        """Set a nonnegative byte limit; zero means unlimited.

        Reducing the limit immediately applies the existing LRU policy.
        """
        if isinstance(byte_limit, bool) or not isinstance(byte_limit, int) or byte_limit < 0:
            raise ValueError("maxmemory must be a nonnegative integer")
        self.purge_expired()
        self.maxmemory = byte_limit
        self._evict_to_limit()

    def info_memory(self) -> str:
        """Report logical UTF-8 bytes, the configured limit and LRU removals."""
        self.purge_expired()
        return (
            "used_memory:{}\nmaxmemory:{}\nevicted_keys:{}".format(
                self.used_memory, self.maxmemory, self.evicted_keys
            )
        )

    def expire(self, key: str, seconds: int) -> bool:
        """Set or replace a key's deadline; nonpositive durations delete it."""
        now = self._now_ns()
        self._purge_at(now)
        entry = self._data.get(key)
        if entry is None:
            return False
        if seconds <= 0:
            self._remove_entry(key)
        else:
            entry.expires_at = now + seconds * 1_000_000_000
            self._expiry.push((entry.expires_at, key))
        return True

    def ttl(self, key: str) -> int:
        """Return floored remaining seconds, -1 without TTL, or -2 if missing."""
        now = self._now_ns()
        self._purge_at(now)
        entry = self._data.get(key)
        if entry is None:
            return -2
        if entry.expires_at is None:
            return -1
        return (entry.expires_at - now) // 1_000_000_000
