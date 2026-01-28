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
    type: Literal["float", "int", "bool", "enum"]
    kernel_unit: str
    allowed_units: tuple  # Tuple for immutability
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    keywords: tuple = field(default_factory=tuple)  # Tuple for immutability
    description: str = ""
    allowed_values: Optional[tuple] = None  # For enum types

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
    "hull.draft_fwd_m": RefinableField(
        path="hull.draft_fwd_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=0.3,
        max_value=30.0,
        keywords=("forward draft", "draft forward", "draft fwd", "draft at bow"),
        description="Draft at forward perpendicular",
    ),
    "hull.draft_aft_m": RefinableField(
        path="hull.draft_aft_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=0.3,
        max_value=30.0,
        keywords=("aft draft", "draft aft", "draft at stern"),
        description="Draft at aft perpendicular",
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
    "hull.auto_equilibrate_draft": RefinableField(
        path="hull.auto_equilibrate_draft",
        type="bool",
        kernel_unit="",
        allowed_units=("",),
        keywords=("auto equilibrate", "equilibrate draft", "auto draft", "solve draft"),
        description="If true, allow equilibrium draft solver to apply to hull.draft",
    ),
    "hull.auto_converge_hydro_weight": RefinableField(
        path="hull.auto_converge_hydro_weight",
        type="bool",
        kernel_unit="",
        allowed_units=("",),
        keywords=("converge hydro weight", "hydro-weight converge", "fixed point draft", "solve hydro weight"),
        description="If true, run hydro-weight fixed-point loop and mutate hull.draft to equilibrium draft",
    ),
    "hull.freeboard_m": RefinableField(
        path="hull.freeboard_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=0.3,
        max_value=10.0,
        keywords=("freeboard", "more freeboard", "freeboard height"),
        description="Minimum freeboard at side",
    ),

    # =========================================================================
    # HULL TYPE AND MATERIAL (Module 65.1 - Enum support)
    # =========================================================================
    "hull.hull_type": RefinableField(
        path="hull.hull_type",
        type="enum",
        kernel_unit="",
        allowed_units=("",),
        keywords=("hull type", "catamaran", "monohull", "trimaran"),
        description="Hull configuration type",
        allowed_values=(
            "monohull",
            "catamaran",
            "trimaran",
            "swath",
            "planing",
            "semi_planing",
            "displacement",
            "semi_displacement",
            "foil_assisted",
            "air_cushion",
        ),
    ),
    "hull.hull_spacing_m": RefinableField(
        path="hull.hull_spacing_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "ft"),
        min_value=1.0,
        max_value=50.0,
        keywords=("hull spacing", "demihull spacing", "catamaran spacing", "hull separation", "separation"),
        description="Centerline spacing between demihulls (catamaran/trimaran)",
    ),
    "hull.transom_beam_ratio": RefinableField(
        path="hull.transom_beam_ratio",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.0,
        max_value=1.0,
        keywords=("transom", "transom width", "wider transom", "pointed stern", "transom beam ratio"),
        description="Transom width as fraction of max beam (0=pointed, 1=full)",
    ),
    "hull.bow_flare_deg": RefinableField(
        path="hull.bow_flare_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=0.0,
        max_value=45.0,
        keywords=("bow flare", "flare", "more bow flare"),
        description="Bow flare angle above waterline",
    ),
    "hull.stem_rake_deg": RefinableField(
        path="hull.stem_rake_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=0.0,
        max_value=30.0,
        keywords=("stem rake", "raked stem", "rake"),
        description="Stem rake angle from vertical (0=vertical, positive=raked aft)",
    ),
    "hull.bow_entrance_deg": RefinableField(
        path="hull.bow_entrance_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=5.0,
        max_value=45.0,
        keywords=("bow entrance", "entry angle", "finer entry", "blunter bow", "sharper bow entry"),
        description="Waterline entry half-angle",
    ),
    "structural_design.hull_material": RefinableField(
        path="structural_design.hull_material",
        type="enum",
        kernel_unit="",
        allowed_units=("",),
        keywords=("material", "aluminum", "steel", "composite", "frp"),
        description="Hull construction material",
        allowed_values=("aluminum", "steel", "frp", "composite", "wood",
                       "cfrp", "titanium", "hybrid_composite", "grp"),
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
        keywords=("block coefficient", "cb", "fullness", "fuller", "blocky", "boxy"),
        description="Block coefficient",
    ),
    "hull.cp": RefinableField(
        path="hull.cp",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.5,
        max_value=0.95,
        keywords=("prismatic coefficient", "cp", "finer entry", "fine entry", "tapered ends", "full ends"),
        description="Prismatic coefficient",
    ),
    "hull.cm": RefinableField(
        path="hull.cm",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.7,
        max_value=1.0,
        keywords=("midship coefficient", "cm", "v shape", "v-shaped", "deeper v", "boxy midship"),
        description="Midship section coefficient",
    ),
    "hull.cwp": RefinableField(
        path="hull.cwp",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.65,
        max_value=0.95,
        keywords=("waterplane coefficient", "waterplane area coefficient", "cwp"),
        description="Waterplane area coefficient",
    ),
    "hull.lcb_fraction": RefinableField(
        path="hull.lcb_fraction",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.45,
        max_value=0.58,
        keywords=("lcb fraction", "lcb", "center of buoyancy", "buoyancy aft", "buoyancy forward"),
        description="Longitudinal center of buoyancy as fraction of LWL from FP (0=bow/FP, 1=stern/AP)",
    ),
    "hull.deadrise_deg": RefinableField(
        path="hull.deadrise_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=0.0,
        max_value=45.0,
        keywords=("deadrise", "deadrise angle", "deep v", "deeper v"),
        description="Deadrise angle at midship",
    ),
    "hull.deadrise_transom_deg": RefinableField(
        path="hull.deadrise_transom_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=0.0,
        max_value=30.0,
        keywords=("transom deadrise", "deadrise transom", "flatter transom", "transom v"),
        description="Deadrise angle at transom",
    ),

    # =========================================================================
    # PHASE 2: CHINE VARIATIONS
    # =========================================================================
    "hull.chine_type": RefinableField(
        path="hull.chine_type",
        type="enum",
        kernel_unit="",
        allowed_units=("",),
        keywords=(
            "chine", "chine type", "hard chine", "soft chine", "round bilge",
            "double chine", "triple chine", "reverse chine", "variable chine",
            "angular hull", "round hull", "chined hull",
        ),
        description="Hull chine configuration",
        allowed_values=("none", "soft", "hard", "single", "double", "triple", "reverse", "variable"),
    ),
    "hull.chine_count": RefinableField(
        path="hull.chine_count",
        type="int",
        kernel_unit="",
        allowed_units=("",),
        min_value=0,
        max_value=4,
        keywords=("chine count", "number of chines", "how many chines"),
        description="Number of chine lines per side",
    ),
    "hull.chine_flat_width_m": RefinableField(
        path="hull.chine_flat_width_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "mm", "ft"),
        min_value=0.0,
        max_value=0.5,
        keywords=("chine flat", "flat at chine", "chine width", "landing"),
        description="Width of horizontal flat at chine",
    ),

    # =========================================================================
    # PHASE 3: BOW FORMS
    # =========================================================================
    "hull.bow_style": RefinableField(
        path="hull.bow_style",
        type="enum",
        kernel_unit="",
        allowed_units=("",),
        keywords=(
            "bow style", "bow form", "bow shape", "bow type",
            "wedge bow", "axe bow", "wave piercing", "faceted bow",
            "traditional bow", "sharp bow", "angular bow", "plumb bow",
        ),
        description="Bow form style",
        allowed_values=("traditional", "wedge", "axe", "faceted", "wave_piercing", "spoon", "clipper"),
    ),
    "hull.bow_facet_count": RefinableField(
        path="hull.bow_facet_count",
        type="int",
        kernel_unit="",
        allowed_units=("",),
        min_value=2,
        max_value=8,
        keywords=("bow facets", "bow panels", "facet count"),
        description="Number of planar facets in bow (for faceted style)",
    ),
    "hull.bow_half_angle_deg": RefinableField(
        path="hull.bow_half_angle_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=8.0,
        max_value=45.0,
        keywords=("bow angle", "bow entry angle", "bow sharpness", "fine entry", "blunt bow"),
        description="Half-angle of bow entry (smaller = sharper)",
    ),
    "hull.stem_profile": RefinableField(
        path="hull.stem_profile",
        type="enum",
        kernel_unit="",
        allowed_units=("",),
        keywords=("stem", "stem profile", "bow profile", "plumb stem", "raked stem"),
        description="Stem (bow edge) profile shape",
        allowed_values=("vertical", "raked", "wave_piercing", "axe", "clipper", "bulbous"),
    ),

    # =========================================================================
    # PHASE 4: SPRAY RAILS + KNUCKLE LINES
    # =========================================================================
    "hull.spray_rail_count": RefinableField(
        path="hull.spray_rail_count",
        type="int",
        kernel_unit="",
        allowed_units=("",),
        min_value=0,
        max_value=5,
        keywords=(
            "spray rails", "spray rail", "add spray rails", "number of spray rails",
            "deflector", "spray deflector",
        ),
        description="Number of spray rails per side",
    ),
    "hull.has_spray_rails": RefinableField(
        path="hull.has_spray_rails",
        type="bool",
        kernel_unit="",
        allowed_units=("",),
        keywords=("spray rails", "add spray rails", "remove spray rails", "enable spray rails"),
        description="Enable spray rails",
    ),
    "hull.has_knuckle_lines": RefinableField(
        path="hull.has_knuckle_lines",
        type="bool",
        kernel_unit="",
        allowed_units=("",),
        keywords=("knuckle", "knuckle line", "hard edge", "longitudinal edge", "add knuckle"),
        description="Enable knuckle lines (hard longitudinal edges)",
    ),

    # =========================================================================
    # PHASE 5: TRANSOM VARIATIONS
    # =========================================================================
    "hull.transom_style": RefinableField(
        path="hull.transom_style",
        type="enum",
        kernel_unit="",
        allowed_units=("",),
        keywords=(
            "transom", "transom style", "stern", "stern style",
            "raked transom", "vertical transom", "stepped transom",
            "tunnel stern", "sugar scoop", "notched transom",
        ),
        description="Transom form style",
        allowed_values=("vertical", "raked", "reverse_raked", "stepped", "tunneled", "sugar_scoop", "notched"),
    ),
    "hull.transom_rake_deg": RefinableField(
        path="hull.transom_rake_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=-15.0,
        max_value=30.0,
        keywords=("transom rake", "transom angle", "stern rake"),
        description="Transom rake angle from vertical",
    ),

    # =========================================================================
    # PHASE 6: TUMBLEHOME, PANELS, DECK
    # =========================================================================
    "hull.tumblehome_enabled": RefinableField(
        path="hull.tumblehome_enabled",
        type="bool",
        kernel_unit="",
        allowed_units=("",),
        keywords=(
            "tumblehome", "inward lean", "topside tumblehome",
            "military style", "stealth", "reduce radar",
        ),
        description="Enable tumblehome (inward lean above waterline)",
    ),
    "hull.tumblehome_angle_deg": RefinableField(
        path="hull.tumblehome_angle_deg",
        type="float",
        kernel_unit="deg",
        allowed_units=("deg", "rad"),
        min_value=0.0,
        max_value=20.0,
        keywords=("tumblehome angle", "inward lean angle"),
        description="Tumblehome angle at deck (positive = inward lean)",
    ),
    "hull.tumblehome_start_ratio": RefinableField(
        path="hull.tumblehome_start_ratio",
        type="float",
        kernel_unit="",
        allowed_units=("",),
        min_value=0.0,
        max_value=1.0,
        keywords=("tumblehome start", "tumblehome height"),
        description="Height above waterline where tumblehome starts (ratio)",
    ),
    "hull.panel_style": RefinableField(
        path="hull.panel_style",
        type="enum",
        kernel_unit="",
        allowed_units=("",),
        keywords=(
            "panel style", "faceted", "smooth hull", "flat panels",
            "aluminum construction", "developable", "sheet metal",
        ),
        description="Hull panel surface style",
        allowed_values=("smooth", "faceted", "developable"),
    ),
    "hull.deck_enabled": RefinableField(
        path="hull.deck_enabled",
        type="bool",
        kernel_unit="",
        allowed_units=("",),
        keywords=("deck", "add deck", "close hull", "deck surface", "generate deck"),
        description="Generate deck surface",
    ),
    "hull.deck_camber_m": RefinableField(
        path="hull.deck_camber_m",
        type="float",
        kernel_unit="m",
        allowed_units=("m", "mm", "ft"),
        min_value=0.0,
        max_value=0.3,
        keywords=("deck camber", "deck crown", "deck curvature"),
        description="Deck camber (crown) height at centerline",
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
