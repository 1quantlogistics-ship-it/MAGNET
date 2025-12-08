"""
MAGNET Compliance Enumerations (v1.1)

Compliance framework enumerations.
"""

from enum import Enum


class RegulatoryFramework(Enum):
    """Regulatory framework types."""
    ABS_HSNC = "abs_high_speed_naval_craft"
    ABS_HSC = "abs_high_speed_craft"
    ABS_STEEL_VESSEL = "abs_steel_vessel"
    DNV_HSLC = "dnv_high_speed_light_craft"
    DNV_RU_SHIP = "dnv_rules_ships"
    LR_SSC = "lr_special_service_craft"
    USCG_SUBCHAPTER_T = "uscg_subchapter_t"
    USCG_SUBCHAPTER_K = "uscg_subchapter_k"
    HSC_CODE_2000 = "hsc_code_2000"
    SOLAS = "solas"
    MARPOL = "marpol"
    ISO_12215 = "iso_12215"


class RuleCategory(Enum):
    """Rule category types."""
    STRUCTURAL = "structural"
    STABILITY = "stability"
    FREEBOARD = "freeboard"
    FIRE_SAFETY = "fire_safety"
    LIFESAVING = "lifesaving"
    MACHINERY = "machinery"
    ELECTRICAL = "electrical"
    NAVIGATION = "navigation"
    POLLUTION = "pollution"
    TONNAGE = "tonnage"


class FindingSeverity(Enum):
    """Severity of compliance findings."""
    PASS = "pass"
    ADVISORY = "advisory"
    WARNING = "warning"
    NON_CONFORMANCE = "non_conformance"
    CRITICAL = "critical"


class ComplianceStatus(Enum):
    """Overall compliance status."""
    COMPLIANT = "compliant"
    CONDITIONALLY_COMPLIANT = "conditionally_compliant"
    REVIEW_REQUIRED = "review_required"
    NON_COMPLIANT = "non_compliant"
