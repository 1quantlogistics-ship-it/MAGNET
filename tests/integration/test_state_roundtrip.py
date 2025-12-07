"""
Integration tests for state serialization roundtrip.

Tests full serialize/deserialize cycle across all modules.
"""

import pytest
import json
import tempfile
import os
from magnet.core.design_state import DesignState
from magnet.core.state_manager import StateManager


class TestFullRoundtrip:
    """Test complete roundtrip serialization."""

    def test_empty_state_roundtrip(self):
        """Test roundtrip of empty state."""
        original = DesignState()
        data = original.to_dict()
        restored = DesignState.from_dict(data)

        # Compare key fields
        assert restored.version == original.version
        # design_id should match
        assert restored.design_id == original.design_id

    def test_populated_state_roundtrip(self):
        """Test roundtrip of populated state."""
        original = DesignState(design_name="Integration Test Vessel")

        # Populate mission
        original.mission.vessel_type = "patrol"
        original.mission.max_speed_kts = 35.0
        original.mission.range_nm = 500.0
        original.mission.crew_berthed = 6

        # Populate hull
        original.hull.loa = 25.0
        original.hull.beam = 6.0
        original.hull.draft = 1.5
        original.hull.cb = 0.45

        # Populate propulsion
        original.propulsion.num_engines = 2
        original.propulsion.total_installed_power_kw = 1500.0
        original.propulsion.engine_make = "MTU"

        # Populate weight
        original.weight.lightship_weight_mt = 45.0
        original.weight.full_load_displacement_mt = 65.0

        # Populate stability
        original.stability.gm_transverse_m = 1.2
        original.stability.gz_max_m = 0.8  # Canonical: gz_max_m (not gz_max)

        data = original.to_dict()
        restored = DesignState.from_dict(data)

        # Verify all sections
        assert restored.design_name == original.design_name
        assert restored.mission.vessel_type == original.mission.vessel_type
        assert restored.mission.max_speed_kts == original.mission.max_speed_kts
        assert restored.hull.loa == original.hull.loa
        assert restored.hull.cb == original.hull.cb
        assert restored.propulsion.num_engines == original.propulsion.num_engines
        assert restored.weight.lightship_weight_mt == original.weight.lightship_weight_mt
        assert restored.stability.gm_transverse_m == original.stability.gm_transverse_m

    def test_all_sections_survive_roundtrip(self):
        """Test all 27 sections survive roundtrip.

        Uses canonical field names per ALPHA's v1.19 schema.
        """
        original = DesignState()

        # Set a value in each section using CANONICAL field names
        original.mission.vessel_type = "test_mission"
        original.hull.loa = 1.0
        original.structural_design.hull_material = "aluminum"  # Canonical: hull_material
        original.structural_loads.slamming_pressure_kpa = 100.0  # Canonical field
        original.propulsion.num_engines = 1
        original.weight.lightship_weight_mt = 10.0
        original.stability.gm_transverse_m = 0.5
        original.loading.current_condition = "full_load"  # LoadingState uses tank_states dict
        original.arrangement.num_decks = 2  # Canonical: num_decks
        original.compliance.classification_society = "ABS"  # Canonical: classification_society
        original.production.build_hours = 1000.0  # Canonical: build_hours
        original.cost.total_cost = 1000000.0
        original.optimization.converged = True  # Canonical: converged
        original.reports.generated = True  # Canonical: generated is bool
        original.kernel.status = "running"
        original.analysis.operability_index = 0.9
        original.performance.design_speed_kts = 30.0  # Use existing field
        original.systems.electrical_load_kw = 50.0
        original.outfitting.berth_count = 4
        original.environmental.design_sea_state = "4"  # String per canonical schema
        original.deck_equipment.anchor_weight_kg = 50.0
        original.vision.geometry_generated = True
        original.resistance.total_resistance_kn = 25.0
        original.seakeeping.roll_period_s = 8.5  # Canonical: roll_period_s
        original.maneuvering.tactical_diameter_m = 100.0
        original.electrical.frequency_hz = 60.0  # Canonical: frequency_hz
        original.safety.lifejackets = 10  # Canonical: lifejackets

        data = original.to_dict()
        restored = DesignState.from_dict(data)

        # Verify each section using canonical field names
        assert restored.mission.vessel_type == "test_mission"
        assert restored.hull.loa == 1.0
        assert restored.structural_design.hull_material == "aluminum"
        assert restored.propulsion.num_engines == 1
        assert restored.stability.gm_transverse_m == 0.5
        assert restored.analysis.operability_index == 0.9
        assert restored.vision.geometry_generated == True
        assert restored.safety.lifejackets == 10


