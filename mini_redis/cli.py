"""Interactive prompt and pipe-friendly command processing."""

import sys
from typing import Optional, TextIO

from .commands import CommandProcessor


def run_repl(
    input_stream: Optional[TextIO] = None,
    output_stream: Optional[TextIO] = None,
    processor: Optional[CommandProcessor] = None,
) -> int:
    """Read commands until EOF, Ctrl+C, exit or quit; return a process exit code."""
    source = input_stream if input_stream is not None else sys.stdin
    destination = output_stream if output_stream is not None else sys.stdout
    commands = processor if processor is not None else CommandProcessor()
    interactive = source.isatty()
    while True:
        try:
            if interactive:
                destination.write("mini-redis> ")
                destination.flush()
            line = source.readline()
            if not line:
                break
            if line.strip().lower() in ("exit", "quit"):
                break
            response = commands.execute(line)
            if response:
                destination.write(response + "\n")
                destination.flush()
        except KeyboardInterrupt:
            if interactive:
                destination.write("\n")
            break
    return 0


def main() -> int:
    """Entry point shared by python -m mini_redis and main.py."""
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    return run_repl()
