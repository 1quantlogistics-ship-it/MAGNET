"""
production/assembly.py - Work breakdown and assembly sequencing.

BRAVO OWNS THIS FILE.

Module 11 v1.1 - Assembly sequence generator.

v1.1 NOTE: Assembly sequence code unchanged from v1.0 - no field name changes.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Set

from .enums import AssemblyLevel, WorkPackageType
from .models import WorkPackage, AssemblySequenceResult

if TYPE_CHECKING:
    from ..core.state_manager import StateManager


class AssemblySequencer:
    """
    Work breakdown and assembly sequence generator.

    Creates work packages organized by assembly level and determines
    dependencies for scheduling.
    """

    # Work hours per unit for different package types (parametric)
    HOURS_PER_M2_PLATE = 2.0  # Hours per m² of plate work
    HOURS_PER_M_PROFILE = 0.5  # Hours per meter of profile work
    HOURS_PER_M_WELD = 1.5  # Hours per meter of welding

    def __init__(self, productivity_factor: float = 1.0):
        """
        Initialize assembly sequencer.

        Args:
            productivity_factor: Adjust work hours (< 1 = faster, > 1 = slower)
        """
        self.productivity_factor = productivity_factor
        self._package_counter = 0

    def generate_sequence(self, state: "StateManager") -> AssemblySequenceResult:
        """
        Generate assembly sequence from state.

        Args:
            state: StateManager with hull and material data

        Returns:
            AssemblySequenceResult with work packages and summary
        """
        result = AssemblySequenceResult()
        self._package_counter = 0

        # Get dimensions
        lwl = state.get("hull.lwl", 0)
        beam = state.get("hull.beam", 0)
        depth = state.get("hull.depth", 0)

        if lwl <= 0 or beam <= 0 or depth <= 0:
            return result

        # Get frame spacing for zone division
        frame_spacing_mm = state.get("structure.frame_spacing_mm", 500.0)
        frame_spacing_m = frame_spacing_mm / 1000.0

        # Calculate number of zones (blocks)
        num_zones = max(3, int(lwl / 5))  # ~5m zones

        # === LEVEL 1: COMPONENT FABRICATION ===

        # Plate cutting packages (per zone)
        plate_packages = []
        for i in range(num_zones):
            zone_name = f"Zone-{i+1:02d}"
            pkg = self._create_package(
                name=f"Plate Cutting - {zone_name}",
                package_type=WorkPackageType.FABRICATION,
                assembly_level=AssemblyLevel.COMPONENT,
                work_hours=self._estimate_plate_hours(lwl, beam, depth, num_zones),
                zone=zone_name,
                description=f"Cut and prepare plates for {zone_name}",
            )
            plate_packages.append(pkg)
            result.packages.append(pkg)

        # Profile cutting packages (per zone)
        profile_packages = []
        for i in range(num_zones):
            zone_name = f"Zone-{i+1:02d}"
            pkg = self._create_package(
                name=f"Profile Cutting - {zone_name}",
                package_type=WorkPackageType.FABRICATION,
                assembly_level=AssemblyLevel.COMPONENT,
                work_hours=self._estimate_profile_hours(lwl, beam, depth, num_zones, frame_spacing_m),
                zone=zone_name,
                description=f"Cut and prepare profiles for {zone_name}",
            )
            profile_packages.append(pkg)
            result.packages.append(pkg)

        # === LEVEL 2: SUBASSEMBLY ===

        # Panel assembly packages (stiffened panels)
        panel_packages = []
        for i in range(num_zones):
            zone_name = f"Zone-{i+1:02d}"
            dependencies = [
                plate_packages[i].package_id,
                profile_packages[i].package_id,
            ]
            pkg = self._create_package(
                name=f"Panel Assembly - {zone_name}",
                package_type=WorkPackageType.WELDING,
                assembly_level=AssemblyLevel.SUBASSEMBLY,
                work_hours=self._estimate_panel_hours(lwl, beam, depth, num_zones),
                zone=zone_name,
                dependencies=dependencies,
                description=f"Weld stiffeners to panels for {zone_name}",
            )
            panel_packages.append(pkg)
            result.packages.append(pkg)

        # === LEVEL 3: UNIT ASSEMBLY ===

        # Block assembly packages
        block_packages = []
        for i in range(num_zones):
            zone_name = f"Zone-{i+1:02d}"
            dependencies = [panel_packages[i].package_id]
            pkg = self._create_package(
                name=f"Block Assembly - {zone_name}",
                package_type=WorkPackageType.WELDING,
                assembly_level=AssemblyLevel.UNIT,
                work_hours=self._estimate_block_hours(lwl, beam, depth, num_zones),
                zone=zone_name,
                dependencies=dependencies,
                description=f"Assemble 3D block structure for {zone_name}",
            )
            block_packages.append(pkg)
            result.packages.append(pkg)

        # === LEVEL 4: ZONE JOINING ===

        # Block joining - sequential from aft to fwd
        join_packages = []
        for i in range(num_zones - 1):
            zone_name = f"Join-{i+1:02d}/{i+2:02d}"
            # Depends on both adjacent blocks
            dependencies = [
                block_packages[i].package_id,
                block_packages[i + 1].package_id,
            ]
            # Also depends on previous join if exists
            if join_packages:
                dependencies.append(join_packages[-1].package_id)

            pkg = self._create_package(
                name=f"Block Joining - {zone_name}",
                package_type=WorkPackageType.WELDING,
                assembly_level=AssemblyLevel.ZONE,
                work_hours=self._estimate_join_hours(beam, depth),
                zone=zone_name,
                dependencies=dependencies,
                description=f"Weld blocks together at {zone_name}",
            )
            join_packages.append(pkg)
            result.packages.append(pkg)

        # === LEVEL 5: HULL COMPLETION ===

        # Final hull welding
        final_weld_deps = [p.package_id for p in join_packages] if join_packages else [
            p.package_id for p in block_packages
        ]
        final_weld = self._create_package(
            name="Final Hull Welding",
            package_type=WorkPackageType.WELDING,
            assembly_level=AssemblyLevel.HULL,
            work_hours=self._estimate_final_weld_hours(lwl, beam),
            dependencies=final_weld_deps,
            description="Complete all hull welding and inspection",
        )
        result.packages.append(final_weld)

        # Hull testing
        test_pkg = self._create_package(
            name="Hull Testing",
            package_type=WorkPackageType.TESTING,
            assembly_level=AssemblyLevel.HULL,
            work_hours=max(40, lwl * 2),  # Min 40 hours, ~2h per meter
            dependencies=[final_weld.package_id],
            description="Watertight testing and NDT inspection",
        )
        result.packages.append(test_pkg)

        # Painting
        paint_pkg = self._create_package(
            name="Hull Painting",
            package_type=WorkPackageType.PAINTING,
            assembly_level=AssemblyLevel.HULL,
            work_hours=self._estimate_paint_hours(lwl, beam, depth),
            dependencies=[test_pkg.package_id],
            description="Surface preparation and paint application",
        )
        result.packages.append(paint_pkg)

        # === CALCULATE TOTALS ===

        result.total_work_hours = sum(p.work_hours for p in result.packages)
        result.critical_path_hours = self._calculate_critical_path(result.packages)

        return result

    def _create_package(
        self,
        name: str,
        package_type: WorkPackageType,
        assembly_level: AssemblyLevel,
        work_hours: float,
        zone: str = None,
        dependencies: List[str] = None,
        description: str = "",
    ) -> WorkPackage:
        """Create a work package with unique ID."""
        self._package_counter += 1
        return WorkPackage(
            package_id=f"WP-{self._package_counter:04d}",
            name=name,
            package_type=package_type,
            assembly_level=assembly_level,
            work_hours=round(work_hours * self.productivity_factor, 1),
            dependencies=dependencies or [],
            zone=zone,
            description=description,
        )

    def _estimate_plate_hours(
        self, lwl: float, beam: float, depth: float, num_zones: int
    ) -> float:
        """Estimate plate cutting hours per zone."""
        # Total plate area approximation
        total_area = (lwl * beam) + (2 * lwl * depth) + (lwl * beam * 0.9)
        area_per_zone = total_area / num_zones
        return area_per_zone * self.HOURS_PER_M2_PLATE * 0.3  # Cutting is ~30% of total

    def _estimate_profile_hours(
        self,
        lwl: float,
        beam: float,
        depth: float,
        num_zones: int,
        frame_spacing_m: float,
    ) -> float:
        """Estimate profile cutting hours per zone."""
        # Total profile length approximation
        num_frames = int(lwl / frame_spacing_m) if frame_spacing_m > 0 else 20
        frame_length = (beam + 2 * depth) * num_frames
        num_longitudinals = int(beam / 0.3) * 2
        long_length = lwl * num_longitudinals

        total_length = frame_length + long_length
        length_per_zone = total_length / num_zones
        return length_per_zone * self.HOURS_PER_M_PROFILE * 0.4  # Cutting is ~40%

    def _estimate_panel_hours(
        self, lwl: float, beam: float, depth: float, num_zones: int
    ) -> float:
        """Estimate panel assembly (welding) hours per zone."""
        # Stiffener welding - mostly fillet welds
        total_area = (lwl * beam * 2) + (2 * lwl * depth)
        area_per_zone = total_area / num_zones
        # Assume ~0.5m of weld per m² of panel
        weld_length = area_per_zone * 0.5
        return weld_length * self.HOURS_PER_M_WELD

    def _estimate_block_hours(
        self, lwl: float, beam: float, depth: float, num_zones: int
    ) -> float:
        """Estimate 3D block assembly hours per zone."""
        # More complex than panel - fitting and welding
        zone_length = lwl / num_zones
        perimeter = 2 * (beam + depth)
        # Butt welds at panel intersections
        weld_length = perimeter * zone_length * 0.3  # ~30% of internal perimeter
        return weld_length * self.HOURS_PER_M_WELD * 1.5  # More complex welds

    def _estimate_join_hours(self, beam: float, depth: float) -> float:
        """Estimate block joining hours."""
        # Full perimeter butt weld
        perimeter = 2 * (beam + depth)
        return perimeter * self.HOURS_PER_M_WELD * 2.0  # Heavy butt welds

    def _estimate_final_weld_hours(self, lwl: float, beam: float) -> float:
        """Estimate final welding hours."""
        # Cleanup welds, deck penetrations, etc.
        return max(80, (lwl * beam) * 0.1)  # Min 80 hours

    def _estimate_paint_hours(
        self, lwl: float, beam: float, depth: float
    ) -> float:
        """Estimate painting hours."""
        # Total surface area
        area = (lwl * beam * 2) + (2 * lwl * depth)
        # ~0.5 hours per m² for prep + prime + finish
        return area * 0.5

    def _calculate_critical_path(self, packages: List[WorkPackage]) -> float:
        """
        Calculate critical path duration.

        Simple implementation: finds longest path through dependency graph.
        """
        if not packages:
            return 0.0

        # Build package lookup
        pkg_map: Dict[str, WorkPackage] = {p.package_id: p for p in packages}

        # Calculate earliest finish for each package (topological order)
        earliest_finish: Dict[str, float] = {}

        def get_earliest_finish(pkg_id: str) -> float:
            if pkg_id in earliest_finish:
                return earliest_finish[pkg_id]

            pkg = pkg_map.get(pkg_id)
            if not pkg:
                return 0.0

            # Start after all dependencies finish
            if pkg.dependencies:
                earliest_start = max(
                    get_earliest_finish(dep) for dep in pkg.dependencies
                )
            else:
                earliest_start = 0.0

            finish = earliest_start + pkg.work_hours
            earliest_finish[pkg_id] = finish
            return finish

        # Calculate for all packages
        for pkg in packages:
            get_earliest_finish(pkg.package_id)

        return max(earliest_finish.values()) if earliest_finish else 0.0
