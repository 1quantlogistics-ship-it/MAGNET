"""
Integration tests for weight estimation pipeline.

Tests full flow of weight estimation validators with physics integration.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from magnet.weight import (
    WeightEstimationValidator,
    WeightStabilityValidator,
    WeightAggregator,
    SWBSGroup,
)
from magnet.weight.estimators import (
    HullStructureEstimator,
    PropulsionPlantEstimator,
    ElectricPlantEstimator,
    CommandSurveillanceEstimator,
    AuxiliarySystemsEstimator,
    OutfitFurnishingsEstimator,
)
from magnet.weight.utils import determinize_dict
from magnet.validators.taxonomy import ValidatorState


class MockStateManager:
    """Mock StateManager for integration testing."""

    def __init__(self, initial_values=None):
        self._values = initial_values or {}
        self._modified = {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value
        self._modified[key] = datetime.utcnow()

    def get_field_metadata(self, key):
        if key in self._modified:
            mock = Mock()
            mock.last_modified = self._modified[key]
            return mock
        return None


class TestWeightPipeline:
    """Test weight estimation pipeline."""

    def test_full_pipeline_execution(self):
        """Test executing weight estimation pipeline."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.hull_type": "monohull",
            "hull.material": "aluminum_5083",
            "hull.displacement_mt": 700.0,
            "hull.wetted_surface_m2": 500.0,
            "propulsion.installed_power_kw": 2000.0,
            "propulsion.number_of_engines": 2,
            "propulsion.engine_type": "high_speed_diesel",
            "mission.crew_size": 6,
            "mission.passengers": 0,
            "mission.vessel_type": "commercial",
        })

        # Execute weight estimation
        weight_validator = WeightEstimationValidator()
        weight_result = weight_validator.validate(state_manager, {})

        assert weight_result.passed
        assert "weight.lightship_mt" in state_manager._values
        assert "weight.lightship_vcg_m" in state_manager._values
        assert state_manager._values["weight.lightship_mt"] > 0

    def test_all_group_weights_calculated(self):
        """Test all SWBS group weights are calculated."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "propulsion.installed_power_kw": 2000.0,
            "propulsion.number_of_engines": 2,
            "mission.crew_size": 6,
        })

        WeightEstimationValidator().validate(state_manager, {})

        # Check all groups have weights
        assert state_manager._values.get("weight.group_100_mt", 0) > 0  # Hull
        assert state_manager._values.get("weight.group_200_mt", 0) > 0  # Propulsion
        assert state_manager._values.get("weight.group_300_mt", 0) > 0  # Electrical
        assert state_manager._values.get("weight.group_400_mt", 0) > 0  # Command
        assert state_manager._values.get("weight.group_500_mt", 0) > 0  # Auxiliary
        assert state_manager._values.get("weight.group_600_mt", 0) > 0  # Outfit

    def test_lightship_is_sum_of_groups_plus_margin(self):
        """Test lightship equals sum of groups plus margin."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        })

        WeightEstimationValidator().validate(state_manager, {})

        # Sum all group weights
        group_sum = 0
        for group_num in [100, 200, 300, 400, 500, 600]:
            group_sum += state_manager._values.get(f"weight.group_{group_num}_mt", 0)

        # Add margin
        margin = state_manager._values.get("weight.margin_mt", 0)
        expected_lightship = group_sum + margin

        actual_lightship = state_manager._values["weight.lightship_mt"]

        # Allow small tolerance for rounding
        assert abs(actual_lightship - expected_lightship) < 0.01

    def test_vcg_is_physically_reasonable(self):
        """Test VCG is within physical bounds."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        })

        WeightEstimationValidator().validate(state_manager, {})

        vcg = state_manager._values["weight.lightship_vcg_m"]
        depth = 4.0

        # VCG should be above baseline (> 0) and below depth
        assert vcg > 0
        assert vcg < depth

        # Typically VCG is 40-60% of depth for vessels
        assert vcg > depth * 0.3
        assert vcg < depth * 0.8

    def test_parameter_change_affects_results(self):
        """Test that changing parameters changes results."""
        base_state = {
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        }

        # First run
        state1 = MockStateManager(base_state.copy())
        WeightEstimationValidator().validate(state1, {})
        lightship1 = state1._values["weight.lightship_mt"]

        # Change beam (affects hull weight)
        modified_state = base_state.copy()
        modified_state["hull.beam"] = 12.0  # Wider

        state2 = MockStateManager(modified_state)
        WeightEstimationValidator().validate(state2, {})
        lightship2 = state2._values["weight.lightship_mt"]

        # Wider beam should increase weight
        assert lightship2 > lightship1


class TestWeightStabilityBridge:
    """Test weight-stability integration."""

    def test_kg_written_to_stability(self):
        """Test KG is correctly bridged to stability."""
        # First run weight estimation
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        })

        # Weight estimation
        WeightEstimationValidator().validate(state_manager, {})
        vcg = state_manager._values["weight.lightship_vcg_m"]

        # Weight-stability bridge
        WeightStabilityValidator().validate(state_manager, {})

        # Verify KG was written to stability namespace
        assert "stability.kg_m" in state_manager._values
        assert state_manager._values["stability.kg_m"] == vcg

    def test_estimated_gm_calculated(self):
        """Test estimated GM is calculated from weight VCG."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.5,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        })

        WeightEstimationValidator().validate(state_manager, {})
        WeightStabilityValidator().validate(state_manager, {})

        # Check GM was calculated
        assert "weight.estimated_gm_m" in state_manager._values
        gm = state_manager._values["weight.estimated_gm_m"]
        assert gm > 0  # Should be positive for stable vessel

    def test_full_chain_physics_weight_stability(self):
        """Test full chain from physics through weight to stability."""
        # Simulate physics outputs
        state_manager = MockStateManager({
            # Hull inputs
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            # Physics outputs (would come from HydrostaticsValidator)
            "hull.displacement_mt": 700.0,
            "hull.displacement_m3": 683.0,
            "hull.kb_m": 1.35,
            "hull.bm_m": 3.5,
            "hull.wetted_surface_m2": 520.0,
            # Propulsion inputs
            "propulsion.installed_power_kw": 2000.0,
            "propulsion.number_of_engines": 2,
            "mission.crew_size": 6,
        })

        # Weight estimation
        weight_result = WeightEstimationValidator().validate(state_manager, {})
        assert weight_result.passed

        # Weight-stability bridge
        stability_result = WeightStabilityValidator().validate(state_manager, {})
        assert stability_result.passed

        # Verify the chain
        assert state_manager._values["weight.lightship_mt"] > 0
        assert state_manager._values["weight.lightship_vcg_m"] > 0
        assert state_manager._values["stability.kg_m"] > 0
        assert state_manager._values["weight.estimated_gm_m"] > 0

        # KG should equal lightship VCG
        assert (state_manager._values["stability.kg_m"] ==
                state_manager._values["weight.lightship_vcg_m"])


