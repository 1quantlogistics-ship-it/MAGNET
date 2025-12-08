"""
reporting/generators/compliance.py - Compliance report generator.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Compliance report.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseReportGenerator
from ..schema import Report, ReportSection, ReportTable
from ..enums import ReportType, SectionType

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


class ComplianceReportGenerator(BaseReportGenerator):
    """Generates compliance report."""

    report_type = ReportType.COMPLIANCE

    def generate(self, state: "StateManager") -> Report:
        """Generate compliance report."""
        self._section_counter = 0
        self._table_counter = 0

        report = Report(
            metadata=self._create_metadata(state, "Compliance Report")
        )

        # Executive summary
        report.executive_summary = self._generate_executive_summary(state)

        # Sections
        report.add_section(self._compliance_summary(state))
        report.add_section(self._stability_compliance(state))
        report.add_section(self._structural_compliance(state))
        report.add_section(self._regulatory_findings(state))

        return report

    def _generate_executive_summary(self, state: "StateManager") -> str:
        """Generate executive summary."""
        status = state.get("compliance.status", "unknown")
        pass_count = state.get("compliance.pass_count", 0)
        fail_count = state.get("compliance.fail_count", 0)
        total = pass_count + fail_count
        pass_rate = state.get("compliance.pass_rate", 0)

        if status == "compliant":
            summary = f"The design is COMPLIANT with all applicable rules."
        elif status == "conditionally_compliant":
            summary = f"The design is CONDITIONALLY COMPLIANT pending review items."
        else:
            summary = f"The design is NON-COMPLIANT and requires modifications."

        summary += f" {pass_count} of {total} rules passed ({pass_rate:.1f}%)."

        return summary

    def _compliance_summary(self, state: "StateManager") -> ReportSection:
        """Generate compliance summary section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.COMPLIANCE,
            title="Compliance Summary",
        )

        # Overall status
        status = state.get("compliance.status", "unknown")
        section.add_paragraph(f"Overall Compliance Status: **{status.upper().replace('_', ' ')}**")

        # Frameworks checked
        frameworks = state.get("compliance.frameworks_checked", [])
        if frameworks:
            section.add_paragraph(
                f"The design was evaluated against: {', '.join(frameworks)}"
            )

        # Summary table
        summary_table = ReportTable(
            table_id=self._next_table_id(),
            title="Compliance Summary",
            headers=["Metric", "Value"],
        )

        summary_table.add_row("Total Rules Evaluated", state.get("compliance.pass_count", 0) + state.get("compliance.fail_count", 0))
        summary_table.add_row("Rules Passed", state.get("compliance.pass_count", 0))
        summary_table.add_row("Rules Failed", state.get("compliance.fail_count", 0))
        summary_table.add_row("Rules Incomplete", state.get("compliance.incomplete_count", 0))
        summary_table.add_row("Pass Rate", f"{state.get('compliance.pass_rate', 0):.1f}%")

        section.add_table(summary_table)

        return section

    def _stability_compliance(self, state: "StateManager") -> ReportSection:
        """Generate stability compliance section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.STABILITY,
            title="Stability Compliance",
        )

        stab_status = state.get("compliance.stability_status", "unknown")
        section.add_paragraph(f"Stability Compliance Status: {stab_status.upper()}")

        # Get findings related to stability
        findings = state.get("compliance.findings", {})
        if isinstance(findings, dict):
            items = findings.get("items", [])
        else:
            items = []

        stability_findings = [f for f in items if "stability" in str(f).lower() or "gm" in str(f).lower() or "gz" in str(f).lower()]

        if stability_findings:
            findings_table = ReportTable(
                table_id=self._next_table_id(),
                title="Stability Findings",
                headers=["Rule ID", "Status", "Message"],
            )

            for finding in stability_findings[:10]:  # Limit to 10
                if isinstance(finding, dict):
                    findings_table.add_row(
                        finding.get("rule_id", "N/A"),
                        finding.get("status", "N/A"),
                        finding.get("message", "N/A")[:80],
                    )

            section.add_table(findings_table)

        return section

    def _structural_compliance(self, state: "StateManager") -> ReportSection:
        """Generate structural compliance section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.CUSTOM,
            title="Structural Compliance",
        )

        section.add_paragraph(
            "Structural compliance is evaluated per classification society rules."
        )

        return section

    def _regulatory_findings(self, state: "StateManager") -> ReportSection:
        """Generate detailed findings section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.APPENDIX,
            title="Detailed Findings",
        )

        # Get all findings
        findings = state.get("compliance.findings", {})
        if isinstance(findings, dict):
            items = findings.get("items", [])
        else:
            items = []

        if not items:
            section.add_paragraph("No detailed findings available.")
            return section

        # Create table of all findings
        all_findings_table = ReportTable(
            table_id=self._next_table_id(),
            title="All Compliance Findings",
            headers=["Rule ID", "Category", "Status", "Severity", "Message"],
        )

        for finding in items:
            if isinstance(finding, dict):
                all_findings_table.add_row(
                    finding.get("rule_id", "N/A"),
                    finding.get("category", "N/A"),
                    finding.get("status", "N/A"),
                    finding.get("severity", "N/A"),
                    finding.get("message", "N/A")[:60],
                )

        section.add_table(all_findings_table)

        return section
