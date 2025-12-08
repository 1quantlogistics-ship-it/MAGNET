"""
Unit tests for MAGNET Hydrostatics Calculator.

Tests Module 05 v1.2 hydrostatics calculations.
"""

import pytest
import math
from datetime import datetime
from unittest.mock import MagicMock, patch

from magnet.physics import (
    HydrostaticsResults,
    HydrostaticsCalculator,
    HydrostaticsValidator,
    HYDROSTATICS_INPUTS,
    HYDROSTATICS_OUTPUTS,
)
from magnet.validators.taxonomy import ValidatorState, ResultSeverity
from magnet.core.constants import SEAWATER_DENSITY_KG_M3


# =============================================================================
# TEST HYDROSTATICS RESULTS
# =============================================================================

class TestHydrostaticsResults:
    """Test HydrostaticsResults dataclass."""

    def test_create_results(self):
        """Test creating a results object."""
        results = HydrostaticsResults(
            displacement_mt=100.0,
            volume_displaced_m3=97.56,
            kb_m=1.5,
            bm_m=3.0,
            km_m=4.5,
            lcb_m=10.0,
            vcb_m=1.5,
            waterplane_area_m2=50.0,
            lcf_m=9.5,
            moment_of_inertia_l_m4=1000.0,
            moment_of_inertia_t_m4=200.0,
            tpc=0.5125,
            mct=5.0,
            wetted_surface_m2=120.0,
            freeboard_m=1.0,
        )

        assert results.displacement_mt == 100.0
        assert results.volume_displaced_m3 == 97.56
        assert results.kb_m == 1.5
        assert results.bm_m == 3.0
        assert results.km_m == 4.5
        assert results.tpc == 0.5125
        assert results.freeboard_m == 1.0

    def test_serialization(self):
        """Test serialization to dict with proper precision."""
        results = HydrostaticsResults(
            displacement_mt=100.12345,
            volume_displaced_m3=97.56789,
            kb_m=1.5123,
            bm_m=3.0456,
            km_m=4.5579,
            lcb_m=10.0123,
            vcb_m=1.5123,
            waterplane_area_m2=50.123,
            lcf_m=9.5456,
            moment_of_inertia_l_m4=1000.123,
            moment_of_inertia_t_m4=200.456,
            tpc=0.51234567,
            mct=5.123,
            wetted_surface_m2=120.456,
            freeboard_m=1.0123,
        )

        data = results.to_dict()

        # Check precision
        assert data["displacement_mt"] == 100.12  # 2 decimal places
        assert data["volume_displaced_m3"] == 97.568  # 3 decimal places
        assert data["kb_m"] == 1.512  # 3 decimal places
        assert data["tpc"] == 0.5123  # 4 decimal places
        assert data["mct"] == 5.12  # 2 decimal places

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "displacement_mt": 100.0,
            "volume_displaced_m3": 97.56,
            "kb_m": 1.5,
            "bm_m": 3.0,
            "km_m": 4.5,
            "lcb_m": 10.0,
            "vcb_m": 1.5,
            "waterplane_area_m2": 50.0,
            "lcf_m": 9.5,
            "moment_of_inertia_l_m4": 1000.0,
            "moment_of_inertia_t_m4": 200.0,
            "tpc": 0.5125,
            "mct": 5.0,
            "wetted_surface_m2": 120.0,
            "freeboard_m": 1.0,
            "hull_type": "deep_v",
            "deadrise_deg": 15.0,
        }

        results = HydrostaticsResults.from_dict(data)

        assert results.displacement_mt == 100.0
        assert results.hull_type == "deep_v"
        assert results.deadrise_deg == 15.0

    def test_roundtrip_serialization(self):
        """Test serialization roundtrip preserves data."""
        original = HydrostaticsResults(
            displacement_mt=150.5,
            volume_displaced_m3=146.83,
            kb_m=2.0,
            bm_m=4.0,
            km_m=6.0,
            lcb_m=12.0,
            vcb_m=2.0,
            waterplane_area_m2=60.0,
            lcf_m=11.5,
            moment_of_inertia_l_m4=1500.0,
            moment_of_inertia_t_m4=300.0,
            tpc=0.615,
            mct=6.0,
            wetted_surface_m2=140.0,
            freeboard_m=1.5,
            hull_type="catamaran",
            warnings=["Test warning"],
        )

        restored = HydrostaticsResults.from_dict(original.to_dict())

        assert abs(restored.displacement_mt - original.displacement_mt) < 0.01
        assert restored.hull_type == original.hull_type


