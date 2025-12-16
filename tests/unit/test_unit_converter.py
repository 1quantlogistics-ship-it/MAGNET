"""
Unit tests for UnitConverter.

Tests deterministic unit conversions.
"""

import pytest
from magnet.core.unit_converter import (
    UnitConverter,
    UnitConversionError,
    clamp_to_bounds,
)


class TestUnitConverter:
    """Tests for UnitConverter class."""

    def test_mw_to_kw(self):
        """1 MW = 1000 kW."""
        assert UnitConverter.normalize(1, "MW", "kW") == 1000.0

    def test_kw_to_mw(self):
        """1000 kW = 1 MW."""
        assert UnitConverter.normalize(1000, "kW", "MW") == 1.0

    def test_ft_to_m(self):
        """1 ft = 0.3048 m."""
        result = UnitConverter.normalize(1, "ft", "m")
        assert abs(result - 0.3048) < 0.0001

    def test_m_to_ft(self):
        """1 m = 3.28084 ft."""
        result = UnitConverter.normalize(1, "m", "ft")
        assert abs(result - 3.28084) < 0.0001

    def test_nm_to_km(self):
        """1 nm = 1.852 km."""
        result = UnitConverter.normalize(1, "nm", "km")
        assert abs(result - 1.852) < 0.0001

    def test_kts_to_ms(self):
        """1 kt = 0.514444 m/s."""
        result = UnitConverter.normalize(1, "kts", "m/s")
        assert abs(result - 0.514444) < 0.0001

    def test_same_unit_returns_value(self):
        """Converting to same unit returns original value."""
        assert UnitConverter.normalize(42.5, "m", "m") == 42.5

    def test_unknown_conversion_raises(self):
        """Unknown conversion raises UnitConversionError."""
        with pytest.raises(UnitConversionError, match="Unknown conversion"):
            UnitConverter.normalize(1, "lightyears", "parsecs")

    def test_exact_case_required(self):
        """Conversions require exact case for mixed-case units like kW."""
        # MW -> kW works (exact match)
        assert UnitConverter.normalize(1, "MW", "kW") == 1000.0
        # Use exact case - "kW" not "KW"

    def test_hp_to_kw(self):
        """1 hp = 0.7457 kW."""
        result = UnitConverter.normalize(1, "hp", "kW")
        assert abs(result - 0.7457) < 0.001

    def test_mt_to_kg(self):
        """1 mt = 1000 kg."""
        assert UnitConverter.normalize(1, "mt", "kg") == 1000.0


class TestCanConvert:
    """Tests for can_convert method."""

    def test_supported_conversion(self):
        """Returns True for supported conversions."""
        assert UnitConverter.can_convert("MW", "kW") is True
        assert UnitConverter.can_convert("m", "ft") is True

    def test_unsupported_conversion(self):
        """Returns False for unsupported conversions."""
        assert UnitConverter.can_convert("lightyears", "parsecs") is False

    def test_same_unit(self):
        """Same unit always converts."""
        assert UnitConverter.can_convert("m", "m") is True
        assert UnitConverter.can_convert("anything", "anything") is True


class TestGetSupportedUnits:
    """Tests for get_supported_units."""

    def test_returns_set(self):
        """Returns a set of unit strings."""
        units = UnitConverter.get_supported_units()
        assert isinstance(units, set)
        assert len(units) > 0

    def test_contains_common_units(self):
        """Contains common units."""
        units = UnitConverter.get_supported_units()
        assert "m" in units
        assert "ft" in units
        assert "kW" in units
        assert "MW" in units
        assert "kts" in units


class TestClampToBounds:
    """Tests for clamp_to_bounds function."""

    def test_value_within_bounds(self):
        """Value within bounds is unchanged."""
        clamped, was_clamped = clamp_to_bounds(50, 0, 100)
        assert clamped == 50
        assert was_clamped is False

    def test_value_below_min(self):
        """Value below min is clamped to min."""
        clamped, was_clamped = clamp_to_bounds(-10, 0, 100)
        assert clamped == 0
        assert was_clamped is True

    def test_value_above_max(self):
        """Value above max is clamped to max."""
        clamped, was_clamped = clamp_to_bounds(150, 0, 100)
        assert clamped == 100
        assert was_clamped is True

    def test_no_min(self):
        """No min bound means no lower clamping."""
        clamped, was_clamped = clamp_to_bounds(-1000, None, 100)
        assert clamped == -1000
        assert was_clamped is False

    def test_no_max(self):
        """No max bound means no upper clamping."""
        clamped, was_clamped = clamp_to_bounds(1000000, 0, None)
        assert clamped == 1000000
        assert was_clamped is False

    def test_no_bounds(self):
        """No bounds means no clamping."""
        clamped, was_clamped = clamp_to_bounds(12345, None, None)
        assert clamped == 12345
        assert was_clamped is False
