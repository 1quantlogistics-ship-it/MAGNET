"""
Unit tests for production assembly sequencer.

Tests AssemblySequencer work package generation.
"""

import pytest
from magnet.production.assembly import AssemblySequencer
from magnet.production.models import WorkPackage, AssemblySequenceResult
from magnet.production.enums import AssemblyLevel, WorkPackageType


class MockStateManager:
    """Mock StateManager for testing."""

    def __init__(self, data: dict = None):
        self._data = data or {}

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


class TestAssemblySequencer:
    """Tests for AssemblySequencer."""

    @pytest.fixture
    def sequencer(self):
        """Create sequencer instance."""
        return AssemblySequencer()

    @pytest.fixture
    def state_25m_workboat(self):
        """Create state for 25m workboat."""
        return MockStateManager({
            "hull": {
                "lwl": 25.0,
                "beam": 6.0,
                "depth": 3.0,
            },
            "structure": {
                "frame_spacing_mm": 500.0,
            },
        })

    def test_basic_sequence_generation(self, sequencer, state_25m_workboat):
        """Test basic sequence generation."""
        result = sequencer.generate_sequence(state_25m_workboat)

        assert isinstance(result, AssemblySequenceResult)
        assert result.package_count > 0
        assert result.total_work_hours > 0
        assert result.critical_path_hours > 0

    def test_empty_dimensions_returns_empty_result(self, sequencer):
        """Test empty dimensions return empty result."""
        state = MockStateManager({})
        result = sequencer.generate_sequence(state)

        assert result.package_count == 0
        assert result.total_work_hours == 0

    def test_zero_dimensions_returns_empty_result(self, sequencer):
        """Test zero dimensions return empty result."""
        state = MockStateManager({
            "hull": {"lwl": 0, "beam": 0, "depth": 0}
        })
        result = sequencer.generate_sequence(state)

        assert result.package_count == 0
        assert result.total_work_hours == 0

    def test_packages_have_unique_ids(self, sequencer, state_25m_workboat):
        """Test all packages have unique IDs."""
        result = sequencer.generate_sequence(state_25m_workboat)
        ids = [pkg.package_id for pkg in result.packages]

        assert len(ids) == len(set(ids))

    def test_component_level_packages(self, sequencer, state_25m_workboat):
        """Test component level packages exist."""
        result = sequencer.generate_sequence(state_25m_workboat)

        component_pkgs = [
            p for p in result.packages
            if p.assembly_level == AssemblyLevel.COMPONENT
        ]
        assert len(component_pkgs) > 0

        # Should include plate and profile cutting
        has_plate = any("Plate" in p.name for p in component_pkgs)
        has_profile = any("Profile" in p.name for p in component_pkgs)
        assert has_plate
        assert has_profile

    def test_subassembly_level_packages(self, sequencer, state_25m_workboat):
        """Test subassembly level packages exist."""
        result = sequencer.generate_sequence(state_25m_workboat)

        subasm_pkgs = [
            p for p in result.packages
            if p.assembly_level == AssemblyLevel.SUBASSEMBLY
        ]
        assert len(subasm_pkgs) > 0

    def test_unit_level_packages(self, sequencer, state_25m_workboat):
        """Test unit (block) level packages exist."""
        result = sequencer.generate_sequence(state_25m_workboat)

        unit_pkgs = [
            p for p in result.packages
            if p.assembly_level == AssemblyLevel.UNIT
        ]
        assert len(unit_pkgs) > 0

    def test_hull_level_packages(self, sequencer, state_25m_workboat):
        """Test hull level packages exist."""
        result = sequencer.generate_sequence(state_25m_workboat)

        hull_pkgs = [
            p for p in result.packages
            if p.assembly_level == AssemblyLevel.HULL
        ]
        assert len(hull_pkgs) > 0

        # Should include final welding, testing, painting
        pkg_names = [p.name for p in hull_pkgs]
        assert any("Weld" in n for n in pkg_names)
        assert any("Test" in n for n in pkg_names)
        assert any("Paint" in n for n in pkg_names)

    def test_dependencies_valid(self, sequencer, state_25m_workboat):
        """Test all dependencies reference valid packages."""
        result = sequencer.generate_sequence(state_25m_workboat)

        all_ids = {pkg.package_id for pkg in result.packages}

        for pkg in result.packages:
            for dep in pkg.dependencies:
                assert dep in all_ids, f"Invalid dependency {dep} in {pkg.package_id}"

    def test_no_circular_dependencies(self, sequencer, state_25m_workboat):
        """Test no circular dependencies exist."""
        result = sequencer.generate_sequence(state_25m_workboat)

        # Build dependency graph
        deps = {pkg.package_id: set(pkg.dependencies) for pkg in result.packages}

        # Check for cycles using topological sort approach
        visited = set()
        in_stack = set()

        def has_cycle(node):
            if node in in_stack:
                return True
            if node in visited:
                return False

            visited.add(node)
            in_stack.add(node)

            for dep in deps.get(node, []):
                if has_cycle(dep):
                    return True

            in_stack.remove(node)
            return False

        for pkg_id in deps:
            assert not has_cycle(pkg_id), f"Circular dependency involving {pkg_id}"

    def test_component_packages_no_dependencies(self, sequencer, state_25m_workboat):
        """Test component level packages have no dependencies."""
        result = sequencer.generate_sequence(state_25m_workboat)

        component_pkgs = [
            p for p in result.packages
            if p.assembly_level == AssemblyLevel.COMPONENT
        ]

        for pkg in component_pkgs:
            assert len(pkg.dependencies) == 0

    def test_higher_levels_depend_on_lower(self, sequencer, state_25m_workboat):
        """Test higher assembly levels depend on lower levels."""
        result = sequencer.generate_sequence(state_25m_workboat)

        pkg_map = {p.package_id: p for p in result.packages}
        level_order = [
            AssemblyLevel.COMPONENT,
            AssemblyLevel.SUBASSEMBLY,
            AssemblyLevel.UNIT,
            AssemblyLevel.ZONE,
            AssemblyLevel.HULL,
        ]

        for pkg in result.packages:
            pkg_level_idx = level_order.index(pkg.assembly_level)

            for dep_id in pkg.dependencies:
                dep_pkg = pkg_map.get(dep_id)
                if dep_pkg:
                    dep_level_idx = level_order.index(dep_pkg.assembly_level)
                    assert dep_level_idx <= pkg_level_idx, \
                        f"{pkg.package_id} ({pkg.assembly_level}) depends on {dep_id} ({dep_pkg.assembly_level})"

    def test_work_package_types(self, sequencer, state_25m_workboat):
        """Test various work package types are created."""
        result = sequencer.generate_sequence(state_25m_workboat)

        types_found = {pkg.package_type for pkg in result.packages}

        assert WorkPackageType.FABRICATION in types_found
        assert WorkPackageType.WELDING in types_found
        assert WorkPackageType.TESTING in types_found
        assert WorkPackageType.PAINTING in types_found

    def test_critical_path_less_than_total(self, sequencer, state_25m_workboat):
        """Test critical path is less than or equal to total hours."""
        result = sequencer.generate_sequence(state_25m_workboat)

        assert result.critical_path_hours <= result.total_work_hours
        # Critical path should be a significant portion
        assert result.critical_path_hours >= result.total_work_hours * 0.1

    def test_larger_vessel_more_packages(self, sequencer):
        """Test larger vessel has more work packages."""
        small = MockStateManager({
            "hull": {"lwl": 15.0, "beam": 4.0, "depth": 2.0},
        })
        large = MockStateManager({
            "hull": {"lwl": 30.0, "beam": 8.0, "depth": 4.0},
        })

        small_result = sequencer.generate_sequence(small)
        large_result = sequencer.generate_sequence(large)

        assert large_result.package_count > small_result.package_count
        assert large_result.total_work_hours > small_result.total_work_hours

    def test_productivity_factor(self):
        """Test productivity factor adjusts work hours."""
        state = MockStateManager({
            "hull": {"lwl": 20.0, "beam": 5.0, "depth": 2.5},
        })

        normal = AssemblySequencer(productivity_factor=1.0)
        slow = AssemblySequencer(productivity_factor=1.5)

        normal_result = normal.generate_sequence(state)
        slow_result = slow.generate_sequence(state)

        # Same number of packages
        assert normal_result.package_count == slow_result.package_count
        # More hours with slower productivity
        assert slow_result.total_work_hours > normal_result.total_work_hours

    def test_result_to_dict(self, sequencer, state_25m_workboat):
        """Test result serialization."""
        result = sequencer.generate_sequence(state_25m_workboat)
        data = result.to_dict()

        assert "packages" in data
        assert "summary" in data
        assert data["summary"]["package_count"] == result.package_count
        assert data["summary"]["total_work_hours"] == round(result.total_work_hours, 1)

    def test_zone_assignments(self, sequencer, state_25m_workboat):
        """Test packages have zone assignments."""
        result = sequencer.generate_sequence(state_25m_workboat)

        # Component, subassembly, unit packages should have zones
        zoned_levels = [AssemblyLevel.COMPONENT, AssemblyLevel.SUBASSEMBLY, AssemblyLevel.UNIT]
        zoned_pkgs = [p for p in result.packages if p.assembly_level in zoned_levels]

        assert all(pkg.zone is not None for pkg in zoned_pkgs)


