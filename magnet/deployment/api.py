"""
deployment/api.py - REST API v1.2
BRAVO OWNS THIS FILE.

Section 56: Deployment Infrastructure
Provides REST API with full PhaseMachine integration.

v1.2 Fixes:
- Blocker #12: Forward reference bug - Pydantic models at module level

v1.1 Fixes:
- Blocker #5: WebSocket task launched in startup
- Blocker #8: Field validation with aliases
- Blocker #11: Full PhaseMachine integration
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import asyncio
import os
import json
import hashlib
import math

if TYPE_CHECKING:
    from magnet.bootstrap.app import AppContext

logger = logging.getLogger("deployment.api")

# Frontend dist path (relative to project root)
FRONTEND_DIST_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "app", "dist")

# Module 65.2: Serve ui_v2 directly (no build step required)
UI_V2_PATH = os.path.join(os.path.dirname(__file__), "..", "ui_v2")

# LLM translator prompt version (derived from REFINABLE_SCHEMA; single source of truth)
LLM_PROMPT_VERSION = "intent_translator_schema_v3_hullform_params"

# Module-level calculator registry (initialized on startup)
_calculator_registry = None


# =============================================================================
# Request/Response Models (v1.2: Moved to module level to fix forward ref bug)
# =============================================================================

try:
    from pydantic import BaseModel, field_validator

    class DesignCreate(BaseModel):
        """Request model for creating a new design."""
        name: str
        mission: Optional[Dict[str, Any]] = None
        vessel_type: Optional[str] = None

    class DesignUpdate(BaseModel):
        """Request model for updating a design value."""
        path: str
        value: Any

        @field_validator('path')
        @classmethod
        def validate_path(cls, v):
            # v1.1: Allow aliased paths (fixes blocker #8)
            valid_prefixes = [
                'metadata', 'mission', 'hull', 'structure', 'propulsion',
                'systems', 'weight', 'stability', 'compliance', 'phase_states',
                'production', 'outfitting', 'arrangement',
            ]
            prefix = v.split('.')[0]
            if prefix not in valid_prefixes:
                raise ValueError(f'Invalid path prefix: {prefix}. Valid: {valid_prefixes}')
            return v

    class PhaseRun(BaseModel):
        """Request model for running a phase."""
        phases: Optional[List[str]] = None
        max_iterations: int = 5
        async_mode: bool = False
        # Optional optimistic lock (prevents stale writes / race conditions)
        expected_version: Optional[int] = None

    class PhaseApprove(BaseModel):
        """Request model for approving a phase."""
        comment: Optional[str] = None

    class JobSubmit(BaseModel):
        """Request model for submitting a background job."""
        job_type: str
        payload: Dict[str, Any] = {}
        priority: str = "normal"

    class ValidationRun(BaseModel):
        """Request model for running validation."""
        phase: Optional[str] = None
        validators: Optional[List[str]] = None
        # Optional optimistic lock (prevents stale writes / race conditions)
        expected_version: Optional[int] = None
        # If true, persist validator writes as a committed design version.
        # Default is False: validate is diagnostic and should not create commits by default.
        persist: bool = False

    class ActionSubmit(BaseModel):
        """Request model for submitting an ActionPlan."""
        plan_id: str
        intent_id: str
        design_version_before: int
        actions: List[Dict[str, Any]]

        @field_validator('actions')
        @classmethod
        def validate_actions(cls, v):
            if not v:
                raise ValueError('actions list cannot be empty')
            return v

    class IntentPreviewRequest(BaseModel):
        """Request model for previewing an intent (Module 63/65.1)."""
        text: str
        design_version_before: Optional[int] = None
        mode: Optional[str] = "single"  # Module 65.1: "single" or "compound"

    class LLMActionProposal(BaseModel):
        """Structured LLM proposal for a single action (fallback compiler)."""
        action_type: str
        # For set/increase/decrease: required. For run_phases/query: may be omitted.
        path: Optional[str] = None
        value: Optional[Any] = None
        amount: Optional[float] = None
        unit: Optional[str] = None
        bucket: Optional[str] = None
        phases: Optional[List[str]] = None
        query_target: Optional[str] = None
        query_params: Optional[Dict[str, Any]] = None

    class LLMProposals(BaseModel):
        """Structured LLM proposal envelope."""
        actions: List[LLMActionProposal]

    _PYDANTIC_AVAILABLE = True

except ImportError:
    _PYDANTIC_AVAILABLE = False
    # Stub classes for when pydantic is not available
    class DesignCreate:
        pass
    class DesignUpdate:
        pass
    class PhaseRun:
        pass
    class PhaseApprove:
        pass
    class JobSubmit:
        pass
    class ValidationRun:
        pass
    class ActionSubmit:
        pass
    class IntentPreviewRequest:
        pass
    class LLMActionProposal:
        pass
    class LLMProposals:
        pass


# =============================================================================
# Module 65.1 / Control Plane v1.1: HypotheticalStateView with Provenance
# =============================================================================

# Import Control Plane HSV (replaces primitive implementation)
from magnet.control_plane import (
    HypotheticalStateView as ControlPlaneHSV,
    ValueSource,
    ProjectedValue,
)
from magnet.control_plane import (
    query_explain,
    query_history,
    query_impact,
    query_latest,
    get_explain_store,
    DualOutput,
    RecordStatus,
)


class HypotheticalStateView:
    """
    Control Plane v1.1: HypotheticalStateView with 4-source provenance.

    Wrapper that creates a ControlPlaneHSV and exposes both:
    - get(path) for gate compatibility (returns raw value)
    - get_projected(path) for provenance (returns ProjectedValue)
    - to_digest() for UI response
    """

    def __init__(self, real_state_manager, proposed_actions: list):
        """
        Args:
            real_state_manager: The real StateManager to read from
            proposed_actions: List of Action objects to overlay
        """
        # Convert actions to Action objects if needed
        from magnet.kernel.intent_protocol import Action, ActionType
        
        converted_actions = []
        for action in proposed_actions:
            if isinstance(action, Action):
                converted_actions.append(action)
            elif isinstance(action, dict):
                action_type_str = action.get('action_type', 'set')
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    action_type = ActionType.SET
                
                converted_actions.append(Action(
                    action_type=action_type,
                    path=action.get('path'),
                    value=action.get('value'),
                ))
        
        # Create the Control Plane HSV
        self._hsv = ControlPlaneHSV(real_state_manager, converted_actions)

    def get(self, path: str, default=None):
        """
        Return value for gate compatibility (GateCondition.evaluate()).
        
        Uses get_raw() which returns just the value, not ProjectedValue.
        """
        return self._hsv.get_raw(path, default)
    
    def get_projected(self, path: str, default=None) -> ProjectedValue:
        """
        Return ProjectedValue with provenance.
        
        Use this when you need to know the source of the value.
        """
        return self._hsv.get(path, default)
    
    @property
    def contains_virtual_defaults(self) -> bool:
        """True if any value came from kernel baselines."""
        return self._hsv.contains_virtual_defaults
    
    @property
    def virtual_defaults_used(self) -> list:
        """List of paths that used kernel baselines."""
        return list(self._hsv.virtual_defaults_used)
    
    @property
    def stale_paths(self) -> list:
        """List of derived paths that are stale."""
        return list(self._hsv.stale_paths)
    
    @property
    def overlay(self) -> dict:
        """The overlay dictionary (proposed values)."""
        return self._hsv.overlay
    
    @property
    def contains_placeholders(self) -> bool:
        """True if any hull dimensions are still placeholders."""
        return self._hsv.contains_placeholders
    
    @property
    def placeholders_found(self) -> list:
        """List of hull dimension paths that have placeholder provenance."""
        return list(self._hsv.placeholders_found)
    
    def to_digest(self) -> dict:
        """
        Generate digest for UI response.
        
        Returns provenance-tagged projections, stale paths, etc.
        """
        return self._hsv.to_digest()


def check_gates_on_hypothetical(phase: str, hypothetical_view: HypotheticalStateView) -> list:
    """
    Check gate conditions for a phase using hypothetical state.

    Module 65.1: Uses existing GATE_CONDITIONS and GateCondition.evaluate()
    with zero new validation logic. The hypothetical_view overlays proposed
    actions on real state.

    Args:
        phase: Phase name (e.g., "hull_form")
        hypothetical_view: HypotheticalStateView with proposed values

    Returns:
        List of dicts for missing/failed gates: [{path, reason, gate_name}]
    """
    from magnet.core.phase_states import GATE_CONDITIONS

    gates = GATE_CONDITIONS.get(phase, [])
    missing = []

    for gate in gates:
        if not gate.required:
            continue

        # Use existing gate.evaluate() - the core reuse mechanism
        passed, message = gate.evaluate(hypothetical_view)

        if not passed:
            missing.append({
                "path": gate.check_path,
                "reason": gate.error_message or message,
                "gate_name": gate.name,
                "phase": phase,
            })

    return missing


# =============================================================================
# LLM FALLBACK COMPILER (Module 67.x)
# =============================================================================

async def _compile_intent_with_llm_fallback(
    design_id: str,
    request,
    state_manager,
    validator,
    mode: str,
    llm_client=None,
):
    """
    LLM-first compilation with deterministic fallback.

    Translator contract:
    - LLM is the primary translator from human text → kernel Actions.
    - Deterministic parser is fallback only if LLM is unavailable or fails.

    Returns preview payload with provenance and optional apply_payload (gated).
    """
    logger.info(f"[intent_preview] mode={mode} design={design_id} text={getattr(request, 'text', '')!r}")
    import uuid
    from magnet.deployment.intent_parser import (
        parse_intent_to_actions,
        extract_compound_intent,
        get_guidance_message,
    )
    from magnet.core.field_aliases import normalize_path
    from magnet.core.refinable_schema import is_refinable, REFINABLE_SCHEMA
    from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
    from magnet.llm import LLMOptions

    version_before = getattr(request, "design_version_before", None) or state_manager.design_version
    unsupported_mentions = []

    def _serialize_actions(actions_list):
        out = []
        for a in actions_list:
            d: Dict[str, Any] = {"action_type": a.action_type.value}
            if getattr(a, "path", None) is not None:
                d["path"] = a.path
            if getattr(a, "value", None) is not None:
                d["value"] = getattr(a, "value", None)
            if getattr(a, "amount", None) is not None:
                d["amount"] = getattr(a, "amount", None)
            if getattr(a, "unit", None) is not None:
                d["unit"] = getattr(a, "unit", None)
            if getattr(a, "phases", None) is not None:
                d["phases"] = getattr(a, "phases", None)
            if getattr(a, "format", None) is not None:
                d["format"] = getattr(a, "format", None)
            if getattr(a, "message", None) is not None:
                d["message"] = getattr(a, "message", None)
            if getattr(a, "query_target", None) is not None:
                d["query_target"] = getattr(a, "query_target", None)
            if getattr(a, "query_params", None) is not None:
                d["query_params"] = getattr(a, "query_params", None)
            out.append(d)
        return out

    def _build_translator_system_prompt() -> str:
        """
        Schema-driven translator prompt (single source of truth):
        - Valid paths + types (from REFINABLE_SCHEMA)
        - Enum fields include allowed values
        - Numeric fields include kernel units and bounds
        """
        def _fmt_field(p: str, field) -> str:
            try:
                f_type = getattr(field, "type", None)
                keywords = getattr(field, "keywords", None) or ()
                kw = f", keywords={tuple(keywords)}" if keywords else ""
                desc = (getattr(field, "description", None) or "").strip()
                d = f", description={desc!r}" if desc else ""
                if f_type == "enum":
                    allowed = getattr(field, "allowed_values", None) or ()
                    allowed_block = ", ".join(str(v) for v in allowed) if allowed else ""
                    if allowed_block:
                        return f"- {p} (enum: {allowed_block}{kw}{d})"
                    return f"- {p} (enum{kw}{d})"
                if f_type in ("float", "int"):
                    unit = getattr(field, "kernel_unit", "") or ""
                    min_v = getattr(field, "min_value", None)
                    max_v = getattr(field, "max_value", None)
                    allowed_units = getattr(field, "allowed_units", None) or ()
                    bounds = ""
                    if (min_v is not None) or (max_v is not None):
                        bounds = f", bounds={min_v}..{max_v}"
                    au = f", allowed_units={tuple(allowed_units)}" if allowed_units else ""
                    u = f", unit={unit}" if unit else ""
                    return f"- {p} ({f_type}{u}{au}{bounds}{kw}{d})"
                if f_type == "bool":
                    return f"- {p} (bool{kw}{d})"
            except Exception:
                pass
            return f"- {p}"

        lines = []
        for p in sorted(REFINABLE_SCHEMA.keys()):
            lines.append(_fmt_field(p, REFINABLE_SCHEMA.get(p)))

        allowed_paths_block = "\n".join(lines)

        return (
            "You are MAGNET's kernel translator. Convert the user's text into kernel actions.\n"
            "\n"
            f"Prompt version: {LLM_PROMPT_VERSION}\n"
            "\n"
            "Valid action_type values:\n"
            "- set\n"
            "- increase\n"
            "- decrease\n"
            "- run_phases\n"
            "- query\n"
            "\n"
            "Valid refinable paths (from REFINABLE_SCHEMA):\n"
            f"{allowed_paths_block}\n"
            "\n"
            "Bucket vocabulary (use when user implies magnitude without a number):\n"
            "- a_bit\n"
            "- normal\n"
            "- way\n"
            "\n"
            "Interpretation hints (choose the MOST specific matching path):\n"
            "- If user mentions transom/stern/aft width or a pointed stern: use hull.transom_beam_ratio (0..1), not hull.beam.\n"
            "- If user mentions trim/even keel/by the bow/by the stern: use hull.draft_fwd_m and/or hull.draft_aft_m; use hull.draft only for overall draft.\n"
            "- If user mentions freeboard/higher sides: use hull.freeboard_m.\n"
            "- If user mentions bow flare/spray/deck wetness: use hull.bow_flare_deg.\n"
            "- If user mentions stem rake: use hull.stem_rake_deg.\n"
            "- If user mentions bow entry angle/sharp entry/blunt bow: use hull.bow_entrance_deg.\n"
            "- If user mentions transom deadrise/flatter transom: use hull.deadrise_transom_deg.\n"
            "- If user mentions LCB/center of buoyancy forward/aft: use hull.lcb_fraction (fraction from FP; 0=bow/FP, 1=stern/AP).\n"
            "\n"
            "QUERY targets (read-only analysis):\n"
            "- hull.proportions\n"
            "- hull.regime\n"
            "\n"
            "Synthesis trigger:\n"
            "- If user asks to size/synthesize/generate the hull from a mission, first SET the mission/hull constraints they provided,\n"
            "  then include {action_type:\"run_phases\", phases:[\"hull\"]}.\n"
            "\n"
            "=== HULL STYLE VOCABULARY (LLM-Generated Hull Refinement v1.0) ===\n"
            "\n"
            "When the user describes aesthetic intent, propose hull FEATURES, not just dimensions.\n"
            "\n"
            "Core Feature Paths (8 key toggles):\n"
            "- hull.bow_style: traditional | wedge | axe | wave_piercing (shape of bow)\n"
            "- hull.chine_type: soft | hard | double | triple (hull cross-section)\n"
            "- hull.spray_rail_count: 0-4 (horizontal deflectors)\n"
            "- hull.tumblehome_enabled: true | false (inward lean above waterline)\n"
            "- hull.tumblehome_angle_deg: 0-15 (how much inward lean)\n"
            "- hull.transom_style: vertical | raked | stepped (stern shape)\n"
            "- hull.panel_style: smooth | faceted (surface finish)\n"
            "- hull.bow_half_angle_deg: 12-35 (sharpness of bow entry)\n"
            "\n"
            "Hull Style Presets (use when user describes aesthetic intent):\n"
            "\n"
            "AGGRESSIVE_PATROL: For 'military', 'tactical', 'intimidating', 'aggressive', 'stealth'\n"
            "  → bow_style=wedge, chine_type=hard, spray_rail_count=3\n"
            "  → tumblehome_enabled=true, tumblehome_angle_deg=8, panel_style=smooth\n"
            "\n"
            "RUGGED_WORKBOAT: For 'industrial', 'practical', 'aluminum', 'rugged', 'workboat'\n"
            "  → bow_style=traditional, chine_type=hard, spray_rail_count=1\n"
            "  → tumblehome_enabled=false, panel_style=faceted\n"
            "\n"
            "SLEEK_PERFORMANCE: For 'racing', 'speed', 'sport', 'fast', 'sleek', 'offshore'\n"
            "  → bow_style=axe, chine_type=double, spray_rail_count=4\n"
            "  → transom_style=stepped, panel_style=smooth, bow_half_angle_deg=12\n"
            "\n"
            "Feature Proposal Rules:\n"
            "- If user mentions style keywords, propose the FULL feature set for that style.\n"
            "- You MAY mix or override individual features based on additional context.\n"
            "- If user says 'aggressive patrol boat', propose BOTH dimensions AND style features.\n"
            "- Feature paths are in REFINABLE_SCHEMA and follow the same rules as numeric paths.\n"
            "\n"
            "Example - user says 'Design an aggressive 12m patrol boat':\n"
            "{\n"
            "  \"actions\": [\n"
            "    {\"action_type\": \"set\", \"path\": \"hull.loa\", \"value\": 12, \"unit\": \"m\"},\n"
            "    {\"action_type\": \"set\", \"path\": \"hull.hull_type\", \"value\": \"planing\"},\n"
            "    {\"action_type\": \"set\", \"path\": \"hull.bow_style\", \"value\": \"wedge\"},\n"
            "    {\"action_type\": \"set\", \"path\": \"hull.chine_type\", \"value\": \"hard\"},\n"
            "    {\"action_type\": \"set\", \"path\": \"hull.spray_rail_count\", \"value\": 3},\n"
            "    {\"action_type\": \"set\", \"path\": \"hull.tumblehome_enabled\", \"value\": true},\n"
            "    {\"action_type\": \"set\", \"path\": \"hull.tumblehome_angle_deg\", \"value\": 8},\n"
            "    {\"action_type\": \"run_phases\", \"phases\": [\"hull\"]}\n"
            "  ]\n"
            "}\n"
            "\n"
            "=== END HULL STYLE VOCABULARY ===\n"
            "\n"
            "Rules:\n"
            "- For set/increase/decrease: path MUST be one of the refinable paths above.\n"
            "- For run_phases: do not include path; include phases (e.g., [\"hull\"]).\n"
            "- For query: do not include path; include query_target and optional query_params.\n"
            "- For enum/bool fields: use set.\n"
            "- For relative numeric changes: use increase/decrease with either bucket OR amount+unit.\n"
            "- If ambiguous, prefer bucket=normal.\n"
            "- If you cannot map the request to the valid paths, return an empty actions list.\n"
        )

    def _maybe_log_prompt_verification(system_prompt: str) -> None:
        """
        P0 verification helper: remove once prompt schema coverage is confirmed.
        Enable via MAGNET_LLM_PROMPT_DEBUG=true.
        """
        try:
            if os.getenv("MAGNET_LLM_PROMPT_DEBUG", "false").lower() != "true":
                return

            def _snippet(needle: str, window: int = 220) -> str:
                idx = system_prompt.find(needle)
                if idx < 0:
                    return ""
                start = max(0, idx - window)
                end = min(len(system_prompt), idx + window)
                return system_prompt[start:end]

            has_hull_type = "hull.hull_type" in system_prompt
            logger.info(f"[intent_preview] prompt_contains_hull.hull_type={has_hull_type}")
            if has_hull_type:
                logger.info("[intent_preview] prompt_snippet_hull.hull_type:\n" + _snippet("hull.hull_type"))

            has_hull_loa = "hull.loa" in system_prompt
            logger.info(f"[intent_preview] prompt_contains_hull.loa={has_hull_loa}")
            if has_hull_loa:
                logger.info("[intent_preview] prompt_snippet_hull.loa:\n" + _snippet("hull.loa"))
        except Exception as e:
            logger.debug(f"[intent_preview] prompt_verification_log_failed: {type(e).__name__}: {e}")

    def _compute_missing_required(approved_actions: list) -> list:
        """
        Compute missing gates for phases touched by approved actions (compound mode only).
        
        Constraint-Aware Completion v1.0: Also includes placeholder hull dimensions
        that need synthesis to be replaced with proportional values.
        """
        from magnet.core.phase_ownership import get_phase_for_path

        hypothetical = HypotheticalStateView(state_manager, approved_actions)

        target_phases = set()
        for a in approved_actions:
            path = getattr(a, "path", None)
            if not path:
                continue
            phase = get_phase_for_path(path)
            if phase:
                target_phases.add(phase)

        missing_required = []
        for phase in target_phases:
            missing_required.extend(check_gates_on_hypothetical(phase, hypothetical))

        # Constraint-Aware Completion v1.0: Add placeholder dimensions
        # These need synthesis to produce proportional values
        if hypothetical.contains_placeholders:
            for path in hypothetical.placeholders_found:
                missing_required.append({
                    "path": path,
                    "reason": f"{path} is a placeholder (ship-scale baseline). "
                              "Synthesis required to compute proportional dimensions from mission.",
                    "gate_name": "placeholder_needs_synthesis",
                    "synthesis_required": True,
                })

        # Dedupe by path
        seen = set()
        unique_missing = []
        for m in missing_required:
            if m.get("path") not in seen:
                unique_missing.append(m)
                seen.add(m.get("path"))
        return unique_missing

    def _compute_query_results(approved_actions: list) -> Optional[Dict[str, Any]]:
        """
        Compute QUERY results for approved query actions (preview-only; zero mutation).

        Returns:
            - None if no query actions
            - Dict keyed by query_target for one or more query actions
        """
        try:
            from magnet.kernel.intent_protocol import ActionType
            from magnet.kernel.analysis import HullAnalyzer
        except Exception:
            return None

        query_actions = [a for a in approved_actions if getattr(a, "action_type", None) == ActionType.QUERY]
        if not query_actions:
            return None

        analyzer = HullAnalyzer(state_manager)
        results: Dict[str, Any] = {}

        for qa in query_actions:
            target = getattr(qa, "query_target", None)
            if not target:
                continue
            if target == "hull.proportions":
                results[target] = analyzer.analyze_proportions()
            elif target == "hull.regime":
                results[target] = analyzer.analyze_regime()
            else:
                results[target] = {"error": f"Unknown query target: {target}"}

        return results or None

    async def _try_llm_first():
        if not llm_client or not _PYDANTIC_AVAILABLE:
            if not llm_client:
                logger.info("[intent_preview] llm_unavailable: llm_client=None")
            if not _PYDANTIC_AVAILABLE:
                logger.info("[intent_preview] llm_unavailable: pydantic_missing")
            return None
        # 67.7 debug: bypass is_available() as a hard gate and attempt the LLM call
        # to surface the real exception (availability checks can hide root causes).
        if hasattr(llm_client, "is_available"):
            try:
                available = llm_client.is_available()
                if not available:
                    logger.warning("[intent_preview] llm_is_available=false (bypassing gate; attempting call anyway)")
            except Exception as e:
                logger.exception(f"LLM availability check failed (bypassing gate): {type(e).__name__}: {e}")

        system_prompt = _build_translator_system_prompt()
        _maybe_log_prompt_verification(system_prompt)
        try:
            llm_response = await llm_client.complete_json(
                request.text,
                LLMProposals,
                system_prompt=system_prompt,
                options=LLMOptions(temperature=0),
            )
        except Exception as e:
            logger.exception(f"LLM call failed: {type(e).__name__}: {e}")
            return None

        proposals = getattr(llm_response, "actions", []) or []

        # Canonical hash for auditability
        try:
            canonical_json = llm_response.model_dump_json(sort_keys=True)
        except Exception:
            canonical_json = json.dumps(proposals, default=str, sort_keys=True)
        llm_output_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

        llm_actions = []
        for proposal in proposals:
            try:
                action_type = ActionType(proposal.action_type)
            except Exception:
                continue

            # Translator action surface (extended): allow read-only QUERY and RUN_PHASES trigger.
            if action_type not in (
                ActionType.SET,
                ActionType.INCREASE,
                ActionType.DECREASE,
                ActionType.RUN_PHASES,
                ActionType.QUERY,
            ):
                continue

            # ----------------------------------------------------------------
            # RUN_PHASES (no path)
            # ----------------------------------------------------------------
            if action_type == ActionType.RUN_PHASES:
                phases = getattr(proposal, "phases", None) or []
                if not isinstance(phases, list) or not phases:
                    continue
                llm_actions.append(Action(action_type=action_type, phases=phases))
                continue

            # ----------------------------------------------------------------
            # QUERY (no path)
            # ----------------------------------------------------------------
            if action_type == ActionType.QUERY:
                query_target = getattr(proposal, "query_target", None)
                if not query_target:
                    continue
                llm_actions.append(
                    Action(
                        action_type=action_type,
                        query_target=query_target,
                        query_params=getattr(proposal, "query_params", None),
                    )
                )
                continue

            # ----------------------------------------------------------------
            # SET / INCREASE / DECREASE (requires refinable path)
            # ----------------------------------------------------------------
            if not getattr(proposal, "path", None):
                continue

            path = normalize_path(proposal.path)
            if not is_refinable(path):
                continue

            if action_type in (ActionType.INCREASE, ActionType.DECREASE):
                bucket = proposal.bucket
                if not bucket and proposal.unit and str(proposal.unit).startswith("bucket:"):
                    _, _, bucket_token = str(proposal.unit).partition(":")
                    bucket = bucket_token or "normal"

                if bucket:
                    llm_actions.append(
                        Action(action_type=action_type, path=path, amount=None, unit=f"bucket:{bucket}")
                    )
                elif proposal.amount is not None:
                    llm_actions.append(
                        Action(
                            action_type=action_type,
                            path=path,
                            amount=proposal.amount,
                            unit=proposal.unit,
                        )
                    )
                else:
                    # Allow kernel to apply default bucket ("normal") for bucket-enabled paths
                    llm_actions.append(Action(action_type=action_type, path=path, amount=None, unit=None))

            elif action_type == ActionType.SET:
                if proposal.value is None:
                    continue
                llm_actions.append(
                    Action(
                        action_type=action_type,
                        path=path,
                        value=proposal.value,
                        unit=proposal.unit,
                    )
                )

        if not llm_actions:
            # Treat empty translation as "failed to translate" so deterministic fallback can try.
            logger.info("[intent_preview] llm_translated_no_usable_actions; falling back")
            return None

        llm_plan_id = f"llm_preview_{uuid.uuid4().hex[:8]}"
        llm_intent_id = f"llm_intent_{uuid.uuid4().hex[:8]}"
        llm_plan = ActionPlan(
            plan_id=llm_plan_id,
            intent_id=llm_intent_id,
            design_id=design_id,
            design_version_before=version_before,
            actions=llm_actions,
            proposed_at=datetime.now(timezone.utc),
        )

        llm_result = validator.validate(llm_plan, state_manager, check_stale=False)

        missing_required = _compute_missing_required(llm_result.approved) if mode == "compound" else []
        query_results = _compute_query_results(llm_result.approved)

        apply_payload = None
        allow_apply = os.getenv("MAGNET_CHAT_GUESS_APPLY", "true").lower() == "true"
        if llm_result.approved and allow_apply:
            # QUERY is read-only; it should not be sent to /actions.
            apply_actions = [a for a in llm_result.approved if getattr(a, "action_type", None) != ActionType.QUERY]
            if apply_actions:
                apply_payload = {
                    "plan_id": llm_plan_id,
                    "intent_id": llm_intent_id,
                    "design_version_before": state_manager.design_version,
                    "actions": _serialize_actions(apply_actions),
                }

        if not llm_result.approved:
            intent_status = "blocked"
        elif missing_required:
            intent_status = "partial"
        else:
            intent_status = "complete"

        llm_meta = {
            "provider": getattr(getattr(llm_client, "provider", None), "name", None) or "llm_client",
            "model": getattr(getattr(llm_client, "provider", None), "model", None),
            "temperature": 0,
            "prompt_version": LLM_PROMPT_VERSION,
        }

        # Control Plane v1.1: Generate HSV projections with provenance
        hsv = HypotheticalStateView(state_manager, llm_result.approved)
        hsv_digest = hsv.to_digest()
        
        # Constraint-Aware Completion v1.0: Check if synthesis should be suggested
        synthesis_suggested = False
        synthesis_reason = None
        if hsv.contains_placeholders:
            # Check if we have enough constraints to synthesize
            has_loa = any(getattr(a, 'path', '') == 'hull.loa' for a in llm_result.approved) or \
                      state_manager.get("hull.loa") is not None
            has_hull_type = any(getattr(a, 'path', '') == 'hull.hull_type' for a in llm_result.approved) or \
                           state_manager.get("hull.hull_type") is not None
            if has_loa:
                synthesis_suggested = True
                synthesis_reason = (
                    f"Hull dimensions {list(hsv.placeholders_found)} are placeholders. "
                    "Run hull synthesis to compute proportional dimensions based on mission constraints."
                )

        resp = {
            "preview": True,
            "intent_mode": mode,
            "plan_id": llm_plan_id,
            "intent_id": llm_intent_id,
            "design_version_before": state_manager.design_version,
            "actions": _serialize_actions(llm_plan.actions),
            "approved": _serialize_actions(llm_result.approved),
            "query_results": query_results,
            "rejected": [
                {"action": {"path": a.path, "value": getattr(a, 'value', None)}, "reason": reason}
                for a, reason in llm_result.rejected
            ],
            "warnings": llm_result.warnings,
            "unsupported_mentions": unsupported_mentions,
            "missing_required": missing_required,
            "intent_status": intent_status,
            "provenance": "llm_guess",
            "llm_meta": llm_meta,
            "llm_output_sha256": llm_output_sha256,
            "apply_payload": apply_payload,
            # Control Plane v1.1: Provenance-tagged projections
            "projections": hsv_digest.get("projections", []),
            "stale_paths": hsv_digest.get("stale_paths", []),
            "contains_virtual_defaults": hsv_digest.get("contains_virtual_defaults", False),
            "virtual_defaults_used": hsv_digest.get("virtual_defaults_used", []),
            # Constraint-Aware Completion v1.0
            "contains_placeholders": hsv_digest.get("contains_placeholders", False),
            "placeholders_found": hsv_digest.get("placeholders_found", []),
            "synthesis_suggested": synthesis_suggested,
            "synthesis_reason": synthesis_reason,
        }

        # Preserve compound response shape expected by clients
        if mode == "compound":
            resp["proposed_actions"] = _serialize_actions(llm_plan.actions)
        return resp

    # === LLM-first ===
    llm_resp = await _try_llm_first()
    if llm_resp is not None:
        return llm_resp

    # === Deterministic fallback ===
    actions = []
    if mode == "compound":
        compound = extract_compound_intent(request.text)
        actions = compound["proposed_actions"]
        unsupported_mentions = compound.get("unsupported_mentions", [])
    else:
        actions = parse_intent_to_actions(request.text)

    logger.info(
        "[intent_preview] deterministic_fallback_extract",
        extra={
            "design_id": design_id,
            "mode": mode,
            "text": getattr(request, "text", ""),
            "det_actions": len(actions),
        },
    )

    if not actions:
        resp = {
            "preview": True,
            "intent_mode": mode,
            "plan_id": None,
            "intent_id": None,
            "design_version_before": state_manager.design_version,
            "actions": [],
            "approved": [],
            "rejected": [],
            "warnings": [],
            "unsupported_mentions": unsupported_mentions,
            "missing_required": [],
            "intent_status": "blocked",
            "provenance": "deterministic",
            "guidance": get_guidance_message(),
            "apply_payload": None,
            # Control Plane v1.1: Empty provenance when blocked
            "projections": [],
            "stale_paths": [],
            "contains_virtual_defaults": False,
            "virtual_defaults_used": [],
        }
        if mode == "compound":
            resp["proposed_actions"] = []
        return resp

    det_plan_id = f"det_preview_{uuid.uuid4().hex[:8]}"
    det_intent_id = f"det_intent_{uuid.uuid4().hex[:8]}"
    det_plan = ActionPlan(
        plan_id=det_plan_id,
        intent_id=det_intent_id,
        design_id=design_id,
        design_version_before=version_before,
        actions=actions,
        proposed_at=datetime.now(timezone.utc),
    )

    det_result = validator.validate(det_plan, state_manager, check_stale=False)
    missing_required = _compute_missing_required(det_result.approved) if mode == "compound" else []

    apply_payload = None
    if det_result.approved:
        apply_actions = [a for a in det_result.approved if getattr(a, "action_type", None) != ActionType.QUERY]
        if apply_actions:
            apply_payload = {
                "plan_id": det_plan_id,
                "intent_id": det_intent_id,
                "design_version_before": state_manager.design_version,
                "actions": _serialize_actions(apply_actions),
            }

    if not det_result.approved:
        intent_status = "blocked"
    elif missing_required:
        intent_status = "partial"
    else:
        intent_status = "complete"

    # Control Plane v1.1: Generate HSV projections with provenance
    hsv = HypotheticalStateView(state_manager, det_result.approved)
    hsv_digest = hsv.to_digest()

    resp = {
        "preview": True,
        "intent_mode": mode,
        "plan_id": det_plan_id if det_result.approved else None,
        "intent_id": det_intent_id if det_result.approved else None,
        "design_version_before": state_manager.design_version,
        "actions": _serialize_actions(det_plan.actions),
        "approved": _serialize_actions(det_result.approved),
        "rejected": [
            {"action": {"path": a.path, "value": getattr(a, 'value', None)}, "reason": reason}
            for a, reason in det_result.rejected
        ],
        "warnings": det_result.warnings,
        "unsupported_mentions": unsupported_mentions,
        "missing_required": missing_required,
        "intent_status": intent_status,
        "provenance": "deterministic",
        "apply_payload": apply_payload,
        # Control Plane v1.1: Provenance-tagged projections
        "projections": hsv_digest.get("projections", []),
        "stale_paths": hsv_digest.get("stale_paths", []),
        "contains_virtual_defaults": hsv_digest.get("contains_virtual_defaults", False),
        "virtual_defaults_used": hsv_digest.get("virtual_defaults_used", []),
    }
    if mode == "compound":
        resp["proposed_actions"] = _serialize_actions(det_plan.actions)
    return resp


def create_fastapi_app(context: "AppContext" = None):
    """
    Create FastAPI application with full integration.

    Args:
        context: Application context with config and container

    Returns:
        FastAPI application instance
    """
    try:
        from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect, File, UploadFile, Form
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
        from fastapi.staticfiles import StaticFiles
    except ImportError:
        logger.warning("FastAPI not installed, creating stub app")
        return _create_stub_app()

    from .websocket import ConnectionManager, WSMessage, get_connection_manager
    from .worker import submit_job, get_job_status, JobPriority

    # Configuration
    enable_docs = True
    docs_url = "/docs"
    cors_origins = ["*"]

    # TASK-007: Legacy Intent→Action protocol REMOVED.
    # Spiral endpoints (/spiral/chat, /spiral/apply) are the single authority.
    # Legacy endpoints now return 410 Gone with migration instructions.
    # 
    # Migration: Replace calls to:
    #   POST /api/v1/designs/{id}/intent/preview  → POST /api/v1/designs/{id}/spiral/chat
    #   POST /api/v1/designs/{id}/actions         → POST /api/v1/designs/{id}/spiral/apply
    legacy_intent_enabled = False  # Permanently disabled

    if context and context.config:
        if hasattr(context.config, 'api'):
            enable_docs = getattr(context.config.api, 'enable_docs', True)
            docs_url = getattr(context.config.api, 'docs_url', '/docs')
            cors_origins = getattr(context.config.api, 'cors_origins', ['*'])

    app = FastAPI(
        title="MAGNET API",
        description="Ship Design Validation System API",
        version="1.1.0",
        docs_url=docs_url if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # WebSocket manager
    ws_manager = get_connection_manager()

    # =========================================================================
    # Wire Geometry Router (Intent→Action Protocol integration)
    # =========================================================================

    try:
        from magnet.webgl.api_endpoints import create_geometry_router

        def state_manager_getter(design_id: str):
            """
            Get StateManager for geometry endpoints (design-scoped).

            IMPORTANT: Geometry endpoints must operate on the DesignStore-backed
            StateManager for the requested design_id. Do NOT use a global/container
            StateManager here, or multi-design + spiral resources will desync.
            """
            try:
                from magnet.deployment.design_store import DesignStore, DesignNotFound
                store = DesignStore(context.container if context else None)
                return store.load(design_id)
            except DesignNotFound:
                return None
            except Exception as e:
                logger.warning(f"Could not load StateManager for geometry (design={design_id}): {e}")
                return None

        geometry_router = create_geometry_router(state_manager_getter)
        app.include_router(geometry_router)
        logger.info("Geometry router wired successfully")
    except Exception as e:
        logger.warning(f"Could not wire geometry router: {e}")

    # =========================================================================
    # Wire Orphaned Routers (Phase 0.1 - MAGNET_Merge_Implementation_Plan.md)
    # These routers existed but were not mounted. Now wired for design spiral.
    # =========================================================================

    # Agents router - clarification system for human-in-the-loop
    try:
        from magnet.agents.api_endpoints import create_agents_router
        from magnet.agents.clarification import ClarificationManager

        # Get or create clarification manager
        clarification_manager = None
        if context and context.container:
            try:
                clarification_manager = context.container.resolve(ClarificationManager)
            except Exception:
                clarification_manager = ClarificationManager()

        agents_router = create_agents_router(clarification_manager)
        if agents_router:
            app.include_router(agents_router, prefix="/api/v1/agents", tags=["agents"])
            logger.info("Agents router mounted successfully")
    except Exception as e:
        logger.warning(f"Could not mount agents router: {e}")

    # Interior router - interior layout generation
    try:
        from magnet.interior.api_endpoints import create_interior_router
        from magnet.interior.integration.state_integration import InteriorStateIntegrator

        # Create state integrator if possible
        state_integrator = None
        try:
            if context and context.container:
                from magnet.core.state_manager import StateManager
                sm = context.container.resolve(StateManager)
                state_integrator = InteriorStateIntegrator(sm)
        except Exception:
            pass

        interior_router = create_interior_router(state_integrator)
        if interior_router:
            app.include_router(interior_router, prefix="/api/v1/interior", tags=["interior"])
            logger.info("Interior router mounted successfully")
    except Exception as e:
        logger.warning(f"Could not mount interior router: {e}")

    # Routing router - systems routing (fuel, electrical, HVAC)
    try:
        from magnet.routing.integration.api_endpoints import create_routing_router
        from magnet.routing.integration.state_integration import RoutingStateIntegrator

        # Create state integrator if possible
        routing_state_integrator = None
        try:
            if context and context.container:
                from magnet.core.state_manager import StateManager
                sm = context.container.resolve(StateManager)
                routing_state_integrator = RoutingStateIntegrator(sm)
        except Exception:
            pass

        routing_router = create_routing_router(routing_state_integrator)
        if routing_router:
            app.include_router(routing_router, prefix="/api/v1/routing", tags=["routing"])
            logger.info("Routing router mounted successfully")
    except Exception as e:
        logger.warning(f"Could not mount routing router: {e}")

    # =========================================================================
    # §SKELETON:WireRouter - Spiral Endpoints (design-scoped, persistent)
    # =========================================================================

    try:
        from magnet.deployment.spiral_endpoints import create_spiral_router
        from magnet.deployment.design_store import DesignStore

        def spiral_state_manager_getter(design_id: str):
            """Get StateManager for spiral endpoints via DesignStore."""
            try:
                store = DesignStore(context.container if context else None)
                if store.exists(design_id):
                    return store.load(design_id)
            except Exception as e:
                logger.warning(f"Could not load design {design_id} for spiral: {e}")
            return None

        spiral_router = create_spiral_router(
            get_state_manager=spiral_state_manager_getter,
            ws_manager=ws_manager,
        )
        app.include_router(spiral_router)
        logger.info("Spiral router wired successfully")
    except Exception as e:
        logger.warning(f"Could not mount spiral router: {e}")

    # =========================================================================
    # Dependencies
    # =========================================================================

    def get_state_manager(design_id: str = None, request: "Request" = None):
        # FastAPI should inject path params into dependency args by name, but in practice
        # some call sites (and nested dependency chains) end up calling this without
        # design_id. Fall back to reading the design_id from the incoming request.
        if not design_id and request is not None:
            try:
                design_id = (request.path_params or {}).get("design_id")
            except Exception:
                design_id = design_id
        try:
            from magnet.core.state_manager import StateManager
            from magnet.deployment.design_store import DesignStore, DesignNotFound
        except Exception:
            return None

        # Design-scoped load (works with or without DI container).
        if design_id:
            try:
                store = DesignStore(context.container if (context and context.container) else None)
                return store.load(design_id)
            except DesignNotFound:
                return None
            except Exception as e:
                logger.warning(f"Could not load StateManager for design {design_id}: {e}")
                return None

        # Container-scoped fallback (only available when bootstrapped).
        if context and context.container:
            try:
                return context.container.resolve(StateManager)
            except Exception as e:
                logger.warning(f"Could not resolve StateManager: {e}")
                return None

        return None

    def get_conductor():
        if context and context.container:
            try:
                from magnet.kernel.conductor import Conductor
                return context.container.resolve(Conductor)
            except Exception as e:
                logger.warning(f"Could not resolve Conductor: {e}")
        return None

    def get_phase_machine():
        if context and context.container:
            try:
                from magnet.core.phase_states import PhaseMachine
                return context.container.resolve(PhaseMachine)
            except Exception as e:
                logger.warning(f"Could not resolve PhaseMachine: {e}")
        return None

    def get_vision():
        if context and context.container:
            try:
                from magnet.vision.router import VisionRouter
                return context.container.resolve(VisionRouter)
            except Exception as e:
                logger.warning(f"Could not resolve VisionRouter: {e}")
        return None

    def get_pipeline_executor():
        """Get configured PipelineExecutor from DI container."""
        if context and context.container:
            try:
                from magnet.validators.executor import PipelineExecutor
                return context.container.resolve(PipelineExecutor)
            except Exception as e:
                logger.warning(f"Could not resolve PipelineExecutor: {e}")
        return None

    def get_validator_topology():
        """Get ValidatorTopology from DI container."""
        if context and context.container:
            try:
                from magnet.validators.topology import ValidatorTopology
                return context.container.resolve(ValidatorTopology)
            except Exception as e:
                logger.warning(f"Could not resolve ValidatorTopology: {e}")
        return None

    def get_result_aggregator():
        """Get ResultAggregator from DI container."""
        if context and context.container:
            try:
                from magnet.validators.aggregator import ResultAggregator
                return context.container.resolve(ResultAggregator)
            except Exception as e:
                logger.warning(f"Could not resolve ResultAggregator: {e}")
        return None

    def _build_design_scoped_pipeline(state_manager):
        """
        Build a design-scoped validator pipeline bound to the provided StateManager.

        IMPORTANT:
        - ValidatorTopology is definition-only and can be reused.
        - PipelineExecutor MUST be created per request because it binds state_manager.
        """
        from magnet.validators.topology import ValidatorTopology
        from magnet.validators.registry import ValidatorRegistry
        from magnet.validators.executor import PipelineExecutor
        from magnet.validators.aggregator import ResultAggregator

        # Ensure validator instances exist (implementations wired to IDs)
        try:
            if not ValidatorRegistry.get_all_instances():
                ValidatorRegistry.initialize_defaults()
                ValidatorRegistry.instantiate_all()
        except Exception as e:
            logger.warning(f"ValidatorRegistry init: {e}")

        # Always build a fresh topology from the authoritative builtin registry.
        # (Avoids DI/container-cached topology drift across reloads/workers.)
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        executor = PipelineExecutor(
            topology=topology,
            state_manager=state_manager,
            validator_registry=ValidatorRegistry.get_all_instances(),
            design_id=getattr(getattr(state_manager, "state", None), "design_id", None),
        )
        aggregator = ResultAggregator(topology=topology, state_manager=state_manager)

        # Seed cross-phase completion tracking from persisted design state so that
        # validators in later phases can run even when their dependencies were completed
        # in earlier phase requests (e.g., weight depends on physics/hydrostatics from hull).
        try:
            completed = state_manager.get("orchestration.completed_validators")
            if isinstance(completed, list) and completed:
                executor._all_completed_validators = set(str(x) for x in completed if x)  # type: ignore[attr-defined]
        except Exception:
            pass

        return executor, aggregator

    def get_action_validator():
        """Get ActionPlanValidator for action validation."""
        try:
            from magnet.kernel.action_validator import ActionPlanValidator
            return ActionPlanValidator()
        except Exception as e:
            logger.warning(f"Could not create ActionPlanValidator: {e}")
        return None

    def get_action_executor(design_id: str = None, request: "Request" = None):
        """Get ActionExecutor for action execution."""
        state_manager = get_state_manager(design_id=design_id, request=request)
        if not state_manager:
            return None
        try:
            from magnet.kernel.action_executor import ActionExecutor
            from magnet.kernel.event_dispatcher import EventDispatcher
            dispatcher = EventDispatcher(design_id=getattr(state_manager._state, 'design_id', ''))
            return ActionExecutor(state_manager, dispatcher)
        except Exception as e:
            logger.warning(f"Could not create ActionExecutor: {e}")
        return None

    def get_event_dispatcher():
        """Get EventDispatcher instance."""
        state_manager = get_state_manager()
        design_id = ""
        if state_manager:
            design_id = getattr(state_manager._state, 'design_id', '')
        try:
            from magnet.kernel.event_dispatcher import EventDispatcher
            return EventDispatcher(design_id=design_id)
        except Exception as e:
            logger.warning(f"Could not create EventDispatcher: {e}")
        return None

    def get_llm_client():
        """Get LLMClient via DI (fallback compiler)."""
        if context and context.container:
            try:
                from magnet.agents.llm_client import LLMClient
                return context.container.resolve(LLMClient)
            except Exception as e:
                logger.warning(f"Could not resolve LLMClient: {e}")
        return None

    # =========================================================================
    # Startup/Shutdown (fixes blocker #5)
    # =========================================================================

    @app.on_event("startup")
    async def startup():
        logger.info("API server starting")
        
        # Register calculators with cascade executor
        try:
            from magnet.dependencies.calculator_registry_init import create_registry_and_register
            # Create and register calculators (stored as module-level for now)
            global _calculator_registry
            _calculator_registry = create_registry_and_register()
            logger.info("✅ Calculator registry initialized")
        except Exception as e:
            logger.error(f"Failed to initialize calculator registry: {e}")
            # Non-fatal - continue startup
        
        # v1.1: Launch WebSocket message processor (fixes blocker #5)
        asyncio.create_task(ws_manager.process_messages())
        logger.info("WebSocket message processor started")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("API server stopping")
        await ws_manager.shutdown()

    # =========================================================================
    # Health Endpoints
    # =========================================================================

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "1.1.0",
            "websocket_clients": ws_manager.client_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @app.get("/ready")
    async def readiness_check(
        state_manager=Depends(get_state_manager),
    ):
        """Readiness check endpoint."""
        checks = {
            "state_manager": state_manager is not None,
        }

        if context and context.container:
            try:
                from magnet.kernel.conductor import Conductor
                context.container.resolve(Conductor)
                checks["conductor"] = True
            except Exception:
                checks["conductor"] = False

        return {
            "ready": all(checks.values()),
            "checks": checks,
        }

    # =========================================================================
    # Module 65.2: Meta endpoint for UI auto-configuration
    # =========================================================================

    @app.get("/api/v1/meta")
    async def get_meta():
        """Return server capabilities for UI auto-configuration."""
        return {
            "version": "1.2.0",
            "capabilities": ["compound_intent", "glb_export", "websocket"],
            "endpoints": {
                "designs": "/api/v1/designs",
                "health": "/health",
                "ws": "/ws/{design_id}"
            }
        }

    # =========================================================================
    # Design Endpoints with PhaseMachine integration (fixes blocker #11)
    # =========================================================================

    @app.get("/api/v1/designs")
    async def list_designs(
        state_manager=Depends(get_state_manager),
    ):
        """List all designs from DesignStore (design-scoped, persisted)."""
        # Unit-test mode (create_fastapi_app(None)) expects this endpoint to exist
        # and return an empty list (not to hit the real filesystem).
        if not context or not getattr(context, "container", None):
            return {"designs": []}
        try:
            from magnet.deployment.design_store import DesignStore
            store = DesignStore(context.container if context else None)
            designs: list[dict] = []
            for did in store.list_designs():
                try:
                    sm = store.load(did)
                    from magnet.ui.utils import get_state_value
                    designs.append(
                        {
                            "design_id": did,
                            "name": get_state_value(sm, "metadata.name", "Untitled"),
                            "created_at": get_state_value(sm, "metadata.created_at"),
                        }
                    )
                except Exception:
                    designs.append({"design_id": did, "name": "Untitled", "created_at": None})
            return {"designs": designs}
        except Exception:
            # Fallback: return empty (UI will create a new design)
            return {"designs": []}

    @app.post("/api/v1/designs")
    async def create_design(
        design: DesignCreate,
        phase_machine=Depends(get_phase_machine),
    ):
        """Create a new design."""
        import uuid
        from magnet.ui.utils import set_state_value, set_phase_status

        # IMPORTANT: designs are design-scoped and must be persisted to DesignStore.
        # Do NOT rely on a single container-resolved global StateManager here.
        try:
            from magnet.core.state_manager import StateManager
            from magnet.deployment.design_store import DesignStore
        except Exception:
            raise HTTPException(status_code=503, detail="StateManager not available")

        # Generate an ID with enough entropy to avoid collisions.
        # Also avoid overwriting an existing design file (single authority: no silent merges).
        store = None
        try:
            store = DesignStore(context.container if context else None)
        except Exception:
            store = None

        design_id = None
        for _ in range(10):
            candidate = f"MAGNET-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            try:
                if store and store.exists(candidate):
                    continue
            except Exception:
                pass
            design_id = candidate
            break
        if not design_id:
            design_id = f"MAGNET-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex.upper()}"

        sm = StateManager()

        # Canonical identity fields (top-level) + metadata mirrors.
        # Keep these in sync so all modules can reliably identify the design.
        # NOTE: This is identity wiring, not design recognition.
        set_state_value(sm, "design_id", design_id, "api")
        set_state_value(sm, "design_name", design.name, "api")

        set_state_value(sm, "metadata.design_id", design_id, "api")
        set_state_value(sm, "metadata.name", design.name, "api")
        set_state_value(sm, "metadata.created_at", datetime.now(timezone.utc).isoformat(), "api")

        # New designs should start BLANK (no legacy geometry fallback).
        # Geometry should come from design-language resources via spiral chat/sketch.
        set_state_value(sm, "metadata.legacy_geometry_fallback_enabled", False, "api")

        # Truthfulness: new blank designs must never inherit an old truth badge.
        # Start in DECOUPLED until geometry+physics are explicitly generated and validated.
        try:
            set_state_value(sm, "simulation_integrity", "DECOUPLED", "api")
            set_state_value(sm, "metadata.simulation_integrity", "DECOUPLED", "api")
        except Exception:
            pass

        if design.vessel_type:
            set_state_value(sm, "mission.vessel_type", design.vessel_type, "api")

        if design.mission:
            for key, value in design.mission.items():
                set_state_value(sm, f"mission.{key}", value, "api")

        # NOTE: We intentionally do NOT seed hull.* placeholder dimensions for blank designs.
        # This prevents accidental legacy/visual-only hull generation on load.

        # v1.1: Initialize phases via PhaseMachine (fixes blocker #11)
        phases = ["mission", "hull_form", "structure", "propulsion",
                  "systems", "weight_stability", "compliance", "production"]

        # Apply phase initialization to the design-scoped state manager
        if phase_machine:
            try:
                phase_machine.initialize_design(design_id)
            except Exception as e:
                logger.warning(f"PhaseMachine init: {e}")
                for phase in phases:
                    set_phase_status(sm, phase, "pending", "api")
        else:
            for phase in phases:
                set_phase_status(sm, phase, "pending", "api")

        # Persist to DesignStore (single authority for GET /designs/{id} and spiral endpoints)
        try:
            if store is None:
                store = DesignStore(context.container if context else None)
            store.save(design_id, state_manager=sm)
        except Exception as e:
            logger.warning(f"Failed to persist new design {design_id}: {e}")

        # Notify WebSocket clients
        ws_manager.queue_message(WSMessage(
            type="design_created",
            design_id=design_id,
            payload={"name": design.name},
        ))

        return {"design_id": design_id, "name": design.name}

    @app.get("/api/v1/designs/{design_id}")
    async def get_design(
        design_id: str,
        include_provenance: str = "full",
        state_manager=Depends(get_state_manager),
    ):
        """
        Get design details (design-scoped).

        IMPORTANT: Do not depend on a global/container StateManager here.
        Always load by design_id via DesignStore to avoid "StateManager not available" failures.
        """
        from magnet.deployment.design_store import DesignStore, DesignNotFound
        from magnet.ui.utils import serialize_state

        try:
            store = DesignStore(context.container if context else None)
            sm = store.load(design_id)
        except DesignNotFound:
            raise HTTPException(status_code=404, detail="Design not found")
        except Exception as e:
            logger.warning(f"Failed to load design {design_id}: {e}")
            raise HTTPException(status_code=500, detail="Failed to load design")

        # Additive-only: keep the existing nested payload for legacy/UI consumers,
        # but also attach the canonical Walking Trail `state` map + corresponding `provenance`.
        payload = serialize_state(sm)
        try:
            if isinstance(payload, dict):
                if hasattr(sm, "export_state_flat"):
                    state_flat = sm.export_state_flat(include_metadata=False)
                    # Expand canonical aliases into the flat map for API consumers.
                    # (Many parts of the system use canonical keys like hull.bm_m even when the
                    # underlying stored field is a legacy/dataclass name like hull.bmt.)
                    try:
                        from magnet.core.field_aliases import FIELD_ALIASES
                        if isinstance(state_flat, dict):
                            for alias, target in (FIELD_ALIASES or {}).items():
                                if alias not in state_flat and target in state_flat:
                                    state_flat[alias] = state_flat.get(target)
                    except Exception:
                        pass
                    payload["state"] = state_flat
                    if hasattr(sm, "export_api_provenance"):
                        payload["provenance"] = sm.export_api_provenance(state_flat, include=include_provenance)
                        payload["provenance_mode"] = include_provenance
        except Exception as e:
            logger.warning(f"Failed to attach provenance for design {design_id}: {e}")

        # Ensure response is strict-JSON safe (no NaN/Infinity).
        def _sanitize(obj: Any) -> Any:
            if isinstance(obj, float):
                return obj if math.isfinite(obj) else None
            if isinstance(obj, dict):
                return {k: _sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_sanitize(v) for v in obj]
            if isinstance(obj, tuple):
                return [_sanitize(v) for v in obj]
            return obj

        return _sanitize(payload)

    @app.patch("/api/v1/designs/{design_id}")
    async def update_design(
        design_id: str,
        update: DesignUpdate,
        state_manager=Depends(get_state_manager),
        phase_machine=Depends(get_phase_machine),
        validator=Depends(get_action_validator),
        executor=Depends(get_action_executor),
    ):
        """
        Update design value via Intent→Action Protocol.

        Routes through:
        1. ActionPlanValidator (REFINABLE_SCHEMA check, unit conversion, bounds)
        2. ActionExecutor (transactional execution, event emission)
        3. StateManager.commit() (design_version increment)

        Module 62 P0.1: Closed bypass route - no longer uses set_state_value()
        """
        import uuid
        from magnet.ui.utils import get_state_value
        from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
        from magnet.kernel.action_validator import StalePlanError

        # === BOUNDARY CHECK: Reject non-refinable paths at API level ===
        # Audit P0-4: Fail fast FIRST, before any other checks
        from magnet.core.refinable_schema import is_refinable
        if not is_refinable(update.path):
            raise HTTPException(
                status_code=400,
                detail={"error": "not_refinable", "path": update.path,
                        "message": f"Path '{update.path}' is not refinable via PATCH. "
                                   f"Only paths in REFINABLE_SCHEMA can be modified."}
            )
        # === END BOUNDARY CHECK ===

        # Verify dependencies
        if not state_manager:
            raise HTTPException(status_code=404, detail="Design not found")
        if not validator:
            raise HTTPException(status_code=503, detail="ActionPlanValidator not available")
        if not executor:
            raise HTTPException(status_code=503, detail="ActionExecutor not available")

        # Verify design exists
        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        # Build Action from PATCH payload
        action = Action(
            action_type=ActionType.SET,
            path=update.path,
            value=update.value,
        )

        # Create ActionPlan
        plan = ActionPlan(
            plan_id=f"patch_{uuid.uuid4().hex[:8]}",
            intent_id=f"patch_intent_{uuid.uuid4().hex[:8]}",
            design_id=design_id,
            design_version_before=state_manager.design_version,
            actions=[action],
            proposed_at=datetime.now(timezone.utc),
        )

        # Validate through ActionPlanValidator
        try:
            validation_result = validator.validate(plan, state_manager)
        except StalePlanError as e:
            raise HTTPException(
                status_code=409,
                detail={"error": "stale_plan", "message": str(e)}
            )

        if validation_result.has_rejections:
            rejection = validation_result.rejected[0]
            raise HTTPException(
                status_code=400,
                detail={"error": "validation_failed", "path": rejection[0].path, "reason": rejection[1]}
            )

        # Execute through ActionExecutor (owns transaction)
        exec_result = executor.execute(validation_result.approved, plan)
        if not exec_result.success:
            raise HTTPException(
                status_code=500,
                detail={"error": "execution_failed", "errors": exec_result.errors}
            )

        # Persist to DesignStore (the lake)
        # PATCH now flows through the same persistence path as POST /designs,
        # POST /spiral/chat, and POST /spiral/apply
        from magnet.deployment.design_store import DesignStore, VersionConflictError
        try:
            store = DesignStore(context.container if context else None)
            new_version = store.save(
                design_id,
                state_manager=state_manager,
                expected_version=int(plan.design_version_before),
            )
        except VersionConflictError as e:
            raise HTTPException(status_code=409, detail=e.to_dict())
        except Exception as e:
            logger.warning(f"Failed to persist PATCH for {design_id}: {e}")
            new_version = exec_result.design_version_after

        # Trigger dependency invalidation
        affected_phases = []
        if phase_machine:
            try:
                affected_phases = phase_machine.invalidate_dependents(update.path)
                if affected_phases:
                    logger.info(f"Invalidated phases: {affected_phases}")
            except Exception as e:
                logger.warning(f"Invalidation: {e}")

        # Notify clients
        ws_manager.queue_message(WSMessage(
            type="design_updated",
            design_id=design_id,
            payload={
                "path": update.path,
                "design_version": exec_result.design_version_after,
                "affected_phases": affected_phases,
            },
        ))

        return {
            "path": update.path,
            "value": update.value,
            "design_version_before": exec_result.design_version_before,
            "design_version_after": int(new_version),
            "affected_phases": affected_phases,
            "warnings": validation_result.warnings,
        }

    @app.delete("/api/v1/designs/{design_id}")
    async def delete_design(
        design_id: str,
        state_manager=Depends(get_state_manager),
    ):
        """Delete/reset design."""
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        # Reset state (in-memory only)
        try:
            state_manager.reset()
        except Exception:
            pass

        ws_manager.queue_message(WSMessage(
            type="design_deleted",
            design_id=design_id,
        ))

        return {"status": "deleted", "design_id": design_id}

    # =========================================================================
    # Actions Endpoint (Intent→Action Protocol) — DEPRECATED (TASK-007)
    # =========================================================================
    #
    # TASK-007: This endpoint is DEPRECATED and returns 410 Gone.
    # Use /spiral/apply instead.
    #
    # TASK-007: Legacy Intent→Action endpoint removed (single authority = Spiral).
    # Use POST /api/v1/designs/{design_id}/spiral/apply
    # @app.post("/api/v1/designs/{design_id}/actions")
    async def submit_actions(
        design_id: str,
        action_submit: ActionSubmit,
    ):
        """
        DEPRECATED: Use POST /api/v1/designs/{design_id}/spiral/apply instead.

        This endpoint has been removed as part of TASK-007 (Dual Control Plane Resolution).
        The Spiral protocol is now the single authority for design mutations.
        """
        raise HTTPException(
            status_code=410,
            detail={
                "error": "endpoint_deprecated",
                "message": "This endpoint has been removed. Use /spiral/apply instead.",
                "migration": "POST /api/v1/designs/{design_id}/spiral/apply",
            }
        )

        # Resolve dependencies lazily to allow 404 gating without dependency evaluation.
        state_manager = get_state_manager(design_id)
        validator = get_action_validator()
        executor = get_action_executor()

        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")
        if not validator:
            raise HTTPException(status_code=503, detail="ActionPlanValidator not available")
        if not executor:
            raise HTTPException(status_code=503, detail="ActionExecutor not available")

        # Verify design exists
        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            from magnet.kernel.intent_protocol import Action, ActionPlan, ActionType
            from magnet.kernel.action_validator import StalePlanError

            # Convert raw action dicts to Action objects
            actions = []
            for action_dict in action_submit.actions:
                action_type_str = action_dict.get("action_type", "set")
                try:
                    action_type = ActionType(action_type_str)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid action_type: {action_type_str}"
                    )

                action = Action(
                    action_type=action_type,
                    path=action_dict.get("path"),
                    value=action_dict.get("value"),
                    amount=action_dict.get("amount"),
                    unit=action_dict.get("unit"),
                    phases=action_dict.get("phases"),
                    format=action_dict.get("format"),
                    message=action_dict.get("message"),
                )
                actions.append(action)

            # Create ActionPlan
            plan = ActionPlan(
                plan_id=action_submit.plan_id,
                intent_id=action_submit.intent_id,
                design_id=design_id,
                design_version_before=action_submit.design_version_before,
                actions=actions,
                proposed_at=datetime.now(timezone.utc),
            )

            # Validate the plan
            try:
                validation_result = validator.validate(plan, state_manager)
            except StalePlanError as e:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "stale_plan",
                        "message": str(e),
                        "current_design_version": state_manager.design_version,
                    }
                )

            # Check for rejections
            if validation_result.has_rejections:
                return {
                    "success": False,
                    "plan_id": plan.plan_id,
                    "design_version": state_manager.design_version,
                    "approved_count": len(validation_result.approved),
                    "rejected_count": len(validation_result.rejected),
                    "rejections": [
                        {"path": action.path, "reason": reason}
                        for action, reason in validation_result.rejected
                    ],
                    "warnings": validation_result.warnings,
                }

            # Execute approved actions with raw intent (for ExplainRecord)
            raw_intent = getattr(action_submit, 'text', None) if hasattr(action_submit, 'text') else ""
            exec_result = executor.execute(
                validation_result.approved,
                plan,
                validation_result=validation_result,
                raw_intent=raw_intent or f"ActionPlan {plan.plan_id}",
            )

            # Notify WebSocket clients
            ws_manager.queue_message(WSMessage(
                type="actions_executed",
                design_id=design_id,
                payload={
                    "plan_id": plan.plan_id,
                    "actions_executed": exec_result.actions_executed,
                    "design_version": exec_result.design_version_after,
                    "explain_record_id": exec_result.explain_record_id,
                },
            ))
            
            # v1.1: Also emit explain_record_created event
            if exec_result.explain_record_id:
                ws_manager.queue_message(WSMessage(
                    type="explain_record_created",
                    design_id=design_id,
                    payload={
                        "record_id": exec_result.explain_record_id,
                        "design_version": exec_result.design_version_after,
                        "status": "committed" if exec_result.success else "aborted",
                    },
                ))

            return {
                "success": exec_result.success,
                "plan_id": plan.plan_id,
                "actions_executed": exec_result.actions_executed,
                "design_version_before": exec_result.design_version_before,
                "design_version_after": exec_result.design_version_after,
                "warnings": validation_result.warnings + exec_result.warnings,
                "errors": exec_result.errors,
                # v1.1: Control Plane audit trail
                "explain_record_id": exec_result.explain_record_id,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Action submission failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # Design Revert Endpoints (Undo / Restore Version)
    # =========================================================================

    @app.post("/api/v1/designs/{design_id}/undo")
    async def undo_design(
        design_id: str,
        state_manager=Depends(get_state_manager),
    ):
        """
        Revert to the previous committed design_version (design_version - 1).
        """
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        target_version = max(state_manager.design_version - 1, 0)
        if target_version == state_manager.design_version:
            raise HTTPException(status_code=400, detail="No previous version to revert to")

        success = False
        try:
            success = state_manager.revert_to_version(target_version)
        except Exception as e:
            logger.error(f"Undo failed: {e}")
            raise HTTPException(status_code=500, detail="Undo failed")

        if not success:
            raise HTTPException(status_code=404, detail="Target version not found")

        ws_manager.queue_message(WSMessage(
            type="design_reverted",
            design_id=design_id,
            payload={"design_version": target_version},
        ))

        return {
            "success": True,
            "design_version": state_manager.design_version,
        }

    @app.post("/api/v1/designs/{design_id}/versions/{version}/restore")
    async def restore_design_version(
        design_id: str,
        version: int,
        state_manager=Depends(get_state_manager),
    ):
        """
        Restore a specific design_version.
        """
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            version = int(version)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid version")

        try:
            success = state_manager.revert_to_version(version)
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise HTTPException(status_code=500, detail="Restore failed")

        if not success:
            raise HTTPException(status_code=404, detail="Version not found")

        ws_manager.queue_message(WSMessage(
            type="design_reverted",
            design_id=design_id,
            payload={"design_version": version},
        ))

        return {
            "success": True,
            "design_version": state_manager.design_version,
        }

    # =========================================================================
    # Intent Preview Endpoint — DEPRECATED (TASK-007)
    # =========================================================================
    # TASK-007: Legacy Intent→Action endpoint removed (single authority = Spiral).
    # Use POST /api/v1/designs/{design_id}/spiral/chat
    # @app.post("/api/v1/designs/{design_id}/intent/preview")
    async def preview_intent(
        design_id: str,
        request: IntentPreviewRequest,
    ):
        """
        DEPRECATED: Use POST /api/v1/designs/{design_id}/spiral/chat instead.

        This endpoint has been removed as part of TASK-007 (Dual Control Plane Resolution).
        The Spiral protocol is now the single authority for design mutations.
        """
        raise HTTPException(
            status_code=410,
            detail={
                "error": "endpoint_deprecated",
                "message": "This endpoint has been removed. Use /spiral/chat instead.",
                "migration": "POST /api/v1/designs/{design_id}/spiral/chat",
            }
        )

        # Resolve dependencies lazily to allow 404 gating without dependency evaluation.
        state_manager = get_state_manager(design_id)
        validator = get_action_validator()
        llm_client = get_llm_client()

        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")
        if not validator:
            raise HTTPException(status_code=503, detail="ActionPlanValidator not available")

        # Verify design exists
        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        # Module 65.1: Compound mode
        mode = getattr(request, 'mode', 'single') or 'single'
        try:
            return await _compile_intent_with_llm_fallback(
            design_id=design_id,
                request=request,
                state_manager=state_manager,
                validator=validator,
                mode=mode,
                llm_client=llm_client,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Preview error: {e}")
            raise HTTPException(status_code=500, detail=f"Preview error: {e}")

    # =========================================================================
    # Phase Endpoints with PhaseMachine integration (fixes blocker #11)
    # =========================================================================

    @app.get("/api/v1/designs/{design_id}/phases")
    async def list_phases(
        design_id: str,
        state_manager=Depends(get_state_manager),
    ):
        """List all phases and their status."""
        from magnet.ui.utils import get_phase_status

        phases = ["mission", "hull_form", "structure", "propulsion",
                  "systems", "weight_stability", "compliance", "production"]

        result = []
        for phase in phases:
            status = get_phase_status(state_manager, phase, "pending") if state_manager else "pending"
            result.append({"phase": phase, "status": status})

        return {"phases": result}

    @app.get("/api/v1/designs/{design_id}/phases/{phase}")
    async def get_phase(
        design_id: str,
        phase: str,
        state_manager=Depends(get_state_manager),
    ):
        """Get phase details."""
        from magnet.ui.utils import get_phase_status, get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        status = get_phase_status(state_manager, phase, "pending")
        phase_state = get_state_value(state_manager, f"phase_states.{phase}", {})

        return {
            "phase": phase,
            "status": status,
            "details": phase_state,
        }

    # Module 63: Phase ID mapping (UI names → kernel canonical names)
    PHASE_ID_MAP = {
        # Legacy UI/client phase names (compat only)
        "hull_form": "hull",
        "weight_stability": "weight",  # NOTE: stability is separate phase
        "mission_requirements": "mission",
        "structural_scantlings": "structure",
        "general_arrangement": "arrangement",
        # All other names pass through unchanged
    }

    def _map_phase_id(ui_phase: str) -> str:
        """Map UI phase name to kernel canonical phase ID."""
        return PHASE_ID_MAP.get(ui_phase, ui_phase)

    @app.post("/api/v1/designs/{design_id}/phases/{phase}/run")
    async def run_phase(
        design_id: str,
        phase: str,
        run_config: PhaseRun = PhaseRun(),
        phase_machine=Depends(get_phase_machine),
        state_manager=Depends(get_state_manager),
    ):
        """Run a single phase with PhaseMachine integration."""
        from magnet.ui.utils import set_phase_status

        # Module 63: Map UI phase name to kernel canonical name
        kernel_phase = _map_phase_id(phase)

        # v1.1: Check dependencies via PhaseMachine (fixes blocker #11)
        if phase_machine:
            try:
                if not phase_machine.can_start_phase(kernel_phase):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Phase '{phase}' dependencies not met"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"PhaseMachine check: {e}")

        if run_config.async_mode:
            # Submit as background job
            job_id = await submit_job(
                "run_phase",
                {"phase": kernel_phase},
                design_id=design_id,
            )
            return {"job_id": job_id, "phase": phase, "status": "submitted"}

        # Run synchronously (design-scoped + persisted)
        if state_manager:
            # Optimistic locking (narrow bridge): reject stale runs if provided.
            try:
                design_version_before = int(state_manager.get("design_version", 0) or 0)
            except Exception:
                design_version_before = 0

            if run_config.expected_version is not None and int(run_config.expected_version) != int(design_version_before):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "version_conflict",
                        "design_id": design_id,
                        "expected_version": int(run_config.expected_version),
                        "actual_version": int(design_version_before),
                        "message": "Design was modified by another request",
                    },
                )

            txn_id = None
            try:
                from magnet.kernel.conductor import Conductor
                from magnet.deployment.design_store import DesignStore, VersionConflictError

                # All kernel writes must be atomic and versioned.
                txn_id = state_manager.begin_transaction()

                conductor = Conductor(state_manager=state_manager)
                try:
                    executor, aggregator = _build_design_scoped_pipeline(state_manager)
                    conductor.set_pipeline_executor(executor)
                    conductor.set_result_aggregator(aggregator)
                except Exception as e:
                    logger.warning(f"Phase pipeline wiring unavailable (continuing): {e}")

                result = conductor.run_phase(kernel_phase)

                # If phase execution was blocked before any meaningful execution, do not commit.
                # (Keeps versions clean and avoids persisting no-op runs.)
                status_val = getattr(getattr(result, "status", None), "value", "")
                if status_val == "blocked":
                    try:
                        state_manager.rollback()
                    except Exception:
                        pass
                else:
                    # Persist cross-phase validator completion set for subsequent phases.
                    try:
                        completed = sorted(getattr(executor, "get_completed_validators")())
                        state_manager.set("orchestration.completed_validators", completed, "kernel/validator_pipeline")
                    except Exception:
                        pass

                    state_manager.commit()
                    store = DesignStore(context.container if (context and context.container) else None)
                    try:
                        store.save(design_id, state_manager=state_manager, expected_version=design_version_before)
                    except VersionConflictError as e:
                        # Roll back in-memory (best-effort) and surface 409.
                        raise HTTPException(status_code=409, detail=e.to_dict())

                ws_manager.queue_message(WSMessage(
                    type="phase_completed",
                    design_id=design_id,
                    payload={
                        "phase": phase,
                        "kernel_phase": kernel_phase,
                        "status": status_val or "completed",
                    },
                ))

                design_version_after = design_version_before
                try:
                    design_version_after = int(state_manager.get("design_version", design_version_before) or design_version_before)
                except Exception:
                    design_version_after = design_version_before

                return {
                    "phase": phase,
                    "kernel_phase": kernel_phase,
                    "status": status_val or "completed",
                    "design_version_before": int(design_version_before),
                    "design_version_after": int(design_version_after),
                    "result": result.to_dict() if hasattr(result, 'to_dict') else {},
                }
            except HTTPException:
                raise
            except Exception as e:
                try:
                    if getattr(state_manager, "in_transaction", lambda: False)():
                        state_manager.rollback()
                except Exception:
                    pass
                logger.error(f"Phase {phase} failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Fallback: just update status
        if state_manager:
            set_phase_status(state_manager, phase, "completed", "api")

        return {"phase": phase, "status": "completed"}

    @app.post("/api/v1/designs/{design_id}/phases/{phase}/validate")
    async def validate_phase(
        design_id: str,
        phase: str,
        config: ValidationRun = ValidationRun(),
        state_manager=Depends(get_state_manager),
    ):
        """Validate a specific phase using the configured pipeline executor."""
        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        # Module 63: Map UI phase name to kernel canonical name
        kernel_phase = _map_phase_id(phase)

        txn_started = False
        committed = False
        try:
            from magnet.deployment.design_store import DesignStore, VersionConflictError

            # optimistic lock (optional)
            try:
                design_version_before = int(state_manager.get("design_version", 0) or 0)
            except Exception:
                design_version_before = 0
            if config.expected_version is not None and int(config.expected_version) != int(design_version_before):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "version_conflict",
                        "design_id": design_id,
                        "expected_version": int(config.expected_version),
                        "actual_version": int(design_version_before),
                        "message": "Design was modified by another request",
                    },
                )

            executor, aggregator = _build_design_scoped_pipeline(state_manager)

            # Validate is read-only by default, but validators currently write derived outputs.
            # We always run in a transaction so we can rollback unless persistence is requested.
            state_manager.begin_transaction()
            txn_started = True

            # Run phase validation via single authority (Guardrail #2)
            execution_state = executor.execute_phase(kernel_phase)

            # Check phase output contract (Guardrail #1)
            from magnet.validators.contracts import check_phase_contract
            contract_result = check_phase_contract(kernel_phase, state_manager)

            # Get gate status
            gate_status = None
            if aggregator:
                try:
                    gate_status = aggregator.check_gate(kernel_phase, execution_state)
                except Exception as e:
                    logger.warning(f"Gate check failed: {e}")

            # Flatten findings for Contract 7/8 shaping
            all_findings = []
            for vid, vr in (execution_state.results or {}).items():
                if not vr or not hasattr(vr, "findings"):
                    continue
                for f in (vr.findings or []):
                    try:
                        all_findings.append((vid, f))
                    except Exception:
                        continue

            # Determine overall success (Gate vs Grade model):
            # - Only REQUIRED gate validators block can_advance
            # - Contract outputs still matter
            gate_allows = gate_status.can_advance if gate_status else True
            phase_success = bool(contract_result.satisfied and gate_allows)

            validators_passed = len([
                v for v, r in execution_state.results.items()
                if getattr(getattr(r, "state", None), "value", "") in ["passed", "warning"]
            ])

            # Contract 7: classify error response type
            # Missing inputs: validators often report "Missing required parameters: ..."
            missing_inputs = []
            for _vid, finding in all_findings:
                msg = getattr(finding, "message", "") or ""
                if "Missing required parameters:" in msg:
                    try:
                        tail = msg.split("Missing required parameters:", 1)[1].strip()
                        missing_inputs.extend([s.strip() for s in tail.split(",") if s.strip()])
                    except Exception:
                        continue

            # Gate vs grade:
            # - gate_failed: hydrostatics (required gate) blocks progression
            # - grade_warning: severe findings exist but can proceed with human decision
            has_severe_grade = any(getattr(f, "severity", None) and getattr(f.severity, "value", "") == "error" for _, f in all_findings)
            human_decision_required = bool(has_severe_grade and gate_allows and contract_result.satisfied)

            # Contract 8: suggested fixes
            suggested_fixes = []
            try:
                from magnet.validators.fix_generator import generate_fixes
                suggested_fixes = generate_fixes(findings=[f for _, f in all_findings], state_manager=state_manager)
            except Exception as e:
                logger.debug(f"Suggested fix generation skipped: {e}")

            ws_manager.queue_message(WSMessage(
                type="validation_completed",
                design_id=design_id,
                payload={
                    "phase": phase,
                    "kernel_phase": kernel_phase,
                    "passed": phase_success,
                },
            ))

            # Contract 7: error envelope (additive; keep existing keys for callers/tests)
            base_payload = {
                "status": "success" if phase_success else "failed",
                "phase": phase,
                "kernel_phase": kernel_phase,
                "passed": bool(phase_success),
                "validators_run": len(execution_state.completed) + len(execution_state.failed),
                "validators_passed": validators_passed,
                "validators_failed": len(execution_state.failed),
                "contract_satisfied": contract_result.satisfied,
                "missing_outputs": contract_result.missing_outputs,
                "can_advance": bool(gate_allows and contract_result.satisfied),
                "blocking_validators": gate_status.blocking_validators if gate_status else [],
                "results": {
                    vid: result.to_dict() if hasattr(result, 'to_dict') else {}
                    for vid, result in execution_state.results.items()
                },
                # Additive contract fields
                "findings": [
                    {
                        **(f.to_dict() if hasattr(f, "to_dict") else {}),
                        "validator_id": vid,
                    }
                    for vid, f in all_findings
                ],
                "suggested_fixes": suggested_fixes,
                "human_decision_required": bool(human_decision_required),
            }

            # Missing inputs takes precedence (400)
            if missing_inputs and not contract_result.satisfied:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "missing_inputs",
                        "phase": phase,
                        "missing_inputs": sorted(set(missing_inputs)),
                        "findings": base_payload["findings"],
                        "suggested_fixes": suggested_fixes,
                    },
                )

            # Gate failed (422) if the REQUIRED gate does not allow advancement
            if gate_status and not gate_status.can_advance:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "gate_failed",
                        "phase": phase,
                        "gate": kernel_phase,
                        "blocking_validators": gate_status.blocking_validators,
                        "findings": base_payload["findings"],
                        "suggested_fixes": suggested_fixes,
                        "human_decision_required": False,
                    },
                )

            # Grade warning envelope (200)
            if human_decision_required:
                base_payload.update({
                    "error": "grade_warning",
                    "grade": f"{kernel_phase}/grade",
                })

            # Persist validator writes only if explicitly requested.
            if getattr(config, "persist", False):
                state_manager.commit()
                committed = True
                store = DesignStore(context.container if (context and context.container) else None)
                try:
                    store.save(design_id, state_manager=state_manager, expected_version=design_version_before)
                except VersionConflictError as e:
                    raise HTTPException(status_code=409, detail=e.to_dict())

            return base_payload
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Phase validation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # Default: rollback so validate is non-mutating.
            if txn_started and not committed:
                try:
                    state_manager.rollback()
                except Exception:
                    pass

    @app.post("/api/v1/designs/{design_id}/phases/{phase}/approve")
    async def approve_phase(
        design_id: str,
        phase: str,
        approval: PhaseApprove = PhaseApprove(),
        state_manager=Depends(get_state_manager),
        phase_machine=Depends(get_phase_machine),
    ):
        """Approve a phase via PhaseMachine."""
        from magnet.ui.utils import set_phase_status, get_phase_status

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current = get_phase_status(state_manager, phase)
        if current not in ["completed", "active"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot approve phase in '{current}' status"
            )

        # v1.1: Approve via PhaseMachine (fixes blocker #11)
        if phase_machine:
            try:
                phase_machine.approve_phase(phase, comment=approval.comment)
            except Exception as e:
                logger.warning(f"PhaseMachine approve: {e}")
                set_phase_status(state_manager, phase, "approved", "api")
        else:
            set_phase_status(state_manager, phase, "approved", "api")

        ws_manager.queue_message(WSMessage(
            type="phase_approved",
            design_id=design_id,
            payload={"phase": phase, "comment": approval.comment},
        ))

        return {"phase": phase, "status": "approved"}

    # =========================================================================
    # Control Plane v1.1: Query Endpoints (Explainability)
    # =========================================================================

    @app.get("/api/v1/designs/{design_id}/explain/{path:path}")
    async def explain_path(
        design_id: str,
        path: str,
        format: str = "dual",
        state_manager=Depends(get_state_manager),
    ):
        """
        Control Plane v1.1: Query the explanation for a path's current value.

        Returns:
            - narrative: Human-readable explanation
            - schema: Machine-parseable structured data

        Args:
            design_id: Design identifier
            path: The state path to explain (e.g., "hull.beam")
            format: Response format ("dual", "narrative", "schema")
        """
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            # Walking Trail Contract 6: allow explain_ref to be resolved via the existing
            # /explain/{path:path} endpoint by detecting exp_v{N}_... tokens.
            if isinstance(path, str) and path.startswith("exp_v"):
                # Resolve explain_ref by scanning current provenance map.
                # NOTE: historical version resolution is not yet implemented; this resolves
                # only when the ref matches the current version's provenance entries.
                try:
                    from magnet.deployment.design_store import DesignStore
                    store = DesignStore(context.container if context else None)
                    sm = store.load(design_id)
                    state_flat = sm.export_state_flat(include_metadata=False) if hasattr(sm, "export_state_flat") else {}
                    prov = sm.export_api_provenance(state_flat, include="full") if hasattr(sm, "export_api_provenance") else {}
                    matched_path = None
                    matched_entry = None
                    for pth, meta in (prov or {}).items():
                        if isinstance(meta, dict) and meta.get("explain_ref") == path:
                            matched_path = pth
                            matched_entry = meta
                            break
                    if not matched_path:
                        raise HTTPException(status_code=404, detail={"error": "explain_ref_not_found", "explain_ref": path})

                    # Use control-plane explain for the resolved path, but wrap in ref-oriented envelope.
                    r = query_explain(path=matched_path, design_id=design_id)
                    dv = matched_entry.get("design_version") if isinstance(matched_entry, dict) else None
                    resp = {
                        "explain_ref": path,
                        "parameter": matched_path,
                        "validator_id": matched_entry.get("validator_id") if isinstance(matched_entry, dict) else None,
                        "design_version": dv,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "narrative": getattr(r, "narrative", None),
                        "schema": getattr(r, "schema", None),
                    }
                    return resp
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Explain ref resolution failed: {e}")
                    raise HTTPException(status_code=500, detail={"error": "explain_ref_failed", "message": str(e)})

            result = query_explain(path=path, design_id=design_id)
            
            if format == "narrative":
                return {"narrative": result.narrative}
            elif format == "schema":
                return {"schema": result.schema}
            else:
                return {
                    "narrative": result.narrative,
                    "schema": result.schema,
                }
        except Exception as e:
            logger.error(f"Query explain failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/designs/{design_id}/history/{path:path}")
    async def history_path(
        design_id: str,
        path: str,
        limit: int = 10,
        format: str = "dual",
        state_manager=Depends(get_state_manager),
    ):
        """
        Control Plane v1.1: Query the change history for a path.

        Returns the last N changes to the specified path with full provenance.
        """
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            result = query_history(path=path, design_id=design_id, limit=limit)
            
            if format == "narrative":
                return {"narrative": result.narrative}
            elif format == "schema":
                return {"schema": result.schema}
            else:
                return {
                    "narrative": result.narrative,
                    "schema": result.schema,
                }
        except Exception as e:
            logger.error(f"Query history failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/designs/{design_id}/impact/{version}")
    async def impact_version(
        design_id: str,
        version: int,
        format: str = "dual",
        state_manager=Depends(get_state_manager),
    ):
        """
        Control Plane v1.1: Query the engineering impact for a version.

        Returns what changed and the calculated impact on derived metrics.
        """
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            result = query_impact(version=version, design_id=design_id)
            
            if format == "narrative":
                return {"narrative": result.narrative}
            elif format == "schema":
                return {"schema": result.schema}
            else:
                return {
                    "narrative": result.narrative,
                    "schema": result.schema,
                }
        except Exception as e:
            logger.error(f"Query impact failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/v1/designs/{design_id}/explain/latest")
    async def explain_latest(
        design_id: str,
        format: str = "dual",
        state_manager=Depends(get_state_manager),
    ):
        """
        Control Plane v1.1: Query the most recent ExplainRecord.

        Returns the explanation for the most recent committed change.
        """
        from magnet.ui.utils import get_state_value

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            result = query_latest(design_id=design_id)
            
            if format == "narrative":
                return {"narrative": result.narrative}
            elif format == "schema":
                return {"schema": result.schema}
            else:
                return {
                    "narrative": result.narrative,
                    "schema": result.schema,
                }
        except Exception as e:
            logger.error(f"Query latest failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # Control Plane v1.1: Why Query Router (Natural Language)
    # =========================================================================

    class WhyQueryBody(BaseModel):
        """Request body for /why endpoint"""
        query: str
        context_paths: Optional[List[str]] = None
        context_version: Optional[int] = None

    @app.post("/api/v1/designs/{design_id}/why")
    async def why_query(
        design_id: str,
        body: WhyQueryBody,
        state_manager=Depends(get_state_manager),
        llm_client=Depends(get_llm_client),
    ):
        """
        Control Plane v1.1: Natural language "why" query router.

        Routes natural language questions to appropriate explain endpoints:
        - "Why did the beam change?" → query_explain("hull.beam")
        - "What is GM?" → PathRegistry lookup (define intent)
        - "What changed in version 5?" → query_impact(5)
        - "When did draft change?" → query_history("hull.draft")

        Args:
            design_id: Design identifier
            body: Request body with query, context_paths, context_version

        Returns:
            WhyQueryResult with intent, results, and optional clarification
        """
        from magnet.ui.utils import get_state_value
        from magnet.control_plane import (
            WhyQueryRouter,
            WhyQueryRequest,
            get_why_router,
        )

        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        current_id = get_state_value(state_manager, "metadata.design_id")
        if current_id != design_id:
            raise HTTPException(status_code=404, detail="Design not found")

        try:
            # Get or create router (with optional LLM for fallback)
            router = get_why_router(llm_client=llm_client)

            # Build request from body
            request = WhyQueryRequest(
                query=body.query,
                design_id=design_id,
                context_paths=body.context_paths,
                context_version=body.context_version,
            )

            # Resolve and dispatch
            result = router.resolve(request)

            # Format response
            return {
                "intent": result.intent.value,
                "results": [
                    {
                        "path": r.path,
                        "version": r.version,
                        "narrative": r.output.narrative,
                        "schema": r.output.schema,
                    }
                    for r in result.results
                ],
                "truncated": result.truncated,
                "clarification": result.clarification,
                "extraction": {
                    "intent": result.extraction.intent.value,
                    "paths": result.extraction.paths,
                    "version": result.extraction.version,
                    "confidence": result.extraction.confidence,
                    "source": result.extraction.source,
                } if result.extraction else None,
            }

        except Exception as e:
            logger.error(f"Why query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # Job Endpoints
    # =========================================================================

    @app.post("/api/v1/jobs")
    async def submit_job_endpoint(job: JobSubmit):
        """Submit a background job."""
        priority = {
            "low": JobPriority.LOW,
            "normal": JobPriority.NORMAL,
            "high": JobPriority.HIGH,
            "critical": JobPriority.CRITICAL,
        }.get(job.priority.lower(), JobPriority.NORMAL)

        job_id = await submit_job(job.job_type, job.payload, priority=priority)
        return {"job_id": job_id, "status": "submitted"}

    @app.get("/api/v1/jobs/{job_id}")
    async def get_job_endpoint(job_id: str):
        """Get job status."""
        status = get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        return status

    # =========================================================================
    # Vision Endpoints
    # =========================================================================

    @app.post("/api/v1/designs/{design_id}/render")
    async def render_snapshot(
        design_id: str,
        view: str = "perspective",
        width: int = 1024,
        height: int = 768,
        vision=Depends(get_vision),
    ):
        """Render a snapshot of the design."""
        if not vision:
            return {"status": "vision not available"}

        try:
            from magnet.vision.router import VisionRequest

            request = VisionRequest(
                operation="render",
                parameters={
                    "view": view,
                    "width": width,
                    "height": height,
                },
            )

            response = vision.process_request(request)

            return {
                "success": response.success if hasattr(response, 'success') else True,
                "snapshots": [s.to_dict() for s in response.snapshots] if hasattr(response, 'snapshots') and response.snapshots else [],
            }
        except Exception as e:
            logger.error(f"Render failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # =========================================================================
    # Report Endpoints
    # =========================================================================

    @app.post("/api/v1/designs/{design_id}/reports")
    async def generate_report(
        design_id: str,
        report_type: str = "summary",
        formats: List[str] = ["pdf"],
        state_manager=Depends(get_state_manager),
    ):
        """Generate a design report."""
        if not state_manager:
            raise HTTPException(status_code=503, detail="StateManager not available")

        # Submit as background job
        job_id = await submit_job(
            "generate_report",
            {"report_type": report_type, "formats": formats},
            design_id=design_id,
        )

        return {"job_id": job_id, "status": "generating"}

    # =========================================================================
    # WebSocket Endpoint
    # =========================================================================

    @app.websocket("/ws/{design_id}")
    async def websocket_endpoint(websocket: WebSocket, design_id: str):
        """WebSocket connection for real-time updates."""
        client = await ws_manager.connect(websocket, design_id=design_id)

        try:
            while True:
                data = await websocket.receive_json()
                await ws_manager.handle_incoming(client.client_id, data)
        except WebSocketDisconnect:
            await ws_manager.disconnect(client.client_id)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await ws_manager.disconnect(client.client_id)

    # =========================================================================
    # Design Language Endpoints (NEW PATH - bypasses legacy family/type priors)
    # =========================================================================

    # Request/Response models for design language
    class ProgramRequest(BaseModel):
        """Request to execute a design program."""
        program_text: str
        design_id: Optional[str] = None
        dry_run: bool = False

    class ProgramResponse(BaseModel):
        """Response from program execution."""
        success: bool
        design_id: str
        actions_applied: int
        constraints_registered: int
        validation: Dict[str, Any]
        errors: List[str]
        geometry_generated: bool

    class ProposeRequest(BaseModel):
        """Request to propose geometry from natural language."""
        intent: str
        current_state: Optional[Dict[str, Any]] = None
        constraints: Optional[List[str]] = None

    class ProposeResponse(BaseModel):
        """Response from geometry proposal."""
        success: bool
        program_text: str
        program_id: str
        operations_count: int
        average_confidence: float
        errors: List[str]

    class ProposeAndExecuteRequest(BaseModel):
        """Request to propose and execute in one call."""
        intent: str
        constraints: Optional[List[str]] = None
        dry_run: bool = False
        min_confidence: float = 0.5

    class ProposeAndExecuteResponse(BaseModel):
        """Response from propose-and-execute."""
        success: bool
        proposal_accepted: bool
        program_text: str
        average_confidence: float
        validation: Dict[str, Any]
        errors: List[str]
        geometry_generated: bool

    @app.post("/api/v1/program", tags=["Design Language"])
    async def execute_design_program(
        request: ProgramRequest,
        state_manager=Depends(get_state_manager),
    ):
        """
        Execute a design program using geometry primitives.
        
        This is the NEW PATH that bypasses legacy family/type priors.
        Agents output geometry.* primitives, kernel compiles to HullGeometry.
        
        Example program:
        ```
        CREATE geometry.body main { body_type: "slender_displacement", physics_category: "surface_piercing" }
        CREATE geometry.section bow { station: 0.0, body_id: "main", points: [[0,0], [1,-0.5], [1,-1.5], [0,-2]] }
        SET hull.loa = 25.0
        CONSTRAIN hull.gm >= 0.5
        ```
        """
        from magnet.kernel.program_executor import execute_program
        
        try:
            result = execute_program(
                program_text=request.program_text,
                state_manager=state_manager,
                dry_run=request.dry_run,
            )
            
            return ProgramResponse(
                success=result.success,
                design_id=request.design_id or "new",
                actions_applied=len(result.actions),
                constraints_registered=len(result.constraints) if hasattr(result, 'constraints') else 0,
                validation=result.validation or {},
                errors=result.errors,
                geometry_generated=result.geometry is not None,
            )
            
        except Exception as e:
            logger.error(f"Program execution error: {e}")
            return ProgramResponse(
                success=False,
                design_id=request.design_id or "error",
                actions_applied=0,
                constraints_registered=0,
                validation={},
                errors=[str(e)],
                geometry_generated=False,
            )

    @app.post("/api/v1/propose", tags=["Design Language"])
    async def propose_geometry(
        request: ProposeRequest,
        state_manager=Depends(get_state_manager),
    ):
        """
        Propose geometry primitives from natural language intent.
        
        Uses LLM to translate design intent into geometry.* operations.
        Returns a program that can be executed via POST /api/v1/program.
        
        Example:
        ```json
        {
          "intent": "Create a fast patrol vessel, 25m LOA, twin hull configuration",
          "constraints": ["GM >= 0.8m", "Draft <= 1.5m"]
        }
        ```
        """
        from magnet.agents.geometry_proposer import propose_geometry as do_propose
        
        try:
            # Get current state if not provided
            current_state = request.current_state
            if current_state is None and state_manager:
                current_state = state_manager.to_dict() if hasattr(state_manager, 'to_dict') else {}
            
            result = await do_propose(
                intent=request.intent,
                current_state=current_state,
            )
            
            if result.success and result.program:
                avg_conf = sum(op.confidence for op in result.program.operations) / len(result.program.operations) if result.program.operations else 0.0
                
                return ProposeResponse(
                    success=True,
                    program_text=result.program_text,
                    program_id=result.program.program_id,
                    operations_count=len(result.program.operations),
                    average_confidence=avg_conf,
                    errors=[],
                )
            else:
                return ProposeResponse(
                    success=False,
                    program_text="",
                    program_id="",
                    operations_count=0,
                    average_confidence=0.0,
                    errors=[result.error or "Unknown error"],
                )
                
        except Exception as e:
            logger.error(f"Proposal error: {e}")
            return ProposeResponse(
                success=False,
                program_text="",
                program_id="",
                operations_count=0,
                average_confidence=0.0,
                errors=[str(e)],
            )

    @app.post("/api/v1/propose-and-execute", tags=["Design Language"])
    async def propose_and_execute(
        request: ProposeAndExecuteRequest,
        state_manager=Depends(get_state_manager),
    ):
        """
        Propose geometry from intent and execute if confidence is sufficient.
        
        This is the primary endpoint for the new design language path.
        Combines natural language → geometry primitives → compiled geometry.
        
        Flow:
        1. LLM translates intent to geometry.* operations
        2. If average confidence >= min_confidence, execute program
        3. Return validation results
        """
        from magnet.agents.geometry_proposer import propose_geometry as do_propose
        from magnet.kernel.program_executor import execute_program
        
        try:
            # Step 1: Propose
            current_state = state_manager.to_dict() if state_manager and hasattr(state_manager, 'to_dict') else {}
            proposal = await do_propose(
                intent=request.intent,
                current_state=current_state,
            )
            
            if not proposal.success or not proposal.program:
                return ProposeAndExecuteResponse(
                    success=False,
                    proposal_accepted=False,
                    program_text="",
                    average_confidence=0.0,
                    validation={},
                    errors=[proposal.error or "Proposal failed"],
                    geometry_generated=False,
                )
            
            # Calculate confidence
            avg_conf = sum(op.confidence for op in proposal.program.operations) / len(proposal.program.operations) if proposal.program.operations else 0.0
            
            # Step 2: Check confidence threshold
            if avg_conf < request.min_confidence:
                return ProposeAndExecuteResponse(
                    success=True,  # Proposal succeeded, just not executed
                    proposal_accepted=False,
                    program_text=proposal.program_text,
                    average_confidence=avg_conf,
                    validation={},
                    errors=[f"Confidence {avg_conf:.2f} below threshold {request.min_confidence}"],
                    geometry_generated=False,
                )
            
            # Step 3: Execute
            result = execute_program(
                program_text=proposal.program_text,
                state_manager=state_manager,
                dry_run=request.dry_run,
            )
            
            return ProposeAndExecuteResponse(
                success=result.success,
                proposal_accepted=True,
                program_text=proposal.program_text,
                average_confidence=avg_conf,
                validation=result.validation or {},
                errors=result.errors,
                geometry_generated=result.geometry is not None,
            )
            
        except Exception as e:
            logger.error(f"Propose-and-execute error: {e}")
            return ProposeAndExecuteResponse(
                success=False,
                proposal_accepted=False,
                program_text="",
                average_confidence=0.0,
                validation={},
                errors=[str(e)],
                geometry_generated=False,
            )

    # =========================================================================
    # Change Propagation (Part XIV: Iterative Design Loop)
    # =========================================================================

    class PropagateRequest(BaseModel):
        """Request to propagate a parameter change through the pipeline."""
        key: str                      # "hull.beam"
        value: Any                    # 5.0
        design_id: Optional[str] = None
        auto_adjust: bool = False     # Attempt to fix constraint violations

    class MetricDeltaResponse(BaseModel):
        """Delta for a single metric."""
        previous: Optional[float]
        current: Optional[float]
        delta: Optional[float]
        percent_change: Optional[float]
        direction: str  # "improved", "degraded", "neutral", "unknown"

    class ConstraintViolationResponse(BaseModel):
        """A constraint that failed after propagation."""
        constraint: str
        current: float
        required: float
        severity: str
        suggestion: str

    class PropagateResponse(BaseModel):
        """Response from change propagation."""
        success: bool
        changed: Dict[str, Any]
        invalidated_phases: List[str]
        deltas: Dict[str, MetricDeltaResponse]
        constraint_violations: List[ConstraintViolationResponse]
        cascade_time_ms: int
        errors: List[str] = []

    @app.post("/api/v1/propagate", tags=["Design Language"])
    async def propagate_change(
        request: PropagateRequest,
        state_manager=Depends(get_state_manager),
    ) -> PropagateResponse:
        """
        Change a parameter and propagate through the pipeline.
        
        This is the core of the iterative design spiral:
        1. Engineer/agent changes a parameter
        2. System identifies which phases are invalidated
        3. System reruns only those phases
        4. System computes deltas for ALL affected metrics
        5. System surfaces any constraint violations
        
        Returns deltas for all affected metrics and any constraint violations.
        
        Example:
        ```json
        POST /api/v1/propagate
        {
            "key": "hull.beam",
            "value": 5.0
        }
        
        Response:
        {
            "success": false,
            "changed": {"key": "hull.beam", "previous": 4.5, "new": 5.0},
            "invalidated_phases": ["hull", "weight", "stability", "cost"],
            "deltas": {
                "stability.gm_m": {"previous": 0.65, "current": 0.42, "delta": -0.23, "direction": "degraded"}
            },
            "constraint_violations": [
                {"constraint": "stability.gm_m >= 0.5", "current": 0.42, "required": 0.5}
            ],
            "cascade_time_ms": 127
        }
        ```
        """
        from magnet.kernel.propagation import PropagationEngine
        from magnet.kernel.conductor import Conductor
        
        errors = []
        
        try:
            # Get or create conductor
            conductor = Conductor(state_manager)
            design_id = request.design_id or state_manager.get("design_id") or "propagation_session"
            conductor.create_session(design_id)
            
            # Run propagation
            engine = PropagationEngine()
            result = engine.propagate_change(
                key=request.key,
                new_value=request.value,
                state_manager=state_manager,
                conductor=conductor,
            )
            
            # Convert to response format
            deltas = {}
            for k, v in result.metric_deltas.items():
                deltas[k] = MetricDeltaResponse(
                    previous=v.previous,
                    current=v.current,
                    delta=v.delta,
                    percent_change=v.percent_change,
                    direction=v.direction,
                )
            
            violations = []
            for v in result.constraint_violations:
                violations.append(ConstraintViolationResponse(
                    constraint=v.expression,
                    current=v.current_value,
                    required=v.required_value,
                    severity=v.severity,
                    suggestion=v.suggestion,
                ))
            
            return PropagateResponse(
                success=result.success,
                changed={
                    "key": result.changed_key,
                    "previous": result.previous_value,
                    "new": result.new_value,
                },
                invalidated_phases=result.invalidated_phases,
                deltas=deltas,
                constraint_violations=violations,
                cascade_time_ms=result.cascade_time_ms,
                errors=errors,
            )
            
        except Exception as e:
            logger.error(f"Propagation error: {e}")
            return PropagateResponse(
                success=False,
                changed={"key": request.key, "previous": None, "new": request.value},
                invalidated_phases=[],
                deltas={},
                constraint_violations=[],
                cascade_time_ms=0,
                errors=[str(e)],
            )

    # =========================================================================
    # Chat-Based Design Loop (NEW PATH - Geometry Primitives)
    # =========================================================================
    #
    # THIS IS THE NEW PATH — separate from intent_protocol.py.
    #
    # Two systems coexist:
    # 1. OLD: intent_protocol.py → parameter refinement → legacy synthesis
    # 2. NEW: geometry_proposer.py → program_executor.py → compiler.py → HullGeometry
    #
    # This endpoint uses the NEW path exclusively. It does NOT touch intent_protocol.
    #
    # Reference: MAGNET_System_State_Analysis.md Parts XIII-XVI

    class ChatDesignRequest(BaseModel):
        """Request for chat-based design iteration (NEW PATH)."""
        message: str                  # Natural language OR direct DSL
        conversation_id: Optional[str] = None
        constraints: Optional[List[str]] = None
        use_llm: bool = True  # Use GeometryProposer for natural language

    class ChatDesignResponse(BaseModel):
        """Response from chat-based design iteration."""
        success: bool
        conversation_id: str
        iteration: int
        feedback: str
        metrics: Dict[str, float]
        deltas: Dict[str, float]
        geometry_generated: bool
        errors: List[str] = []

    # Store conversations in memory (use Redis/DB for production)
    _design_conversations: Dict[str, Any] = {}
    _clarification_managers: Dict[str, Any] = {}  # Session-level clarification managers

    @app.post("/api/v1/design/chat", tags=["Design Language"])
    async def design_chat(request: ChatDesignRequest) -> ChatDesignResponse:
        """
        Chat-based iterative design loop using geometry primitives (NEW PATH).
        
        THIS BYPASSES intent_protocol.py ENTIRELY.
        
        Flow:
        1. User provides natural language OR direct geometry DSL
        2. If natural language: GeometryProposer translates to DSL
        3. DSL → program_executor → compiler → HullGeometry
        4. Validation (hydrostatics, resistance)
        5. Feedback returned with deltas
        
        No family/type priors. Pure geometry primitives.
        
        Example conversation:
        ```
        # Natural language (requires use_llm=True)
        POST /api/v1/design/chat
        {"message": "Create a 25m fast patrol vessel with twin hulls"}
        
        # Direct DSL (works without LLM)
        POST /api/v1/design/chat
        {"message": "CREATE geometry.body port { body_type: \"demihull\", offset_y_m: -3.0 }\\nCREATE geometry.body stbd { body_type: \"demihull\", offset_y_m: 3.0 }", "use_llm": false}
        
        # Continue conversation
        POST /api/v1/design/chat
        {"message": "Make it more stable", "conversation_id": "..."}
        ```
        """
        from magnet.agents.design_conversation import DesignConversation
        import uuid
        
        try:
            # Get or create conversation
            conv_id = request.conversation_id
            if conv_id and conv_id in _design_conversations:
                conversation = _design_conversations[conv_id]
            else:
                conv_id = str(uuid.uuid4())
                
                # Get or create clarification manager for this session
                from magnet.agents.clarification import ClarificationManager
                if conv_id not in _clarification_managers:
                    _clarification_managers[conv_id] = ClarificationManager()
                
                conversation = DesignConversation(
                    initial_state={"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}},
                    conversation_id=conv_id,
                    use_llm=request.use_llm,
                    clarification_manager=_clarification_managers[conv_id],
                    confidence_threshold=0.6,
                )
                _design_conversations[conv_id] = conversation
            
            # Process message via NEW path
            result = await conversation.chat(
                request.message,
                constraints=request.constraints,
            )
            
            return ChatDesignResponse(
                success=result.success,
                conversation_id=conv_id,
                iteration=result.iteration_number,
                feedback=result.feedback_to_user,
                metrics=result.metrics,
                deltas=result.deltas,
                geometry_generated=result.execution_result is not None and result.execution_result.geometry is not None,
                errors=result.execution_result.errors if result.execution_result else [],
            )
            
        except Exception as e:
            logger.error(f"Design chat error: {e}")
            return ChatDesignResponse(
                success=False,
                conversation_id=request.conversation_id or "",
                iteration=0,
                feedback=f"Error: {str(e)}",
                metrics={},
                deltas={},
                geometry_generated=False,
                errors=[str(e)],
            )

    @app.get("/api/v1/design/chat/{conversation_id}/summary", tags=["Design Language"])
    async def get_design_conversation_summary(conversation_id: str):
        """Get summary of a design conversation (NEW PATH)."""
        if conversation_id not in _design_conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation = _design_conversations[conversation_id]
        return conversation.get_summary()

    @app.get("/api/v1/design/chat/{conversation_id}/history", tags=["Design Language"])
    async def get_design_conversation_history(conversation_id: str):
        """Get full history of a design conversation (NEW PATH)."""
        if conversation_id not in _design_conversations:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        conversation = _design_conversations[conversation_id]
        return conversation.get_history()

    # =========================================================================
    # Phase 0.5: Vision Interpreter — Sketch to Geometry
    # Reference: MAGNET_Merge_Implementation_Plan.md
    # =========================================================================

    @app.post("/api/v1/design/sketch", tags=["Design Language"])
    async def interpret_sketch_endpoint(
        image: UploadFile = File(..., description="Hand-drawn sketch image"),
        annotations: str = Form(default="", description="Optional text annotations"),
        session_id: Optional[str] = Form(default=None, description="Design session ID"),
        generate_geometry: bool = Form(default=True, description="Generate geometry from interpretation"),
    ):
        """
        Interpret a hand-drawn sketch and generate geometry.
        
        This is a key human-in-the-loop input modality. Engineers can sketch
        hull concepts on paper or tablet and have them converted to geometry
        primitives.
        
        Flow:
        1. VisionInterpreter extracts geometric information from sketch
        2. Generates intent string (geometry-only, NO design types)
        3. If generate_geometry=True: GeometryProposer converts to DSL
        4. ProgramExecutor compiles geometry
        
        Returns interpretation + optionally generated geometry.
        
        INVARIANT: Response will NEVER contain "catamaran", "trimaran", etc.
                   Only geometric descriptions.
        
        Example:
            curl -X POST /api/v1/design/sketch \\
                -F "image=@sketch.png" \\
                -F "annotations=25m fast vessel" \\
                -F "generate_geometry=true"
        """
        from magnet.agents.vision_interpreter import VisionInterpreter, interpret_sketch
        from magnet.llm.providers.anthropic import AnthropicProvider
        import uuid
        
        try:
            # Read image
            image_data = await image.read()
            
            # Determine media type
            media_type = image.content_type or "image/png"
            if media_type not in ("image/png", "image/jpeg", "image/gif", "image/webp"):
                raise HTTPException(400, f"Unsupported image type: {media_type}")
            
            # Create interpreter with Anthropic provider
            try:
                provider = AnthropicProvider()
                interpreter = VisionInterpreter(provider)
            except Exception as e:
                logger.warning(f"Could not create vision interpreter: {e}")
                return {
                    "success": False,
                    "error": f"Vision interpreter not available: {e}",
                }
            
            # Interpret sketch
            vision_result = await interpreter.interpret_sketch(
                image_data=image_data,
                annotations=annotations,
                image_media_type=media_type,
            )
            
            if not vision_result.success:
                return {
                    "success": False,
                    "error": vision_result.error,
                }
            
            response = {
                "success": True,
                "interpretation": vision_result.interpretation.model_dump() if vision_result.interpretation else None,
                "intent_string": vision_result.intent_string,
                "session_id": session_id or str(uuid.uuid4()),
            }
            
            # Optionally generate geometry
            if generate_geometry:
                try:
                    from magnet.agents.design_conversation import DesignConversation
                    
                    # Get or create conversation
                    conv_id = session_id or str(uuid.uuid4())
                    if conv_id in _design_conversations:
                        conversation = _design_conversations[conv_id]
                    else:
                        # Get or create clarification manager for this session
                        from magnet.agents.clarification import ClarificationManager
                        if conv_id not in _clarification_managers:
                            _clarification_managers[conv_id] = ClarificationManager()
                        
                        conversation = DesignConversation(
                            initial_state={"hull": {"loa": 25.0, "draft": 1.5, "vcg": 1.0}},
                            conversation_id=conv_id,
                            use_llm=True,
                            clarification_manager=_clarification_managers[conv_id],
                            confidence_threshold=0.6,
                        )
                        _design_conversations[conv_id] = conversation
                    
                    # Process interpreted intent with vision context for reconciliation
                    vision_context = {
                        "body_count": vision_result.interpretation.body_count if vision_result.interpretation else 1,
                        "loa_m": vision_result.interpretation.loa_m if vision_result.interpretation else None,
                        "beam_m": vision_result.interpretation.beam_m if vision_result.interpretation else None,
                    }
                    
                    chat_result = await conversation.chat(
                        vision_result.intent_string,
                        constraints=[],
                        vision_context=vision_context,
                    )
                    
                    response["geometry_result"] = {
                        "success": chat_result.success,
                        "feedback": chat_result.feedback_to_user,
                        "metrics": chat_result.metrics,
                        "geometry_generated": chat_result.execution_result is not None and chat_result.execution_result.geometry is not None,
                    }
                    response["session_id"] = conv_id
                    
                    # Issue 1.1: Generate GLB if geometry was created
                    if chat_result.execution_result and chat_result.execution_result.geometry:
                        try:
                            from magnet.webgl.geometry_adapter import hull_geometry_to_webgl
                            from magnet.webgl.geometry_pipeline import HullGeometryPipeline
                            from magnet.webgl.exporter import Exporter, ExportFormat
                            import base64
                            
                            # Convert kernel HullGeometry to WebGL format
                            webgl_geom = hull_geometry_to_webgl(
                                chat_result.execution_result.geometry,
                                design_id=conv_id,
                                version_id="v1",
                            )
                            
                            # Tessellate to mesh
                            pipeline = HullGeometryPipeline(hull_geom=webgl_geom)
                            mesh = pipeline.tessellate()
                            
                            # Export to GLB
                            exporter = Exporter()
                            glb_bytes = exporter.export(mesh, ExportFormat.GLB)
                            
                            # Return base64-encoded GLB for embedding
                            glb_base64 = base64.b64encode(glb_bytes).decode('utf-8')
                            
                            response["geometry_result"]["glb_data"] = glb_base64
                            response["geometry_result"]["glb_size_bytes"] = len(glb_bytes)
                            
                            logger.info(f"Generated GLB for sketch: {len(glb_bytes)} bytes")
                            
                        except Exception as e:
                            logger.warning(f"GLB generation failed: {e}")
                            response["geometry_result"]["glb_error"] = str(e)
                    
                except Exception as e:
                    logger.warning(f"Geometry generation failed: {e}")
                    response["geometry_result"] = {
                        "success": False,
                        "error": str(e),
                    }
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Sketch interpretation error: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Frontend Static Files (Module 65.2: Serve ui_v2 directly)
    # =========================================================================

    # Priority 1: Serve ui_v2 directly (no build step required)
    if os.path.exists(UI_V2_PATH):
        # Mount JS and CSS directories at /ui/v2/js and /ui/v2/css
        # (HTML uses relative paths like src="js/..." which resolve to /ui/v2/js/...)
        js_path = os.path.join(UI_V2_PATH, "js")
        css_path = os.path.join(UI_V2_PATH, "css")
        if os.path.exists(js_path):
            app.mount("/ui/v2/js", StaticFiles(directory=js_path), name="ui_v2_js")
        if os.path.exists(css_path):
            app.mount("/ui/v2/css", StaticFiles(directory=css_path), name="ui_v2_css")
        logger.info(f"Mounted Studio UI from {UI_V2_PATH}")

        # Serve UI at /ui/v2/ (canonical). Root "/" redirects there to prevent
        # relative asset paths (js/..., css/...) from breaking when accessed at "/".
        @app.get("/", include_in_schema=False)
        async def redirect_root_to_ui():
            return RedirectResponse(url="/ui/v2/")

        @app.get("/ui/v2", include_in_schema=False)
        async def redirect_ui_v2_to_slash():
            # IMPORTANT: index.html uses relative asset paths. If the user loads
            # /ui/v2 (no trailing slash), the browser resolves `js/...` as /ui/js/...
            # and the backend adapter fails to load.
            return RedirectResponse(url="/ui/v2/")

        @app.get("/ui/v2/", response_class=HTMLResponse, include_in_schema=False)
        async def serve_ui_v2():
            """Serve Studio UI (single-origin, canonical at /ui/v2/)."""
            index_path = os.path.join(UI_V2_PATH, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "r") as f:
                    return HTMLResponse(content=f.read())
            return HTMLResponse(content="<h1>MAGNET API</h1><p>UI not found.</p>")

        @app.api_route(
            "/{full_path:path}",
            # For non-GET/HEAD requests to unknown paths, prefer 404 (not 405),
            # so removed endpoints are indistinguishable from non-existent ones.
            # Do not include OPTIONS here; CORS middleware should handle preflight.
            methods=["POST", "PUT", "PATCH", "DELETE"],
            include_in_schema=False,
        )
        async def reject_frontend_mutations(full_path: str):
            raise HTTPException(status_code=404, detail="Not found")

        @app.api_route(
            "/{full_path:path}",
            # SPA serving should not intercept non-GET/HEAD requests. In particular, do not
            # swallow OPTIONS preflight (CORS) which should return 405 or be handled by CORS middleware.
            methods=["GET", "HEAD"],
            include_in_schema=False,
        )
        async def serve_frontend_spa(request: Request, full_path: str):
            """Serve frontend SPA for all non-API routes (GET/HEAD only)."""
            # Don't serve frontend for API, docs, or WebSocket paths
            if full_path.startswith(("api/", "docs", "redoc", "openapi", "ws/", "health", "ready")):
                raise HTTPException(status_code=404, detail="Not found")

            # Strip ui/v2/ prefix if present (UI is served at /ui/v2/ but files are at UI_V2_PATH/)
            file_path = full_path
            if file_path.startswith("ui/v2/"):
                file_path = file_path[6:]  # Remove "ui/v2/"
            elif file_path == "ui/v2":
                file_path = ""

            # Try to serve static file from ui_v2
            if file_path:
                static_path = os.path.join(UI_V2_PATH, file_path)
                if os.path.exists(static_path) and os.path.isfile(static_path):
                    return FileResponse(static_path)

            # Fall back to index.html for SPA routing
            index_path = os.path.join(UI_V2_PATH, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            raise HTTPException(status_code=404, detail="UI not found")

    else:
        logger.info(f"No UI found at {UI_V2_PATH}; legacy frontend dist path is deprecated and not served.")

    return app


def _create_stub_app():
    """Create stub app when FastAPI is not available."""
    class StubApp:
        def __init__(self):
            self._routes = {}

        def get(self, path):
            def decorator(func):
                self._routes[f"GET {path}"] = func
                return func
            return decorator

        def post(self, path):
            def decorator(func):
                self._routes[f"POST {path}"] = func
                return func
            return decorator

    return StubApp()


# Module-level app instance for uvicorn
#
# IMPORTANT:
# `uvicorn magnet.deployment.api:app` imports this module directly.
# If we build the app with `context=None`, DI/container wiring is bypassed and
# StateManager-dependent endpoints (e.g. reports) can return 503.
#
# Prefer creating the FastAPI app using the bootstrap context when available,
# while keeping a safe fallback for minimal environments.
def _get_uvicorn_app():
    try:
        from magnet.bootstrap.app import MAGNETApp

        bootstrap = MAGNETApp().build()
        return create_fastapi_app(bootstrap.context)
    except Exception:
        # Fallback: build a context-less app (may limit some endpoints).
        return create_fastapi_app()


app = _get_uvicorn_app()
