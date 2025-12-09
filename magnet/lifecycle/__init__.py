"""
lifecycle/ - Design Lifecycle & Export
BRAVO OWNS THIS FILE.

Section 45: Design Lifecycle

This module provides version control, branching, and export capabilities.
"""

from .versions import (
    VersionStatus,
    DesignVersion,
    DesignBranch,
    compute_state_hash,
    HASH_EXCLUDE_FIELDS,
)

from .manager import (
    LifecycleManager,
)

from .export import (
    ExportFormat,
    ExportConfig,
    DesignExporter,
)

__all__ = [
    # Versions
    "VersionStatus",
    "DesignVersion",
    "DesignBranch",
    "compute_state_hash",
    "HASH_EXCLUDE_FIELDS",
    # Manager
    "LifecycleManager",
    # Export
    "ExportFormat",
    "ExportConfig",
    "DesignExporter",
]
