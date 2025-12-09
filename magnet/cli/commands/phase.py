"""
cli/commands/phase.py - Phase execution commands v1.1
BRAVO OWNS THIS FILE.

Section 51: CLI Interface
"""

from __future__ import annotations
import argparse
from typing import List, TYPE_CHECKING

from ..core import CLICommand, CommandResult, CLIContext

from magnet.ui.utils import (
    get_state_value,
    get_phase_status,
    set_phase_status,
    phase_hooks,
)


class PhaseCommand(CLICommand):
    """Run design phases."""

    name = "phase"
    description = "Run one or more design phases"
    aliases = ["run", "execute"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "phases",
            nargs="*",
            help="Phases to run (default: all remaining)",
        )
        parser.add_argument(
            "--from", "-f",
            dest="start_from",
            help="Start from this phase",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done",
        )
        parser.add_argument(
            "--max-iterations",
            type=int,
            default=5,
            help="Maximum iterations per phase",
        )

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if not ctx.conductor:
            return CommandResult(
                success=False,
                error="Conductor not initialized. Use 'new' or 'load' first.",
            )

        phases = args.phases if args.phases else None

        if args.dry_run:
            return self._dry_run(phases, args.start_from, ctx)

        try:
            run = ctx.conductor.run_full_design(
                phases=phases,
                start_from=args.start_from,
                max_iterations=args.max_iterations,
            )

            # Trigger phase completion hooks for snapshots
            for phase_result in getattr(run, 'phase_results', []):
                if getattr(phase_result, 'status', '') == "completed":
                    phase_hooks.trigger(phase_result.phase, ctx.state)

            phases_completed = getattr(run, 'phases_completed', [])
            final_status = getattr(run, 'final_status', 'unknown')

            return CommandResult(
                success=final_status == "completed",
                message=f"Run completed: {final_status}",
                data={
                    "status": final_status,
                    "phases_completed": phases_completed,
                },
            )

        except Exception as e:
            return CommandResult(
                success=False,
                error=str(e),
            )

    def _dry_run(
        self,
        phases: List[str],
        start_from: str,
        ctx: CLIContext,
    ) -> CommandResult:
        """Show what would be executed."""
        all_phases = [
            "mission", "hull_form", "structure", "propulsion",
            "systems", "weight_stability", "compliance", "production"
        ]

        if phases:
            to_run = phases
        elif start_from:
            idx = all_phases.index(start_from) if start_from in all_phases else 0
            to_run = all_phases[idx:]
        else:
            to_run = all_phases

        phase_info = []
        for phase in to_run:
            status = get_phase_status(ctx.state, phase, "pending") if ctx.state else "pending"
            phase_info.append({"phase": phase, "current_status": status})

        return CommandResult(
            success=True,
            message="Dry run - would execute phases:",
            data={"phases": phase_info},
        )


class ValidateCommand(CLICommand):
    """Run validation on current state."""

    name = "validate"
    description = "Run validators on current design"
    aliases = ["check", "verify"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--phase", "-p", help="Validate specific phase")
        parser.add_argument("--verbose", "-v", action="store_true", help="Show details")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded")

        # Use aliased paths for compliance data
        overall_passed = get_state_value(ctx.state, "compliance.overall_passed", True)
        errors = get_state_value(ctx.state, "compliance.errors", [])
        warnings = get_state_value(ctx.state, "compliance.warnings", [])

        error_count = len(errors) if isinstance(errors, list) else 0
        warning_count = len(warnings) if isinstance(warnings, list) else 0

        result_data = {
            "passed": overall_passed,
            "errors": error_count,
            "warnings": warning_count,
        }

        if args.phase:
            phase_status = get_phase_status(ctx.state, args.phase, "pending")
            result_data["phase"] = args.phase
            result_data["phase_status"] = phase_status

        if args.verbose:
            result_data["error_details"] = errors[:10] if isinstance(errors, list) else []
            result_data["warning_details"] = warnings[:10] if isinstance(warnings, list) else []

        return CommandResult(
            success=overall_passed,
            message="Validation complete" if overall_passed else "Validation failed",
            data=result_data,
        )


class ApproveCommand(CLICommand):
    """Approve current phase."""

    name = "approve"
    description = "Approve current phase and proceed"
    aliases = ["accept", "ok"]

    def configure_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("phase", nargs="?", help="Phase to approve (default: current)")

    def execute(self, ctx: CLIContext, args: argparse.Namespace) -> CommandResult:
        if ctx.state is None:
            return CommandResult(success=False, error="No design loaded")

        if args.phase:
            target_phase = args.phase
        elif ctx.conductor:
            target_phase = getattr(ctx.conductor, 'current_phase', None)
        else:
            target_phase = None

        if not target_phase:
            return CommandResult(
                success=False,
                error="No phase specified and no phase currently active",
            )

        current_status = get_phase_status(ctx.state, target_phase, "pending")

        if current_status not in ["completed", "active"]:
            return CommandResult(
                success=False,
                error=f"Phase '{target_phase}' is {current_status}, cannot approve",
            )

        # Use set_phase_status for proper format
        set_phase_status(ctx.state, target_phase, "approved", "cli")

        # Trigger phase hooks for snapshots
        phase_hooks.trigger(target_phase, ctx.state)

        return CommandResult(
            success=True,
            message=f"Approved phase: {target_phase}",
            data={"phase": target_phase, "status": "approved"},
        )
