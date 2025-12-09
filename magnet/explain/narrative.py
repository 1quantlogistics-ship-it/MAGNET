"""
explain/narrative.py - Generate human-readable narratives
BRAVO OWNS THIS FILE.

Section 42: Explanation Engine
v1.1: Fixed speed field naming with aliases
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid

from .schemas import (
    Explanation, ExplanationLevel, ParameterDiff,
    ValidatorSummary, Warning
)

if TYPE_CHECKING:
    from magnet.protocol.schemas import ValidationResult


# v1.1: Parameter name mappings with aliases
PARAMETER_NAMES = {
    # Hull
    "hull.loa": "Length Overall",
    "hull.lwl": "Waterline Length",
    "hull.beam": "Beam",
    "hull.draft": "Draft",
    "hull.depth": "Depth",
    "hull.cb": "Block Coefficient",
    "hull.displacement_mt": "Displacement",

    # Performance - v1.1: Multiple aliases
    "performance.max_speed_kts": "Maximum Speed",
    "performance.max_speed_knots": "Maximum Speed",  # Alias
    "performance.cruise_speed_kts": "Cruise Speed",
    "performance.cruise_speed_knots": "Cruise Speed",  # Alias
    "performance.range_nm": "Range",

    # Stability
    "stability.gm_transverse_m": "Transverse GM",
    "stability.gz_max": "Maximum GZ",

    # Structure
    "structure.plating.bottom_thickness_mm": "Bottom Plating",
    "structure.plating.side_thickness_mm": "Side Plating",

    # Propulsion
    "propulsion.installed_power_kw": "Installed Power",
    "propulsion.total_installed_power_kw": "Installed Power",  # Alias
}


class NarrativeGenerator:
    """
    Generates human-readable narratives from design data.
    """

    def __init__(self):
        self.parameter_names = PARAMETER_NAMES.copy()

    def get_parameter_name(self, path: str) -> str:
        """Get human-readable name for parameter."""
        if path in self.parameter_names:
            return self.parameter_names[path]

        # Generate from path
        parts = path.split('.')
        name = parts[-1].replace('_', ' ').title()
        return name

    def generate_explanation(
        self,
        level: ExplanationLevel,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
        validation_result: Optional["ValidationResult"] = None,
    ) -> Explanation:
        """Generate explanation for state change."""
        explanation = Explanation(
            explanation_id=str(uuid.uuid4())[:8],
            level=level,
        )

        # Generate parameter diffs
        explanation.parameter_diffs = self._generate_diffs(old_state, new_state)

        # Process validation results
        if validation_result:
            explanation.validator_summaries = self._summarize_validation(validation_result)
            explanation.warnings = self._extract_warnings(validation_result)

        # Generate narrative
        explanation.summary = self._generate_summary(explanation)

        if level in [ExplanationLevel.STANDARD, ExplanationLevel.DETAILED, ExplanationLevel.EXPERT]:
            explanation.narrative = self._generate_narrative(explanation, level)

        # Generate next steps
        explanation.next_steps = self._generate_next_steps(explanation)

        return explanation

    def _generate_diffs(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
    ) -> List[ParameterDiff]:
        """Generate parameter diffs."""
        diffs = []

        def compare_dicts(old: Dict, new: Dict, prefix: str = ""):
            for key in set(list(old.keys()) + list(new.keys())):
                path = f"{prefix}.{key}" if prefix else key
                old_val = old.get(key)
                new_val = new.get(key)

                if isinstance(old_val, dict) and isinstance(new_val, dict):
                    compare_dicts(old_val, new_val, path)
                elif old_val != new_val:
                    diff = ParameterDiff(
                        path=path,
                        name=self.get_parameter_name(path),
                        old_value=old_val,
                        new_value=new_val,
                    )

                    # Calculate change percent
                    if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)) and old_val != 0:
                        diff.change_percent = ((new_val - old_val) / abs(old_val)) * 100

                        # Determine significance
                        if abs(diff.change_percent) > 20:
                            diff.significance = "major"
                        elif abs(diff.change_percent) > 10:
                            diff.significance = "normal"
                        else:
                            diff.significance = "minor"

                    diffs.append(diff)

        compare_dicts(old_state, new_state)
        return diffs

    def _summarize_validation(
        self,
        result: "ValidationResult",
    ) -> List[ValidatorSummary]:
        """Summarize validation results."""
        summaries = []

        # Group findings by validator
        by_validator: Dict[str, List] = {}
        for finding in result.findings:
            # v1.1: Handle missing validator_name
            validator = getattr(finding, 'validator_name', None) or 'unknown'
            if validator not in by_validator:
                by_validator[validator] = []
            by_validator[validator].append(finding)

        for validator_name, findings in by_validator.items():
            errors = sum(1 for f in findings if f.severity == "error")
            warnings = sum(1 for f in findings if f.severity == "warning")

            summary = ValidatorSummary(
                validator_name=validator_name,
                passed=errors == 0,
                error_count=errors,
                warning_count=warnings,
                key_message=findings[0].message if findings else "",
            )
            summaries.append(summary)

        return summaries

    def _extract_warnings(
        self,
        result: "ValidationResult",
    ) -> List[Warning]:
        """Extract warnings from validation."""
        warnings = []

        for finding in result.findings:
            if finding.severity in ["warning", "error", "critical"]:
                warning = Warning(
                    severity=finding.severity,
                    category=getattr(finding, 'validator_name', None) or 'validation',
                    message=finding.message,
                    suggestion=getattr(finding, 'suggestion', ''),
                )
                warnings.append(warning)

        return warnings

    def _generate_summary(self, explanation: Explanation) -> str:
        """Generate one-line summary."""
        parts = []

        # Count changes
        if explanation.parameter_diffs:
            parts.append(f"{len(explanation.parameter_diffs)} parameter(s) changed")

        # Validation status
        passed = all(v.passed for v in explanation.validator_summaries)
        if explanation.validator_summaries:
            if passed:
                parts.append("all checks passed")
            else:
                error_count = sum(v.error_count for v in explanation.validator_summaries)
                parts.append(f"{error_count} issue(s) found")

        return "; ".join(parts) if parts else "No significant changes"

    def _generate_narrative(
        self,
        explanation: Explanation,
        level: ExplanationLevel,
    ) -> str:
        """Generate detailed narrative."""
        paragraphs = []

        # Changes section
        if explanation.parameter_diffs:
            major_changes = [d for d in explanation.parameter_diffs if d.significance in ["major", "critical"]]

            if major_changes:
                change_text = []
                for diff in major_changes[:5]:
                    if diff.change_percent is not None:
                        change_text.append(
                            f"{diff.name} changed from {diff.old_value} to {diff.new_value} "
                            f"({diff.change_percent:+.1f}%)"
                        )
                    else:
                        change_text.append(
                            f"{diff.name} changed from {diff.old_value} to {diff.new_value}"
                        )

                paragraphs.append("Key changes: " + "; ".join(change_text) + ".")

        # Validation section
        if explanation.validator_summaries:
            passed_validators = [v for v in explanation.validator_summaries if v.passed]
            failed_validators = [v for v in explanation.validator_summaries if not v.passed]

            if failed_validators:
                issues = []
                for v in failed_validators[:3]:
                    issues.append(f"{v.validator_name}: {v.key_message}")
                paragraphs.append("Issues found: " + "; ".join(issues))

            if passed_validators and level == ExplanationLevel.DETAILED:
                paragraphs.append(
                    f"{len(passed_validators)} validator(s) passed: "
                    f"{', '.join(v.validator_name for v in passed_validators)}"
                )

        return "\n\n".join(paragraphs)

    def _generate_next_steps(self, explanation: Explanation) -> List[str]:
        """Generate recommended next steps."""
        steps = []

        # Based on warnings
        for warning in explanation.warnings[:3]:
            if warning.suggestion:
                steps.append(warning.suggestion)

        # Based on validation
        failed = [v for v in explanation.validator_summaries if not v.passed]
        if failed:
            steps.append(f"Address {len(failed)} failed validation(s)")

        if not steps:
            steps.append("Review changes and proceed to next phase")

        return steps
