"""
MAGNET Validator Taxonomy

Module 04 v1.1 - Production-Ready

Defines validator categories, types, and metadata.

v1.1 Fixes Applied:
- FIX #2: Parameter naming normalized to Section 1 conventions
- FIX #5: Clear separation of validation vs execution failure
- FIX #6: Deterministic input hashing via JSON normalization
- FIX #9: Resource requirements enforced by scheduler
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
import hashlib
import json
import logging

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ValidatorCategory(Enum):
    """High-level categories of validators."""
    PHYSICS = "physics"
    BOUNDS = "bounds"
    CLASS_RULES = "class_rules"
    STABILITY = "stability"
    WEIGHT = "weight"            # NEW v1.1: Weight estimation
    ARRANGEMENT = "arrangement"  # NEW v1.1: General arrangement
    LOADING = "loading"          # NEW v1.1: Loading computer
    REGULATORY = "regulatory"
    PRODUCTION = "production"
    ECONOMICS = "economics"      # NEW v1.1: Cost estimation
    OPTIMIZATION = "optimization"  # NEW v1.1: Design optimization
    REPORTING = "reporting"      # NEW v1.1: Report generation
    CUSTOM = "custom"


class ValidatorPriority(Enum):
    """Execution priority (lower = runs first)."""
    CRITICAL = 1      # Must run first (physics foundations)
    HIGH = 2          # Important dependencies
    NORMAL = 3        # Standard validators
    LOW = 4           # Can run later
    BACKGROUND = 5    # Non-blocking


class ValidatorState(Enum):
    """Lifecycle state of a validator."""
    PENDING = "pending"           # Queued, not yet run
    RUNNING = "running"           # Currently executing
    PASSED = "passed"             # Completed successfully
    FAILED = "failed"             # Completed with validation failures
    WARNING = "warning"           # Passed with warnings
    STALE = "stale"              # Results outdated
    SKIPPED = "skipped"          # Intentionally not run
    ERROR = "error"              # Execution error (code failure, NOT validation failure)
    BLOCKED = "blocked"          # Waiting on dependencies
    NOT_IMPLEMENTED = "not_implemented"  # No implementation exists (permanent, not transient)


class ResultSeverity(Enum):
    """
    Severity of validation findings.

    v1.4: Added PREFERENCE for "could be better but not wrong" guidance.
    """
    ERROR = "error"              # Blocks phase advancement
    WARNING = "warning"          # Advisory, doesn't block
    PREFERENCE = "preference"    # v1.4: Could be better, but not wrong
    INFO = "info"                # Informational only
    PASSED = "passed"            # Check passed


# v1.4: Severity ordering for comparison (higher = more severe)
SEVERITY_ORDER = {
    "passed": 0,
    "info": 1,
    "preference": 2,
    "warning": 3,
    "error": 4,
}


class GateRequirement(Enum):
    """
    How a validator participates in gate evaluation (v1.1).

    Gate semantics (consistent invariant):
    1. NOT_IMPLEMENTED validators ALWAYS skip - regardless of GateRequirement
    2. REQUIRED + IMPLEMENTED + FAILED → BLOCK gate
    3. OPTIONAL + FAILED → WARNING (no block)
    4. INFORMATIONAL → LOG only, no gate impact

    This ensures NOT_IMPLEMENTED validators never block phase progression,
    while allowing explicit control over which implemented validators
    are required vs optional.
    """
    REQUIRED = "required"        # MUST pass for gate to pass (if implemented)
    OPTIONAL = "optional"        # Contributes to score but doesn't block
    INFORMATIONAL = "info"       # Logged only, no gate impact


# =============================================================================
# RESOURCE REQUIREMENTS (FIX #9)
# =============================================================================

@dataclass
class ResourceRequirements:
    """
    Resource requirements for a validator.

    FIX #9: Now enforced by resource-aware scheduler.
    """
    cpu_cores: int = 1
    ram_gb: float = 0.5
    gpu_required: bool = False
    gpu_memory_gb: float = 0.0
    disk_gb: float = 0.1

    def fits_in(self, available: "ResourcePool") -> bool:
        """Check if requirements fit in available resources."""
        return (
            self.cpu_cores <= available.cpu_cores and
            self.ram_gb <= available.ram_gb and
            (not self.gpu_required or available.gpu_available) and
            self.gpu_memory_gb <= available.gpu_memory_gb and
            self.disk_gb <= available.disk_gb
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores,
            "ram_gb": self.ram_gb,
            "gpu_required": self.gpu_required,
            "gpu_memory_gb": self.gpu_memory_gb,
            "disk_gb": self.disk_gb,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceRequirements":
        return cls(
            cpu_cores=data.get("cpu_cores", 1),
            ram_gb=data.get("ram_gb", 0.5),
            gpu_required=data.get("gpu_required", False),
            gpu_memory_gb=data.get("gpu_memory_gb", 0.0),
            disk_gb=data.get("disk_gb", 0.1),
        )


@dataclass
class ResourcePool:
    """
    Available resources for validator execution.

    FIX #9: Used by scheduler to manage concurrent execution.
    """
    cpu_cores: int = 4
    ram_gb: float = 8.0
    gpu_available: bool = False
    gpu_memory_gb: float = 0.0
    disk_gb: float = 10.0

    def allocate(self, req: ResourceRequirements) -> bool:
        """Try to allocate resources. Returns True if successful."""
        if not req.fits_in(self):
            return False

        self.cpu_cores -= req.cpu_cores
        self.ram_gb -= req.ram_gb
        if req.gpu_required:
            self.gpu_memory_gb -= req.gpu_memory_gb
        self.disk_gb -= req.disk_gb
        return True

    def release(self, req: ResourceRequirements) -> None:
        """Release allocated resources."""
        self.cpu_cores += req.cpu_cores
        self.ram_gb += req.ram_gb
        if req.gpu_required:
            self.gpu_memory_gb += req.gpu_memory_gb
        self.disk_gb += req.disk_gb

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores,
            "ram_gb": self.ram_gb,
            "gpu_available": self.gpu_available,
            "gpu_memory_gb": self.gpu_memory_gb,
            "disk_gb": self.disk_gb,
        }


# =============================================================================
# VALIDATOR DEFINITION
# =============================================================================

@dataclass
class ValidatorDefinition:
    """
    Complete definition of a validator.

    v1.1: Resource requirements now enforced, parameter names normalized.
    """
    # Identity
    validator_id: str              # e.g., "physics/hydrostatics"
    name: str                      # Human-readable name
    description: str               # What this validator checks

    # Classification
    category: ValidatorCategory
    priority: ValidatorPriority = ValidatorPriority.NORMAL

    # Phase association
    phase: str = ""                # Which phase this validates
    is_gate_condition: bool = False  # Does this block phase advancement?
    gate_severity: ResultSeverity = ResultSeverity.ERROR
    gate_requirement: GateRequirement = GateRequirement.OPTIONAL  # v1.1: Required vs optional

    # Dependencies
    depends_on_validators: List[str] = field(default_factory=list)
    depends_on_parameters: List[str] = field(default_factory=list)  # FIX #2: Use Section 1 names

    # FIX #3: Parameters this validator WRITES (for implicit dependency edges)
    produces_parameters: List[str] = field(default_factory=list)

    # Execution
    timeout_seconds: int = 60
    max_retries: int = 2           # FIX #5: Only for exceptions, not validation failures
    retry_delay_seconds: int = 5
    is_cacheable: bool = True
    cache_ttl_seconds: int = 3600  # 1 hour default

    # Parallelization (FIX #9)
    can_run_parallel: bool = True
    resource_requirements: ResourceRequirements = field(default_factory=ResourceRequirements)

    # Metadata
    version: str = "1.0.0"
    author: str = "system"
    tags: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.validator_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence."""
        return {
            "validator_id": self.validator_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "phase": self.phase,
            "is_gate_condition": self.is_gate_condition,
            "gate_severity": self.gate_severity.value,
            "gate_requirement": self.gate_requirement.value,  # v1.1
            "depends_on_validators": self.depends_on_validators,
            "depends_on_parameters": self.depends_on_parameters,
            "produces_parameters": self.produces_parameters,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "is_cacheable": self.is_cacheable,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "can_run_parallel": self.can_run_parallel,
            "resource_requirements": self.resource_requirements.to_dict(),
            "version": self.version,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidatorDefinition":
        """Load from serialized data."""
        return cls(
            validator_id=data["validator_id"],
            name=data["name"],
            description=data.get("description", ""),
            category=ValidatorCategory(data["category"]),
            priority=ValidatorPriority(data.get("priority", 3)),
            phase=data.get("phase", ""),
            is_gate_condition=data.get("is_gate_condition", False),
            gate_severity=ResultSeverity(data.get("gate_severity", "error")),
            gate_requirement=GateRequirement(data.get("gate_requirement", "optional")),  # v1.1
            depends_on_validators=data.get("depends_on_validators", []),
            depends_on_parameters=data.get("depends_on_parameters", []),
            produces_parameters=data.get("produces_parameters", []),
            timeout_seconds=data.get("timeout_seconds", 60),
            max_retries=data.get("max_retries", 2),
            is_cacheable=data.get("is_cacheable", True),
            cache_ttl_seconds=data.get("cache_ttl_seconds", 3600),
            can_run_parallel=data.get("can_run_parallel", True),
            resource_requirements=ResourceRequirements.from_dict(
                data.get("resource_requirements", {})
            ),
            version=data.get("version", "1.0.0"),
            tags=data.get("tags", []),
        )


# =============================================================================
# VALIDATION RESULT
# =============================================================================

@dataclass
class ValidationFinding:
    """
    A single finding from a validator.

    v1.2: Added `adjustment` field for structured optimization hints.
    The synthesis loop can use these to guide hull mutations.
    """
    finding_id: str
    severity: ResultSeverity
    message: str
    parameter_path: Optional[str] = None
    expected_value: Optional[Any] = None
    actual_value: Optional[Any] = None
    suggestion: Optional[str] = None
    reference: Optional[str] = None  # e.g., "ABS Rule 3-2-1/5.1"

    # v1.2: Structured adjustment hint for synthesis optimization
    # Format: {"path": "hull.lwl", "direction": "increase"|"decrease", "magnitude": 0.05}
    adjustment: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "finding_id": self.finding_id,
            "severity": self.severity.value,
            "message": self.message,
            "parameter_path": self.parameter_path,
            "expected_value": str(self.expected_value) if self.expected_value is not None else None,
            "actual_value": str(self.actual_value) if self.actual_value is not None else None,
            "suggestion": self.suggestion,
            "reference": self.reference,
        }
        if self.adjustment:
            result["adjustment"] = self.adjustment
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationFinding":
        return cls(
            finding_id=data["finding_id"],
            severity=ResultSeverity(data["severity"]),
            message=data["message"],
            parameter_path=data.get("parameter_path"),
            expected_value=data.get("expected_value"),
            actual_value=data.get("actual_value"),
            suggestion=data.get("suggestion"),
            reference=data.get("reference"),
            adjustment=data.get("adjustment"),
        )


