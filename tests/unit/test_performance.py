"""
tests/unit/test_performance.py - Tests for Modules 39-40 (Performance).

BRAVO OWNS THIS FILE.

Tests for performance modules implemented by BRAVO:
- Module 39: Performance Prediction
- Module 40: Operational Envelope
"""

import pytest
import math
from unittest.mock import MagicMock

from magnet.performance import (
    # Resistance & Prediction
    ResistanceComponents, SpeedPowerPoint, PropulsiveEfficiency,
    PerformancePredictor, PerformanceValidator,
    # Envelope
    OperationalLimit, SpeedSeaStatePoint, OperationalEnvelope,
    EnvelopeGenerator, EnvelopeValidator,
)


# =============================================================================
# MODULE 39: PERFORMANCE PREDICTION TESTS
# =============================================================================

class TestResistanceComponents:
    """Test ResistanceComponents dataclass."""

    def test_resistance_components_creation(self):
        """Test creating resistance components."""
        rc = ResistanceComponents(
            speed_kts=25.0,
            frictional_kn=5.0,
            residuary_kn=10.0,
            appendage_kn=1.0,
            air_kn=0.5,
        )
        assert rc.speed_kts == 25.0
        assert rc.frictional_kn == 5.0

    def test_resistance_components_total(self):
        """Test total resistance calculation."""
        rc = ResistanceComponents(
            frictional_kn=5.0,
            residuary_kn=10.0,
            appendage_kn=1.0,
            air_kn=0.5,
            spray_kn=0.5,
        )
        assert rc.total_kn == 17.0

    def test_resistance_components_power(self):
        """Test effective power calculation."""
        rc = ResistanceComponents(
            speed_kts=20.0,
            frictional_kn=10.0,
        )
        # Power = R * V
        speed_m_s = 20.0 * 0.5144
        expected_kw = 10.0 * 1000 * speed_m_s / 1000
        assert rc.total_kw == pytest.approx(expected_kw, rel=0.01)

    def test_resistance_components_to_dict(self):
        """Test serialization."""
        rc = ResistanceComponents(
            speed_kts=25.0,
            frictional_kn=5.0,
            residuary_kn=10.0,
        )
        data = rc.to_dict()
        assert "total_kn" in data
        assert "effective_power_kw" in data


class TestSpeedPowerPoint:
    """Test SpeedPowerPoint dataclass."""

    def test_speed_power_point_creation(self):
        """Test creating a speed-power point."""
        point = SpeedPowerPoint(
            speed_kts=25.0,
            froude_number=0.55,
            resistance_kn=15.0,
            effective_power_kw=200.0,
            delivered_power_kw=280.0,
            brake_power_kw=290.0,
        )
        assert point.speed_kts == 25.0
        assert point.brake_power_kw == 290.0

    def test_speed_power_point_to_dict(self):
        """Test serialization."""
        point = SpeedPowerPoint(
            speed_kts=30.0,
            froude_number=0.65,
            brake_power_kw=500.0,
        )
        data = point.to_dict()
        assert data["speed_kts"] == 30.0
        assert data["froude_number"] == 0.65


class TestPropulsiveEfficiency:
    """Test PropulsiveEfficiency dataclass."""

    def test_propulsive_efficiency_creation(self):
        """Test creating efficiency breakdown."""
        eff = PropulsiveEfficiency(
            hull_efficiency=1.05,
            propeller_efficiency=0.65,
            transmission_efficiency=0.97,
        )
        assert eff.hull_efficiency == 1.05

    def test_propulsive_coefficient(self):
        """Test propulsive coefficient calculation."""
        eff = PropulsiveEfficiency(
            hull_efficiency=1.0,
            relative_rotative=1.0,
            propeller_efficiency=0.65,
        )
        assert eff.propulsive_coefficient == pytest.approx(0.65, rel=0.01)

    def test_overall_efficiency(self):
        """Test overall efficiency calculation."""
        eff = PropulsiveEfficiency(
            hull_efficiency=1.0,
            relative_rotative=1.0,
            propeller_efficiency=0.65,
            transmission_efficiency=0.97,
        )
        expected = 0.65 * 0.97
        assert eff.overall_efficiency == pytest.approx(expected, rel=0.01)

    def test_propulsive_efficiency_to_dict(self):
        """Test serialization."""
        eff = PropulsiveEfficiency(
            propeller_efficiency=0.68,
        )
        data = eff.to_dict()
        assert "propulsive_coefficient" in data
        assert "overall_efficiency" in data


