"""
Integration tests for production planning pipeline.

Tests full flow from hull dimensions through production planning.
"""

import pytest
from datetime import date

from magnet.production.material_takeoff import MaterialTakeoff
from magnet.production.assembly import AssemblySequencer
from magnet.production.schedule import BuildScheduler
from magnet.production.validators import (
    ProductionPlanningValidator,
    get_production_planning_definition,
)
from magnet.production.enums import MaterialCategory, AssemblyLevel, ProductionPhase


class MockStateManager:
    """Mock StateManager for integration testing."""

    def __init__(self, data: dict = None):
        self._data = data or {}
        self._writes = {}

    def get(self, key: str, default=None):
        """Get value by dotted key."""
        keys = key.split(".")
        current = self._data
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def write(self, key: str, value, agent: str, description: str):
        """Record a write operation."""
        self._writes[key] = {
            "value": value,
            "agent": agent,
            "description": description,
        }

    def set(self, key: str, value, source=None):
        """Set value by dotted key."""
        self._writes[key] = {"value": value, "agent": source or "", "description": ""}

    def get_written(self, key: str):
        """Get a written value."""
        if key in self._writes:
            return self._writes[key]["value"]
        return None


class TestProductionPipeline:
    """Test full production planning pipeline."""

    @pytest.fixture
    def state_25m_patrol(self):
        """State for 25m patrol boat."""
        return MockStateManager({
            "hull": {
                "lwl": 25.0,
                "beam": 6.0,
                "depth": 3.0,
            },
            "structure": {
                "material": "aluminum_5083",
                "frame_spacing_mm": 500.0,
                "bottom_plate_thickness_mm": 8.0,
                "side_plate_thickness_mm": 6.0,
                "deck_plate_thickness_mm": 5.0,
            },
            "mission": {
                "vessel_type": "patrol",
            },
        })

    @pytest.fixture
    def state_50m_workboat(self):
        """State for 50m offshore workboat."""
        return MockStateManager({
            "hull": {
                "lwl": 50.0,
                "beam": 12.0,
                "depth": 5.0,
            },
            "structure": {
                "material": "steel_mild",
                "frame_spacing_mm": 600.0,
                "bottom_plate_thickness_mm": 12.0,
                "side_plate_thickness_mm": 10.0,
                "deck_plate_thickness_mm": 8.0,
            },
            "mission": {
                "vessel_type": "offshore_supply",
            },
        })

    def test_full_pipeline_25m_patrol(self, state_25m_patrol):
        """Test full pipeline for 25m patrol boat."""
        # Step 1: Material Takeoff
        takeoff = MaterialTakeoff()
        material_result = takeoff.calculate(state_25m_patrol)

        assert material_result.item_count > 0
        assert material_result.total_weight_kg > 0

        # Step 2: Assembly Sequence
        sequencer = AssemblySequencer()
        assembly_result = sequencer.generate_sequence(state_25m_patrol)

        assert assembly_result.package_count > 0
        assert assembly_result.total_work_hours > 0

        # Step 3: Build Schedule
        scheduler = BuildScheduler()
        start_date = date(2025, 1, 1)
        schedule_result = scheduler.generate_schedule(
            state_25m_patrol,
            assembly_result=assembly_result,
            material_result=material_result,
            start_date=start_date,
        )

        assert schedule_result.milestone_count > 0
        assert schedule_result.total_days > 0
        assert schedule_result.end_date > start_date

        # Verify reasonable values for 25m vessel
        assert 5000 <= material_result.total_weight_kg <= 50000
        assert 500 <= assembly_result.total_work_hours <= 10000
        assert 30 <= schedule_result.total_days <= 365

    def test_full_pipeline_50m_workboat(self, state_50m_workboat):
        """Test full pipeline for 50m steel workboat."""
        takeoff = MaterialTakeoff()
        material_result = takeoff.calculate(state_50m_workboat)

        sequencer = AssemblySequencer()
        assembly_result = sequencer.generate_sequence(state_50m_workboat)

        scheduler = BuildScheduler()
        schedule_result = scheduler.generate_schedule(
            state_50m_workboat,
            assembly_result=assembly_result,
            material_result=material_result,
            start_date=date(2025, 1, 1),
        )

        # Steel vessel should be heavier
        assert material_result.total_weight_kg > 50000

        # Larger vessel needs more time
        assert schedule_result.total_days > 100

    def test_validator_integration(self, state_25m_patrol):
        """Test validator runs complete pipeline."""
        defn = get_production_planning_definition()
        validator = ProductionPlanningValidator(defn)

        result = validator.validate(state_25m_patrol, {})

        # Should pass or warn
        assert result.error_count == 0

        # Should write all outputs
        assert state_25m_patrol.get_written("production.material_takeoff") is not None
        assert state_25m_patrol.get_written("production.assembly_sequence") is not None
        assert state_25m_patrol.get_written("production.build_schedule") is not None
        assert state_25m_patrol.get_written("production.summary") is not None

    def test_pipeline_data_consistency(self, state_25m_patrol):
        """Test data is consistent across pipeline stages."""
        defn = get_production_planning_definition()
        validator = ProductionPlanningValidator(defn)
        validator.validate(state_25m_patrol, {"start_date": date(2025, 1, 1)})

        # Get all outputs
        takeoff = state_25m_patrol.get_written("production.material_takeoff")
        sequence = state_25m_patrol.get_written("production.assembly_sequence")
        schedule = state_25m_patrol.get_written("production.build_schedule")
        summary = state_25m_patrol.get_written("production.summary")

        # Summary should match individual results
        assert summary["material_weight_kg"] == takeoff["summary"]["total_weight_kg"]
        assert summary["work_packages"] == sequence["summary"]["package_count"]
        assert summary["total_work_hours"] == sequence["summary"]["total_work_hours"]
        assert summary["build_duration_days"] == schedule["summary"]["total_days"]

    def test_pipeline_respects_material_type(self):
        """Test pipeline produces different results for different materials."""
        alu_state = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
            "structure": {"material": "aluminum_5083"},
        })
        steel_state = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
            "structure": {"material": "steel_mild"},
        })

        takeoff = MaterialTakeoff()
        alu_result = takeoff.calculate(alu_state)
        steel_result = takeoff.calculate(steel_state)

        # Steel plates should be ~3x heavier (profiles use fixed kg/m)
        assert steel_result.plate_weight_kg > alu_result.plate_weight_kg * 2.5
        # Total weight should still be significantly more
        assert steel_result.total_weight_kg > alu_result.total_weight_kg * 1.5

    def test_pipeline_scales_with_size(self):
        """Test pipeline scales appropriately with vessel size."""
        small = MockStateManager({
            "hull": {"lwl": 15.0, "beam": 4.0, "depth": 2.0},
            "structure": {"frame_spacing_mm": 400.0},
        })
        large = MockStateManager({
            "hull": {"lwl": 40.0, "beam": 10.0, "depth": 4.5},
            "structure": {"frame_spacing_mm": 600.0},
        })

        defn = get_production_planning_definition()
        validator = ProductionPlanningValidator(defn)

        validator.validate(small, {})
        small_summary = small.get_written("production.summary")

        validator.validate(large, {})
        large_summary = large.get_written("production.summary")

        # Larger vessel should have more of everything
        assert large_summary["material_weight_kg"] > small_summary["material_weight_kg"]
        assert large_summary["work_packages"] > small_summary["work_packages"]
        assert large_summary["total_work_hours"] > small_summary["total_work_hours"]
        assert large_summary["build_duration_days"] > small_summary["build_duration_days"]


