"""
tests/unit/test_analysis.py - Tests for Modules 34-35 (Noise/Vibration, Seakeeping).

BRAVO OWNS THIS FILE.

Tests for analysis modules implemented by BRAVO:
- Module 34: Noise & Vibration Analysis
- Module 35: Seakeeping Analysis
"""

import pytest
import math
from unittest.mock import MagicMock

from magnet.analysis import (
    # Noise & Vibration
    NoiseSource, SpaceNoiseLevel, IsolationMount, NoiseVibrationResults,
    IMO_NOISE_LIMITS, estimate_engine_swl, estimate_generator_swl,
    NoiseVibrationAnalyzer, NoiseVibrationValidator,
    # Seakeeping
    SEA_STATES, NORDFORSK_CRITERIA,
    MotionResponse, OperabilityResult, SeakeepingResults,
    SeakeepingPredictor, SeakeepingValidator,
)


# =============================================================================
# MODULE 34: NOISE & VIBRATION TESTS
# =============================================================================

class TestNoiseSource:
    """Test NoiseSource dataclass."""

    def test_noise_source_creation(self):
        """Test creating a noise source."""
        source = NoiseSource(
            source_id="ME-1",
            source_type="main_engine",
            sound_power_level_dba=115.0,
        )
        assert source.source_id == "ME-1"
        assert source.source_type == "main_engine"
        assert source.sound_power_level_dba == 115.0

    def test_noise_source_to_dict(self):
        """Test NoiseSource serialization."""
        source = NoiseSource(
            source_id="GEN-1",
            source_type="generator",
            sound_power_level_dba=105.3,
        )
        data = source.to_dict()
        assert data["source_id"] == "GEN-1"
        assert data["sound_power_level_dba"] == 105.3


class TestEstimateSWL:
    """Test sound power level estimation functions."""

    def test_estimate_engine_swl(self):
        """Test engine SWL estimation."""
        # 93 + 10 * log10(1000) = 93 + 30 = 123 dBA
        swl = estimate_engine_swl(1000)
        assert swl == pytest.approx(123.0, rel=0.01)

    def test_estimate_engine_swl_zero_power(self):
        """Test engine SWL with zero power uses minimum of 1."""
        swl = estimate_engine_swl(0)
        assert swl == 93.0  # log10(1) = 0

    def test_estimate_generator_swl(self):
        """Test generator SWL estimation."""
        # 85 + 10 * log10(100) = 85 + 20 = 105 dBA
        swl = estimate_generator_swl(100)
        assert swl == pytest.approx(105.0, rel=0.01)


class TestIMONoiseLimits:
    """Test IMO noise limits dictionary."""

    def test_imo_limits_wheelhouse(self):
        """Test wheelhouse noise limit."""
        assert IMO_NOISE_LIMITS["wheelhouse"] == 65

    def test_imo_limits_crew_cabin(self):
        """Test crew cabin noise limit."""
        assert IMO_NOISE_LIMITS["crew_cabin"] == 60

    def test_imo_limits_engine_room(self):
        """Test engine room noise limit."""
        assert IMO_NOISE_LIMITS["engine_room"] == 110


class TestSpaceNoiseLevel:
    """Test SpaceNoiseLevel dataclass."""

    def test_space_noise_level_creation(self):
        """Test creating a space noise level."""
        level = SpaceNoiseLevel(
            space_id="WH-1",
            space_type="wheelhouse",
            predicted_level_dba=58.0,
            limit_dba=65.0,
        )
        assert level.space_id == "WH-1"
        assert level.predicted_level_dba == 58.0

    def test_space_noise_level_compliant(self):
        """Test compliance check."""
        level = SpaceNoiseLevel(
            predicted_level_dba=58.0,
            limit_dba=65.0,
        )
        assert level.compliant is True

    def test_space_noise_level_non_compliant(self):
        """Test non-compliance."""
        level = SpaceNoiseLevel(
            predicted_level_dba=68.0,
            limit_dba=65.0,
        )
        assert level.compliant is False

    def test_space_noise_level_margin(self):
        """Test margin calculation."""
        level = SpaceNoiseLevel(
            predicted_level_dba=58.0,
            limit_dba=65.0,
        )
        assert level.margin_dba == 7.0

    def test_space_noise_level_to_dict(self):
        """Test serialization."""
        level = SpaceNoiseLevel(
            space_id="CC-1",
            space_type="crew_cabin",
            predicted_level_dba=55.5,
            limit_dba=60.0,
        )
        data = level.to_dict()
        assert data["compliant"] is True
        assert data["margin_dba"] == 4.5


