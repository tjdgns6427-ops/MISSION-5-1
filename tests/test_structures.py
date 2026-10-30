"""Independent data-structure tests, including collisions and heap updates."""

import random
import unittest

from mini_redis.structures.dynamic_array import DynamicArray
from mini_redis.structures.hash_map import HashMap
from mini_redis.structures.linked_list import DoublyLinkedList, Node
from mini_redis.structures.min_heap import MinHeap


class DynamicArrayTests(unittest.TestCase):
    def test_append_grows_capacity_without_losing_values(self):
        array = DynamicArray(initial_capacity=2)
        array.append("a")
        array.append("b")
        self.assertEqual(array.capacity, 2)
        array.append("c")
        self.assertEqual(array.capacity, 4)
        self.assertEqual(list(array), ["a", "b", "c"])

    def test_get_set_remove_pop_and_indexing(self):
        array = DynamicArray()
        for value in ("a", "b", "c"):
            array.append(value)
        self.assertEqual(array.get(1), "b")
        array.set(1, "B")
        self.assertEqual(array[1], "B")
        array[0] = "A"
        self.assertEqual(array.remove(1), "B")
        self.assertEqual(list(array), ["A", "c"])
        self.assertEqual(array.pop(), "c")
        self.assertEqual(array.pop(), "A")
        self.assertEqual(len(array), 0)
        with self.assertRaises(IndexError):
            array.pop()

    def test_growth_repeatedly_preserves_order(self):
        array = DynamicArray(initial_capacity=1)
        for number in range(200):
            array.append(number)
        self.assertEqual(list(array), list(range(200)))
        self.assertGreaterEqual(array.capacity, 200)
        for number in reversed(range(200)):
            self.assertEqual(array.pop(), number)

    def test_out_of_bounds_access_is_rejected(self):
        array = DynamicArray()
        array.append("x")
        for action in (lambda: array.get(1), lambda: array.set(1, "y"), lambda: array.remove(1)):
            with self.assertRaises(IndexError):
                action()


class LinkedListTests(unittest.TestCase):
    def test_empty_removal(self):
        linked = DoublyLinkedList()
        self.assertIsNone(linked.front)
        self.assertIsNone(linked.back)
        self.assertIsNone(linked.remove_front())
        self.assertIsNone(linked.remove_back())
        self.assertEqual(linked.size(), 0)

    def test_insert_at_both_ends_and_remove_at_both_ends(self):
        linked = DoublyLinkedList()
        middle = linked.insert_back("middle")
        first = linked.insert_front("first")
        last = linked.insert_back("last")
        self.assertEqual(list(linked), ["first", "middle", "last"])
        self.assertIs(linked.front, first)
        self.assertIs(linked.back, last)
        self.assertIs(first.next, middle)
        self.assertIs(middle.prev, first)
        self.assertIs(middle.next, last)
        self.assertIs(last.prev, middle)
        self.assertEqual(linked.remove_front(), "first")
        self.assertEqual(linked.remove_back(), "last")
        self.assertIs(linked.front, middle)
        self.assertIs(linked.back, middle)
        self.assertEqual(linked.remove_back(), "middle")
        self.assertEqual(len(linked), 0)

    def test_remove_middle_node_repairs_neighbors(self):
        linked = DoublyLinkedList()
        first = linked.insert_back("a")
        middle = linked.insert_back("b")
        last = linked.insert_back("c")
        self.assertEqual(linked.remove_node(middle), "b")
        self.assertIs(first.next, last)
        self.assertIs(last.prev, first)
        self.assertIsNone(middle.prev)
        self.assertIsNone(middle.next)
        self.assertEqual(list(linked), ["a", "c"])
        self.assertEqual(len(linked), 2)

    def test_move_last_middle_and_first_to_front(self):
        linked = DoublyLinkedList()
        first = linked.insert_back("a")
        middle = linked.insert_back("b")
        last = linked.insert_back("c")
        linked.move_to_front(last)
        self.assertEqual(list(linked), ["c", "a", "b"])
        self.assertIs(linked.back, middle)
        linked.move_to_front(first)
        self.assertEqual(list(linked), ["a", "c", "b"])
        linked.move_to_front(first)
        self.assertEqual(list(linked), ["a", "c", "b"])
        self.assertEqual(len(linked), 3)

    def test_single_node_move_and_remove(self):
        linked = DoublyLinkedList()
        node = linked.insert_front("a")
        linked.move_to_front(node)
        self.assertEqual(list(linked), ["a"])
        self.assertEqual(linked.remove_node(node), "a")
        self.assertIsNone(linked.front)
        self.assertIsNone(linked.back)

    def test_foreign_and_detached_nodes_are_rejected(self):
        linked = DoublyLinkedList()
        other = DoublyLinkedList()
        foreign = other.insert_back("foreign")
        detached = Node("detached")
        removed = linked.insert_back("removed")
        linked.remove_node(removed)
        for node in (foreign, detached, removed):
            with self.subTest(data=node.data):
                with self.assertRaises(ValueError):
                    linked.remove_node(node)
                with self.assertRaises(ValueError):
                    linked.move_to_front(node)
        self.assertEqual(list(other), ["foreign"])


