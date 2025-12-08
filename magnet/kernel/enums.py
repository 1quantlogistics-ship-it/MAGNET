"""
kernel/enums.py - Kernel enumerations.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - Integration Kernel enumerations.
"""

from enum import Enum


class PhaseStatus(Enum):
    """Phase execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class GateCondition(Enum):
    """Gate condition types."""
    ALL_PASS = "all_pass"           # All validators must pass
    CRITICAL_PASS = "critical_pass" # Critical validators must pass
    THRESHOLD = "threshold"          # Pass rate >= threshold
    MANUAL = "manual"               # Manual approval required


class SessionStatus(Enum):
    """Design session status."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseType(Enum):
    """Phase types for categorization."""
    DEFINITION = "definition"       # mission, requirements
    ANALYSIS = "analysis"           # hull, structure, stability
    INTEGRATION = "integration"     # arrangement, loading
    VERIFICATION = "verification"   # compliance, cost
    OUTPUT = "output"               # reporting, optimization
    CUSTOM = "custom"               # Custom phases
