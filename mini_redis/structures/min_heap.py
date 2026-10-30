"""An indexed minimum heap for physical TTL updates and deletion."""

from typing import Optional, Tuple

from .dynamic_array import DynamicArray
from .hash_map import HashMap

Expiry = Tuple[float, str]


class MinHeap:
    """Order (deadline, key) pairs and keep exactly one entry per key.

    The custom hash map tracks each key's array position. Updating an expiry
    or deleting a key therefore removes the old timer immediately in O(log n)
    expected time, without accumulating obsolete heap records.
    """

    def __init__(self) -> None:
        self._items = DynamicArray()  # type: DynamicArray[Expiry]
        self._positions = HashMap()  # type: HashMap[int]

    def __len__(self) -> int:
        return len(self._items)

    def size(self) -> int:
        return len(self._items)

    def peek(self) -> Optional[Expiry]:
        """Read the earliest timer in O(1), or None when empty."""
        return self._items[0] if len(self._items) else None

    def _swap(self, first: int, second: int) -> None:
        left = self._items[first]
        right = self._items[second]
        self._items[first] = right
        self._items[second] = left
        self._positions.put(right[1], first)
        self._positions.put(left[1], second)

    def _heapify_up(self, index: int) -> int:
        while index > 0:
            parent = (index - 1) // 2
            if self._items[parent] <= self._items[index]:
                break
            self._swap(parent, index)
            index = parent
        return index

    def _heapify_down(self, index: int) -> int:
        while True:
            smallest = index
            left = index * 2 + 1
            right = left + 1
            if left < len(self._items) and self._items[left] < self._items[smallest]:
                smallest = left
            if right < len(self._items) and self._items[right] < self._items[smallest]:
                smallest = right
            if smallest == index:
                return index
            self._swap(index, smallest)
            index = smallest

    def push(self, item: Expiry) -> None:
        """Insert a timer or replace that key's deadline in O(log n)."""
        key = item[1]
        index = self._positions.get(key)
        if index is None:
            index = len(self._items)
            self._items.append(item)
            self._positions.put(key, index)
            self._heapify_up(index)
            return
        previous = self._items[index]
        self._items[index] = item
        if item < previous:
            self._heapify_up(index)
        else:
            self._heapify_down(index)

    def pop(self) -> Optional[Expiry]:
        """Remove the earliest timer in O(log n), or None when empty."""
        first = self.peek()
        if first is None:
            return None
        self.remove(first[1])
        return first

    def remove(self, key: str) -> bool:
        """Remove a key's timer in O(log n) without searching the heap."""
        index = self._positions.get(key)
        if index is None:
            return False
        last = self._items.pop()
        self._positions.remove(key)
        if index < len(self._items):
            self._items[index] = last
            self._positions.put(last[1], index)
            if index > 0 and self._items[index] < self._items[(index - 1) // 2]:
                self._heapify_up(index)
            else:
                self._heapify_down(index)
        return True
