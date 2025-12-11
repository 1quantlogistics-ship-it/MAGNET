"""
magnet/llm/services/compliance_service.py - Compliance Service

High-level service for generating compliance remediation guidance.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..prompts.schemas import ComplianceRemediationResponse, RemediationAction
from ..prompts.compliance import (
    COMPLIANCE_SYSTEM_PROMPT,
    RULE_EXPLANATION_SYSTEM_PROMPT,
    create_remediation_prompt,
    create_rule_explanation_prompt,
    create_batch_remediation_prompt,
    get_fallback_remediation,
)

if TYPE_CHECKING:
    from ..protocol import LLMProviderProtocol

logger = logging.getLogger("llm.services.compliance")


class ComplianceService:
    """
    Service for generating compliance remediation guidance.

    Features:
    - LLM-powered remediation suggestions with trade-off analysis
    - Rule explanations with regulatory context
    - Batch processing for multiple failures
    - Automatic fallback to standard remediation patterns
    """

    def __init__(
        self,
        llm: Optional["LLMProviderProtocol"] = None,
        use_fallback: bool = True,
    ):
        """
        Initialize the compliance service.

        Args:
            llm: LLM provider instance (optional)
            use_fallback: Whether to use fallback when LLM unavailable
        """
        self.llm = llm
        self.use_fallback = use_fallback

    async def generate_remediation(
        self,
        rule_name: str,
        rule_description: str,
        actual_value: Any,
        required_value: Any,
        design_context: Dict[str, Any],
        framework: Optional[str] = None,
    ) -> ComplianceRemediationResponse:
        """
        Generate remediation guidance for a compliance failure.

        Args:
            rule_name: Name of the failed rule
            rule_description: Description of the rule
            actual_value: Current value
            required_value: Required value
            design_context: Current design state
            framework: Compliance framework (imo_intact, class_dnv, etc.)

        Returns:
            ComplianceRemediationResponse with actions and trade-offs
        """
        if self.llm is None:
            logger.debug("No LLM available, using fallback")
            return self._fallback_remediation(rule_name, actual_value, required_value)

        prompt = create_remediation_prompt(
            rule_name=rule_name,
            rule_description=rule_description,
            actual_value=actual_value,
            required_value=required_value,
            design_context=design_context,
            framework=framework,
        )

        try:
            return await self.llm.complete_json(
                prompt=prompt,
                response_model=ComplianceRemediationResponse,
                system_prompt=COMPLIANCE_SYSTEM_PROMPT,
            )

        except Exception as e:
            logger.warning(f"LLM remediation failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_remediation(rule_name, actual_value, required_value)
            raise

    async def explain_rule(
        self,
        rule_name: str,
        rule_description: str,
        framework: Optional[str] = None,
    ) -> str:
        """
        Generate an explanation of a compliance rule.

        Args:
            rule_name: Name of the rule
            rule_description: Brief description
            framework: Compliance framework

        Returns:
            Explanation text
        """
        if self.llm is None:
            return self._fallback_rule_explanation(rule_name, rule_description, framework)

        prompt = create_rule_explanation_prompt(
            rule_name=rule_name,
            rule_description=rule_description,
            framework=framework,
        )

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=RULE_EXPLANATION_SYSTEM_PROMPT,
            )
            return response.content

        except Exception as e:
            logger.warning(f"LLM rule explanation failed: {e}, using fallback")
            if self.use_fallback:
                return self._fallback_rule_explanation(rule_name, rule_description, framework)
            raise

    async def generate_batch_remediation(
        self,
        failures: List[Dict[str, Any]],
        design_context: Dict[str, Any],
    ) -> List[ComplianceRemediationResponse]:
        """
        Generate remediation for multiple compliance failures.

        Args:
            failures: List of compliance failures
            design_context: Current design state

        Returns:
            List of remediation responses
        """
        if not failures:
            return []

        if self.llm is None:
            logger.debug("No LLM available, using fallback for batch")
            return [
                self._fallback_remediation(
                    f.get("rule_name", "unknown"),
                    f.get("actual_value"),
                    f.get("required_value"),
                )
                for f in failures
            ]

        prompt = create_batch_remediation_prompt(failures, design_context)

        try:
            response = await self.llm.complete(
                prompt=prompt,
                system_prompt=COMPLIANCE_SYSTEM_PROMPT,
            )

            # Parse JSON array response
            import json
            content = response.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)

            return [
                ComplianceRemediationResponse(**item)
                for item in data
                if isinstance(item, dict)
            ]

        except Exception as e:
            logger.warning(f"LLM batch remediation failed: {e}, using fallback")
            if self.use_fallback:
                return [
                    self._fallback_remediation(
                        f.get("rule_name", "unknown"),
                        f.get("actual_value"),
                        f.get("required_value"),
                    )
                    for f in failures
                ]
            raise

    async def prioritize_failures(
        self,
        failures: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Prioritize compliance failures by severity.

        Args:
            failures: List of compliance failures

        Returns:
            Sorted list with highest priority first
        """
        # Simple deterministic prioritization
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        def get_severity(failure: Dict[str, Any]) -> int:
            # Stability failures are critical
            rule_name = failure.get("rule_name", "").lower()
            if any(term in rule_name for term in ["gm", "gz", "stability"]):
                return 0
            # Freeboard is high
            if "freeboard" in rule_name:
                return 1
            # Default to medium
            return 2

        return sorted(failures, key=get_severity)

    # =========================================================================
    # Fallback Methods
    # =========================================================================

    def _fallback_remediation(
        self,
        rule_name: str,
        actual_value: Any,
        required_value: Any,
    ) -> ComplianceRemediationResponse:
        """Generate deterministic fallback remediation."""
        data = get_fallback_remediation(rule_name, actual_value, required_value)

        actions = [
            RemediationAction(
                action=a["action"],
                parameter=a.get("parameter"),
                suggested_value=a.get("suggested_value"),
                estimated_impact=a.get("estimated_impact"),
                trade_offs=a.get("trade_offs", []),
            )
            for a in data.get("remediation_actions", [])
        ]

        return ComplianceRemediationResponse(
            rule_name=data["rule_name"],
            severity=data.get("severity", "medium"),
            explanation=data["explanation"],
            current_state=data["current_state"],
            required_state=data["required_state"],
            remediation_actions=actions,
            estimated_effort=data.get("estimated_effort"),
        )

    def _fallback_rule_explanation(
        self,
        rule_name: str,
        rule_description: str,
        framework: Optional[str],
    ) -> str:
        """Generate simple rule explanation."""
        framework_name = framework or "maritime regulatory standards"
        return (
            f"{rule_name} is a requirement under {framework_name}.\n\n"
            f"Description: {rule_description}\n\n"
            "This rule ensures vessel safety and regulatory compliance. "
            "Failure to meet this requirement may result in classification issues "
            "or operational restrictions. Consult the relevant regulatory documents "
            "for detailed requirements."
        )

    # =========================================================================
    # Domain-Specific Methods
    # =========================================================================

    async def remediate_gm_failure(
        self,
        gm_actual: float,
        gm_required: float,
        design_context: Dict[str, Any],
    ) -> ComplianceRemediationResponse:
        """
        Generate remediation for GM failure.

        Args:
            gm_actual: Current GM value
            gm_required: Required GM value
            design_context: Design state

        Returns:
            ComplianceRemediationResponse
        """
        return await self.generate_remediation(
            rule_name="Minimum Metacentric Height (GM)",
            rule_description="Minimum initial metacentric height for intact stability",
            actual_value=gm_actual,
            required_value=gm_required,
            design_context=design_context,
            framework="imo_intact",
        )

    async def remediate_freeboard_failure(
        self,
        freeboard_actual: float,
        freeboard_required: float,
        design_context: Dict[str, Any],
    ) -> ComplianceRemediationResponse:
        """
        Generate remediation for freeboard failure.

        Args:
            freeboard_actual: Current freeboard
            freeboard_required: Required freeboard
            design_context: Design state

        Returns:
            ComplianceRemediationResponse
        """
        return await self.generate_remediation(
            rule_name="Minimum Freeboard",
            rule_description="Minimum freeboard for reserve buoyancy and seakeeping",
            actual_value=freeboard_actual,
            required_value=freeboard_required,
            design_context=design_context,
            framework="imo_loadline",
        )

    async def remediate_gz_failure(
        self,
        gz_actual: float,
        gz_required: float,
        angle: float,
        design_context: Dict[str, Any],
    ) -> ComplianceRemediationResponse:
        """
        Generate remediation for GZ curve failure.

        Args:
            gz_actual: Current GZ value
            gz_required: Required GZ value
            angle: Heel angle for the criterion
            design_context: Design state

        Returns:
            ComplianceRemediationResponse
        """
        return await self.generate_remediation(
            rule_name=f"Righting Arm (GZ) at {angle}°",
            rule_description=f"Minimum righting lever arm at {angle} degrees heel",
            actual_value=gz_actual,
            required_value=gz_required,
            design_context=design_context,
            framework="imo_intact",
        )

    async def get_comprehensive_report(
        self,
        failures: List[Dict[str, Any]],
        design_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report with all remediations.

        Args:
            failures: List of compliance failures
            design_context: Design state

        Returns:
            Dict with summary and detailed remediations
        """
        if not failures:
            return {
                "status": "compliant",
                "summary": "All compliance checks passed",
                "failures": [],
                "remediations": [],
            }

        # Prioritize failures
        prioritized = await self.prioritize_failures(failures)

        # Generate remediations
        remediations = await self.generate_batch_remediation(prioritized, design_context)

        # Count by severity
        critical = sum(1 for r in remediations if r.severity == "critical")
        high = sum(1 for r in remediations if r.severity == "high")

        return {
            "status": "non_compliant",
            "summary": f"{len(failures)} compliance failures ({critical} critical, {high} high)",
            "failures": prioritized,
            "remediations": [r.model_dump() for r in remediations],
            "recommended_priority": [
                r.rule_name for r in remediations
                if r.severity in ("critical", "high")
            ],
        }
