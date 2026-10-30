"""Command parsing, Redis-style output, and error regression tests."""

import json
import unittest

from mini_redis.commands import CommandProcessor
from mini_redis.store import MiniRedis
from tests.test_store import FakeClock


INTEGER_ERROR = "(error) ERR value is not an integer or out of range"
OOM_ERROR = "(error) OOM command not allowed when used_memory > 'maxmemory'"


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.store = MiniRedis(clock=self.clock)
        self.commands = CommandProcessor(store=self.store)

    def execute(self, line):
        return self.commands.execute(line)

    def test_basic_string_commands_and_output(self):
        self.assertEqual(self.execute('SET user:1 "Alice"'), "OK")
        self.assertEqual(self.execute("GET user:1"), '"Alice"')
        self.assertEqual(self.execute("EXISTS user:1"), "(integer) 1")
        self.assertEqual(self.execute("DBSIZE"), "(integer) 1")
        self.assertEqual(self.execute("DEL user:1"), "(integer) 1")
        self.assertEqual(self.execute("DEL user:1"), "(integer) 0")
        self.assertEqual(self.execute("GET user:1"), "(nil)")
        self.assertEqual(self.execute("EXISTS user:1"), "(integer) 0")

    def test_empty_line_is_ignored(self):
        for line in ("", " ", "\t  "):
            self.assertEqual(self.execute(line), "")

    def test_command_names_are_case_insensitive(self):
        self.assertEqual(self.execute('sEt a "hello world"'), "OK")
        self.assertEqual(self.execute("gEt a"), '"hello world"')
        self.assertEqual(self.execute("cOnFiG sEt MaXmEmOrY 100"), "OK")
        self.assertIn("maxmemory:100", self.execute("iNfO MeMoRy"))

    def test_double_quoted_spaces_and_empty_strings(self):
        self.assertEqual(self.execute('SET "my key" "hello world"'), "OK")
        self.assertEqual(self.execute('GET "my key"'), '"hello world"')
        self.assertEqual(self.execute('SET "" ""'), "OK")
        self.assertEqual(self.execute('GET ""'), '""')

    def test_quoted_unicode_value_is_not_ascii_escaped(self):
        self.assertEqual(self.execute('SET 이름 "홍길동 😀"'), "OK")
        self.assertEqual(self.execute("GET 이름"), '"홍길동 😀"')

    def test_output_quotes_and_backslashes_are_escaped(self):
        value = 'a"b\\c'
        self.store.set("special", value)
        self.assertEqual(self.execute("GET special"), json.dumps(value, ensure_ascii=False))

    def test_keys_numbered_output(self):
        self.execute("SET a 1")
        self.execute("SET b 2")
        lines = self.execute("KEYS").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith('1) ') or lines[0].startswith('1. '))
        self.assertTrue(lines[1].startswith('2) ') or lines[1].startswith('2. '))
        actual = sorted(line.split(" ", 1)[1] for line in lines)
        self.assertEqual(actual, ['"a"', '"b"'])

    def test_empty_keys_output(self):
        self.assertEqual(self.execute("KEYS"), "(empty array)")

    def test_expiry_command_outputs(self):
        self.assertEqual(self.execute("EXPIRE absent 3"), "(integer) 0")
        self.assertEqual(self.execute("TTL absent"), "(integer) -2")
        self.execute("SET a x")
        self.assertEqual(self.execute("TTL a"), "(integer) -1")
        self.assertEqual(self.execute("EXPIRE a 3"), "(integer) 1")
        self.assertEqual(self.execute("TTL a"), "(integer) 3")
        self.clock.advance(3)
        self.assertEqual(self.execute("TTL a"), "(integer) -2")
        self.assertEqual(self.execute("DBSIZE"), "(integer) 0")

    def test_negative_and_zero_expiry(self):
        for seconds in ("0", "-1"):
            self.execute("SET a x")
            self.assertEqual(self.execute("EXPIRE a " + seconds), "(integer) 1")
            self.assertEqual(self.execute("GET a"), "(nil)")

    def test_info_memory_has_required_values(self):
        self.execute("CONFIG SET maxmemory 10")
        self.execute("SET a 1")
        self.assertEqual(
            self.execute("INFO memory"),
            "used_memory:2\nmaxmemory:10\nevicted_keys:0",
        )

    def test_assignment_lru_example(self):
        self.assertEqual(self.execute("CONFIG SET maxmemory 30"), "OK")
        self.execute('SET user:1 "Alice"')
        self.execute('SET user:2 "Bob"')
        self.execute('SET user:3 "Charlie"')
        self.assertEqual(self.execute("GET user:1"), "(nil)")
        self.assertEqual(
            self.execute("INFO memory"),
            "used_memory:22\nmaxmemory:30\nevicted_keys:1",
        )

    def test_unknown_command_error(self):
        self.assertEqual(
            self.execute("HELLO"),
            "(error) ERR unknown command 'HELLO'",
        )

    def test_wrong_number_of_arguments(self):
        invalid = (
            ("SET", "SET"),
            ("SET a", "SET"),
            ("SET a b c", "SET"),
            ("GET", "GET"),
            ("GET a b", "GET"),
            ("DEL", "DEL"),
            ("DEL a b", "DEL"),
            ("EXISTS", "EXISTS"),
            ("DBSIZE extra", "DBSIZE"),
            ("KEYS *", "KEYS"),
            ("CONFIG SET maxmemory", "CONFIG"),
            ("CONFIG SET maxmemory 1 extra", "CONFIG"),
            ("INFO", "INFO"),
            ("INFO memory extra", "INFO"),
            ("EXPIRE a", "EXPIRE"),
            ("EXPIRE a 1 extra", "EXPIRE"),
            ("TTL", "TTL"),
        )
        for line, name in invalid:
            with self.subTest(line=line):
                self.assertEqual(
                    self.execute(line),
                    "(error) ERR wrong number of arguments for '" + name + "' command",
                )

    def test_invalid_integers_and_signed_64_bit_overflow(self):
        self.execute("SET a x")
        invalid = (
            "abc", "1.0", "1e3", "0x10", "+", "--1", "1_000", "１２", "١٢",
            "9223372036854775808", "-9223372036854775809",
        )
        for number in invalid:
            for prefix in ("EXPIRE a ", "CONFIG SET maxmemory "):
                with self.subTest(prefix=prefix, number=number):
                    self.assertEqual(self.execute(prefix + number), INTEGER_ERROR)
        self.assertEqual(self.execute("GET a"), '"x"')
        self.assertEqual(self.execute("TTL a"), "(integer) -1")

    def test_negative_maxmemory_is_rejected(self):
        self.assertEqual(self.execute("CONFIG SET maxmemory -1"), INTEGER_ERROR)
        self.assertEqual(self.store.maxmemory, 0)

    def test_plus_sign_and_signed_64_bit_maximum_are_valid(self):
        self.assertEqual(self.execute("CONFIG SET maxmemory +100"), "OK")
        self.assertEqual(self.execute("CONFIG SET maxmemory 9223372036854775807"), "OK")
        self.execute("SET a x")
        self.assertEqual(self.execute("EXPIRE a +10"), "(integer) 1")

    def test_largest_expiry_does_not_overflow_or_exceed_requested_duration(self):
        self.execute("SET a x")
        self.assertEqual(self.execute("EXPIRE a 9223372036854775807"), "(integer) 1")
        ttl = int(self.execute("TTL a").split()[-1])
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 9223372036854775807)

    def test_extremely_long_integer_is_an_error_without_crashing(self):
        huge = "9" * 5000
        self.assertEqual(self.execute("CONFIG SET maxmemory " + huge), INTEGER_ERROR)
        self.assertEqual(self.execute("EXPIRE a " + huge), INTEGER_ERROR)
        self.assertEqual(self.execute("SET a good"), "OK")

    def test_unclosed_quote_returns_an_error_and_repl_remains_usable(self):
        self.assertTrue(self.execute('SET a "unclosed').startswith("(error) ERR"))
        self.assertEqual(self.execute("SET a good"), "OK")
        self.assertEqual(self.execute("GET a"), '"good"')

    def test_oom_output_and_error_recovery(self):
        self.execute("CONFIG SET maxmemory 2")
        self.execute("SET a x")
        self.assertEqual(self.execute("SET long large"), OOM_ERROR)
        self.assertEqual(self.execute("GET a"), '"x"')
        self.assertEqual(self.execute("SET b y"), "OK")


if __name__ == "__main__":
    unittest.main()
