"""
MAGNET Core Enumerations

All enumeration types used throughout the MAGNET system.
"""

from enum import Enum, auto


class PhaseState(str, Enum):
    """
    Possible states for each design phase in the phase state machine.
    """
    DRAFT = "draft"              # Initial state, work in progress
    ACTIVE = "active"            # Currently being worked on
    LOCKED = "locked"            # Completed and locked
    INVALIDATED = "invalidated"  # Upstream change invalidated this phase
    PENDING = "pending"          # Waiting for dependencies
    COMPLETED = "completed"      # Finished
    APPROVED = "approved"        # Explicitly approved by reviewer
    ERROR = "error"              # Phase encountered an error
    SKIPPED = "skipped"          # Phase intentionally skipped


class DesignPhase(str, Enum):
    """
    The 9 ordered design phases in MAGNET.

    Flow: mission -> hull_form -> structure -> arrangement ->
          propulsion -> weight -> stability -> compliance -> production
    """
    MISSION = "mission"
    HULL_FORM = "hull_form"
    STRUCTURE = "structure"
    ARRANGEMENT = "arrangement"
    PROPULSION = "propulsion"
    WEIGHT = "weight"
    STABILITY = "stability"
    COMPLIANCE = "compliance"
    PRODUCTION = "production"


class VesselType(str, Enum):
    """
    Classification of vessel types supported by MAGNET.
    """
    PATROL = "patrol"
    FERRY = "ferry"
    WORKBOAT = "workboat"
    YACHT = "yacht"
    FISHING = "fishing"
    CARGO = "cargo"
    MILITARY = "military"
    RESEARCH = "research"
    TUG = "tug"
    PASSENGER = "passenger"
    OFFSHORE = "offshore"
    PILOT = "pilot"
    SAR = "sar"  # Search and Rescue
    CREW_BOAT = "crew_boat"
    LANDING_CRAFT = "landing_craft"
    OTHER = "other"


class HullType(str, Enum):
    """
    Hull form configurations.
    """
    MONOHULL = "monohull"
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    SWATH = "swath"  # Small Waterplane Area Twin Hull
    PLANING = "planing"
    SEMI_PLANING = "semi_planing"
    DISPLACEMENT = "displacement"
    SEMI_DISPLACEMENT = "semi_displacement"
    FOIL_ASSISTED = "foil_assisted"
    AIR_CUSHION = "air_cushion"


class PropulsionType(str, Enum):
    """
    Propulsion system types.
    """
    OUTBOARD = "outboard"
    INBOARD = "inboard"
    STERNDRIVE = "sterndrive"
    WATERJET = "waterjet"
    POD = "pod"
    SAIL = "sail"
    HYBRID = "hybrid"
    ELECTRIC = "electric"
    DIESEL_ELECTRIC = "diesel_electric"
    SURFACE_DRIVE = "surface_drive"
    FIXED_PITCH = "fixed_pitch"
    CONTROLLABLE_PITCH = "controllable_pitch"
    AZIMUTH = "azimuth"
    VOITH_SCHNEIDER = "voith_schneider"


class MaterialType(str, Enum):
    """
    Hull and structural material types.
    """
    ALUMINUM = "aluminum"
    STEEL = "steel"
    FRP = "frp"  # Fiber Reinforced Plastic
    COMPOSITE = "composite"
    WOOD = "wood"
    CFRP = "cfrp"  # Carbon Fiber Reinforced Plastic
    TITANIUM = "titanium"
    HYBRID_COMPOSITE = "hybrid_composite"
    GRP = "grp"  # Glass Reinforced Plastic


class ClassificationSociety(str, Enum):
    """
    Classification societies for vessel certification.
    """
    ABS = "abs"           # American Bureau of Shipping
    DNV = "dnv"           # Det Norske Veritas
    LLOYDS = "lloyds"     # Lloyd's Register
    BV = "bv"             # Bureau Veritas
    RINA = "rina"         # Registro Italiano Navale
    USCG = "uscg"         # US Coast Guard
    MCA = "mca"           # Maritime and Coastguard Agency (UK)
    CLASS_NK = "class_nk" # Nippon Kaiji Kyokai
    CCS = "ccs"           # China Classification Society
    KR = "kr"             # Korean Register
    RMRS = "rmrs"         # Russian Maritime Register of Shipping
    NONE = "none"


class OperationalMode(str, Enum):
    """
    Vessel operational modes.
    """
    TRANSIT = "transit"
    LOITER = "loiter"
    STATION_KEEPING = "station_keeping"
    MANEUVERING = "maneuvering"
    ANCHOR = "anchor"
    DOCKING = "docking"
    EMERGENCY = "emergency"
    MAINTENANCE = "maintenance"


class SeaState(str, Enum):
    """
    Sea state classifications (Douglas scale).
    """
    CALM_GLASSY = "0"     # 0m
    CALM_RIPPLED = "1"    # 0-0.1m
    SMOOTH = "2"          # 0.1-0.5m
    SLIGHT = "3"          # 0.5-1.25m
    MODERATE = "4"        # 1.25-2.5m
    ROUGH = "5"           # 2.5-4m
    VERY_ROUGH = "6"      # 4-6m
    HIGH = "7"            # 6-9m
    VERY_HIGH = "8"       # 9-14m
    PHENOMENAL = "9"      # 14m+


class StructuralZone(str, Enum):
    """
    Structural zones for plating and framing.
    """
    BOTTOM = "bottom"
    BOTTOM_FORWARD = "bottom_forward"
    SIDE = "side"
    DECK = "deck"
    TRANSOM = "transom"
    KEEL = "keel"
    CHINE = "chine"
    SUPERSTRUCTURE = "superstructure"
    BULKHEAD = "bulkhead"
    WEB_FRAME = "web_frame"


class LoadCondition(str, Enum):
    """
    Standard loading conditions for stability analysis.
    """
    LIGHTSHIP = "lightship"
    FULL_LOAD = "full_load"
    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    BALLAST = "ballast"
    HALF_STORES = "half_stores"
    MINIMUM_OPERATING = "minimum_operating"
    MAXIMUM_DEADWEIGHT = "maximum_deadweight"


class ValidationSeverity(str, Enum):
    """
    Severity levels for validation results.
    """
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PASSED = "passed"


class ComplianceStatus(str, Enum):
    """
    Status of compliance checks.
    """
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_CHECKED = "not_checked"
    NOT_APPLICABLE = "not_applicable"


class AgentRole(str, Enum):
    """
    Agent roles in the MAGNET system.
    """
    ALPHA = "alpha"       # Architect - design leadership
    BRAVO = "bravo"       # Test engineer
    CHARLIE = "charlie"   # Documentation
    DELTA = "delta"       # Integration
    ECHO = "echo"         # Operations
    FOXTROT = "foxtrot"   # Frontend
    GOLF = "golf"         # Graphics/visualization


class TransitionTrigger(str, Enum):
    """
    Events that can trigger phase transitions.
    """
    USER_REQUEST = "user_request"
    GATE_PASSED = "gate_passed"
    UPSTREAM_CHANGED = "upstream_changed"
    VALIDATION_FAILED = "validation_failed"
    TIMEOUT = "timeout"
    AGENT_COMPLETED = "agent_completed"
    EXTERNAL_EVENT = "external_event"
