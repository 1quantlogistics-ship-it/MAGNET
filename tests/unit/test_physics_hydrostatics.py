"""
Unit tests for magnet/physics/hydrostatics.py

Tests HydrostaticsCalculator and HydrostaticsResults.
"""

import pytest
import math
from magnet.physics.hydrostatics import (
    HydrostaticsCalculator,
    HydrostaticsResults,
    HYDROSTATICS_INPUTS,
    HYDROSTATICS_OUTPUTS,
    RHO_SEAWATER,
)


class TestHydrostaticsResults:
    """Test HydrostaticsResults dataclass."""

    def test_create_results(self):
        """Test creating results with all fields."""
        results = HydrostaticsResults(
            displacement_mt=100.0,
            volume_displaced_m3=97.56,
            kb_m=1.5,
            bm_m=2.0,
            km_m=3.5,
            lcb_m=22.0,
            vcb_m=1.5,
            waterplane_area_m2=250.0,
            lcf_m=21.0,
            moment_of_inertia_l_m4=5000.0,
            moment_of_inertia_t_m4=500.0,
            tpc=2.5,
            mct=50.0,
            wetted_surface_m2=400.0,
            freeboard_m=1.5,
        )
        assert results.displacement_mt == 100.0
        assert results.kb_m == 1.5
        assert results.bm_m == 2.0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        results = HydrostaticsResults(
            displacement_mt=100.0,
            volume_displaced_m3=97.56,
            kb_m=1.5,
            bm_m=2.0,
            km_m=3.5,
            lcb_m=22.0,
            vcb_m=1.5,
            waterplane_area_m2=250.0,
            lcf_m=21.0,
            moment_of_inertia_l_m4=5000.0,
            moment_of_inertia_t_m4=500.0,
            tpc=2.5,
            mct=50.0,
            wetted_surface_m2=400.0,
            freeboard_m=1.5,
        )
        data = results.to_dict()
        assert data["displacement_mt"] == 100.0
        assert data["kb_m"] == 1.5
        assert "warnings" in data

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "displacement_mt": 150.0,
            "volume_displaced_m3": 146.34,
            "kb_m": 2.0,
            "bm_m": 3.0,
            "km_m": 5.0,
            "lcb_m": 25.0,
            "vcb_m": 2.0,
            "waterplane_area_m2": 300.0,
            "lcf_m": 24.0,
            "moment_of_inertia_l_m4": 6000.0,
            "moment_of_inertia_t_m4": 600.0,
            "tpc": 3.0,
            "mct": 60.0,
            "wetted_surface_m2": 500.0,
            "freeboard_m": 2.0,
        }
        results = HydrostaticsResults.from_dict(data)
        assert results.displacement_mt == 150.0
        assert results.kb_m == 2.0


