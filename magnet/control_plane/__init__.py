"""
MAGNET Control Plane v1.1 (Two-Phase WAL)

The audit spine that makes everything else trustworthy.

Two-Phase WAL Flow:
1. PENDING record written BEFORE commit attempt
2. COMMITTED/INCOMPLETE/ABORTED written AFTER commit outcome
3. Every design_version has at least a receipt stub

Modules:
- hsv: HypotheticalStateView for truth-preserving counterfactual previews
- explain: ExplainRecord schema with two-phase WAL for evidence-based auditability
- query: Query Mode for retrieving stored evidence
"""

from magnet.control_plane.hsv import (
    HypotheticalStateView,
    ProjectedValue,
    ValueSource,
    GEOMETRY_AFFECTING_PATHS,
    DERIVED_HYDROSTATIC_PATHS,
    KERNEL_BASELINES,
)
from magnet.control_plane.explain import (
    # Record status (two-phase WAL)
    RecordStatus,
    # Core schemas
    ExplainRecord,
    PathDelta,
    ValidatorReceipt,
    MetricDelta,
    CalculationProvenance,
    # Provenance types
    ChangeSource,
    ApprovalType,
    ValidatorStatus,
    # Stores
    ExplainRecordStore,
    DurableExplainRecordStore,
    # Factory functions (two-phase)
    create_pending_record,
    finalize_record,
    mark_incomplete,
    mark_aborted,
    # Legacy factory
    create_explain_record,
    # Store management
    get_explain_store,
    reset_explain_store,
    set_explain_store,
)
from magnet.control_plane.query import (
    query_explain,
    query_history,
    query_impact,
    query_latest,
    query_pending,
    DualOutput,
)
from magnet.control_plane.path_registry import (
    PathRegistry,
    PathMetadata,
    get_path_registry,
    reset_path_registry,
)
from magnet.control_plane.why_router import (
    WhyQueryRouter,
    WhyQueryRequest,
    WhyQueryResult,
    WhyQueryExtraction,
    WhyIntent,
    get_why_router,
    reset_why_router,
    get_router_metrics,
    RouterMetrics,
    ROUTER_METRICS,
)

__all__ = [
    # HSV
    "HypotheticalStateView",
    "ProjectedValue",
    "ValueSource",
    "GEOMETRY_AFFECTING_PATHS",
    "DERIVED_HYDROSTATIC_PATHS",
    "KERNEL_BASELINES",
    # Record Status
    "RecordStatus",
    # Explain Schemas
    "ExplainRecord",
    "PathDelta",
    "ValidatorReceipt",
    "MetricDelta",
    "CalculationProvenance",
    # Provenance Types
    "ChangeSource",
    "ApprovalType",
    "ValidatorStatus",
    # Stores
    "ExplainRecordStore",
    "DurableExplainRecordStore",
    # Factory Functions (Two-Phase WAL)
    "create_pending_record",
    "finalize_record",
    "mark_incomplete",
    "mark_aborted",
    "create_explain_record",
    # Store Management
    "get_explain_store",
    "reset_explain_store",
    "set_explain_store",
    # Query Mode
    "query_explain",
    "query_history",
    "query_impact",
    "query_latest",
    "query_pending",
    "DualOutput",
    # Path Registry
    "PathRegistry",
    "PathMetadata",
    "get_path_registry",
    "reset_path_registry",
    # Why Query Router
    "WhyQueryRouter",
    "WhyQueryRequest",
    "WhyQueryResult",
    "WhyQueryExtraction",
    "WhyIntent",
    "get_why_router",
    "reset_why_router",
    # Router Metrics (Determinism Audit)
    "get_router_metrics",
    "RouterMetrics",
    "ROUTER_METRICS",
]
