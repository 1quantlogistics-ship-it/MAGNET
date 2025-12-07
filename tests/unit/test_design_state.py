"""
Unit tests for DesignState.

Tests the unified design state container with all 27 sections.
"""

import pytest
from magnet.core.design_state import DesignState

SECTION_NAMES = DesignState.SECTION_NAMES
from magnet.core.dataclasses import MissionConfig, HullState, PropulsionState


class TestDesignStateCreation:
    """Test DesignState creation."""

    def test_create_empty(self):
        """Test creating empty DesignState."""
        state = DesignState()
        assert state.design_id is not None
        assert state.version == "1.19.0"

    def test_create_with_name(self):
        """Test creating DesignState with name."""
        state = DesignState(design_name="Test Vessel")
        assert state.design_name == "Test Vessel"

    def test_auto_generates_id(self):
        """Test that design_id is auto-generated."""
        state1 = DesignState()
        state2 = DesignState()
        assert state1.design_id != state2.design_id

    def test_has_all_27_sections(self):
        """Test that all 27 sections are present."""
        state = DesignState()
        for section_name in SECTION_NAMES:
            assert hasattr(state, section_name), f"Missing section: {section_name}"


class TestDesignStateSections:
    """Test DesignState section access."""

    def test_mission_section(self):
        """Test mission section."""
        state = DesignState()
        assert isinstance(state.mission, MissionConfig)
        state.mission.vessel_type = "patrol"
        assert state.mission.vessel_type == "patrol"

    def test_hull_section(self):
        """Test hull section."""
        state = DesignState()
        assert isinstance(state.hull, HullState)
        state.hull.loa = 25.0
        assert state.hull.loa == 25.0

    def test_propulsion_section(self):
        """Test propulsion section."""
        state = DesignState()
        assert isinstance(state.propulsion, PropulsionState)
        state.propulsion.num_engines = 2
        assert state.propulsion.num_engines == 2

    def test_get_section(self):
        """Test get_section method."""
        state = DesignState()
        mission = state.get_section("mission")
        assert mission is state.mission

    def test_set_section(self):
        """Test set_section method."""
        state = DesignState()
        new_mission = MissionConfig(vessel_type="ferry")
        state.set_section("mission", new_mission)
        assert state.mission.vessel_type == "ferry"


class TestDesignStateSerialization:
    """Test DesignState serialization."""

    def test_to_dict(self):
        """Test serialization to dict."""
        state = DesignState(design_name="Test")
        state.mission.vessel_type = "patrol"
        state.hull.loa = 25.0

        data = state.to_dict()
        assert isinstance(data, dict)
        assert data["design_name"] == "Test"
        assert data["mission"]["vessel_type"] == "patrol"
        assert data["hull"]["loa"] == 25.0

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "design_id": "test-123",
            "design_name": "Test Vessel",
            "mission": {"vessel_type": "ferry", "max_speed_kts": 30.0},
            "hull": {"loa": 50.0, "beam": 10.0},
        }

        state = DesignState.from_dict(data)
        assert state.design_id == "test-123"
        assert state.design_name == "Test Vessel"
        assert state.mission.vessel_type == "ferry"
        assert state.hull.loa == 50.0

    def test_roundtrip(self):
        """Test roundtrip serialization."""
        original = DesignState(design_name="Roundtrip Test")
        original.mission.vessel_type = "workboat"
        original.mission.max_speed_kts = 25.0
        original.hull.loa = 20.0
        original.hull.beam = 5.0
        original.propulsion.num_engines = 2

        data = original.to_dict()
        restored = DesignState.from_dict(data)

        assert restored.design_name == original.design_name
        assert restored.mission.vessel_type == original.mission.vessel_type
        assert restored.hull.loa == original.hull.loa
        assert restored.propulsion.num_engines == original.propulsion.num_engines


class TestDesignStateValidation:
    """Test DesignState validation."""

    def test_validate_empty(self):
        """Test validation of empty state."""
        state = DesignState()
        is_valid, errors = state.validate()
        # Empty state should be valid (design_id is auto-generated)
        assert is_valid or "design_id" not in errors[0]

    def test_validate_invalid_dimensions(self):
        """Test validation catches invalid dimensions."""
        state = DesignState()
        state.hull.loa = 20.0
        state.hull.lwl = 25.0  # lwl > loa is invalid

        is_valid, errors = state.validate()
        assert not is_valid
        assert any("lwl" in err.lower() for err in errors)

    def test_validate_negative_gm(self):
        """Test validation catches negative GM."""
        state = DesignState()
        state.stability.gm_transverse_m = -0.5

        is_valid, errors = state.validate()
        assert not is_valid
        assert any("gm" in err.lower() for err in errors)


class TestDesignStatePatch:
    """Test DesignState patch method."""

    def test_patch_single_value(self):
        """Test patching a single value."""
        state = DesignState()
        modified = state.patch({"mission.vessel_type": "patrol"}, source="test")
        assert "mission.vessel_type" in modified
        assert state.mission.vessel_type == "patrol"

    def test_patch_multiple_values(self):
        """Test patching multiple values."""
        state = DesignState()
        updates = {
            "mission.vessel_type": "ferry",
            "mission.max_speed_kts": 30.0,
            "hull.loa": 50.0,
        }
        modified = state.patch(updates, source="test")
        assert len(modified) == 3
        assert state.mission.vessel_type == "ferry"
        assert state.hull.loa == 50.0


class TestDesignStateDiff:
    """Test DesignState diff method."""

    def test_diff_identical(self):
        """Test diff of identical states."""
        state1 = DesignState()
        state2 = DesignState.from_dict(state1.to_dict())
        state2.design_id = state1.design_id  # Match IDs

        differences = state1.diff(state2)
        # Filter out timestamp differences
        non_time_diffs = {k: v for k, v in differences.items()
                         if "timestamp" not in k.lower() and "_at" not in k}
        assert len(non_time_diffs) == 0

    def test_diff_different(self):
        """Test diff of different states."""
        state1 = DesignState()
        state1.mission.vessel_type = "patrol"

        state2 = DesignState.from_dict(state1.to_dict())
        state2.mission.vessel_type = "ferry"

        differences = state1.diff(state2)
        assert "mission.vessel_type" in differences
        assert differences["mission.vessel_type"] == ("patrol", "ferry")


class TestDesignStateCopy:
    """Test DesignState copy method."""

    def test_copy(self):
        """Test deep copy."""
        original = DesignState(design_name="Original")
        original.mission.vessel_type = "patrol"

        copied = original.copy()

        # Should be equal
        assert copied.design_name == original.design_name
        assert copied.mission.vessel_type == original.mission.vessel_type

        # But independent
        copied.mission.vessel_type = "ferry"
        assert original.mission.vessel_type == "patrol"
        assert copied.mission.vessel_type == "ferry"


class TestDesignStateSummary:
    """Test DesignState summary method."""

    def test_summary(self):
        """Test summary output."""
        state = DesignState(design_name="Test Vessel")
        state.mission.vessel_type = "patrol"
        state.hull.loa = 25.0

        summary = state.summary()
        assert isinstance(summary, str)
        assert "Test Vessel" in summary
        assert "patrol" in summary or "Patrol" in summary
        assert "25" in summary
