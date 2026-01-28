"""
TASK-019: Integrated GZ Cross-Curves (Future Truth) — confidence behavior
"""

from magnet.stability.gz_curve import GZCurveCalculator


def test_confidence_degrades_with_heel():
    calc = GZCurveCalculator()
    res = calc.calculate(
        gm_m=0.8,
        bm_m=3.0,
        beam_m=6.0,
        freeboard_m=1.2,
        max_heel_deg=80.0,
        heel_step_deg=20.0,
    )
    # confidence at 0 should be >= confidence at 60
    c0 = next(p.stability_confidence for p in res.curve if p.heel_deg == 0.0)
    c60 = next(p.stability_confidence for p in res.curve if p.heel_deg == 60.0)
    assert c0 > c60

