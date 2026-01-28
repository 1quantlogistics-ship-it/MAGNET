"""
Phase 2 chine variations (enum-free).

This suite validates that chine behavior is controlled via continuous parameters
and explicit configs (not a fixed ChineType enum).
"""

import math

import pytest

from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.parameters import (
    HullDefinition,
    HullFeatures,
    MainDimensions,
    FormCoefficients,
    DeadriseProfile,
    ChineConfig,
)


def _create_definition(features: HullFeatures) -> HullDefinition:
    return HullDefinition(
        hull_id="TEST-CHINE",
        hull_name="Test Chine",
        dimensions=MainDimensions(
            loa=26.0,
            lwl=24.0,
            lpp=23.5,
            beam_max=6.2,
            beam_wl=5.8,
            beam_chine=5.4,
            depth=3.2,
            draft=1.4,
        ),
        coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.70, cwp=0.75, lcb=0.52, lcf=0.50),
        deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
        features=features,
    )


class TestChineConfigGeneration:
    @pytest.mark.parametrize("chine_count, expected", [(0, 0), (1, 1), (2, 2), (3, 3), (5, 3)])
    def test_get_chine_configs_from_count(self, chine_count: int, expected: int):
        features = HullFeatures(chine_count=chine_count)
        configs = features.get_chine_configs()
        assert len(configs) == expected

    def test_explicit_chines_override_defaults(self):
        explicit = [ChineConfig(height_ratio=0.5, angle_deg=30, is_hard=True)]
        features = HullFeatures(chine_count=3, chines=explicit)
        configs = features.get_chine_configs()
        assert configs == explicit

    def test_reverse_chine_enabled_generates_reverse_config(self):
        features = HullFeatures(
            chine_count=1,
            chine_style="reverse",
            reverse_chine_height_ratio=0.4,
            reverse_chine_extension_m=0.15,
        )
        configs = features.get_chine_configs()
        assert len(configs) == 1
        assert configs[0].angle_deg < 0  # outward angle convention


class TestChineGeometry:
    def test_double_chine_generates_multiple_chine_points(self):
        gen = HullGenerator(config=GeneratorConfig(num_sections=9, points_per_section=25))
        definition = _create_definition(HullFeatures(chine_count=2))
        hull = gen.generate(definition)

        mid = hull.sections[len(hull.sections) // 2]
        chine_pts = [p for p in mid.points if p.is_chine]
        assert len(chine_pts) >= 2

    def test_triple_chine_generates_multiple_chine_points(self):
        gen = HullGenerator(config=GeneratorConfig(num_sections=9, points_per_section=29))
        definition = _create_definition(HullFeatures(chine_count=3))
        hull = gen.generate(definition)

        mid = hull.sections[len(hull.sections) // 2]
        chine_pts = [p for p in mid.points if p.is_chine]
        assert len(chine_pts) >= 3

    def test_variable_chine_no_nan(self):
        gen = HullGenerator(config=GeneratorConfig(num_sections=9, points_per_section=25))
        features = HullFeatures(
            chine_count=1,
            chine_style="variable",
            chine_transition_start=0.3,
            chine_transition_end=0.6,
        )
        definition = _create_definition(features)
        hull = gen.generate(definition)

        for section in hull.sections:
            for p in section.points:
                assert not math.isnan(p.position.x)
                assert not math.isnan(p.position.y)
                assert not math.isnan(p.position.z)

