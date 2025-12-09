"""
ui/ - User Interface Layer
BRAVO OWNS THIS FILE.

Modules 51-54: CLI, Vision, Reporting & UI Components
- Module 51: CLI Interface
- Module 52: Vision Subsystem
- Module 53: Reporting System
- Module 54: UI Components

Provides unified state access and UI utilities for all interface modules.
"""

from .utils import (
    # Field aliases
    UI_FIELD_ALIASES,
    # State access
    get_state_value,
    set_state_value,
    get_nested,
    # Phase status
    PHASE_STATE_ENUM_MAP,
    UI_STATUS_TO_ENUM,
    get_phase_status,
    set_phase_status,
    # Serialization
    serialize_state,
    load_state_from_dict,
    # Registry
    SnapshotRegistry,
    snapshot_registry,
    # Hooks
    PhaseCompletionHooks,
    phase_hooks,
)

from .dashboard import (
    WidgetType,
    Widget,
    MetricWidget,
    ProgressWidget,
    ValidationWidget,
    TableWidget,
    DashboardBuilder,
)

from .phase_navigator import (
    PhaseStatus,
    PhaseInfo,
    PHASE_DEFINITIONS,
    PhaseNavigator,
)

from .validation_panel import (
    ValidationSeverity,
    ValidationCategory,
    ValidationMessage,
    ValidationSummary,
    ValidationResult,
    ValidationPanel,
    ValidationHistory,
    CategoryPanel,
    ComplianceMatrix,
)

from .components import (
    ComponentType,
    ComponentStyle,
    Component,
    InputType,
    ParameterInput,
    ParameterGroup,
    ValueDisplay,
    AlertComponent,
    ButtonComponent,
    ButtonGroup,
    Column,
    DataTable,
    ProgressBar,
    StepProgress,
    Panel,
    Tab,
    TabContainer,
    FormBuilder,
    ComponentRegistry,
    component_registry,
)

from .chat import (
    MessageRole,
    ChatMessage,
    ChatSession,
    ChatHandler,
)

from .events import (
    EventType,
    UIEvent,
    EventBus,
    event_bus,
    emit_state_changed,
    emit_phase_completed,
    emit_validation_completed,
    emit_snapshot_created,
)


__all__ = [
    # Aliases
    "UI_FIELD_ALIASES",
    # State access
    "get_state_value",
    "set_state_value",
    "get_nested",
    # Phase status
    "PHASE_STATE_ENUM_MAP",
    "UI_STATUS_TO_ENUM",
    "get_phase_status",
    "set_phase_status",
    # Serialization
    "serialize_state",
    "load_state_from_dict",
    # Registry
    "SnapshotRegistry",
    "snapshot_registry",
    # Hooks
    "PhaseCompletionHooks",
    "phase_hooks",
    # Dashboard
    "WidgetType",
    "Widget",
    "MetricWidget",
    "ProgressWidget",
    "ValidationWidget",
    "TableWidget",
    "DashboardBuilder",
    # Phase Navigator
    "PhaseStatus",
    "PhaseInfo",
    "PHASE_DEFINITIONS",
    "PhaseNavigator",
    # Chat
    "MessageRole",
    "ChatMessage",
    "ChatSession",
    "ChatHandler",
    # Events
    "EventType",
    "UIEvent",
    "EventBus",
    "event_bus",
    "emit_state_changed",
    "emit_phase_completed",
    "emit_validation_completed",
    "emit_snapshot_created",
    # Validation Panel
    "ValidationSeverity",
    "ValidationCategory",
    "ValidationMessage",
    "ValidationSummary",
    "ValidationResult",
    "ValidationPanel",
    "ValidationHistory",
    "CategoryPanel",
    "ComplianceMatrix",
    # Components
    "ComponentType",
    "ComponentStyle",
    "Component",
    "InputType",
    "ParameterInput",
    "ParameterGroup",
    "ValueDisplay",
    "AlertComponent",
    "ButtonComponent",
    "ButtonGroup",
    "Column",
    "DataTable",
    "ProgressBar",
    "StepProgress",
    "Panel",
    "Tab",
    "TabContainer",
    "FormBuilder",
    "ComponentRegistry",
    "component_registry",
]