class TestAssemblyDependencyFlow:
    """Test assembly sequence dependency correctness."""

    def test_dependency_order_correct(self):
        """Test dependencies flow correctly through levels."""
        state = MockStateManager({
            "hull": {"lwl": 25.0, "beam": 6.0, "depth": 3.0},
            "structure": {"frame_spacing_mm": 500.0},
        })

        sequencer = AssemblySequencer()
        result = sequencer.generate_sequence(state)

        # Build package map
        pkg_map = {p.package_id: p for p in result.packages}

        # Verify all dependencies exist and are valid
        for pkg in result.packages:
            for dep_id in pkg.dependencies:
                assert dep_id in pkg_map, f"Missing dependency {dep_id}"
                dep = pkg_map[dep_id]

                # Dependency should be at same or lower level
                level_order = [
                    AssemblyLevel.COMPONENT,
                    AssemblyLevel.SUBASSEMBLY,
                    AssemblyLevel.UNIT,
                    AssemblyLevel.ZONE,
                    AssemblyLevel.HULL,
                ]
                pkg_idx = level_order.index(pkg.assembly_level)
                dep_idx = level_order.index(dep.assembly_level)
                assert dep_idx <= pkg_idx

    def test_critical_path_is_achievable(self):
        """Test critical path represents achievable sequence."""
        state = MockStateManager({
            "hull": {"lwl": 25.0, "beam": 6.0, "depth": 3.0},
        })

        sequencer = AssemblySequencer()
        result = sequencer.generate_sequence(state)

        # Critical path should be sum of longest chain
        pkg_map = {p.package_id: p for p in result.packages}

        def get_finish_time(pkg_id, memo={}):
            if pkg_id in memo:
                return memo[pkg_id]
            pkg = pkg_map[pkg_id]
            if not pkg.dependencies:
                result_time = pkg.work_hours
            else:
                max_dep = max(get_finish_time(d, memo) for d in pkg.dependencies)
                result_time = max_dep + pkg.work_hours
            memo[pkg_id] = result_time
            return result_time

        # Calculate actual critical path
        max_finish = max(get_finish_time(p.package_id) for p in result.packages)

        # Should match reported critical path
        assert abs(max_finish - result.critical_path_hours) < 1.0


