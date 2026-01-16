"""
MAGNET Control Plane v1.1 — ExplainRecord Schema (WAL-Style)

Two-phase audit records for every committed design change.

Core Contract:
- PENDING record written BEFORE commit attempt
- COMMITTED/INCOMPLETE/ABORTED written AFTER commit outcome
- Records are append-only, "last write wins per record_id"
- Every design_version has at least a receipt stub

Status Semantics:
- PENDING: Written before commit, outcome unknown
- COMMITTED: Commit succeeded, finalization succeeded
- INCOMPLETE: Commit succeeded, finalization failed (partial truth)
- ABORTED: Commit failed, state was rolled back (no version created)

This is the foundation that prevents the system from "lying backward."
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set
import uuid
import json
import copy
import logging
import os

logger = logging.getLogger("control_plane.explain")


# =============================================================================
# RECORD STATUS (Two-Phase WAL)
# =============================================================================

class RecordStatus(str, Enum):
    """
    Status of an ExplainRecord in the two-phase WAL flow.
    
    State machine:
        PENDING → COMMITTED (success)
        PENDING → INCOMPLETE (commit ok, finalize failed)
        PENDING → ABORTED (commit failed)
    """
    PENDING = "pending"         # Written before commit attempt
    COMMITTED = "committed"     # Commit + finalize both succeeded
    INCOMPLETE = "incomplete"   # Commit succeeded, finalize failed
    ABORTED = "aborted"         # Commit failed, state rolled back


# =============================================================================
# PROVENANCE TYPES
# =============================================================================

class ChangeSource(str, Enum):
    """
    Source of a parameter change.
    
    Tracks who/what initiated the change for full attribution.
    """
    USER = "user"               # Direct user input (deterministic parse)
    LLM_GUESS = "llm_guess"     # LLM-proposed value
    CLAMPED = "clamped"         # Validator clamped to bounds
    SYSTEM = "system"           # System-initiated (e.g., initialization)


class ApprovalType(str, Enum):
    """
    How the change was approved.
    
    Critical for distinguishing deliberate vs auto-applied changes.
    """
    EXPLICIT = "explicit"       # User clicked "Apply"
    IMPLICIT = "implicit"       # Auto-apply was enabled


class ValidatorStatus(str, Enum):
    """
    Outcome of validation for a single action.
    """
    PASSED = "passed"           # Accepted without modification
    CLAMPED = "clamped"         # Value was adjusted to bounds
    REJECTED = "rejected"       # Action was rejected


# =============================================================================
# PATH DELTA
# =============================================================================

@dataclass(frozen=True)
class PathDelta:
    """
    Record of a single parameter change.
    
    Immutable to ensure audit integrity.
    """
    path: str
    old_value: Any
    new_value: Any
    source: ChangeSource
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "old_value": self._serialize(self.old_value),
            "new_value": self._serialize(self.new_value),
            "source": self.source.value,
        }
    
    @staticmethod
    def _serialize(value: Any) -> Any:
        """Serialize value for JSON storage."""
        if hasattr(value, "to_dict"):
            return value.to_dict()
        elif isinstance(value, (list, dict)):
            return copy.deepcopy(value)
        return value
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PathDelta":
        return cls(
            path=data["path"],
            old_value=data["old_value"],
            new_value=data["new_value"],
            source=ChangeSource(data["source"]),
        )


# =============================================================================
# VALIDATOR RECEIPT
# =============================================================================

@dataclass(frozen=True)
class ValidatorReceipt:
    """
    Record of validator outcome for a single action.
    
    This is the "receipt" proving what the validator did.
    """
    validator_id: str
    path: str
    status: ValidatorStatus
    original_value: Any
    final_value: Any
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "path": self.path,
            "status": self.status.value,
            "original_value": self.original_value,
            "final_value": self.final_value,
            "reason": self.reason,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidatorReceipt":
        return cls(
            validator_id=data["validator_id"],
            path=data["path"],
            status=ValidatorStatus(data["status"]),
            original_value=data["original_value"],
            final_value=data["final_value"],
            reason=data["reason"],
        )


# =============================================================================
# METRIC DELTA (with Calculation Provenance)
# =============================================================================

@dataclass(frozen=True)
class CalculationProvenance:
    """
    Provenance for a computed metric.
    
    Answers: "How was this number calculated?"
    """
    method_id: str              # e.g., "savitsky_v2", "simpson_integration"
    geometry_hash: str          # SHA256 of geometry used
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "method_id": self.method_id,
            "geometry_hash": self.geometry_hash,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalculationProvenance":
        return cls(
            method_id=data["method_id"],
            geometry_hash=data["geometry_hash"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(timezone.utc),
        )


@dataclass(frozen=True)
class MetricDelta:
    """
    Change in a computed metric with full provenance.
    
    This answers both "what changed" AND "how do we know."
    """
    metric_path: str
    before: Optional[float]
    after: Optional[float]
    delta: Optional[float]
    calculation_provenance: Optional[CalculationProvenance] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_path": self.metric_path,
            "before": self.before,
            "after": self.after,
            "delta": self.delta,
            "calculation_provenance": self.calculation_provenance.to_dict() if self.calculation_provenance else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MetricDelta":
        prov = data.get("calculation_provenance")
        return cls(
            metric_path=data["metric_path"],
            before=data.get("before"),
            after=data.get("after"),
            delta=data.get("delta"),
            calculation_provenance=CalculationProvenance.from_dict(prov) if prov else None,
        )


# =============================================================================
# EXPLAIN RECORD (Two-Phase WAL)
# =============================================================================

@dataclass(frozen=True)
class ExplainRecord:
    """
    Immutable audit record for a design change attempt.
    
    Two-Phase WAL:
    - Phase 1: Written as PENDING before commit
    - Phase 2: Updated to COMMITTED/INCOMPLETE/ABORTED after outcome
    
    Invariants:
    - record_id is globally unique
    - Append-only (new records overwrite old with same record_id)
    - Contains evidence for "why" questions even if incomplete
    """
    # Identity
    record_id: str
    design_id: str
    
    # Version transition (version_after is None for PENDING/ABORTED)
    version_before: int
    version_after: Optional[int]
    
    # Timestamp
    timestamp: datetime
    
    # Two-phase status
    status: RecordStatus
    
    # What changed (known at PENDING time)
    path_deltas: tuple  # Tuple[PathDelta, ...] for immutability
    
    # Provenance (known at PENDING time)
    method: Literal["deterministic", "llm_guess"]
    raw_intent: str     # Original user input
    plan_id: str        # ActionPlan ID
    approval_type: ApprovalType
    
    # Validation evidence (may be partial for PENDING)
    validator_receipts: tuple  # Tuple[ValidatorReceipt, ...]
    
    # Impact (only populated for COMMITTED, empty otherwise)
    impact_delta: tuple  # Tuple[MetricDelta, ...]
    
    # Finalization metadata
    finalized_at: Optional[datetime] = None
    finalize_error: Optional[str] = None
    
    def __post_init__(self):
        """Ensure tuples for immutability."""
        if isinstance(self.path_deltas, list):
            object.__setattr__(self, 'path_deltas', tuple(self.path_deltas))
        if isinstance(self.validator_receipts, list):
            object.__setattr__(self, 'validator_receipts', tuple(self.validator_receipts))
        if isinstance(self.impact_delta, list):
            object.__setattr__(self, 'impact_delta', tuple(self.impact_delta))
    
    @property
    def is_terminal(self) -> bool:
        """True if this record is in a terminal state."""
        return self.status in (RecordStatus.COMMITTED, RecordStatus.INCOMPLETE, RecordStatus.ABORTED)
    
    @property
    def has_version(self) -> bool:
        """True if this record has a committed version."""
        return self.version_after is not None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "design_id": self.design_id,
            "version_before": self.version_before,
            "version_after": self.version_after,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "path_deltas": [d.to_dict() for d in self.path_deltas],
            "method": self.method,
            "raw_intent": self.raw_intent,
            "plan_id": self.plan_id,
            "approval_type": self.approval_type.value,
            "validator_receipts": [r.to_dict() for r in self.validator_receipts],
            "impact_delta": [m.to_dict() for m in self.impact_delta],
            "finalized_at": self.finalized_at.isoformat() if self.finalized_at else None,
            "finalize_error": self.finalize_error,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExplainRecord":
        return cls(
            record_id=data["record_id"],
            design_id=data["design_id"],
            version_before=data["version_before"],
            version_after=data.get("version_after"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            status=RecordStatus(data.get("status", "committed")),  # Default for legacy
            path_deltas=[PathDelta.from_dict(d) for d in data.get("path_deltas", [])],
            method=data["method"],
            raw_intent=data["raw_intent"],
            plan_id=data["plan_id"],
            approval_type=ApprovalType(data["approval_type"]),
            validator_receipts=[ValidatorReceipt.from_dict(r) for r in data.get("validator_receipts", [])],
            impact_delta=[MetricDelta.from_dict(m) for m in data.get("impact_delta", [])],
            finalized_at=datetime.fromisoformat(data["finalized_at"]) if data.get("finalized_at") else None,
            finalize_error=data.get("finalize_error"),
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ExplainRecord":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def get_deltas_for_path(self, path: str) -> List[PathDelta]:
        """Get all deltas for a specific path."""
        return [d for d in self.path_deltas if d.path == path]
    
    def get_receipts_for_path(self, path: str) -> List[ValidatorReceipt]:
        """Get all validator receipts for a specific path."""
        return [r for r in self.validator_receipts if r.path == path]


# =============================================================================
# FACTORY FUNCTIONS (Two-Phase)
# =============================================================================

def create_pending_record(
    design_id: str,
    version_before: int,
    path_deltas: List[PathDelta],
    method: Literal["deterministic", "llm_guess"],
    raw_intent: str,
    plan_id: str,
    approval_type: ApprovalType,
    validator_receipts: Optional[List[ValidatorReceipt]] = None,
) -> ExplainRecord:
    """
    Create a PENDING record before commit attempt.
    
    This captures intent and proposed changes BEFORE we know
    if the commit will succeed.
    """
    return ExplainRecord(
        record_id=f"explain_{uuid.uuid4().hex[:12]}",
        design_id=design_id,
        version_before=version_before,
        version_after=None,  # Unknown until commit
        timestamp=datetime.now(timezone.utc),
        status=RecordStatus.PENDING,
        path_deltas=path_deltas,
        method=method,
        raw_intent=raw_intent,
        plan_id=plan_id,
        approval_type=approval_type,
        validator_receipts=validator_receipts or [],
        impact_delta=[],  # Empty until finalized
        finalized_at=None,
        finalize_error=None,
    )


def finalize_record(
    pending: ExplainRecord,
    version_after: int,
    validator_receipts: List[ValidatorReceipt],
    impact_delta: List[MetricDelta],
) -> ExplainRecord:
    """
    Finalize a PENDING record after successful commit.
    
    Returns a new COMMITTED record with full impact data.
    """
    return ExplainRecord(
        record_id=pending.record_id,
        design_id=pending.design_id,
        version_before=pending.version_before,
        version_after=version_after,
        timestamp=pending.timestamp,
        status=RecordStatus.COMMITTED,
        path_deltas=pending.path_deltas,
        method=pending.method,
        raw_intent=pending.raw_intent,
        plan_id=pending.plan_id,
        approval_type=pending.approval_type,
        validator_receipts=validator_receipts,
        impact_delta=impact_delta,
        finalized_at=datetime.now(timezone.utc),
        finalize_error=None,
    )


def mark_incomplete(
    pending: ExplainRecord,
    version_after: int,
    error: str,
) -> ExplainRecord:
    """
    Mark a record as INCOMPLETE when commit succeeded but finalize failed.
    
    The version_after is known (commit happened), but impact metrics unavailable.
    """
    return ExplainRecord(
        record_id=pending.record_id,
        design_id=pending.design_id,
        version_before=pending.version_before,
        version_after=version_after,  # Commit DID happen
        timestamp=pending.timestamp,
        status=RecordStatus.INCOMPLETE,
        path_deltas=pending.path_deltas,
        method=pending.method,
        raw_intent=pending.raw_intent,
        plan_id=pending.plan_id,
        approval_type=pending.approval_type,
        validator_receipts=pending.validator_receipts,
        impact_delta=[],  # Not available
        finalized_at=datetime.now(timezone.utc),
        finalize_error=error,
    )


def mark_aborted(
    pending: ExplainRecord,
    error: str,
) -> ExplainRecord:
    """
    Mark a record as ABORTED when commit failed (state rolled back).
    
    No version_after because no commit happened.
    """
    return ExplainRecord(
        record_id=pending.record_id,
        design_id=pending.design_id,
        version_before=pending.version_before,
        version_after=None,  # Commit did NOT happen
        timestamp=pending.timestamp,
        status=RecordStatus.ABORTED,
        path_deltas=pending.path_deltas,
        method=pending.method,
        raw_intent=pending.raw_intent,
        plan_id=pending.plan_id,
        approval_type=pending.approval_type,
        validator_receipts=pending.validator_receipts,
        impact_delta=[],
        finalized_at=datetime.now(timezone.utc),
        finalize_error=error,
    )


# Legacy factory for backwards compatibility
def create_explain_record(
    design_id: str,
    version_before: int,
    version_after: int,
    path_deltas: List[PathDelta],
    method: Literal["deterministic", "llm_guess"],
    raw_intent: str,
    plan_id: str,
    approval_type: ApprovalType,
    validator_receipts: List[ValidatorReceipt],
    impact_delta: List[MetricDelta],
) -> ExplainRecord:
    """
    Legacy factory function to create a COMMITTED ExplainRecord directly.
    
    Use create_pending_record + finalize_record for WAL flow.
    """
    return ExplainRecord(
        record_id=f"explain_{uuid.uuid4().hex[:12]}",
        design_id=design_id,
        version_before=version_before,
        version_after=version_after,
        timestamp=datetime.now(timezone.utc),
        status=RecordStatus.COMMITTED,
        path_deltas=path_deltas,
        method=method,
        raw_intent=raw_intent,
        plan_id=plan_id,
        approval_type=approval_type,
        validator_receipts=validator_receipts,
        impact_delta=impact_delta,
        finalized_at=datetime.now(timezone.utc),
        finalize_error=None,
    )


# =============================================================================
# DURABLE EXPLAIN RECORD STORE (JSONL)
# =============================================================================

class DurableExplainRecordStore:
    """
    Append-only JSONL storage for ExplainRecords.
    
    Disk is source of truth; in-memory index for fast queries.
    
    Key Invariants:
    - "Last write wins per record_id" for index construction
    - PENDING records tracked separately until terminal
    - COMMITTED records indexed by version_after
    
    Directory Structure:
        storage/designs/{design_id}/explain_records.jsonl
    """
    
    def __init__(self, storage_root: Optional[Path] = None):
        """
        Initialize the store.
        
        Args:
            storage_root: Root directory for storage (default: ./storage)
        """
        self._storage_root = storage_root or Path("storage")
        
        # In-memory indices (built from disk on load)
        # design_id -> version_after -> ExplainRecord (only COMMITTED/INCOMPLETE)
        self._by_version: Dict[str, Dict[int, ExplainRecord]] = {}
        # record_id -> ExplainRecord (all terminal records)
        self._by_id: Dict[str, ExplainRecord] = {}
        # record_id -> ExplainRecord (PENDING only, waiting for outcome)
        self._pending: Dict[str, ExplainRecord] = {}
        # Loaded designs (to avoid re-loading)
        self._loaded_designs: Set[str] = set()
    
    def _get_log_path(self, design_id: str) -> Path:
        """Get the JSONL log path for a design."""
        return self._storage_root / "designs" / design_id / "explain_records.jsonl"
    
    def _append_to_log(self, record: ExplainRecord) -> None:
        """
        Append a record to the JSONL log.
        
        This is the only write operation. All records are appended.
        """
        log_path = self._get_log_path(record.design_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_path, 'a') as f:
            f.write(record.to_json() + '\n')
    
    def _index_record(self, record: ExplainRecord) -> None:
        """
        Index a record in memory.
        
        "Last write wins per record_id" - newer records overwrite older.
        """
        design_id = record.design_id
        
        # Always update by_id index
        self._by_id[record.record_id] = record
        
        # Handle by status
        if record.status == RecordStatus.PENDING:
            self._pending[record.record_id] = record
        else:
            # Terminal state - remove from pending if present
            self._pending.pop(record.record_id, None)
            
            # Index by version if we have one
            if record.version_after is not None:
                if design_id not in self._by_version:
                    self._by_version[design_id] = {}
                self._by_version[design_id][record.version_after] = record
    
    def load_design(self, design_id: str) -> None:
        """
        Load all records for a design from disk.
        
        Uses "last write wins per record_id" to handle
        the append-only log with multiple writes per record.
        """
        if design_id in self._loaded_designs:
            return
        
        log_path = self._get_log_path(design_id)
        if not log_path.exists():
            self._loaded_designs.add(design_id)
            return
        
        # Temporary dict to collect "last write wins"
        records_by_id: Dict[str, ExplainRecord] = {}
        
        with open(log_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = ExplainRecord.from_json(line)
                    # Last write wins
                    records_by_id[record.record_id] = record
                except Exception as e:
                    logger.warning(f"Failed to parse line {line_num} in {log_path}: {e}")
        
        # Index all records (final state per record_id)
        for record in records_by_id.values():
            self._index_record(record)
        
        self._loaded_designs.add(design_id)
        logger.info(f"Loaded {len(records_by_id)} explain records for design {design_id}")
    
    # =========================================================================
    # TWO-PHASE WRITE OPERATIONS
    # =========================================================================
    
    def store_pending(self, record: ExplainRecord) -> None:
        """
        Store a PENDING record before commit attempt.
        
        This MUST succeed before commit is attempted.
        """
        if record.status != RecordStatus.PENDING:
            raise ValueError(f"Expected PENDING record, got {record.status}")
        
        self._append_to_log(record)
        self._index_record(record)
        logger.debug(f"Stored PENDING record {record.record_id}")
    
    def finalize(self, record_id: str, finalized: ExplainRecord) -> None:
        """
        Finalize a PENDING record to COMMITTED.
        
        Called after successful commit and impact calculation.
        """
        if finalized.status != RecordStatus.COMMITTED:
            raise ValueError(f"Expected COMMITTED record, got {finalized.status}")
        if finalized.record_id != record_id:
            raise ValueError(f"Record ID mismatch: {record_id} vs {finalized.record_id}")
        
        self._append_to_log(finalized)
        self._index_record(finalized)
        logger.debug(f"Finalized record {record_id} to COMMITTED")
    
    def store_incomplete(self, record_id: str, incomplete: ExplainRecord) -> None:
        """
        Mark a record as INCOMPLETE (commit succeeded, finalize failed).
        """
        if incomplete.status != RecordStatus.INCOMPLETE:
            raise ValueError(f"Expected INCOMPLETE record, got {incomplete.status}")
        
        self._append_to_log(incomplete)
        self._index_record(incomplete)
        logger.warning(f"Marked record {record_id} as INCOMPLETE: {incomplete.finalize_error}")
    
    def store_aborted(self, record_id: str, aborted: ExplainRecord) -> None:
        """
        Mark a record as ABORTED (commit failed, state rolled back).
        """
        if aborted.status != RecordStatus.ABORTED:
            raise ValueError(f"Expected ABORTED record, got {aborted.status}")
        
        self._append_to_log(aborted)
        self._index_record(aborted)
        logger.warning(f"Marked record {record_id} as ABORTED: {aborted.finalize_error}")
    
    # Legacy store method for backwards compatibility
    def store(self, record: ExplainRecord) -> None:
        """
        Store a record directly (legacy API).
        
        For WAL flow, use store_pending() + finalize().
        """
        self._append_to_log(record)
        self._index_record(record)
    
    # =========================================================================
    # RECONCILIATION
    # =========================================================================
    
    def reconcile_pending(
        self,
        design_id: str,
        current_version: int,
        last_explain_record_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Reconcile orphaned PENDING records on startup.
        
        Uses commit correlation token (last_explain_record_id) for exact matching.
        
        Args:
            design_id: Design to reconcile
            current_version: Current design_version in state
            last_explain_record_id: Correlation token from state metadata
        
        Returns:
            Dict of record_id -> final status ("incomplete" or "aborted")
        """
        results: Dict[str, str] = {}
        
        # Find PENDING records for this design
        pending_for_design = [
            r for r in self._pending.values()
            if r.design_id == design_id
        ]
        
        for pending in pending_for_design:
            if last_explain_record_id and pending.record_id == last_explain_record_id:
                # This PENDING record's commit succeeded (correlation match)
                # Mark as INCOMPLETE since finalize didn't complete
                incomplete = mark_incomplete(
                    pending,
                    version_after=current_version,
                    error="Orphaned: commit succeeded but finalize did not complete (recovered on startup)",
                )
                self.store_incomplete(pending.record_id, incomplete)
                results[pending.record_id] = "incomplete"
                logger.info(f"Reconciled {pending.record_id} as INCOMPLETE (correlation match)")
            else:
                # No correlation match - commit likely failed
                aborted = mark_aborted(
                    pending,
                    error="Orphaned: no commit correlation found (assumed failed)",
                )
                self.store_aborted(pending.record_id, aborted)
                results[pending.record_id] = "aborted"
                logger.info(f"Reconciled {pending.record_id} as ABORTED (no correlation)")
        
        return results
    
    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================
    
    def get_by_version(self, design_id: str, version: int) -> Optional[ExplainRecord]:
        """Get record for a specific design version."""
        self.load_design(design_id)
        return self._by_version.get(design_id, {}).get(version)
    
    def get_by_id(self, record_id: str) -> Optional[ExplainRecord]:
        """Get record by its unique ID."""
        return self._by_id.get(record_id)
    
    def get_pending(self, record_id: str) -> Optional[ExplainRecord]:
        """Get a PENDING record by ID."""
        return self._pending.get(record_id)
    
    def get_history_for_path(
        self,
        design_id: str,
        path: str,
        limit: int = 10,
    ) -> List[ExplainRecord]:
        """
        Get records where a specific path was modified.
        
        Returns most recent first. Only includes terminal records.
        """
        self.load_design(design_id)
        design_records = self._by_version.get(design_id, {})
        matching = []
        
        for version in sorted(design_records.keys(), reverse=True):
            record = design_records[version]
            if any(d.path == path for d in record.path_deltas):
                matching.append(record)
                if len(matching) >= limit:
                    break
        
        return matching
    
    def get_latest(self, design_id: str) -> Optional[ExplainRecord]:
        """Get the most recent record for a design."""
        self.load_design(design_id)
        design_records = self._by_version.get(design_id, {})
        if not design_records:
            return None
        
        latest_version = max(design_records.keys())
        return design_records[latest_version]
    
    def get_all_for_design(self, design_id: str) -> List[ExplainRecord]:
        """Get all terminal records for a design, sorted by version."""
        self.load_design(design_id)
        design_records = self._by_version.get(design_id, {})
        return [
            design_records[v]
            for v in sorted(design_records.keys())
        ]
    
    def count(self, design_id: Optional[str] = None) -> int:
        """Count terminal records, optionally filtered by design."""
        if design_id:
            self.load_design(design_id)
            return len(self._by_version.get(design_id, {}))
        return len(self._by_id)
    
    def count_pending(self) -> int:
        """Count PENDING records across all designs."""
        return len(self._pending)