class TestIsolationMount:
    """Test IsolationMount dataclass."""

    def test_isolation_mount_creation(self):
        """Test creating an isolation mount."""
        mount = IsolationMount(
            mount_type="rubber",
            static_deflection_mm=3.0,
            natural_frequency_hz=5.0,
            isolation_efficiency=0.85,
        )
        assert mount.mount_type == "rubber"
        assert mount.isolation_efficiency == 0.85

    def test_isolation_mount_design(self):
        """Test design_for_isolation class method."""
        # Design for 200 Hz disturbing frequency
        mount = IsolationMount.design_for_isolation(200.0, 0.9)
        assert mount.natural_frequency_hz == pytest.approx(200.0 / 3, rel=0.01)
        assert mount.isolation_efficiency > 0.8

    def test_isolation_mount_to_dict(self):
        """Test serialization."""
        mount = IsolationMount(
            mount_type="spring",
            static_deflection_mm=8.5,
            natural_frequency_hz=3.0,
            isolation_efficiency=0.95,
        )
        data = mount.to_dict()
        assert data["mount_type"] == "spring"


class TestNoiseVibrationResults:
    """Test NoiseVibrationResults dataclass."""

    def test_noise_vibration_results_empty(self):
        """Test empty results."""
        results = NoiseVibrationResults()
        assert results.compliant is True  # No spaces = compliant
        assert results.max_level_dba == 0
        assert results.spaces_exceeding == 0

    def test_noise_vibration_results_compliant(self):
        """Test compliant results."""
        results = NoiseVibrationResults(
            space_levels=[
                SpaceNoiseLevel(space_id="WH", predicted_level_dba=60, limit_dba=65),
                SpaceNoiseLevel(space_id="CC", predicted_level_dba=55, limit_dba=60),
            ]
        )
        assert results.compliant is True
        assert results.max_level_dba == 60
        assert results.spaces_exceeding == 0

    def test_noise_vibration_results_non_compliant(self):
        """Test non-compliant results."""
        results = NoiseVibrationResults(
            space_levels=[
                SpaceNoiseLevel(space_id="WH", predicted_level_dba=70, limit_dba=65),
                SpaceNoiseLevel(space_id="CC", predicted_level_dba=55, limit_dba=60),
            ]
        )
        assert results.compliant is False
        assert results.spaces_exceeding == 1

    def test_noise_vibration_results_to_dict(self):
        """Test serialization."""
        results = NoiseVibrationResults(
            sources=[NoiseSource(source_id="ME-1", source_type="main_engine", sound_power_level_dba=115)],
            space_levels=[SpaceNoiseLevel(space_id="WH", predicted_level_dba=60, limit_dba=65)],
        )
        data = results.to_dict()
        assert "sources" in data
        assert "space_levels" in data
        assert data["compliant"] is True


