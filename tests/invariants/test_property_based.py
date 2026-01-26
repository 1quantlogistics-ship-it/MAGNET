"""
tests/invariants/test_property_based.py

Phase 1 (Geometry Stability): property-based invariant tests.

This file is intentionally safe to include even when Hypothesis is not installed:
it will be skipped instead of failing import-time.
"""

from __future__ import annotations

import math

import pytest

hypothesis = pytest.importorskip("hypothesis", reason="hypothesis not installed")

from hypothesis import given, settings, strategies as st  # noqa: E402


@st.composite
def box_hull_inputs(draw):
    """
    Generate stable, valid dimensions for a simple box-like hull.
    """
    loa = draw(st.floats(min_value=5.0, max_value=120.0, allow_nan=False, allow_infinity=False))
    beam = draw(
        st.floats(
            min_value=max(0.5, loa * 0.05),
            max_value=max(1.0, loa * 0.30),
            allow_nan=False,
            allow_infinity=False,
        )
    )
    depth = draw(
        st.floats(
            min_value=max(0.8, beam * 0.30),
            max_value=max(1.2, beam * 1.50),
            allow_nan=False,
            allow_infinity=False,
        )
    )
    draft = draw(
        st.floats(
            min_value=max(0.05, depth * 0.10),
            max_value=depth * 0.95,
            allow_nan=False,
            allow_infinity=False,
        )
    )
    return float(loa), float(beam), float(depth), float(draft)


def _box_sections_resources(*, loa: float, beam: float, depth: float) -> dict:
    """
    Build a simple "box-like" hull using three constant half-sections.

    IMPORTANT: In MAGNET's design-language compiler, `geometry.section.points`
    represent an OPEN half-breadth curve y(z) (keel->deck), not a closed polygon.
    """
    hb = float(beam) / 2.0
    pts = [[0.0, 0.0], [hb, 0.05], [hb, 1.0], [hb, float(depth)]]
    return {
        "s0": {"_type": "geometry.section", "_id": "s0", "station": 0.0, "body_id": "main", "points": pts},
        "s1": {"_type": "geometry.section", "_id": "s1", "station": 0.5, "body_id": "main", "points": pts},
        "s2": {"_type": "geometry.section", "_id": "s2", "station": 1.0, "body_id": "main", "points": pts},
    }


class TestPhysicsInvariants:
    """
    Hydrostatics must not produce NaN/inf for valid simple hulls.
    """

    @given(box_hull_inputs())
    @settings(max_examples=25, deadline=None)
    def test_geometry_hydrostatics_is_finite(self, dims):
        loa, beam, depth, draft = dims

        from magnet.kernel.stdlib.compiler import compile_to_geometry
        from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry

        resources = _box_sections_resources(loa=loa, beam=beam, depth=depth)
        geo = compile_to_geometry(
            {
                "design_id": "HYP_BOX",
                "hull": {"loa": loa},
                "geometry_intent": {"surface_definition": "smooth"},
                "resources": resources,
            }
        )
        hs = compute_hydrostatics_from_geometry(geo, draft=float(draft))

        # Displacement should be finite and non-negative.
        assert math.isfinite(float(hs.displacement_kg))
        assert float(hs.displacement_kg) >= 0.0

        # Waterplane area should be finite and non-negative.
        assert math.isfinite(float(hs.waterplane_area_m2))
        assert float(hs.waterplane_area_m2) >= 0.0


class TestTransactionInvariants:
    """
    Transactions must be atomic (no partial writes survive rollback).
    """

    @given(
        st.floats(min_value=5.0, max_value=120.0, allow_nan=False, allow_infinity=False),
        st.floats(min_value=1.0, max_value=30.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=25, deadline=None)
    def test_rollback_restores_prior_state(self, loa, beam):
        from magnet.core.design_state import DesignState
        from magnet.core.state_manager import StateManager

        sm = StateManager(DesignState())
        before = sm.to_dict()

        sm.begin_transaction()
        try:
            sm.set("hull.loa", float(loa), "hypothesis")
            sm.set("hull.beam", float(beam), "hypothesis")
            raise ValueError("force rollback")
        except ValueError:
            sm.rollback()

        after = sm.to_dict()
        assert after == before

