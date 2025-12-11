"""
magnet/llm/services/explanation_service.py - Explanation Service

High-level service for generating design change explanations and narratives.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..prompts.schemas import ExplanationResponse, ParameterChangeExplanation, ChangeImpact
from ..prompts.explanation import (
    EXPLANATION_SYSTEM_PROMPT,
    NARRATIVE_SYSTEM_PROMPT,
    create_change_explanation_prompt,
    create_narrative_prompt,
    create_next_steps_prompt,
    get_fallback_explanation,
    get_parameter_display_name,
)

if TYPE_CHECKING:
    from ..protocol import LLMProviderProtocol

logger = logging.getLogger("llm.services.explanation")


class ExplanationService:
    """
    Service for generating design explanations and narratives.

    Features:
    - LLM-powered explanations with context awareness
    - Multiple detail levels (SUMMARY to EXPERT)
    - Automatic fallback to deterministic templates
    - Domain-specific explanations (stability, performance)
    """

    def __init__(
        self,
        llm: Optional["LLMProviderProtocol"] = None,
        use_fallback: bool = True,
    ):
        """
        Initialize the explanation service.

        Args:
            llm: LLM provider instance (optional)
            use_fallback: Whether to use fallback when LLM unavailable
        """
        self.llm = llm
        self.use_fallback = use_fallback

    async def explain_changes(
        self,
        parameter_diffs: List[Dict[str, Any]],
        validation_results: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[str]] = None,
        level: str = "STANDARD",
    ) -> ExplanationResponse:
        """
        Generate an explanation for design changes.

        Args:
            parameter_diffs: List of parameter changes
            validation_results: Optional validation results
            warnings: Optional warning messages
            level: Detail level (SUMMARY/STANDARD/DETAILED/EXPERT)

        Returns:
            ExplanationResponse with narrative and details
        """
        validation_results = validation_results or []
        warnings = warnings or []

        if self.llm is None:
            logger.debug("No LLM available, using fallback")
            return self._fallback_explanation(parameter_diffs, validation_results, warnings)

        prompt = create_change_explanation_prompt(
            parameter_diffs=parameter_diffs,
            validation_results=validation_results,
            warnings=warnings,
            level=level,
        )

        try:
            return await self.llm.complete_json(
                prompt=prompt,
                response_model=ExplanationResponse,
                system_prompt=EXPLANATION_SYSTEM_PROMPT,
            )

        except Exception as e:
            logger.warning(f"LLM explanation failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_explanation(parameter_diffs, validation_results, warnings)
            raise

    async def generate_narrative(
        self,
        design_context: Dict[str, Any],
        changes_summary: str,
        audience: str = "naval_architect",
    ) -> str:
        """
        Generate a cohesive narrative for the design state.

        Args:
            design_context: Current design state information
            changes_summary: Summary of recent changes
            audience: Target audience

        Returns:
            Narrative text string
        """
        if self.llm is None:
            return self._fallback_narrative(design_context, changes_summary)

        prompt = create_narrative_prompt(
            design_context=design_context,
            changes_summary=changes_summary,
            audience=audience,
        )

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=NARRATIVE_SYSTEM_PROMPT,
            )
            return response.content

        except Exception as e:
            logger.warning(f"LLM narrative failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_narrative(design_context, changes_summary)
            raise

    async def suggest_next_steps(
        self,
        current_state: Dict[str, Any],
        completed_phases: Optional[List[str]] = None,
        validation_status: Optional[Dict[str, bool]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate recommended next steps for the design.

        Args:
            current_state: Current design state
            completed_phases: List of completed phases
            validation_status: Validation pass/fail status

        Returns:
            List of next step recommendations
        """
        completed_phases = completed_phases or []
        validation_status = validation_status or {}

        if self.llm is None:
            return self._fallback_next_steps(current_state, completed_phases, validation_status)

        prompt = create_next_steps_prompt(
            current_state=current_state,
            completed_phases=completed_phases,
            validation_status=validation_status,
        )

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=EXPLANATION_SYSTEM_PROMPT,
            )

            # Parse JSON array response
            import json
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)

        except Exception as e:
            logger.warning(f"LLM next steps failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_next_steps(current_state, completed_phases, validation_status)
            raise

    async def explain_single_parameter(
        self,
        parameter_path: str,
        old_value: Any,
        new_value: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> ParameterChangeExplanation:
        """
        Generate explanation for a single parameter change.

        Args:
            parameter_path: Parameter path
            old_value: Previous value
            new_value: New value
            context: Additional context

        Returns:
            ParameterChangeExplanation
        """
        # Calculate change percent if numeric
        change_percent = None
        if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
            if old_value != 0:
                change_percent = ((new_value - old_value) / abs(old_value)) * 100

        diff = {
            "parameter": parameter_path,
            "name": get_parameter_display_name(parameter_path),
            "old_value": old_value,
            "new_value": new_value,
            "change_percent": change_percent or 0,
        }

        response = await self.explain_changes(
            parameter_diffs=[diff],
            level="DETAILED",
        )

        if response.changes:
            return response.changes[0]

        # Fallback single explanation
        return ParameterChangeExplanation(
            parameter=parameter_path,
            old_value=old_value,
            new_value=new_value,
            change_percent=change_percent,
            impact=ChangeImpact.MODERATE,
            explanation=f"{get_parameter_display_name(parameter_path)} changed from {old_value} to {new_value}",
            trade_offs=[],
        )

    # =========================================================================
    # Fallback Methods
    # =========================================================================

    def _fallback_explanation(
        self,
        parameter_diffs: List[Dict[str, Any]],
        validation_results: List[Dict[str, Any]],
        warnings: List[str],
    ) -> ExplanationResponse:
        """Generate deterministic fallback explanation."""
        data = get_fallback_explanation(parameter_diffs, validation_results, warnings)

        changes = [
            ParameterChangeExplanation(
                parameter=c["parameter"],
                old_value=c["old_value"],
                new_value=c["new_value"],
                change_percent=c.get("change_percent"),
                impact=ChangeImpact(c.get("impact", "moderate")),
                explanation=c["explanation"],
                trade_offs=c.get("trade_offs", []),
            )
            for c in data.get("changes", [])
        ]

        return ExplanationResponse(
            summary=data["summary"],
            narrative=data["narrative"],
            changes=changes,
            next_steps=data.get("next_steps", []),
            warnings=data.get("warnings", []),
        )

    def _fallback_narrative(
        self,
        design_context: Dict[str, Any],
        changes_summary: str,
    ) -> str:
        """Generate simple fallback narrative."""
        parts = ["Design Status Report", "=" * 20, ""]

        # Add context
        if design_context:
            parts.append("Current Design State:")
            for key, value in design_context.items():
                display_name = get_parameter_display_name(key)
                parts.append(f"  - {display_name}: {value}")
            parts.append("")

        # Add changes
        if changes_summary:
            parts.append("Recent Changes:")
            parts.append(changes_summary)

        return "\n".join(parts)

    def _fallback_next_steps(
        self,
        current_state: Dict[str, Any],
        completed_phases: List[str],
        validation_status: Dict[str, bool],
    ) -> List[Dict[str, Any]]:
        """Generate deterministic next steps."""
        steps = []

        # Check for failing validations
        failing = [name for name, passed in validation_status.items() if not passed]
        if failing:
            steps.append({
                "step": f"Address failing validations: {', '.join(failing[:3])}",
                "priority": 1,
                "reason": "Validations must pass before proceeding",
            })

        # Check for incomplete phases
        all_phases = ["mission", "hull_form", "arrangement", "stability", "compliance"]
        incomplete = [p for p in all_phases if p not in completed_phases]
        if incomplete:
            next_phase = incomplete[0]
            steps.append({
                "step": f"Complete {next_phase.replace('_', ' ').title()} phase",
                "priority": 2,
                "reason": f"Required for design progression",
            })

        # Default step
        if not steps:
            steps.append({
                "step": "Review design and run optimization",
                "priority": 3,
                "reason": "Design appears complete, optimization may improve results",
            })

        return steps

    # =========================================================================
    # Domain-Specific Methods
    # =========================================================================

    async def explain_stability_changes(
        self,
        stability_params: Dict[str, Dict[str, Any]],
        compliance_status: Dict[str, bool],
    ) -> str:
        """
        Explain stability-related changes.

        Args:
            stability_params: Dict of stability parameters with old/new values
            compliance_status: IMO compliance status

        Returns:
            Explanation text
        """
        diffs = [
            {
                "parameter": f"stability.{key}",
                "name": get_parameter_display_name(f"stability.{key}"),
                "old_value": val.get("old"),
                "new_value": val.get("new"),
                "change_percent": self._calc_change_percent(val.get("old"), val.get("new")),
            }
            for key, val in stability_params.items()
        ]

        # Convert compliance to validation format
        validations = [
            {"name": name, "passed": passed, "message": "IMO compliance check"}
            for name, passed in compliance_status.items()
        ]

        response = await self.explain_changes(diffs, validations, level="DETAILED")
        return response.narrative

    async def explain_performance_changes(
        self,
        performance_metrics: Dict[str, Any],
        previous_metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Explain performance metric changes.

        Args:
            performance_metrics: Current performance values
            previous_metrics: Previous values for comparison

        Returns:
            Explanation text
        """
        diffs = []
        for key, value in performance_metrics.items():
            diff = {
                "parameter": f"performance.{key}",
                "name": get_parameter_display_name(f"performance.{key}"),
                "new_value": value,
            }
            if previous_metrics and key in previous_metrics:
                diff["old_value"] = previous_metrics[key]
                diff["change_percent"] = self._calc_change_percent(
                    previous_metrics[key], value
                )
            diffs.append(diff)

        response = await self.explain_changes(diffs, level="STANDARD")
        return response.narrative

    @staticmethod
    def _calc_change_percent(old: Any, new: Any) -> Optional[float]:
        """Calculate percentage change between values."""
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            if old != 0:
                return ((new - old) / abs(old)) * 100
        return None