class TestDeterminizedSummary:
    """Test determinized summary data (v1.1 FIX #6)."""

    def test_summary_data_is_deterministic(self):
        """Test summary data is deterministic across runs."""
        state = {
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        }

        # Run twice
        state1 = MockStateManager(state.copy())
        WeightEstimationValidator().validate(state1, {})
        summary1 = state1._values["weight.summary_data"]

        state2 = MockStateManager(state.copy())
        WeightEstimationValidator().validate(state2, {})
        summary2 = state2._values["weight.summary_data"]

        # Summary data should be identical
        import json
        assert json.dumps(summary1, sort_keys=True) == json.dumps(summary2, sort_keys=True)

    def test_determinize_dict_function(self):
        """Test determinize_dict utility function."""
        data = {
            "z_key": 1.23456789,
            "a_key": {"nested": 2.34567890},
            "b_key": [1.1, 2.2, 3.3],
        }

        result = determinize_dict(data, precision=4)

        # Keys should be sorted
        keys = list(result.keys())
        assert keys == sorted(keys)

        # Floats should be rounded
        assert result["z_key"] == 1.2346
        assert result["a_key"]["nested"] == 2.3457
        assert result["b_key"] == [1.1, 2.2, 3.3]


class TestEdgeCases:
    """Test edge cases in weight pipeline."""

    def test_minimal_vessel(self):
        """Test very small vessel."""
        state_manager = MockStateManager({
            "hull.lwl": 10.0,
            "hull.beam": 3.0,
            "hull.depth": 1.5,
            "hull.draft": 0.8,
            "hull.cb": 0.45,
            "hull.displacement_mt": 15.0,
            "propulsion.installed_power_kw": 200.0,
            "mission.crew_size": 2,
        })

        result = WeightEstimationValidator().validate(state_manager, {})
        assert result.passed
        assert state_manager._values["weight.lightship_mt"] > 0
        assert state_manager._values["weight.lightship_mt"] < 50  # Should be small

    def test_large_vessel(self):
        """Test large vessel."""
        state_manager = MockStateManager({
            "hull.lwl": 100.0,
            "hull.beam": 18.0,
            "hull.depth": 8.0,
            "hull.draft": 5.0,
            "hull.cb": 0.65,
            "hull.displacement_mt": 6000.0,
            "propulsion.installed_power_kw": 8000.0,
            "mission.crew_size": 20,
            "mission.passengers": 100,
        })

        result = WeightEstimationValidator().validate(state_manager, {})
        assert result.passed
        assert state_manager._values["weight.lightship_mt"] > 1000  # Should be substantial

    def test_high_power_vessel(self):
        """Test high-powered vessel (e.g., patrol boat)."""
        state_manager = MockStateManager({
            "hull.lwl": 40.0,
            "hull.beam": 8.0,
            "hull.depth": 3.5,
            "hull.draft": 1.8,
            "hull.cb": 0.45,
            "hull.displacement_mt": 250.0,
            "propulsion.installed_power_kw": 6000.0,  # High power for size
            "propulsion.engine_type": "high_speed_diesel",
            "mission.crew_size": 8,
            "mission.vessel_type": "patrol",
        })

        result = WeightEstimationValidator().validate(state_manager, {})
        assert result.passed

        # Propulsion should be significant portion of weight
        group_200 = state_manager._values.get("weight.group_200_mt", 0)
        lightship = state_manager._values["weight.lightship_mt"]
        assert group_200 / lightship > 0.1  # At least 10% propulsion

    def test_passenger_vessel(self):
        """Test passenger vessel has significant outfit weight."""
        state_manager = MockStateManager({
            "hull.lwl": 60.0,
            "hull.beam": 12.0,
            "hull.depth": 5.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 1000.0,
            "propulsion.installed_power_kw": 3000.0,
            "mission.crew_size": 10,
            "mission.passengers": 150,  # Passenger vessel
            "mission.vessel_type": "ferry",
        })

        result = WeightEstimationValidator().validate(state_manager, {})
        assert result.passed

        # Outfit (G600) should be significant
        group_600 = state_manager._values.get("weight.group_600_mt", 0)
        assert group_600 > 5  # At least 5 tonnes for 150 passengers
