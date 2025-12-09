"""
cli/core.py - Core CLI infrastructure v1.1

Module 51: CLI Interface
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import argparse
import logging

from magnet.ui.utils import (
    get_state_value,
    set_state_value,
    serialize_state,
    load_state_from_dict,
    get_phase_status,
    snapshot_registry,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("cli")


class OutputFormat(Enum):
    """Output format options."""
    TEXT = "text"
    JSON = "json"
    TABLE = "table"
    MINIMAL = "minimal"


@dataclass
class CLIContext:
    """Context for CLI operations."""

    state: Optional["StateManager"] = None
    conductor: Optional[Any] = None

    # Current design
    design_id: str = ""
    design_path: str = ""

    # Output settings
    output_format: OutputFormat = OutputFormat.TEXT
    verbose: bool = False
    color: bool = True

    # Session
    history: List[str] = field(default_factory=list)

    # Snapshot registry reference
    _snapshot_registry: Any = None

    def __post_init__(self):
        self._snapshot_registry = snapshot_registry

    @property
    def snapshots(self):
        """Access to snapshot registry."""
        return self._snapshot_registry

    def get_value(self, path: str, default: Any = None) -> Any:
        """Get value from state using unified accessor."""
        if self.state is None:
            return default
        return get_state_value(self.state, path, default)

    def set_value(self, path: str, value: Any, source: str = "cli") -> bool:
        """Set value in state using unified accessor."""
        if self.state is None:
            return False
        return set_state_value(self.state, path, value, source)

    def get_phase(self, phase: str, default: str = "pending") -> str:
        """Get phase status using unified accessor."""
        if self.state is None:
            return default
        return get_phase_status(self.state, phase, default)


@dataclass
class CommandResult:
    """Result of a CLI command execution."""

    success: bool = True
    message: str = ""
    data: Any = None
    error: Optional[str] = None

    # For display formatting
    format_hint: str = "text"
    exit_code: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }


class CLICommand(ABC):
    """Base class for CLI commands."""

    name: str = "command"
    description: str = "Base command"
    aliases: List[str] = []

    @abstractmethod
    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Execute the command."""
        pass

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        """Configure argument parser for this command."""
        pass


class CommandRegistry:
    """Registry for CLI commands."""

    def __init__(self):
        self._commands: Dict[str, CLICommand] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, command: CLICommand) -> None:
        """Register a command."""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name

    def get(self, name: str) -> Optional[CLICommand]:
        """Get command by name or alias."""
        if name in self._commands:
            return self._commands[name]
        if name in self._aliases:
            return self._commands[self._aliases[name]]
        return None

    def list_commands(self) -> List[str]:
        """List all command names."""
        return list(self._commands.keys())

    def get_all(self) -> Dict[str, CLICommand]:
        """Get all commands."""
        return dict(self._commands)


# Global registry
command_registry = CommandRegistry()


def format_output(result: CommandResult, format: OutputFormat) -> str:
    """Format command result for display."""
    if format == OutputFormat.JSON:
        import json
        return json.dumps(result.to_dict(), indent=2, default=str)

    elif format == OutputFormat.TABLE:
        if isinstance(result.data, list) and result.data:
            lines = []
            if isinstance(result.data[0], dict):
                keys = list(result.data[0].keys())
                lines.append(" | ".join(keys))
                lines.append("-" * (len(keys) * 15))
                for row in result.data:
                    lines.append(" | ".join(str(row.get(k, "")) for k in keys))
            return "\n".join(lines)
        return str(result.data)

    elif format == OutputFormat.MINIMAL:
        if result.success:
            return str(result.data) if result.data else ""
        return result.error or "Error"

    else:  # TEXT
        if result.success:
            output = result.message
            if result.data:
                if isinstance(result.data, dict):
                    for k, v in result.data.items():
                        output += f"\n  {k}: {v}"
                else:
                    output += f"\n{result.data}"
            return output
        return f"Error: {result.error}"