class TestNoiseVibrationAnalyzer:
    """Test NoiseVibrationAnalyzer class."""

    def _create_mock_state(self, **kwargs):
        """Create a mock state manager."""
        state = MagicMock()
        defaults = {
            "propulsion.num_engines": 2,
            "propulsion.installed_power_kw": 2000,
            "propulsion.total_installed_power_kw": 2000,
            "electrical.num_generators": 2,
            "electrical.total_generation_kw": 100,
            "hvac.total_power_kw": 15,
            "outfitting.system": {
                "spaces": [
                    {"space_id": "WH", "space_type": "wheelhouse"},
                    {"space_id": "CC-1", "space_type": "crew_cabin"},
                ]
            },
        }
        defaults.update(kwargs)
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def test_analyzer_analyze(self):
        """Test full analysis."""
        state = self._create_mock_state()
        analyzer = NoiseVibrationAnalyzer(state)
        results = analyzer.analyze()

        assert len(results.sources) >= 2  # At least engines
        assert len(results.space_levels) == 2

    def test_analyzer_identify_sources(self):
        """Test source identification."""
        state = self._create_mock_state()
        analyzer = NoiseVibrationAnalyzer(state)
        sources = analyzer._identify_sources()

        engine_sources = [s for s in sources if s.source_type == "main_engine"]
        assert len(engine_sources) == 2

    def test_analyzer_get_spaces_fallback(self):
        """Test fallback spaces when outfitting not available."""
        state = self._create_mock_state(**{"outfitting.system": {}})
        analyzer = NoiseVibrationAnalyzer(state)
        spaces = analyzer._get_spaces()

        assert len(spaces) == 3  # Default fallback

    def test_analyzer_predict_levels(self):
        """Test level prediction."""
        state = self._create_mock_state()
        analyzer = NoiseVibrationAnalyzer(state)
        sources = analyzer._identify_sources()
        spaces = [{"space_id": "WH", "space_type": "wheelhouse"}]
        levels = analyzer._predict_levels(sources, spaces)

        assert len(levels) == 1
        assert levels[0].limit_dba == 65  # Wheelhouse limit


class TestNoiseVibrationValidator:
    """Test NoiseVibrationValidator class."""

    def _create_mock_state(self):
        """Create a mock state manager."""
        state = MagicMock()
        stored = {}

        def mock_get(key, default=None):
            defaults = {
                "propulsion.num_engines": 2,
                "propulsion.installed_power_kw": 2000,
                "electrical.num_generators": 2,
                "electrical.total_generation_kw": 100,
                "hvac.total_power_kw": 15,
                "outfitting.system": {},
            }
            return stored.get(key, defaults.get(key, default))

        def mock_set(key, value):
            stored[key] = value

        state.get = mock_get
        state.set = mock_set
        return state, stored

    def test_validator_validate(self):
        """Test validation."""
        state, stored = self._create_mock_state()
        validator = NoiseVibrationValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert "analysis.noise_vibration" in stored
        assert "analysis.noise_compliant" in stored

    def test_validator_metadata(self):
        """Test validator metadata."""
        validator = NoiseVibrationValidator()
        assert validator.validator_id == "analysis/noise_vibration"
        assert validator.phase == "analysis"
        assert "propulsion.num_engines" in validator.reads


# =============================================================================
# MODULE 35: SEAKEEPING TESTS
# =============================================================================

class TestSeaStates:
    """Test SEA_STATES dictionary."""

    def test_sea_states_calm(self):
        """Test calm sea state."""
        assert SEA_STATES[0]["name"] == "Calm (glassy)"
        assert SEA_STATES[0]["hs_m"] == 0.0

    def test_sea_states_moderate(self):
        """Test moderate sea state."""
        assert SEA_STATES[4]["name"] == "Moderate"
        assert SEA_STATES[4]["hs_m"] == 2.5

    def test_sea_states_rough(self):
        """Test rough sea state."""
        assert SEA_STATES[5]["name"] == "Rough"
        assert SEA_STATES[5]["hs_m"] == 4.0


class TestNordforskCriteria:
    """Test NORDFORSK_CRITERIA dictionary."""

    def test_nordforsk_vertical_accel(self):
        """Test vertical acceleration limit."""
        assert NORDFORSK_CRITERIA["bridge_vertical_accel_g"] == 0.20

    def test_nordforsk_roll(self):
        """Test roll amplitude limit."""
        assert NORDFORSK_CRITERIA["roll_amplitude_deg"] == 8.0

    def test_nordforsk_msi(self):
        """Test MSI limit."""
        assert NORDFORSK_CRITERIA["msi_percent"] == 20.0


class TestMotionResponse:
    """Test MotionResponse dataclass."""

    def test_motion_response_creation(self):
        """Test creating a motion response."""
        response = MotionResponse(
            location="bridge",
            heave_amplitude_m=0.5,
            pitch_amplitude_deg=3.0,
            roll_amplitude_deg=5.0,
            vertical_accel_g=0.15,
            lateral_accel_g=0.08,
            msi_percent=12.0,
        )
        assert response.location == "bridge"
        assert response.vertical_accel_g == 0.15

    def test_motion_response_to_dict(self):
        """Test serialization."""
        response = MotionResponse(
            location="bow",
            heave_amplitude_m=0.8,
            pitch_amplitude_deg=4.5,
        )
        data = response.to_dict()
        assert data["location"] == "bow"
        assert data["heave_amplitude_m"] == 0.8


