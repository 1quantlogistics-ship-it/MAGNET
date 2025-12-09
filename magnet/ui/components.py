"""
ui/components.py - Reusable UI components v1.1
BRAVO OWNS THIS FILE.

Section 54: UI Components
Provides reusable components for building interfaces.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING
from enum import Enum
import logging

from .utils import get_state_value, set_state_value

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("ui.components")


# =============================================================================
# COMPONENT BASE
# =============================================================================

class ComponentType(Enum):
    """Types of UI components."""
    INPUT = "input"
    DISPLAY = "display"
    BUTTON = "button"
    SELECT = "select"
    TABLE = "table"
    CHART = "chart"
    CONTAINER = "container"
    PROGRESS = "progress"
    ALERT = "alert"


@dataclass
class ComponentStyle:
    """Styling for components."""
    width: Optional[str] = None
    height: Optional[str] = None
    padding: Optional[str] = None
    margin: Optional[str] = None
    background: Optional[str] = None
    border: Optional[str] = None
    color: Optional[str] = None
    font_size: Optional[str] = None
    text_align: Optional[str] = None
    css_class: str = ""

    def to_css(self) -> str:
        """Convert to CSS style string."""
        styles = []
        if self.width:
            styles.append(f"width: {self.width}")
        if self.height:
            styles.append(f"height: {self.height}")
        if self.padding:
            styles.append(f"padding: {self.padding}")
        if self.margin:
            styles.append(f"margin: {self.margin}")
        if self.background:
            styles.append(f"background: {self.background}")
        if self.border:
            styles.append(f"border: {self.border}")
        if self.color:
            styles.append(f"color: {self.color}")
        if self.font_size:
            styles.append(f"font-size: {self.font_size}")
        if self.text_align:
            styles.append(f"text-align: {self.text_align}")
        return "; ".join(styles)


@dataclass
class Component:
    """Base component class."""
    component_id: str = ""
    component_type: ComponentType = ComponentType.DISPLAY
    label: str = ""
    visible: bool = True
    enabled: bool = True
    style: ComponentStyle = field(default_factory=ComponentStyle)
    tooltip: str = ""
    data: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.component_id,
            "type": self.component_type.value,
            "label": self.label,
            "visible": self.visible,
            "enabled": self.enabled,
            "tooltip": self.tooltip,
            "data": self.data,
        }


# =============================================================================
# INPUT COMPONENTS
# =============================================================================

class InputType(Enum):
    """Types of input fields."""
    TEXT = "text"
    NUMBER = "number"
    DECIMAL = "decimal"
    SELECT = "select"
    CHECKBOX = "checkbox"
    SLIDER = "slider"
    COLOR = "color"


@dataclass
class ParameterInput(Component):
    """Input component for design parameters."""
    path: str = ""
    input_type: InputType = InputType.TEXT
    value: Any = None
    default_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    unit: str = ""
    options: List[Tuple[str, Any]] = field(default_factory=list)
    required: bool = False
    readonly: bool = False
    validation_pattern: str = ""
    placeholder: str = ""

    def __post_init__(self):
        self.component_type = ComponentType.INPUT

    def validate(self) -> Tuple[bool, str]:
        """Validate current value."""
        if self.required and self.value is None:
            return False, f"{self.label} is required"

        if self.input_type in [InputType.NUMBER, InputType.DECIMAL]:
            if self.value is not None:
                try:
                    val = float(self.value)
                    if self.min_value is not None and val < self.min_value:
                        return False, f"{self.label} must be >= {self.min_value}"
                    if self.max_value is not None and val > self.max_value:
                        return False, f"{self.label} must be <= {self.max_value}"
                except (ValueError, TypeError):
                    return False, f"{self.label} must be a number"

        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "path": self.path,
            "input_type": self.input_type.value,
            "value": self.value,
            "default": self.default_value,
            "min": self.min_value,
            "max": self.max_value,
            "step": self.step,
            "unit": self.unit,
            "required": self.required,
            "readonly": self.readonly,
            "placeholder": self.placeholder,
        })
        if self.options:
            base["options"] = [{"label": o[0], "value": o[1]} for o in self.options]
        return base

    def render_ascii(self) -> str:
        """Render as ASCII input representation."""
        value_str = str(self.value) if self.value is not None else self.placeholder or "---"
        unit_str = f" {self.unit}" if self.unit else ""
        req_str = "*" if self.required else ""
        return f"{self.label}{req_str}: [{value_str}{unit_str}]"

    def render_html(self) -> str:
        """Render as HTML input element."""
        attrs = [
            f'id="{self.component_id}"',
            f'name="{self.path}"',
        ]

        if self.input_type == InputType.SELECT:
            options_html = "\n".join(
                f'<option value="{v}" {"selected" if v == self.value else ""}>{l}</option>'
                for l, v in self.options
            )
            return f'<select {" ".join(attrs)}>{options_html}</select>'

        input_type = {
            InputType.TEXT: "text",
            InputType.NUMBER: "number",
            InputType.DECIMAL: "number",
            InputType.CHECKBOX: "checkbox",
            InputType.COLOR: "color",
            InputType.SLIDER: "range",
        }.get(self.input_type, "text")

        attrs.append(f'type="{input_type}"')

        if self.value is not None:
            if self.input_type == InputType.CHECKBOX:
                if self.value:
                    attrs.append("checked")
            else:
                attrs.append(f'value="{self.value}"')

        if self.min_value is not None:
            attrs.append(f'min="{self.min_value}"')
        if self.max_value is not None:
            attrs.append(f'max="{self.max_value}"')
        if self.step is not None:
            attrs.append(f'step="{self.step}"')
        if self.placeholder:
            attrs.append(f'placeholder="{self.placeholder}"')
        if self.required:
            attrs.append("required")
        if self.readonly:
            attrs.append("readonly")

        return f'<input {" ".join(attrs)} />'


@dataclass
class ParameterGroup:
    """Group of related parameter inputs."""
    group_id: str = ""
    title: str = ""
    description: str = ""
    parameters: List[ParameterInput] = field(default_factory=list)
    collapsed: bool = False

    def add_parameter(self, param: ParameterInput) -> None:
        """Add parameter to group."""
        self.parameters.append(param)

    def get_values(self) -> Dict[str, Any]:
        """Get all parameter values."""
        return {p.path: p.value for p in self.parameters}

    def validate_all(self) -> Tuple[bool, List[str]]:
        """Validate all parameters."""
        errors = []
        for param in self.parameters:
            valid, msg = param.validate()
            if not valid:
                errors.append(msg)
        return len(errors) == 0, errors

    def render_ascii(self) -> str:
        """Render as ASCII."""
        lines = [f"[{self.title}]", "-" * 40]
        for param in self.parameters:
            lines.append(f"  {param.render_ascii()}")
        return "\n".join(lines)


# =============================================================================
# DISPLAY COMPONENTS
# =============================================================================

@dataclass
class ValueDisplay(Component):
    """Display component for showing values."""
    path: str = ""
    value: Any = None
    unit: str = ""
    format_string: str = ""
    precision: int = 2
    show_trend: bool = False
    trend_value: Optional[float] = None
    status: str = "normal"

    def __post_init__(self):
        self.component_type = ComponentType.DISPLAY

    def format_value(self) -> str:
        """Format the display value."""
        if self.value is None:
            return "\u2014"  # em dash

        if self.format_string:
            try:
                return self.format_string.format(self.value)
            except (ValueError, KeyError):
                pass

        if isinstance(self.value, float):
            return f"{self.value:.{self.precision}f}"

        return str(self.value)

    def render_ascii(self) -> str:
        """Render as ASCII."""
        formatted = self.format_value()
        unit_str = f" {self.unit}" if self.unit else ""
        trend_str = ""
        if self.show_trend and self.trend_value is not None:
            if self.trend_value > 0:
                trend_str = f" \u2191{self.trend_value:+.1f}"
            elif self.trend_value < 0:
                trend_str = f" \u2193{self.trend_value:.1f}"
        return f"{self.label}: {formatted}{unit_str}{trend_str}"

    def render_html(self) -> str:
        """Render as HTML."""
        formatted = self.format_value()
        trend_html = ""
        if self.show_trend and self.trend_value is not None:
            trend_class = "up" if self.trend_value > 0 else "down"
            trend_html = f'<span class="trend {trend_class}">{self.trend_value:+.1f}</span>'

        return f'''
        <div class="value-display status-{self.status}">
            <span class="label">{self.label}</span>
            <span class="value">{formatted}</span>
            <span class="unit">{self.unit}</span>
            {trend_html}
        </div>
        '''


@dataclass
class AlertComponent(Component):
    """Alert/notification component."""
    message: str = ""
    severity: str = "info"
    dismissible: bool = True
    icon: str = ""

    SEVERITY_ICONS = {
        "info": "\u2139",      # ℹ
        "success": "\u2713",   # ✓
        "warning": "\u26a0",   # ⚠
        "error": "\u2717",     # ✗
        "critical": "\u2620",  # ☠
    }

    def __post_init__(self):
        self.component_type = ComponentType.ALERT
        if not self.icon:
            self.icon = self.SEVERITY_ICONS.get(self.severity, "")

    def render_ascii(self) -> str:
        """Render as ASCII."""
        return f"{self.icon} [{self.severity.upper()}] {self.message}"

    def render_html(self) -> str:
        """Render as HTML."""
        dismiss = '<button class="dismiss">&times;</button>' if self.dismissible else ""
        return f'''
        <div class="alert alert-{self.severity}">
            <span class="icon">{self.icon}</span>
            <span class="message">{self.message}</span>
            {dismiss}
        </div>
        '''


# =============================================================================
# BUTTON COMPONENTS
# =============================================================================

@dataclass
class ButtonComponent(Component):
    """Button component."""
    text: str = ""
    action: str = ""
    variant: str = "default"
    icon: str = ""
    confirm_message: str = ""

    def __post_init__(self):
        self.component_type = ComponentType.BUTTON

    def render_ascii(self) -> str:
        """Render as ASCII."""
        icon_str = f"{self.icon} " if self.icon else ""
        return f"[{icon_str}{self.text}]"

    def render_html(self) -> str:
        """Render as HTML."""
        attrs = [
            f'id="{self.component_id}"',
            f'class="btn btn-{self.variant}"',
            f'data-action="{self.action}"',
        ]
        if not self.enabled:
            attrs.append("disabled")
        if self.confirm_message:
            attrs.append(f'data-confirm="{self.confirm_message}"')

        icon_html = f'<span class="icon">{self.icon}</span>' if self.icon else ""
        return f'<button {" ".join(attrs)}>{icon_html}{self.text}</button>'


@dataclass
class ButtonGroup:
    """Group of related buttons."""
    group_id: str = ""
    buttons: List[ButtonComponent] = field(default_factory=list)
    orientation: str = "horizontal"

    def add_button(self, btn: ButtonComponent) -> None:
        """Add button to group."""
        self.buttons.append(btn)

    def render_ascii(self) -> str:
        """Render as ASCII."""
        sep = "  " if self.orientation == "horizontal" else "\n"
        return sep.join(b.render_ascii() for b in self.buttons)


# =============================================================================
# TABLE COMPONENTS
# =============================================================================

@dataclass
class Column:
    """Table column definition."""
    key: str = ""
    header: str = ""
    width: Optional[str] = None
    align: str = "left"
    format_func: Optional[Callable] = None
    sortable: bool = False

    def format_value(self, value: Any) -> str:
        """Format a cell value."""
        if self.format_func:
            return self.format_func(value)
        if value is None:
            return "\u2014"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)


@dataclass
class DataTable(Component):
    """Data table component."""
    columns: List[Column] = field(default_factory=list)
    rows: List[Dict[str, Any]] = field(default_factory=list)
    page_size: int = 10
    current_page: int = 0
    sortable: bool = True
    filterable: bool = False
    selectable: bool = False
    selected_rows: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.component_type = ComponentType.TABLE

    def get_page_rows(self) -> List[Dict[str, Any]]:
        """Get rows for current page."""
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.rows[start:end]

    def total_pages(self) -> int:
        """Get total number of pages."""
        if not self.rows:
            return 1
        return (len(self.rows) - 1) // self.page_size + 1

    def render_ascii(self) -> str:
        """Render as ASCII table."""
        if not self.columns:
            return "[Empty table]"

        # Calculate column widths
        col_widths = {}
        for col in self.columns:
            col_widths[col.key] = len(col.header)

        for row in self.get_page_rows():
            for col in self.columns:
                val = col.format_value(row.get(col.key))
                col_widths[col.key] = max(col_widths[col.key], len(val))

        # Build header
        header_parts = []
        for col in self.columns:
            header_parts.append(col.header.ljust(col_widths[col.key]))
        header = " | ".join(header_parts)

        lines = [header, "-" * len(header)]

        # Build rows
        for row in self.get_page_rows():
            row_parts = []
            for col in self.columns:
                val = col.format_value(row.get(col.key))
                if col.align == "right":
                    row_parts.append(val.rjust(col_widths[col.key]))
                else:
                    row_parts.append(val.ljust(col_widths[col.key]))
            lines.append(" | ".join(row_parts))

        # Pagination
        if self.total_pages() > 1:
            lines.append("")
            lines.append(f"Page {self.current_page + 1}/{self.total_pages()}")

        return "\n".join(lines)

    def render_html(self) -> str:
        """Render as HTML table."""
        html = ['<table class="data-table">', '  <thead>', '    <tr>']

        for col in self.columns:
            sortable = 'sortable' if col.sortable else ''
            html.append(f'      <th class="{sortable}" data-key="{col.key}">{col.header}</th>')

        html.extend(['    </tr>', '  </thead>', '  <tbody>'])

        for i, row in enumerate(self.get_page_rows()):
            selected = 'selected' if i in self.selected_rows else ''
            html.append(f'    <tr class="{selected}" data-row="{i}">')
            for col in self.columns:
                val = col.format_value(row.get(col.key))
                html.append(f'      <td style="text-align: {col.align}">{val}</td>')
            html.append('    </tr>')

        html.extend(['  </tbody>', '</table>'])
        return "\n".join(html)


# =============================================================================
# PROGRESS COMPONENTS
# =============================================================================

@dataclass
class ProgressBar(Component):
    """Progress bar component."""
    current: float = 0
    total: float = 100
    show_percent: bool = True
    show_label: bool = True
    color: str = "primary"

    def __post_init__(self):
        self.component_type = ComponentType.PROGRESS

    @property
    def percent(self) -> float:
        """Get percentage complete."""
        if self.total == 0:
            return 0
        return min(100, max(0, (self.current / self.total) * 100))

    def render_ascii(self, width: int = 30) -> str:
        """Render as ASCII progress bar."""
        filled = int(width * self.percent / 100)
        empty = width - filled
        bar = "\u2588" * filled + "\u2591" * empty

        parts = []
        if self.show_label and self.label:
            parts.append(f"{self.label}: ")
        parts.append(f"[{bar}]")
        if self.show_percent:
            parts.append(f" {self.percent:.0f}%")

        return "".join(parts)

    def render_html(self) -> str:
        """Render as HTML progress bar."""
        label_html = f'<span class="label">{self.label}</span>' if self.show_label else ""
        percent_html = f'<span class="percent">{self.percent:.0f}%</span>' if self.show_percent else ""

        return f'''
        <div class="progress-container">
            {label_html}
            <div class="progress-bar color-{self.color}">
                <div class="progress-fill" style="width: {self.percent}%"></div>
            </div>
            {percent_html}
        </div>
        '''


@dataclass
class StepProgress(Component):
    """Step-based progress component."""
    steps: List[str] = field(default_factory=list)
    current_step: int = 0
    completed_steps: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.component_type = ComponentType.PROGRESS

    def render_ascii(self) -> str:
        """Render as ASCII step progress."""
        lines = []
        for i, step in enumerate(self.steps):
            if i in self.completed_steps:
                icon = "\u2713"  # ✓
            elif i == self.current_step:
                icon = "\u25c9"  # ◉
            else:
                icon = "\u25cb"  # ○

            connector = ""
            if i < len(self.steps) - 1:
                connector = "\n    |"

            lines.append(f" {icon} {step}{connector}")

        return "\n".join(lines)


# =============================================================================
# CONTAINER COMPONENTS
# =============================================================================

@dataclass
class Panel(Component):
    """Panel container component."""
    title: str = ""
    content: str = ""
    children: List[Component] = field(default_factory=list)
    collapsible: bool = False
    collapsed: bool = False
    bordered: bool = True

    def __post_init__(self):
        self.component_type = ComponentType.CONTAINER

    def add_child(self, component: Component) -> None:
        """Add child component."""
        self.children.append(component)

    def render_ascii(self) -> str:
        """Render as ASCII panel."""
        lines = []

        if self.title:
            lines.append(f"\u250c{'─' * 48}\u2510")
            lines.append(f"\u2502 {self.title:<46} \u2502")
            lines.append(f"\u251c{'─' * 48}\u2524")
        else:
            lines.append(f"\u250c{'─' * 48}\u2510")

        if self.content:
            for line in self.content.split("\n"):
                lines.append(f"\u2502 {line:<46} \u2502")

        for child in self.children:
            if hasattr(child, 'render_ascii'):
                child_lines = child.render_ascii().split("\n")
                for line in child_lines:
                    lines.append(f"\u2502 {line:<46} \u2502")

        lines.append(f"\u2514{'─' * 48}\u2518")

        return "\n".join(lines)


@dataclass
class Tab:
    """Single tab definition."""
    tab_id: str = ""
    title: str = ""
    icon: str = ""
    content: str = ""
    children: List[Component] = field(default_factory=list)
    disabled: bool = False


@dataclass
class TabContainer(Component):
    """Tabbed container component."""
    tabs: List[Tab] = field(default_factory=list)
    active_tab: int = 0

    def __post_init__(self):
        self.component_type = ComponentType.CONTAINER

    def add_tab(self, tab: Tab) -> None:
        """Add a tab."""
        self.tabs.append(tab)

    def render_ascii(self) -> str:
        """Render as ASCII tabs."""
        if not self.tabs:
            return "[Empty tabs]"

        # Tab headers
        headers = []
        for i, tab in enumerate(self.tabs):
            marker = "\u25bc" if i == self.active_tab else " "
            headers.append(f"[{marker} {tab.title}]")

        lines = ["  ".join(headers), "=" * 50]

        # Active tab content
        if 0 <= self.active_tab < len(self.tabs):
            active = self.tabs[self.active_tab]
            if active.content:
                lines.append(active.content)
            for child in active.children:
                if hasattr(child, 'render_ascii'):
                    lines.append(child.render_ascii())

        return "\n".join(lines)


# =============================================================================
# FORM BUILDER
# =============================================================================

class FormBuilder:
    """Builder for creating forms from state schema."""

    def __init__(self, state: "StateManager"):
        self.state = state

    def build_hull_form(self) -> ParameterGroup:
        """Build hull parameters form."""
        group = ParameterGroup(
            group_id="hull_params",
            title="Hull Parameters",
            description="Principal dimensions and form coefficients",
        )

        group.add_parameter(ParameterInput(
            component_id="loa",
            label="Length Overall",
            path="hull.loa",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "hull.loa"),
            min_value=5.0,
            max_value=200.0,
            step=0.1,
            unit="m",
            required=True,
        ))

        group.add_parameter(ParameterInput(
            component_id="beam",
            label="Beam",
            path="hull.beam",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "hull.beam"),
            min_value=1.0,
            max_value=40.0,
            step=0.1,
            unit="m",
            required=True,
        ))

        group.add_parameter(ParameterInput(
            component_id="draft",
            label="Draft",
            path="hull.draft",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "hull.draft"),
            min_value=0.5,
            max_value=15.0,
            step=0.1,
            unit="m",
            required=True,
        ))

        group.add_parameter(ParameterInput(
            component_id="depth",
            label="Depth",
            path="hull.depth",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "hull.depth"),
            min_value=1.0,
            max_value=20.0,
            step=0.1,
            unit="m",
        ))

        group.add_parameter(ParameterInput(
            component_id="cb",
            label="Block Coefficient",
            path="hull.cb",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "hull.cb"),
            min_value=0.3,
            max_value=0.9,
            step=0.01,
        ))

        return group

    def build_mission_form(self) -> ParameterGroup:
        """Build mission parameters form."""
        group = ParameterGroup(
            group_id="mission_params",
            title="Mission Parameters",
            description="Speed, range, and operational requirements",
        )

        group.add_parameter(ParameterInput(
            component_id="max_speed",
            label="Maximum Speed",
            path="mission.max_speed_kts",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "mission.max_speed_kts"),
            min_value=5.0,
            max_value=60.0,
            step=0.5,
            unit="kts",
        ))

        group.add_parameter(ParameterInput(
            component_id="cruise_speed",
            label="Cruise Speed",
            path="mission.cruise_speed_kts",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "mission.cruise_speed_kts"),
            min_value=5.0,
            max_value=50.0,
            step=0.5,
            unit="kts",
        ))

        group.add_parameter(ParameterInput(
            component_id="range",
            label="Range",
            path="mission.range_nm",
            input_type=InputType.DECIMAL,
            value=get_state_value(self.state, "mission.range_nm"),
            min_value=50.0,
            max_value=5000.0,
            step=10.0,
            unit="nm",
        ))

        group.add_parameter(ParameterInput(
            component_id="passengers",
            label="Passengers",
            path="mission.passengers",
            input_type=InputType.NUMBER,
            value=get_state_value(self.state, "mission.passengers"),
            min_value=0,
            max_value=500,
            step=1,
        ))

        group.add_parameter(ParameterInput(
            component_id="crew",
            label="Crew",
            path="mission.crew",
            input_type=InputType.NUMBER,
            value=get_state_value(self.state, "mission.crew"),
            min_value=1,
            max_value=50,
            step=1,
        ))

        return group

    def build_propulsion_form(self) -> ParameterGroup:
        """Build propulsion parameters form."""
        group = ParameterGroup(
            group_id="propulsion_params",
            title="Propulsion",
            description="Engine and propulsion configuration",
        )

        group.add_parameter(ParameterInput(
            component_id="prop_type",
            label="Propulsion Type",
            path="propulsion.propulsion_type",
            input_type=InputType.SELECT,
            value=get_state_value(self.state, "propulsion.propulsion_type"),
            options=[
                ("Waterjet", "waterjet"),
                ("Fixed Pitch Propeller", "fixed_pitch"),
                ("Controllable Pitch Propeller", "cpp"),
                ("Surface Drive", "surface_drive"),
                ("Outboard", "outboard"),
            ],
        ))

        group.add_parameter(ParameterInput(
            component_id="num_engines",
            label="Number of Engines",
            path="propulsion.num_engines",
            input_type=InputType.NUMBER,
            value=get_state_value(self.state, "propulsion.num_engines"),
            min_value=1,
            max_value=6,
            step=1,
        ))

        group.add_parameter(ParameterInput(
            component_id="installed_power",
            label="Total Installed Power",
            path="propulsion.installed_power_kw",
            input_type=InputType.NUMBER,
            value=get_state_value(self.state, "propulsion.installed_power_kw"),
            min_value=100,
            max_value=50000,
            step=100,
            unit="kW",
        ))

        return group


# =============================================================================
# COMPONENT REGISTRY
# =============================================================================

class ComponentRegistry:
    """Registry for managing UI components."""

    def __init__(self):
        self._components: Dict[str, Component] = {}
        self._by_type: Dict[ComponentType, List[str]] = {}

    def register(self, component: Component) -> None:
        """Register a component."""
        self._components[component.component_id] = component

        ctype = component.component_type
        if ctype not in self._by_type:
            self._by_type[ctype] = []
        self._by_type[ctype].append(component.component_id)

    def get(self, component_id: str) -> Optional[Component]:
        """Get component by ID."""
        return self._components.get(component_id)

    def get_by_type(self, component_type: ComponentType) -> List[Component]:
        """Get all components of a type."""
        ids = self._by_type.get(component_type, [])
        return [self._components[cid] for cid in ids if cid in self._components]

    def clear(self) -> None:
        """Clear all components."""
        self._components.clear()
        self._by_type.clear()


# Global registry
component_registry = ComponentRegistry()
