"""
Integration tests for weight-stability bridge.

Tests the critical integration between Module 07 (Weight) and Module 06 (Stability).
Verifies that stability.kg_m is correctly written and used.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from magnet.weight import (
    WeightEstimationValidator,
    WeightStabilityValidator,
)
from magnet.stability import (
    IntactGMValidator,
    GZCurveValidator,
    IMO_INTACT,
)
from magnet.validators.taxonomy import ValidatorState


class MockStateManager:
    """Mock StateManager for integration testing."""

    def __init__(self, initial_values=None):
        self._values = initial_values or {}
        self._modified = {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        self._values[key] = value
        self._modified[key] = datetime.utcnow()

    def get_field_metadata(self, key):
        if key in self._modified:
            mock = Mock()
            mock.last_modified = self._modified[key]
            return mock
        return None


class TestKGSourcingPriority:
    """Test KG sourcing priority (v1.2 stability feature)."""

    def test_stability_kg_used_when_present(self):
        """Test that stability.kg_m is used when present."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
            "hull.displacement_mt": 500.0,
            "stability.kg_m": 2.5,  # Direct KG value
            "weight.lightship_vcg_m": 3.0,  # Should NOT be used
        })

        IntactGMValidator().validate(state_manager, {})

        # GM should use stability.kg_m = 2.5, not weight VCG
        # GM = KB + BM - KG = 1.5 + 3.0 - 2.5 = 2.0
        assert abs(state_manager._values["stability.gm_transverse_m"] - 2.0) < 0.01

    def test_weight_vcg_fallback_when_no_stability_kg(self):
        """Test that weight.lightship_vcg_m is used as fallback."""
        state_manager = MockStateManager({
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
            "hull.displacement_mt": 500.0,
            # No stability.kg_m
            "weight.lightship_vcg_m": 2.8,  # Should be used as fallback
        })

        IntactGMValidator().validate(state_manager, {})

        # GM should use weight.lightship_vcg_m = 2.8
        # GM = KB + BM - KG = 1.5 + 3.0 - 2.8 = 1.7
        assert abs(state_manager._values["stability.gm_transverse_m"] - 1.7) < 0.01


class TestFullWeightToStabilityChain:
    """Test full chain from weight estimation through stability calculation."""

    def test_complete_chain_execution(self):
        """Test complete weight → stability calculation chain."""
        state_manager = MockStateManager({
            # Hull parameters
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            # Hydrostatics outputs (simulated)
            "hull.displacement_mt": 700.0,
            "hull.kb_m": 1.35,
            "hull.bm_m": 3.5,
            "hull.wetted_surface_m2": 520.0,
            # Propulsion
            "propulsion.installed_power_kw": 2000.0,
            "propulsion.number_of_engines": 2,
            "mission.crew_size": 6,
        })

        # Step 1: Weight estimation
        weight_result = WeightEstimationValidator().validate(state_manager, {})
        assert weight_result.passed
        assert state_manager._values["weight.lightship_vcg_m"] > 0

        # Step 2: Weight-stability bridge
        bridge_result = WeightStabilityValidator().validate(state_manager, {})
        assert bridge_result.passed
        assert "stability.kg_m" in state_manager._values

        # Step 3: Intact GM calculation
        gm_result = IntactGMValidator().validate(state_manager, {})
        assert gm_result.passed
        assert state_manager._values["stability.gm_transverse_m"] > 0

        # Step 4: GZ curve
        gz_result = GZCurveValidator().validate(state_manager, {})
        assert gz_result.passed

        # Verify KG chain
        assert (state_manager._values["stability.kg_m"] ==
                state_manager._values["weight.lightship_vcg_m"])

    def test_chain_produces_valid_stability(self):
        """Test that chain produces valid stability for well-designed vessel."""
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.kb_m": 1.35,
            "hull.bm_m": 3.5,  # Good BM for stability
            "hull.wetted_surface_m2": 520.0,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        })

        # Run full chain
        WeightEstimationValidator().validate(state_manager, {})
        WeightStabilityValidator().validate(state_manager, {})
        IntactGMValidator().validate(state_manager, {})
        GZCurveValidator().validate(state_manager, {})

        # Check stability is adequate
        gm = state_manager._values["stability.gm_transverse_m"]
        assert gm >= IMO_INTACT.gm_min_m  # 0.15m minimum

    def test_chain_detects_unstable_vessel(self):
        """Test that chain detects vessel with poor stability."""
        # Design a top-heavy vessel
        state_manager = MockStateManager({
            "hull.lwl": 50.0,
            "hull.beam": 8.0,  # Narrow beam = low BM
            "hull.depth": 6.0,  # Tall vessel
            "hull.draft": 2.0,
            "hull.cb": 0.50,
            "hull.displacement_mt": 400.0,
            "hull.kb_m": 1.0,
            "hull.bm_m": 2.0,  # Low BM
            "propulsion.installed_power_kw": 1500.0,
            "mission.crew_size": 6,
            "mission.passengers": 50,  # Passengers add weight high
        })

        WeightEstimationValidator().validate(state_manager, {})
        bridge_result = WeightStabilityValidator().validate(state_manager, {})

        # Weight-stability bridge should detect potential issue
        estimated_gm = state_manager._values.get("weight.estimated_gm_m", 0)

        # Either low/negative GM warning in bridge, or low GM in actual calculation
        if estimated_gm < IMO_INTACT.gm_min_m:
            assert bridge_result.state in [ValidatorState.WARNING, ValidatorState.FAILED]