class TestOperabilityResult:
    """Test OperabilityResult dataclass."""

    def test_operability_result_operable(self):
        """Test operable result."""
        result = OperabilityResult(
            sea_state=3,
            hs_m=1.25,
            criteria_met={
                "bridge_vertical_accel": True,
                "roll_amplitude": True,
                "pitch_amplitude": True,
            }
        )
        assert result.operable is True
        assert result.percent_met == 100.0

    def test_operability_result_not_operable(self):
        """Test non-operable result."""
        result = OperabilityResult(
            sea_state=5,
            hs_m=4.0,
            criteria_met={
                "bridge_vertical_accel": False,
                "roll_amplitude": True,
                "pitch_amplitude": False,
            }
        )
        assert result.operable is False
        assert result.percent_met == pytest.approx(33.33, rel=0.1)

    def test_operability_result_to_dict(self):
        """Test serialization."""
        result = OperabilityResult(
            sea_state=3,
            criteria_met={"roll": True, "pitch": True}
        )
        data = result.to_dict()
        assert data["operable"] is True


class TestSeakeepingResults:
    """Test SeakeepingResults dataclass."""

    def test_seakeeping_results_creation(self):
        """Test creating seakeeping results."""
        results = SeakeepingResults(
            roll_period_s=8.0,
            pitch_period_s=2.5,
            heave_period_s=3.0,
            max_operational_ss=4,
            operability_index=85.0,
        )
        assert results.roll_period_s == 8.0
        assert results.max_operational_ss == 4

    def test_seakeeping_results_to_dict(self):
        """Test serialization."""
        results = SeakeepingResults(
            roll_period_s=7.5,
            pitch_period_s=2.4,
            heave_period_s=2.8,
        )
        data = results.to_dict()
        assert "roll_period_s" in data
        assert "responses" in data


class TestSeakeepingPredictor:
    """Test SeakeepingPredictor class."""

    def _create_mock_state(self, **kwargs):
        """Create a mock state manager."""
        state = MagicMock()
        defaults = {
            "hull.lwl": 23.0,
            "hull.beam": 6.0,
            "hull.draft": 1.5,
            "stability.gm_transverse_m": 1.2,
            "mission.cruise_speed_kts": 25.0,
        }
        defaults.update(kwargs)
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def test_predictor_verify_inputs_valid(self):
        """Test input verification with valid inputs."""
        state = self._create_mock_state()
        predictor = SeakeepingPredictor(state)
        missing = predictor._verify_inputs()
        assert len(missing) == 0

    def test_predictor_verify_inputs_missing(self):
        """Test input verification with missing inputs."""
        state = self._create_mock_state(**{"hull.lwl": None})
        predictor = SeakeepingPredictor(state)
        missing = predictor._verify_inputs()
        assert len(missing) == 1
        assert "hull.lwl" in missing[0]

    def test_predictor_analyze(self):
        """Test full analysis."""
        state = self._create_mock_state()
        predictor = SeakeepingPredictor(state)
        results = predictor.analyze()

        assert results.roll_period_s > 0
        assert results.pitch_period_s > 0
        assert len(results.operability_by_ss) == 6
        assert len(results.responses) > 0

    def test_predictor_natural_periods(self):
        """Test natural period calculation."""
        state = self._create_mock_state()
        predictor = SeakeepingPredictor(state)
        periods = predictor._calculate_natural_periods()

        assert "roll_period_s" in periods
        assert "pitch_period_s" in periods
        assert "heave_period_s" in periods
        assert all(p > 0 for p in periods.values())

    def test_predictor_motions(self):
        """Test motion calculation."""
        state = self._create_mock_state()
        predictor = SeakeepingPredictor(state)
        periods = predictor._calculate_natural_periods()
        responses = predictor._calculate_motions(3, 1.25, periods)

        assert len(responses) == 4  # bridge, bow, midship, stern
        locations = [r.location for r in responses]
        assert "bridge" in locations
        assert "bow" in locations

    def test_predictor_operability_assessment(self):
        """Test operability assessment."""
        state = self._create_mock_state()
        predictor = SeakeepingPredictor(state)
        periods = predictor._calculate_natural_periods()
        responses = predictor._calculate_motions(0, 0.0, periods)
        operability = predictor._assess_operability(0, 0.0, responses)

        # Calm sea should be operable
        assert operability.operable is True


