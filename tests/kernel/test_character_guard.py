from magnet.hull_gen.generator import HullGenerator, GeneratorConfig
from magnet.hull_gen.parameters import (
    DeadriseProfile,
    FormCoefficients,
    HullDefinition,
    HullFeatures,
    MainDimensions,
)
from magnet.kernel.character_guard import (
    CharacterPreservationConfig,
    extract_character_signature,
    evaluate_character_guard,
)


def _make_geom(*, hull_id: str, deadrise_midship: float) -> object:
    gen = HullGenerator(config=GeneratorConfig(num_sections=11, points_per_section=25))
    definition = HullDefinition(
        hull_id=hull_id,
        hull_name=hull_id,
        dimensions=MainDimensions(
            loa=20.0,
            lwl=19.0,
            beam_max=4.8,
            beam_wl=4.8,
            depth=3.0,
            draft=1.2,
        ),
        coefficients=FormCoefficients(cb=0.50, cp=0.65, cm=0.80, cwp=0.75, lcb=0.52),
        deadrise=DeadriseProfile.warped(14.0, float(deadrise_midship), 25.0),
        features=HullFeatures(chine_count=1),
    )
    return gen.generate(definition)


def test_character_guard_pass_for_small_geometry_change():
    g0 = _make_geom(hull_id="cg", deadrise_midship=18.0)
    g1 = _make_geom(hull_id="cg", deadrise_midship=19.0)  # small tweak

    base = extract_character_signature(g0)
    cand = extract_character_signature(g1)
    cfg = CharacterPreservationConfig(soft_limit=0.50, hard_limit=1.0)  # make pass likely

    res = evaluate_character_guard(baseline=base, candidate=cand, config=cfg)
    assert res.decision == "pass"
    assert res.predicted_drift >= 0.0


def test_character_guard_rejects_when_drift_exceeds_hard_limit():
    g0 = _make_geom(hull_id="cg2", deadrise_midship=10.0)
    g1 = _make_geom(hull_id="cg2", deadrise_midship=40.0)  # big change

    base = extract_character_signature(g0)
    cand = extract_character_signature(g1)
    # Tight limits so a major bottom-angle change trips the guard.
    cfg = CharacterPreservationConfig(soft_limit=0.05, hard_limit=0.20)

    res = evaluate_character_guard(baseline=base, candidate=cand, config=cfg)
    assert "deadrise_midship_deg" in base.metrics and "deadrise_midship_deg" in cand.metrics
    assert res.decision in ("needs_confirmation", "reject_rewrite")
    assert res.predicted_drift > cfg.soft_limit

