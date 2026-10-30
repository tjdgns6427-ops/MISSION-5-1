"""An array with explicit capacity growth and indexed storage."""

from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class DynamicArray(Generic[T]):
    """Grow a fixed-size backing array by doubling when it becomes full.

    Python lists are used only as fixed-capacity indexed memory. Appending to
    the list or using a built-in mapping is unnecessary for this structure.
    """

    def __init__(self, initial_capacity: int = 4) -> None:
        if not isinstance(initial_capacity, int) or initial_capacity < 1:
            raise ValueError("initial_capacity must be a positive integer")
        self._capacity = initial_capacity
        self._length = 0
        self._storage = [None] * self._capacity

    @property
    def capacity(self) -> int:
        """Return allocated slots, including unused capacity."""
        return self._capacity

    def __len__(self) -> int:
        return self._length

    def size(self) -> int:
        return self._length

    def _normalize_index(self, index: int) -> int:
        if not isinstance(index, int):
            raise TypeError("array indices must be integers")
        if index < 0:
            index += self._length
        if index < 0 or index >= self._length:
            raise IndexError("array index out of range")
        return index

    def _grow(self) -> None:
        new_storage = [None] * (self._capacity * 2)
        for index in range(self._length):
            new_storage[index] = self._storage[index]
        self._storage = new_storage
        self._capacity *= 2

    def append(self, value: T) -> None:
        """Append in amortized O(1), doubling capacity when necessary."""
        if self._length == self._capacity:
            self._grow()
        self._storage[self._length] = value
        self._length += 1

    def get(self, index: int) -> T:
        """Read an occupied slot in O(1)."""
        return self._storage[self._normalize_index(index)]

    def set(self, index: int, value: T) -> None:
        """Replace an occupied slot in O(1)."""
        self._storage[self._normalize_index(index)] = value

    def remove(self, index: int) -> T:
        """Remove a slot and shift later values left in O(n)."""
        index = self._normalize_index(index)
        value = self._storage[index]
        for position in range(index, self._length - 1):
            self._storage[position] = self._storage[position + 1]
        self._length -= 1
        self._storage[self._length] = None
        return value

    def pop(self, index: int = -1) -> T:
        """Remove the last item in O(1), or another item in O(n)."""
        return self.remove(index)

    def __getitem__(self, index: int) -> T:
        return self.get(index)

    def __setitem__(self, index: int, value: T) -> None:
        self.set(index, value)

    def __iter__(self) -> Iterator[T]:
        for index in range(self._length):
            yield self._storage[index]
