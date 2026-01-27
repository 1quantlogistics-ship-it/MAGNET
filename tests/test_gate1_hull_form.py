"""
Gate 1 Hull Form Tests (Enum-free).

Gate intent (Phase 3):
- Authoritative geometry generation must work from continuous parameters
- No synthesis path depends on categorical hull type buckets
"""

import pytest


def test_hull_generator_produces_geometry_from_definition():
    from magnet.hull_gen.generator import HullGenerator
    from magnet.hull_gen.parameters import (
        HullDefinition,
        MainDimensions,
        FormCoefficients,
        DeadriseProfile,
        HullFeatures,
    )

    gen = HullGenerator()
    definition = HullDefinition(
        hull_id="test-hull",
        hull_name="Test Hull",
        dimensions=MainDimensions(
            loa=25.0,
            lwl=23.0,
            lpp=22.5,
            beam_max=6.0,
            beam_wl=5.7,
            beam_chine=5.4,
            depth=3.0,
            draft=1.5,
            draft_fwd=1.5,
            draft_aft=1.5,
        ),
        coefficients=FormCoefficients(
            cb=0.45,
            cp=0.65,
            cm=0.70,
            cwp=0.75,
            lcb=0.52,
            lcf=0.50,
        ),
        deadrise=DeadriseProfile.warped(15.0, 17.0, 40.0),
        features=HullFeatures(chine_count=1),
    )

    geom = gen.generate(definition)
    assert geom is not None
    assert len(geom.sections) > 0