# =============================================================================
# IN-MEMORY STORE (for testing/backwards compatibility)
# =============================================================================

class ExplainRecordStore:
    """
    In-memory store for ExplainRecords.
    
    For production, use DurableExplainRecordStore.
    This exists for backwards compatibility and testing.
    """
    
    def __init__(self):
        self._records: Dict[str, Dict[int, ExplainRecord]] = {}
        self._by_id: Dict[str, ExplainRecord] = {}
        self._pending: Dict[str, ExplainRecord] = {}
    
    def store_pending(self, record: ExplainRecord) -> None:
        """Store a PENDING record."""
        self._pending[record.record_id] = record
        self._by_id[record.record_id] = record
    
    def finalize(self, record_id: str, finalized: ExplainRecord) -> None:
        """Finalize a PENDING record to COMMITTED."""
        self._pending.pop(record_id, None)
        self._index_committed(finalized)
    
    def store_incomplete(self, record_id: str, incomplete: ExplainRecord) -> None:
        """Mark a record as INCOMPLETE."""
        self._pending.pop(record_id, None)
        self._index_committed(incomplete)
    
    def store_aborted(self, record_id: str, aborted: ExplainRecord) -> None:
        """Mark a record as ABORTED."""
        self._pending.pop(record_id, None)
        self._by_id[record_id] = aborted
    
    def _index_committed(self, record: ExplainRecord) -> None:
        """Index a committed/incomplete record."""
        design_id = record.design_id
        if design_id not in self._records:
            self._records[design_id] = {}
        if record.version_after is not None:
            self._records[design_id][record.version_after] = record
        self._by_id[record.record_id] = record
    
    # Legacy store method
    def store(self, record: ExplainRecord) -> None:
        """Store a record directly (legacy API)."""
        if record.status == RecordStatus.PENDING:
            self.store_pending(record)
        else:
            self._index_committed(record)
    
    def get_by_version(self, design_id: str, version: int) -> Optional[ExplainRecord]:
        return self._records.get(design_id, {}).get(version)
    
    def get_by_id(self, record_id: str) -> Optional[ExplainRecord]:
        return self._by_id.get(record_id)
    
    def get_pending(self, record_id: str) -> Optional[ExplainRecord]:
        return self._pending.get(record_id)
    
    def get_history_for_path(
        self,
        design_id: str,
        path: str,
        limit: int = 10,
    ) -> List[ExplainRecord]:
        design_records = self._records.get(design_id, {})
        matching = []
        for version in sorted(design_records.keys(), reverse=True):
            record = design_records[version]
            if any(d.path == path for d in record.path_deltas):
                matching.append(record)
                if len(matching) >= limit:
                    break
        return matching
    
    def get_latest(self, design_id: str) -> Optional[ExplainRecord]:
        design_records = self._records.get(design_id, {})
        if not design_records:
            return None
        latest_version = max(design_records.keys())
        return design_records[latest_version]
    
    def get_all_for_design(self, design_id: str) -> List[ExplainRecord]:
        design_records = self._records.get(design_id, {})
        return [design_records[v] for v in sorted(design_records.keys())]
    
    def count(self, design_id: Optional[str] = None) -> int:
        if design_id:
            return len(self._records.get(design_id, {}))
        return len(self._by_id)


# =============================================================================
# GLOBAL STORE INSTANCE
# =============================================================================

_global_store: Optional[DurableExplainRecordStore] = None


def get_explain_store() -> DurableExplainRecordStore:
    """
    Get the global ExplainRecordStore instance.
    
    Creates a DurableExplainRecordStore if one doesn't exist.
    """
    global _global_store
    if _global_store is None:
        _global_store = DurableExplainRecordStore()
    return _global_store


def reset_explain_store(storage_root: Optional[Path] = None) -> None:
    """
    Reset the global store (for testing).
    """
    global _global_store
    _global_store = DurableExplainRecordStore(storage_root)


def set_explain_store(store: DurableExplainRecordStore) -> None:
    """
    Set the global store instance (for testing with custom store).
    """
    global _global_store
    _global_store = store
