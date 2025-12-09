"""
cli/repl.py - Read-Eval-Print Loop v1.1

Module 51: CLI Interface
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import argparse
import shlex
import sys
import logging

from .core import (
    CLIContext,
    CLICommand,
    CommandResult,
    CommandRegistry,
    OutputFormat,
    format_output,
    command_registry,
)
from .commands import (
    NewCommand,
    LoadCommand,
    SaveCommand,
    ExportCommand,
    GetCommand,
    SetCommand,
    ListCommand,
    StatusCommand,
    HistoryCommand,
    SnapshotCommand,
    PhaseCommand,
    ValidateCommand,
    ApproveCommand,
)

logger = logging.getLogger("cli.repl")


class REPL:
    """
    Interactive Read-Eval-Print Loop for MAGNET CLI.
    """

    def __init__(
        self,
        ctx: Optional[CLIContext] = None,
        registry: Optional[CommandRegistry] = None,
    ):
        """
        Initialize REPL.

        Args:
            ctx: CLI context (created if not provided)
            registry: Command registry (uses global if not provided)
        """
        self.ctx = ctx or CLIContext()
        self.registry = registry or command_registry
        self._running = False
        self._parsers: Dict[str, argparse.ArgumentParser] = {}

        # Register default commands
        self._register_default_commands()

    def _register_default_commands(self) -> None:
        """Register default commands."""
        commands = [
            NewCommand(),
            LoadCommand(),
            SaveCommand(),
            ExportCommand(),
            GetCommand(),
            SetCommand(),
            ListCommand(),
            StatusCommand(),
            HistoryCommand(),
            SnapshotCommand(),
            PhaseCommand(),
            ValidateCommand(),
            ApproveCommand(),
        ]

        for cmd in commands:
            self.registry.register(cmd)
            parser = argparse.ArgumentParser(prog=cmd.name, description=cmd.description)
            cmd.configure_parser(parser)
            self._parsers[cmd.name] = parser

    def run(self, prompt: str = "magnet> ") -> None:
        """
        Start interactive REPL loop.

        Args:
            prompt: Prompt string to display
        """
        self._running = True
        print("MAGNET Design System CLI v1.1")
        print("Type 'help' for available commands, 'quit' to exit\n")

        while self._running:
            try:
                line = input(prompt).strip()

                if not line:
                    continue

                if line.lower() in ("quit", "exit", "q"):
                    self._running = False
                    print("Goodbye!")
                    break

                if line.lower() == "help":
                    self._show_help()
                    continue

                result = self.execute_line(line)
                output = format_output(result, self.ctx.output_format)
                print(output)

            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                self._running = False
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

    def execute_line(self, line: str) -> CommandResult:
        """
        Execute a single command line.

        Args:
            line: Command line to execute

        Returns:
            CommandResult
        """
        try:
            parts = shlex.split(line)
        except ValueError as e:
            return CommandResult(success=False, error=f"Parse error: {e}", exit_code=1)

        if not parts:
            return CommandResult(success=True)

        cmd_name = parts[0]
        cmd_args = parts[1:]

        # Add to history
        self.ctx.history.append(line)

        # Find command
        cmd = self.registry.get(cmd_name)
        if cmd is None:
            return CommandResult(
                success=False,
                error=f"Unknown command: {cmd_name}. Type 'help' for available commands.",
                exit_code=1,
            )

        # Parse arguments
        parser = self._parsers.get(cmd.name)
        if parser is None:
            parser = argparse.ArgumentParser(prog=cmd.name)
            cmd.configure_parser(parser)
            self._parsers[cmd.name] = parser

        try:
            args = parser.parse_args(cmd_args)
        except SystemExit:
            # argparse calls sys.exit on error
            return CommandResult(
                success=False,
                error=f"Invalid arguments for {cmd_name}",
                exit_code=1,
            )

        # Execute command
        return cmd.execute(self.ctx, args)

    def execute_batch(self, commands: List[str]) -> List[CommandResult]:
        """
        Execute a batch of commands.

        Args:
            commands: List of command lines

        Returns:
            List of CommandResults
        """
        results = []
        for line in commands:
            line = line.strip()
            if line and not line.startswith("#"):
                result = self.execute_line(line)
                results.append(result)
                if not result.success:
                    break  # Stop on error
        return results

    def execute_file(self, filepath: str) -> List[CommandResult]:
        """
        Execute commands from a file.

        Args:
            filepath: Path to script file

        Returns:
            List of CommandResults
        """
        with open(filepath, 'r') as f:
            commands = f.readlines()
        return self.execute_batch(commands)

    def _show_help(self) -> None:
        """Display help information."""
        print("\nAvailable Commands:")
        print("-" * 40)

        for name, cmd in sorted(self.registry.get_all().items()):
            aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
            print(f"  {name:15}{aliases}")
            print(f"    {cmd.description}")

        print("\nBuilt-in Commands:")
        print("  help          Show this help")
        print("  quit/exit     Exit the REPL")
        print()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="MAGNET Design System CLI")
    parser.add_argument("--script", "-s", help="Execute script file")
    parser.add_argument("--command", "-c", help="Execute single command")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    ctx = CLIContext(
        output_format=OutputFormat.JSON if args.json else OutputFormat.TEXT,
        verbose=args.verbose,
    )
    repl = REPL(ctx)

    if args.script:
        results = repl.execute_file(args.script)
        exit_code = 0 if all(r.success for r in results) else 1
        sys.exit(exit_code)

    elif args.command:
        result = repl.execute_line(args.command)
        print(format_output(result, ctx.output_format))
        sys.exit(result.exit_code)

    else:
        repl.run()


if __name__ == "__main__":
    main()
