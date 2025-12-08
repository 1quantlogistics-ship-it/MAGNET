"""
MAGNET Compliance Rule Checkers (v1.1)

Rule checking hierarchy for evaluating design against regulatory requirements.

v1.1: Verified field names match Module 01 v1.8 StabilityState:
  - stability.angle_of_max_gz_deg (NOT angle_of_maximum_gz_deg)
  - stability.area_0_30_m_rad, area_0_40_m_rad, area_30_40_m_rad
  - stability.gz_max_m, stability.gm_m
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging
import uuid

from .enums import RuleCategory, FindingSeverity
from .rule_schema import RuleRequirement, Finding, RuleReference

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


class RuleChecker(ABC):
    """Abstract base class for rule checkers."""

    @property
    @abstractmethod
    def category(self) -> RuleCategory:
        """Category of rules this checker handles."""
        pass

    @abstractmethod
    def check(
        self,
        rule: RuleRequirement,
        state: "StateManager",
    ) -> Finding:
        """
        Evaluate a rule against current state.

        Args:
            rule: Rule requirement to check
            state: StateManager with current design state

        Returns:
            Finding with evaluation results
        """
        pass

    def _get_value(
        self,
        state: "StateManager",
        path: str,
        default: Any = None,
    ) -> Any:
        """Get value from state using dot-notation path."""
        try:
            parts = path.split(".")
            if len(parts) == 2:
                namespace, key = parts
                return state.read(namespace, key, default)
            return default
        except Exception:
            return default

    def _create_finding(
        self,
        rule: RuleRequirement,
        status: str,
        severity: FindingSeverity,
        message: str,
        actual_value: Any = None,
        required_value: Any = None,
        margin: Optional[float] = None,
        margin_percent: Optional[float] = None,
        remediation: Optional[str] = None,
    ) -> Finding:
        """Create a standardized Finding object."""
        return Finding(
            finding_id=f"F-{uuid.uuid4().hex[:8].upper()}",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=severity,
            status=status,
            message=message,
            actual_value=actual_value,
            required_value=required_value,
            margin=margin,
            margin_percent=margin_percent,
            references=rule.references.copy(),
            remediation_guidance=remediation,
            affected_parameters=rule.required_inputs.copy(),
        )


class StabilityRuleChecker(RuleChecker):
    """
    Checker for stability-related rules.

    Handles ABS HSNC, HSC Code, USCG stability requirements.

    v1.1 Field Names (verified against Module 01 v1.8):
      - stability.gm_m - Metacentric height
      - stability.gz_max_m - Maximum GZ
      - stability.angle_of_max_gz_deg - Angle of max GZ (NOT angle_of_maximum_gz_deg)
      - stability.area_0_30_m_rad - Area under GZ curve 0-30 deg
      - stability.area_0_40_m_rad - Area under GZ curve 0-40 deg
      - stability.area_30_40_m_rad - Area under GZ curve 30-40 deg
      - stability.range_deg - Range of positive stability
      - stability.damage_all_pass - Damage stability status
    """

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.STABILITY

    def check(
        self,
        rule: RuleRequirement,
        state: "StateManager",
    ) -> Finding:
        """Evaluate stability rule."""

        # Check for required inputs
        missing_inputs = []
        input_values = {}

        for input_path in rule.required_inputs:
            value = self._get_value(state, input_path)
            if value is None:
                missing_inputs.append(input_path)
            else:
                input_values[input_path] = value

        if missing_inputs:
            return self._create_finding(
                rule=rule,
                status="incomplete",
                severity=FindingSeverity.WARNING,
                message=f"Missing required inputs: {', '.join(missing_inputs)}",
                remediation="Run stability analysis to generate required data",
            )

        # Evaluate based on rule type
        try:
            return self._evaluate_stability_rule(rule, input_values, state)
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
            return self._create_finding(
                rule=rule,
                status="error",
                severity=FindingSeverity.WARNING,
                message=f"Evaluation error: {str(e)}",
            )

    def _evaluate_stability_rule(
        self,
        rule: RuleRequirement,
        values: Dict[str, Any],
        state: "StateManager",
    ) -> Finding:
        """Evaluate specific stability rule."""

        # Get the primary value to check
        if len(rule.required_inputs) == 0:
            return self._create_finding(
                rule=rule,
                status="error",
                severity=FindingSeverity.WARNING,
                message="No required inputs defined for rule",
            )

        primary_input = rule.required_inputs[0]
        actual_value = values.get(primary_input)

        # Handle formula-based rules (like GM minimum)
        if rule.formula:
            required_value = self._evaluate_formula(rule.formula, values, state)
        else:
            required_value = rule.limit_value

        if required_value is None:
            return self._create_finding(
                rule=rule,
                status="error",
                severity=FindingSeverity.WARNING,
                message="Could not determine required value",
            )

        # Compare values based on limit type
        passes = self._compare_values(actual_value, required_value, rule.limit_type)

        # Calculate margin
        if isinstance(actual_value, (int, float)) and isinstance(required_value, (int, float)):
            margin = actual_value - required_value
            if required_value != 0:
                margin_percent = (margin / abs(required_value)) * 100
            else:
                margin_percent = 0.0 if actual_value == 0 else float('inf')
        else:
            margin = None
            margin_percent = None

        if passes:
            severity = FindingSeverity.PASS
            status = "pass"
            message = f"{rule.name}: {actual_value:.3f} meets requirement of {required_value:.3f}"
            remediation = None
        else:
            if rule.mandatory:
                severity = FindingSeverity.NON_CONFORMANCE
            else:
                severity = FindingSeverity.WARNING
            status = "fail"
            message = f"{rule.name}: {actual_value:.3f} does not meet requirement of {required_value:.3f}"
            remediation = self._generate_stability_remediation(rule, actual_value, required_value)

        return self._create_finding(
            rule=rule,
            status=status,
            severity=severity,
            message=message,
            actual_value=actual_value,
            required_value=required_value,
            margin=margin,
            margin_percent=margin_percent,
            remediation=remediation,
        )

    def _evaluate_formula(
        self,
        formula: str,
        values: Dict[str, Any],
        state: "StateManager",
    ) -> Optional[float]:
        """Evaluate formula string to get required value."""

        # Handle common formulas
        if "max(" in formula:
            # Parse max(a, b*c) format
            # Example: max(0.15, 0.04 * beam)
            beam = self._get_value(state, "hull.beam", 0)
            if "0.04 * beam" in formula or "0.04*beam" in formula:
                return max(0.15, 0.04 * beam)

        # Simple numeric limit
        try:
            return float(formula)
        except ValueError:
            return None

    def _compare_values(
        self,
        actual: Any,
        required: Any,
        limit_type: str,
    ) -> bool:
        """Compare actual value against required based on limit type."""
        if limit_type == "minimum":
            return actual >= required
        elif limit_type == "maximum":
            return actual <= required
        elif limit_type == "exact":
            return abs(actual - required) < 0.001
        else:
            return actual >= required  # Default to minimum

    def _generate_stability_remediation(
        self,
        rule: RuleRequirement,
        actual: Any,
        required: Any,
    ) -> str:
        """Generate remediation guidance for stability failures."""

        if "GM" in rule.name:
            return (
                f"Increase metacentric height by lowering VCG or increasing beam. "
                f"Required improvement: {required - actual:.3f}m"
            )
        elif "Area" in rule.name:
            return (
                f"Increase righting arm area by improving GZ curve. "
                f"Consider lowering VCG or increasing freeboard."
            )
        elif "GZ" in rule.name and "Angle" not in rule.name:
            return (
                f"Increase maximum righting arm. "
                f"Consider lowering VCG or optimizing hull form."
            )
        elif "Angle" in rule.name:
            return (
                f"Angle of maximum GZ is too low. "
                f"Review hull form and weight distribution."
            )
        elif "Range" in rule.name:
            return (
                f"Increase range of positive stability. "
                f"Review hull form for adequate reserve buoyancy."
            )
        else:
            return f"Review stability parameters to meet requirement of {required}"


class StructuralRuleChecker(RuleChecker):
    """
    Checker for structural rules.

    Handles plate thickness, scantling, and structural requirements.
    """

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.STRUCTURAL

    def check(
        self,
        rule: RuleRequirement,
        state: "StateManager",
    ) -> Finding:
        """Evaluate structural rule."""

        # Check for required inputs
        missing_inputs = []
        input_values = {}

        for input_path in rule.required_inputs:
            value = self._get_value(state, input_path)
            if value is None:
                missing_inputs.append(input_path)
            else:
                input_values[input_path] = value

        if missing_inputs:
            return self._create_finding(
                rule=rule,
                status="incomplete",
                severity=FindingSeverity.WARNING,
                message=f"Missing required inputs: {', '.join(missing_inputs)}",
                remediation="Structural analysis required to determine scantlings",
            )

        # Structural rules often require complex calculations
        # For now, flag as review_required unless we have specific formulas
        return self._create_finding(
            rule=rule,
            status="review_required",
            severity=FindingSeverity.ADVISORY,
            message=f"{rule.name}: Requires detailed structural analysis",
            remediation="Perform FEA or classification society scantling calculations",
        )


class FreeboardRuleChecker(RuleChecker):
    """
    Checker for freeboard rules.

    Handles minimum freeboard and reserve buoyancy requirements.
    """

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.FREEBOARD

    def check(
        self,
        rule: RuleRequirement,
        state: "StateManager",
    ) -> Finding:
        """Evaluate freeboard rule."""

        # Check for required inputs
        missing_inputs = []
        input_values = {}

        for input_path in rule.required_inputs:
            value = self._get_value(state, input_path)
            if value is None:
                missing_inputs.append(input_path)
            else:
                input_values[input_path] = value

        if missing_inputs:
            return self._create_finding(
                rule=rule,
                status="incomplete",
                severity=FindingSeverity.WARNING,
                message=f"Missing required inputs: {', '.join(missing_inputs)}",
                remediation="Calculate freeboard from hull geometry and loading conditions",
            )

        freeboard = input_values.get("hull.freeboard", 0)
        lwl = input_values.get("hull.lwl", 0)

        # Basic freeboard check - minimum 0.3m or LWL-based
        if lwl > 0:
            min_freeboard = max(0.3, lwl * 0.01)  # Simplified rule
        else:
            min_freeboard = 0.3

        if freeboard >= min_freeboard:
            return self._create_finding(
                rule=rule,
                status="pass",
                severity=FindingSeverity.PASS,
                message=f"Freeboard {freeboard:.2f}m meets minimum {min_freeboard:.2f}m",
                actual_value=freeboard,
                required_value=min_freeboard,
                margin=freeboard - min_freeboard,
                margin_percent=((freeboard - min_freeboard) / min_freeboard) * 100 if min_freeboard > 0 else 0,
            )
        else:
            return self._create_finding(
                rule=rule,
                status="fail",
                severity=FindingSeverity.NON_CONFORMANCE if rule.mandatory else FindingSeverity.WARNING,
                message=f"Freeboard {freeboard:.2f}m below minimum {min_freeboard:.2f}m",
                actual_value=freeboard,
                required_value=min_freeboard,
                margin=freeboard - min_freeboard,
                margin_percent=((freeboard - min_freeboard) / min_freeboard) * 100 if min_freeboard > 0 else 0,
                remediation="Increase hull depth or reduce loaded draft",
            )


# Checker registry
RULE_CHECKERS: Dict[RuleCategory, RuleChecker] = {
    RuleCategory.STABILITY: StabilityRuleChecker(),
    RuleCategory.STRUCTURAL: StructuralRuleChecker(),
    RuleCategory.FREEBOARD: FreeboardRuleChecker(),
}


def get_checker(category: RuleCategory) -> Optional[RuleChecker]:
    """Get appropriate checker for a rule category."""
    return RULE_CHECKERS.get(category)
