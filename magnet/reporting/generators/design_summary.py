"""
reporting/generators/design_summary.py - Design summary report generator.

ALPHA OWNS THIS FILE.

Module 14 v1.1 - Design summary report.

v1.1 PATCHES:
- P1: hull.lcb_percent_lwl (not hull.lcb_percent)
- P3: Displacement path fallback
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from .base import BaseReportGenerator
from ..schema import Report, ReportSection, ReportTable
from ..enums import ReportType, SectionType

if TYPE_CHECKING:
    from ...core.state_manager import StateManager


class DesignSummaryGenerator(BaseReportGenerator):
    """Generates design summary report."""

    report_type = ReportType.DESIGN_SUMMARY

    def generate(self, state: "StateManager") -> Report:
        """Generate design summary report."""
        self._section_counter = 0
        self._table_counter = 0

        report = Report(
            metadata=self._create_metadata(state, "Design Summary Report")
        )

        # Executive summary
        report.executive_summary = self._generate_executive_summary(state)

        # Sections
        report.add_section(self._principal_characteristics(state))
        report.add_section(self._hull_form_section(state))
        report.add_section(self._weight_estimate_section(state))
        report.add_section(self._stability_section(state))
        report.add_section(self._propulsion_section(state))

        return report

    def _generate_executive_summary(self, state: "StateManager") -> str:
        """Generate executive summary."""
        vessel_type = state.get("mission.vessel_type", "vessel")
        lwl = state.get("hull.lwl", 0)
        beam = state.get("hull.beam", 0)
        max_speed = state.get("mission.max_speed_kts", 0)

        # P3 FIX: Get displacement from multiple sources
        displacement = state.get("weight.displacement_mt")
        if displacement is None or displacement == 0:
            displacement = state.get("hull.displacement_mt", 0)

        return (
            f"This report summarizes the design characteristics of the "
            f"{vessel_type.replace('_', ' ')} with overall dimensions of "
            f"{lwl:.1f}m LOA × {beam:.1f}m beam. The vessel has a design "
            f"displacement of {displacement:.1f} MT and is designed for "
            f"a maximum speed of {max_speed:.1f} knots."
        )

    def _principal_characteristics(self, state: "StateManager") -> ReportSection:
        """Generate principal characteristics section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.PRINCIPAL_CHARACTERISTICS,
            title="Principal Characteristics",
        )

        # P3 FIX: Get displacement from multiple sources
        displacement = state.get("weight.displacement_mt")
        if displacement is None or displacement == 0:
            displacement = state.get("hull.displacement_mt", 0)

        # Main characteristics table
        chars_table = ReportTable(
            table_id=self._next_table_id(),
            title="Principal Dimensions",
            headers=["Parameter", "Value"],
        )

        chars = [
            ("Length Overall (LOA)", f"{state.get('hull.loa', 0):.2f} m"),
            ("Length Waterline (LWL)", f"{state.get('hull.lwl', 0):.2f} m"),
            ("Beam (B)", f"{state.get('hull.beam', 0):.2f} m"),
            ("Depth (D)", f"{state.get('hull.depth', 0):.2f} m"),
            ("Draft (T)", f"{state.get('hull.draft', 0):.2f} m"),
            ("Displacement", f"{displacement:.1f} MT"),
            ("Lightship Weight", f"{state.get('weight.lightship_mt', 0):.1f} MT"),
            ("Deadweight", f"{state.get('weight.deadweight_mt', 0):.1f} MT"),
            ("Max Speed", f"{state.get('mission.max_speed_kts', 0):.1f} kts"),
            ("Range", f"{state.get('mission.range_nm', 0):.0f} nm"),
            ("Crew", f"{state.get('mission.crew_size', 0)} persons"),
            ("Passengers", f"{state.get('mission.passengers', 0)} persons"),
        ]

        for param, value in chars:
            chars_table.add_row(param, value)

        section.add_table(chars_table)

        return section

    def _hull_form_section(self, state: "StateManager") -> ReportSection:
        """Generate hull form section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.HULL_FORM,
            title="Hull Form",
        )

        hull_type = state.get("hull.hull_type", "displacement")
        section.add_paragraph(
            f"The vessel features a {hull_type} hull form designed for "
            f"the specified operational profile."
        )

        # Hull form coefficients table
        coeff_table = ReportTable(
            table_id=self._next_table_id(),
            title="Hull Form Coefficients",
            headers=["Coefficient", "Value", "Description"],
        )

        # P1 FIX: Use hull.lcb_percent_lwl NOT hull.lcb_percent
        coeffs = [
            ("Cb", state.get("hull.cb", 0), "Block Coefficient"),
            ("Cp", state.get("hull.cp", 0), "Prismatic Coefficient"),
            ("Cwp", state.get("hull.cwp", 0), "Waterplane Coefficient"),
            ("LCB", state.get("hull.lcb_percent_lwl", 0), "LCB (% LWL from FP)"),  # P1 FIX
        ]

        for name, value, desc in coeffs:
            coeff_table.add_row(name, f"{value:.3f}", desc)

        section.add_table(coeff_table)

        return section

    def _weight_estimate_section(self, state: "StateManager") -> ReportSection:
        """Generate weight estimate section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.WEIGHT_ESTIMATE,
            title="Weight Estimate",
        )

        section.add_paragraph(
            "Weight estimation follows SWBS (Ship Work Breakdown Structure) methodology."
        )

        # Weight breakdown table
        weight_table = ReportTable(
            table_id=self._next_table_id(),
            title="Weight Breakdown by SWBS Group",
            headers=["Group", "Description", "Weight (MT)"],
        )

        groups = [
            ("100", "Hull Structure", state.get("weight.group_100_mt", 0)),
            ("200", "Propulsion Plant", state.get("weight.group_200_mt", 0)),
            ("300", "Electrical Plant", state.get("weight.group_300_mt", 0)),
            ("400", "Command & Surveillance", state.get("weight.group_400_mt", 0)),
            ("500", "Auxiliary Systems", state.get("weight.group_500_mt", 0)),
            ("600", "Outfit & Furnishings", state.get("weight.group_600_mt", 0)),
            ("---", "Margin", state.get("weight.margin_mt", 0)),
        ]

        for grp, desc, weight in groups:
            weight_table.add_row(grp, desc, f"{weight:.2f}")

        weight_table.add_row("", "LIGHTSHIP", f"{state.get('weight.lightship_mt', 0):.2f}")

        section.add_table(weight_table)

        return section

    def _stability_section(self, state: "StateManager") -> ReportSection:
        """Generate stability section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.STABILITY,
            title="Stability Summary",
        )

        gm = state.get("stability.gm_m", 0)
        status = "satisfactory" if gm >= 0.35 else "requires review"
        section.add_paragraph(
            f"Initial stability analysis indicates GM = {gm:.3f}m. "
            f"Stability is {status} per IMO criteria."
        )

        # Stability parameters table
        stab_table = ReportTable(
            table_id=self._next_table_id(),
            title="Stability Parameters",
            headers=["Parameter", "Value", "Criterion", "Status"],
        )

        gz_max = state.get("stability.gz_max_m", 0)
        angle_max = state.get("stability.angle_of_max_gz_deg", 0)
        area_0_30 = state.get("stability.area_0_30_m_rad", 0)
        area_0_40 = state.get("stability.area_0_40_m_rad", 0)
        area_30_40 = state.get("stability.area_30_40_m_rad", 0)

        params = [
            ("GM", f"{gm:.3f} m", "≥ 0.35 m", "PASS" if gm >= 0.35 else "FAIL"),
            ("GZ max", f"{gz_max:.3f} m", "≥ 0.20 m", "PASS" if gz_max >= 0.20 else "FAIL"),
            ("Angle of GZ max", f"{angle_max:.1f}°", "≥ 25°", "PASS" if angle_max >= 25 else "FAIL"),
            ("Area 0-30°", f"{area_0_30:.4f} m·rad", "≥ 0.055", "PASS" if area_0_30 >= 0.055 else "FAIL"),
            ("Area 0-40°", f"{area_0_40:.4f} m·rad", "≥ 0.090", "PASS" if area_0_40 >= 0.090 else "FAIL"),
            ("Area 30-40°", f"{area_30_40:.4f} m·rad", "≥ 0.030", "PASS" if area_30_40 >= 0.030 else "FAIL"),
        ]

        for param, value, criterion, status in params:
            stab_table.add_row(param, value, criterion, status)

        section.add_table(stab_table)

        return section

    def _propulsion_section(self, state: "StateManager") -> ReportSection:
        """Generate propulsion section."""
        section = ReportSection(
            section_id=self._next_section_id(),
            section_type=SectionType.PROPULSION,
            title="Propulsion",
        )

        power = state.get("propulsion.installed_power_kw", 0)
        num_engines = state.get("propulsion.number_of_engines", 2)

        section.add_paragraph(
            f"The vessel is equipped with {num_engines} main engine(s) "
            f"providing a total installed power of {power:.0f} kW."
        )

        # Propulsion table
        prop_table = ReportTable(
            table_id=self._next_table_id(),
            title="Propulsion System",
            headers=["Parameter", "Value"],
        )

        params = [
            ("Total Installed Power", f"{power:.0f} kW"),
            ("Number of Engines", f"{num_engines}"),
            ("Power per Engine", f"{power/num_engines:.0f} kW"),
            ("Propulsive Efficiency", f"{state.get('propulsion.propulsive_efficiency', 0.65):.0%}"),
            ("Design Speed", f"{state.get('mission.max_speed_kts', 0):.1f} knots"),
        ]

        for param, value in params:
            prop_table.add_row(param, value)

        section.add_table(prop_table)

        return section
