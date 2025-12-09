"""
ui/phase_navigator.py - Phase navigation component v1.1
BRAVO OWNS THIS FILE.

Section 54: UI Components
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from enum import Enum

from .utils import get_state_value, get_phase_status

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager


class PhaseStatus(Enum):
    """Phase completion status - UI-friendly values."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    APPROVED = "approved"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class PhaseInfo:
    phase_id: str = ""
    name: str = ""
    description: str = ""
    status: PhaseStatus = PhaseStatus.PENDING
    progress_percent: float = 0
    primary_agent: str = ""
    validation_passed: bool = True
    error_count: int = 0
    warning_count: int = 0
    depends_on: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "primary_agent": self.primary_agent,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "depends_on": self.depends_on,
        }


# Phase definitions with metadata
PHASE_DEFINITIONS = {
    "mission": PhaseInfo(
        phase_id="mission",
        name="Mission Definition",
        description="Define vessel type, speed, range, and operational requirements",
        primary_agent="user",
        depends_on=[],
    ),
    "hull_form": PhaseInfo(
        phase_id="hull_form",
        name="Hull Form",
        description="Design hull geometry, principal dimensions, and coefficients",
        primary_agent="naval_architect",
        depends_on=["mission"],
    ),
    "structure": PhaseInfo(
        phase_id="structure",
        name="Structural Design",
        description="Design scantlings, framing, and structural arrangements",
        primary_agent="structural_engineer",
        depends_on=["hull_form"],
    ),
    "propulsion": PhaseInfo(
        phase_id="propulsion",
        name="Propulsion",
        description="Select and size propulsion system",
        primary_agent="systems_engineer",
        depends_on=["hull_form"],
    ),
    "systems": PhaseInfo(
        phase_id="systems",
        name="Ship Systems",
        description="Design electrical, HVAC, fuel, and auxiliary systems",
        primary_agent="systems_engineer",
        depends_on=["propulsion"],
    ),
    "weight_stability": PhaseInfo(
        phase_id="weight_stability",
        name="Weight & Stability",
        description="Calculate weight distribution and stability characteristics",
        primary_agent="naval_architect",
        depends_on=["structure", "systems"],
    ),
    "compliance": PhaseInfo(
        phase_id="compliance",
        name="Compliance",
        description="Verify regulatory compliance and classification requirements",
        primary_agent="compliance_officer",
        depends_on=["weight_stability"],
    ),
    "production": PhaseInfo(
        phase_id="production",
        name="Production",
        description="Generate production plans and cost estimates",
        primary_agent="production_engineer",
        depends_on=["compliance"],
    ),
}


