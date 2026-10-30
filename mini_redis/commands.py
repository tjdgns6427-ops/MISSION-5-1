"""Parse the assignment's ten commands and format Redis-style responses."""

import json
import re
import shlex
from typing import Optional

from .store import MiniRedis, OutOfMemoryError

INTEGER_ERROR = "(error) ERR value is not an integer or out of range"
OOM_ERROR = "(error) OOM command not allowed when used_memory > 'maxmemory'"
MIN_INTEGER = -(2 ** 63)
MAX_INTEGER = 2 ** 63 - 1


def parse_integer(token: str, nonnegative: bool = False) -> int:
    """Accept only signed ASCII decimal integers in the signed 64-bit range."""
    if re.fullmatch(r"[+-]?[0-9]+", token) is None:
        raise ValueError(INTEGER_ERROR)
    number = int(token)
    if number < MIN_INTEGER or number > MAX_INTEGER or (nonnegative and number < 0):
        raise ValueError(INTEGER_ERROR)
    return number


def quote(value: str) -> str:
    """Quote strings, preserving Korean text while escaping control characters."""
    return json.dumps(value, ensure_ascii=False)


class CommandProcessor:
    """A small explicit dispatcher, with no native key-value command registry."""

    def __init__(self, store: Optional[MiniRedis] = None):
        self.store = store if store is not None else MiniRedis()

    @staticmethod
    def _arity_error(command: str) -> str:
        return "(error) ERR wrong number of arguments for '{}' command".format(command)

    def execute(self, line: str) -> str:
        """Execute one line; malformed input becomes an error, keeping REPL alive."""
        try:
            args = shlex.split(line, comments=False, posix=True)
        except ValueError:
            return "(error) ERR syntax error"
        if not args:
            return ""
        command = args[0].upper()
        if command == "SET":
            if len(args) != 3:
                return self._arity_error(command)
            try:
                self.store.set(args[1], args[2])
            except OutOfMemoryError:
                return OOM_ERROR
            return "OK"
        if command == "GET":
            if len(args) != 2:
                return self._arity_error(command)
            value = self.store.get(args[1])
            return "(nil)" if value is None else quote(value)
        if command == "DEL":
            if len(args) != 2:
                return self._arity_error(command)
            return "(integer) {}".format(int(self.store.delete(args[1])))
        if command == "EXISTS":
            if len(args) != 2:
                return self._arity_error(command)
            return "(integer) {}".format(int(self.store.exists(args[1])))
        if command == "DBSIZE":
            if len(args) != 1:
                return self._arity_error(command)
            return "(integer) {}".format(self.store.dbsize())
        if command == "KEYS":
            if len(args) != 1:
                return self._arity_error(command)
            keys = self.store.keys()
            if not keys:
                return "(empty array)"
            return "\n".join(
                "{}) {}".format(index, quote(key))
                for index, key in enumerate(keys, start=1)
            )
        if command == "CONFIG":
            if len(args) != 4:
                return self._arity_error(command)
            if args[1].upper() != "SET" or args[2].lower() != "maxmemory":
                return "(error) ERR unsupported CONFIG option"
            try:
                limit = parse_integer(args[3], nonnegative=True)
            except ValueError:
                return INTEGER_ERROR
            self.store.config_set_maxmemory(limit)
            return "OK"
        if command == "INFO":
            if len(args) != 2:
                return self._arity_error(command)
            if args[1].lower() != "memory":
                return "(error) ERR unsupported INFO section"
            return self.store.info_memory()
        if command == "EXPIRE":
            if len(args) != 3:
                return self._arity_error(command)
            try:
                seconds = parse_integer(args[2])
            except ValueError:
                return INTEGER_ERROR
            return "(integer) {}".format(int(self.store.expire(args[1], seconds)))
        if command == "TTL":
            if len(args) != 2:
                return self._arity_error(command)
            return "(integer) {}".format(self.store.ttl(args[1]))
        return "(error) ERR unknown command '{}'".format(args[0])
