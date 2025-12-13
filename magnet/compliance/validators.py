"""
MAGNET Compliance Validators (v1.1)

Validator interface implementations for compliance checking.

v1.1 Outputs (per directive):
  - compliance.status - Overall compliance status
  - compliance.pass_count - Number of passing rules
  - compliance.fail_count - Number of failing rules
  - compliance.findings - List of findings (determinized)
  - compliance.report - Full report (determinized)
  - compliance.frameworks_checked - List of checked frameworks
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging
import uuid

from .enums import RegulatoryFramework, RuleCategory, ComplianceStatus
from .engine import ComplianceEngine, ComplianceReport
from .rule_library import RULE_LIBRARY

from ..validators.taxonomy import (
    ValidatorInterface,
    ValidatorDefinition,
    ValidatorCategory,
    ValidatorPriority,
    ValidatorState,
    ValidationResult,
    ValidationFinding,
    ResultSeverity,
)

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


def determinize_dict(data: Dict[str, Any], precision: int = 6) -> Dict[str, Any]:
    """
    Make dictionary deterministic for hashing/caching.

    - Sorts all keys recursively
    - Rounds floats to consistent precision
    - Ensures consistent JSON serialization
    """
    if isinstance(data, dict):
        return {k: determinize_dict(v, precision) for k, v in sorted(data.items())}
    elif isinstance(data, list):
        return [determinize_dict(item, precision) for item in data]
    elif isinstance(data, float):
        return round(data, precision)
    else:
        return data


class ComplianceValidator(ValidatorInterface):
    """
    Main compliance validation interface.

    Reads:
        hull.lwl, hull.beam, hull.depth, hull.draft
        stability.gm_m, stability.gz_max_m, stability.angle_of_max_gz_deg
        stability.area_0_30_m_rad, stability.area_0_40_m_rad, stability.area_30_40_m_rad
        mission.vessel_type
        compliance.frameworks (optional - defaults to ABS_HSNC)

    Writes:
        compliance.status - Overall status (compliant, non_compliant, review_required)
        compliance.pass_count - Number of passing rules
        compliance.fail_count - Number of failing rules
        compliance.incomplete_count - Number of incomplete checks
        compliance.findings - Determinized list of findings
        compliance.report - Determinized full report
        compliance.frameworks_checked - List of frameworks evaluated
        compliance.pass_rate - Percentage of passed rules
    """

    def __init__(self, definition: ValidatorDefinition):
        super().__init__(definition)
        self.engine = ComplianceEngine(RULE_LIBRARY)

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """
        Run compliance validation.

        Args:
            state_manager: StateManager with current design state
            context: Validation context

        Returns:
            ValidationResult with compliance status
        """
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Get vessel info
            lwl = state_manager.get("hull.lwl", 0)
            vessel_type = state_manager.get("mission.vessel_type", "patrol")
            vessel_name = state_manager.get("mission.vessel_name", "Unnamed Vessel")

            # Get frameworks to check (default to ABS HSNC)
            framework_values = state_manager.get("compliance.frameworks", None)
            if framework_values is None:
                frameworks = [RegulatoryFramework.ABS_HSNC]
            elif isinstance(framework_values, list):
                frameworks = []
                for fv in framework_values:
                    try:
                        if isinstance(fv, RegulatoryFramework):
                            frameworks.append(fv)
                        else:
                            frameworks.append(RegulatoryFramework(fv))
                    except ValueError:
                        result.add_finding(ValidationFinding(
                            finding_id=str(uuid.uuid4())[:8],
                            severity=ResultSeverity.WARNING,
                            message=f"Unknown framework: {fv}",
                            parameter_path=f"compliance.frameworks.{fv}",
                        ))
                if not frameworks:
                    frameworks = [RegulatoryFramework.ABS_HSNC]
            else:
                frameworks = [RegulatoryFramework.ABS_HSNC]

            # Run compliance evaluation
            report = self.engine.evaluate(
                state=state_manager,
                frameworks=frameworks,
                vessel_type=vessel_type,
                length_m=lwl,
                vessel_name=vessel_name,
            )

            # Write results to state
            source = "compliance/regulatory"
            state_manager.set("compliance.status", report.overall_status.value, source)
            state_manager.set("compliance.pass_count", report.pass_count, source)
            state_manager.set("compliance.fail_count", report.fail_count, source)
            state_manager.set("compliance.incomplete_count", report.incomplete_count, source)
            state_manager.set("compliance.pass_rate", report.get_pass_rate(), source)

            # Determinize findings for state storage
            findings_data = [f.to_dict() for f in report.findings]
            state_manager.set("compliance.findings", determinize_dict({"items": findings_data}), source)

            # Determinize full report
            report_data = report.to_dict()
            state_manager.set("compliance.report", determinize_dict(report_data), source)

            # Frameworks checked
            state_manager.set("compliance.frameworks_checked", [f.value for f in frameworks], source)

            # Generate validation findings from compliance findings
            for finding in report.findings:
                if finding.status == "fail":
                    severity = ResultSeverity.ERROR if finding.severity.value in ["critical", "non_conformance"] else ResultSeverity.WARNING
                    result.add_finding(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=severity,
                        message=finding.message,
                        parameter_path=finding.rule_id,
                        suggestion=finding.remediation_guidance,
                    ))
                elif finding.status == "incomplete":
                    result.add_finding(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.WARNING,
                        message=finding.message,
                        parameter_path=finding.rule_id,
                    ))
                elif finding.status == "pass":
                    result.add_finding(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.INFO,
                        message=finding.message,
                        parameter_path=finding.rule_id,
                    ))

            # Determine final state
            if report.overall_status in [ComplianceStatus.COMPLIANT, ComplianceStatus.CONDITIONALLY_COMPLIANT]:
                result.state = ValidatorState.PASSED
            elif result.error_count > 0:
                result.state = ValidatorState.FAILED
            else:
                result.state = ValidatorState.WARNING

            result.completed_at = datetime.now(timezone.utc)

            logger.info(
                f"Compliance validation: {report.pass_count}/{report.total_rules} rules passed, "
                f"status={report.overall_status.value}"
            )

            return result

        except Exception as e:
            logger.error(f"Compliance validation error: {e}")
            result.state = ValidatorState.ERROR
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc)
            return result


class StabilityComplianceValidator(ValidatorInterface):
    """
    Focused stability compliance check.

    Specifically evaluates stability rules without full compliance suite.
    Useful for quick stability-specific validation.

    Reads:
        stability.gm_m, stability.gz_max_m, stability.angle_of_max_gz_deg
        stability.area_0_30_m_rad, stability.area_0_40_m_rad, stability.area_30_40_m_rad
        stability.range_deg

    Writes:
        compliance.stability_status - Stability-specific compliance status
        compliance.stability_pass_count - Stability rules passed
        compliance.stability_fail_count - Stability rules failed
    """

    def __init__(self, definition: ValidatorDefinition):
        super().__init__(definition)
        self.engine = ComplianceEngine(RULE_LIBRARY)

    def validate(
        self,
        state_manager: "StateManager",
        context: Dict[str, Any]
    ) -> ValidationResult:
        """Run stability-focused compliance check."""
        result = ValidationResult(
            validator_id=self.definition.validator_id,
            state=ValidatorState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

        try:
            # Evaluate stability category only
            findings = self.engine.evaluate_category(
                state=state_manager,
                category=RuleCategory.STABILITY,
                frameworks=[RegulatoryFramework.ABS_HSNC],
            )

            pass_count = sum(1 for f in findings if f.status == "pass")
            fail_count = sum(1 for f in findings if f.status == "fail")

            # Determine status
            if fail_count == 0 and pass_count > 0:
                status = "compliant"
            elif fail_count > 0:
                status = "non_compliant"
            else:
                status = "review_required"

            # Write results
            source = "compliance/stability_check"
            state_manager.set("compliance.stability_status", status, source)
            state_manager.set("compliance.stability_pass_count", pass_count, source)
            state_manager.set("compliance.stability_fail_count", fail_count, source)

            # Generate validation findings
            for finding in findings:
                if finding.status == "fail":
                    result.add_finding(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.ERROR,
                        message=finding.message,
                        parameter_path=finding.rule_id,
                        suggestion=finding.remediation_guidance,
                    ))
                elif finding.status == "pass":
                    result.add_finding(ValidationFinding(
                        finding_id=str(uuid.uuid4())[:8],
                        severity=ResultSeverity.INFO,
                        message=finding.message,
                        parameter_path=finding.rule_id,
                    ))

            # Determine final state
            if fail_count == 0:
                result.state = ValidatorState.PASSED
            else:
                result.state = ValidatorState.FAILED

            result.completed_at = datetime.now(timezone.utc)
            return result

        except Exception as e:
            logger.error(f"Stability compliance error: {e}")
            result.state = ValidatorState.ERROR
            result.error_message = str(e)
            result.completed_at = datetime.now(timezone.utc)
            return result


# =============================================================================
# VALIDATOR DEFINITION FACTORY
# =============================================================================

def get_compliance_validator_definition() -> ValidatorDefinition:
    """Create ValidatorDefinition for compliance/regulatory validator."""
    return ValidatorDefinition(
        validator_id="compliance/regulatory",
        name="Regulatory Compliance Engine",
        description="Evaluates design against ABS HSNC, HSC Code, USCG rules (v1.1)",
        category=ValidatorCategory.REGULATORY,
        priority=ValidatorPriority.HIGH,
        phase="compliance",
        is_gate_condition=True,
        depends_on_validators=["stability/intact_gm", "stability/gz_curve"],
        depends_on_parameters=[
            "hull.lwl", "hull.beam", "mission.vessel_type",
            "stability.gm_m", "stability.gz_max_m", "stability.angle_of_max_gz_deg",
            "stability.area_0_30_m_rad", "stability.area_0_40_m_rad", "stability.area_30_40_m_rad",
        ],
        produces_parameters=[
            "compliance.status",
            "compliance.pass_count",
            "compliance.fail_count",
            "compliance.incomplete_count",
            "compliance.findings",
            "compliance.report",
            "compliance.frameworks_checked",
            "compliance.pass_rate",
        ],
        tags=["compliance", "regulatory", "abs", "hsc", "uscg", "v1.1"],
    )


def get_stability_compliance_definition() -> ValidatorDefinition:
    """Create ValidatorDefinition for compliance/stability validator."""
    return ValidatorDefinition(
        validator_id="compliance/stability",
        name="Stability Compliance Check",
        description="Focused stability rules compliance check (v1.1)",
        category=ValidatorCategory.REGULATORY,
        priority=ValidatorPriority.NORMAL,
        phase="compliance",
        is_gate_condition=False,
        depends_on_validators=["stability/gz_curve"],
        depends_on_parameters=[
            "stability.gm_m", "stability.gz_max_m",
        ],
        produces_parameters=[
            "compliance.stability_status",
            "compliance.stability_pass_count",
            "compliance.stability_fail_count",
        ],
        tags=["compliance", "stability", "v1.1"],
    )


def register_compliance_validators():
    """Register compliance validators with the pipeline."""
    # This would be called by the main validator registry
    return [
        (get_compliance_validator_definition(), ComplianceValidator),
        (get_stability_compliance_definition(), StabilityComplianceValidator),
    ]
