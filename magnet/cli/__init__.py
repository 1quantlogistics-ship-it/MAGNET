"""
cli/ - Command Line Interface (Module 51)

Provides command-line access to MAGNET functionality including:
- Interactive REPL
- Batch mode execution
- Design commands (new, load, save, export)
- Phase commands (start, status, advance)
- Query commands (get, set, list)
"""

from .core import (
    CLIContext,
    OutputFormat,
    CommandResult,
    CommandRegistry,
    CLICommand,
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

from .repl import REPL


__all__ = [
    # Core
    "CLIContext",
    "OutputFormat",
    "CommandResult",
    "CommandRegistry",
    "CLICommand",
    # Commands
    "NewCommand",
    "LoadCommand",
    "SaveCommand",
    "ExportCommand",
    "GetCommand",
    "SetCommand",
    "ListCommand",
    "StatusCommand",
    "HistoryCommand",
    "SnapshotCommand",
    "PhaseCommand",
    "ValidateCommand",
    "ApproveCommand",
    # REPL
    "REPL",
]
