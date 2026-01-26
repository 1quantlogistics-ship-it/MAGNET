"""
Phase 3 bow form tests (enum-free).

Bow behavior must be controlled via `BowConfig` (continuous params),
not via any style/profile enums.
"""

import math

import pytest

from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.bow_generator import BowGenerator
from magnet.hull_gen.parameters import (
    HullDefinition,
    MainDimensions,
    FormCoefficients,
    DeadriseProfile,
    HullFeatures,
    BowConfig,
)


def _base_definition(features: HullFeatures) -> HullDefinition:
    return HullDefinition(
        hull_id="TEST-PHASE3",
        hull_name="Test Phase 3 Hull",
        dimensions=MainDimensions(
            loa=20.0,
            lwl=19.0,
            lpp=18.5,
            beam_max=5.0,
            beam_wl=4.8,
            beam_chine=4.5,
            depth=3.0,
            draft=1.5,
        ),
        coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.80, cwp=0.75, lcb=0.52),
        deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
        features=features,
    )


class TestBowConfig:
    def test_defaults(self):
        cfg = BowConfig()
        assert cfg.facet_count == 0
        assert cfg.half_angle_deg == 25.0
        assert cfg.region_length == 0.20

    @pytest.mark.parametrize(
        "facet_count, planarity, expected",
        [
            (0, 0.0, False),  # smooth
            (1, 1.0, True),   # wedge
            (3, 1.0, True),   # faceted
            (3, 0.2, False),  # facets requested but not planar -> treat as smooth
        ],
    )
    def test_is_angular(self, facet_count: int, planarity: float, expected: bool):
        cfg = BowConfig(facet_count=facet_count, planarity=planarity)
        assert cfg.is_angular() is expected


class TestBowGenerator:
    @pytest.mark.parametrize(
        "cfg",
        [
            BowConfig(),  # smooth
            BowConfig(facet_count=1, planarity=1.0),  # wedge
            BowConfig(facet_count=3, planarity=1.0),  # faceted
            BowConfig(stem_rake_deg=-5.0, flare_deg=-5.0),  # wave-piercing-like (still smooth unless planar)
        ],
    )
    def test_generate_returns_sections(self, cfg: BowConfig):
        gen = BowGenerator()
        features = HullFeatures(chine_count=1)
        definition = _base_definition(features)

        geom = gen.generate(definition, cfg, num_sections=6)
        assert geom.sections, "Expected bow sections to be generated"

    def test_angular_bows_produce_panel_edges(self):
        gen = BowGenerator()
        definition = _base_definition(HullFeatures(chine_count=1))
        cfg = BowConfig(facet_count=1, planarity=1.0)

        geom = gen.generate(definition, cfg, num_sections=6)
        assert len(geom.panel_edges) > 0

    def test_traditional_bow_has_no_panel_edges(self):
        gen = BowGenerator()
        definition = _base_definition(HullFeatures(chine_count=1))
        cfg = BowConfig()

        geom = gen.generate(definition, cfg, num_sections=6)
        assert len(geom.panel_edges) == 0


class TestHullGeneratorIntegration:
    @pytest.mark.parametrize(
        "bow_cfg, expect_edges",
        [
            (BowConfig(), False),
            (BowConfig(facet_count=1, planarity=1.0, region_length=0.25), True),
            (BowConfig(facet_count=3, planarity=1.0, region_length=0.25), True),
            (BowConfig(stem_rake_deg=-5.0, flare_deg=-5.0, region_length=0.25), False),
        ],
    )
    def test_hull_generator_uses_bow_config(self, bow_cfg: BowConfig, expect_edges: bool):
        generator = HullGenerator(GeneratorConfig(num_sections=21))

        features = HullFeatures(chine_count=1, bow_config=bow_cfg)
        hull = generator.generate(_base_definition(features))

        assert len(hull.sections) == 21
        assert hull.volume >= 0.0

        if expect_edges:
            assert len(hull.bow_panel_edges) > 0
        else:
            assert len(hull.bow_panel_edges) == 0

    def test_no_nan_in_generated_points(self):
        generator = HullGenerator(GeneratorConfig(num_sections=21))
        features = HullFeatures(chine_count=1, bow_config=BowConfig(facet_count=1, planarity=1.0))
        hull = generator.generate(_base_definition(features))

        for section in hull.sections:
            for p in section.points:
                assert not math.isnan(p.position.x)
                assert not math.isnan(p.position.y)
                assert not math.isnan(p.position.z)