class TestPerformancePredictor:
    """Test PerformancePredictor class."""

    def _create_mock_state(self, **kwargs):
        """Create a mock state manager."""
        state = MagicMock()
        defaults = {
            "hull.loa": 25.0,
            "hull.lwl": 23.0,
            "hull.beam": 6.0,
            "hull.draft": 1.5,
            "hull.wetted_surface_m2": 120.0,
            "weight.full_load_displacement_mt": 80.0,
            "weight.displacement_mt": 80.0,
            "mission.max_speed_kts": 35.0,
            "mission.cruise_speed_kts": 25.0,
            "mission.max_speed_knots": 35.0,
            "mission.cruise_speed_knots": 25.0,
            "propulsion.propulsion_type": "propeller",
            "propulsion.installed_power_kw": 2000.0,
        }
        defaults.update(kwargs)
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def test_predictor_predict(self):
        """Test full prediction."""
        state = self._create_mock_state()
        predictor = PerformancePredictor(state)
        results = predictor.predict()

        assert "curve" in results
        assert "efficiency" in results
        assert "cruise_power_kw" in results
        assert "max_power_kw" in results
        assert len(results["curve"]) > 0

    def test_predictor_efficiency_propeller(self):
        """Test efficiency estimation for propeller."""
        state = self._create_mock_state(propulsion__propulsion_type="propeller")
        state.get = lambda key, default=None: {
            "propulsion.propulsion_type": "propeller"
        }.get(key, default)
        predictor = PerformancePredictor(state)
        eff = predictor._estimate_efficiency()
        assert eff.hull_efficiency == 1.05

    def test_predictor_efficiency_waterjet(self):
        """Test efficiency estimation for waterjet."""
        state = self._create_mock_state()
        state.get = lambda key, default=None: {
            "propulsion.propulsion_type": "waterjet"
        }.get(key, default)
        predictor = PerformancePredictor(state)
        eff = predictor._estimate_efficiency()
        assert eff.propeller_efficiency == 0.68

    def test_predictor_speed_fallback(self):
        """Test speed field fallback to _knots."""
        state = self._create_mock_state(**{
            "mission.max_speed_kts": None,
            "mission.cruise_speed_kts": None,
        })
        predictor = PerformancePredictor(state)
        results = predictor.predict()
        assert results["max_speed_kts"] == 35.0  # From _knots fallback


