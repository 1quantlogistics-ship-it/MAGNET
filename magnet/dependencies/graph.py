"""
MAGNET Dependency Graph

Module 03 v1.1 - Production-Ready

Defines the directed acyclic graph of parameter dependencies.
Enables cascade invalidation when upstream parameters change.

v1.1 Fixes Applied:
- FIX #1: No circular imports (uses string phase/param references)
- FIX #2: Normalized to Section 1 field naming conventions
- FIX #3: Separate edge types (DATA_FLOW vs SEMANTIC)
- FIX #4: get_all_downstream returns parameters, not phases
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# EDGE TYPES (FIX #3)
# =============================================================================

class EdgeType(Enum):
    """Type of dependency relationship."""
    DATA_FLOW = "data_flow"      # A's value is computed from B's value
    SEMANTIC = "semantic"        # A's meaning depends on B being set
    VALIDATION = "validation"    # A triggers validation of B
    DERIVED = "derived"          # A is derived from B (read-only)


# =============================================================================
# PHASE OWNERSHIP (FIX #2: Normalized field names)
# =============================================================================

PHASE_OWNERSHIP: Dict[str, List[str]] = {
    "mission": [
        "mission.vessel_type",
        "mission.vessel_name",
        "mission.max_speed_kts",
        "mission.cruise_speed_kts",
        "mission.range_nm",
        "mission.endurance_hours",
        "mission.crew_berthed",
        "mission.passengers",
        "mission.cargo_capacity_mt",
        "mission.operating_area",
        "mission.design_sea_state",
        "mission.classification_society",
        "mission.class_notation",
        "environmental.design_sea_state",
        "environmental.design_wave_height_m",
        "environmental.water_density_kg_m3",
    ],

    "hull_form": [
        "hull.loa",
        "hull.lwl",
        "hull.beam",
        "hull.draft",
        "hull.depth",
        "hull.hull_type",
        "hull.cb",
        "hull.cp",
        "hull.cm",
        "hull.cwp",
        "hull.deadrise_deg",
        "hull.displacement_m3",
        "hull.wetted_surface_m2",
        "hull.waterplane_area_m2",
        "hull.lcb_from_ap_m",
        "hull.lcf_from_ap_m",
        "hull.vcb_m",
        "hull.bmt",
        "hull.bml",
        "hull.kmt",
        "hull.tpc",
        "hull.mct",
        "vision.geometry_generated",
        "vision.mesh_valid",
        "vision.vertex_count",
        "vision.face_count",
        "resistance.total_resistance_kn",
        "resistance.froude_number",
        "resistance.reynolds_number",
    ],

    "structure": [
        "structural_design.hull_material",
        "structural_design.plating_zones",
        "structural_design.bottom_plating_mm",
        "structural_design.side_plating_mm",
        "structural_design.deck_plating_mm",
        "structural_design.frame_spacing_mm",
        "structural_design.longitudinals",
        "structural_design.transverse_frames",
        "structural_design.watertight_bulkheads",
        "structural_design.bulkhead_positions_m",
        "structural_loads.slamming_pressure_kpa",
        "structural_loads.hydrostatic_pressure_kpa",
        "structural_loads.design_vertical_acceleration_g",
        "structural_loads.design_bending_moment_knm",
    ],

    "arrangement": [
        "arrangement.deck_layouts",
        "arrangement.num_decks",
        "arrangement.compartments",
        "arrangement.fuel_tanks",
        "arrangement.fresh_water_tanks",
        "arrangement.ballast_tanks",
        "arrangement.total_fuel_capacity_l",
        "arrangement.total_fw_capacity_l",
        "arrangement.engine_room_volume_m3",
        "arrangement.accommodation_area_m2",
        "outfitting.berth_count",
        "outfitting.cabin_count",
        "outfitting.helm_seats",
        "deck_equipment.anchor_weight_kg",
        "deck_equipment.windlass_type",
        "deck_equipment.cleats_count",
    ],

    "propulsion": [
        "propulsion.propulsion_type",
        "propulsion.total_installed_power_kw",
        "propulsion.num_engines",
        "propulsion.engine_make",
        "propulsion.engine_model",
        "propulsion.engine_power_kw",
        "propulsion.num_propellers",
        "propulsion.propeller_diameter_m",
        "propulsion.propeller_pitch_m",
        "propulsion.propulsive_efficiency",
        "propulsion.fuel_type",
        "propulsion.sfc_g_kwh",
        "performance.speed_power_curve",
        "performance.design_speed_kts",
        "performance.design_power_kw",
        "performance.range_at_cruise_nm",
        "performance.fuel_consumption_cruise_lph",
    ],

    "weight": [
        "weight.lightship_weight_mt",
        "weight.full_load_displacement_mt",
        "weight.deadweight_mt",
        "weight.hull_structure_mt",
        "weight.machinery_mt",
        "weight.outfit_mt",
        "weight.fuel_mt",
        "weight.fresh_water_mt",
        "weight.cargo_mt",
        "weight.lightship_lcg_m",
        "weight.lightship_vcg_m",
        "weight.full_load_lcg_m",
        "weight.full_load_vcg_m",
        "weight.weight_items",
        "weight.free_surface_moment_mt_m",
    ],

    "stability": [
        "stability.gm_transverse_m",
        "stability.gm_longitudinal_m",
        "stability.gz_max_m",
        "stability.angle_of_max_gz_deg",
        "stability.angle_of_vanishing_stability_deg",
        "stability.area_0_30_m_rad",
        "stability.area_0_40_m_rad",
        "stability.area_30_40_m_rad",
        "stability.kg_m",
        "stability.kb_m",
        "stability.bm_m",
        "stability.gz_curve",
        "stability.damage_cases",
        "stability.imo_intact_passed",
        "stability.imo_damage_passed",
        "loading.loading_conditions",
        "loading.current_condition",
        "loading.tank_states",
        "seakeeping.roll_period_s",
        "seakeeping.pitch_period_s",
        "seakeeping.roll_rao",
        "seakeeping.pitch_rao",
        "maneuvering.tactical_diameter_m",
        "maneuvering.turning_radius_m",
    ],

    "compliance": [
        "compliance.overall_passed",
        "compliance.checks",
        "compliance.errors",
        "compliance.warnings",
        "compliance.stability_checks_passed",
        "compliance.structural_checks_passed",
        "compliance.safety_checks_passed",
        "compliance.class_rules",
        "compliance.certifications_required",
        "safety.liferaft_capacity",
        "safety.num_liferafts",
        "safety.lifejackets",
        "safety.fire_detection_zones",
        "safety.escape_routes",
    ],

    "production": [
        "production.build_hours",
        "production.hull_hours",
        "production.material_cost",
        "production.labor_cost",
        "production.build_duration_days",
        "production.milestones",
        "production.yard_name",
        "cost.total_cost",
        "cost.material_cost",
        "cost.labor_cost",
        "cost.engineering_cost",
        "cost.contingency_amount",
        "reports.generated",
        "reports.design_summary",
        "reports.compliance_report",
    ],
}


# Build reverse mapping: parameter -> phase
PARAMETER_TO_PHASE: Dict[str, str] = {}
for phase, params in PHASE_OWNERSHIP.items():
    for param in params:
        PARAMETER_TO_PHASE[param] = phase


def get_phase_for_parameter(param: str) -> Optional[str]:
    """Get the phase that owns a parameter."""
    # Exact match
    if param in PARAMETER_TO_PHASE:
        return PARAMETER_TO_PHASE[param]

    # Prefix match (e.g., "hull.some_new_field" -> "hull_form")
    section = param.split(".")[0] if "." in param else param
    section_to_phase = {
        "mission": "mission",
        "environmental": "mission",
        "hull": "hull_form",
        "vision": "hull_form",
        "resistance": "hull_form",
        "structural_design": "structure",
        "structural_loads": "structure",
        "arrangement": "arrangement",
        "outfitting": "arrangement",
        "deck_equipment": "arrangement",
        "propulsion": "propulsion",
        "performance": "propulsion",
        "weight": "weight",
        "stability": "stability",
        "loading": "stability",
        "seakeeping": "stability",
        "maneuvering": "stability",
        "compliance": "compliance",
        "safety": "compliance",
        "production": "production",
        "cost": "production",
        "reports": "production",
    }
    return section_to_phase.get(section)


def get_parameters_for_phase(phase: str) -> List[str]:
    """Get all parameters owned by a phase."""
    return PHASE_OWNERSHIP.get(phase, [])


# =============================================================================
# PHASE DEPENDENCIES
# =============================================================================

PHASE_DEPENDENCIES: Dict[str, List[str]] = {
    "mission": [],
    "hull_form": ["mission"],
    "structure": ["hull_form"],
    "arrangement": ["hull_form", "structure"],
    "propulsion": ["hull_form", "mission"],
    "weight": ["structure", "propulsion", "arrangement"],
    "stability": ["hull_form", "weight"],
    "compliance": ["structure", "stability", "weight"],
    "production": ["compliance"],
}


DOWNSTREAM_PHASES: Dict[str, List[str]] = {
    "mission": ["hull_form", "propulsion", "weight", "stability", "compliance", "production"],
    "hull_form": ["structure", "arrangement", "propulsion", "weight", "stability", "compliance", "production"],
    "structure": ["arrangement", "weight", "compliance", "production"],
    "arrangement": ["weight", "production"],
    "propulsion": ["weight", "stability", "compliance", "production"],
    "weight": ["stability", "compliance", "production"],
    "stability": ["compliance", "production"],
    "compliance": ["production"],
    "production": [],
}


# =============================================================================
# PARAMETER DEPENDENCIES (FIX #2: Normalized names)
# =============================================================================

PARAMETER_DEPENDENCIES: Dict[str, List[str]] = {
    # Hull computations depend on dimensions
    "hull.displacement_m3": ["hull.loa", "hull.beam", "hull.draft", "hull.cb"],
    "hull.wetted_surface_m2": ["hull.loa", "hull.beam", "hull.draft", "hull.cb"],
    "hull.waterplane_area_m2": ["hull.loa", "hull.beam", "hull.cwp"],

    # Resistance depends on hull form
    "resistance.total_resistance_kn": [
        "hull.loa", "hull.beam", "hull.draft", "hull.displacement_m3",
        "hull.wetted_surface_m2", "mission.max_speed_kts"
    ],
    "resistance.froude_number": ["hull.lwl", "mission.max_speed_kts"],

    # Weight depends on structure and propulsion
    "weight.lightship_weight_mt": [
        "weight.hull_structure_mt", "weight.machinery_mt", "weight.outfit_mt"
    ],
    "weight.full_load_displacement_mt": [
        "weight.lightship_weight_mt", "weight.deadweight_mt"
    ],

    # Stability depends on hull and weight
    "stability.gm_transverse_m": [
        "hull.bmt", "weight.lightship_vcg_m", "hull.vcb_m"
    ],
    "stability.gz_max_m": [
        "stability.gm_transverse_m", "hull.displacement_m3"
    ],

    # Performance depends on resistance and propulsion
    "performance.design_power_kw": [
        "resistance.total_resistance_kn", "propulsion.propulsive_efficiency"
    ],
    "performance.range_at_cruise_nm": [
        "arrangement.total_fuel_capacity_l", "performance.fuel_consumption_cruise_lph",
        "mission.cruise_speed_kts"
    ],

    # Compliance depends on stability and structure
    "compliance.overall_passed": [
        "compliance.stability_checks_passed",
        "compliance.structural_checks_passed",
        "compliance.safety_checks_passed"
    ],
    "compliance.stability_checks_passed": [
        "stability.gm_transverse_m", "stability.gz_max_m"
    ],

    # Cost depends on production
    "cost.total_cost": [
        "cost.material_cost", "cost.labor_cost", "cost.engineering_cost"
    ],
}


# =============================================================================
# DEPENDENCY NODE
# =============================================================================

@dataclass
class DependencyNode:
    """A node in the dependency graph representing a parameter."""
    parameter_path: str
    phase: str

    # Dependencies
    depends_on: Set[str] = field(default_factory=set)
    depended_by: Set[str] = field(default_factory=set)

    # Metadata
    is_computed: bool = False
    computation_order: int = 0
    last_invalidated: Optional[datetime] = None

    def __hash__(self):
        return hash(self.parameter_path)


@dataclass
class DependencyEdge:
    """An edge in the dependency graph."""
    source: str      # Upstream parameter (dependency)
    target: str      # Downstream parameter (dependent)
    edge_type: EdgeType = EdgeType.DATA_FLOW
    weight: float = 1.0

    def __hash__(self):
        return hash((self.source, self.target))


# =============================================================================
# DEPENDENCY GRAPH
# =============================================================================

class DependencyGraphError(Exception):
    """Base exception for dependency graph errors."""
    pass


class CyclicDependencyError(DependencyGraphError):
    """Raised when a cyclic dependency is detected."""

    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        super().__init__(f"Cyclic dependency detected: {' -> '.join(cycle)}")


class DependencyGraph:
    """
    Directed acyclic graph of parameter dependencies.

    v1.1 Fixes:
    - FIX #1: No circular imports
    - FIX #3: Separate edge types
    - FIX #4: get_all_downstream returns parameters
    """

    def __init__(self):
        self._nodes: Dict[str, DependencyNode] = {}
        self._edges: Dict[Tuple[str, str], DependencyEdge] = {}
        self._is_built: bool = False
        self._build_timestamp: Optional[datetime] = None

    def add_parameter(self, param: str, phase: Optional[str] = None) -> DependencyNode:
        """Add a parameter to the graph."""
        if param in self._nodes:
            return self._nodes[param]

        if phase is None:
            phase = get_phase_for_parameter(param) or "unknown"

        node = DependencyNode(parameter_path=param, phase=phase)
        self._nodes[param] = node
        return node

    def add_dependency(
        self,
        dependent: str,
        dependency: str,
        edge_type: EdgeType = EdgeType.DATA_FLOW
    ) -> DependencyEdge:
        """
        Add a dependency: dependent depends on dependency.

        Args:
            dependent: The downstream parameter (computed from dependency)
            dependency: The upstream parameter (input to dependent)
            edge_type: Type of relationship
        """
        # Ensure nodes exist
        self.add_parameter(dependent)
        self.add_parameter(dependency)

        # Create edge
        edge_key = (dependency, dependent)
        if edge_key in self._edges:
            return self._edges[edge_key]

        edge = DependencyEdge(
            source=dependency,
            target=dependent,
            edge_type=edge_type
        )
        self._edges[edge_key] = edge

        # Update node references
        self._nodes[dependent].depends_on.add(dependency)
        self._nodes[dependency].depended_by.add(dependent)

        return edge

    def build_from_definitions(self) -> None:
        """Build graph from PARAMETER_DEPENDENCIES definitions."""
        # Add all parameters from phase ownership
        for phase, params in PHASE_OWNERSHIP.items():
            for param in params:
                self.add_parameter(param, phase)

        # Add explicit dependencies
        for dependent, dependencies in PARAMETER_DEPENDENCIES.items():
            for dep in dependencies:
                self.add_dependency(dependent, dep)

        # Validate no cycles
        cycles = self._detect_cycles()
        if cycles:
            raise CyclicDependencyError(cycles[0])

        # Compute topological order
        self._compute_order()

        self._is_built = True
        self._build_timestamp = datetime.utcnow()

        logger.info(
            f"Dependency graph built: {len(self._nodes)} parameters, "
            f"{len(self._edges)} edges"
        )

    def _detect_cycles(self) -> List[List[str]]:
        """Detect cycles using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(param: str, path: List[str]) -> None:
            visited.add(param)
            rec_stack.add(param)
            path.append(param)

            node = self._nodes.get(param)
            if node:
                for dep in node.depended_by:
                    if dep not in visited:
                        dfs(dep, path.copy())
                    elif dep in rec_stack:
                        cycle_start = path.index(dep)
                        cycles.append(path[cycle_start:] + [dep])

            rec_stack.remove(param)

        for param in self._nodes:
            if param not in visited:
                dfs(param, [])

        return cycles

    def _compute_order(self) -> None:
        """Compute topological order using Kahn's algorithm."""
        in_degree = {p: len(self._nodes[p].depends_on) for p in self._nodes}
        queue = deque([p for p, d in in_degree.items() if d == 0])
        order = 0

        while queue:
            param = queue.popleft()
            self._nodes[param].computation_order = order
            order += 1

            for dependent in self._nodes[param].depended_by:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    def get_direct_dependencies(self, param: str) -> Set[str]:
        """Get parameters that this parameter directly depends on."""
        node = self._nodes.get(param)
        return node.depends_on.copy() if node else set()

    def get_direct_dependents(self, param: str) -> Set[str]:
        """Get parameters that directly depend on this parameter."""
        node = self._nodes.get(param)
        return node.depended_by.copy() if node else set()

    def get_all_dependencies(self, param: str) -> Set[str]:
        """Get all upstream dependencies (transitive closure)."""
        result = set()
        to_process = [param]

        while to_process:
            current = to_process.pop()
            node = self._nodes.get(current)
            if node:
                for dep in node.depends_on:
                    if dep not in result:
                        result.add(dep)
                        to_process.append(dep)

        return result

    def get_all_downstream(self, param: str) -> Set[str]:
        """
        Get all downstream dependents (transitive closure).

        FIX #4: Returns parameter paths, not phase names.
        """
        result = set()
        to_process = [param]

        while to_process:
            current = to_process.pop()
            node = self._nodes.get(current)
            if node:
                for dependent in node.depended_by:
                    if dependent not in result:
                        result.add(dependent)
                        to_process.append(dependent)

        return result

    def get_downstream_phases(self, param: str) -> Set[str]:
        """Get phases affected by changes to this parameter."""
        downstream_params = self.get_all_downstream(param)
        phases = set()

        for p in downstream_params:
            node = self._nodes.get(p)
            if node:
                phases.add(node.phase)

        # Also get phase-level downstream
        param_phase = get_phase_for_parameter(param)
        if param_phase and param_phase in DOWNSTREAM_PHASES:
            phases.update(DOWNSTREAM_PHASES[param_phase])

        return phases

    def get_computation_order(self, params: Set[str]) -> List[str]:
        """Get parameters in computation order (dependencies first)."""
        return sorted(
            params,
            key=lambda p: self._nodes[p].computation_order if p in self._nodes else 0
        )

    def get_recalculation_order(self, changed_params: Set[str]) -> List[str]:
        """
        Get ordered list of parameters to recalculate after changes.

        Returns all downstream parameters in topological order.
        """
        # Collect all downstream parameters
        to_recalculate = set()
        for param in changed_params:
            to_recalculate.update(self.get_all_downstream(param))

        # Return in computation order
        return self.get_computation_order(to_recalculate)

    def get_node(self, param: str) -> Optional[DependencyNode]:
        """Get a node by parameter path."""
        return self._nodes.get(param)

    def get_edge(self, source: str, target: str) -> Optional[DependencyEdge]:
        """Get an edge by source and target."""
        return self._edges.get((source, target))

    def has_parameter(self, param: str) -> bool:
        """Check if parameter exists in graph."""
        return param in self._nodes

    def get_all_parameters(self) -> List[str]:
        """Get all parameters in computation order."""
        return self.get_computation_order(set(self._nodes.keys()))

    def get_parameters_for_phase(self, phase: str) -> List[str]:
        """Get all parameters owned by a phase."""
        return [
            p for p, n in self._nodes.items()
            if n.phase == phase
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph for persistence."""
        return {
            "nodes": {
                p: {
                    "phase": n.phase,
                    "depends_on": list(n.depends_on),
                    "depended_by": list(n.depended_by),
                    "is_computed": n.is_computed,
                    "computation_order": n.computation_order,
                }
                for p, n in self._nodes.items()
            },
            "edges": [
                {
                    "source": e.source,
                    "target": e.target,
                    "edge_type": e.edge_type.value,
                    "weight": e.weight,
                }
                for e in self._edges.values()
            ],
            "build_timestamp": self._build_timestamp.isoformat() if self._build_timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DependencyGraph":
        """Load graph from serialized data."""
        graph = cls()

        for param, node_data in data.get("nodes", {}).items():
            node = graph.add_parameter(param, node_data.get("phase"))
            node.is_computed = node_data.get("is_computed", False)
            node.computation_order = node_data.get("computation_order", 0)

        for edge_data in data.get("edges", []):
            graph.add_dependency(
                edge_data["target"],
                edge_data["source"],
                EdgeType(edge_data.get("edge_type", "data_flow"))
            )

        graph._is_built = True
        if data.get("build_timestamp"):
            graph._build_timestamp = datetime.fromisoformat(data["build_timestamp"])

        return graph


# =============================================================================
# MODULE-LEVEL INSTANCE
# =============================================================================

_default_graph: Optional[DependencyGraph] = None


def get_default_graph() -> DependencyGraph:
    """Get or create the default dependency graph."""
    global _default_graph
    if _default_graph is None:
        _default_graph = DependencyGraph()
        _default_graph.build_from_definitions()
    return _default_graph