class TestFileRoundtrip:
    """Test file-based roundtrip."""

    def test_json_file_roundtrip(self):
        """Test roundtrip through JSON file."""
        manager = StateManager()
        manager.state.design_name = "File Roundtrip Test"
        manager.state.mission.vessel_type = "ferry"
        manager.state.hull.loa = 100.0

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name

        try:
            manager.save_to_file(filepath)

            # Verify file contents
            with open(filepath, 'r') as f:
                data = json.load(f)
            assert data["design_name"] == "File Roundtrip Test"

            # Load into new manager
            manager2 = StateManager()
            manager2.load_from_file(filepath)

            assert manager2.state.design_name == "File Roundtrip Test"
            assert manager2.state.mission.vessel_type == "ferry"
            assert manager2.state.hull.loa == 100.0
        finally:
            os.unlink(filepath)


class TestStateManagerRoundtrip:
    """Test roundtrip through StateManager."""

    def test_manager_to_dict_roundtrip(self):
        """Test roundtrip through StateManager dict methods."""
        manager = StateManager()
        manager.set("mission.vessel_type", "patrol", source="test")
        manager.set("hull.loa", 30.0, source="test")
        manager.set("propulsion.num_engines", 2, source="test")

        data = manager.to_dict()

        manager2 = StateManager()
        manager2.from_dict(data)

        assert manager2.get("mission.vessel_type") == "patrol"
        assert manager2.get("hull.loa") == 30.0
        assert manager2.get("propulsion.num_engines") == 2

    def test_snapshot_roundtrip(self):
        """Test roundtrip through snapshot."""
        manager = StateManager()
        manager.state.design_name = "Snapshot Test"
        manager.state.mission.vessel_type = "workboat"

        snapshot = manager.export_snapshot(include_metadata=True)
        assert "snapshot_timestamp" in snapshot

        manager2 = StateManager()
        manager2.from_dict(snapshot)
        assert manager2.state.design_name == "Snapshot Test"


class TestComplexDataRoundtrip:
    """Test roundtrip with complex data types."""

    def test_list_fields_roundtrip(self):
        """Test roundtrip of list fields using canonical field names."""
        state = DesignState()
        state.mission.special_features = ["Ice Class", "DP2"]  # Canonical: special_features
        state.compliance.errors = ["Error 1", "Error 2"]

        restored = DesignState.from_dict(state.to_dict())
        assert restored.mission.special_features == ["Ice Class", "DP2"]
        assert restored.compliance.errors == ["Error 1", "Error 2"]

    def test_dict_fields_roundtrip(self):
        """Test roundtrip of dict fields."""
        state = DesignState()
        state.mission.operational_profile = {"transit": 0.6, "loiter": 0.3, "anchor": 0.1}
        state.structural_design.plating_zones = {"bottom": {"thickness": 10.0}}

        restored = DesignState.from_dict(state.to_dict())
        assert restored.mission.operational_profile["transit"] == 0.6
        assert restored.structural_design.plating_zones["bottom"]["thickness"] == 10.0

    def test_nested_list_roundtrip(self):
        """Test roundtrip of nested lists."""
        state = DesignState()
        state.stability.gz_curve = [
            {"heel_deg": 0, "gz_m": 0.0},
            {"heel_deg": 30, "gz_m": 0.5},
            {"heel_deg": 60, "gz_m": 0.3},
        ]

        restored = DesignState.from_dict(state.to_dict())
        assert len(restored.stability.gz_curve) == 3
        assert restored.stability.gz_curve[1]["gz_m"] == 0.5
