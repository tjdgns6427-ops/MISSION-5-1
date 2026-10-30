"""A doubly linked list with constant-time node operations."""

from typing import Generic, Iterator, Optional, TypeVar

T = TypeVar("T")


class Node(Generic[T]):
    """Store data and neighboring links; retain ownership for safe removal."""

    __slots__ = ("data", "prev", "next", "_owner")

    def __init__(self, data: T) -> None:
        self.data = data
        self.prev = None  # type: Optional[Node[T]]
        self.next = None  # type: Optional[Node[T]]
        self._owner = None  # type: Optional[DoublyLinkedList[T]]


class DoublyLinkedList(Generic[T]):
    """Keep direct head/tail links and move known nodes without a search."""

    def __init__(self) -> None:
        self._front = None  # type: Optional[Node[T]]
        self._back = None  # type: Optional[Node[T]]
        self._length = 0

    @property
    def front(self) -> Optional[Node[T]]:
        return self._front

    @property
    def back(self) -> Optional[Node[T]]:
        return self._back

    def __len__(self) -> int:
        return self._length

    def size(self) -> int:
        return self._length

    def insert_front(self, data: T) -> Node[T]:
        """Create a front node in O(1) and return its stable handle."""
        node = Node(data)
        node._owner = self
        node.next = self._front
        if self._front is None:
            self._back = node
        else:
            self._front.prev = node
        self._front = node
        self._length += 1
        return node

    def insert_back(self, data: T) -> Node[T]:
        """Create a back node in O(1) and return its stable handle."""
        node = Node(data)
        node._owner = self
        node.prev = self._back
        if self._back is None:
            self._front = node
        else:
            self._back.next = node
        self._back = node
        self._length += 1
        return node

    def _check_owner(self, node: Node[T]) -> None:
        if not isinstance(node, Node) or node._owner is not self:
            raise ValueError("node does not belong to this list")

    def _unlink(self, node: Node[T]) -> None:
        """Detach neighboring links without changing size or ownership."""
        if node.prev is None:
            self._front = node.next
        else:
            node.prev.next = node.next
        if node.next is None:
            self._back = node.prev
        else:
            node.next.prev = node.prev

    def remove_node(self, node: Node[T]) -> T:
        """Remove a known node in O(1); reject foreign or removed nodes."""
        self._check_owner(node)
        self._unlink(node)
        node.prev = None
        node.next = None
        node._owner = None
        self._length -= 1
        return node.data

    def remove_front(self) -> Optional[T]:
        if self._front is None:
            return None
        return self.remove_node(self._front)

    def remove_back(self) -> Optional[T]:
        if self._back is None:
            return None
        return self.remove_node(self._back)

    def move_to_front(self, node: Node[T]) -> None:
        """Move the same node to the front in O(1), retaining its identity."""
        self._check_owner(node)
        if node is self._front:
            return
        self._unlink(node)
        node.prev = None
        node.next = self._front
        self._front.prev = node
        self._front = node

    def __iter__(self) -> Iterator[T]:
        node = self._front
        while node is not None:
            yield node.data
            node = node.next
