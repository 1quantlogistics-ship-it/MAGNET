"""
TASK-017: Remove Type Factors from Weight Estimation
"""

from magnet.weight.estimators.hull import HullStructureEstimator, get_hull_factor_from_geometry


def test_multi_body_penalty_independent_of_name():
    # The multiplier is purely geometric: body_count drives penalty.
    mono = get_hull_factor_from_geometry(body_count=1, lb_ratio=6.0, froude_number=0.3)
    multi = get_hull_factor_from_geometry(body_count=2, lb_ratio=6.0, froude_number=0.3)
    assert mono == 1.0
    assert multi > mono


def test_estimate_uses_geometry_factor():
    est = HullStructureEstimator()
    base = est.estimate(
        lwl=20.0,
        beam=4.0,
        depth=2.5,
        cb=0.55,
        body_count=1,
        froude_number=0.35,
        material="aluminum_5083",
        service_type="commercial",
    )
    multi = est.estimate(
        lwl=20.0,
        beam=4.0,
        depth=2.5,
        cb=0.55,
        body_count=2,
        froude_number=0.35,
        material="aluminum_5083",
        service_type="commercial",
    )
    base_mt = sum(i.weight_kg for i in base) / 1000.0
    multi_mt = sum(i.weight_kg for i in multi) / 1000.0
    assert multi_mt > base_mt