class TestParameterPropagation:
    """Test parameter propagation through the chain."""

    def test_vcg_change_affects_gm(self):
        """Test that VCG from weight affects GM."""
        base_state = {
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.kb_m": 1.35,
            "hull.bm_m": 3.5,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        }

        # Run chain with default design
        state1 = MockStateManager(base_state.copy())
        WeightEstimationValidator().validate(state1, {})
        WeightStabilityValidator().validate(state1, {})
        IntactGMValidator().validate(state1, {})
        gm1 = state1._values["stability.gm_transverse_m"]

        # Increase depth (increases VCG typically)
        modified_state = base_state.copy()
        modified_state["hull.depth"] = 5.0  # Taller vessel

        state2 = MockStateManager(modified_state)
        WeightEstimationValidator().validate(state2, {})
        WeightStabilityValidator().validate(state2, {})
        IntactGMValidator().validate(state2, {})
        gm2 = state2._values["stability.gm_transverse_m"]

        # Taller vessel typically has lower GM (higher VCG)
        assert gm2 < gm1

    def test_beam_change_affects_stability(self):
        """Test that beam change affects both BM and weight."""
        base_state = {
            "hull.lwl": 50.0,
            "hull.beam": 10.0,
            "hull.depth": 4.0,
            "hull.draft": 2.5,
            "hull.cb": 0.55,
            "hull.displacement_mt": 700.0,
            "hull.kb_m": 1.35,
            "hull.bm_m": 3.5,
            "propulsion.installed_power_kw": 2000.0,
            "mission.crew_size": 6,
        }

        # Run with normal beam
        state1 = MockStateManager(base_state.copy())
        WeightEstimationValidator().validate(state1, {})
        WeightStabilityValidator().validate(state1, {})
        weight1 = state1._values["weight.lightship_mt"]

        # Increase beam (wider vessel)
        modified_state = base_state.copy()
        modified_state["hull.beam"] = 12.0
        modified_state["hull.bm_m"] = 5.0  # BM increases with beam

        state2 = MockStateManager(modified_state)
        WeightEstimationValidator().validate(state2, {})
        WeightStabilityValidator().validate(state2, {})
        weight2 = state2._values["weight.lightship_mt"]

        # Wider vessel should be heavier
        assert weight2 > weight1

        # Wider vessel should have higher estimated GM
        gm1 = state1._values.get("weight.estimated_gm_m", 0)
        gm2 = state2._values.get("weight.estimated_gm_m", 0)
        assert gm2 > gm1  # Higher BM improves GM


class TestStabilityReadyFlag:
    """Test weight.stability_ready flag behavior."""

    def test_stability_ready_true_for_good_vessel(self):
        """Test stability_ready is True for vessel with adequate GM."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 2.0,  # Low VCG
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
            # KM = 4.5, KG = 2.0, GM = 2.5 (good)
        })

        WeightStabilityValidator().validate(state_manager, {})

        assert state_manager._values["weight.stability_ready"] == True

    def test_stability_ready_false_for_negative_gm(self):
        """Test stability_ready is False for negative GM."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 5.0,  # Very high VCG
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 2.0,
            # KM = 3.5, KG = 5.0, GM = -1.5 (unstable)
        })

        WeightStabilityValidator().validate(state_manager, {})

        assert state_manager._values["weight.stability_ready"] == False

    def test_stability_ready_true_for_marginal_gm(self):
        """Test stability_ready is True but warns for marginal GM."""
        state_manager = MockStateManager({
            "weight.lightship_vcg_m": 4.3,  # High VCG
            "weight.lightship_mt": 100.0,
            "hull.kb_m": 1.5,
            "hull.bm_m": 3.0,
            # KM = 4.5, KG = 4.3, GM = 0.2 (marginal but positive)
        })

        result = WeightStabilityValidator().validate(state_manager, {})

        # Should still be ready but with warning
        assert state_manager._values["weight.stability_ready"] == True
        # May have warning about low GM
        assert result.state in [ValidatorState.PASSED, ValidatorState.WARNING]
