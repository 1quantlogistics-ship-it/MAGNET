"""
MAGNET Compliance Rule Library (v1.1)

Regulatory rule definitions library.

v1.1 FIX: Corrected field names to match StabilityState in Module 01 v1.8:
  - stability.angle_of_max_gz_deg (CORRECT - matches Module 01)
  - stability.area_0_30_m_rad (CORRECT)
  - stability.area_0_40_m_rad (CORRECT)
  - stability.area_30_40_m_rad (CORRECT)
  - stability.gz_max_m (CORRECT)
  - stability.gm_m (CORRECT)
"""

from typing import Dict, List, Optional

from .rule_schema import RuleRequirement, RuleReference
from .enums import RuleCategory, RegulatoryFramework


class RuleLibrary:
    """Repository of regulatory rules."""

    def __init__(self):
        self._rules: Dict[str, RuleRequirement] = {}
        self._by_framework: Dict[RegulatoryFramework, List[str]] = {}
        self._by_category: Dict[RuleCategory, List[str]] = {}

        self._load_abs_hsnc_rules()
        self._load_hsc_code_rules()
        self._load_uscg_rules()

    def register(self, rule: RuleRequirement) -> None:
        """Register a rule in the library."""
        self._rules[rule.rule_id] = rule

        if rule.framework not in self._by_framework:
            self._by_framework[rule.framework] = []
        self._by_framework[rule.framework].append(rule.rule_id)

        if rule.category not in self._by_category:
            self._by_category[rule.category] = []
        self._by_category[rule.category].append(rule.rule_id)

    def get(self, rule_id: str) -> Optional[RuleRequirement]:
        """Get rule by ID."""
        return self._rules.get(rule_id)

    def get_by_framework(self, framework: RegulatoryFramework) -> List[RuleRequirement]:
        """Get all rules for a framework."""
        rule_ids = self._by_framework.get(framework, [])
        return [self._rules[rid] for rid in rule_ids]

    def get_by_category(self, category: RuleCategory) -> List[RuleRequirement]:
        """Get all rules for a category."""
        rule_ids = self._by_category.get(category, [])
        return [self._rules[rid] for rid in rule_ids]

    def get_applicable_rules(
        self,
        framework: RegulatoryFramework,
        vessel_type: str,
        length_m: float,
    ) -> List[RuleRequirement]:
        """Get rules applicable to a specific vessel."""
        applicable = []
        for rule in self.get_by_framework(framework):
            # Check vessel type restriction
            if rule.vessel_types and vessel_type not in rule.vessel_types:
                continue
            # Check length restrictions
            if rule.min_length_m and length_m < rule.min_length_m:
                continue
            if rule.max_length_m and length_m > rule.max_length_m:
                continue
            applicable.append(rule)
        return applicable

    def get_all_rules(self) -> List[RuleRequirement]:
        """Get all registered rules."""
        return list(self._rules.values())

    def _load_abs_hsnc_rules(self) -> None:
        """Load ABS High-Speed Naval Craft rules."""

        # GM Minimum
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-3-2-1",
            name="Intact Stability - Minimum GM",
            description="Minimum metacentric height for intact stability",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "3/2.1", "3.1.1", edition_year=2024)],
            required_inputs=["stability.gm_m", "hull.beam"],
            acceptance_criteria="GM ≥ 0.15m or 0.04B, whichever is greater",
            formula="max(0.15, 0.04 * beam)",
            limit_type="minimum",
            mandatory=True,
        ))

        # GZ Area 0-30°
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-3-2-2",
            name="Intact Stability - GZ Curve Area 0-30°",
            description="Area under GZ curve from 0 to 30 degrees",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "3/2.1", "3.1.2", edition_year=2024)],
            required_inputs=["stability.area_0_30_m_rad"],  # CORRECT FIELD NAME
            acceptance_criteria="Area ≥ 0.055 m-rad",
            limit_value=0.055,
            limit_type="minimum",
            mandatory=True,
        ))

        # GZ Area 0-40°
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-3-2-3",
            name="Intact Stability - GZ Curve Area 0-40°",
            description="Area under GZ curve from 0 to 40 degrees",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "3/2.1", "3.1.3", edition_year=2024)],
            required_inputs=["stability.area_0_40_m_rad"],  # CORRECT FIELD NAME
            acceptance_criteria="Area ≥ 0.090 m-rad",
            limit_value=0.090,
            limit_type="minimum",
            mandatory=True,
        ))

        # GZ Area 30-40°
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-3-2-4",
            name="Intact Stability - GZ Curve Area 30-40°",
            description="Area under GZ curve from 30 to 40 degrees",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "3/2.1", "3.1.4", edition_year=2024)],
            required_inputs=["stability.area_30_40_m_rad"],  # CORRECT FIELD NAME
            acceptance_criteria="Area ≥ 0.030 m-rad",
            limit_value=0.030,
            limit_type="minimum",
            mandatory=True,
        ))

        # Maximum GZ
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-3-2-5",
            name="Intact Stability - Maximum GZ",
            description="Maximum righting lever",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "3/2.1", "3.1.5", edition_year=2024)],
            required_inputs=["stability.gz_max_m"],  # CORRECT FIELD NAME
            acceptance_criteria="GZ_max ≥ 0.20m",
            limit_value=0.20,
            limit_type="minimum",
            mandatory=True,
        ))

        # Angle of Maximum GZ
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-3-2-6",
            name="Intact Stability - Angle of Maximum GZ",
            description="Angle at which maximum GZ occurs",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "3/2.1", "3.1.6", edition_year=2024)],
            required_inputs=["stability.angle_of_max_gz_deg"],  # CORRECT FIELD NAME (v1.1 verified)
            acceptance_criteria="θ_GZmax ≥ 25°",
            limit_value=25.0,
            limit_type="minimum",
            mandatory=True,
        ))

        # Bottom Plating
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-4-1-1",
            name="Bottom Plating - Minimum Thickness",
            description="Minimum bottom shell plating thickness",
            category=RuleCategory.STRUCTURAL,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "4/1.1", "1.1.1", edition_year=2024)],
            required_inputs=["structure.bottom_plate_thickness_mm", "hull.lwl"],
            acceptance_criteria="t ≥ calculated minimum per 4/1.1",
            mandatory=True,
        ))

        # Side Plating
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-4-1-2",
            name="Side Shell Plating - Minimum Thickness",
            description="Minimum side shell plating thickness",
            category=RuleCategory.STRUCTURAL,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "4/1.1", "1.1.2", edition_year=2024)],
            required_inputs=["structure.side_plate_thickness_mm", "hull.lwl"],
            acceptance_criteria="t ≥ calculated minimum per 4/1.1",
            mandatory=True,
        ))

        # Freeboard
        self.register(RuleRequirement(
            rule_id="ABS-HSNC-3-1-1",
            name="Minimum Freeboard",
            description="Minimum freeboard at all points",
            category=RuleCategory.FREEBOARD,
            framework=RegulatoryFramework.ABS_HSNC,
            references=[RuleReference("ABS HSNC", "3/1.1", "1.1.1", edition_year=2024)],
            required_inputs=["hull.freeboard", "hull.lwl"],
            acceptance_criteria="Freeboard ≥ calculated minimum",
            mandatory=True,
        ))

    def _load_hsc_code_rules(self) -> None:
        """Load IMO HSC Code 2000 rules."""

        self.register(RuleRequirement(
            rule_id="HSC-2000-2-7-1",
            name="HSC Stability - Intact GM",
            description="Metacentric height for high-speed craft",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.HSC_CODE_2000,
            references=[RuleReference("HSC Code 2000", "2.7", "2.7.1", edition_year=2000)],
            required_inputs=["stability.gm_m"],  # CORRECT FIELD NAME
            acceptance_criteria="GM ≥ 0.05m for passenger craft",
            limit_value=0.05,
            limit_type="minimum",
            mandatory=True,
        ))

        self.register(RuleRequirement(
            rule_id="HSC-2000-2-8-1",
            name="HSC Damage Stability",
            description="One-compartment damage stability",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.HSC_CODE_2000,
            references=[RuleReference("HSC Code 2000", "2.8", "2.8.1", edition_year=2000)],
            required_inputs=["stability.damage_all_pass"],  # CORRECT FIELD NAME
            acceptance_criteria="Vessel must survive one-compartment flooding",
            mandatory=True,
        ))

        # Range of stability
        self.register(RuleRequirement(
            rule_id="HSC-2000-2-7-2",
            name="HSC Range of Stability",
            description="Range of positive stability",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.HSC_CODE_2000,
            references=[RuleReference("HSC Code 2000", "2.7", "2.7.2", edition_year=2000)],
            required_inputs=["stability.range_deg"],
            acceptance_criteria="Range ≥ 20° for passenger craft",
            limit_value=20.0,
            limit_type="minimum",
            mandatory=True,
        ))

    def _load_uscg_rules(self) -> None:
        """Load USCG CFR rules."""

        self.register(RuleRequirement(
            rule_id="USCG-46CFR-170-170",
            name="USCG Stability - Passenger Vessels",
            description="Stability requirements for passenger vessels",
            category=RuleCategory.STABILITY,
            framework=RegulatoryFramework.USCG_SUBCHAPTER_T,
            references=[RuleReference("46 CFR", "170.170", edition_year=2024)],
            required_inputs=["stability.gm_m", "mission.passengers"],
            acceptance_criteria="Must meet passenger heel test or calculated stability",
            mandatory=True,
            vessel_types=["ferry", "passenger"],
        ))

        self.register(RuleRequirement(
            rule_id="USCG-46CFR-178-310",
            name="USCG Freeboard - Small Passenger Vessels",
            description="Minimum freeboard for Subchapter T vessels",
            category=RuleCategory.FREEBOARD,
            framework=RegulatoryFramework.USCG_SUBCHAPTER_T,
            references=[RuleReference("46 CFR", "178.310", edition_year=2024)],
            required_inputs=["hull.freeboard"],
            acceptance_criteria="Freeboard ≥ values in Table 178.310",
            mandatory=True,
            max_length_m=19.8,
        ))

        # Collision bulkhead
        self.register(RuleRequirement(
            rule_id="USCG-46CFR-179-210",
            name="USCG Collision Bulkhead",
            description="Collision bulkhead position",
            category=RuleCategory.STRUCTURAL,
            framework=RegulatoryFramework.USCG_SUBCHAPTER_T,
            references=[RuleReference("46 CFR", "179.210", edition_year=2024)],
            required_inputs=["arrangement.collision_bulkhead_m", "hull.lwl"],
            acceptance_criteria="Collision bulkhead 5-15% LWL from FP",
            mandatory=True,
        ))


# Singleton instance
RULE_LIBRARY = RuleLibrary()
