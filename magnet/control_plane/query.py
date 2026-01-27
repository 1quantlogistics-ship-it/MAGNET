"""
MAGNET Control Plane v1.1 — Query Mode (Two-Phase WAL)

Evidence-based queries for answering "why" questions.

Core Contract:
- All answers come from stored ExplainRecords
- No state mutation during queries
- No inference or reconstruction from memory
- Dual output: human narrative + machine schema
- Explicitly handles all record statuses (PENDING, COMMITTED, INCOMPLETE, ABORTED)

This is how engineers interrogate the system's decisions.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

from magnet.control_plane.explain import (
    ExplainRecord,
    ExplainRecordStore,
    DurableExplainRecordStore,
    PathDelta,
    MetricDelta,
    RecordStatus,
    get_explain_store,
)

if TYPE_CHECKING:
    pass


# Type alias for store
AnyExplainStore = Union[ExplainRecordStore, DurableExplainRecordStore]


# =============================================================================
# DUAL OUTPUT
# =============================================================================

@dataclass
class DualOutput:
    """
    Response format for all query operations.
    
    Contains both human-readable narrative and machine-parseable schema.
    This ensures:
    - Engineers get plain-English explanations
    - UI/LLM gets structured data for rendering/reasoning
    """
    # Human-readable summary
    narrative: str
    
    # Machine-parseable data
    schema: Dict[str, Any]
    
    # Query metadata
    query_type: str
    query_params: Dict[str, Any]
    record_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative": self.narrative,
            "schema": self.schema,
            "query_type": self.query_type,
            "query_params": self.query_params,
            "record_count": self.record_count,
        }


# =============================================================================
# STATUS INDICATORS
# =============================================================================

def _get_status_indicator(record: ExplainRecord) -> str:
    """
    Get human-readable status indicator for a record.
    """
    if record.status == RecordStatus.PENDING:
        return "⏳ [PENDING: commit in progress]"
    elif record.status == RecordStatus.INCOMPLETE:
        return f"⚠️ [INCOMPLETE: {record.finalize_error or 'impact metrics unavailable'}]"
    elif record.status == RecordStatus.ABORTED:
        return f"❌ [ABORTED: {record.finalize_error or 'commit failed'}]"
    else:  # COMMITTED
        return ""


def _get_version_display(record: ExplainRecord) -> str:
    """
    Get version display string, handling None for ABORTED records.
    """
    if record.version_after is not None:
        return f"v{record.version_after}"
    else:
        return "(no version - commit did not complete)"


# =============================================================================
# NARRATIVE GENERATORS
# =============================================================================

def _generate_explain_narrative(record: ExplainRecord, path: str) -> str:
    """
    Generate human-readable explanation for a path change.
    
    Template-based, deterministic—no LLM involved.
    Handles all record statuses explicitly.
    """
    deltas = [d for d in record.path_deltas if d.path == path]
    if not deltas:
        return f"No changes to '{path}' found in {_get_version_display(record)}."
    
    delta = deltas[0]
    
    # Build the narrative
    parts = [
        f"'{path}' changed from {delta.old_value} to {delta.new_value}",
        f"in {_get_version_display(record)}",
    ]
    
    # Add source attribution
    if delta.source.value == "llm_guess":
        parts.append("(proposed by LLM)")
    elif delta.source.value == "clamped":
        parts.append("(clamped by validator)")
    elif delta.source.value == "user":
        parts.append("(from user input)")
    
    # Add validator context
    receipts = [r for r in record.validator_receipts if r.path == path]
    if receipts:
        receipt = receipts[0]
        if receipt.status.value == "clamped":
            parts.append(f"— {receipt.reason}")
        elif receipt.status.value == "rejected":
            parts.append(f"— rejected: {receipt.reason}")
    
    # Add intent context
    if record.raw_intent:
        parts.append(f'— triggered by: "{record.raw_intent}"')
    
    # Add approval type
    if record.approval_type.value == "implicit":
        parts.append("— auto-applied (undo available)")
    
    # Add status indicator for non-COMMITTED records
    status_indicator = _get_status_indicator(record)
    if status_indicator:
        parts.append(status_indicator)
    
    return " ".join(parts)


def _generate_history_narrative(records: List[ExplainRecord], path: str) -> str:
    """
    Generate timeline narrative for a path's history.
    """
    if not records:
        return f"No history found for '{path}'."
    
    lines = [f"History of '{path}' ({len(records)} changes):"]
    
    for record in records:
        deltas = [d for d in record.path_deltas if d.path == path]
        for delta in deltas:
            source_tag = f"[{delta.source.value}]"
            status_tag = f"[{record.status.value}]" if record.status != RecordStatus.COMMITTED else ""
            version_str = _get_version_display(record)
            lines.append(
                f"  {version_str}: {delta.old_value} → {delta.new_value} {source_tag} {status_tag}".strip()
            )
    
    return "\n".join(lines)


def _generate_impact_narrative(record: ExplainRecord) -> str:
    """
    Generate impact summary narrative.
    """
    version_str = _get_version_display(record)
    
    # Handle non-COMMITTED records
    if record.status == RecordStatus.PENDING:
        return f"Impact data pending for {version_str} — commit in progress."
    elif record.status == RecordStatus.ABORTED:
        return f"No impact data for {version_str} — commit was aborted: {record.finalize_error}"
    elif record.status == RecordStatus.INCOMPLETE:
        return f"Impact data unavailable for {version_str} — {record.finalize_error}"
    
    # COMMITTED record
    if not record.impact_delta:
        return f"No computed impact data for {version_str}."
    
    lines = [f"Impact of {version_str}:"]
    
    for metric in record.impact_delta:
        delta_str = f"{metric.delta:+.2f}" if metric.delta is not None else "N/A"
        lines.append(
            f"  {metric.metric_path}: {metric.before} → {metric.after} (Δ{delta_str})"
        )
        if metric.calculation_provenance:
            lines.append(
                f"    calculated by: {metric.calculation_provenance.method_id}"
            )
    
    return "\n".join(lines)


# =============================================================================
# QUERY FUNCTIONS
# =============================================================================

def query_explain(
    path: str,
    design_id: Optional[str] = None,
    store: Optional[AnyExplainStore] = None,
) -> DualOutput:
    """
    QUERY(explain, {path})
    
    Find the most recent change to a path and explain why it happened.
    
    Args:
        path: The state path to explain
        design_id: Design to search (uses latest if None)
        store: ExplainRecordStore (uses global if None)
    
    Returns:
        DualOutput with narrative and schema
    
    Evidence Source:
        ExplainRecord.path_deltas + validator_receipts
    """
    store = store or get_explain_store()
    
    # Get records for path
    records = []
    if design_id:
        records = store.get_history_for_path(design_id, path, limit=1)
    else:
        # Search all designs - use _by_version for DurableStore compatibility
        index = getattr(store, '_by_version', getattr(store, '_records', {}))
        for did in index.keys():
            found = store.get_history_for_path(did, path, limit=1)
            if found:
                records = found
                design_id = did
                break
    
    if not records:
        return DualOutput(
            narrative=f"No recorded changes to '{path}'.",
            schema={"path": path, "found": False, "record": None},
            query_type="explain",
            query_params={"path": path, "design_id": design_id},
            record_count=0,
        )
    
    record = records[0]
    deltas = [d for d in record.path_deltas if d.path == path]
    receipts = [r for r in record.validator_receipts if r.path == path]
    
    return DualOutput(
        narrative=_generate_explain_narrative(record, path),
        schema={
            "path": path,
            "found": True,
            "record_id": record.record_id,
            "design_id": record.design_id,
            "version": record.version_after,
            "status": record.status.value,
            "is_complete": record.status == RecordStatus.COMMITTED,
            "timestamp": record.timestamp.isoformat(),
            "raw_intent": record.raw_intent,
            "method": record.method,
            "approval_type": record.approval_type.value,
            "deltas": [d.to_dict() for d in deltas],
            "validator_receipts": [r.to_dict() for r in receipts],
            "finalize_error": record.finalize_error,
        },
        query_type="explain",
        query_params={"path": path, "design_id": design_id},
        record_count=1,
    )


def query_history(
    path: str,
    design_id: str,
    limit: int = 10,
    store: Optional[AnyExplainStore] = None,
) -> DualOutput:
    """
    QUERY(history, {path})
    
    Get the timeline of changes to a specific path.
    
    Args:
        path: The state path to query
        design_id: Design to search
        limit: Maximum number of records to return
        store: ExplainRecordStore (uses global if None)
    
    Returns:
        DualOutput with narrative and schema
    
    Evidence Source:
        All ExplainRecords where path appears in path_deltas
    """
    store = store or get_explain_store()
    
    records = store.get_history_for_path(design_id, path, limit=limit)
    
    if not records:
        return DualOutput(
            narrative=f"No history found for '{path}' in design '{design_id}'.",
            schema={
                "path": path,
                "design_id": design_id,
                "history": [],
            },
            query_type="history",
            query_params={"path": path, "design_id": design_id, "limit": limit},
            record_count=0,
        )
    
    # Build history entries
    history_entries = []
    for record in records:
        deltas = [d for d in record.path_deltas if d.path == path]
        for delta in deltas:
            history_entries.append({
                "version": record.version_after,
                "status": record.status.value,
                "is_complete": record.status == RecordStatus.COMMITTED,
                "timestamp": record.timestamp.isoformat(),
                "old_value": delta.old_value,
                "new_value": delta.new_value,
                "source": delta.source.value,
                "raw_intent": record.raw_intent,
                "method": record.method,
                "record_id": record.record_id,
                "finalize_error": record.finalize_error,
            })
    
    return DualOutput(
        narrative=_generate_history_narrative(records, path),
        schema={
            "path": path,
            "design_id": design_id,
            "history": history_entries,
        },
        query_type="history",
        query_params={"path": path, "design_id": design_id, "limit": limit},
        record_count=len(records),
    )


def query_impact(
    version: int,
    design_id: str,
    store: Optional[AnyExplainStore] = None,
) -> DualOutput:
    """
    QUERY(impact, {version})
    
    Get the engineering impact of a specific version.
    
    Args:
        version: The design_version to query
        design_id: Design to search
        store: ExplainRecordStore (uses global if None)
    
    Returns:
        DualOutput with narrative and schema
    
    Evidence Source:
        ExplainRecord.impact_delta
    """
    store = store or get_explain_store()
    
    record = store.get_by_version(design_id, version)
    
    if not record:
        return DualOutput(
            narrative=f"No record found for version {version} in design '{design_id}'.",
            schema={
                "version": version,
                "design_id": design_id,
                "found": False,
                "impact": [],
            },
            query_type="impact",
            query_params={"version": version, "design_id": design_id},
            record_count=0,
        )
    
    return DualOutput(
        narrative=_generate_impact_narrative(record),
        schema={
            "version": version,
            "design_id": design_id,
            "found": True,
            "record_id": record.record_id,
            "status": record.status.value,
            "is_complete": record.status == RecordStatus.COMMITTED,
            "timestamp": record.timestamp.isoformat(),
            "impact": [m.to_dict() for m in record.impact_delta],
            "path_deltas": [d.to_dict() for d in record.path_deltas],
            "finalize_error": record.finalize_error,
        },
        query_type="impact",
        query_params={"version": version, "design_id": design_id},
        record_count=1,
    )


def query_latest(
    design_id: str,
    store: Optional[AnyExplainStore] = None,
) -> DualOutput:
    """
    Get the latest ExplainRecord for a design.
    
    Useful for "what just happened?" queries.
    """
    store = store or get_explain_store()
    
    record = store.get_latest(design_id)
    
    if not record:
        return DualOutput(
            narrative=f"No records found for design '{design_id}'.",
            schema={
                "design_id": design_id,
                "found": False,
                "record": None,
            },
            query_type="latest",
            query_params={"design_id": design_id},
            record_count=0,
        )
    
    version_str = _get_version_display(record)
    status_indicator = _get_status_indicator(record)
    narrative = f"Latest change ({version_str}): {record.raw_intent}"
    if status_indicator:
        narrative += f" {status_indicator}"
    
    return DualOutput(
        narrative=narrative,
        schema={
            "design_id": design_id,
            "found": True,
            "record": record.to_dict(),
        },
        query_type="latest",
        query_params={"design_id": design_id},
        record_count=1,
    )


def query_pending(
    design_id: Optional[str] = None,
    store: Optional[AnyExplainStore] = None,
) -> DualOutput:
    """
    Get all PENDING records (useful for debugging/monitoring).
    
    Args:
        design_id: Optional filter by design
        store: ExplainRecordStore (uses global if None)
    
    Returns:
        DualOutput with list of pending records
    """
    store = store or get_explain_store()
    
    # Get pending records
    pending_dict = getattr(store, '_pending', {})
    pending_records = list(pending_dict.values())
    
    if design_id:
        pending_records = [r for r in pending_records if r.design_id == design_id]
    
    if not pending_records:
        return DualOutput(
            narrative="No pending records found.",
            schema={
                "design_id": design_id,
                "pending_count": 0,
                "records": [],
            },
            query_type="pending",
            query_params={"design_id": design_id},
            record_count=0,
        )
    
    return DualOutput(
        narrative=f"Found {len(pending_records)} pending record(s).",
        schema={
            "design_id": design_id,
            "pending_count": len(pending_records),
            "records": [r.to_dict() for r in pending_records],
        },
        query_type="pending",
        query_params={"design_id": design_id},
        record_count=len(pending_records),
    )
