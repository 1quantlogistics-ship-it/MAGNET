"""
§SKELETON:SpiralEndpoints

Spiral endpoints for design-scoped, persistent, single-authority design iteration.

These endpoints:
- Operate on DesignStore-backed StateManager (persisted)
- Are atomic (rollback on failure)
- Emit WS messages UI already understands
- Return structured metrics/deltas + design_version
"""
from __future__ import annotations

from datetime import datetime
import json
import uuid
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel
from fastapi import APIRouter, File, Form, HTTPException, UploadFile


class SpiralChatRequest(BaseModel):
    message: str
    constraints: Optional[List[str]] = None
    # Concurrency control (failure mode #1): optimistic locking
    expected_version: Optional[int] = None
    request_id: Optional[str] = None  # idempotency key (UI retries / double-click safety)
    min_confidence: float = 0.6
    force_apply: bool = False  # explicit user override when confidence is low
    # Spiral execution scope (failure mode #2): ensure downstream phases work
    run_critical_phases: bool = True
    critical_phases: Optional[List[str]] = None  # e.g. ["hull_form", "weight_stability", "structure"]
    # GLB readiness controls (shortcut #2)
    glb_timeout_ms: int = 2000
    glb_retry_limit: int = 5
    # §SKELETON:CheckpointPruning - Checkpoint management
    max_checkpoint_iterations: int = 50  # Prune checkpoints older than this
    clarification_response: Optional[Dict[str, Any]] = None  # Response to previous clarification


class SpiralChatResponse(BaseModel):
    success: bool
    design_id: str
    design_version_before: int
    design_version_after: int
    # Track iteration explicitly (not only via WebSocket) so UI can persist state across WS reconnect.
    spiral_iteration: int = 0
    status: str  # applied | proposal_low_confidence | needs_clarification | partial | failed
    feedback: str
    program_text: str = ""
    average_confidence: float = 0.0
    # Shortcut #1 fix: clarification must be first-class
    clarification_questions: List[Dict[str, Any]] = []
    clarification_request_id: Optional[str] = None
    metrics: Dict[str, float] = {}
    deltas: Dict[str, float] = {}
    invalidated_phases: List[str] = []
    failed_phases: List[str] = []  # failure mode #2: downstream phase failures
    glb_ready: bool = False
    glb_retry_after_ms: Optional[int] = None
    errors: List[str] = []
    requires_confirmation: bool = False
    # Path B: surface state-drift integrity warnings (do not hide drift).
    integrity_warnings: List[str] = []


class HumanApprovalToken(BaseModel):
    decision: str  # CONTINUE_DESPITE_WARNING | REVISE
    approved_by: str
    timestamp: str  # ISO8601
    rationale: str = ""
    acknowledged_risks: List[str] = []


def _maybe_parse_json_program_from_message(message: str) -> Optional[Dict[str, Any]]:
    """
    Allow UIv2 to submit JSON programs directly (no LLM required).

    Supported inputs:
    - Raw JSON object starting with '{'
    - 'json: { ... }'
    - fenced blocks:
        ```json
        { ... }
        ```
    """
    s = (message or "").strip()
    if not s:
        return None

    lowered = s.lower()
    if lowered.startswith("json:"):
        s = s[5:].strip()

    # Strip ```json ... ``` fences (UI can paste multiline)
    if s.startswith("```"):
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        s = "\n".join(lines).strip()

    if not s.startswith("{"):
        return None

    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def _program_json_to_program_text(program_json: Dict[str, Any]) -> str:
    """
    Convert program JSON to DSL text so we can reuse the existing execution + checkpoint pipeline.

    This mirrors `magnet.kernel.program_executor.execute_program_json()` but also returns
    the rendered text for checkpointing and UI display.
    """
    ops = program_json.get("operations", [])
    if not isinstance(ops, list):
        return ""

    def _dumps(v: Any) -> str:
        return json.dumps(v, separators=(",", ":"), ensure_ascii=False)

    lines: List[str] = []
    for op in ops:
        if not isinstance(op, dict):
            continue
        op_type = str(op.get("op", "")).upper().strip()
        if op_type == "CREATE":
            rtype = op.get("type", "")
            rid = op.get("id", "")
            params = op.get("params", {})
            lines.append(f"CREATE {rtype} {rid} {_dumps(params)}")
        elif op_type == "UPDATE":
            rid = op.get("id", "")
            params = op.get("params", {})
            lines.append(f"UPDATE {rid} {_dumps(params)}")
        elif op_type == "DELETE":
            rid = op.get("id", "")
            lines.append(f"DELETE {rid}")
        elif op_type == "SET":
            path = op.get("path", "")
            value = op.get("value")
            lines.append(f"SET {path} = {_dumps(value)}")
        elif op_type == "LOFT":
            sid = op.get("id", "")
            sections = op.get("sections", [])
            if isinstance(sections, list):
                lines.append(f"LOFT {sid} FROM [{', '.join(map(str, sections))}]")
        elif op_type == "MIRROR":
            source = op.get("source", "")
            target = op.get("target", "")
            lines.append(f"MIRROR {source} AS {target}")
        elif op_type == "CONSTRAIN":
            path = op.get("path", "")
            operator = op.get("operator", ">=")
            value = op.get("value", 0)
            lines.append(f"CONSTRAIN {path} {operator} {value}")

    return "\n".join(lines).strip()


class SpiralSketchResponse(BaseModel):
    success: bool
    design_id: str
    design_version_before: int
    design_version_after: int
    interpretation: Optional[Dict[str, Any]] = None
    # Failure mode #3: explicit extracted values for human confirmation
    extracted_values: Dict[str, Any] = {}
    requires_confirmation: bool = True
    intent_string: str = ""
    program_text: str = ""
    average_confidence: float = 0.0
    status: str
    feedback: str
    clarification_questions: List[Dict[str, Any]] = []
    metrics: Dict[str, float] = {}
    deltas: Dict[str, float] = {}
    glb_ready: bool = False
    glb_retry_after_ms: Optional[int] = None
    errors: List[str] = []
    spiral_iteration: int = 0