class TestSeakeepingValidator:
    """Test SeakeepingValidator class."""

    def _create_mock_state(self, **overrides):
        """Create a mock state manager."""
        state = MagicMock()
        stored = {}

        def mock_get(key, default=None):
            defaults = {
                "hull.lwl": 23.0,
                "hull.beam": 6.0,
                "hull.draft": 1.5,
                "stability.gm_transverse_m": 1.2,
                "mission.cruise_speed_kts": 25.0,
            }
            defaults.update(overrides)
            return stored.get(key, defaults.get(key, default))

        def mock_set(key, value):
            stored[key] = value

        state.get = mock_get
        state.set = mock_set
        return state, stored

    def test_validator_validate_success(self):
        """Test successful validation."""
        state, stored = self._create_mock_state()
        validator = SeakeepingValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert "analysis.seakeeping" in stored
        assert "analysis.operability_index" in stored

    def test_validator_validate_missing_inputs(self):
        """Test validation with missing inputs."""
        state, stored = self._create_mock_state(**{"hull.lwl": None})
        validator = SeakeepingValidator()
        result = validator.validate(state)

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validator_metadata(self):
        """Test validator metadata."""
        validator = SeakeepingValidator()
        assert validator.validator_id == "analysis/seakeeping"
        assert validator.phase == "analysis"
        assert "hull.lwl" in validator.reads
        assert "analysis.seakeeping" in validator.writes


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestAnalysisIntegration:
    """Integration tests for analysis modules."""

    def _create_full_mock_state(self):
        """Create a mock state with all required values."""
        state = MagicMock()
        stored = {}

        defaults = {
            # Hull parameters
            "hull.lwl": 23.0,
            "hull.beam": 6.0,
            "hull.draft": 1.5,
            # Propulsion
            "propulsion.num_engines": 2,
            "propulsion.installed_power_kw": 2000,
            "propulsion.total_installed_power_kw": 2000,
            # Electrical
            "electrical.num_generators": 2,
            "electrical.total_generation_kw": 100,
            # HVAC
            "hvac.total_power_kw": 15,
            # Stability
            "stability.gm_transverse_m": 1.2,
            # Mission
            "mission.cruise_speed_kts": 25.0,
            # Outfitting
            "outfitting.system": {
                "spaces": [
                    {"space_id": "WH", "space_type": "wheelhouse"},
                    {"space_id": "CC-1", "space_type": "crew_cabin"},
                    {"space_id": "MESS", "space_type": "mess"},
                ]
            },
        }

        def mock_get(key, default=None):
            return stored.get(key, defaults.get(key, default))

        def mock_set(key, value):
            stored[key] = value

        state.get = mock_get
        state.set = mock_set
        return state, stored

    def test_full_noise_vibration_analysis(self):
        """Test complete noise/vibration analysis pipeline."""
        state, stored = self._create_full_mock_state()

        validator = NoiseVibrationValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert stored["analysis.noise_compliant"] in [True, False]
        assert stored["analysis.max_noise_level_dba"] >= 0

    def test_full_seakeeping_analysis(self):
        """Test complete seakeeping analysis pipeline."""
        state, stored = self._create_full_mock_state()

        validator = SeakeepingValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert stored["analysis.max_sea_state"] >= 0
        assert stored["analysis.operability_index"] >= 0

    def test_combined_analysis(self):
        """Test running both analysis modules."""
        state, stored = self._create_full_mock_state()

        # Run noise/vibration analysis
        nv_validator = NoiseVibrationValidator()
        nv_result = nv_validator.validate(state)
        assert nv_result["valid"] is True

        # Run seakeeping analysis
        sk_validator = SeakeepingValidator()
        sk_result = sk_validator.validate(state)
        assert sk_result["valid"] is True

        # Verify both results stored
        assert "analysis.noise_vibration" in stored
        assert "analysis.seakeeping" in stored
