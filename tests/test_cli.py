"""End-to-end subprocess tests of the actual command-line entry points."""

import io
from pathlib import Path
import subprocess
import sys
import unittest

from mini_redis.cli import run_repl


PROJECT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, script, entry=None):
        args = [sys.executable, "-X", "utf8"]
        args.extend(entry if entry is not None else ["-m", "mini_redis"])
        result = subprocess.run(
            args,
            input=script,
            text=True,
            encoding="utf-8",
            capture_output=True,
            cwd=str(PROJECT),
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_module_entrypoint_accepts_piped_commands_and_eof(self):
        output = self.run_cli('SET user:1 "Alice Smith"\nGET user:1\nDBSIZE\n')
        self.assertEqual(output.splitlines(), ["OK", '"Alice Smith"', "(integer) 1"])

    def test_exit_and_quit_stop_processing(self):
        for command in ("exit", "quit", "EXIT", "QuIt"):
            with self.subTest(command=command):
                output = self.run_cli("SET a x\n" + command + "\nGET a\n")
                self.assertEqual(output.splitlines(), ["OK"])

    def test_bad_command_does_not_abort_the_program(self):
        output = self.run_cli("HELLO\nSET a x\nGET a\nquit\n")
        self.assertEqual(
            output.splitlines(),
            ["(error) ERR unknown command 'HELLO'", "OK", '"x"'],
        )

    def test_main_script_entrypoint(self):
        self.assertEqual(self.run_cli("DBSIZE\n", ["main.py"]).strip(), "(integer) 0")

    def test_unicode_input_and_output(self):
        output = self.run_cli('SET 이름 "홍길동 😀"\nGET 이름\n')
        self.assertEqual(output.splitlines(), ["OK", '"홍길동 😀"'])

    def test_empty_input_and_blank_lines(self):
        self.assertEqual(self.run_cli(""), "")
        self.assertEqual(self.run_cli("\n \n\t\n"), "")


class InteractiveInput(io.StringIO):
    """In-memory input that behaves like an interactive terminal."""

    def isatty(self):
        return True


class InterruptedInput(InteractiveInput):
    def readline(self, *args):
        raise KeyboardInterrupt


class ReplTests(unittest.TestCase):
    def test_interactive_prompt_is_printed_before_each_command(self):
        source = InteractiveInput("SET a x\nGET a\nquit\n")
        destination = io.StringIO()
        result = run_repl(input_stream=source, output_stream=destination)
        self.assertEqual(result, 0)
        self.assertEqual(destination.getvalue(), 'mini-redis> OK\nmini-redis> "x"\nmini-redis> ')

    def test_interactive_eof_exits_normally(self):
        destination = io.StringIO()
        self.assertEqual(run_repl(input_stream=InteractiveInput(""), output_stream=destination), 0)
        self.assertEqual(destination.getvalue(), "mini-redis> ")

    def test_keyboard_interrupt_exits_without_traceback(self):
        destination = io.StringIO()
        self.assertEqual(run_repl(input_stream=InterruptedInput(), output_stream=destination), 0)
        self.assertEqual(destination.getvalue(), "mini-redis> \n")

    def test_noninteractive_stream_has_no_prompts(self):
        destination = io.StringIO()
        self.assertEqual(run_repl(input_stream=io.StringIO("DBSIZE\n"), output_stream=destination), 0)
        self.assertEqual(destination.getvalue(), "(integer) 0\n")


if __name__ == "__main__":
    unittest.main()