class IntegrityRepairRequest(BaseModel):
    preview_only: bool = True
    # optimistic locking
    expected_version: Optional[int] = None


class IntegrityRepairResponse(BaseModel):
    success: bool
    design_id: str
    design_version_before: int
    design_version_after: int
    applied: bool
    actions: List[Dict[str, Any]] = []
    warnings: List[str] = []
    errors: List[str] = []


def create_spiral_router(
    get_state_manager: Callable[[str], Any],
    ws_manager: Any,
) -> APIRouter:
    """
    Create the spiral endpoints router.
    Gated by MAGNET_SPIRAL_ENABLED environment variable.
    """
    import os
    
    # §SKELETON:SpiralEnabledFlag
    spiral_enabled = os.environ.get("MAGNET_SPIRAL_ENABLED", "true").lower() == "true"
    if not spiral_enabled:
        # Return empty router - endpoints won't be registered
        return APIRouter(tags=["Design Spiral (disabled)"])
    
    router = APIRouter(tags=["Design Spiral"])

    @router.post("/api/v1/designs/{design_id}/approve_decision")
    async def approve_decision(design_id: str, token: HumanApprovalToken) -> Dict[str, Any]:
        """
        Human Decision Point approval endpoint.

        Clears kernel.awaiting_human_decision and stores the approval token for auditability.
        """
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        design_version_before = sm.get("design_version", 0) if hasattr(sm, "get") else 0

        try:
            txn = sm.begin_transaction()
            sm.set("kernel.awaiting_human_decision", False, source="human_decision")
            sm.set("kernel.human_decision_token", token.model_dump(), source="human_decision")
            # Keep request payload for traceability, but mark it resolved.
            sm.set("kernel.human_decision_resolved_at", datetime.utcnow().isoformat(), source="human_decision")
            sm.commit()
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error": "apply_failed", "message": str(e)})

        # persist
        try:
            from magnet.deployment.design_store import DesignStore, VersionConflictError
            store = DesignStore(None)
            new_version = store.save(design_id, state_manager=sm, expected_version=int(design_version_before or 0))
            # Append turn record (append-only witness).
            store.append_turn_record(design_id, {
                "turn_id": f"turn_{uuid.uuid4().hex[:12]}",
                "phase": "human_decision",
                "trigger": "user_request",
                "design_version_before": int(design_version_before or 0),
                "design_version_after": int(new_version),
                "committed": True,
                "outputs_written": {
                    "kernel.awaiting_human_decision": getattr(sm, "compute_explain_ref", lambda p, design_version=None: None)("kernel.awaiting_human_decision", design_version=int(new_version)),
                    "kernel.human_decision_token": getattr(sm, "compute_explain_ref", lambda p, design_version=None: None)("kernel.human_decision_token", design_version=int(new_version)),
                    "kernel.human_decision_resolved_at": getattr(sm, "compute_explain_ref", lambda p, design_version=None: None)("kernel.human_decision_resolved_at", design_version=int(new_version)),
                },
            })
        except VersionConflictError as e:
            raise HTTPException(status_code=409, detail=e.to_dict())
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error": "persist_failed", "message": str(e)})

        design_version_after = sm.get("design_version", design_version_before) if hasattr(sm, "get") else design_version_before
        return {
            "success": True,
            "design_id": design_id,
            "design_version_before": int(design_version_before or 0),
            "design_version_after": int(design_version_after or design_version_before),
        }

    @router.post("/api/v1/designs/{design_id}/integrity/repair", response_model=IntegrityRepairResponse)
    async def repair_integrity(design_id: str, request: IntegrityRepairRequest) -> IntegrityRepairResponse:
        """
        Path B: Repair state drift by reconciling resources referential integrity.

        Default behavior (preview_only=True):
        - Report what would be repaired.
        Apply (preview_only=False):
        - Undelete any geometry.body that is still referenced by live geometry.section resources.
        - Create minimal implicit body resources for any referenced body_id missing entirely.
        - Persist to DesignStore and bump design_version via StateManager.set().
        """
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        current_version = sm.get("design_version", 0) if hasattr(sm, "get") else 0
        if request.expected_version is not None and request.expected_version != current_version:
            raise HTTPException(
                status_code=409,
                detail={"error": "stale_version", "expected_version": request.expected_version, "current_version": current_version},
            )

        state_dict = sm.to_dict() if hasattr(sm, "to_dict") else {}
        resources = (state_dict.get("resources") or {}) if isinstance(state_dict, dict) else {}
        if not isinstance(resources, dict):
            return IntegrityRepairResponse(
                success=False,
                design_id=design_id,
                design_version_before=current_version,
                design_version_after=current_version,
                applied=False,
                errors=["resources_not_a_dict"],
            )

        # referenced bodies from live sections
        referenced_body_ids = set()
        for _rid, r in resources.items():
            if isinstance(r, dict) and r.get("_type") == "geometry.section" and not r.get("_deleted"):
                bid = r.get("body_id")
                if isinstance(bid, str) and bid:
                    referenced_body_ids.add(bid)

        actions: List[Dict[str, Any]] = []
        warnings: List[str] = []

        # plan repairs
        bodies_to_undelete = []
        bodies_to_create = []
        for bid in sorted(referenced_body_ids):
            b = resources.get(bid)
            if isinstance(b, dict) and b.get("_type") == "geometry.body":
                if b.get("_deleted"):
                    bodies_to_undelete.append(bid)
            else:
                # missing body resource entirely
                bodies_to_create.append(bid)

        for bid in bodies_to_undelete:
            actions.append({"op": "UNDELETE_BODY", "body_id": bid, "path": f"resources.{bid}._deleted", "value": False})
        for bid in bodies_to_create:
            actions.append({"op": "CREATE_IMPLICIT_BODY", "body_id": bid, "path": f"resources.{bid}", "value": {
                "_type": "geometry.body",
                "_id": bid,
                "body_type": "implicit_body",
                "physics_category": "surface_piercing",
                "offset_x_m": 0.0,
                "offset_y_m": 0.0,
                "offset_z_m": 0.0,
            }})

        if not actions:
            return IntegrityRepairResponse(
                success=True,
                design_id=design_id,
                design_version_before=current_version,
                design_version_after=current_version,
                applied=False,
                actions=[],
                warnings=[],
                errors=[],
            )

        if request.preview_only:
            warnings.append("Preview only. Re-run with preview_only=false to apply.")
            return IntegrityRepairResponse(
                success=True,
                design_id=design_id,
                design_version_before=current_version,
                design_version_after=current_version,
                applied=False,
                actions=actions,
                warnings=warnings,
                errors=[],
            )

        # apply repairs
        try:
            txn = sm.begin_transaction()
            for a in actions:
                if a["op"] == "UNDELETE_BODY":
                    sm.set(a["path"], a["value"], source="integrity_repair")
                elif a["op"] == "CREATE_IMPLICIT_BODY":
                    sm.set(a["path"], a["value"], source="integrity_repair")
            sm.commit()
        except Exception as e:
            return IntegrityRepairResponse(
                success=False,
                design_id=design_id,
                design_version_before=current_version,
                design_version_after=current_version,
                applied=False,
                actions=actions,
                warnings=warnings,
                errors=[f"apply_failed: {e}"],
            )

        # persist
        try:
            from magnet.deployment.design_store import DesignStore, VersionConflictError
            store = DesignStore(None)
            new_version = store.save(design_id, state_manager=sm, expected_version=int(current_version or 0))
            store.append_turn_record(design_id, {
                "turn_id": f"turn_{uuid.uuid4().hex[:12]}",
                "phase": "integrity_repair",
                "trigger": "user_request",
                "design_version_before": int(current_version or 0),
                "design_version_after": int(new_version),
                "committed": True,
                "actions": actions,
                "outputs_written": {
                    (a.get("path") if isinstance(a, dict) else None): (
                        getattr(sm, "compute_explain_ref", lambda p, design_version=None: None)(a.get("path"), design_version=int(new_version))
                        if isinstance(a, dict) and isinstance(a.get("path"), str) else None
                    )
                    for a in (actions or [])
                    if isinstance(a, dict) and isinstance(a.get("path"), str)
                },
            })
        except VersionConflictError as e:
            return IntegrityRepairResponse(
                success=False,
                design_id=design_id,
                design_version_before=current_version,
                design_version_after=current_version,
                applied=False,
                actions=actions,
                warnings=warnings,
                errors=[json.dumps(e.to_dict())],
            )
        except Exception as e:
            return IntegrityRepairResponse(
                success=False,
                design_id=design_id,
                design_version_before=current_version,
                design_version_after=current_version,
                applied=True,
                actions=actions,
                warnings=warnings,
                errors=[f"persist_failed: {e}"],
            )

        new_version = sm.get("design_version", current_version) if hasattr(sm, "get") else current_version
        return IntegrityRepairResponse(
            success=True,
            design_id=design_id,
            design_version_before=current_version,
            design_version_after=int(new_version or current_version),
            applied=True,
            actions=actions,
            warnings=warnings,
            errors=[],
        )

    @router.post("/api/v1/designs/{design_id}/spiral/chat", response_model=SpiralChatResponse)
    async def spiral_chat(design_id: str, request: SpiralChatRequest) -> SpiralChatResponse:
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        # Path B: detect integrity drift (deleted bodies still referenced by live sections).
        # We do NOT auto-mutate in chat; we surface warnings + offer a repair endpoint.
        integrity_warnings: List[str] = []
        try:
            state_dict = sm.to_dict() if hasattr(sm, "to_dict") else {}
            resources = (state_dict.get("resources") or {}) if isinstance(state_dict, dict) else {}
            if isinstance(resources, dict):
                referenced_body_ids = set()
                for _rid, r in resources.items():
                    if isinstance(r, dict) and r.get("_type") == "geometry.section" and not r.get("_deleted"):
                        bid = r.get("body_id")
                        if isinstance(bid, str) and bid:
                            referenced_body_ids.add(bid)
                for bid in sorted(referenced_body_ids):
                    b = resources.get(bid)
                    if isinstance(b, dict) and b.get("_type") == "geometry.body" and b.get("_deleted"):
                        integrity_warnings.append(
                            f"Body '{bid}' is marked _deleted but is still referenced by live sections. "
                            f"Run Repair to reconcile."
                        )
        except Exception:
            pass

        # Failure mode #1: optimistic locking (stale version → 409)
        current_version = sm.get("design_version", 0) if hasattr(sm, "get") else 0
        if request.expected_version is not None and request.expected_version != current_version:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "stale_version",
                    "expected_version": request.expected_version,
                    "current_version": current_version,
                },
            )

        design_version_before = current_version

        # (A) Meta / explain requests should NOT go through the geometry proposer.
        # These are "human-in-the-loop communication" queries, not state mutations.
        msg = (request.message or "").strip()
        lowered_msg = msg.lower()
        # Holds either the LLM-generated DSL or user-supplied JSON→DSL conversion.
        program_text: str = ""
        avg_conf: float = 0.0
        explain_triggers = (
            "what did you change",
            "what changed",
            "summarize changes",
            "summarize what changed",
            "explain what changed",
            "explain the changes",
            "show the changes",
            "diff",
        )
        if any(t in lowered_msg for t in explain_triggers):
            spiral_state = sm.get("phase_states.hull_form", {}).get("spiral", {}) if hasattr(sm, "get") else {}
            checkpoints = spiral_state.get("checkpoints", []) if isinstance(spiral_state, dict) else []
            last_cp = checkpoints[-1] if checkpoints else {}
            program_text = (last_cp.get("program_text") or "").strip()
            it = int(spiral_state.get("iteration", 0) or 0) if isinstance(spiral_state, dict) else 0
            dv = int(sm.get("design_version", design_version_before) or design_version_before) if hasattr(sm, "get") else design_version_before
            return SpiralChatResponse(
                success=True,
                design_id=design_id,
                design_version_before=dv,
                design_version_after=dv,
                spiral_iteration=it,
                status="applied",
                feedback=(
                    "Last applied change (most recent spiral checkpoint):\n"
                    + (program_text[:1200] + ("…" if len(program_text) > 1200 else "") if program_text else "(no program recorded)")
                ),
                program_text=program_text,
                average_confidence=float(last_cp.get("confidence", 1.0) or 1.0),
                glb_ready=False,
                errors=[],
                integrity_warnings=integrity_warnings,
            )

        # (B0) If the user pastes a JSON DesignProgram, apply it directly (no LLM required).
        program_json = _maybe_parse_json_program_from_message(msg)
        if program_json is not None:
            program_text = _program_json_to_program_text(program_json)
            if not program_text:
                return SpiralChatResponse(
                    success=False,
                    design_id=design_id,
                    design_version_before=design_version_before,
                    design_version_after=design_version_before,
                    status="failed",
                    feedback=(
                        "JSON program parsed, but no executable operations were found. "
                        "Expected: {\"operations\": [{\"op\":\"CREATE\",\"type\":\"geometry.section\",...}, ...]}"
                    ),
                    program_text="",
                    average_confidence=0.0,
                    errors=["empty_or_invalid_operations"],
                    integrity_warnings=integrity_warnings,
                )
            avg_conf = 1.0

        # (B) Propose geometry program from message (if NL)
        from magnet.agents.geometry_proposer import create_geometry_proposer
        proposer = create_geometry_proposer()
        proposal = None
        if not program_text:
            proposal = await proposer.propose(intent=request.message, current_state=sm.to_dict())
            if not proposal.success or not proposal.program:
                err = (proposal.error or "proposal_failed")
                lowered = err.lower()

                # LLM may be unavailable (no network / missing permissions). Provide a no-LLM testing path.
                if "failed to initialize anthropic client" in lowered or "operation not permitted" in lowered:
                    return SpiralChatResponse(
                        success=True,
                        design_id=design_id,
                        design_version_before=design_version_before,
                        design_version_after=design_version_before,
                        status="needs_clarification",
                        feedback=(
                            "LLM is unavailable in this environment (Anthropic client could not initialize). "
                            "To test geometry_schema.json without an LLM, paste a JSON DesignProgram directly into the command box.\n\n"
                            "Example:\n"
                            "json: {\"operations\": [{\"op\":\"CREATE\",\"type\":\"geometry.section\",\"id\":\"bow\",\"params\":{\"station\":0.0,\"points\":[[0,0],[1,-0.5],[1,0.5]]}}]}\n"
                        ),
                        errors=[err],
                        clarification_request_id=request.request_id,
                        clarification_questions=[],
                        requires_confirmation=False,
                        integrity_warnings=integrity_warnings,
                    )
            
                # Human-in-loop: LLM timeout is recoverable - suggest simpler request
                if "llm_timeout" in lowered or "timed out" in lowered:
                    return SpiralChatResponse(
                        success=True,  # Not a system failure, just slow
                        design_id=design_id,
                        design_version_before=design_version_before,
                        design_version_after=design_version_before,
                        status="needs_clarification",
                        feedback=(
                            "The AI model took too long to respond. This can happen with complex requests. "
                            "Try a simpler request like 'create a 22m patrol boat' or try again."
                        ),
                        errors=[],
                        clarification_request_id=request.request_id,
                        clarification_questions=[
                            {
                                "id": "timeout_retry",
                                "question": "Would you like to try a simpler request, or retry the same request?",
                                "type": "select",
                                "options": ["retry_same", "try_simpler"],
                            }
                        ],
                        requires_confirmation=False,  # User can just type a new command
                        integrity_warnings=integrity_warnings,
                    )
                if "geometry.section.points" in lowered or ("points must be" in lowered and "[y" in lowered):
                    # Human-in-loop: surface a clarification rather than producing plausible junk.
                    return SpiralChatResponse(
                        success=True,
                        design_id=design_id,
                        design_version_before=design_version_before,
                        design_version_after=design_version_before,
                        status="needs_clarification",
                        feedback=(
                            "Clarification needed: section point coordinates were ambiguous/invalid. "
                            "Polygon section points must be 2D [y,z] only (X comes from station)."
                        ),
                        errors=[err],
                        clarification_request_id=request.request_id,
                        clarification_questions=[
                            {
                                "id": "section_points_coordinate_contract",
                                "question": (
                                    "Your requested change produced section points that look like [x,y,z] triples. "
                                    "In MAGNET, polygon section points MUST be [[y,z],...]. "
                                    "Confirm you want 2D section points (y,z) with X derived from station."
                                ),
                                "type": "confirm",
                                "options": ["yes_use_2d_yz_only"],
                            }
                        ],
                        requires_confirmation=True,
                    )

                return SpiralChatResponse(
                    success=False,
                    design_id=design_id,
                    design_version_before=design_version_before,
                    design_version_after=design_version_before,
                    status="failed",
                    feedback=f"Proposal failed: {err}",
                    errors=[err],
                    integrity_warnings=integrity_warnings,
                )

            avg_conf = sum(op.confidence for op in proposal.program.operations) / max(len(proposal.program.operations), 1)
            program_text = proposal.program_text

        # (B.1) If the proposer returned no concrete operations, treat as clarification, not low-confidence apply.
        if proposal and not proposal.program.operations:
            return SpiralChatResponse(
                success=True,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="needs_clarification",
                feedback="Clarification needed: no concrete geometry operations were proposed. Please specify what to change about the geometry.",
                program_text=program_text,
                average_confidence=0.0,
                clarification_request_id=request.request_id,
                clarification_questions=[
                    {
                        "id": "no_ops",
                        "question": "Do you want to change hull shape (sections), add a feature (discontinuity), or change configuration (bodies/offsets)?",
                        "type": "select",
                        "options": ["sections", "discontinuity", "bodies_offsets"],
                    }
                ],
                requires_confirmation=True,
                integrity_warnings=integrity_warnings,
            )

        # (C) Low confidence → do not commit unless force_apply (human-in-loop)
        if proposal and avg_conf < request.min_confidence and not request.force_apply:
            return SpiralChatResponse(
                success=True,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="proposal_low_confidence",
                feedback=f"Low confidence ({avg_conf:.2f}). Please refine or explicitly apply.",
                program_text=program_text,
                average_confidence=avg_conf,
                requires_confirmation=True,
                integrity_warnings=integrity_warnings,
            )

        # (D) Execute program atomically into the design-scoped StateManager
        from magnet.kernel.program_executor import execute_program
        try:
            result = execute_program(program_text=program_text, state_manager=sm, dry_run=False)
        except Exception as e:
            msg = str(e)
            lowered = msg.lower()
            if "points" in lowered and ("[y, z]" in msg or "x is derived from station" in lowered):
                return SpiralChatResponse(
                    success=True,
                    design_id=design_id,
                    design_version_before=design_version_before,
                    design_version_after=design_version_before,
                    status="needs_clarification",
                    feedback=(
                        "Clarification needed: invalid section point format. "
                        "Polygon section points must be 2D [y,z] pairs (X comes from station)."
                    ),
                    program_text=program_text,
                    average_confidence=avg_conf,
                    errors=[msg],
                    clarification_request_id=request.request_id,
                    clarification_questions=[
                        {
                            "id": "section_points_coordinate_contract",
                            "question": (
                                "Confirm section point convention: polygon section points are [[y,z],...]. "
                                "The attempted update used a non-2D point format."
                            ),
                            "type": "confirm",
                            "options": ["yes_use_2d_yz_only"],
                        }
                    ],
                    requires_confirmation=True,
                )
            return SpiralChatResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="failed",
                feedback="Execution failed",
                program_text=program_text,
                average_confidence=avg_conf,
                errors=[str(e)],
            )

        # IMPORTANT: execute_program returns an ExecutionResult; it does not always raise.
        # If the grammar/validation fails (e.g., invalid geometry.section.points), we must
        # surface it as human-in-loop clarification and MUST NOT mutate spiral checkpoints.
        if not getattr(result, "success", False):
            errs = list(getattr(result, "errors", []) or [])
            joined = "\n".join(errs).lower()
            if "points" in joined and ("[y, z]" in joined or "x is derived from station" in joined):
                return SpiralChatResponse(
                    success=True,
                    design_id=design_id,
                    design_version_before=design_version_before,
                    design_version_after=design_version_before,
                    status="needs_clarification",
                    feedback=(
                        "Clarification needed: invalid section point format. "
                        "Polygon section points must be 2D [y,z] pairs (X comes from station)."
                    ),
                    program_text=program_text,
                    average_confidence=avg_conf,
                    errors=errs,
                    clarification_request_id=request.request_id,
                    clarification_questions=[
                        {
                            "id": "section_points_coordinate_contract",
                            "question": (
                                "The attempted update used a non-2D section point format. "
                                "Confirm polygon section points are [[y,z],...] with X derived from station."
                            ),
                            "type": "confirm",
                            "options": ["yes_use_2d_yz_only"],
                        }
                    ],
                    requires_confirmation=True,
                )
            return SpiralChatResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="failed",
                feedback="Execution failed",
                program_text=program_text,
                average_confidence=avg_conf,
                errors=errs or ["execution_failed"],
            )

        design_version_after = sm.get("design_version", design_version_before) if hasattr(sm, "get") else design_version_before

        # ---------------------------------------------------------------------
        # Bridge: geometry primitives → hull.* scalars (demo-critical)
        #
        # Kernel phases (hull/weight/stability) still gate on hull.lwl/beam/draft/depth/cb.
        # When the design is authored via geometry.* primitives, those scalars may be absent.
        #
        # For demo operations, infer reasonable hull scalars from the authoritative mesh
        # bounds and seed them ONLY if missing. This unblocks:
        # - hydrostatics/weight/stability validators
        # - equilibrium UI fields
        # - propulsion power checks
        # ---------------------------------------------------------------------
        try:
            import re
            # NOTE: hull.* and mission.* are refinable paths and require transactions.
            pending_writes: Dict[str, Any] = {}

            # (1) Prefer deriving scalars directly from the proposed program (fast, deterministic).
            # This avoids any dependency on mesh generation during the request.
            try:
                max_y = None
                min_z = None
                max_z = None
                if proposal and getattr(proposal, "program", None):
                    for op in getattr(proposal.program, "operations", []) or []:
                        if getattr(op, "type", None) != "geometry.section":
                            continue
                        pts = (getattr(op, "params", {}) or {}).get("points") or []
                        if not isinstance(pts, list):
                            continue
                        for pt in pts:
                            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                                continue
                            y, z = pt[0], pt[1]
                            try:
                                y = float(y)
                                z = float(z)
                            except Exception:
                                continue
                            max_y = y if max_y is None else max(max_y, y)
                            min_z = z if min_z is None else min(min_z, z)
                            max_z = z if max_z is None else max(max_z, z)

                if max_y is not None and sm.get("hull.beam") is None:
                    pending_writes["hull.beam"] = float(max_y) * 2.0
                if min_z is not None and sm.get("hull.draft") is None:
                    pending_writes["hull.draft"] = float(max(0.0, -min_z))
                if max_z is not None and sm.get("hull.depth") is None:
                    pending_writes["hull.depth"] = float(max(0.0, max_z))
                if sm.get("hull.cb") is None:
                    pending_writes["hull.cb"] = 0.45
            except Exception:
                pass

            # (2) Infer length from user intent text (common in demo prompts: "12 meter ...").
            if sm.get("hull.lwl") is None:
                m_len = re.search(r"([0-9]+(?:\\.[0-9]+)?)\\s*(?:m|meter|meters)\\b", (request.message or "").lower())
                if m_len:
                    lwl = float(m_len.group(1))
                    pending_writes["hull.lwl"] = lwl
                    # Optional: keep LOA aligned if absent
                    if sm.get("hull.loa") is None:
                        pending_writes["hull.loa"] = lwl

            # (3) Fallback: derive length/beam/depth from authoritative mesh bounds if still missing.
            # (Keeps robustness for prompts without explicit length.)
            try:
                if any(
                    sm.get(k) is None
                    for k in ("hull.lwl", "hull.beam", "hull.draft", "hull.depth")
                ):
                    from magnet.webgl.geometry_service import GeometryService
                    from magnet.webgl.schema import LODLevel

                    service = GeometryService(state_manager=sm)
                    mesh, _mode = service.get_hull_geometry(design_id=design_id, lod=LODLevel.LOW, allow_visual_only=True)
                    b = getattr(mesh, "bounds", None)
                    if b is not None:
                        min_x, min_y, min_z = b.min
                        max_x, max_y, max_z = b.max
                        length_m = float(max_x - min_x)
                        beam_m = float(max_y - min_y)
                        draft_m = float(max(0.0, -min_z))
                        depth_m = float(max(0.0, max_z))

                        if sm.get("hull.lwl") is None and length_m > 0:
                            pending_writes["hull.lwl"] = length_m
                        if sm.get("hull.beam") is None and beam_m > 0:
                            pending_writes["hull.beam"] = beam_m
                        if sm.get("hull.draft") is None and draft_m > 0:
                            pending_writes["hull.draft"] = draft_m
                        if sm.get("hull.depth") is None and depth_m > 0:
                            pending_writes["hull.depth"] = depth_m
                        if sm.get("hull.cb") is None:
                            pending_writes["hull.cb"] = 0.45
            except Exception:
                pass

            # Best-effort mission speed parse to unblock resistance/propulsion.
            if sm.get("mission.max_speed_kts") is None:
                m = re.search(r"([0-9]+(?:\\.[0-9]+)?)\\s*(?:kts?|knots?)\\b", (request.message or "").lower())
                if m:
                    pending_writes["mission.max_speed_kts"] = float(m.group(1))

            # Apply writes transactionally (refinable-path enforcement).
            if pending_writes:
                try:
                    txn = sm.begin_transaction()
                    for path, value in pending_writes.items():
                        sm.set(path, value, "geometry")
                    sm.commit()
                except Exception:
                    # Never fail spiral due to bridge writes.
                    try:
                        sm.rollback()
                    except Exception:
                        pass
        except Exception:
            pass

        # (D.1) Failure mode #2: run critical phases/cascade before returning "applied"
        failed_phases: List[str] = []
        invalidated_phases: List[str] = []
        if request.run_critical_phases:
            # Use canonical kernel phase names (see magnet/kernel/registry.py).
            # These phases are ordered and dependency-checked by the Conductor.
            phases = request.critical_phases or ["hull", "structure", "propulsion", "weight", "stability"]
            try:
                from magnet.kernel.conductor import Conductor
                from magnet.validators.registry import ValidatorRegistry
                from magnet.validators.topology import ValidatorTopology
                from magnet.validators.executor import PipelineExecutor
                from magnet.validators.builtin import get_all_validators

                # Wire the river: ensure validators flow into the Conductor
                # Without this, the Conductor falls back to legacy execution
                # with an empty _validators dict, computing nothing.
                if not ValidatorRegistry._initialized:
                    ValidatorRegistry.reset()
                    ValidatorRegistry.initialize_defaults()
                    ValidatorRegistry.instantiate_all()

                # Build topology from validator definitions
                topology = ValidatorTopology()
                for defn in get_all_validators():
                    topology.add_validator(defn)
                topology.build()

                # Create wired executor
                executor = PipelineExecutor(
                    topology=topology,
                    state_manager=sm,
                    validator_registry=ValidatorRegistry.get_all_instances(),
                )

                # Now the Conductor has water to carry
                conductor = Conductor(state_manager=sm)
                conductor.set_pipeline_executor(executor)

                for p in phases:
                    try:
                        res = conductor.run_phase(p)
                        # PhaseResult has status, not success.
                        if getattr(res, "status", None) is not None and getattr(res.status, "value", "") in ("failed", "blocked"):
                            failed_phases.append(p)
                    except Exception:
                        failed_phases.append(p)

                # Pour the water into the reservoir:
                # write_to_state() stores kernel metadata (session, phase history)
                conductor.write_to_state()

            except Exception:
                # Phase runner not wired - non-blocking but visible
                pass

        # Human Decision Point: if conductor set awaiting_human_decision, surface it as needs_clarification
        # so UI can request explicit approval without treating the run as "failed".
        try:
            if sm.get("kernel.awaiting_human_decision", False):
                req = sm.get("kernel.human_decision_request", {}) or {}
                reasons = req.get("severe_reasons") or []
                return SpiralChatResponse(
                    success=True,
                    design_id=design_id,
                    design_version_before=design_version_before,
                    design_version_after=design_version_after,
                    spiral_iteration=0,
                    status="needs_clarification",
                    feedback="Human Decision Point: severe grade detected. Approve to continue or revise the design.",
                    program_text=program_text,
                    average_confidence=avg_conf,
                    clarification_request_id=request.request_id,
                    clarification_questions=[
                        {
                            "id": "human_decision_point",
                            "question": "Severe grade detected: " + (", ".join(reasons) if reasons else "see kernel.human_decision_request") + ". Continue anyway?",
                            "type": "choice",
                            "options": ["CONTINUE_DESPITE_WARNING", "REVISE"],
                        }
                    ],
                    requires_confirmation=True,
                    failed_phases=failed_phases,
                    invalidated_phases=invalidated_phases,
                    errors=[],
                    integrity_warnings=integrity_warnings,
                )
        except Exception:
            pass

        # (G) §SKELETON:CheckpointPruning - Manage spiral iteration and prune old checkpoints
        current_iteration = 1
        try:
            spiral_state = sm.get("phase_states.hull_form", {}).get("spiral", {}) if hasattr(sm, "get") else {}
            current_iteration = spiral_state.get("iteration", 0) + 1
            checkpoints = spiral_state.get("checkpoints", [])
            
            checkpoints.append({
                "iteration": current_iteration,
                "design_version": design_version_after,
                "program_text": program_text,
                "confidence": avg_conf,
                "timestamp": datetime.utcnow().isoformat(),
            })
            
            if len(checkpoints) > request.max_checkpoint_iterations:
                checkpoints = checkpoints[-request.max_checkpoint_iterations:]
            
            sm.set("phase_states.hull_form", {
                **sm.get("phase_states.hull_form", {}),
                "spiral": {
                    "iteration": current_iteration,
                    "checkpoints": checkpoints,
                    "last_message": request.message,
                }
            }, source="spiral_chat")
        except Exception:
            current_iteration = 1

        # (H) Persistence is authority: save to DesignStore so subsequent requests load this update.
        try:
            from magnet.deployment.design_store import DesignStore, VersionConflictError
            store = DesignStore(None)
            # Only apply version-lock if we actually advanced the design_version.
            dv_after = sm.get("design_version", design_version_before) if hasattr(sm, "get") else design_version_before
            if int(dv_after or 0) > int(design_version_before or 0):
                new_version = store.save(
                    design_id,
                    state_manager=sm,
                    expected_version=int(design_version_before or 0),
                )
            else:
                # No committed changes (e.g., no-op message). Persist is unnecessary.
                new_version = int(dv_after or design_version_before)

            # Append turn record (always witness the attempt).
            store.append_turn_record(design_id, {
                "turn_id": f"turn_{uuid.uuid4().hex[:12]}",
                "phase": "spiral_chat",
                "trigger": "user_request",
                "request_id": request.request_id,
                "design_version_before": int(design_version_before or 0),
                "design_version_after": int(new_version),
                "committed": int(new_version) > int(design_version_before or 0),
                "program_text": program_text[:1200] if isinstance(program_text, str) else "",
                "average_confidence": float(avg_conf or 0.0),
                "failed_phases": failed_phases,
                "integrity_warnings": integrity_warnings,
                "outputs_written": {
                    p: getattr(sm, "compute_explain_ref", lambda x, design_version=None: None)(p, design_version=int(new_version))
                    for p in (sm.get_last_commit_written_paths() if hasattr(sm, "get_last_commit_written_paths") else [])
                    if isinstance(p, str)
                } if int(new_version) > int(design_version_before or 0) else {},
            })
        except VersionConflictError as e:
            raise HTTPException(status_code=409, detail=e.to_dict())
        except Exception as e:
            return SpiralChatResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                spiral_iteration=current_iteration,
                status="failed",
                feedback="Persistence failed",
                program_text=program_text,
                average_confidence=avg_conf,
                errors=[f"persist_failed: {e}"],
            )

        # (E) Emit WS events using existing types (transition safe)
        try:
            from magnet.deployment.websocket import WSMessage, MessageType
            ws_manager.queue_message(
                WSMessage(
                    type=MessageType.DESIGN_UPDATED.value,
                    design_id=design_id,
                    payload={
                        "source": "spiral",
                        "request_id": request.request_id,
                        "design_version_after": design_version_after,
                        "spiral_iteration": current_iteration,
                        "average_confidence": avg_conf,
                        "status": (
                            "partial"
                            if result.success and failed_phases
                            else ("applied" if result.success else "failed")
                        ),
                        "metrics": (result.validation or {}).get("metrics", {}),
                        "deltas": (result.validation or {}).get("deltas", {}),
                        "failed_phases": failed_phases,
                        "invalidated_phases": invalidated_phases,
                    },
                )
            )
            ws_manager.queue_message(
                WSMessage(
                    type=MessageType.SNAPSHOT_CREATED.value,
                    design_id=design_id,
                    payload={"design_version_after": design_version_after, "artifact": "geometry.glb", "ready": True},
                )
            )
        except Exception:
            # WS not available - continue without WS updates
            pass

        return SpiralChatResponse(
            success=result.success,
            design_id=design_id,
            design_version_before=design_version_before,
            design_version_after=int(new_version or design_version_after),
            spiral_iteration=current_iteration,
            status=(
                "partial"
                if result.success and failed_phases
                else ("applied" if result.success else "failed")
            ),
            feedback="Applied" if result.success else "Failed",
            program_text=program_text,
            average_confidence=avg_conf,
            metrics=(result.validation or {}).get("metrics", {}),
            deltas=(result.validation or {}).get("deltas", {}),
            invalidated_phases=invalidated_phases or (result.validation or {}).get("invalidated_phases", []),
            failed_phases=failed_phases,
            glb_ready=True if result.success else False,
            errors=result.errors if hasattr(result, "errors") else [],
            integrity_warnings=integrity_warnings,
        )

    @router.post("/api/v1/designs/{design_id}/spiral/sketch", response_model=SpiralSketchResponse)
    async def spiral_sketch(
        design_id: str,
        image: UploadFile = File(...),
        annotations: str = Form(default=""),
        confirm_execution: bool = Form(default=False),
        expected_version: Optional[int] = Form(default=None),
    ) -> SpiralSketchResponse:
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        design_version_before = sm.get("design_version", 0) if hasattr(sm, "get") else 0
        
        if expected_version is not None and expected_version != design_version_before:
            raise HTTPException(
                status_code=409,
                detail={"error": "stale_version", "expected_version": expected_version, "current_version": design_version_before},
            )

        # Step 1: Vision → interpretation
        from magnet.agents.vision_interpreter import VisionInterpreter
        from magnet.llm.providers.anthropic import AnthropicProvider
        provider = AnthropicProvider()
        interpreter = VisionInterpreter(provider)
        image_data = await image.read()
        vision = await interpreter.interpret_sketch(
            image_data=image_data, 
            annotations=annotations, 
            image_media_type=image.content_type
        )
        
        if not vision.success:
            return SpiralSketchResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                status="failed",
                feedback="Sketch interpretation failed",
                errors=[vision.error or "vision_failed"],
            )

        extracted_values = vision.interpretation.model_dump() if vision.interpretation else {}
        
        # If not confirmed, return for human review (NEVER auto-execute sketches)
        if not confirm_execution:
            return SpiralSketchResponse(
                success=True,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                interpretation=extracted_values,
                extracted_values=extracted_values,
                requires_confirmation=True,
                intent_string=vision.intent_string,
                average_confidence=vision.confidence if hasattr(vision, 'confidence') else 0.5,
                status="awaiting_confirmation",
                feedback="Please confirm extracted values before execution",
            )

        # Confirmed - proceed with geometry proposal
        from magnet.agents.geometry_proposer import create_geometry_proposer
        proposer = create_geometry_proposer()
        proposal = await proposer.propose(intent=vision.intent_string, current_state=sm.to_dict())
        
        if not proposal.success or not proposal.program:
            return SpiralSketchResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                interpretation=extracted_values,
                intent_string=vision.intent_string,
                status="failed",
                feedback="Geometry proposal failed",
                errors=[proposal.error or "proposal_failed"],
            )

        # Execute program
        from magnet.kernel.program_executor import execute_program
        try:
            result = execute_program(program_text=proposal.program_text, state_manager=sm, dry_run=False)
        except Exception as e:
            return SpiralSketchResponse(
                success=False,
                design_id=design_id,
                design_version_before=design_version_before,
                design_version_after=design_version_before,
                interpretation=extracted_values,
                intent_string=vision.intent_string,
                program_text=proposal.program_text,
                status="failed",
                feedback="Execution failed",
                errors=[str(e)],
            )

        design_version_after = sm.get("design_version", design_version_before) if hasattr(sm, "get") else design_version_before
        avg_conf = sum(op.confidence for op in proposal.program.operations) / max(len(proposal.program.operations), 1)

        # Emit WS events
        try:
            from magnet.deployment.websocket import WSMessage, MessageType
            ws_manager.queue_message(
                WSMessage(
                    type=MessageType.DESIGN_UPDATED.value,
                    design_id=design_id,
                    payload={"source": "spiral_sketch", "design_version_after": design_version_after},
                )
            )
            ws_manager.queue_message(
                WSMessage(
                    type=MessageType.SNAPSHOT_CREATED.value,
                    design_id=design_id,
                    payload={"design_version_after": design_version_after, "artifact": "geometry.glb", "ready": True},
                )
            )
        except Exception:
            pass

        return SpiralSketchResponse(
            success=result.success,
            design_id=design_id,
            design_version_before=design_version_before,
            design_version_after=design_version_after,
            interpretation=extracted_values,
            extracted_values=extracted_values,
            requires_confirmation=False,
            intent_string=vision.intent_string,
            program_text=proposal.program_text,
            average_confidence=avg_conf,
            status="applied" if result.success else "failed",
            feedback="Sketch executed successfully" if result.success else "Execution failed",
            metrics=(result.validation or {}).get("metrics", {}),
            deltas=(result.validation or {}).get("deltas", {}),
            glb_ready=True if result.success else False,
            errors=result.errors if hasattr(result, 'errors') else [],
        )

    # §SKELETON:MigrationEndpoint
    @router.post("/api/v1/designs/{design_id}/migrate-to-geometry")
    async def migrate_to_geometry(
        design_id: str,
        preview_only: bool = True,
        expected_version: Optional[int] = None,
    ):
        """
        MIGRATION ONLY: Convert legacy parametric state to geometry primitives.
        
        ⚠️ WARNING: This is one-time backward compatibility code.
        DO NOT copy this pattern to kernel or agent code.
        """
        sm = get_state_manager(design_id)
        if not sm:
            raise HTTPException(status_code=404, detail="Design not found")

        current_version = sm.get("design_version", 0) if hasattr(sm, "get") else 0
        if expected_version is not None and expected_version != current_version:
            raise HTTPException(status_code=409, detail={"error": "stale_version"})

        # Check if already has geometry resources
        resources = sm.get("resources", {}) if hasattr(sm, "get") else {}
        if resources.get("geometry"):
            return {"success": False, "error": "Design already has geometry resources", "needs_migration": False}

        # Extract legacy parameters
        hull_loa = sm.get("hull.loa") if hasattr(sm, "get") else None
        hull_beam = sm.get("hull.beam") if hasattr(sm, "get") else None
        hull_draft = sm.get("hull.draft") if hasattr(sm, "get") else None
        hull_type = sm.get("hull.hull_type", "monohull") if hasattr(sm, "get") else "monohull"

        if not all([hull_loa, hull_beam, hull_draft]):
            return {"success": False, "error": "Missing required hull dimensions", "needs_migration": True}

        # Generate migration program (MIGRATION ONLY - geometry-derived)
        body_count = (
            sm.get("geometry.body_count", 0)
            or sm.get("hull.body_count", 0)
            or sm.get("hull.num_hulls", 0)
            or 1
        )
        try:
            body_count = int(body_count)
        except Exception:
            body_count = 1
        body_count = max(1, body_count)

        hull_spacing = sm.get("hull.hull_spacing_m") if hasattr(sm, "get") else None
        if hull_spacing is None and hull_beam:
            hull_spacing = hull_beam / 2

        body_offset = 0.0
        if body_count > 1 and hull_spacing:
            body_offset = float(hull_spacing) / 2.0

        program_lines = [
            f"# MIGRATION: Auto-generated from legacy state",
            f"# Source: hull_type={hull_type}, loa={hull_loa}, beam={hull_beam}, draft={hull_draft}",
            f"# Provenance: migration_only",
            f"",
        ]
        
        if body_count == 1:
            program_lines.extend([
                f'CREATE geometry.body main {{',
                f'  body_type: "hull"',
                f'  physics_category: "surface_piercing"',
                f'  offset_y_m: 0.0',
                f'}}',
            ])
        else:
            program_lines.extend([
                f'CREATE geometry.body port {{',
                f'  body_type: "demihull"',
                f'  physics_category: "surface_piercing"',
                f'  offset_y_m: {-body_offset}',
                f'}}',
                f'CREATE geometry.body stbd {{',
                f'  body_type: "demihull"',
                f'  physics_category: "surface_piercing"',
                f'  offset_y_m: {body_offset}',
                f'}}',
            ])

        program_text = "\n".join(program_lines)

        if preview_only:
            return {
                "success": True,
                "preview_only": True,
                "program_text": program_text,
                "needs_migration": True,
                "legacy_values": {"hull_type": hull_type, "loa": hull_loa, "beam": hull_beam, "draft": hull_draft},
                "message": "Review program and call with preview_only=false to execute",
            }

        # Execute migration
        from magnet.kernel.program_executor import execute_program
        try:
            result = execute_program(program_text=program_text, state_manager=sm, dry_run=False)
            return {
                "success": result.success,
                "preview_only": False,
                "program_text": program_text,
                "design_version_after": sm.get("design_version", current_version) if hasattr(sm, "get") else current_version,
                "errors": result.errors if hasattr(result, 'errors') else [],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    return router

