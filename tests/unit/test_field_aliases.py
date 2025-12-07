"""
Unit tests for field_aliases.py.

Tests alias resolution and normalization.
"""

import pytest
from magnet.core.field_aliases import (
    normalize_path,
    is_alias,
    get_canonical,
    get_alias,
    list_aliases,
    get_all_paths_for_section,
    FIELD_ALIASES,
)


class TestNormalizePath:
    """Test normalize_path function."""

    def test_canonical_unchanged(self):
        """Test canonical paths are unchanged."""
        assert normalize_path("mission.vessel_type") == "mission.vessel_type"
        assert normalize_path("hull.loa") == "hull.loa"

    def test_alias_resolved(self):
        """Test aliases are resolved."""
        assert normalize_path("mission.max_speed_knots") == "mission.max_speed_kts"
        assert normalize_path("hull.length") == "hull.loa"

    def test_prefix_alias_resolved(self):
        """Test prefix aliases are resolved."""
        # "structure" -> "structural_design"
        result = normalize_path("structure.material")
        assert "structural_design" in result

    def test_unknown_path_unchanged(self):
        """Test unknown paths are unchanged."""
        assert normalize_path("unknown.path") == "unknown.path"


class TestIsAlias:
    """Test is_alias function."""

    def test_alias_detected(self):
        """Test aliases are detected."""
        assert is_alias("mission.max_speed_knots")
        assert is_alias("hull.length")

    def test_canonical_not_alias(self):
        """Test canonical paths are not aliases."""
        assert not is_alias("mission.max_speed_kts")
        assert not is_alias("hull.loa")


class TestGetCanonical:
    """Test get_canonical function."""

    def test_alias_to_canonical(self):
        """Test getting canonical from alias."""
        assert get_canonical("mission.max_speed_knots") == "mission.max_speed_kts"

    def test_canonical_returns_self(self):
        """Test canonical returns itself."""
        assert get_canonical("mission.vessel_type") == "mission.vessel_type"


class TestGetAlias:
    """Test get_alias function."""

    def test_get_alias_for_canonical(self):
        """Test getting alias for canonical path."""
        alias = get_alias("mission.max_speed_kts")
        assert alias == "mission.max_speed_knots"

    def test_no_alias_returns_none(self):
        """Test None returned when no alias exists."""
        result = get_alias("some.unique.path")
        assert result is None


class TestListAliases:
    """Test list_aliases function."""

    def test_list_all(self):
        """Test listing all aliases."""
        all_aliases = list_aliases()
        assert isinstance(all_aliases, dict)
        assert len(all_aliases) > 0

    def test_list_by_prefix(self):
        """Test listing aliases by prefix."""
        mission_aliases = list_aliases("mission")
        assert isinstance(mission_aliases, dict)
        # All should start with mission
        for alias in mission_aliases.keys():
            assert alias.startswith("mission")

    def test_list_empty_prefix(self):
        """Test listing with non-matching prefix."""
        result = list_aliases("nonexistent_section")
        assert isinstance(result, dict)
        assert len(result) == 0


class TestGetAllPathsForSection:
    """Test get_all_paths_for_section function."""

    def test_mission_paths(self):
        """Test getting all paths for mission section."""
        paths = get_all_paths_for_section("mission")
        assert isinstance(paths, dict)
        # Should include both aliases and canonical
        assert len(paths) > 0

    def test_hull_paths(self):
        """Test getting all paths for hull section."""
        paths = get_all_paths_for_section("hull")
        assert isinstance(paths, dict)


class TestAliasConsistency:
    """Test alias mapping consistency."""

    def test_all_aliases_resolve(self):
        """Test all aliases resolve to valid canonical paths."""
        for alias, canonical in FIELD_ALIASES.items():
            # Alias shouldn't equal canonical
            assert alias != canonical
            # Canonical shouldn't be another alias
            assert canonical not in FIELD_ALIASES

    def test_no_circular_aliases(self):
        """Test no circular alias definitions."""
        seen = set()
        for alias in FIELD_ALIASES.keys():
            canonical = normalize_path(alias)
            # Normalizing the canonical should return itself
            assert normalize_path(canonical) == canonical
