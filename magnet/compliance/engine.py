"""
MAGNET Compliance Engine (v1.1)

Central compliance evaluation engine.

v1.1: Writes determinized compliance.report to state.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging

from .enums import RegulatoryFramework, RuleCategory, FindingSeverity, ComplianceStatus
from .rule_schema import RuleRequirement, Finding
from .rule_library import RuleLibrary, RULE_LIBRARY
from .checkers import get_checker, RuleChecker

if TYPE_CHECKING:
    from ..core.state_manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class ComplianceReport:
    """Complete compliance evaluation report."""

    report_id: str
    vessel_name: str
    vessel_type: str
    frameworks_checked: List[RegulatoryFramework]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Results
    overall_status: ComplianceStatus = ComplianceStatus.REVIEW_REQUIRED
    total_rules: int = 0
    pass_count: int = 0
    fail_count: int = 0
    incomplete_count: int = 0
    review_count: int = 0

    # Findings by category
    findings: List[Finding] = field(default_factory=list)
    findings_by_category: Dict[str, List[Finding]] = field(default_factory=dict)
    findings_by_framework: Dict[str, List[Finding]] = field(default_factory=dict)

    # Critical items
    critical_findings: List[Finding] = field(default_factory=list)
    non_conformances: List[Finding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "report_id": self.report_id,
            "vessel_name": self.vessel_name,
            "vessel_type": self.vessel_type,
            "frameworks_checked": [f.value for f in self.frameworks_checked],
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "summary": {
                "total_rules": self.total_rules,
                "pass_count": self.pass_count,
                "fail_count": self.fail_count,
                "incomplete_count": self.incomplete_count,
                "review_count": self.review_count,
            },
            "findings": [f.to_dict() for f in self.findings],
            "critical_findings": [f.to_dict() for f in self.critical_findings],
            "non_conformances": [f.to_dict() for f in self.non_conformances],
        }

    def get_pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        evaluated = self.pass_count + self.fail_count
        if evaluated == 0:
            return 0.0
        return (self.pass_count / evaluated) * 100


class ComplianceEngine:
    """
    Central compliance evaluation engine.

    Coordinates rule lookup, checking, and report generation.

    v1.1 Features:
    - Multi-framework support (ABS HSNC, HSC Code, USCG)
    - Category-specific checkers
    - Determinized report output for state caching
    """

    def __init__(self, rule_library: Optional[RuleLibrary] = None):
        """
        Initialize compliance engine.

        Args:
            rule_library: Rule library to use (defaults to RULE_LIBRARY singleton)
        """
        self.rule_library = rule_library or RULE_LIBRARY
        self._custom_checkers: Dict[RuleCategory, RuleChecker] = {}

    def register_checker(self, category: RuleCategory, checker: RuleChecker) -> None:
        """Register a custom checker for a category."""
        self._custom_checkers[category] = checker

    def get_checker(self, category: RuleCategory) -> Optional[RuleChecker]:
        """Get checker for category, preferring custom over default."""
        return self._custom_checkers.get(category) or get_checker(category)

    def evaluate(
        self,
        state: "StateManager",
        frameworks: List[RegulatoryFramework],
        vessel_type: str,
        length_m: float,
        vessel_name: str = "Unnamed Vessel",
    ) -> ComplianceReport:
        """
        Evaluate design against specified frameworks.

        Args:
            state: StateManager with current design state
            frameworks: List of regulatory frameworks to check
            vessel_type: Type of vessel (e.g., "ferry", "patrol")
            length_m: Vessel length for rule applicability
            vessel_name: Name of vessel for report

        Returns:
            ComplianceReport with all findings
        """
        import uuid

        report = ComplianceReport(
            report_id=f"CR-{uuid.uuid4().hex[:8].upper()}",
            vessel_name=vessel_name,
            vessel_type=vessel_type,
            frameworks_checked=frameworks,
        )

        # Gather applicable rules from all frameworks
        all_rules = []
        for framework in frameworks:
            rules = self.rule_library.get_applicable_rules(framework, vessel_type, length_m)
            all_rules.extend(rules)
            logger.debug(f"Found {len(rules)} applicable rules for {framework.value}")

        report.total_rules = len(all_rules)

        # Evaluate each rule
        for rule in all_rules:
            checker = self.get_checker(rule.category)

            if checker is None:
                # No checker available - mark as review required
                finding = Finding(
                    finding_id=f"F-{uuid.uuid4().hex[:8].upper()}",
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=FindingSeverity.ADVISORY,
                    status="review_required",
                    message=f"No automated checker for {rule.category.value} rules",
                    references=rule.references.copy(),
                )
            else:
                finding = checker.check(rule, state)

            # Add finding to report
            report.findings.append(finding)

            # Categorize by status
            if finding.status == "pass":
                report.pass_count += 1
            elif finding.status == "fail":
                report.fail_count += 1
                if finding.severity == FindingSeverity.NON_CONFORMANCE:
                    report.non_conformances.append(finding)
                elif finding.severity == FindingSeverity.CRITICAL:
                    report.critical_findings.append(finding)
            elif finding.status == "incomplete":
                report.incomplete_count += 1
            else:  # review_required, error
                report.review_count += 1

            # Group by category
            cat_key = rule.category.value
            if cat_key not in report.findings_by_category:
                report.findings_by_category[cat_key] = []
            report.findings_by_category[cat_key].append(finding)

            # Group by framework
            fw_key = rule.framework.value
            if fw_key not in report.findings_by_framework:
                report.findings_by_framework[fw_key] = []
            report.findings_by_framework[fw_key].append(finding)

        # Determine overall status
        report.overall_status = self._determine_status(report)

        logger.info(
            f"Compliance evaluation complete: {report.pass_count}/{report.total_rules} passed, "
            f"status={report.overall_status.value}"
        )

        return report

    def evaluate_single_framework(
        self,
        state: "StateManager",
        framework: RegulatoryFramework,
        vessel_type: str,
        length_m: float,
        vessel_name: str = "Unnamed Vessel",
    ) -> ComplianceReport:
        """Convenience method to evaluate single framework."""
        return self.evaluate(
            state=state,
            frameworks=[framework],
            vessel_type=vessel_type,
            length_m=length_m,
            vessel_name=vessel_name,
        )

    def evaluate_category(
        self,
        state: "StateManager",
        category: RuleCategory,
        frameworks: Optional[List[RegulatoryFramework]] = None,
    ) -> List[Finding]:
        """
        Evaluate all rules in a specific category.

        Args:
            state: StateManager with design state
            category: Category to evaluate
            frameworks: Limit to these frameworks (None = all)

        Returns:
            List of findings for the category
        """
        rules = self.rule_library.get_by_category(category)

        if frameworks:
            rules = [r for r in rules if r.framework in frameworks]

        findings = []
        checker = self.get_checker(category)

        if checker is None:
            logger.warning(f"No checker available for category {category.value}")
            return findings

        for rule in rules:
            finding = checker.check(rule, state)
            findings.append(finding)

        return findings

    def _determine_status(self, report: ComplianceReport) -> ComplianceStatus:
        """Determine overall compliance status from findings."""

        # Critical findings = non-compliant
        if report.critical_findings:
            return ComplianceStatus.NON_COMPLIANT

        # Non-conformances = non-compliant
        if report.non_conformances:
            return ComplianceStatus.NON_COMPLIANT

        # Any failures = non-compliant
        if report.fail_count > 0:
            return ComplianceStatus.NON_COMPLIANT

        # Incomplete or review items = review required
        if report.incomplete_count > 0 or report.review_count > 0:
            return ComplianceStatus.REVIEW_REQUIRED

        # All passed = compliant
        if report.pass_count == report.total_rules:
            return ComplianceStatus.COMPLIANT

        # Default to conditionally compliant
        return ComplianceStatus.CONDITIONALLY_COMPLIANT

    def get_framework_summary(
        self,
        report: ComplianceReport,
        framework: RegulatoryFramework,
    ) -> Dict[str, Any]:
        """Get summary for a specific framework from report."""
        fw_findings = report.findings_by_framework.get(framework.value, [])

        pass_count = sum(1 for f in fw_findings if f.status == "pass")
        fail_count = sum(1 for f in fw_findings if f.status == "fail")
        total = len(fw_findings)

        return {
            "framework": framework.value,
            "total_rules": total,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": (pass_count / total * 100) if total > 0 else 0.0,
            "status": "compliant" if fail_count == 0 else "non_compliant",
        }
