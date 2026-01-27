"""
tests/unit/test_hull_gen.py - Enum-free hull-gen regression tests.

Phase 3: form "type" buckets are removed from hull_gen.
"""

import pytest

from magnet.hull_gen import (
    MainDimensions,
    FormCoefficients,
    DeadriseProfile,
    HullFeatures,
    HullDefinition,
)

from magnet.hull_gen.generator import HullGenerator, GeneratorConfig, generate_hull_from_parameters


def test_hull_definition_serialization_roundtrip():
    d = HullDefinition(
        hull_id="TEST-001",
        hull_name="Test Hull",
        dimensions=MainDimensions(lwl=24.0, beam_wl=5.8, draft=1.4, loa=26.0, beam_max=6.2, depth=3.2),
        coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.70, cwp=0.75, lcb=0.52, lcf=0.50),
        deadrise=DeadriseProfile.warped(18.0, 20.0, 45.0),
        features=HullFeatures(chine_count=1),
    )
    d.compute_displacement()
    data = d.to_dict()
    d2 = HullDefinition.from_dict(data)
    assert d2.hull_id == "TEST-001"
    assert d2.dimensions.lwl == pytest.approx(24.0)
    assert d2.coefficients.cb == pytest.approx(0.45)


def test_generate_hull_from_parameters_smoke():
    geo = generate_hull_from_parameters(lwl=24.0, beam=6.0, draft=1.4, deadrise_deg=18.0)
    assert geo is not None
    assert len(geo.sections) > 0


def test_generator_runs_with_explicit_definition():
    gen = HullGenerator(GeneratorConfig(num_sections=21, points_per_section=25))
    d = HullDefinition(
        hull_id="TEST-GEN",
        hull_name="Test",
        dimensions=MainDimensions(loa=26.0, lwl=24.0, lpp=23.5, beam_max=6.2, beam_wl=5.8, beam_chine=5.4, depth=3.2, draft=1.4),
        coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.70, cwp=0.75, lcb=0.52, lcf=0.50),
        deadrise=DeadriseProfile.warped(18.0, 20.0, 45.0),
        features=HullFeatures(chine_count=1),
    )
    geo = gen.generate(d)
    assert geo is not None
    assert len(geo.sections) == 21

