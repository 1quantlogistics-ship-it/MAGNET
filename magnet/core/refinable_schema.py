"""
MAGNET Refinable Schema v1.0

Defines which state paths can be modified via conversational input.
This is the whitelist for LLM-proposed actions.

Each RefinableField specifies:
- path: The state path (e.g., "hull.loa")
- type: The value type (float, int, bool)
- kernel_unit: The canonical unit stored in state
- allowed_units: Units the LLM may use (converted to kernel_unit)
- min_value, max_value: Bounds for clamping
- keywords: Terms that help LLM match intent to this field
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass(frozen=True)
class RefinableField:
    """
    Definition of a refinable parameter.

    Immutable to prevent runtime modification.
    """
    path: str
    type: Literal["float", "int", "bool"]
    kernel_unit: str
    allowed_units: tuple  # Tuple for immutability
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    keywords: tuple = field(default_factory=tuple)  # Tuple for immutability
    description: str = ""

    def __post_init__(self):
        """Convert lists to tuples for immutability."""
        if isinstance(self.allowed_units, list):
            object.__setattr__(self, 'allowed_units', tuple(self.allowed_units))
        if isinstance(self.keywords, list):
            object.__setattr__(self, 'keywords', tuple(self.keywords))


# =============================================================================
# REFINABLE SCHEMA
# =============================================================================

REFINABLE_SCHEMA: Dict[str, RefinableField] = {
    # =========================================================================
    # HULL DIMENSIONS
    # =========================================================================
    "hull.loa": RefinableField(
        path="hull.loa",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=5.0,
        max_value=500.0,
        keywords=("length", "loa", "overall length", "ship length"),
        description="Length overall",
    ),
    "hull.lwl": RefinableField(
        path="hull.lwl",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=4.0,
        max_value=500.0,
        keywords=("waterline length", "lwl"),
        description="Length at waterline",
    ),
    "hull.beam": RefinableField(
        path="hull.beam",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=1.0,
        max_value=100.0,
        keywords=("beam", "width", "breadth"),
        description="Maximum beam",
    ),
    "hull.draft": RefinableField(
        path="hull.draft",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=0.3,
        max_value=30.0,
        keywords=("draft", "draught"),
        description="Design draft",
    ),
    "hull.depth": RefinableField(
        path="hull.depth",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=0.5,
        max_value=50.0,
        keywords=("depth", "hull depth"),
        description="Moulded depth",
    ),

    # =========================================================================
    # HULL FORM COEFFICIENTS
    # =========================================================================
    "hull.cb": RefinableField(
        path="hull.cb",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.3,
        max_value=0.95,
        keywords=("block coefficient", "cb"),
        description="Block coefficient",
    ),
    "hull.cp": RefinableField(
        path="hull.cp",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.5,
        max_value=0.95,
        keywords=("prismatic coefficient", "cp"),
        description="Prismatic coefficient",
    ),
    "hull.cm": RefinableField(
        path="hull.cm",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.7,
        max_value=1.0,
        keywords=("midship coefficient", "cm"),
        description="Midship section coefficient",
    ),
    "hull.deadrise_deg": RefinableField(
        path="hull.deadrise_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=0.0,
        max_value=45.0,
        keywords=("deadrise", "deadrise angle"),
        description="Deadrise angle at transom",
    ),

    # =========================================================================
    # PROPULSION
    # =========================================================================
    "propulsion.total_installed_power_kw": RefinableField(
        path="propulsion.total_installed_power_kw",
        type="float",
        kernel_unit="kW",
        allowed_units=("kW", "MW", "hp"),
        min_value=10.0,
        max_value=100000.0,
        keywords=("power", "installed power", "propulsion power", "engine power", "megawatt", "mw"),
        description="Total installed propulsion power",
    ),
    "propulsion.num_engines": RefinableField(
        path="propulsion.num_engines",
        type="int",
        kernel_unit="",
        allowed_units=("",),
        min_value=1,
        max_value=8,
        keywords=("engines", "number of engines", "engine count"),
        description="Number of main engines",
    ),
    "propulsion.num_propellers": RefinableField(
        path="propulsion.num_propellers",
        type="int",
        kernel_unit="",
        allowed_units=("",),
        min_value=1,
        max_value=8,
        keywords=("propellers", "props", "screws"),
        description="Number of propellers",
    ),
    "propulsion.propeller_diameter_m": RefinableField(
        path="propulsion.propeller_diameter_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft", "mm"),
        min_value=0.3,
        max_value=15.0,
        keywords=("propeller diameter", "prop diameter"),
        description="Propeller diameter",
    ),

    # =========================================================================
    # MISSION
    # =========================================================================
    "mission.max_speed_kts": RefinableField(
        path="mission.max_speed_kts",
        type="float",
        kernel_unit="kts",
        allowed_units=("kts", "m/s", "km/h"),
        min_value=1.0,
        max_value=60.0,
        keywords=("max speed", "top speed", "maximum speed"),
        description="Maximum speed",
    ),
    "mission.cruise_speed_kts": RefinableField(
        path="mission.cruise_speed_kts",
        type="float",
        kernel_unit="kts",
        allowed_units=("kts", "m/s", "km/h"),
        min_value=1.0,
        max_value=50.0,
        keywords=("cruise speed", "cruising speed", "service speed"),
        description="Cruise speed",
    ),
    "mission.range_nm": RefinableField(
        path="mission.range_nm",
        type="float",
        kernel_unit="nm",
        allowed_units=("nm", "km"),
        min_value=10.0,
        max_value=30000.0,
        keywords=("range", "endurance range"),
        description="Range at cruise speed",
    ),
    "mission.crew_berthed": RefinableField(
        path="mission.crew_berthed",
        type="int",
        kernel_unit="",
        allowed_units=("",),
        min_value=0,
        max_value=1000,
        keywords=("crew", "crew size", "berthed crew"),
        description="Number of crew berthed",
    ),
    "mission.passengers": RefinableField(
        path="mission.passengers",
        type="int",
        kernel_unit="",
        allowed_units=("",),
        min_value=0,
        max_value=5000,
        keywords=("passengers", "pax"),
        description="Number of passengers",
    ),

    # =========================================================================
    # STABILITY
    # =========================================================================
    "mission.gm_required_m": RefinableField(
        path="mission.gm_required_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=0.15,
        max_value=5.0,
        keywords=("gm", "metacentric height", "stability"),
        description="Required metacentric height",
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_field(path: str) -> Optional[RefinableField]:
    """
    Get a RefinableField by path.

    Args:
        path: State path (e.g., "hull.loa")

    Returns:
        RefinableField or None if not refinable
    """
    return REFINABLE_SCHEMA.get(path)


def is_refinable(path: str) -> bool:
    """
    Check if a path is refinable.

    Args:
        path: State path

    Returns:
        True if the path can be modified via actions
    """
    return path in REFINABLE_SCHEMA


def get_all_refinable_paths() -> List[str]:
    """
    Get all refinable paths.

    Returns:
        List of refinable state paths
    """
    return list(REFINABLE_SCHEMA.keys())


def find_by_keyword(keyword: str) -> List[RefinableField]:
    """
    Find fields matching a keyword.

    Args:
        keyword: Search term (case-insensitive)

    Returns:
        List of matching RefinableFields
    """
    keyword_lower = keyword.lower()
    matches = []

    for field in REFINABLE_SCHEMA.values():
        if keyword_lower in field.path.lower():
            matches.append(field)
            continue

        for kw in field.keywords:
            if keyword_lower in kw.lower():
                matches.append(field)
                break

    return matches
