from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.parameters import (
    DeadriseProfile,
    FormCoefficients,
    HullDefinition,
    HullFeatures,
    MainDimensions,
)
from magnet.kernel.classification import classify_hull


def test_classification_regime_and_descriptors():
    gen = HullGenerator(config=GeneratorConfig(num_sections=11, points_per_section=25))
    definition = HullDefinition(
        hull_id="cls",
        hull_name="cls",
        dimensions=MainDimensions(loa=20.0, lwl=19.0, beam_max=4.8, beam_wl=4.8, depth=3.0, draft=1.4),
        coefficients=FormCoefficients(cb=0.45, cp=0.65, cm=0.80, cwp=0.75, lcb=0.52),
        deadrise=DeadriseProfile.warped(18.0, 20.0, 35.0),
        features=HullFeatures(chine_count=1),
    )

    geom = gen.generate(definition)
    cls = classify_hull(geom, speed_kts=35.0, lwl_m=definition.dimensions.lwl)
    assert cls.regime in ("displacement", "semi-displacement", "planing")
    assert cls.body_count >= 1
    assert "hard-chine" in (cls.form_descriptors or [])

