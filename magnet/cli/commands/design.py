"""
cli/commands/design.py - Design management commands v1.1
BRAVO OWNS THIS FILE.

Section 51: CLI Interface
"""

from __future__ import annotations
import argparse
from pathlib import Path
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from ..core import CLICommand, CommandResult, CLIContext

from magnet.ui.utils import (
    get_state_value,
    set_state_value,
    serialize_state,
    load_state_from_dict,
)


class NewCommand(CLICommand):
    """Create a new design."""

    name = "new"
    description = "Create a new design project"
    aliases = ["create", "init"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("name", nargs="?", default="Untitled Design",
                          help="Design name")
        parser.add_argument("--template", "-t", help="Template to use")
        parser.add_argument("--output", "-o", help="Output directory")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        design_id = f"MAGNET-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

        if ctx.state:
            set_state_value(ctx.state, "metadata.design_id", design_id, "cli")
            set_state_value(ctx.state, "metadata.name", args.name, "cli")
            set_state_value(ctx.state, "metadata.created_at", datetime.utcnow().isoformat(), "cli")
            set_state_value(ctx.state, "metadata.version", "0.1.0", "cli")

            # Initialize required namespaces
            set_state_value(ctx.state, "phase_states", {}, "cli")
            set_state_value(ctx.state, "hull", {}, "cli")
            set_state_value(ctx.state, "mission", {}, "cli")

            ctx.design_id = design_id

        if args.template:
            self._apply_template(args.template, ctx)

        return CommandResult(
            success=True,
            message=f"Created design: {args.name}",
            data={"design_id": design_id, "name": args.name},
        )

    def _apply_template(self, template_name: str, ctx: CLIContext) -> None:
        """Apply a design template."""
        templates = {
            "patrol": {
                "mission.vessel_type": "patrol",
                "mission.max_speed_kts": 35,
                "mission.cruise_speed_kts": 25,
                "mission.range_nm": 300,
                "mission.crew_berthed": 6,
            },
            "ferry": {
                "mission.vessel_type": "ferry",
                "mission.max_speed_kts": 28,
                "mission.cruise_speed_kts": 22,
                "mission.range_nm": 150,
                "mission.crew_berthed": 4,
                "mission.passengers": 50,
            },
            "workboat": {
                "mission.vessel_type": "workboat",
                "mission.max_speed_kts": 20,
                "mission.cruise_speed_kts": 12,
                "mission.range_nm": 200,
                "mission.crew_berthed": 4,
            },
        }

        if template_name in templates and ctx.state:
            for path, value in templates[template_name].items():
                set_state_value(ctx.state, path, value, "template")


class LoadCommand(CLICommand):
    """Load an existing design."""

    name = "load"
    description = "Load a design from file"
    aliases = ["open"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", help="Path to design file")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        path = Path(args.path)

        if not path.exists():
            return CommandResult(
                success=False,
                error=f"File not found: {path}",
                exit_code=1,
            )

        try:
            data = json.loads(path.read_text())

            if ctx.state:
                load_state_from_dict(ctx.state, data)

            design_id = data.get("metadata", {}).get("design_id", "UNKNOWN")
            ctx.design_id = design_id
            ctx.design_path = str(path)

            return CommandResult(
                success=True,
                message=f"Loaded design from {path}",
                data={"design_id": design_id, "path": str(path)},
            )

        except json.JSONDecodeError as e:
            return CommandResult(
                success=False,
                error=f"Invalid JSON: {e}",
                exit_code=2,
            )


class SaveCommand(CLICommand):
    """Save current design."""

    name = "save"
    description = "Save current design to file"
    aliases = []

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("path", nargs="?", help="Output path (optional)")
        parser.add_argument("--format", "-f", choices=["json", "yaml"], default="json")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(
                success=False,
                error="No design loaded",
                exit_code=1,
            )

        if args.path:
            path = Path(args.path)
        elif ctx.design_path:
            path = Path(ctx.design_path)
        else:
            design_id = ctx.design_id or "untitled"
            path = Path(f"{design_id}.json")

        # Use unified serializer
        data = serialize_state(ctx.state)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str))

        ctx.design_path = str(path)

        return CommandResult(
            success=True,
            message=f"Saved to {path}",
            data={"path": str(path)},
        )


class ExportCommand(CLICommand):
    """Export design to various formats."""

    name = "export"
    description = "Export design to PDF, DOCX, or other formats"
    aliases = []

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("format", choices=["pdf", "docx", "json", "html"],
                          help="Export format")
        parser.add_argument("--output", "-o", help="Output path")
        parser.add_argument("--template", "-t", help="Report template")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(
                success=False,
                error="No design loaded",
                exit_code=1,
            )

        output_path = args.output or f"design_export.{args.format}"

        try:
            if args.format == "json":
                data = serialize_state(ctx.state)
                Path(output_path).write_text(json.dumps(data, indent=2, default=str))
            else:
                # Try to use reporting module
                try:
                    from magnet.reporting import ReportGenerator
                    generator = ReportGenerator()
                    generator.generate(
                        state=ctx.state,
                        output_path=output_path,
                        format=args.format,
                        template=args.template,
                    )
                except ImportError:
                    return CommandResult(
                        success=False,
                        error=f"Reporting module not available for {args.format}",
                    )

            return CommandResult(
                success=True,
                message=f"Exported to {output_path}",
                data={"path": output_path, "format": args.format},
            )

        except Exception as e:
            return CommandResult(
                success=False,
                error=str(e),
            )
