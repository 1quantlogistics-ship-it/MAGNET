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
    from magnet.kernel.enriched_delta import EnrichedDelta, DeltaSummary
    from magnet.kernel.program_executor import ExecutionResult


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

    # =========================================================================
    # Phase 5: Geometry-Specific Narrative Generation
    # Reference: MAGNET_Merge_Implementation_Plan.md
    # =========================================================================

    def generate_geometry_narrative(
        self,
        exec_result: Optional["ExecutionResult"] = None,
        deltas: Optional[List["EnrichedDelta"]] = None,
        level: ExplanationLevel = ExplanationLevel.STANDARD,
    ) -> str:
        """
        Generate narrative for geometry execution result.
        
        This is the NEW PATH feedback generation that works with
        geometry primitives instead of hull types.
        
        Args:
            exec_result: ExecutionResult from program_executor
            deltas: List of EnrichedDeltas showing what changed
            level: Detail level for narrative
        
        Returns:
            Human-readable narrative string
        """
        paragraphs = []
        
        # Geometry execution summary
        if exec_result:
            paragraphs.append(self._format_geometry_execution(exec_result))
        
        # Delta summary with directions
        if deltas:
            paragraphs.append(self._format_deltas(deltas, level))
        
        # Validation summary
        if exec_result and exec_result.validation:
            paragraphs.append(self._format_geometry_validation(exec_result.validation))
        
        # Recommendations
        recommendations = self._generate_geometry_recommendations(exec_result, deltas)
        if recommendations:
            paragraphs.append("**Recommendations:**\n" + "\n".join(f"- {r}" for r in recommendations))
        
        return "\n\n".join(p for p in paragraphs if p)

    def _format_geometry_execution(self, exec_result: "ExecutionResult") -> str:
        """Format geometry execution summary."""
        if exec_result.success:
            action_count = len(exec_result.actions) if exec_result.actions else 0
            return f"✅ **Geometry compiled successfully** ({action_count} actions executed)"
        else:
            errors = exec_result.errors or []
            error_text = "; ".join(errors[:3])
            return f"❌ **Geometry compilation failed**: {error_text}"

    def _format_deltas(
        self,
        deltas: List["EnrichedDelta"],
        level: ExplanationLevel,
    ) -> str:
        """Format deltas with direction indicators."""
        if not deltas:
            return ""
        
        # Group by direction
        improved = [d for d in deltas if d.direction == "improved"]
        degraded = [d for d in deltas if d.direction == "degraded"]
        neutral = [d for d in deltas if d.direction == "neutral"]
        
        lines = ["**Changes:**"]
        
        # Show improved first
        for delta in improved[:5]:
            lines.append(f"  ✅ {delta.format_for_display()}")
        
        # Then degraded
        for delta in degraded[:5]:
            lines.append(f"  ⚠️ {delta.format_for_display()}")
        
        # Then neutral (only at detailed level)
        if level in [ExplanationLevel.DETAILED, ExplanationLevel.EXPERT]:
            for delta in neutral[:3]:
                lines.append(f"  ➡️ {delta.format_for_display()}")
        
        # Summary line
        summary_parts = []
        if improved:
            summary_parts.append(f"{len(improved)} improved")
        if degraded:
            summary_parts.append(f"{len(degraded)} degraded")
        if neutral and level == ExplanationLevel.EXPERT:
            summary_parts.append(f"{len(neutral)} unchanged")
        
        if summary_parts:
            lines.append(f"\n*Summary: {', '.join(summary_parts)}*")
        
        return "\n".join(lines)

    def _format_geometry_validation(self, validation: Dict[str, Any]) -> str:
        """Format validation results from geometry execution."""
        lines = ["**Validation:**"]
        
        # Hydrostatics
        hydro = validation.get("hydrostatics", {})
        if hydro:
            gm = hydro.get("gm_m")
            if gm is not None:
                status = "✅" if gm >= 0.5 else "⚠️"
                lines.append(f"  {status} GM: {gm:.2f}m")
            
            displacement = hydro.get("displacement_m3")
            if displacement is not None:
                lines.append(f"  📊 Displacement: {displacement:.1f}m³")
        
        # Resistance
        resist = validation.get("resistance", {})
        if resist:
            resistance = resist.get("resistance_kn")
            method_valid = resist.get("method_valid", True)
            validity_note = resist.get("validity_note", "")
            
            if resistance is not None:
                lines.append(f"  🚀 Resistance: {resistance:.1f}kN")
            
            # Surface validity warnings when method is not valid
            if not method_valid and validity_note:
                lines.append(f"  ⚠️  Resistance validity: {validity_note}")
        
        # Constraint violations
        violations = validation.get("constraint_violations", [])
        if violations:
            lines.append(f"  ❌ {len(violations)} constraint violation(s)")
            for v in violations[:3]:
                lines.append(f"     - {v.get('path')}: required {v.get('required')}, actual {v.get('actual')}")
        
        return "\n".join(lines) if len(lines) > 1 else ""

    def _generate_geometry_recommendations(
        self,
        exec_result: Optional["ExecutionResult"],
        deltas: Optional[List["EnrichedDelta"]],
    ) -> List[str]:
        """Generate recommendations based on geometry results."""
        recommendations = []
        
        if exec_result and not exec_result.success:
            recommendations.append("Fix geometry errors before proceeding")
            return recommendations
        
        if exec_result and exec_result.validation:
            hydro = exec_result.validation.get("hydrostatics", {})
            gm = hydro.get("gm_m")
            
            if gm is not None and gm < 0.5:
                recommendations.append(
                    f"GM ({gm:.2f}m) is below 0.5m — consider increasing beam or lowering VCG"
                )
            
            violations = exec_result.validation.get("constraint_violations", [])
            if violations:
                for v in violations[:2]:
                    path = v.get("path", "unknown")
                    recommendations.append(f"Address constraint violation: {path}")
        
        if deltas:
            degraded = [d for d in deltas if d.direction == "degraded"]
            if degraded:
                worst = max(degraded, key=lambda d: abs(d.percent_change or 0))
                recommendations.append(
                    f"Review {worst.display_name} degradation ({worst.percent_change:+.1f}%)"
                )
        
        if not recommendations:
            recommendations.append("Design looks good — proceed to next iteration or finalize")
        
        return recommendations