class PhaseNavigator:
    """
    Manages phase navigation.

    v1.1: Uses get_phase_status with translation.
    """

    def __init__(self, state: "StateManager"):
        self.state = state
        self._phases = list(PHASE_DEFINITIONS.keys())

    def get_phase_info(self, phase_id: str) -> PhaseInfo:
        """Get information about a phase."""
        base = PHASE_DEFINITIONS.get(phase_id)
        if not base:
            return PhaseInfo(phase_id=phase_id, name=phase_id)

        info = PhaseInfo(
            phase_id=base.phase_id,
            name=base.name,
            description=base.description,
            primary_agent=base.primary_agent,
            depends_on=list(base.depends_on),
        )

        # v1.1: Use get_phase_status with translation
        status_str = get_phase_status(self.state, phase_id, "pending")

        try:
            info.status = PhaseStatus(status_str)
        except ValueError:
            info.status = PhaseStatus.PENDING

        # Get phase state details
        phase_state = get_state_value(self.state, f"phase_states.{phase_id}", {})
        if isinstance(phase_state, dict):
            info.error_count = phase_state.get("error_count", 0)
            info.warning_count = phase_state.get("warning_count", 0)
            info.validation_passed = phase_state.get("validation_passed", True)

        # Calculate progress
        if info.status in [PhaseStatus.COMPLETED, PhaseStatus.APPROVED]:
            info.progress_percent = 100
        elif info.status == PhaseStatus.ACTIVE:
            info.progress_percent = 50
        elif info.status == PhaseStatus.ERROR:
            info.progress_percent = 50

        return info

    def get_all_phases(self) -> List[PhaseInfo]:
        """Get information about all phases."""
        return [self.get_phase_info(p) for p in self._phases]

    def get_current_phase(self) -> Optional[PhaseInfo]:
        """Get the currently active phase."""
        for phase_id in self._phases:
            info = self.get_phase_info(phase_id)
            if info.status == PhaseStatus.ACTIVE:
                return info
        return None

    def get_next_phase(self) -> Optional[PhaseInfo]:
        """Get the next phase that can be started."""
        for phase_id in self._phases:
            info = self.get_phase_info(phase_id)
            if info.status == PhaseStatus.PENDING:
                # Check if all dependencies are met
                deps_met = all(
                    self.get_phase_info(dep).status in [PhaseStatus.COMPLETED, PhaseStatus.APPROVED]
                    for dep in info.depends_on
                )
                if deps_met:
                    return info
        return None

    def get_completed_phases(self) -> List[PhaseInfo]:
        """Get all completed phases."""
        return [
            p for p in self.get_all_phases()
            if p.status in [PhaseStatus.COMPLETED, PhaseStatus.APPROVED]
        ]

    def get_phase_tree(self) -> Dict[str, Any]:
        """Get full phase tree structure."""
        phases = self.get_all_phases()
        current = self.get_current_phase()
        next_phase = self.get_next_phase()

        return {
            "phases": [p.to_dict() for p in phases],
            "current": current.phase_id if current else None,
            "next": next_phase.phase_id if next_phase else None,
            "completed_count": sum(
                1 for p in phases
                if p.status in [PhaseStatus.COMPLETED, PhaseStatus.APPROVED]
            ),
            "total_count": len(phases),
        }

    def can_start_phase(self, phase_id: str) -> bool:
        """Check if a phase can be started."""
        info = self.get_phase_info(phase_id)

        if info.status != PhaseStatus.PENDING:
            return False

        # Check dependencies
        for dep_id in info.depends_on:
            dep_info = self.get_phase_info(dep_id)
            if dep_info.status not in [PhaseStatus.COMPLETED, PhaseStatus.APPROVED]:
                return False

        return True

    def render_ascii(self) -> str:
        """Render phase tree as ASCII art."""
        phases = self.get_all_phases()
        icons = {
            PhaseStatus.PENDING: "\u25cb",    # ○
            PhaseStatus.ACTIVE: "\u25c9",     # ◉
            PhaseStatus.COMPLETED: "\u25cf",  # ●
            PhaseStatus.APPROVED: "\u2713",   # ✓
            PhaseStatus.ERROR: "\u2717",      # ✗
            PhaseStatus.SKIPPED: "\u2212",    # −
        }

        lines = ["Design Phases", "=" * 50]

        for i, phase in enumerate(phases):
            icon = icons.get(phase.status, "?")
            connector = "\u2514\u2500\u2500" if i == len(phases) - 1 else "\u251c\u2500\u2500"
            line = f"  {connector} {icon} {phase.name}"

            if phase.status == PhaseStatus.ACTIVE:
                line += " \u2190 current"
            elif phase.error_count > 0:
                line += f" ({phase.error_count} errors)"
            elif phase.status == PhaseStatus.APPROVED:
                line += " [approved]"

            lines.append(line)

        # Summary
        completed = sum(1 for p in phases if p.status in [PhaseStatus.COMPLETED, PhaseStatus.APPROVED])
        lines.append("")
        lines.append(f"Progress: {completed}/{len(phases)} phases complete")

        return "\n".join(lines)

    def render_html(self) -> str:
        """Render phase tree as HTML."""
        phases = self.get_all_phases()

        status_colors = {
            PhaseStatus.PENDING: "#ccc",
            PhaseStatus.ACTIVE: "#ff9900",
            PhaseStatus.COMPLETED: "#00aa00",
            PhaseStatus.APPROVED: "#0066cc",
            PhaseStatus.ERROR: "#cc0000",
            PhaseStatus.SKIPPED: "#999",
        }

        html = ['<div class="phase-navigator">']
        html.append('<ul class="phase-list">')

        for phase in phases:
            color = status_colors.get(phase.status, "#ccc")
            html.append(f'<li class="phase-item phase-{phase.status.value}">')
            html.append(f'  <span class="phase-dot" style="background: {color}"></span>')
            html.append(f'  <span class="phase-name">{phase.name}</span>')
            html.append(f'  <span class="phase-status">{phase.status.value}</span>')
            html.append('</li>')

        html.append('</ul>')
        html.append('</div>')

        return "\n".join(html)