class TestHydrostaticsCalculator:
    """Test HydrostaticsCalculator class."""

    def setup_method(self):
        """Set up calculator for tests."""
        self.calculator = HydrostaticsCalculator()

    def test_displacement_calculation(self):
        """Test displacement calculation accuracy."""
        # V = L * B * T * Cb
        # Displacement = V * rho / 1000
        lwl, beam, draft, cb = 50.0, 10.0, 2.5, 0.55
        expected_volume = lwl * beam * draft * cb  # 687.5 m³
        expected_displacement = expected_volume * RHO_SEAWATER / 1000  # 704.69 t

        results = self.calculator.calculate(
            lwl=lwl, beam=beam, draft=draft, depth=4.0, cb=cb
        )

        assert abs(results.volume_displaced_m3 - expected_volume) < 0.1
        assert abs(results.displacement_mt - expected_displacement) < 0.5

    def test_kb_calculation(self):
        """Test KB (center of buoyancy) calculation."""
        # Morrish approximation: KB = T * (5/6 - Cb/3)
        draft, cb = 2.5, 0.55
        expected_kb = draft * (5.0/6.0 - cb/3.0)

        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=draft, depth=4.0, cb=cb
        )

        assert abs(results.kb_m - expected_kb) < 0.01

    def test_bm_calculation_positive(self):
        """Test BM (metacentric radius) is positive."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )
        assert results.bm_m > 0

    def test_km_equals_kb_plus_bm(self):
        """Test KM = KB + BM."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )
        assert abs(results.km_m - (results.kb_m + results.bm_m)) < 0.001

    def test_tpc_calculation(self):
        """Test TPC (tonnes per cm immersion) calculation."""
        # TPC = (rho * Awp) / 100000
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )
        # TPC should be positive and reasonable
        assert results.tpc > 0
        assert results.tpc < 50  # Reasonable upper bound for this hull

    def test_mct_calculation(self):
        """Test MCT (moment to change trim) calculation."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )
        assert results.mct > 0

    def test_freeboard_calculation(self):
        """Test freeboard calculation."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )
        assert results.freeboard_m == 4.0 - 2.5  # depth - draft

    def test_negative_freeboard_warning(self):
        """Test warning for negative freeboard."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=3.0, depth=2.5, cb=0.55  # draft > depth
        )
        assert results.freeboard_m < 0
        assert any("freeboard" in w.lower() for w in results.warnings)

    def test_all_v12_outputs_present(self):
        """Test that all v1.2 outputs are present."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )
        data = results.to_dict()

        # v1.2 required outputs
        required = [
            "displacement_mt", "volume_displaced_m3",
            "kb_m", "bm_m", "km_m", "lcb_m", "vcb_m",
            "tpc", "mct", "lcf_m",
            "waterplane_area_m2", "wetted_surface_m2", "freeboard_m"
        ]
        for field in required:
            assert field in data, f"Missing v1.2 output: {field}"

    def test_hull_type_monohull(self):
        """Test monohull calculations."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55,
            hull_type="monohull"
        )
        assert results.hull_type == "monohull"
        assert results.displacement_mt > 0

    def test_hull_type_deep_v(self):
        """Test deep-V hull calculations."""
        results = self.calculator.calculate(
            lwl=30.0, beam=6.0, draft=1.5, depth=2.5, cb=0.45,
            hull_type="deep_v", deadrise_deg=20.0
        )
        assert results.hull_type == "deep_v"
        assert results.deadrise_deg == 20.0

    def test_hull_type_catamaran(self):
        """Test catamaran calculations."""
        results = self.calculator.calculate(
            lwl=40.0, beam=12.0, draft=1.8, depth=3.0, cb=0.50,
            hull_type="catamaran"
        )
        assert results.hull_type == "catamaran"
        # Catamaran should have higher BM due to hull spacing
        mono_results = self.calculator.calculate(
            lwl=40.0, beam=12.0, draft=1.8, depth=3.0, cb=0.50,
            hull_type="monohull"
        )
        assert results.bm_m > mono_results.bm_m

    def test_invalid_inputs_raises(self):
        """Test that invalid inputs raise ValueError."""
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=-50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
            )
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=50.0, beam=0, draft=2.5, depth=4.0, cb=0.55
            )
        with pytest.raises(ValueError):
            self.calculator.calculate(
                lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0
            )

    def test_missing_depth_default(self):
        """Test default depth when not provided."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=0, cb=0.55
        )
        # Should default to draft + 1.5m
        assert results.freeboard_m == pytest.approx(1.5, abs=0.1)
        assert any("depth" in w.lower() for w in results.warnings)

    def test_coefficient_estimation_warnings(self):
        """Test warnings when coefficients are estimated."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55,
            # Not providing cp, cm, cwp - should be estimated
        )
        # Should have warnings about estimated coefficients
        assert len(results.warnings) >= 1

    def test_wetted_surface_positive(self):
        """Test wetted surface is positive."""
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55
        )
        assert results.wetted_surface_m2 > 0

    def test_waterplane_area(self):
        """Test waterplane area calculation."""
        # Awp = L * B * Cwp
        results = self.calculator.calculate(
            lwl=50.0, beam=10.0, draft=2.5, depth=4.0, cb=0.55, cwp=0.75
        )
        expected_awp = 50.0 * 10.0 * 0.75
        assert abs(results.waterplane_area_m2 - expected_awp) < 1.0


class TestHydrostaticsConstants:
    """Test module constants."""

    def test_inputs_defined(self):
        """Test HYDROSTATICS_INPUTS is defined."""
        assert len(HYDROSTATICS_INPUTS) > 0
        assert "hull.lwl" in HYDROSTATICS_INPUTS

    def test_outputs_defined(self):
        """Test HYDROSTATICS_OUTPUTS is defined."""
        assert len(HYDROSTATICS_OUTPUTS) > 0
        assert "hull.displacement_m3" in HYDROSTATICS_OUTPUTS

    def test_rho_seawater(self):
        """Test seawater density constant."""
        assert RHO_SEAWATER == 1025.0
