"""
Phase 1 edge typing (enum-free).

Hard edges must be represented as geometric/topological properties on section points,
not as a form enum. This suite checks that chines produce hard edges when enabled.
"""

from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.parameters import (
    HullDefinition,
    HullFeatures,
    MainDimensions,
    FormCoefficients,
    DeadriseProfile,
)
from magnet.hull_gen.geometry import EdgeType


def _definition(features: HullFeatures) -> HullDefinition:
    return HullDefinition(
        hull_id="EDGE-TEST",
        hull_name="Edge Test",
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


def test_chine_points_are_hard_when_chine_enabled():
    gen = HullGenerator(GeneratorConfig(num_sections=7, points_per_section=25))
    hull = gen.generate(_definition(HullFeatures(chine_count=1)))

    mid = hull.sections[len(hull.sections) // 2]
    chine_pts = [p for p in mid.points if p.is_chine]
    assert chine_pts, "Expected at least one chine point when chine_count=1"
    assert all(p.edge_type == EdgeType.HARD for p in chine_pts)


def test_round_sections_have_no_chine_points_by_default():
    gen = HullGenerator(GeneratorConfig(num_sections=7, points_per_section=25))
    hull = gen.generate(_definition(HullFeatures(chine_count=0)))

    for section in hull.sections:
        assert not any(p.is_chine for p in section.points)

