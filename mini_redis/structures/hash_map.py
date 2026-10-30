"""A UTF-8 hash map with separate chaining and explicit rehashing."""

from typing import Generic, TypeVar

from .dynamic_array import DynamicArray
from .linked_list import DoublyLinkedList

T = TypeVar("T")


class HashMap(Generic[T]):
    """Map string keys to values using handwritten FNV-1a and list chains.

    A bucket table doubles when the load factor becomes greater than 0.75.
    Hash lookup is expected O(1); a fully colliding chain is O(n).
    """

    def __init__(self, initial_capacity: int = 8) -> None:
        if not isinstance(initial_capacity, int) or initial_capacity < 1:
            raise ValueError("initial_capacity must be a positive integer")
        self._capacity = initial_capacity
        self._length = 0
        self._buckets = self._make_buckets(initial_capacity)

    @staticmethod
    def _make_buckets(capacity: int) -> DynamicArray:
        buckets = DynamicArray(capacity)
        for _ in range(capacity):
            buckets.append(DoublyLinkedList())
        return buckets

    @staticmethod
    def _hash(key: str) -> int:
        """Compute deterministic 64-bit FNV-1a over UTF-8 bytes."""
        if not isinstance(key, str):
            raise TypeError("hash map keys must be strings")
        result = 14695981039346656037
        for byte in key.encode("utf-8"):
            result ^= byte
            result = (result * 1099511628211) & 0xFFFFFFFFFFFFFFFF
        return result

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return self._length

    def size(self) -> int:
        return self._length

    def _bucket(self, key: str) -> DoublyLinkedList:
        return self._buckets[self._hash(key) % self._capacity]

    def _find_node(self, key: str):
        node = self._bucket(key).front
        while node is not None:
            if node.data[0] == key:
                return node
            node = node.next
        return None

    def put(self, key: str, value: T) -> None:
        """Insert or replace a value, rehashing after a new-key insertion."""
        node = self._find_node(key)
        if node is not None:
            node.data = (key, value)
            return
        self._bucket(key).insert_back((key, value))
        self._length += 1
        if self._length * 4 > self._capacity * 3:
            self._resize()

    def _resize(self) -> None:
        old_buckets = self._buckets
        self._capacity *= 2
        self._buckets = self._make_buckets(self._capacity)
        for bucket in old_buckets:
            for key, value in bucket:
                self._bucket(key).insert_back((key, value))

    def get(self, key: str, default=None):
        """Return the value, or the caller's default for a missing key."""
        node = self._find_node(key)
        return default if node is None else node.data[1]

    def contains(self, key: str) -> bool:
        """Check presence independently of the stored value."""
        return self._find_node(key) is not None

    def remove(self, key: str) -> bool:
        """Remove a key and report whether it was present."""
        bucket = self._bucket(key)
        node = bucket.front
        while node is not None:
            if node.data[0] == key:
                bucket.remove_node(node)
                self._length -= 1
                return True
            node = node.next
        return False

    def keys(self):
        """Return a snapshot of all keys in unspecified bucket order."""
        result = DynamicArray(max(1, self._length))
        for bucket in self._buckets:
            for key, _ in bucket:
                result.append(key)
        return result
