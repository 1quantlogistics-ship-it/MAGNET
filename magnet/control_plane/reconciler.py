"""
MAGNET Control Plane v1.1 — Startup Reconciliation

Handles orphaned PENDING records on application startup.

This module ensures that even after a crash mid-commit, the system
maintains audit integrity by:
1. Loading all ExplainRecords from disk
2. Finding any PENDING records
3. Using the commit correlation token to determine outcome
4. Marking records as INCOMPLETE or ABORTED accordingly

This is the "crash recovery" component of the Two-Phase WAL.
"""

from __future__ import annotations
from typing import Dict, List, Optional, TYPE_CHECKING
import logging

from magnet.control_plane.explain import (
    get_explain_store,
    DurableExplainRecordStore,
)

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

logger = logging.getLogger("control_plane.reconciler")


def reconcile_design_on_load(
    design_id: str,
    state_manager: "StateManager",
    store: Optional[DurableExplainRecordStore] = None,
) -> Dict[str, str]:
    """
    Reconcile orphaned PENDING records when a design is loaded.
    
    This should be called:
    - When a design is loaded from disk
    - When the application starts up
    - When recovering from a crash
    
    Args:
        design_id: The design to reconcile
        state_manager: StateManager with the current state
        store: ExplainRecordStore (uses global if None)
    
    Returns:
        Dict of record_id -> final status ("incomplete" or "aborted")
    """
    store = store or get_explain_store()
    
    # Ensure the design's records are loaded
    store.load_design(design_id)
    
    # Get the current design version and correlation token
    current_version = state_manager.design_version
    last_explain_record_id = state_manager.get_last_explain_record_id()
    
    # Run reconciliation
    results = store.reconcile_pending(
        design_id=design_id,
        current_version=current_version,
        last_explain_record_id=last_explain_record_id,
    )
    
    if results:
        logger.info(
            f"Reconciled {len(results)} orphaned records for design {design_id}: "
            f"{results}"
        )
    
    return results


def reconcile_all_designs(
    state_managers: Dict[str, "StateManager"],
    store: Optional[DurableExplainRecordStore] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Reconcile all known designs.
    
    Args:
        state_managers: Dict of design_id -> StateManager
        store: ExplainRecordStore (uses global if None)
    
    Returns:
        Dict of design_id -> {record_id -> final status}
    """
    store = store or get_explain_store()
    all_results: Dict[str, Dict[str, str]] = {}
    
    for design_id, state_manager in state_managers.items():
        results = reconcile_design_on_load(design_id, state_manager, store)
        if results:
            all_results[design_id] = results
    
    return all_results


def check_pending_records(
    store: Optional[DurableExplainRecordStore] = None,
) -> List[str]:
    """
    Check for any PENDING records across all designs.
    
    Useful for monitoring and debugging.
    
    Returns:
        List of record_ids that are still PENDING
    """
    store = store or get_explain_store()
    pending_dict = getattr(store, '_pending', {})
    return list(pending_dict.keys())

