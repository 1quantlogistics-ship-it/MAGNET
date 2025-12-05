"""
Material properties for marine structural calculations.

Implements ABS HSNC 2023 material requirements:
- Allowed aluminum alloys for hull structure
- Prohibited alloys (6xxx series due to HAZ sensitivity)
- Heat-affected zone (HAZ) strength reduction factors
- Mechanical properties by temper condition

References:
- ABS HSNC 2023 Part 2, Chapter 4 - Materials
- AWS D1.2 Structural Welding Code - Aluminum
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum


class AluminumAlloy(Enum):
    """Aluminum alloys for marine structural use."""
    # Allowed for hull primary structure (5xxx series)
    AL_5083_H116 = "5083-H116"
    AL_5083_H321 = "5083-H321"
    AL_5086_H116 = "5086-H116"
    AL_5086_H32 = "5086-H32"
    AL_5456_H116 = "5456-H116"
    AL_5456_H321 = "5456-H321"

    # Allowed for secondary structure only
    AL_5052_H32 = "5052-H32"
    AL_5052_H34 = "5052-H34"

    # Prohibited in primary structure (6xxx series - severe HAZ degradation)
    AL_6061_T6 = "6061-T6"       # 70% strength loss in HAZ
    AL_6063_T6 = "6063-T6"       # 70% strength loss in HAZ
    AL_6082_T6 = "6082-T6"       # 50% strength loss in HAZ


@dataclass
class MaterialProperties:
    """Material mechanical properties."""
    alloy: str
    temper: str
    yield_strength: float        # MPa (0.2% proof stress)
    tensile_strength: float      # MPa
    elongation: float            # % minimum
    density: float               # kg/m³
    elastic_modulus: float       # GPa
    poisson_ratio: float
    haz_yield_strength: float    # MPa (in heat-affected zone)
    haz_tensile_strength: float  # MPa (in HAZ)
    haz_factor: float            # Strength reduction factor (HAZ/parent)
    corrosion_allowance: float   # mm (typical for marine service)

    # Classification
    primary_structure_allowed: bool
    secondary_structure_allowed: bool
    rule_reference: str

    @property
    def allowable_stress(self) -> float:
        """Allowable design stress per ABS HSNC (0.6 × yield)."""
        return 0.6 * self.yield_strength

    @property
    def allowable_stress_haz(self) -> float:
        """Allowable design stress in HAZ (0.6 × HAZ yield)."""
        return 0.6 * self.haz_yield_strength


# Material property database
MATERIAL_DATABASE: Dict[AluminumAlloy, MaterialProperties] = {
    # Primary hull structure - 5083 series
    AluminumAlloy.AL_5083_H116: MaterialProperties(
        alloy="5083",
        temper="H116",
        yield_strength=215.0,
        tensile_strength=303.0,
        elongation=10.0,
        density=2660.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=165.0,
        haz_tensile_strength=275.0,
        haz_factor=0.77,  # 23% strength loss
        corrosion_allowance=0.5,
        primary_structure_allowed=True,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.1",
    ),
    AluminumAlloy.AL_5083_H321: MaterialProperties(
        alloy="5083",
        temper="H321",
        yield_strength=228.0,
        tensile_strength=317.0,
        elongation=10.0,
        density=2660.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=165.0,
        haz_tensile_strength=275.0,
        haz_factor=0.72,  # 28% strength loss
        corrosion_allowance=0.5,
        primary_structure_allowed=True,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.1",
    ),

    # Primary hull structure - 5086 series
    AluminumAlloy.AL_5086_H116: MaterialProperties(
        alloy="5086",
        temper="H116",
        yield_strength=195.0,
        tensile_strength=275.0,
        elongation=10.0,
        density=2660.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=152.0,
        haz_tensile_strength=241.0,
        haz_factor=0.78,  # 22% strength loss
        corrosion_allowance=0.5,
        primary_structure_allowed=True,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.1",
    ),
    AluminumAlloy.AL_5086_H32: MaterialProperties(
        alloy="5086",
        temper="H32",
        yield_strength=186.0,
        tensile_strength=262.0,
        elongation=10.0,
        density=2660.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=152.0,
        haz_tensile_strength=241.0,
        haz_factor=0.82,
        corrosion_allowance=0.5,
        primary_structure_allowed=True,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.1",
    ),

    # Primary hull structure - 5456 series (higher strength)
    AluminumAlloy.AL_5456_H116: MaterialProperties(
        alloy="5456",
        temper="H116",
        yield_strength=230.0,
        tensile_strength=317.0,
        elongation=10.0,
        density=2660.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=179.0,
        haz_tensile_strength=283.0,
        haz_factor=0.78,
        corrosion_allowance=0.5,
        primary_structure_allowed=True,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.1",
    ),
    AluminumAlloy.AL_5456_H321: MaterialProperties(
        alloy="5456",
        temper="H321",
        yield_strength=255.0,
        tensile_strength=352.0,
        elongation=10.0,
        density=2660.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=179.0,
        haz_tensile_strength=283.0,
        haz_factor=0.70,
        corrosion_allowance=0.5,
        primary_structure_allowed=True,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.1",
    ),

    # Secondary structure only - 5052 series
    AluminumAlloy.AL_5052_H32: MaterialProperties(
        alloy="5052",
        temper="H32",
        yield_strength=158.0,
        tensile_strength=214.0,
        elongation=12.0,
        density=2680.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=131.0,
        haz_tensile_strength=193.0,
        haz_factor=0.83,
        corrosion_allowance=0.5,
        primary_structure_allowed=False,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.3",
    ),
    AluminumAlloy.AL_5052_H34: MaterialProperties(
        alloy="5052",
        temper="H34",
        yield_strength=179.0,
        tensile_strength=228.0,
        elongation=10.0,
        density=2680.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=131.0,
        haz_tensile_strength=193.0,
        haz_factor=0.73,
        corrosion_allowance=0.5,
        primary_structure_allowed=False,
        secondary_structure_allowed=True,
        rule_reference="ABS HSNC 2-4-1/3.3",
    ),

    # PROHIBITED - 6xxx series (severe HAZ degradation)
    AluminumAlloy.AL_6061_T6: MaterialProperties(
        alloy="6061",
        temper="T6",
        yield_strength=276.0,
        tensile_strength=310.0,
        elongation=12.0,
        density=2700.0,
        elastic_modulus=69.0,
        poisson_ratio=0.33,
        haz_yield_strength=83.0,   # Only 30% of parent!
        haz_tensile_strength=124.0,
        haz_factor=0.30,  # 70% strength loss in HAZ
        corrosion_allowance=0.5,
        primary_structure_allowed=False,
        secondary_structure_allowed=False,
        rule_reference="ABS HSNC 2-4-1/1.3 - PROHIBITED",
    ),
    AluminumAlloy.AL_6063_T6: MaterialProperties(
        alloy="6063",
        temper="T6",
        yield_strength=214.0,
        tensile_strength=241.0,
        elongation=12.0,
        density=2700.0,
        elastic_modulus=69.0,
        poisson_ratio=0.33,
        haz_yield_strength=64.0,   # Only 30% of parent!
        haz_tensile_strength=97.0,
        haz_factor=0.30,  # 70% strength loss in HAZ
        corrosion_allowance=0.5,
        primary_structure_allowed=False,
        secondary_structure_allowed=False,
        rule_reference="ABS HSNC 2-4-1/1.3 - PROHIBITED",
    ),
    AluminumAlloy.AL_6082_T6: MaterialProperties(
        alloy="6082",
        temper="T6",
        yield_strength=255.0,
        tensile_strength=290.0,
        elongation=10.0,
        density=2700.0,
        elastic_modulus=70.0,
        poisson_ratio=0.33,
        haz_yield_strength=128.0,  # 50% of parent
        haz_tensile_strength=185.0,
        haz_factor=0.50,  # 50% strength loss in HAZ
        corrosion_allowance=0.5,
        primary_structure_allowed=False,
        secondary_structure_allowed=False,
        rule_reference="ABS HSNC 2-4-1/1.3 - PROHIBITED",
    ),
}

# Quick reference lists
ALLOWED_ALLOYS: List[AluminumAlloy] = [
    AluminumAlloy.AL_5083_H116,
    AluminumAlloy.AL_5083_H321,
    AluminumAlloy.AL_5086_H116,
    AluminumAlloy.AL_5086_H32,
    AluminumAlloy.AL_5456_H116,
    AluminumAlloy.AL_5456_H321,
    AluminumAlloy.AL_5052_H32,
    AluminumAlloy.AL_5052_H34,
]

PROHIBITED_ALLOYS: List[AluminumAlloy] = [
    AluminumAlloy.AL_6061_T6,
    AluminumAlloy.AL_6063_T6,
    AluminumAlloy.AL_6082_T6,
]

# Default alloy for new designs
DEFAULT_ALLOY = AluminumAlloy.AL_5083_H116


def get_alloy_properties(alloy: AluminumAlloy) -> MaterialProperties:
    """
    Get material properties for an aluminum alloy.

    Args:
        alloy: AluminumAlloy enum value

    Returns:
        MaterialProperties dataclass
    """
    if alloy not in MATERIAL_DATABASE:
        raise ValueError(f"Unknown alloy: {alloy}")
    return MATERIAL_DATABASE[alloy]


def get_haz_factor(alloy: AluminumAlloy) -> float:
    """
    Get HAZ strength reduction factor for an alloy.

    The HAZ factor is the ratio of weld zone strength to parent metal strength.
    For 5xxx series: typically 0.70-0.85 (15-30% reduction)
    For 6xxx series: typically 0.30-0.50 (50-70% reduction) - PROHIBITED

    Args:
        alloy: AluminumAlloy enum value

    Returns:
        HAZ factor (0-1, where 1 = no strength loss)
    """
    props = get_alloy_properties(alloy)
    return props.haz_factor


def validate_material_for_location(
    alloy: AluminumAlloy,
    is_primary_structure: bool = True,
) -> tuple[bool, str]:
    """
    Validate if a material can be used at a structural location.

    Args:
        alloy: AluminumAlloy to validate
        is_primary_structure: True for hull shell, frames, girders
                             False for joiner work, non-structural

    Returns:
        Tuple of (is_valid, message)
    """
    props = get_alloy_properties(alloy)

    if alloy in PROHIBITED_ALLOYS:
        return (
            False,
            f"{alloy.value} is PROHIBITED per {props.rule_reference}. "
            f"HAZ factor = {props.haz_factor:.0%} strength loss is unacceptable."
        )

    if is_primary_structure and not props.primary_structure_allowed:
        return (
            False,
            f"{alloy.value} not allowed for primary structure per {props.rule_reference}. "
            f"Use 5083, 5086, or 5456 series instead."
        )

    return (True, f"{alloy.value} approved for this application per {props.rule_reference}")


def calculate_allowable_stress(
    alloy: AluminumAlloy,
    in_haz: bool = False,
    safety_factor: float = 1.0,
) -> float:
    """
    Calculate allowable design stress.

    ABS HSNC uses 0.6 × yield as base allowable stress.

    Args:
        alloy: AluminumAlloy
        in_haz: True if calculating for heat-affected zone
        safety_factor: Additional factor (default 1.0)

    Returns:
        Allowable stress in MPa
    """
    props = get_alloy_properties(alloy)

    if in_haz:
        base_allowable = props.allowable_stress_haz
    else:
        base_allowable = props.allowable_stress

    return base_allowable / safety_factor


def generate_material_report(alloy: AluminumAlloy) -> str:
    """Generate a human-readable material properties report."""
    props = get_alloy_properties(alloy)

    status = "APPROVED" if alloy in ALLOWED_ALLOYS else "PROHIBITED"

    lines = [
        f"MATERIAL PROPERTIES REPORT",
        f"=" * 50,
        f"",
        f"Alloy: {props.alloy}-{props.temper}",
        f"Status: {status}",
        f"Rule Reference: {props.rule_reference}",
        f"",
        f"MECHANICAL PROPERTIES (Parent Metal)",
        f"-" * 30,
        f"Yield Strength:     {props.yield_strength:8.1f} MPa",
        f"Tensile Strength:   {props.tensile_strength:8.1f} MPa",
        f"Elongation:         {props.elongation:8.1f} %",
        f"Elastic Modulus:    {props.elastic_modulus:8.1f} GPa",
        f"Density:            {props.density:8.0f} kg/m³",
        f"",
        f"HEAT-AFFECTED ZONE (HAZ)",
        f"-" * 30,
        f"HAZ Yield Strength: {props.haz_yield_strength:8.1f} MPa",
        f"HAZ Tensile:        {props.haz_tensile_strength:8.1f} MPa",
        f"HAZ Factor:         {props.haz_factor:8.2f} ({(1-props.haz_factor)*100:.0f}% strength loss)",
        f"",
        f"DESIGN VALUES",
        f"-" * 30,
        f"Allowable Stress:   {props.allowable_stress:8.1f} MPa (0.6 × σy)",
        f"Allowable (HAZ):    {props.allowable_stress_haz:8.1f} MPa",
        f"Corrosion Allow:    {props.corrosion_allowance:8.1f} mm",
        f"",
        f"STRUCTURAL USE",
        f"-" * 30,
        f"Primary Structure:  {'YES' if props.primary_structure_allowed else 'NO'}",
        f"Secondary Structure: {'YES' if props.secondary_structure_allowed else 'NO'}",
        f"",
    ]

    return "\n".join(lines)