@dataclass
class ValidationResult:
    """Complete result from running a validator."""
    validator_id: str
    state: ValidatorState
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Findings
    findings: List[ValidationFinding] = field(default_factory=list)

    # Summary counts
    error_count: int = 0
    warning_count: int = 0
    preference_count: int = 0  # v1.4: "could be better" findings
    info_count: int = 0

    # Execution metadata
    execution_time_ms: int = 0
    was_cached: bool = False
    cache_key: Optional[str] = None
    retry_count: int = 0
    was_skipped_unchanged: bool = False  # FIX #10

    # Error info (for state=ERROR - code failure only)
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    # Input snapshot (for reproducibility)
    input_hash: Optional[str] = None
    parameters_used: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Did validation pass (no errors)?"""
        return self.state in (ValidatorState.PASSED, ValidatorState.WARNING)

    @property
    def has_errors(self) -> bool:
        """Are there blocking errors?"""
        return self.error_count > 0

    @property
    def is_execution_error(self) -> bool:
        """Was this a code failure (not validation failure)?"""
        return self.state == ValidatorState.ERROR

    @property
    def is_not_implemented(self) -> bool:
        """Is this validator missing an implementation? (permanent, not transient)"""
        return self.state == ValidatorState.NOT_IMPLEMENTED

    @property
    def duration(self) -> Optional[timedelta]:
        """Execution duration."""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None

    def add_finding(self, finding: ValidationFinding) -> None:
        """Add a finding and update counts."""
        self.findings.append(finding)
        if finding.severity == ResultSeverity.ERROR:
            self.error_count += 1
        elif finding.severity == ResultSeverity.WARNING:
            self.warning_count += 1
        elif finding.severity == ResultSeverity.PREFERENCE:
            self.preference_count += 1
        elif finding.severity == ResultSeverity.INFO:
            self.info_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence/API."""
        return {
            "validator_id": self.validator_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "findings": [f.to_dict() for f in self.findings],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "preference_count": self.preference_count,  # v1.4
            "info_count": self.info_count,
            "execution_time_ms": self.execution_time_ms,
            "was_cached": self.was_cached,
            "was_skipped_unchanged": self.was_skipped_unchanged,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "passed": self.passed,
            "is_execution_error": self.is_execution_error,
            "is_not_implemented": self.is_not_implemented,
            "input_hash": self.input_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        """Load from serialized data."""
        result = cls(
            validator_id=data["validator_id"],
            state=ValidatorState(data["state"]),
            started_at=datetime.fromisoformat(data["started_at"]),
        )
        if data.get("completed_at"):
            result.completed_at = datetime.fromisoformat(data["completed_at"])
        result.findings = [
            ValidationFinding.from_dict(f) for f in data.get("findings", [])
        ]
        result.error_count = data.get("error_count", 0)
        result.warning_count = data.get("warning_count", 0)
        result.preference_count = data.get("preference_count", 0)  # v1.4
        result.info_count = data.get("info_count", 0)
        result.execution_time_ms = data.get("execution_time_ms", 0)
        result.was_cached = data.get("was_cached", False)
        result.was_skipped_unchanged = data.get("was_skipped_unchanged", False)
        result.retry_count = data.get("retry_count", 0)
        result.error_message = data.get("error_message")
        result.input_hash = data.get("input_hash")
        return result


# =============================================================================
# VALIDATOR INTERFACE (FIX #1, #6)
# =============================================================================

class ValidatorInterface:
    """
    Base interface for validator implementations.

    v1.1 Changes:
    - FIX #1: Uses state_manager.get() not read()
    - FIX #6: JSON normalization for input hashing
    """

    def __init__(self, definition: ValidatorDefinition):
        self.definition = definition

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Run validation and return result.

        Override this in concrete implementations.

        IMPORTANT (FIX #5):
        - Return state=FAILED for validation failures (will NOT retry)
        - Return state=PASSED/WARNING for success
        - Raise exceptions for code failures (WILL retry)
        """
        raise NotImplementedError("Subclasses must implement validate()")

    def get_input_hash(self, state_manager: "StateManager") -> str:
        """
        Compute hash of inputs for caching.

        FIX #1: Uses get() which exists in StateManager
        FIX #6: JSON normalization for deterministic hashing
        """
        values = {}
        for param in self.definition.depends_on_parameters:
            # FIX #1: Use get() which exists in StateManager
            value = state_manager.get(param)
            # FIX #6: Keep native types for JSON serialization
            values[param] = value

        # FIX #6: Deterministic JSON serialization
        try:
            content = json.dumps(
                values,
                sort_keys=True,
                separators=(',', ':'),
                default=str  # Handle non-JSON types
            )
        except (TypeError, ValueError):
            # Fallback for complex types
            content = str(sorted(values.items()))

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def should_skip_unchanged(
        self,
        state_manager: "StateManager",
        last_validation_time: Optional[datetime]
    ) -> bool:
        """
        Check if validator can be skipped due to unchanged inputs.

        FIX #10: Skip validators whose inputs haven't changed.
        """
        if last_validation_time is None:
            return False

        for param in self.definition.depends_on_parameters:
            metadata = state_manager.get_field_metadata(param)
            if metadata and metadata.last_modified > last_validation_time:
                return False

        return True


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_passed_result(
    validator_id: str,
    message: str = "Validation passed",
    execution_time_ms: int = 0,
) -> ValidationResult:
    """Create a passing validation result."""
    import uuid
    result = ValidationResult(
        validator_id=validator_id,
        state=ValidatorState.PASSED,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        execution_time_ms=execution_time_ms,
    )
    result.add_finding(ValidationFinding(
        finding_id=str(uuid.uuid4())[:8],
        severity=ResultSeverity.PASSED,
        message=message,
    ))
    return result


def create_failed_result(
    validator_id: str,
    error_message: str,
    parameter_path: Optional[str] = None,
    suggestion: Optional[str] = None,
) -> ValidationResult:
    """Create a failing validation result."""
    import uuid
    result = ValidationResult(
        validator_id=validator_id,
        state=ValidatorState.FAILED,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )
    result.add_finding(ValidationFinding(
        finding_id=str(uuid.uuid4())[:8],
        severity=ResultSeverity.ERROR,
        message=error_message,
        parameter_path=parameter_path,
        suggestion=suggestion,
    ))
    return result


def create_error_result(
    validator_id: str,
    error_message: str,
    traceback: Optional[str] = None,
) -> ValidationResult:
    """Create an error result (code failure, not validation failure)."""
    return ValidationResult(
        validator_id=validator_id,
        state=ValidatorState.ERROR,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        error_message=error_message,
        error_traceback=traceback,
    )
