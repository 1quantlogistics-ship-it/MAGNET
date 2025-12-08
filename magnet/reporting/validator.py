"""
reporting/validator.py - Reporting validator.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Report generation validator.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..validators.interface import ValidatorInterface, ValidationResult

from .generators import (
    DesignSummaryGenerator,
    ComplianceReportGenerator,
    CostReportGenerator,
    FullReportGenerator,
)
from .exporters import ReportExporter
from .enums import ReportType, ExportFormat

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


class ReportingValidator(ValidatorInterface):
    """
    Generates reports based on design state.

    Reads:
        hull.*, propulsion.*, mission.*
        weight.*, stability.*, compliance.*
        cost.*, optimization.*, production.*

    Writes:
        reporting.available_types (list of available report types)
        reporting.generated_reports (dict of report metadata)
        reporting.last_report_type
        reporting.design_summary (serialized report data)
        reporting.full_report (serialized report data when requested)
    """

    validator_id = "reporting/generator"

    def __init__(self):
        """Initialize reporting validator."""
        self._generators = {
            ReportType.DESIGN_SUMMARY: DesignSummaryGenerator(),
            ReportType.COMPLIANCE: ComplianceReportGenerator(),
            ReportType.COST: CostReportGenerator(),
            ReportType.FULL: FullReportGenerator(),
        }
        self._exporter = ReportExporter()

    def validate(
        self,
        state: "StateManager",
        context: Dict[str, Any],
    ) -> ValidationResult:
        """
        Generate design summary report by default.

        Args:
            state: State manager
            context: Validation context

        Returns:
            ValidationResult with report metadata
        """
        result = ValidationResult(validator_id=self.validator_id)

        try:
            # Determine which report types are available
            available_types = self._determine_available_types(state)

            # Write available types
            if hasattr(state, "write"):
                state.write(
                    "reporting.available_types",
                    [t.value for t in available_types],
                    self.validator_id,
                    "Available report types",
                )
            elif hasattr(state, "set"):
                state.set("reporting.available_types", [t.value for t in available_types])

            # Generate design summary by default
            if ReportType.DESIGN_SUMMARY in available_types:
                report = self._generators[ReportType.DESIGN_SUMMARY].generate(state)

                # Serialize report to state
                report_dict = report.to_dict()

                if hasattr(state, "write"):
                    state.write(
                        "reporting.design_summary",
                        report_dict,
                        self.validator_id,
                        "Design summary report",
                    )
                    state.write(
                        "reporting.last_report_type",
                        ReportType.DESIGN_SUMMARY.value,
                        self.validator_id,
                        "Last generated report type",
                    )
                    state.write(
                        "reporting.generated_reports",
                        {
                            ReportType.DESIGN_SUMMARY.value: {
                                "title": report.metadata.title,
                                "generated_at": report.metadata.generated_at,
                                "section_count": len(report.sections),
                            }
                        },
                        self.validator_id,
                        "Generated reports metadata",
                    )
                elif hasattr(state, "set"):
                    state.set("reporting.design_summary", report_dict)
                    state.set("reporting.last_report_type", ReportType.DESIGN_SUMMARY.value)
                    state.set("reporting.generated_reports", {
                        ReportType.DESIGN_SUMMARY.value: {
                            "title": report.metadata.title,
                            "generated_at": report.metadata.generated_at,
                            "section_count": len(report.sections),
                        }
                    })

                result.passed = True
                result.message = f"Generated design summary report with {len(report.sections)} sections"
                result.details = {
                    "report_type": ReportType.DESIGN_SUMMARY.value,
                    "section_count": len(report.sections),
                    "available_types": [t.value for t in available_types],
                }
            else:
                result.passed = True
                result.message = "Insufficient data for design summary report"
                result.details = {"available_types": []}

        except Exception as e:
            result.passed = False
            result.message = f"Report generation failed: {str(e)}"
            result.error = str(e)

        return result

    def _determine_available_types(
        self, state: "StateManager"
    ) -> List[ReportType]:
        """Determine which report types can be generated."""
        available = []

        # Design summary needs basic hull data
        lwl = state.get("hull.lwl", 0)
        beam = state.get("hull.beam", 0)

        if lwl > 0 and beam > 0:
            available.append(ReportType.DESIGN_SUMMARY)

        # Compliance report needs compliance data
        compliance_status = state.get("compliance.status")
        if compliance_status:
            available.append(ReportType.COMPLIANCE)

        # Cost report needs cost data
        total_price = state.get("cost.total_price", 0)
        if total_price > 0:
            available.append(ReportType.COST)

        # Full report needs at least design summary
        if ReportType.DESIGN_SUMMARY in available:
            available.append(ReportType.FULL)

        return available

    def generate_report(
        self,
        state: "StateManager",
        report_type: ReportType,
        export_format: Optional[ExportFormat] = None,
    ) -> Dict[str, Any]:
        """
        Generate a specific report type.

        Args:
            state: State manager
            report_type: Type of report to generate
            export_format: Optional export format

        Returns:
            Dict containing report data and optionally exported content
        """
        if report_type not in self._generators:
            raise ValueError(f"Unknown report type: {report_type}")

        generator = self._generators[report_type]
        report = generator.generate(state)

        result = {
            "report": report.to_dict(),
            "metadata": {
                "type": report_type.value,
                "title": report.metadata.title,
                "section_count": len(report.sections),
            },
        }

        # Export if requested
        if export_format:
            result["exported"] = self._exporter.export(report, export_format)
            result["metadata"]["export_format"] = export_format.value

        return result

    def export_report(
        self,
        state: "StateManager",
        report_type: ReportType,
        file_path: str,
        export_format: Optional[ExportFormat] = None,
    ) -> str:
        """
        Generate and export report to file.

        Args:
            state: State manager
            report_type: Type of report
            file_path: Output file path
            export_format: Format (auto-detected if None)

        Returns:
            Path to exported file
        """
        generator = self._generators[report_type]
        report = generator.generate(state)

        self._exporter.export_to_file(report, file_path, export_format)

        return file_path