class CollidingHashMap(HashMap):
    """Force every key into one bucket to test separate chaining."""

    @staticmethod
    def _hash(key):
        return 0


class HashMapTests(unittest.TestCase):
    def test_put_get_replace_remove_and_defaults(self):
        table = HashMap()
        sentinel = object()
        self.assertIs(table.get("missing", sentinel), sentinel)
        self.assertFalse(table.contains("missing"))
        self.assertFalse(table.remove("missing"))
        table.put("a", "one")
        table.put("a", "two")
        self.assertEqual(table.get("a"), "two")
        self.assertEqual(table.size(), 1)
        self.assertTrue(table.contains("a"))
        self.assertTrue(table.remove("a"))
        self.assertEqual(len(table), 0)

    def test_none_value_is_distinct_from_a_missing_key(self):
        table = HashMap()
        table.put("a", None)
        self.assertTrue(table.contains("a"))
        self.assertIsNone(table.get("a"))
        self.assertEqual(table.size(), 1)
        self.assertTrue(table.remove("a"))

    def test_collisions_preserve_all_entries_and_support_chain_removal(self):
        table = CollidingHashMap()
        for key in ("head", "middle", "tail"):
            table.put(key, key.upper())
        self.assertEqual(table.size(), 3)
        for key in ("middle", "head", "tail"):
            self.assertEqual(table.get(key), key.upper())
            self.assertTrue(table.remove(key))
            self.assertFalse(table.contains(key))
        self.assertEqual(table.size(), 0)

    def test_load_factor_threshold_doubles_buckets(self):
        table = HashMap(initial_capacity=4)
        for key in ("a", "b", "c"):
            table.put(key, key)
        self.assertEqual(table.capacity, 4)
        table.put("d", "d")
        self.assertEqual(table.capacity, 8)
        table.put("d", "updated")
        self.assertEqual(table.capacity, 8)
        self.assertEqual(table.size(), 4)

    def test_multiple_resizes_keep_values_and_keys(self):
        table = HashMap(initial_capacity=2)
        for number in range(400):
            table.put("key:" + str(number), number)
        self.assertEqual(table.size(), 400)
        for number in range(400):
            self.assertEqual(table.get("key:" + str(number)), number)
        for number in range(0, 400, 2):
            self.assertTrue(table.remove("key:" + str(number)))
        expected = sorted("key:" + str(number) for number in range(1, 400, 2))
        self.assertEqual(sorted(table.keys()), expected)
        self.assertEqual(table.size(), 200)

    def test_empty_and_unicode_keys(self):
        table = HashMap()
        for key in ("", "이름", "😀", "a\x00b"):
            table.put(key, key + "value")
        self.assertEqual(table.size(), 4)
        for key in ("", "이름", "😀", "a\x00b"):
            self.assertEqual(table.get(key), key + "value")

    def test_many_collisions_survive_resizing(self):
        table = CollidingHashMap(initial_capacity=2)
        for number in range(50):
            table.put(str(number), number)
        for number in range(50):
            self.assertEqual(table.get(str(number)), number)
        for number in range(50):
            self.assertTrue(table.remove(str(number)))
        self.assertEqual(table.size(), 0)


