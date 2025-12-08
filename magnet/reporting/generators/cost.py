"""
reporting/generators/cost.py - Cost report generator.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Cost report.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseReportGenerator
from ..schema import Report, ReportSection, ReportTable
from ..enums import ReportType, SectionType

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


class CostReportGenerator(BaseReportGenerator):
    """Generates cost report."""

    report_type = ReportType.COST

    def generate(self, state: "StateManager") -> Report:
        """Generate cost report."""
        self._section_counter = 0
        self._table_counter = 0

        report = Report(
            metadata=self._create_metadata(state, "Cost Estimate Report")
        )

        # Executive summary
        report.executive_summary = self._generate_executive_summary(state)

        # Sections
        report.add_section(self._cost_summary(state))
        report.add_section(self._material_costs(state))
        report.add_section(self._labor_costs(state))
        report.add_section(self._lifecycle_costs(state))

        return report

    def _generate_executive_summary(self, state: "StateManager") -> str:
        """Generate executive summary."""
        total_price = state.get("cost.total_price", 0)
        confidence = state.get("cost.confidence", "rom")
        lifecycle_npv = state.get("cost.lifecycle_npv", 0)

        confidence_range = {
            "rom": "±50%",
            "budgetary": "±25%",
            "definitive": "±10%",
            "firm": "±5%",
        }
        range_str = confidence_range.get(confidence, "±50%")

        return (
            f"The total estimated acquisition cost is ${total_price:,.0f} "
            f"at {confidence.upper()} confidence level ({range_str}). "
            f"The lifecycle NPV over 25 years is ${lifecycle_npv:,.0f}."
        )

    def _cost_summary(self, state: "StateManager") -> ReportSection:
        """Generate cost summary section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.COST,
            title="Cost Summary",
        )

        # Summary table
        summary_table = ReportTable(
            table_id=self._next_table_id(),
            title="Cost Summary",
            headers=["Category", "Amount (USD)"],
        )

        subtotal_material = state.get("cost.subtotal_material", 0)
        subtotal_labor = state.get("cost.subtotal_labor", 0)
        subtotal_equipment = state.get("cost.subtotal_equipment", 0)
        acquisition = state.get("cost.acquisition_cost", 0)
        total_price = state.get("cost.total_price", 0)

        summary_table.add_row("Material", f"${subtotal_material:,.0f}")
        summary_table.add_row("Labor", f"${subtotal_labor:,.0f}")
        summary_table.add_row("Equipment", f"${subtotal_equipment:,.0f}")
        summary_table.add_row("Subtotal", f"${subtotal_material + subtotal_labor + subtotal_equipment:,.0f}")
        summary_table.add_row("Markup & Contingency", f"${acquisition - (subtotal_material + subtotal_labor + subtotal_equipment):,.0f}")
        summary_table.add_row("**Total Price**", f"**${total_price:,.0f}**")

        section.add_table(summary_table)

        # Confidence level
        confidence = state.get("cost.confidence", "rom")
        section.add_paragraph(f"Estimate Confidence: {confidence.upper()}")

        return section

    def _material_costs(self, state: "StateManager") -> ReportSection:
        """Generate material costs section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.CUSTOM,
            title="Material Costs",
        )

        material_total = state.get("cost.subtotal_material", 0)
        section.add_paragraph(
            f"Total material cost: ${material_total:,.0f}"
        )

        # Get detailed breakdown if available
        estimate = state.get("cost.estimate", {})
        if isinstance(estimate, dict):
            breakdowns = estimate.get("breakdowns", {})
            hull_breakdown = breakdowns.get("hull_structure", {})

            if hull_breakdown:
                items = hull_breakdown.get("items", [])
                if items:
                    mat_table = ReportTable(
                        table_id=self._next_table_id(),
                        title="Material Line Items",
                        headers=["Item", "Quantity", "Unit Cost", "Total"],
                    )

                    for item in items[:10]:
                        if isinstance(item, dict) and item.get("material_cost", 0) > 0:
                            mat_table.add_row(
                                item.get("name", "N/A"),
                                f"{item.get('quantity', 0):.0f} {item.get('unit', 'ea')}",
                                f"${item.get('unit_cost', 0):,.2f}",
                                f"${item.get('material_cost', 0):,.0f}",
                            )

                    section.add_table(mat_table)

        return section

    def _labor_costs(self, state: "StateManager") -> ReportSection:
        """Generate labor costs section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.CUSTOM,
            title="Labor Costs",
        )

        labor_total = state.get("cost.subtotal_labor", 0)
        section.add_paragraph(
            f"Total labor cost: ${labor_total:,.0f}"
        )

        # Get hours summary
        summary = state.get("cost.summary", {})
        if isinstance(summary, dict):
            hours = summary.get("hours", {})
            if hours:
                hours_table = ReportTable(
                    table_id=self._next_table_id(),
                    title="Labor Hours by Category",
                    headers=["Category", "Hours"],
                )

                for category, hr in hours.items():
                    hours_table.add_row(category.title(), f"{hr:,.0f}")

                total_hours = sum(hours.values())
                hours_table.add_row("**Total**", f"**{total_hours:,.0f}**")

                section.add_table(hours_table)

        return section

    def _lifecycle_costs(self, state: "StateManager") -> ReportSection:
        """Generate lifecycle costs section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.CUSTOM,
            title="Lifecycle Cost Analysis",
        )

        lifecycle_npv = state.get("cost.lifecycle_npv", 0)
        acquisition = state.get("cost.acquisition_cost", 0)

        section.add_paragraph(
            f"Lifecycle analysis covers 25 years of operations. "
            f"All future costs are discounted at 5% per annum."
        )

        lifecycle_table = ReportTable(
            table_id=self._next_table_id(),
            title="Lifecycle Cost Summary",
            headers=["Phase", "NPV (USD)"],
        )

        lifecycle_table.add_row("Acquisition", f"${acquisition:,.0f}")
        lifecycle_table.add_row("Operations (25 yr)", "See detailed analysis")
        lifecycle_table.add_row("Maintenance (25 yr)", "See detailed analysis")
        lifecycle_table.add_row("Disposal", "See detailed analysis")
        lifecycle_table.add_row("**Total Lifecycle NPV**", f"**${lifecycle_npv:,.0f}**")

        section.add_table(lifecycle_table)

        return section
