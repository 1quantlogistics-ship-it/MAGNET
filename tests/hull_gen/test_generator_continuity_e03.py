"""
Emergency stabilization tests for C1 smoothing in hull generator.

Task IDs:
- E0.3 (Emergency: remove C1 kinks in parametric generator)
"""

from __future__ import annotations

import math

from magnet.hull_gen.generator import HullGenerator
from magnet.hull_gen.parameters import FormCoefficients, HullDefinition, HullFeatures, MainDimensions


def _finite_diff_slope(f, x: float, h: float) -> float:
    return float(f(x + h) - f(x - h)) / (2.0 * float(h))


def test_beam_factor_is_c1_around_key_transitions():
    gen = HullGenerator()

    definition = HullDefinition(
        dimensions=MainDimensions(
            loa=22.0,
            lwl=20.0,
            lpp=19.0,
            beam_max=5.0,
            beam_wl=4.8,
            draft=1.5,
            depth=2.2,
        ),
        coefficients=FormCoefficients(
            cb=0.40,
            cp=0.60,
            cm=0.70,
            cwp=0.72,
            lcb=0.45,
            lcf=0.48,
        ),
        features=HullFeatures(
            bow_entrance_deg=20.0,
            transom_width_fraction=0.85,
        ),
    )

    def f(x: float) -> float:
        return float(gen._get_beam_factor_at_station(definition, float(x)))

    # Check C1 behavior (no slope jumps) at the historical kink points.
    boundaries = [0.1, float(definition.coefficients.lcb), 0.9]
    h = 1e-4

    for b in boundaries:
        # One-sided slopes at the boundary.
        f0 = f(b)
        d_left = (f0 - f(b - h)) / h
        d_right = (f(b + h) - f0) / h

        assert math.isfinite(d_left)
        assert math.isfinite(d_right)

        # With smoothing, slopes should match closely (C1).
        assert abs(d_left - d_right) < 0.25
