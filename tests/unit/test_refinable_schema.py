"""
Unit tests for REFINABLE_SCHEMA.

Tests the whitelist for LLM-proposed actions.
"""

import pytest
from magnet.core.refinable_schema import (
    REFINABLE_SCHEMA,
    RefinableField,
    get_field,
    is_refinable,
    get_all_refinable_paths,
    find_by_keyword,
)


class TestRefinableField:
    """Tests for RefinableField dataclass."""

    def test_field_creation(self):
        """Can create a RefinableField."""
        field = RefinableField(
            path="test.path",
            type="float",
            kernel_unit="m",
            allowed_units=("m", "ft"),
            min_value=0,
            max_value=100,
            keywords=("test", "example"),
        )
        assert field.path == "test.path"
        assert field.type == "float"
        assert "m" in field.allowed_units
        assert "ft" in field.allowed_units

    def test_field_is_immutable(self):
        """RefinableField is frozen (immutable)."""
        field = RefinableField(
            path="test.path",
            type="float",
            kernel_unit="m",
            allowed_units=("m",),
        )
        with pytest.raises(AttributeError):
            field.path = "other.path"

    def test_field_converts_lists_to_tuples(self):
        """Lists are converted to tuples for immutability."""
        field = RefinableField(
            path="test.path",
            type="float",
            kernel_unit="m",
            allowed_units=["m", "ft"],  # List
            keywords=["a", "b"],  # List
        )
        assert isinstance(field.allowed_units, tuple)
        assert isinstance(field.keywords, tuple)


class TestRefinableSchema:
    """Tests for REFINABLE_SCHEMA dictionary."""

    def test_schema_not_empty(self):
        """Schema has entries."""
        assert len(REFINABLE_SCHEMA) > 0

    def test_hull_loa_in_schema(self):
        """hull.loa is refinable."""
        assert "hull.loa" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["hull.loa"]
        assert field.kernel_unit == "m"
        assert "ft" in field.allowed_units

    def test_propulsion_power_in_schema(self):
        """propulsion.total_installed_power_kw is refinable."""
        assert "propulsion.total_installed_power_kw" in REFINABLE_SCHEMA
        field = REFINABLE_SCHEMA["propulsion.total_installed_power_kw"]
        assert field.kernel_unit == "kW"
        assert "MW" in field.allowed_units
        assert "hp" in field.allowed_units

    def test_all_fields_have_required_attributes(self):
        """All fields have required attributes."""
        for path, field in REFINABLE_SCHEMA.items():
            assert field.path == path
            assert field.type in ("float", "int", "bool")
            assert field.kernel_unit is not None
            assert len(field.allowed_units) > 0


class TestGetField:
    """Tests for get_field function."""

    def test_get_existing_field(self):
        """Can get an existing field."""
        field = get_field("hull.loa")
        assert field is not None
        assert field.path == "hull.loa"

    def test_get_nonexistent_field(self):
        """Returns None for nonexistent field."""
        field = get_field("nonexistent.path")
        assert field is None


class TestIsRefinable:
    """Tests for is_refinable function."""

    def test_refinable_path(self):
        """Returns True for refinable paths."""
        assert is_refinable("hull.loa") is True
        assert is_refinable("propulsion.total_installed_power_kw") is True

    def test_non_refinable_path(self):
        """Returns False for non-refinable paths."""
        assert is_refinable("nonexistent.path") is False
        assert is_refinable("design_id") is False


class TestGetAllRefinablePaths:
    """Tests for get_all_refinable_paths function."""

    def test_returns_list(self):
        """Returns a list of paths."""
        paths = get_all_refinable_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0

    def test_contains_known_paths(self):
        """Contains known refinable paths."""
        paths = get_all_refinable_paths()
        assert "hull.loa" in paths
        assert "hull.beam" in paths
        assert "propulsion.total_installed_power_kw" in paths


class TestFindByKeyword:
    """Tests for find_by_keyword function."""

    def test_find_by_exact_keyword(self):
        """Can find fields by exact keyword."""
        matches = find_by_keyword("power")
        assert len(matches) > 0
        paths = [m.path for m in matches]
        assert "propulsion.total_installed_power_kw" in paths

    def test_find_by_partial_keyword(self):
        """Can find fields by partial keyword."""
        matches = find_by_keyword("length")
        assert len(matches) > 0
        # Should match hull.loa which has "length" keyword

    def test_case_insensitive(self):
        """Keyword search is case-insensitive."""
        matches_lower = find_by_keyword("beam")
        matches_upper = find_by_keyword("BEAM")
        assert len(matches_lower) == len(matches_upper)

    def test_no_matches(self):
        """Returns empty list for no matches."""
        matches = find_by_keyword("xyznonexistent")
        assert matches == []

    def test_matches_path(self):
        """Can match by path content."""
        matches = find_by_keyword("hull")
        assert len(matches) > 0
        # Should match all hull.* paths


class TestSchemaConsistency:
    """Tests for schema consistency and completeness."""

    def test_min_less_than_max(self):
        """min_value is less than max_value where both defined."""
        for path, field in REFINABLE_SCHEMA.items():
            if field.min_value is not None and field.max_value is not None:
                assert field.min_value < field.max_value, f"{path}: min >= max"

    def test_kernel_unit_in_allowed(self):
        """kernel_unit is in allowed_units (or empty for dimensionless)."""
        for path, field in REFINABLE_SCHEMA.items():
            if field.kernel_unit:
                assert field.kernel_unit in field.allowed_units, (
                    f"{path}: kernel_unit '{field.kernel_unit}' not in allowed_units"
                )

    def test_int_fields_have_int_bounds(self):
        """Integer fields have integer bounds."""
        for path, field in REFINABLE_SCHEMA.items():
            if field.type == "int":
                if field.min_value is not None:
                    assert field.min_value == int(field.min_value), f"{path}: min is not int"
                if field.max_value is not None:
                    assert field.max_value == int(field.max_value), f"{path}: max is not int"
