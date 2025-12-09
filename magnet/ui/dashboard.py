"""
ui/dashboard.py - Dashboard components v1.1
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


class WidgetType(Enum):
    METRIC = "metric"
    PROGRESS = "progress"
    TABLE = "table"
    CHART = "chart"
    STATUS = "status"
    IMAGE = "image"
    VALIDATION = "validation"
    PHASE_NAV = "phase_nav"


@dataclass
class Widget:
    widget_id: str = ""
    widget_type: WidgetType = WidgetType.METRIC
    title: str = ""
    row: int = 0
    col: int = 0
    width: int = 1
    height: int = 1
    data: Any = None
    style: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "type": self.widget_type.value,
            "title": self.title,
            "row": self.row,
            "col": self.col,
            "width": self.width,
            "height": self.height,
            "data": self.data,
        }


@dataclass
class MetricWidget(Widget):
    value: Any = None
    unit: str = ""
    trend: Optional[str] = None
    status: str = "normal"

    def __post_init__(self):
        self.widget_type = WidgetType.METRIC
        self.data = {
            "value": self.value,
            "unit": self.unit,
            "trend": self.trend,
            "status": self.status,
        }


@dataclass
class ProgressWidget(Widget):
    current: float = 0
    total: float = 100
    label: str = ""

    def __post_init__(self):
        self.widget_type = WidgetType.PROGRESS
        self.data = {
            "current": self.current,
            "total": self.total,
            "percent": (self.current / self.total * 100) if self.total else 0,
            "label": self.label,
        }


@dataclass
class ValidationWidget(Widget):
    passed: bool = True
    errors: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)

    def __post_init__(self):
        self.widget_type = WidgetType.VALIDATION
        self.data = {
            "passed": self.passed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors[:5],
            "warnings": self.warnings[:5],
        }


@dataclass
class TableWidget(Widget):
    headers: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)

    def __post_init__(self):
        self.widget_type = WidgetType.TABLE
        self.data = {
            "headers": self.headers,
            "rows": self.rows,
            "row_count": len(self.rows),
        }


class DashboardBuilder:
    """
    Builds dashboard configuration from state.

    v1.1: Uses get_state_value for all access.
    """

    def __init__(self, state: "StateManager"):
        self.state = state

    def build_overview_dashboard(self) -> List[Widget]:
        """Build main overview dashboard."""
        widgets = []

        # Design ID
        widgets.append(MetricWidget(
            widget_id="design_id",
            title="Design",
            value=get_state_value(self.state, "metadata.design_id", "N/A"),
            row=0, col=0, width=2,
        ))

        # Principal dimensions
        widgets.append(MetricWidget(
            widget_id="loa",
            title="LOA",
            value=self._format(get_state_value(self.state, "hull.loa")),
            unit="m",
            row=1, col=0,
        ))

        widgets.append(MetricWidget(
            widget_id="beam",
            title="Beam",
            value=self._format(get_state_value(self.state, "hull.beam")),
            unit="m",
            row=1, col=1,
        ))

        # v1.1: Displacement via alias
        widgets.append(MetricWidget(
            widget_id="displacement",
            title="Displacement",
            value=self._format(get_state_value(self.state, "hull.displacement_mt")),
            unit="t",
            row=1, col=2,
        ))

        # Performance
        widgets.append(MetricWidget(
            widget_id="max_speed",
            title="Max Speed",
            value=self._format(get_state_value(self.state, "mission.max_speed_kts")),
            unit="kts",
            row=2, col=0,
        ))

        widgets.append(MetricWidget(
            widget_id="range",
            title="Range",
            value=self._format(get_state_value(self.state, "mission.range_nm")),
            unit="nm",
            row=2, col=1,
        ))

        # Stability
        gm = get_state_value(self.state, "stability.gm_transverse_m")
        gm_status = "success" if gm and gm > 0.35 else "warning" if gm else "normal"

        widgets.append(MetricWidget(
            widget_id="gm",
            title="GM",
            value=f"{gm:.3f}" if gm else "\u2014",
            unit="m",
            status=gm_status,
            row=2, col=2,
        ))

        # v1.1: Use get_phase_status with translation
        completed = self._count_completed_phases()

        widgets.append(ProgressWidget(
            widget_id="phase_progress",
            title="Design Progress",
            current=completed,
            total=8,
            label=f"{completed}/8 phases",
            row=3, col=0, width=3,
        ))

        # v1.1: Use aliased paths for compliance
        overall_passed = get_state_value(self.state, "compliance.overall_passed", True)
        errors = get_state_value(self.state, "compliance.errors", [])
        warnings = get_state_value(self.state, "compliance.warnings", [])

        widgets.append(ValidationWidget(
            widget_id="validation_status",
            title="Validation Status",
            passed=overall_passed,
            errors=errors if isinstance(errors, list) else [],
            warnings=warnings if isinstance(warnings, list) else [],
            row=4, col=0, width=3,
        ))

        return widgets

    def build_hull_dashboard(self) -> List[Widget]:
        """Build hull parameters dashboard."""
        widgets = []

        widgets.append(MetricWidget(
            widget_id="hull_loa",
            title="Length Overall",
            value=self._format(get_state_value(self.state, "hull.loa")),
            unit="m",
            row=0, col=0,
        ))

        widgets.append(MetricWidget(
            widget_id="hull_lwl",
            title="Waterline Length",
            value=self._format(get_state_value(self.state, "hull.lwl")),
            unit="m",
            row=0, col=1,
        ))

        widgets.append(MetricWidget(
            widget_id="hull_beam",
            title="Beam",
            value=self._format(get_state_value(self.state, "hull.beam")),
            unit="m",
            row=0, col=2,
        ))

        widgets.append(MetricWidget(
            widget_id="hull_draft",
            title="Draft",
            value=self._format(get_state_value(self.state, "hull.draft")),
            unit="m",
            row=1, col=0,
        ))

        widgets.append(MetricWidget(
            widget_id="hull_depth",
            title="Depth",
            value=self._format(get_state_value(self.state, "hull.depth")),
            unit="m",
            row=1, col=1,
        ))

        widgets.append(MetricWidget(
            widget_id="hull_cb",
            title="Block Coefficient",
            value=self._format(get_state_value(self.state, "hull.cb")),
            row=1, col=2,
        ))

        return widgets

    def build_stability_dashboard(self) -> List[Widget]:
        """Build stability dashboard."""
        widgets = []

        widgets.append(MetricWidget(
            widget_id="stab_gm",
            title="GM (transverse)",
            value=self._format(get_state_value(self.state, "stability.gm_transverse_m")),
            unit="m",
            row=0, col=0,
        ))

        widgets.append(MetricWidget(
            widget_id="stab_gz_max",
            title="GZ Max",
            value=self._format(get_state_value(self.state, "stability.gz_max")),
            unit="m",
            row=0, col=1,
        ))

        widgets.append(MetricWidget(
            widget_id="stab_range",
            title="Range of Stability",
            value=self._format(get_state_value(self.state, "stability.range_deg")),
            unit="\u00b0",
            row=0, col=2,
        ))

        return widgets

    def _format(self, value: Any) -> str:
        if value is None:
            return "\u2014"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _count_completed_phases(self) -> int:
        phases = [
            "mission", "hull_form", "structure", "propulsion",
            "systems", "weight_stability", "compliance", "production"
        ]
        count = 0
        for phase in phases:
            # v1.1: Use get_phase_status with translation
            status = get_phase_status(self.state, phase, "pending")
            if status in ["completed", "approved"]:
                count += 1
        return count
