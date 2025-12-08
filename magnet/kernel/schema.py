"""
kernel/schema.py - Kernel data structures.

BRAVO OWNS THIS FILE.

Module 15 v1.1 - Integration Kernel data structures.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .enums import PhaseStatus, GateCondition, SessionStatus


@dataclass
class PhaseResult:
    """Result of a phase execution."""
    phase_name: str
    status: PhaseStatus

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    validators_run: int = 0
    validators_passed: int = 0
    validators_failed: int = 0

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        """Get phase duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def pass_rate(self) -> float:
        """Get validator pass rate."""
        if self.validators_run == 0:
            return 0.0
        return self.validators_passed / self.validators_run

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_name": self.phase_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_s": round(self.duration_s, 2),
            "validators_run": self.validators_run,
            "validators_passed": self.validators_passed,
            "validators_failed": self.validators_failed,
            "pass_rate": round(self.pass_rate, 2),
            "errors": self.errors,
            "warnings": self.warnings,
        }


@dataclass
class GateResult:
    """Result of a gate evaluation."""
    gate_name: str
    condition: GateCondition
    passed: bool

    evaluated_at: Optional[datetime] = None
    threshold: Optional[float] = None
    actual_value: Optional[float] = None

    blocking_failures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "condition": self.condition.value,
            "passed": self.passed,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "threshold": self.threshold,
            "actual_value": self.actual_value,
            "blocking_failures": self.blocking_failures,
        }


@dataclass
class SessionState:
    """Design session state."""
    session_id: str
    design_id: str
    status: SessionStatus

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    current_phase: Optional[str] = None
    completed_phases: List[str] = field(default_factory=list)

    phase_results: Dict[str, PhaseResult] = field(default_factory=dict)
    gate_results: Dict[str, GateResult] = field(default_factory=dict)

    total_validators_run: int = 0
    total_validators_passed: int = 0

    def add_phase_result(self, result: PhaseResult) -> None:
        """Add phase result and update counters."""
        self.phase_results[result.phase_name] = result
        self.total_validators_run += result.validators_run
        self.total_validators_passed += result.validators_passed
        self.updated_at = datetime.now(timezone.utc)

        if result.status == PhaseStatus.COMPLETED:
            if result.phase_name not in self.completed_phases:
                self.completed_phases.append(result.phase_name)

    def add_gate_result(self, result: GateResult) -> None:
        """Add gate result."""
        self.gate_results[result.gate_name] = result
        self.updated_at = datetime.now(timezone.utc)

    @property
    def overall_pass_rate(self) -> float:
        """Get overall validator pass rate."""
        if self.total_validators_run == 0:
            return 0.0
        return self.total_validators_passed / self.total_validators_run

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "design_id": self.design_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_phase": self.current_phase,
            "completed_phases": self.completed_phases,
            "phase_results": {k: v.to_dict() for k, v in self.phase_results.items()},
            "gate_results": {k: v.to_dict() for k, v in self.gate_results.items()},
            "total_validators_run": self.total_validators_run,
            "total_validators_passed": self.total_validators_passed,
            "overall_pass_rate": round(self.overall_pass_rate, 2),
        }
