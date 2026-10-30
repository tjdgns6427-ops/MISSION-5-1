"""Behavioral tests with a controlled clock: no real waiting is needed."""

import unittest

from mini_redis.store import MiniRedis, OutOfMemoryError


class FakeClock:
    """A monotonic test clock that advances only when a test requests it."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.store = MiniRedis(clock=self.clock)

    def test_empty_store(self):
        self.assertIsNone(self.store.get("missing"))
        self.assertFalse(self.store.exists("missing"))
        self.assertFalse(self.store.delete("missing"))
        self.assertEqual(self.store.dbsize(), 0)
        self.assertEqual(self.store.keys(), [])
        self.assertEqual(self.store.ttl("missing"), -2)

    def test_store_read_replace_and_delete(self):
        self.store.set("name", "Alice")
        self.assertEqual(self.store.get("name"), "Alice")
        self.assertTrue(self.store.exists("name"))
        self.assertEqual(self.store.dbsize(), 1)
        self.assertEqual(self.store.used_memory, 9)
        self.store.set("name", "Bob")
        self.assertEqual(self.store.get("name"), "Bob")
        self.assertEqual(self.store.dbsize(), 1)
        self.assertEqual(self.store.used_memory, 7)
        self.assertTrue(self.store.delete("name"))
        self.assertEqual(self.store.used_memory, 0)
        self.assertEqual(self.store.ttl("name"), -2)

    def test_utf8_memory_counts_bytes(self):
        self.store.set("이름", "홍길동😀")
        expected = len("이름".encode("utf-8")) + len("홍길동😀".encode("utf-8"))
        self.assertEqual(self.store.used_memory, expected)
        self.store.set("이름", "가")
        self.assertEqual(self.store.used_memory, 9)
        self.store.delete("이름")
        self.assertEqual(self.store.used_memory, 0)

    def test_empty_strings_are_valid_data(self):
        self.store.set("", "")
        self.assertTrue(self.store.exists(""))
        self.assertEqual(self.store.get(""), "")
        self.assertEqual(self.store.dbsize(), 1)
        self.assertEqual(self.store.used_memory, 0)

    def test_expiry_status_and_fractional_remaining_time(self):
        self.assertFalse(self.store.expire("missing", 10))
        self.store.set("a", "x")
        self.assertEqual(self.store.ttl("a"), -1)
        self.assertTrue(self.store.expire("a", 3))
        self.assertEqual(self.store.ttl("a"), 3)
        self.clock.advance(0.25)
        self.assertEqual(self.store.ttl("a"), 2)
        self.clock.advance(2.75)
        self.assertIsNone(self.store.get("a"))
        self.assertEqual(self.store.ttl("a"), -2)
        self.assertEqual(self.store.used_memory, 0)
        self.assertEqual(self.store.evicted_keys, 0)

    def test_zero_and_negative_expiry_delete_immediately(self):
        for seconds in (0, -5):
            with self.subTest(seconds=seconds):
                self.store.set("a", "x")
                self.assertTrue(self.store.expire("a", seconds))
                self.assertFalse(self.store.exists("a"))
                self.assertEqual(self.store.used_memory, 0)

    def test_expiry_update_ignores_old_deadline(self):
        self.store.set("a", "x")
        self.store.expire("a", 2)
        self.clock.advance(1)
        self.store.expire("a", 10)
        self.clock.advance(2)
        self.assertEqual(self.store.get("a"), "x")
        self.assertEqual(self.store.ttl("a"), 8)
        self.clock.advance(8)
        self.assertFalse(self.store.exists("a"))

    def test_expiry_update_can_move_deadline_earlier(self):
        self.store.set("a", "x")
        self.store.expire("a", 100)
        self.store.expire("a", 1)
        self.clock.advance(1)
        self.assertFalse(self.store.exists("a"))

    def test_successful_overwrite_resets_expiry(self):
        self.store.set("a", "old")
        self.store.expire("a", 1)
        self.store.set("a", "new")
        self.assertEqual(self.store.ttl("a"), -1)
        self.clock.advance(2)
        self.assertEqual(self.store.get("a"), "new")

    def test_deleted_and_reinserted_key_survives_old_expiry(self):
        self.store.set("a", "old")
        self.store.expire("a", 1)
        self.assertTrue(self.store.delete("a"))
        self.store.set("a", "new")
        self.clock.advance(2)
        self.assertEqual(self.store.get("a"), "new")
        self.assertEqual(self.store.ttl("a"), -1)

    def test_expired_key_is_absent_for_every_key_operation(self):
        operations = (
            lambda: self.assertIsNone(self.store.get("a")),
            lambda: self.assertFalse(self.store.exists("a")),
            lambda: self.assertFalse(self.store.delete("a")),
            lambda: self.assertFalse(self.store.expire("a", 10)),
            lambda: self.assertEqual(self.store.ttl("a"), -2),
        )
        for operation in operations:
            self.store.set("a", "x")
            self.store.expire("a", 1)
            self.clock.advance(1)
            operation()
            self.assertEqual(self.store.used_memory, 0)

    def test_global_queries_remove_all_expired_keys(self):
        for query in (self.store.dbsize, self.store.keys, self.store.info_memory):
            self.store.set("a", "x")
            self.store.set("b", "y")
            self.store.expire("a", 1)
            self.store.expire("b", 1)
            self.clock.advance(1)
            query()
            self.assertEqual(self.store.used_memory, 0)
            self.assertEqual(self.store.dbsize(), 0)

    def test_many_equal_deadlines_expire_together(self):
        for number in range(50):
            key = "key:" + str(number)
            self.store.set(key, "value")
            self.store.expire(key, 5)
        self.clock.advance(5)
        self.assertEqual(self.store.dbsize(), 0)
        self.assertEqual(self.store.used_memory, 0)

    def test_expiry_heap_has_no_stale_entries_after_updates_or_delete(self):
        self.store.set("a", "x")
        for seconds in range(1, 200):
            self.store.expire("a", seconds)
        self.assertEqual(len(self.store._expiry), 1)
        self.store.delete("a")
        self.assertEqual(len(self.store._expiry), 0)

    def test_lru_evicts_oldest_and_get_refreshes_recency(self):
        self.store.config_set_maxmemory(4)
        self.store.set("a", "1")
        self.store.set("b", "2")
        self.assertEqual(self.store.get("a"), "1")
        self.store.set("c", "3")
        self.assertEqual(sorted(self.store.keys()), ["a", "c"])
        self.assertEqual(self.store.evicted_keys, 1)
        self.assertEqual(self.store.used_memory, 4)

    def test_successful_set_refreshes_recency(self):
        self.store.config_set_maxmemory(4)
        self.store.set("a", "1")
        self.store.set("b", "2")
        self.store.set("a", "9")
        self.store.set("c", "3")
        self.assertEqual(sorted(self.store.keys()), ["a", "c"])

    def test_inspection_commands_do_not_refresh_lru(self):
        self.store.config_set_maxmemory(4)
        self.store.set("a", "1")
        self.store.set("b", "2")
        self.store.exists("a")
        self.store.expire("a", 100)
        self.store.ttl("a")
        self.store.keys()
        self.store.dbsize()
        self.store.info_memory()
        self.store.set("c", "3")
        self.assertFalse(self.store.exists("a"))
        self.assertTrue(self.store.exists("b"))

    def test_one_set_can_evict_multiple_keys(self):
        self.store.config_set_maxmemory(6)
        for key in ("a", "b", "c"):
            self.store.set(key, "1")
        self.store.set("d", "12345")
        self.assertEqual(self.store.keys(), ["d"])
        self.assertEqual(self.store.used_memory, 6)
        self.assertEqual(self.store.evicted_keys, 3)

    def test_overwrite_uses_size_difference_before_evicting(self):
        self.store.config_set_maxmemory(6)
        self.store.set("a", "123")
        self.store.set("b", "1")
        self.store.set("a", "4")
        self.assertEqual(sorted(self.store.keys()), ["a", "b"])
        self.assertEqual(self.store.used_memory, 4)
        self.assertEqual(self.store.evicted_keys, 0)

    def test_oversized_new_entry_does_not_evict_other_keys(self):
        self.store.config_set_maxmemory(4)
        self.store.set("a", "1")
        self.store.set("b", "2")
        with self.assertRaises(OutOfMemoryError):
            self.store.set("c", "12345")
        self.assertEqual(sorted(self.store.keys()), ["a", "b"])
        self.assertEqual(self.store.used_memory, 4)
        self.assertEqual(self.store.evicted_keys, 0)

    def test_oversized_overwrite_preserves_value_ttl_and_recency(self):
        self.store.config_set_maxmemory(4)
        self.store.set("a", "1")
        self.store.expire("a", 20)
        self.store.set("b", "2")
        with self.assertRaises(OutOfMemoryError):
            self.store.set("a", "too large")
        self.assertEqual(self.store.ttl("a"), 20)
        self.store.set("c", "3")
        self.assertFalse(self.store.exists("a"))
        self.assertEqual(sorted(self.store.keys()), ["b", "c"])

    def test_oversized_overwrite_preserves_old_value(self):
        self.store.config_set_maxmemory(4)
        self.store.set("a", "1")
        with self.assertRaises(OutOfMemoryError):
            self.store.set("a", "too large")
        self.assertEqual(self.store.get("a"), "1")
        self.assertEqual(self.store.used_memory, 2)

    def test_lowering_limit_enforces_lru_immediately(self):
        for key in ("a", "b", "c"):
            self.store.set(key, "1")
        self.store.config_set_maxmemory(3)
        self.assertEqual(self.store.keys(), ["c"])
        self.assertEqual(self.store.used_memory, 2)
        self.assertEqual(self.store.evicted_keys, 2)

    def test_zero_limit_is_unlimited(self):
        self.store.config_set_maxmemory(2)
        self.store.set("a", "1")
        self.store.config_set_maxmemory(0)
        self.store.set("b", "a long value")
        self.assertEqual(self.store.dbsize(), 2)
        self.assertEqual(self.store.evicted_keys, 0)

    def test_expired_data_is_removed_before_memory_eviction(self):
        self.store.config_set_maxmemory(4)
        self.store.set("a", "1")
        self.store.set("b", "2")
        self.store.expire("b", 1)
        self.clock.advance(1)
        self.store.set("c", "3")
        self.assertEqual(sorted(self.store.keys()), ["a", "c"])
        self.assertEqual(self.store.evicted_keys, 0)

    def test_evicted_expiry_cannot_delete_reinserted_key(self):
        self.store.config_set_maxmemory(2)
        self.store.set("a", "1")
        self.store.expire("a", 1)
        self.store.set("b", "2")
        self.store.set("a", "3")
        self.clock.advance(2)
        self.assertEqual(self.store.get("a"), "3")
        self.assertEqual(self.store.used_memory, 2)
        self.assertEqual(self.store.evicted_keys, 2)

    def test_memory_information(self):
        self.store.set("a", "1")
        self.assertEqual(
            self.store.info_memory(),
            "used_memory:2\nmaxmemory:0\nevicted_keys:0",
        )


if __name__ == "__main__":
    unittest.main()
