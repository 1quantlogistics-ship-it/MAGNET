"""
cli/commands.py - CLI command implementations v1.1

Module 51: CLI Interface
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from .core import CLICommand, CLIContext, CommandResult
from magnet.ui.utils import (
    get_state_value,
    set_state_value,
    serialize_state,
    load_state_from_dict,
    get_phase_status,
    set_phase_status,
)


class NewCommand(CLICommand):
    """Create a new design."""

    name = "new"
    description = "Create a new design"
    aliases = ["create"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("name", nargs="?", default="", help="Design name")
        parser.add_argument("--type", "-t", default="hsc", help="Vessel type")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        try:
            from magnet.core.state_manager import StateManager
            from magnet.core.design_state import DesignState

            state = DesignState()
            if args.name:
                state.design_name = args.name

            ctx.state = StateManager(state)
            ctx.design_id = state.design_id

            if args.type:
                set_state_value(ctx.state, "mission.vessel_type", args.type, "cli")

            return CommandResult(
                success=True,
                message=f"Created new design: {args.name or state.design_id}",
                data={"design_id": state.design_id, "name": args.name},
            )
        except Exception as e:
            return CommandResult(success=False, error=str(e), exit_code=1)


class LoadCommand(CLICommand):
    """Load a design from file."""

    name = "load"
    description = "Load a design from file"
    aliases = ["open"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="Path to design file")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        try:
            path = Path(args.path)
            if not path.exists():
                return CommandResult(success=False, error=f"File not found: {path}", exit_code=1)

            with open(path, 'r') as f:
                data = json.load(f)

            from magnet.core.state_manager import StateManager

            if ctx.state is None:
                from magnet.core.design_state import DesignState
                ctx.state = StateManager(DesignState())

            load_state_from_dict(ctx.state, data)
            ctx.design_path = str(path)
            ctx.design_id = data.get("design_id", "")

            return CommandResult(
                success=True,
                message=f"Loaded design from {path}",
                data={"path": str(path), "design_id": ctx.design_id},
            )
        except Exception as e:
            return CommandResult(success=False, error=str(e), exit_code=1)


class SaveCommand(CLICommand):
    """Save design to file."""

    name = "save"
    description = "Save design to file"
    aliases = ["write"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", help="Path to save file")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        try:
            path = args.path or ctx.design_path
            if not path:
                path = f"design_{ctx.design_id}.json"

            data = serialize_state(ctx.state)

            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            ctx.design_path = path

            return CommandResult(
                success=True,
                message=f"Saved design to {path}",
                data={"path": path},
            )
        except Exception as e:
            return CommandResult(success=False, error=str(e), exit_code=1)


class ExportCommand(CLICommand):
    """Export design in various formats."""

    name = "export"
    description = "Export design in various formats"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="Output path")
        parser.add_argument("--format", "-f", choices=["json", "summary", "report"], default="json")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        try:
            from magnet.glue.lifecycle import DesignExporter, ExportFormat, ExportConfig

            format_map = {
                "json": ExportFormat.JSON_PRETTY,
                "summary": ExportFormat.SUMMARY,
                "report": ExportFormat.REPORT,
            }

            exporter = DesignExporter(ctx.state)
            config = ExportConfig(format=format_map.get(args.format, ExportFormat.JSON_PRETTY))

            if exporter.export_to_file(args.path, config):
                return CommandResult(
                    success=True,
                    message=f"Exported to {args.path}",
                    data={"path": args.path, "format": args.format},
                )
            else:
                return CommandResult(success=False, error="Export failed", exit_code=1)

        except Exception as e:
            return CommandResult(success=False, error=str(e), exit_code=1)


class GetCommand(CLICommand):
    """Get a value from state."""

    name = "get"
    description = "Get a value from design state"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="Dot-notation path (e.g., hull.loa)")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        value = get_state_value(ctx.state, args.path)

        if value is None:
            return CommandResult(
                success=True,
                message=f"{args.path}: (not set)",
                data=None,
            )

        return CommandResult(
            success=True,
            message=f"{args.path}: {value}",
            data={args.path: value},
        )


class SetCommand(CLICommand):
    """Set a value in state."""

    name = "set"
    description = "Set a value in design state"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="Dot-notation path (e.g., hull.loa)")
        parser.add_argument("value", help="Value to set")
        parser.add_argument("--type", "-t", choices=["str", "int", "float", "bool"], default="auto")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        # Parse value type
        value = args.value
        if args.type == "int":
            value = int(value)
        elif args.type == "float":
            value = float(value)
        elif args.type == "bool":
            value = value.lower() in ("true", "1", "yes")
        elif args.type == "auto":
            try:
                value = float(value)
                if value.is_integer():
                    value = int(value)
            except ValueError:
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"

        if set_state_value(ctx.state, args.path, value, "cli"):
            return CommandResult(
                success=True,
                message=f"Set {args.path} = {value}",
                data={args.path: value},
            )
        else:
            return CommandResult(success=False, error=f"Failed to set {args.path}", exit_code=1)


class ListCommand(CLICommand):
    """List contents of state section."""

    name = "list"
    description = "List contents of a state section"
    aliases = ["ls"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", default="", help="Section path")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        if args.path:
            value = get_state_value(ctx.state, args.path)
        else:
            value = serialize_state(ctx.state)

        if isinstance(value, dict):
            keys = list(value.keys())
            return CommandResult(
                success=True,
                message=f"Contents of {args.path or 'root'}:",
                data=keys,
            )
        else:
            return CommandResult(
                success=True,
                message=f"{args.path}: {value}",
                data=value,
            )


class StatusCommand(CLICommand):
    """Show design status."""

    name = "status"
    description = "Show design status"
    aliases = ["stat"]

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        design_id = get_state_value(ctx.state, "design_id", "")
        design_name = get_state_value(ctx.state, "design_name", "Unnamed")
        vessel_type = get_state_value(ctx.state, "mission.vessel_type", "")
        loa = get_state_value(ctx.state, "hull.loa", 0)

        status_data = {
            "design_id": design_id,
            "name": design_name,
            "vessel_type": vessel_type,
            "loa": f"{loa:.2f} m" if loa else "Not set",
            "path": ctx.design_path or "(unsaved)",
        }

        return CommandResult(
            success=True,
            message="Design Status",
            data=status_data,
        )


class PhaseCommand(CLICommand):
    """Phase management commands."""

    name = "phase"
    description = "Phase management"

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("action", choices=["status", "start", "complete", "list"])
        parser.add_argument("phase", nargs="?", help="Phase name")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        if args.action == "status":
            if args.phase:
                status = get_phase_status(ctx.state, args.phase)
                return CommandResult(
                    success=True,
                    message=f"Phase {args.phase}: {status}",
                    data={"phase": args.phase, "status": status},
                )
            else:
                return CommandResult(success=False, error="Phase name required", exit_code=1)

        elif args.action == "start":
            if args.phase:
                set_phase_status(ctx.state, args.phase, "active", "cli")
                return CommandResult(
                    success=True,
                    message=f"Started phase: {args.phase}",
                    data={"phase": args.phase, "status": "active"},
                )
            else:
                return CommandResult(success=False, error="Phase name required", exit_code=1)

        elif args.action == "complete":
            if args.phase:
                set_phase_status(ctx.state, args.phase, "completed", "cli")
                return CommandResult(
                    success=True,
                    message=f"Completed phase: {args.phase}",
                    data={"phase": args.phase, "status": "completed"},
                )
            else:
                return CommandResult(success=False, error="Phase name required", exit_code=1)

        elif args.action == "list":
            phases = get_state_value(ctx.state, "phase_states", {})
            return CommandResult(
                success=True,
                message="Phases:",
                data=phases,
            )

        return CommandResult(success=False, error="Unknown action", exit_code=1)


class ValidateCommand(CLICommand):
    """Run validators."""

    name = "validate"
    description = "Run validators on current design"
    aliases = ["val"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--validator", "-v", help="Specific validator to run")
        parser.add_argument("--phase", "-p", help="Phase to validate")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded", exit_code=1)

        # Basic validation using state.validate() if available
        if hasattr(ctx.state, 'validate'):
            try:
                is_valid, errors = ctx.state.validate()
                return CommandResult(
                    success=is_valid,
                    message="Validation passed" if is_valid else "Validation failed",
                    data={"valid": is_valid, "errors": errors},
                    exit_code=0 if is_valid else 1,
                )
            except Exception as e:
                return CommandResult(success=False, error=str(e), exit_code=1)

        return CommandResult(
            success=True,
            message="No validators configured",
            data={"valid": True, "errors": []},
        )
