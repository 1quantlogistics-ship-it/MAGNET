from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.parameters import (
    DeadriseProfile,
    FormCoefficients,
    HullDefinition,
    HullFeatures,
    MainDimensions,
)
from magnet.kernel.anchor_detector import detect_anchors


def _make_test_hull_geometry():
    gen = HullGenerator(config=GeneratorConfig(num_sections=9, points_per_section=21))
    definition = HullDefinition(
        hull_id="anchor-test",
        hull_name="anchor-test",
        dimensions=MainDimensions(
            loa=18.0,
            lwl=17.0,
            beam_max=4.4,
            beam_wl=4.2,
            depth=2.2,
            draft=0.9,
        ),
        coefficients=FormCoefficients(cb=0.52, cp=0.65, cm=0.80, cwp=0.72, lcb=0.52),
        deadrise=DeadriseProfile.warped(14.0, 16.0, 25.0),
        features=HullFeatures(chine_count=1),
    )
    return gen.generate(definition)


def test_detect_anchors_finds_extrema_labels():
    geom = _make_test_hull_geometry()
    anchors = detect_anchors(geom)

    assert anchors

    labels = {a.semantic_label for a in anchors}
    assert "keel-like" in labels
    assert "sheer-like" in labels
    assert "beam-max" in labels


def test_detect_anchors_is_deterministic_for_same_geometry():
    geom = _make_test_hull_geometry()
    a1 = detect_anchors(geom)
    a2 = detect_anchors(geom)

    # Deterministic ids and ordering are not guaranteed, but the UUID sets should match.
    u1 = {a.uuid for a in a1}
    u2 = {a.uuid for a in a2}
    assert u1 == u2