# =============================================================================
# TEST HYDROSTATICS CALCULATOR
# =============================================================================

class TestHydrostaticsCalculator:
    """Test HydrostaticsCalculator class."""

    @pytest.fixture
    def calculator(self):
        """Create calculator instance."""
        return HydrostaticsCalculator()

    def test_monohull_basic(self, calculator):
        """Test basic monohull calculation."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
            hull_type="monohull",
        )

        # Volume = LWL × B × T × Cb = 20 × 6 × 2 × 0.5 = 120 m³
        assert abs(results.volume_displaced_m3 - 120.0) < 0.1

        # Displacement = V × ρ / 1000 = 120 × 1025 / 1000 = 123 t
        expected_displacement = 120.0 * SEAWATER_DENSITY_KG_M3 / 1000.0
        assert abs(results.displacement_mt - expected_displacement) < 0.1

        # Freeboard = depth - draft = 3.5 - 2.0 = 1.5 m
        assert abs(results.freeboard_m - 1.5) < 0.01

    def test_deep_v_hull(self, calculator):
        """Test deep-V hull calculation."""
        results = calculator.calculate(
            lwl=15.0,
            beam=4.5,
            draft=1.5,
            depth=2.5,
            cb=0.45,
            hull_type="deep_v",
            deadrise_deg=20.0,
        )

        assert results.hull_type == "deep_v"
        assert results.deadrise_deg == 20.0
        assert results.volume_displaced_m3 > 0
        assert results.kb_m > 0
        assert results.bm_m > 0

    def test_catamaran(self, calculator):
        """Test catamaran calculation."""
        results = calculator.calculate(
            lwl=25.0,
            beam=10.0,  # Overall beam
            draft=1.8,
            depth=3.0,
            cb=0.55,
            hull_type="catamaran",
        )

        assert results.hull_type == "catamaran"
        # Catamaran has higher BM due to parallel axis
        assert results.bm_m > 0

    def test_missing_coefficients_estimated(self, calculator):
        """Test coefficient estimation when not provided."""
        results = calculator.calculate(
            lwl=18.0,
            beam=5.0,
            draft=1.8,
            depth=3.0,
            cb=0.52,
            # cp, cm, cwp not provided - should be estimated
        )

        # Should have warnings about estimated coefficients
        assert len(results.warnings) >= 3
        assert any("Cm estimated" in w for w in results.warnings)
        assert any("Cp estimated" in w for w in results.warnings)
        assert any("Cwp estimated" in w for w in results.warnings)

    def test_volume_calculation(self, calculator):
        """Test volume calculation accuracy."""
        # Simple case: V = L × B × T × Cb
        results = calculator.calculate(
            lwl=10.0,
            beam=4.0,
            draft=1.0,
            depth=2.0,
            cb=0.6,
        )

        expected_volume = 10.0 * 4.0 * 1.0 * 0.6  # 24 m³
        assert abs(results.volume_displaced_m3 - expected_volume) < 0.001

    def test_kb_calculation_monohull(self, calculator):
        """Test KB calculation for monohull (Morrish approximation)."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
            hull_type="monohull",
        )

        # KB = T × (5/6 - Cb/3) = 2 × (5/6 - 0.5/3) = 2 × (0.833 - 0.167) = 1.333
        expected_kb = 2.0 * (5.0/6.0 - 0.5/3.0)
        assert abs(results.kb_m - expected_kb) < 0.01

    def test_kb_calculation_deep_v(self, calculator):
        """Test KB calculation for deep-V hull."""
        results = calculator.calculate(
            lwl=15.0,
            beam=4.5,
            draft=1.5,
            depth=2.5,
            cb=0.45,
            hull_type="deep_v",
        )

        # KB = T × (0.78 - 0.285 × Cb) = 1.5 × (0.78 - 0.285 × 0.45)
        expected_kb = 1.5 * (0.78 - 0.285 * 0.45)
        assert abs(results.kb_m - expected_kb) < 0.01

    def test_bm_calculation(self, calculator):
        """Test BM (metacentric radius) calculation."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
            cwp=0.7,
            hull_type="monohull",
        )

        # BM = I_T / V
        # I_T ≈ (1/12) × L × B³ × CI × Cwp
        # V = L × B × T × Cb
        volume = 20.0 * 6.0 * 2.0 * 0.5
        ci = 0.5  # Monohull coefficient
        it = (1.0/12.0) * 20.0 * (6.0**3) * ci * 0.7
        expected_bm = it / volume

        assert abs(results.bm_m - expected_bm) < 0.1

    def test_km_equals_kb_plus_bm(self, calculator):
        """Test KM = KB + BM relationship."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
        )

        assert abs(results.km_m - (results.kb_m + results.bm_m)) < 0.001

    def test_tpc_calculation(self, calculator):
        """Test TPC (tonnes per cm immersion) calculation."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
            cwp=0.7,
        )

        # TPC = (ρ × Awp) / 100000
        # Awp = L × B × Cwp = 20 × 6 × 0.7 = 84 m²
        awp = 20.0 * 6.0 * 0.7
        expected_tpc = (SEAWATER_DENSITY_KG_M3 * awp) / 100000.0

        assert abs(results.tpc - expected_tpc) < 0.0001

    def test_mct_calculation(self, calculator):
        """Test MCT (moment to change trim 1cm) calculation."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
        )

        # MCT should be positive
        assert results.mct > 0

    def test_lcf_calculation(self, calculator):
        """Test LCF calculation."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
            cwp=0.7,
        )

        # LCF should be reasonable fraction of LWL
        assert 0.3 * 20.0 < results.lcf_m < 0.6 * 20.0

    def test_wetted_surface_monohull(self, calculator):
        """Test wetted surface calculation for monohull."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
            hull_type="monohull",
        )

        # Wetted surface should be positive and reasonable
        assert results.wetted_surface_m2 > 0
        # Rough check: S should be around 2 × (L × T + L × B/2)
        assert results.wetted_surface_m2 > 50  # Minimum sanity check

    def test_wetted_surface_deep_v(self, calculator):
        """Test wetted surface calculation for deep-V (includes deadrise factor)."""
        results_flat = calculator.calculate(
            lwl=15.0,
            beam=4.5,
            draft=1.5,
            depth=2.5,
            cb=0.45,
            hull_type="deep_v",
            deadrise_deg=0.0,
        )

        results_20deg = calculator.calculate(
            lwl=15.0,
            beam=4.5,
            draft=1.5,
            depth=2.5,
            cb=0.45,
            hull_type="deep_v",
            deadrise_deg=20.0,
        )

        # Higher deadrise should increase wetted surface
        assert results_20deg.wetted_surface_m2 > results_flat.wetted_surface_m2

    def test_freeboard_positive(self, calculator):
        """Test positive freeboard calculation."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
        )

        assert results.freeboard_m == 1.5

    def test_freeboard_negative_warning(self, calculator):
        """Test warning for negative freeboard."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=3.0,  # Greater than depth
            depth=2.5,
            cb=0.5,
        )

        assert results.freeboard_m < 0
        assert any("Negative freeboard" in w for w in results.warnings)

    def test_calculation_time_tracked(self, calculator):
        """Test that calculation time is tracked."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
        )

        # Should have non-negative calculation time
        assert results.calculation_time_ms >= 0

    def test_invalid_inputs_raise_error(self, calculator):
        """Test that invalid inputs raise ValueError."""
        with pytest.raises(ValueError):
            calculator.calculate(
                lwl=0.0,  # Invalid
                beam=6.0,
                draft=2.0,
                depth=3.5,
                cb=0.5,
            )

        with pytest.raises(ValueError):
            calculator.calculate(
                lwl=20.0,
                beam=6.0,
                draft=2.0,
                depth=3.5,
                cb=-0.1,  # Invalid
            )

    def test_vcb_equals_kb(self, calculator):
        """Test VCB is alias for KB."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
        )

        assert results.vcb_m == results.kb_m

    def test_all_outputs_present(self, calculator):
        """Test all 11 v1.2 outputs are calculated."""
        results = calculator.calculate(
            lwl=20.0,
            beam=6.0,
            draft=2.0,
            depth=3.5,
            cb=0.5,
        )

        # Check all required outputs exist and are reasonable
        assert results.displacement_mt > 0
        assert results.volume_displaced_m3 > 0
        assert results.kb_m > 0
        assert results.bm_m > 0
        assert results.km_m > 0
        assert results.lcb_m > 0
        assert results.vcb_m > 0
        assert results.tpc > 0
        assert results.mct > 0
        assert results.lcf_m > 0
        assert results.waterplane_area_m2 > 0
        assert results.wetted_surface_m2 > 0
        # freeboard can be negative