class MinHeapTests(unittest.TestCase):
    def test_empty_and_single_entry(self):
        heap = MinHeap()
        self.assertIsNone(heap.peek())
        self.assertIsNone(heap.pop())
        self.assertFalse(heap.remove("missing"))
        heap.push((3, "a"))
        self.assertEqual(heap.peek(), (3, "a"))
        self.assertEqual(heap.size(), 1)
        self.assertEqual(heap.pop(), (3, "a"))
        self.assertEqual(len(heap), 0)

    def test_unordered_insertions_pop_in_deadline_order(self):
        heap = MinHeap()
        entries = [(8, "h"), (2, "b"), (5, "e"), (1, "a"), (3, "c"), (7, "g"), (4, "d")]
        for entry in entries:
            heap.push(entry)
        self.assertEqual([heap.pop() for _ in entries], sorted(entries))

    def test_equal_deadlines_remain_valid(self):
        heap = MinHeap()
        for key in ("z", "a", "m"):
            heap.push((5, key))
        actual = [heap.pop(), heap.pop(), heap.pop()]
        self.assertEqual(sorted(actual), [(5, "a"), (5, "m"), (5, "z")])

    def test_upsert_moves_entries_up_or_down_without_duplicates(self):
        heap = MinHeap()
        heap.push((2, "a"))
        heap.push((4, "b"))
        heap.push((6, "c"))
        heap.push((1, "c"))
        self.assertEqual(heap.peek(), (1, "c"))
        self.assertEqual(heap.size(), 3)
        heap.push((10, "c"))
        self.assertEqual(heap.peek(), (2, "a"))
        self.assertEqual([heap.pop(), heap.pop(), heap.pop()], [(2, "a"), (4, "b"), (10, "c")])

    def test_remove_root_middle_and_last(self):
        heap = MinHeap()
        for deadline, key in ((1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e")):
            heap.push((deadline, key))
        self.assertTrue(heap.remove("a"))
        self.assertTrue(heap.remove("c"))
        self.assertTrue(heap.remove("e"))
        self.assertFalse(heap.remove("a"))
        self.assertEqual([heap.pop(), heap.pop()], [(2, "b"), (4, "d")])

    def test_remove_then_reinsert_same_key(self):
        heap = MinHeap()
        heap.push((1, "a"))
        heap.remove("a")
        heap.push((10, "a"))
        self.assertEqual(heap.pop(), (10, "a"))
        self.assertIsNone(heap.pop())

    def test_randomized_updates_and_removals_match_sorted_reference(self):
        rng = random.Random(146)
        heap = MinHeap()
        expected = []
        for _ in range(600):
            key = "key:" + str(rng.randrange(40))
            action = rng.randrange(3)
            old = next((entry for entry in expected if entry[1] == key), None)
            if action == 0:
                deadline = rng.randrange(500)
                if old is not None:
                    expected.remove(old)
                entry = (deadline, key)
                expected.append(entry)
                heap.push(entry)
            elif action == 1:
                self.assertEqual(heap.remove(key), old is not None)
                if old is not None:
                    expected.remove(old)
            elif expected:
                first = min(expected)
                self.assertEqual(heap.pop(), first)
                expected.remove(first)
            else:
                self.assertIsNone(heap.pop())
            self.assertEqual(heap.size(), len(expected))
            self.assertEqual(heap.peek(), min(expected) if expected else None)
        self.assertEqual([heap.pop() for _ in expected], sorted(expected))


if __name__ == "__main__":
    unittest.main()
