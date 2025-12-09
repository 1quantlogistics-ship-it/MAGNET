"""
cli/commands/query.py - Query and inspection commands v1.1
BRAVO OWNS THIS FILE.

Section 51: CLI Interface
"""

from __future__ import annotations
import argparse
import json
from typing import Any, TYPE_CHECKING

from ..core import CLICommand, CommandResult, CLIContext

from magnet.ui.utils import (
    get_state_value,
    set_state_value,
    serialize_state,
    get_phase_status,
    snapshot_registry,
)


class GetCommand(CLICommand):
    """Get a value from state."""

    name = "get"
    description = "Get value at state path"
    aliases = ["show", "read"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="State path (e.g., hull.loa)")
        parser.add_argument("--no-alias", action="store_true",
                          help="Don't use alias fallback")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded")

        value = get_state_value(
            ctx.state,
            args.path,
            default=None,
            use_aliases=not args.no_alias,
        )

        if value is None:
            return CommandResult(
                success=False,
                error=f"Path not found: {args.path}",
            )

        return CommandResult(
            success=True,
            message=f"{args.path} = {value}",
            data={"path": args.path, "value": value},
        )


class SetCommand(CLICommand):
    """Set a value in state."""

    name = "set"
    description = "Set value at state path"
    aliases = ["write", "update"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="State path")
        parser.add_argument("value", help="Value to set")
        parser.add_argument("--type", "-t",
                          choices=["str", "int", "float", "bool", "json"],
                          default="auto")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded")

        value = self._parse_value(args.value, args.type)
        old_value = get_state_value(ctx.state, args.path)

        success = set_state_value(ctx.state, args.path, value, "cli")

        if not success:
            return CommandResult(success=False, error=f"Failed to set {args.path}")

        return CommandResult(
            success=True,
            message=f"{args.path}: {old_value} -> {value}",
            data={"path": args.path, "old": old_value, "new": value},
        )

    def _parse_value(self, value: str, type_hint: str) -> Any:
        """Parse value to appropriate type."""
        if type_hint == "int":
            return int(value)
        elif type_hint == "float":
            return float(value)
        elif type_hint == "bool":
            return value.lower() in ("true", "1", "yes")
        elif type_hint == "json":
            return json.loads(value)
        elif type_hint == "auto":
            try:
                return int(value)
            except ValueError:
                pass
            try:
                return float(value)
            except ValueError:
                pass
            if value.lower() in ("true", "false"):
                return value.lower() == "true"
            return value
        return value


class ListCommand(CLICommand):
    """List state contents."""

    name = "list"
    description = "List contents of state section"
    aliases = ["ls", "dir"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", default="", help="Section path")
        parser.add_argument("--depth", "-d", type=int, default=1, help="Depth to show")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded")

        if args.path:
            data = get_state_value(ctx.state, args.path, {})
        else:
            data = serialize_state(ctx.state)

        if not isinstance(data, dict):
            return CommandResult(
                success=True,
                message=f"{args.path} = {data}",
                data={"path": args.path, "value": data},
            )

        # Flatten to specified depth
        items = self._list_items(data, args.depth)

        return CommandResult(
            success=True,
            message=f"Contents of {args.path or 'root'}:",
            data={"items": items},
        )

    def _list_items(self, data: dict, depth: int, prefix: str = "") -> list:
        """List items up to specified depth."""
        items = []
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and depth > 0:
                items.append({"path": path, "type": "dict", "count": len(value)})
                items.extend(self._list_items(value, depth - 1, path))
            elif isinstance(value, list):
                items.append({"path": path, "type": "list", "count": len(value)})
            else:
                items.append({"path": path, "value": value})
        return items


class StatusCommand(CLICommand):
    """Show design status."""

    name = "status"
    description = "Show current design status"
    aliases = ["info", "st"]

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(
                success=False,
                error="No design loaded",
            )

        metadata = get_state_value(ctx.state, "metadata", {})
        displacement = get_state_value(ctx.state, "hull.displacement_mt", "N/A")

        # Phase status using translation layer
        phases = {}
        for phase in ["mission", "hull_form", "structure", "propulsion",
                     "systems", "weight_stability", "compliance"]:
            phases[phase] = get_phase_status(ctx.state, phase, "pending")

        return CommandResult(
            success=True,
            message=f"Design: {metadata.get('name', 'Untitled')}",
            data={
                "design_id": metadata.get("design_id", "N/A"),
                "name": metadata.get("name", "Untitled"),
                "version": metadata.get("version", "0.0.0"),
                "displacement_mt": displacement,
                "phases": phases,
            },
        )


class HistoryCommand(CLICommand):
    """Show command history."""

    name = "history"
    description = "Show command history"
    aliases = ["hist"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("-n", type=int, default=20, help="Number of entries")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        history = ctx.history[-args.n:]

        return CommandResult(
            success=True,
            message=f"Last {len(history)} commands",
            data={"history": history},
        )


class SnapshotCommand(CLICommand):
    """Take a vision snapshot."""

    name = "snapshot"
    description = "Take a visual snapshot of current design"
    aliases = ["snap", "render"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--view", "-v", default="perspective",
                          choices=["perspective", "top", "side", "front", "bow", "stern"])
        parser.add_argument("--output", "-o", help="Output path")
        parser.add_argument("--section-id", "-s", default="cli_snapshot",
                          help="Section ID for registry")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded")

        try:
            from magnet.vision.router import VisionRouter, VisionRequest

            router = VisionRouter(ctx.state)

            request = VisionRequest(
                request_id="cli_snapshot",
                operation="render",
                parameters={
                    "views": [args.view],
                    "output_dir": args.output or "/tmp/magnet_render",
                    "section_id": args.section_id,
                },
            )

            response = router.process_request(request)

            if response.success and response.snapshots:
                snapshot = response.snapshots[0]

                # Register in snapshot registry
                if snapshot.image_path:
                    snapshot_registry.register(args.section_id, snapshot.image_path)

                return CommandResult(
                    success=True,
                    message=f"Snapshot saved to {snapshot.image_path}",
                    data={"path": snapshot.image_path, "section_id": args.section_id},
                )
            else:
                return CommandResult(
                    success=False,
                    error=response.error or "Snapshot failed",
                )

        except ImportError:
            return CommandResult(success=False, error="Vision module not available")
        except Exception as e:
            return CommandResult(success=False, error=str(e))
