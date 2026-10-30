"""Print and validate a deterministic demo: python -m examples.demo.

Every response comes from the real command processor. The TTL section uses
an injected clock, so the example needs no waiting and has repeatable output.
"""

from mini_redis.commands import CommandProcessor
from mini_redis.store import MiniRedis


class DemoClock:
    """A controllable monotonic clock expressed in seconds."""

    def __init__(self):
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: int) -> None:
        self.now += seconds


def command(processor: CommandProcessor, text: str, expected: str) -> None:
    """Print an actual response and fail immediately if behavior differs."""
    response = processor.execute(text)
    print("mini-redis> " + text)
    print(response)
    if response != expected:
        raise AssertionError(
            "Unexpected response for {!r}: expected {!r}, got {!r}".format(
                text, expected, response
            )
        )


def main() -> None:
    """Demonstrate memory limits, GET recency updates, and exact TTL expiry."""
    print("# 1. LRU eviction: 30-byte memory limit")
    lru = CommandProcessor()
    command(lru, "CONFIG SET maxmemory 30", "OK")
    command(lru, 'SET user:1 "Alice"', "OK")
    command(lru, 'SET user:2 "Bob"', "OK")
    command(lru, 'SET user:3 "Charlie"', "OK")
    command(lru, "GET user:1", "(nil)")
    command(
        lru,
        "INFO memory",
        "used_memory:22\nmaxmemory:30\nevicted_keys:1",
    )
    print("# GET refreshes user:2; user:3 becomes the next eviction victim.")
    command(lru, "GET user:2", '"Bob"')
    command(lru, 'SET user:4 "Dave"', "OK")
    command(lru, "GET user:3", "(nil)")
    command(
        lru,
        "INFO memory",
        "used_memory:19\nmaxmemory:30\nevicted_keys:2",
    )

    print("\n# 2. TTL expiry: injected clock starts at 100.0 seconds")
    clock = DemoClock()
    ttl = CommandProcessor(store=MiniRedis(clock=clock))
    command(ttl, "SET session token", "OK")
    command(ttl, "EXPIRE session 3", "(integer) 1")
    command(ttl, "TTL session", "(integer) 3")
    clock.advance(3)
    print("# Advance injected clock by 3 seconds; no real waiting.")
    command(ttl, "GET session", "(nil)")
    command(ttl, "TTL session", "(integer) -2")
    command(ttl, "DBSIZE", "(integer) 0")
    command(
        ttl,
        "INFO memory",
        "used_memory:0\nmaxmemory:0\nevicted_keys:0",
    )


if __name__ == "__main__":
    main()