# =============================================================================
# TEST HYDROSTATICS VALIDATOR
# =============================================================================

class TestHydrostaticsValidator:
    """Test HydrostaticsValidator class."""

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock state manager."""
        manager = MagicMock()

        # Default hull parameters
        values = {
            "hull.lwl": 20.0,
            "hull.beam": 6.0,
            "hull.draft": 2.0,
            "hull.depth": 3.5,
            "hull.cb": 0.5,
            "hull.cp": None,
            "hull.cm": None,
            "hull.cwp": None,
            "hull.hull_type": "monohull",
            "hull.deadrise_deg": 0.0,
        }

        def get_value(key, default=None):
            return values.get(key, default)

        manager.get = MagicMock(side_effect=get_value)
        manager.set = MagicMock()

        return manager

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return HydrostaticsValidator()

    def test_validate_success(self, validator, mock_state_manager):
        """Test successful validation."""
        result = validator.validate(mock_state_manager, {})

        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)
        assert result.execution_time_ms >= 0

    def test_validate_missing_required_field(self, validator):
        """Test validation fails with missing required field."""
        manager = MagicMock()
        manager.get = MagicMock(side_effect=lambda k, d=None: {
            "hull.lwl": 0.0,  # Missing/invalid
            "hull.beam": 6.0,
            "hull.draft": 2.0,
            "hull.depth": 3.5,
            "hull.cb": 0.5,
        }.get(k, d))

        result = validator.validate(manager, {})

        assert result.state == ValidatorState.FAILED
        assert any("hull.lwl" in f.message for f in result.findings if f.severity == ResultSeverity.ERROR)

    def test_validate_writes_all_outputs(self, validator, mock_state_manager):
        """Test all 11 outputs are written to state manager."""
        validator.validate(mock_state_manager, {})

        # Check that all outputs were written
        written_params = [call[0][0] for call in mock_state_manager.set.call_args_list]

        expected_outputs = [
            "hull.displacement_m3",
            "hull.kb_m",
            "hull.bm_m",
            "hull.vcb_m",
            "hull.lcb_from_ap_m",
            "hull.lcf_from_ap_m",
            "hull.waterplane_area_m2",
            "hull.wetted_surface_m2",
            "hull.tpc",
            "hull.mct",
            "hull.freeboard",
        ]

        for param in expected_outputs:
            assert param in written_params, f"Missing output: {param}"

    def test_validate_missing_depth_defaults(self, validator):
        """Test depth defaults to draft + 1.5m when not provided."""
        manager = MagicMock()
        manager.get = MagicMock(side_effect=lambda k, d=None: {
            "hull.lwl": 20.0,
            "hull.beam": 6.0,
            "hull.draft": 2.0,
            "hull.depth": 0.0,  # Not provided
            "hull.cb": 0.5,
            "hull.hull_type": "monohull",
            "hull.deadrise_deg": 0.0,
        }.get(k, d))
        manager.set = MagicMock()

        result = validator.validate(manager, {})

        # Should succeed (validator defaults depth internally)
        assert result.state in (ValidatorState.PASSED, ValidatorState.WARNING)
        # Freeboard should be approximately 1.5m (the default)
        written_params = {call[0][0]: call[0][1] for call in manager.set.call_args_list}
        assert "hull.freeboard" in written_params
        assert abs(written_params["hull.freeboard"] - 1.5) < 0.1

    def test_integration_with_state_manager(self, validator, mock_state_manager):
        """Test integration with state manager read/write."""
        result = validator.validate(mock_state_manager, {})

        # Should have read required parameters
        assert mock_state_manager.get.called

        # Should have written results
        assert mock_state_manager.set.called

    def test_validator_id_matches_definition(self, validator):
        """Test validator ID matches its definition."""
        assert validator.definition.validator_id == "physics/hydrostatics"


# =============================================================================
# TEST MODULE CONSTANTS
# =============================================================================

class TestModuleConstants:
    """Test module-level constants."""

    def test_inputs_defined(self):
        """Test input parameters are defined."""
        assert len(HYDROSTATICS_INPUTS) > 0
        assert "hull.lwl" in HYDROSTATICS_INPUTS
        assert "hull.cb" in HYDROSTATICS_INPUTS

    def test_outputs_defined(self):
        """Test output parameters are defined (11 for v1.2)."""
        assert len(HYDROSTATICS_OUTPUTS) == 11
        assert "hull.displacement_m3" in HYDROSTATICS_OUTPUTS
        assert "hull.kb_m" in HYDROSTATICS_OUTPUTS
        assert "hull.bm_m" in HYDROSTATICS_OUTPUTS
        assert "hull.tpc" in HYDROSTATICS_OUTPUTS
        assert "hull.mct" in HYDROSTATICS_OUTPUTS
        assert "hull.freeboard" in HYDROSTATICS_OUTPUTS