class TestWorkPackage:
    """Tests for WorkPackage dataclass."""

    def test_create_work_package(self):
        """Test creating work package."""
        pkg = WorkPackage(
            package_id="WP-0001",
            name="Plate Cutting - Zone-01",
            package_type=WorkPackageType.FABRICATION,
            assembly_level=AssemblyLevel.COMPONENT,
            work_hours=40.0,
            zone="Zone-01",
            description="Cut and prepare plates for Zone-01",
        )

        assert pkg.package_id == "WP-0001"
        assert pkg.package_type == WorkPackageType.FABRICATION
        assert pkg.assembly_level == AssemblyLevel.COMPONENT
        assert pkg.work_hours == 40.0
        assert pkg.zone == "Zone-01"

    def test_package_with_dependencies(self):
        """Test package with dependencies."""
        pkg = WorkPackage(
            package_id="WP-0010",
            name="Panel Assembly - Zone-01",
            package_type=WorkPackageType.WELDING,
            assembly_level=AssemblyLevel.SUBASSEMBLY,
            work_hours=60.0,
            dependencies=["WP-0001", "WP-0002"],
        )

        assert len(pkg.dependencies) == 2
        assert "WP-0001" in pkg.dependencies

    def test_package_to_dict(self):
        """Test package serialization."""
        pkg = WorkPackage(
            package_id="WP-0001",
            name="Test Package",
            package_type=WorkPackageType.FABRICATION,
            assembly_level=AssemblyLevel.COMPONENT,
            work_hours=40.0,
        )

        data = pkg.to_dict()
        assert data["package_id"] == "WP-0001"
        assert data["package_type"] == "fabrication"
        assert data["assembly_level"] == "component"
