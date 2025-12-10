"""
test_section_sampler.py - Tests for section_sampler.py v1.1
BRAVO OWNS THIS FILE.

Module 59: Critical Architecture Fixes
Tests for hull section sampling utilities.
"""

import pytest
import math
from unittest.mock import Mock, patch

from magnet.interior.hull_integration.section_sampler import (
    SectionSampler,
    SamplingConfig,
    SampledSection,
    HullFormType,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def default_sampler():
    """Create sampler with default config."""
    return SectionSampler()


@pytest.fixture
def custom_config():
    """Create custom sampling config."""
    return SamplingConfig(
        num_sections=11,
        points_per_curve=10,
        x_start=0.0,
        x_end=1.0,
        include_key_stations=False,
    )


@pytest.fixture
def custom_sampler(custom_config):
    """Create sampler with custom config."""
    return SectionSampler(config=custom_config)


@pytest.fixture
def hull_params():
    """Standard hull parameters for testing."""
    return {
        "loa": 30.0,
        "lwl": 28.0,
        "beam": 7.0,
        "draft": 2.0,
        "depth": 4.0,
        "cb": 0.50,
        "hull_type": HullFormType.SEMI_DISPLACEMENT,
        "deadrise_deg": 12.0,
        "transom_width_ratio": 0.85,
    }


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    sm = Mock()
    sm.get_state_value = Mock(return_value=None)
    return sm


# =============================================================================
# SAMPLING CONFIG TESTS
# =============================================================================

class TestSamplingConfig:
    """Tests for SamplingConfig dataclass."""

    def test_default_config(self):
        """Default config has sensible values."""
        config = SamplingConfig()

        assert config.num_sections == 21
        assert config.points_per_curve == 20
        assert config.x_start == 0.0
        assert config.x_end == 1.0
        assert config.include_key_stations is True
        assert len(config.key_stations) >= 5

    def test_custom_config(self):
        """Custom config values are stored."""
        config = SamplingConfig(
            num_sections=50,
            points_per_curve=30,
            x_start=0.1,
            x_end=0.9,
        )

        assert config.num_sections == 50
        assert config.points_per_curve == 30
        assert config.x_start == 0.1
        assert config.x_end == 0.9

    def test_key_stations_default(self):
        """Key stations include standard positions."""
        config = SamplingConfig()

        assert 0.0 in config.key_stations  # AP
        assert 0.5 in config.key_stations  # Midship
        assert 1.0 in config.key_stations  # FP


# =============================================================================
# SAMPLED SECTION TESTS
# =============================================================================

class TestSampledSection:
    """Tests for SampledSection dataclass."""

    def test_create_section(self):
        """Create section with basic data."""
        section = SampledSection(
            x_position=15.0,
            x_normalized=0.5,
            half_breadth_points=[(0.0, 0.5), (2.0, 3.0), (4.0, 3.5)],
            beam_at_waterline=6.0,
            beam_max=7.0,
            draft_at_section=2.0,
            depth_at_section=4.0,
        )

        assert section.x_position == 15.0
        assert section.x_normalized == 0.5
        assert len(section.half_breadth_points) == 3
        assert section.beam_at_waterline == 6.0

    def test_half_breadth_interpolation(self):
        """Half-breadth interpolation works correctly."""
        section = SampledSection(
            x_position=15.0,
            x_normalized=0.5,
            half_breadth_points=[(0.0, 0.0), (1.0, 2.0), (2.0, 3.0), (4.0, 3.5)],
        )

        # At exact points
        assert abs(section.half_breadth_at_z(0.0) - 0.0) < 0.1
        assert abs(section.half_breadth_at_z(1.0) - 2.0) < 0.1

        # Interpolated
        y_at_0_5 = section.half_breadth_at_z(0.5)
        assert 0.5 < y_at_0_5 < 2.0  # Between 0 and 2

    def test_half_breadth_extrapolation(self):
        """Half-breadth extrapolates beyond range."""
        section = SampledSection(
            x_position=15.0,
            x_normalized=0.5,
            half_breadth_points=[(1.0, 2.0), (2.0, 3.0)],
        )

        # Below range
        assert section.half_breadth_at_z(0.0) == 2.0  # First value

        # Above range
        assert section.half_breadth_at_z(5.0) == 3.0  # Last value

    def test_is_inside(self):
        """is_inside correctly identifies points."""
        section = SampledSection(
            x_position=15.0,
            x_normalized=0.5,
            half_breadth_points=[(0.0, 1.0), (2.0, 3.0), (4.0, 3.5)],
        )

        # Inside
        assert section.is_inside(0.5, 1.0) is True
        assert section.is_inside(-0.5, 1.0) is True  # Port side
        assert section.is_inside(2.0, 2.0) is True

        # Outside (beyond half-breadth)
        assert section.is_inside(5.0, 2.0) is False
        assert section.is_inside(-5.0, 2.0) is False

    def test_to_dict(self):
        """Serialization to dict works."""
        section = SampledSection(
            x_position=15.0,
            x_normalized=0.5,
            half_breadth_points=[(0.0, 0.5), (2.0, 3.0)],
            beam_at_waterline=6.0,
            beam_max=7.0,
            draft_at_section=2.0,
            depth_at_section=4.0,
        )

        data = section.to_dict()

        assert data["x_position"] == 15.0
        assert data["x_normalized"] == 0.5
        assert data["beam_at_waterline"] == 6.0
        assert len(data["half_breadth_points"]) == 2

    def test_from_dict(self):
        """Deserialization from dict works."""
        data = {
            "x_position": 15.0,
            "x_normalized": 0.5,
            "half_breadth_points": [[0.0, 0.5], [2.0, 3.0]],
            "beam_at_waterline": 6.0,
            "beam_max": 7.0,
            "draft_at_section": 2.0,
            "depth_at_section": 4.0,
        }

        section = SampledSection.from_dict(data)

        assert section.x_position == 15.0
        assert section.x_normalized == 0.5
        assert len(section.half_breadth_points) == 2
        assert section.beam_at_waterline == 6.0

    def test_empty_points(self):
        """Handle empty half-breadth points gracefully."""
        section = SampledSection(
            x_position=15.0,
            x_normalized=0.5,
            half_breadth_points=[],
        )

        # Should not raise
        result = section.half_breadth_at_z(1.0)
        assert result == 0.0


# =============================================================================
# SECTION SAMPLER TESTS
# =============================================================================

class TestSectionSampler:
    """Tests for SectionSampler class."""

    def test_create_default(self, default_sampler):
        """Create sampler with default config."""
        assert default_sampler.config.num_sections == 21
        assert default_sampler.config.include_key_stations is True

    def test_create_custom(self, custom_sampler, custom_config):
        """Create sampler with custom config."""
        assert custom_sampler.config.num_sections == 11
        assert custom_sampler.config.include_key_stations is False

    def test_sample_from_params(self, default_sampler, hull_params):
        """Sample sections from parameter dict."""
        sections = default_sampler.sample_from_params(hull_params)

        assert len(sections) >= 21  # At least num_sections
        assert all(isinstance(s, SampledSection) for s in sections)

        # Sections should be sorted by position
        positions = [s.x_position for s in sections]
        assert positions == sorted(positions)

    def test_section_positions(self, default_sampler, hull_params):
        """Section positions span the vessel length."""
        sections = default_sampler.sample_from_params(hull_params)

        # First section at AP
        assert sections[0].x_normalized == pytest.approx(0.0, abs=0.01)
        assert sections[0].x_position == pytest.approx(0.0, abs=0.1)

        # Last section at FP
        assert sections[-1].x_normalized == pytest.approx(1.0, abs=0.01)
        assert sections[-1].x_position == pytest.approx(hull_params["loa"], abs=0.1)

    def test_midship_section(self, default_sampler, hull_params):
        """Midship section has maximum beam."""
        sections = default_sampler.sample_from_params(hull_params)

        # Find midship section
        midship = min(sections, key=lambda s: abs(s.x_normalized - 0.5))

        # Should have full beam
        assert midship.beam_max > 0
        assert midship.beam_max <= hull_params["beam"] * 1.1  # Allow 10% tolerance

    def test_bow_section_narrower(self, default_sampler, hull_params):
        """Bow sections are narrower than midship."""
        sections = default_sampler.sample_from_params(hull_params)

        midship = min(sections, key=lambda s: abs(s.x_normalized - 0.5))
        bow = sections[-1]  # FP

        assert bow.beam_max < midship.beam_max

    def test_transom_section(self, default_sampler, hull_params):
        """Transom section respects transom ratio."""
        sections = default_sampler.sample_from_params(hull_params)

        transom = sections[0]  # AP

        # Transom should be narrower than midship
        midship = min(sections, key=lambda s: abs(s.x_normalized - 0.5))
        assert transom.beam_max < midship.beam_max

    def test_hard_chine_hull(self, default_sampler):
        """Hard chine hull type generates correct sections."""
        params = {
            "loa": 25.0,
            "beam": 6.0,
            "draft": 1.5,
            "depth": 3.0,
            "cb": 0.4,
            "hull_type": HullFormType.HARD_CHINE,
            "deadrise_deg": 18.0,
        }

        sections = default_sampler.sample_from_params(params)

        assert len(sections) > 0
        # Hard chine should have clear break in curve
        midship = min(sections, key=lambda s: abs(s.x_normalized - 0.5))
        assert len(midship.half_breadth_points) >= 3

    def test_round_bilge_hull(self, default_sampler):
        """Round bilge hull type generates smooth sections."""
        params = {
            "loa": 40.0,
            "beam": 10.0,
            "draft": 3.0,
            "depth": 5.0,
            "cb": 0.6,
            "hull_type": HullFormType.ROUND_BILGE,
            "deadrise_deg": 5.0,
        }

        sections = default_sampler.sample_from_params(params)

        assert len(sections) > 0
        # Round bilge should have many points for smooth curve
        midship = min(sections, key=lambda s: abs(s.x_normalized - 0.5))
        assert len(midship.half_breadth_points) >= 10

    def test_planing_hull(self, default_sampler):
        """Planing hull type generates correct sections."""
        params = {
            "loa": 15.0,
            "beam": 4.0,
            "draft": 0.8,
            "depth": 2.0,
            "cb": 0.35,
            "hull_type": HullFormType.PLANING,
            "deadrise_deg": 22.0,
        }

        sections = default_sampler.sample_from_params(params)

        assert len(sections) > 0
        midship = min(sections, key=lambda s: abs(s.x_normalized - 0.5))
        assert midship.beam_max > 0

    def test_default_hull_params(self, default_sampler):
        """Uses default params when none provided."""
        sections = default_sampler.sample_from_params({})

        assert len(sections) > 0
        assert all(s.beam_max > 0 for s in sections)

    def test_caching(self, default_sampler, hull_params):
        """Section caching works correctly."""
        # First call - should generate
        sections1 = default_sampler.sample_from_params(hull_params)

        # Cache manually
        default_sampler._cache["test_design"] = sections1

        # Check cache
        assert "test_design" in default_sampler.get_cached_keys()

        # Clear cache
        default_sampler.clear_cache()
        assert len(default_sampler.get_cached_keys()) == 0

    def test_custom_section_count(self, hull_params):
        """Custom section count is respected."""
        config = SamplingConfig(
            num_sections=5,
            include_key_stations=False,
        )
        sampler = SectionSampler(config=config)

        sections = sampler.sample_from_params(hull_params)

        assert len(sections) == 5

    def test_key_stations_included(self, hull_params):
        """Key stations are included when enabled."""
        config = SamplingConfig(
            num_sections=3,
            include_key_stations=True,
            key_stations=[0.0, 0.5, 1.0],
        )
        sampler = SectionSampler(config=config)

        sections = sampler.sample_from_params(hull_params)

        # Should have at least the key stations
        normalized = [s.x_normalized for s in sections]
        assert any(abs(n - 0.0) < 0.01 for n in normalized)
        assert any(abs(n - 0.5) < 0.01 for n in normalized)
        assert any(abs(n - 1.0) < 0.01 for n in normalized)

    def test_partial_length_sampling(self, hull_params):
        """Sampling a partial length range works."""
        config = SamplingConfig(
            num_sections=11,
            x_start=0.2,
            x_end=0.8,
            include_key_stations=False,
        )
        sampler = SectionSampler(config=config)

        sections = sampler.sample_from_params(hull_params)

        # All sections should be in range
        for section in sections:
            assert 0.2 <= section.x_normalized <= 0.8


# =============================================================================
# HULL FORM TYPE TESTS
# =============================================================================

class TestHullFormType:
    """Tests for HullFormType constants."""

    def test_hull_types_defined(self):
        """All hull form types are defined."""
        assert HullFormType.PLANING == "planing"
        assert HullFormType.SEMI_DISPLACEMENT == "semi_displacement"
        assert HullFormType.DISPLACEMENT == "displacement"
        assert HullFormType.ROUND_BILGE == "round_bilge"
        assert HullFormType.HARD_CHINE == "hard_chine"
        assert HullFormType.CATAMARAN == "catamaran"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSectionSamplerIntegration:
    """Integration tests for section sampling."""

    def test_section_curve_continuity(self, default_sampler, hull_params):
        """Section curves are continuous (no jumps)."""
        sections = default_sampler.sample_from_params(hull_params)

        for section in sections:
            if len(section.half_breadth_points) < 2:
                continue

            sorted_points = sorted(section.half_breadth_points, key=lambda p: p[0])

            for i in range(len(sorted_points) - 1):
                z1, y1 = sorted_points[i]
                z2, y2 = sorted_points[i + 1]

                # No huge jumps in y (max 50% of beam per step)
                max_jump = hull_params["beam"] * 0.5
                assert abs(y2 - y1) < max_jump, f"Large jump at z={z1:.2f}: {y1:.2f} -> {y2:.2f}"

    def test_sections_form_valid_hull(self, default_sampler, hull_params):
        """Sections together form a valid hull shape."""
        sections = default_sampler.sample_from_params(hull_params)

        # Get beam at waterline for each section
        beams = [(s.x_normalized, s.beam_at_waterline) for s in sections]

        # Find max beam and its position
        max_beam_section = max(beams, key=lambda b: b[1])

        # Max beam should be near midship (within 30% of length)
        assert 0.2 < max_beam_section[0] < 0.8, "Max beam not near midship"

        # Bow should be narrower than max
        bow_section = [b for b in beams if b[0] > 0.9][0]
        assert bow_section[1] < max_beam_section[1]

    def test_draft_respected(self, default_sampler, hull_params):
        """Sections respect draft setting."""
        sections = default_sampler.sample_from_params(hull_params)

        for section in sections:
            assert section.draft_at_section == hull_params["draft"]
            assert section.depth_at_section == hull_params["depth"]

    def test_all_sections_have_points(self, default_sampler, hull_params):
        """All sections have half-breadth points."""
        sections = default_sampler.sample_from_params(hull_params)

        for section in sections:
            assert len(section.half_breadth_points) > 0
            assert all(len(p) == 2 for p in section.half_breadth_points)
            assert all(isinstance(p[0], (int, float)) for p in section.half_breadth_points)
            assert all(isinstance(p[1], (int, float)) for p in section.half_breadth_points)


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_beam(self, default_sampler):
        """Handle zero beam gracefully."""
        params = {
            "loa": 25.0,
            "beam": 0.0,  # Invalid but shouldn't crash
            "draft": 1.5,
            "depth": 3.0,
        }

        sections = default_sampler.sample_from_params(params)
        assert len(sections) > 0

    def test_very_small_vessel(self, default_sampler):
        """Handle very small vessel dimensions."""
        params = {
            "loa": 3.0,
            "beam": 1.0,
            "draft": 0.3,
            "depth": 0.5,
        }

        sections = default_sampler.sample_from_params(params)
        assert len(sections) > 0

    def test_very_large_vessel(self, default_sampler):
        """Handle very large vessel dimensions."""
        params = {
            "loa": 300.0,
            "beam": 50.0,
            "draft": 15.0,
            "depth": 25.0,
        }

        sections = default_sampler.sample_from_params(params)
        assert len(sections) > 0
        assert sections[-1].x_position == pytest.approx(300.0, rel=0.01)

    def test_extreme_cb(self, default_sampler):
        """Handle extreme block coefficient values."""
        for cb in [0.1, 0.5, 0.9]:
            params = {
                "loa": 25.0,
                "beam": 6.0,
                "draft": 1.5,
                "depth": 3.0,
                "cb": cb,
            }

            sections = default_sampler.sample_from_params(params)
            assert len(sections) > 0

    def test_extreme_deadrise(self, default_sampler):
        """Handle extreme deadrise angles."""
        for deadrise in [0.0, 25.0, 45.0]:
            params = {
                "loa": 25.0,
                "beam": 6.0,
                "draft": 1.5,
                "depth": 3.0,
                "deadrise_deg": deadrise,
            }

            sections = default_sampler.sample_from_params(params)
            assert len(sections) > 0

    def test_unknown_hull_type(self, default_sampler):
        """Handle unknown hull type (uses default)."""
        params = {
            "loa": 25.0,
            "beam": 6.0,
            "draft": 1.5,
            "depth": 3.0,
            "hull_type": "unknown_type",
        }

        # Should not raise, uses default
        sections = default_sampler.sample_from_params(params)
        assert len(sections) > 0

    def test_single_section(self):
        """Handle single section sampling."""
        config = SamplingConfig(
            num_sections=1,
            include_key_stations=False,
        )
        sampler = SectionSampler(config=config)

        sections = sampler.sample_from_params({
            "loa": 25.0,
            "beam": 6.0,
            "draft": 1.5,
        })

        assert len(sections) == 1