class TestSchedulePhaseCoverage:
    """Test schedule covers all production phases."""

    def test_all_phases_present(self):
        """Test all production phases are in schedule."""
        state = MockStateManager({
            "hull": {"lwl": 25.0, "beam": 6.0, "depth": 3.0},
        })

        scheduler = BuildScheduler()
        result = scheduler.generate_schedule(state, start_date=date(2025, 1, 1))

        phases_found = {m.phase for m in result.milestones}

        for phase in ProductionPhase:
            assert phase in phases_found, f"Missing phase {phase}"

    def test_phases_in_order(self):
        """Test phases are in correct order."""
        state = MockStateManager({
            "hull": {"lwl": 25.0, "beam": 6.0, "depth": 3.0},
        })

        scheduler = BuildScheduler()
        result = scheduler.generate_schedule(state, start_date=date(2025, 1, 1))

        # Get phase order from milestones
        phase_sequence = [m.phase for m in result.milestones]

        expected_order = list(ProductionPhase)

        # Phases should appear in enum order
        for i in range(len(phase_sequence) - 1):
            idx1 = expected_order.index(phase_sequence[i])
            idx2 = expected_order.index(phase_sequence[i + 1])
            assert idx1 <= idx2, f"{phase_sequence[i]} should not come before {phase_sequence[i+1]}"

    def test_delivery_is_last(self):
        """Test delivery phase is last."""
        state = MockStateManager({
            "hull": {"lwl": 25.0, "beam": 6.0, "depth": 3.0},
        })

        scheduler = BuildScheduler()
        result = scheduler.generate_schedule(state, start_date=date(2025, 1, 1))

        last_milestone = result.milestones[-1]
        assert last_milestone.phase == ProductionPhase.DELIVERY


class TestMaterialBreakdown:
    """Test material takeoff breakdown accuracy."""

    def test_plate_profile_separation(self):
        """Test plates and profiles are correctly categorized."""
        state = MockStateManager({
            "hull": {"lwl": 25.0, "beam": 6.0, "depth": 3.0},
            "structure": {
                "bottom_plate_thickness_mm": 8.0,
                "frame_spacing_mm": 500.0,
            },
        })

        takeoff = MaterialTakeoff()
        result = takeoff.calculate(state)

        # Separate plate and profile items
        plates = [i for i in result.items if i.category == MaterialCategory.PLATE]
        profiles = [i for i in result.items if i.category == MaterialCategory.PROFILE]

        assert len(plates) > 0
        assert len(profiles) > 0

        # All plates should have thickness
        assert all(p.thickness_mm is not None for p in plates)

        # All profiles should have length
        assert all(p.length_m is not None for p in profiles)

    def test_weight_calculation_correct(self):
        """Test weight calculations use correct formulas."""
        state = MockStateManager({
            "hull": {"lwl": 10.0, "beam": 3.0, "depth": 1.5},
            "structure": {
                "material": "aluminum_5083",
                "bottom_plate_thickness_mm": 6.0,
            },
        })

        takeoff = MaterialTakeoff()
        result = takeoff.calculate(state)

        # Find bottom plate
        bottom = next(
            (i for i in result.items if "Bottom" in i.description),
            None
        )

        if bottom:
            # Weight = area * thickness * density
            # density for aluminum_5083 = 2660 kg/m³
            expected_weight = bottom.area_m2 * (6.0 / 1000) * 2660
            assert abs(bottom.weight_kg - expected_weight) < 1.0
