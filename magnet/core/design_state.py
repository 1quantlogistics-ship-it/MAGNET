"""
MAGNET DesignState v1.19

The unified design state container holding all 27 sections.
Implements the DesignStateContract interface.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
import uuid
import copy

from magnet.core.constants import DESIGN_STATE_VERSION
from magnet.core.dataclasses import (
    MissionConfig,
    HullState,
    StructuralDesign,
    StructuralLoads,
    PropulsionState,
    WeightEstimate,
    StabilityState,
    LoadingState,
    ArrangementState,
    ComplianceState,
    ProductionState,
    CostState,
    OptimizationState,
    ReportsState,
    KernelState,
    AnalysisState,
    PerformanceState,
    SystemsState,
    OutfittingState,
    EnvironmentalState,
    DeckEquipmentState,
    VisionState,
    ResistanceState,
    SeakeepingState,
    ManeuveringState,
    ElectricalState,
    SafetyState,
)


@dataclass
class PhaseMetadata:
    """Metadata for a design phase."""
    phase: str
    state: str = "draft"
    entered_at: Optional[str] = None
    entered_by: Optional[str] = None
    gate_conditions_passed: List[str] = field(default_factory=list)
    gate_conditions_failed: List[str] = field(default_factory=list)
    invalidated_by_phase: Optional[str] = None
    approval_comment: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseMetadata":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class DesignState:
    """
    Unified Design State Container v1.19

    Contains all 27 design sections plus phase tracking,
    agent state, and metadata.
    """

    # ==================== Identity ====================
    design_id: Optional[str] = None
    design_name: Optional[str] = None
    version: str = DESIGN_STATE_VERSION  # Schema version (e.g., "1.19.0")
    design_version: int = 0  # Per-mutation counter (monotonic, increments on commit)

    # ==================== 27 State Sections ====================

    # 1. Mission
    mission: MissionConfig = field(default_factory=MissionConfig)

    # 2. Hull
    hull: HullState = field(default_factory=HullState)

    # 3-4. Structure
    structural_design: StructuralDesign = field(default_factory=StructuralDesign)
    structural_loads: StructuralLoads = field(default_factory=StructuralLoads)

    # 5. Propulsion
    propulsion: PropulsionState = field(default_factory=PropulsionState)

    # 6. Weight
    weight: WeightEstimate = field(default_factory=WeightEstimate)

    # 7-8. Stability
    stability: StabilityState = field(default_factory=StabilityState)
    loading: LoadingState = field(default_factory=LoadingState)

    # 9. Arrangement
    arrangement: ArrangementState = field(default_factory=ArrangementState)

    # 10. Compliance
    compliance: ComplianceState = field(default_factory=ComplianceState)

    # 11-12. Production
    production: ProductionState = field(default_factory=ProductionState)
    cost: CostState = field(default_factory=CostState)

    # 13. Optimization
    optimization: OptimizationState = field(default_factory=OptimizationState)

    # 14. Reports
    reports: ReportsState = field(default_factory=ReportsState)

    # 15. Kernel
    kernel: KernelState = field(default_factory=KernelState)

    # 16-17. Analysis/Performance
    analysis: AnalysisState = field(default_factory=AnalysisState)
    performance: PerformanceState = field(default_factory=PerformanceState)

    # 18-19. Systems/Outfitting
    systems: SystemsState = field(default_factory=SystemsState)
    outfitting: OutfittingState = field(default_factory=OutfittingState)

    # 20. Environmental
    environmental: EnvironmentalState = field(default_factory=EnvironmentalState)

    # 21. Deck Equipment
    deck_equipment: DeckEquipmentState = field(default_factory=DeckEquipmentState)

    # 22. Vision
    vision: VisionState = field(default_factory=VisionState)

    # 23. Resistance
    resistance: ResistanceState = field(default_factory=ResistanceState)

    # 24. Seakeeping
    seakeeping: SeakeepingState = field(default_factory=SeakeepingState)

    # 25. Maneuvering
    maneuvering: ManeuveringState = field(default_factory=ManeuveringState)

    # 26. Electrical
    electrical: ElectricalState = field(default_factory=ElectricalState)

    # 27. Safety
    safety: SafetyState = field(default_factory=SafetyState)

    # ==================== Phase Integration ====================
    phase_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    phase_metadata: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ==================== Agent Layer ====================
    agents: Dict[str, Any] = field(default_factory=dict)
    orchestration: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)

    # ==================== Metadata ====================
    metadata: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None

    # ==================== Parameter Locks ====================
    locked_parameters: Set[str] = field(default_factory=set)  # Paths that cannot be modified

    def __post_init__(self):
        """Initialize design_id and timestamps if not set."""
        if self.design_id is None:
            self.design_id = str(uuid.uuid4())
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    # ==================== Section Names ====================

    SECTION_NAMES = [
        "mission",
        "hull",
        "structural_design",
        "structural_loads",
        "propulsion",
        "weight",
        "stability",
        "loading",
        "arrangement",
        "compliance",
        "production",
        "cost",
        "optimization",
        "reports",
        "kernel",
        "analysis",
        "performance",
        "systems",
        "outfitting",
        "environmental",
        "deck_equipment",
        "vision",
        "resistance",
        "seakeeping",
        "maneuvering",
        "electrical",
        "safety",
    ]

    # ==================== Serialization ====================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire design state to a dictionary."""
        result = {
            # Identity
            "design_id": self.design_id,
            "design_name": self.design_name,
            "version": self.version,
            "design_version": self.design_version,
            # Timestamps
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            # Phase integration
            "phase_states": self.phase_states,
            "phase_metadata": self.phase_metadata,
            # Agent layer
            "agents": self.agents,
            "orchestration": self.orchestration,
            "decisions": self.decisions,
            # Metadata
            "metadata": self.metadata,
            "history": self.history,
            # Parameter locks
            "locked_parameters": list(self.locked_parameters),
        }

        # Serialize all 27 sections
        for section_name in self.SECTION_NAMES:
            section = getattr(self, section_name)
            if hasattr(section, "to_dict"):
                result[section_name] = section.to_dict()
            else:
                result[section_name] = section

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DesignState":
        """Deserialize a dictionary into a DesignState instance."""
        # Section class mapping
        section_classes = {
            "mission": MissionConfig,
            "hull": HullState,
            "structural_design": StructuralDesign,
            "structural_loads": StructuralLoads,
            "propulsion": PropulsionState,
            "weight": WeightEstimate,
            "stability": StabilityState,
            "loading": LoadingState,
            "arrangement": ArrangementState,
            "compliance": ComplianceState,
            "production": ProductionState,
            "cost": CostState,
            "optimization": OptimizationState,
            "reports": ReportsState,
            "kernel": KernelState,
            "analysis": AnalysisState,
            "performance": PerformanceState,
            "systems": SystemsState,
            "outfitting": OutfittingState,
            "environmental": EnvironmentalState,
            "deck_equipment": DeckEquipmentState,
            "vision": VisionState,
            "resistance": ResistanceState,
            "seakeeping": SeakeepingState,
            "maneuvering": ManeuveringState,
            "electrical": ElectricalState,
            "safety": SafetyState,
        }

        kwargs = {}

        # Extract identity fields
        for key in ["design_id", "design_name", "version", "design_version", "created_at", "updated_at", "created_by"]:
            if key in data:
                kwargs[key] = data[key]

        # Extract phase/agent fields
        for key in ["phase_states", "phase_metadata", "agents", "orchestration", "decisions", "metadata", "history"]:
            if key in data:
                kwargs[key] = data[key]

        # Extract locked_parameters (convert list back to set)
        if "locked_parameters" in data:
            kwargs["locked_parameters"] = set(data["locked_parameters"])

        # Deserialize sections
        for section_name, section_class in section_classes.items():
            if section_name in data and data[section_name] is not None:
                kwargs[section_name] = section_class.from_dict(data[section_name])

        return cls(**kwargs)

    # ==================== Validation ====================

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the design state for internal consistency.

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []

        # Check required identity fields
        if not self.design_id:
            errors.append("design_id is required")

        # Validate hull dimensions consistency
        if self.hull.loa and self.hull.lwl:
            if self.hull.lwl > self.hull.loa:
                errors.append("lwl cannot exceed loa")

        if self.hull.beam and self.hull.beam_wl:
            if self.hull.beam_wl > self.hull.beam:
                errors.append("beam_wl cannot exceed beam")

        if self.hull.draft and self.hull.depth:
            if self.hull.draft > self.hull.depth:
                errors.append("draft cannot exceed depth")

        # Validate hull coefficients
        for coeff_name in ["cb", "cp", "cm", "cwp"]:
            coeff = getattr(self.hull, coeff_name, None)
            if coeff is not None and (coeff < 0 or coeff > 1):
                errors.append(f"hull.{coeff_name} must be between 0 and 1")

        # Validate weight consistency
        if self.weight.lightship_weight_mt and self.weight.full_load_displacement_mt:
            if self.weight.lightship_weight_mt > self.weight.full_load_displacement_mt:
                errors.append("lightship_weight cannot exceed full_load_displacement")

        # Validate stability
        if self.stability.gm_transverse_m is not None and self.stability.gm_transverse_m < 0:
            errors.append("stability.gm_transverse_m cannot be negative (would indicate instability)")

        # Validate mission requirements
        if self.mission.max_speed_kts and self.mission.cruise_speed_kts:
            if self.mission.cruise_speed_kts > self.mission.max_speed_kts:
                errors.append("cruise_speed cannot exceed max_speed")

        # Validate propulsion
        if self.propulsion.num_engines < 0:
            errors.append("num_engines cannot be negative")

        if self.propulsion.num_propellers < 0:
            errors.append("num_propellers cannot be negative")

        return (len(errors) == 0, errors)

    # ==================== Patch ====================

    def patch(self, updates: Dict[str, Any], source: str) -> List[str]:
        """
        Apply a partial update to the design state.

        Args:
            updates: Dictionary of path -> value updates.
            source: Identifier of the update source.

        Returns:
            List of paths that were modified.
        """
        modified_paths = []

        for path, value in updates.items():
            parts = path.split(".")
            if len(parts) == 1:
                # Top-level attribute
                if hasattr(self, parts[0]):
                    setattr(self, parts[0], value)
                    modified_paths.append(path)
            elif len(parts) == 2:
                # Section.attribute
                section_name, attr_name = parts
                section = getattr(self, section_name, None)
                if section is not None and hasattr(section, attr_name):
                    setattr(section, attr_name, value)
                    modified_paths.append(path)
            elif len(parts) >= 3:
                # Deeper nesting - handle nested dicts
                section_name = parts[0]
                section = getattr(self, section_name, None)
                if section is not None:
                    obj = section
                    for part in parts[1:-1]:
                        if hasattr(obj, part):
                            obj = getattr(obj, part)
                        elif isinstance(obj, dict):
                            obj = obj.get(part, {})
                        else:
                            obj = None
                            break
                    if obj is not None:
                        final_attr = parts[-1]
                        if hasattr(obj, final_attr):
                            setattr(obj, final_attr, value)
                            modified_paths.append(path)
                        elif isinstance(obj, dict):
                            obj[final_attr] = value
                            modified_paths.append(path)

        # Record in history
        if modified_paths:
            self.history.append({
                "timestamp": datetime.utcnow().isoformat(),
                "source": source,
                "action": "patch",
                "paths_modified": modified_paths,
            })
            self.updated_at = datetime.utcnow().isoformat()

        return modified_paths

    # ==================== Diff ====================

    def diff(self, other: "DesignState") -> Dict[str, Tuple[Any, Any]]:
        """
        Compare this state with another and return differences.

        Args:
            other: Another DesignState to compare against.

        Returns:
            Dictionary mapping changed paths to (old_value, new_value) tuples.
        """
        differences = {}

        self_dict = self.to_dict()
        other_dict = other.to_dict()

        def compare_dicts(d1: Dict, d2: Dict, prefix: str = ""):
            """Recursively compare two dictionaries."""
            all_keys = set(d1.keys()) | set(d2.keys())
            for key in all_keys:
                path = f"{prefix}.{key}" if prefix else key
                v1 = d1.get(key)
                v2 = d2.get(key)

                if isinstance(v1, dict) and isinstance(v2, dict):
                    compare_dicts(v1, v2, path)
                elif v1 != v2:
                    differences[path] = (v1, v2)

        compare_dicts(self_dict, other_dict)
        return differences

    # ==================== Section Access ====================

    def get_section(self, section_name: str) -> Any:
        """Get a specific section by name."""
        if section_name in self.SECTION_NAMES:
            return getattr(self, section_name)
        raise ValueError(f"Unknown section: {section_name}")

    def set_section(self, section_name: str, value: Any) -> None:
        """Set a specific section by name."""
        if section_name in self.SECTION_NAMES:
            setattr(self, section_name, value)
            self.updated_at = datetime.utcnow().isoformat()
        else:
            raise ValueError(f"Unknown section: {section_name}")

    # ==================== Copy ====================

    def copy(self) -> "DesignState":
        """Create a deep copy of this design state."""
        return DesignState.from_dict(copy.deepcopy(self.to_dict()))

    # ==================== String Representation ====================

    def __repr__(self) -> str:
        return f"DesignState(id={self.design_id}, name={self.design_name}, version={self.version})"

    def summary(self) -> str:
        """Return a summary string of the design state."""
        lines = [
            f"Design: {self.design_name or 'Unnamed'} ({self.design_id})",
            f"Version: {self.version}",
            f"Created: {self.created_at}",
            "",
            "Mission:",
            f"  Type: {self.mission.vessel_type or 'Not set'}",
            f"  Max Speed: {self.mission.max_speed_kts or 'Not set'} kts",
            f"  Range: {self.mission.range_nm or 'Not set'} nm",
            "",
            "Hull:",
            f"  LOA: {self.hull.loa or 'Not set'} m",
            f"  Beam: {self.hull.beam or 'Not set'} m",
            f"  Draft: {self.hull.draft or 'Not set'} m",
            "",
            "Propulsion:",
            f"  Power: {self.propulsion.total_installed_power_kw or 'Not set'} kW",
            f"  Engines: {self.propulsion.num_engines}",
            "",
            "Weight:",
            f"  Lightship: {self.weight.lightship_weight_mt or 'Not set'} MT",
            f"  Full Load: {self.weight.full_load_displacement_mt or 'Not set'} MT",
        ]
        return "\n".join(lines)
