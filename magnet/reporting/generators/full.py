"""
reporting/generators/full.py - Full report generator.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Full comprehensive report.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseReportGenerator
from .design_summary import DesignSummaryGenerator
from .compliance import ComplianceReportGenerator
from .cost import CostReportGenerator
from ..schema import Report, ReportSection
from ..enums import ReportType, SectionType

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


class FullReportGenerator(BaseReportGenerator):
    """Generates comprehensive full report combining all sections."""

    report_type = ReportType.FULL

    def __init__(self):
        super().__init__()
        self._design_gen = DesignSummaryGenerator()
        self._compliance_gen = ComplianceReportGenerator()
        self._cost_gen = CostReportGenerator()

    def generate(self, state: "StateManager") -> Report:
        """Generate full comprehensive report."""
        self._section_counter = 0
        self._table_counter = 0

        report = Report(
            metadata=self._create_metadata(state, "Full Design Report")
        )

        # Generate executive summary from all subsystems
        report.executive_summary = self._generate_executive_summary(state)

        # Generate sub-reports
        design_report = self._design_gen.generate(state)
        compliance_report = self._compliance_gen.generate(state)
        cost_report = self._cost_gen.generate(state)

        # Combine sections with renumbering
        for section in design_report.sections:
            section.section_id = self._next_section_id()
            report.add_section(section)

        for section in compliance_report.sections:
            section.section_id = self._next_section_id()
            report.add_section(section)

        for section in cost_report.sections:
            section.section_id = self._next_section_id()
            report.add_section(section)

        # Add production section
        report.add_section(self._production_section(state))

        # Add optimization section if available
        if state.get("optimization.status"):
            report.add_section(self._optimization_section(state))

        return report

    def _generate_executive_summary(self, state: "StateManager") -> str:
        """Generate comprehensive executive summary."""
        vessel_type = state.get("mission.vessel_type", "vessel")
        lwl = state.get("hull.lwl", 0)
        beam = state.get("hull.beam", 0)

        # Get displacement with fallback
        displacement = state.get("weight.displacement_mt")
        if displacement is None or displacement == 0:
            displacement = state.get("hull.displacement_mt", 0)

        compliance_status = state.get("compliance.status", "unknown")
        total_price = state.get("cost.total_price", 0)

        return (
            f"This comprehensive report covers all aspects of the {vessel_type.replace('_', ' ')} design. "
            f"Principal dimensions are {lwl:.1f}m LWL × {beam:.1f}m beam with a displacement of {displacement:.1f} MT. "
            f"The design is {compliance_status.replace('_', ' ')} per applicable regulations. "
            f"Estimated acquisition cost is ${total_price:,.0f}."
        )

    def _production_section(self, state: "StateManager") -> ReportSection:
        """Generate production planning section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.PRODUCTION,
            title="Production Planning",
        )

        # Get production summary
        summary = state.get("production.summary", {})
        if isinstance(summary, dict) and summary:
            section.add_paragraph(
                f"Build duration: {summary.get('total_days', 0)} days"
            )

            from ..schema import ReportTable
            prod_table = ReportTable(
                table_id=self._next_table_id(),
                title="Production Summary",
                headers=["Metric", "Value"],
            )

            prod_table.add_row("Total Material Weight", f"{summary.get('total_weight_kg', 0):,.0f} kg")
            prod_table.add_row("Work Packages", f"{summary.get('work_package_count', 0)}")
            prod_table.add_row("Build Duration", f"{summary.get('total_days', 0)} days")

            section.add_table(prod_table)
        else:
            section.add_paragraph("Production planning data not available.")

        return section

    def _optimization_section(self, state: "StateManager") -> ReportSection:
        """Generate optimization results section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.CUSTOM,
            title="Design Optimization",
        )

        opt_status = state.get("optimization.status", "unknown")
        iterations = state.get("optimization.iterations", 0)
        evaluations = state.get("optimization.evaluations", 0)

        section.add_paragraph(
            f"Optimization completed with status: {opt_status}. "
            f"Performed {iterations} iterations with {evaluations} total evaluations."
        )

        # Pareto front info
        pareto = state.get("optimization.pareto_front", {})
        if isinstance(pareto, dict):
            solutions = pareto.get("solutions", [])
            if solutions:
                section.add_paragraph(
                    f"Generated {len(solutions)} Pareto-optimal solutions."
                )

        return section