class TestPerformanceValidator:
    """Test PerformanceValidator class."""

    def _create_mock_state(self, **overrides):
        """Create a mock state manager."""
        state = MagicMock()
        stored = {}

        def mock_get(key, default=None):
            defaults = {
                "hull.loa": 25.0,
                "hull.lwl": 23.0,
                "hull.beam": 6.0,
                "hull.draft": 1.5,
                "hull.wetted_surface_m2": 120.0,
                "weight.full_load_displacement_mt": 80.0,
                "mission.max_speed_kts": 35.0,
                "mission.cruise_speed_kts": 25.0,
                "propulsion.propulsion_type": "propeller",
                "propulsion.installed_power_kw": 2000.0,
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
        validator = PerformanceValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert "performance.speed_power_curve" in stored
        assert "performance.cruise_power_kw" in stored

    def test_validator_insufficient_power(self):
        """Test validation with insufficient power."""
        state, stored = self._create_mock_state(**{"propulsion.installed_power_kw": 100})
        validator = PerformanceValidator()
        result = validator.validate(state)

        # Should fail due to low installed power
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validator_metadata(self):
        """Test validator metadata."""
        validator = PerformanceValidator()
        assert validator.validator_id == "performance/prediction"
        assert validator.phase == "propulsion"
        assert "hull.lwl" in validator.reads


# =============================================================================
# MODULE 40: OPERATIONAL ENVELOPE TESTS
# =============================================================================

class TestOperationalLimit:
    """Test OperationalLimit dataclass."""

    def test_operational_limit_creation(self):
        """Test creating an operational limit."""
        limit = OperationalLimit(
            limit_id="LIM-SPEED",
            limit_type="speed",
            value=35.0,
            unit="kts",
            source="design",
        )
        assert limit.limit_id == "LIM-SPEED"
        assert limit.value == 35.0

    def test_operational_limit_to_dict(self):
        """Test serialization."""
        limit = OperationalLimit(
            limit_id="LIM-SS",
            limit_type="sea_state",
            value=4,
            unit="SS",
        )
        data = limit.to_dict()
        assert data["limit_type"] == "sea_state"


class TestSpeedSeaStatePoint:
    """Test SpeedSeaStatePoint dataclass."""

    def test_speed_sea_state_creation(self):
        """Test creating a speed-sea state point."""
        point = SpeedSeaStatePoint(
            sea_state=3,
            hs_m=1.25,
            max_speed_kts=25.0,
            limiting_factor="acceleration",
            range_nm=400.0,
        )
        assert point.sea_state == 3
        assert point.max_speed_kts == 25.0

    def test_speed_sea_state_to_dict(self):
        """Test serialization."""
        point = SpeedSeaStatePoint(
            sea_state=4,
            max_speed_kts=20.5,
        )
        data = point.to_dict()
        assert data["max_speed_kts"] == 20.5


class TestOperationalEnvelope:
    """Test OperationalEnvelope dataclass."""

    def test_operational_envelope_creation(self):
        """Test creating an operational envelope."""
        envelope = OperationalEnvelope(
            envelope_id="ENV-001",
            design_speed_kts=25.0,
            max_operational_sea_state=4,
            range_at_cruise_nm=500.0,
        )
        assert envelope.envelope_id == "ENV-001"
        assert envelope.max_operational_sea_state == 4

    def test_operational_envelope_with_limits(self):
        """Test envelope with limits."""
        envelope = OperationalEnvelope(
            limits=[
                OperationalLimit(limit_id="L1", limit_type="speed", value=35),
                OperationalLimit(limit_id="L2", limit_type="range", value=500),
            ],
        )
        assert len(envelope.limits) == 2

    def test_operational_envelope_to_dict(self):
        """Test serialization."""
        envelope = OperationalEnvelope(
            envelope_id="ENV-002",
            design_speed_kts=30.0,
            speed_sea_state=[
                SpeedSeaStatePoint(sea_state=0, max_speed_kts=35),
            ],
        )
        data = envelope.to_dict()
        assert "limits" in data
        assert "speed_sea_state" in data


class TestEnvelopeGenerator:
    """Test EnvelopeGenerator class."""

    def _create_mock_state(self, **kwargs):
        """Create a mock state manager."""
        state = MagicMock()
        defaults = {
            "metadata.design_id": "TEST-001",
            "mission.max_speed_kts": 35.0,
            "mission.cruise_speed_kts": 25.0,
            "mission.max_speed_knots": 35.0,
            "mission.cruise_speed_knots": 25.0,
            "analysis.max_sea_state": 4,
            "propulsion.fuel_rate_cruise_l_hr": 200.0,
            "fuel.usable_fuel_m3": 5.0,
            "fuel.range_at_cruise_nm": 500.0,
        }
        defaults.update(kwargs)
        state.get = lambda key, default=None: defaults.get(key, default)
        return state

    def test_generator_generate(self):
        """Test full envelope generation."""
        state = self._create_mock_state()
        generator = EnvelopeGenerator(state)
        envelope = generator.generate()

        assert envelope.envelope_id == "ENV-TEST-001"
        assert len(envelope.limits) > 0
        assert len(envelope.speed_sea_state) > 0

    def test_generator_collect_limits(self):
        """Test limit collection."""
        state = self._create_mock_state()
        generator = EnvelopeGenerator(state)
        limits = generator._collect_limits()

        limit_types = [l.limit_type for l in limits]
        assert "speed" in limit_types
        assert "sea_state" in limit_types
        assert "range" in limit_types

    def test_generator_speed_sea_state(self):
        """Test speed-sea state generation."""
        state = self._create_mock_state(**{"analysis.max_sea_state": 4})
        generator = EnvelopeGenerator(state)
        points = generator._generate_speed_sea_state()

        assert len(points) == 5  # SS 0-4
        assert points[0].max_speed_kts == 35.0  # SS 0 = max speed
        assert points[3].limiting_factor == "acceleration"  # SS 3

    def test_generator_endurance(self):
        """Test endurance calculation."""
        state = self._create_mock_state(**{
            "fuel.usable_fuel_m3": 5.0,
            "propulsion.fuel_rate_cruise_l_hr": 200.0,
        })
        generator = EnvelopeGenerator(state)
        endurance = generator._calculate_endurance()

        # 5000 L / 200 L/hr = 25 hours
        assert endurance == pytest.approx(25.0, rel=0.01)

    def test_generator_range(self):
        """Test range calculation."""
        state = self._create_mock_state(**{
            "fuel.usable_fuel_m3": 5.0,
            "propulsion.fuel_rate_cruise_l_hr": 200.0,
            "mission.cruise_speed_kts": 25.0,
        })
        generator = EnvelopeGenerator(state)
        range_nm = generator._calculate_range()

        # 25 hours * 25 kts = 625 nm
        assert range_nm == pytest.approx(625.0, rel=0.01)


class TestEnvelopeValidator:
    """Test EnvelopeValidator class."""

    def _create_mock_state(self, **overrides):
        """Create a mock state manager."""
        state = MagicMock()
        stored = {}

        def mock_get(key, default=None):
            defaults = {
                "metadata.design_id": "TEST-001",
                "mission.max_speed_kts": 35.0,
                "mission.cruise_speed_kts": 25.0,
                "mission.required_range_nm": 300.0,
                "analysis.max_sea_state": 4,
                "propulsion.fuel_rate_cruise_l_hr": 200.0,
                "fuel.usable_fuel_m3": 5.0,
                "fuel.range_at_cruise_nm": 500.0,
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
        validator = EnvelopeValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert "performance.operational_envelope" in stored
        assert "performance.range_nm" in stored

    def test_validator_range_warning(self):
        """Test warning for insufficient range."""
        state, stored = self._create_mock_state(**{
            "mission.required_range_nm": 1000.0,
        })
        validator = EnvelopeValidator()
        result = validator.validate(state)

        assert len(result["warnings"]) > 0

    def test_validator_metadata(self):
        """Test validator metadata."""
        validator = EnvelopeValidator()
        assert validator.validator_id == "performance/envelope"
        assert validator.phase == "analysis"
        assert "analysis.max_sea_state" in validator.reads


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestPerformanceIntegration:
    """Integration tests for performance modules."""

    def _create_full_mock_state(self):
        """Create a mock state with all required values."""
        state = MagicMock()
        stored = {}

        defaults = {
            # Metadata
            "metadata.design_id": "TEST-001",
            # Hull parameters
            "hull.loa": 25.0,
            "hull.lwl": 23.0,
            "hull.beam": 6.0,
            "hull.draft": 1.5,
            "hull.wetted_surface_m2": 120.0,
            # Weight
            "weight.full_load_displacement_mt": 80.0,
            "weight.displacement_mt": 80.0,
            # Mission
            "mission.max_speed_kts": 35.0,
            "mission.cruise_speed_kts": 25.0,
            "mission.required_range_nm": 300.0,
            # Propulsion
            "propulsion.propulsion_type": "propeller",
            "propulsion.installed_power_kw": 2000.0,
            "propulsion.fuel_rate_cruise_l_hr": 200.0,
            # Fuel
            "fuel.usable_fuel_m3": 5.0,
            "fuel.range_at_cruise_nm": 500.0,
            # Analysis (from Module 35)
            "analysis.max_sea_state": 4,
        }

        def mock_get(key, default=None):
            return stored.get(key, defaults.get(key, default))

        def mock_set(key, value):
            stored[key] = value

        state.get = mock_get
        state.set = mock_set
        return state, stored

    def test_full_performance_prediction(self):
        """Test complete performance prediction pipeline."""
        state, stored = self._create_full_mock_state()

        validator = PerformanceValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert stored["performance.cruise_power_kw"] > 0
        assert stored["performance.max_power_kw"] > 0

    def test_full_envelope_generation(self):
        """Test complete envelope generation pipeline."""
        state, stored = self._create_full_mock_state()

        validator = EnvelopeValidator()
        result = validator.validate(state)

        assert result["valid"] is True
        assert stored["performance.range_nm"] > 0
        assert stored["performance.endurance_hr"] > 0

    def test_combined_performance_analysis(self):
        """Test running both performance modules."""
        state, stored = self._create_full_mock_state()

        # Run performance prediction
        perf_validator = PerformanceValidator()
        perf_result = perf_validator.validate(state)
        assert perf_result["valid"] is True

        # Run envelope generation
        env_validator = EnvelopeValidator()
        env_result = env_validator.validate(state)
        assert env_result["valid"] is True

        # Verify both results stored
        assert "performance.speed_power_curve" in stored
        assert "performance.operational_envelope" in stored

    def test_performance_seakeeping_integration(self):
        """Test that envelope uses seakeeping analysis results."""
        state, stored = self._create_full_mock_state()

        # Verify envelope respects max_sea_state from seakeeping
        generator = EnvelopeGenerator(state)
        envelope = generator.generate()

        assert envelope.max_operational_sea_state == 4
        assert len(envelope.speed_sea_state) == 5  # SS 0-4
