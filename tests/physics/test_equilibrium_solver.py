from magnet.kernel.stdlib.compiler import compile_to_geometry
from magnet.physics.equilibrium import solve_equilibrium_draft
from magnet.physics.geometry_hydrostatics import compute_hydrostatics_from_geometry
from magnet.physics.validators import EquilibriumDraftValidator


class MockStateManager:
    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value, source=None):
        self._values[key] = value


def _box_sections_resources(*, loa: float, beam: float, depth: float) -> dict:
    """
    Build a simple "box-like" hull using three constant half-sections.

    IMPORTANT: In MAGNET's design-language compiler, `geometry.section.points`
    represent an OPEN half-breadth curve y(z) (keel->deck), not a closed polygon.
    So for a "box" we approximate y(z) as:
      - y=0 at keel (z=0)
      - y=beam/2 for z>0 (vertical sides)
    """
    hb = beam / 2.0
    pts = [[0.0, 0.0], [hb, 0.05], [hb, 1.0], [hb, depth]]
    return {
        "s0": {"_type": "geometry.section", "_id": "s0", "station": 0.0, "body_id": "main", "points": pts},
        "s1": {"_type": "geometry.section", "_id": "s1", "station": 0.5, "body_id": "main", "points": pts},
        "s2": {"_type": "geometry.section", "_id": "s2", "station": 1.0, "body_id": "main", "points": pts},
    }


def test_solve_equilibrium_draft_recovers_known_draft():
    loa = 20.0
    beam = 5.0
    depth = 3.0
    resources = _box_sections_resources(loa=loa, beam=beam, depth=depth)
    geo = compile_to_geometry(
        {"design_id": "TEST", "hull": {"loa": loa}, "geometry_intent": {"surface_definition": "smooth"}, "resources": resources}
    )

    known_draft = 1.0
    hs = compute_hydrostatics_from_geometry(geo, draft=known_draft)
    target_mt = hs.displacement_kg / 1000.0

    sol = solve_equilibrium_draft(
        geometry=geo,
        target_displacement_mt=target_mt,
        draft_guess_m=0.5,
        depth_m=depth,
    )
    assert sol.converged is True
    assert abs(sol.draft_m - known_draft) < 1e-3


def test_solve_equilibrium_draft_handles_bad_derivative_by_bisection():
    """
    Regression (E0.4): if Aw(T) produces an unusable derivative surrogate,
    the solver must still converge via bracketing/bisection.
    """
    loa = 20.0
    beam = 5.0
    depth = 3.0
    resources = _box_sections_resources(loa=loa, beam=beam, depth=depth)
    geo = compile_to_geometry(
        {"design_id": "TEST", "hull": {"loa": loa}, "geometry_intent": {"surface_definition": "smooth"}, "resources": resources}
    )

    known_draft = 1.0
    hs = compute_hydrostatics_from_geometry(geo, draft=known_draft)
    target_mt = hs.displacement_kg / 1000.0

    # Monkeypatch the residual evaluator to return a near-zero derivative to
    # force bisection fallback. This stays in-module and avoids making a
    # pathological geometry just to trigger the code path.
    import magnet.physics.equilibrium as eq

    orig = eq._eval_residual

    def _wrapped(geometry, draft_m, target_displacement_mt, seawater_density):
        r, disp, d = orig(geometry, draft_m, target_displacement_mt, seawater_density)
        return r, disp, 0.0  # unusable derivative

    eq._eval_residual = _wrapped
    try:
        sol = solve_equilibrium_draft(
            geometry=geo,
            target_displacement_mt=target_mt,
            draft_guess_m=0.2,
            depth_m=depth,
            max_iter=40,
        )
        assert sol.converged is True
        assert abs(sol.draft_m - known_draft) < 2e-3
    finally:
        eq._eval_residual = orig


def test_equilibrium_validator_auto_apply_recomputes_hydrostatics():
    loa = 20.0
    beam = 5.0
    depth = 3.0
    resources = _box_sections_resources(loa=loa, beam=beam, depth=depth)
    # Ensure surface intent is explicit for compilation.
    geo = compile_to_geometry(
        {"design_id": "TEST", "hull": {"loa": loa}, "geometry_intent": {"surface_definition": "smooth"}, "resources": resources}
    )

    known_draft = 1.0
    hs = compute_hydrostatics_from_geometry(geo, draft=known_draft)
    target_mt = hs.displacement_kg / 1000.0

    sm = MockStateManager(
        {
            "design_id": "TEST",
            "resources": resources,
            "geometry_intent.surface_definition": "smooth",
            "hull.loa": loa,
            "hull.lwl": loa,
            "hull.beam": beam,
            "hull.depth": depth,
            "hull.draft": 0.5,
            "hull.auto_equilibrate_draft": True,
            # Provide the equilibrium target via weight (lightship-only equilibrium)
            "weight.lightship_weight_mt": target_mt,
        }
    )

    res = EquilibriumDraftValidator().validate(sm, {})
    assert res.passed is True

    # Draft was applied explicitly
    assert abs(float(sm.get("hull.draft")) - known_draft) < 1e-3

    # Hydrostatics were recomputed to match the new draft (not stale)
    disp_mt_out = float(sm.get("hull.displacement_mt") or 0.0)
    assert abs(disp_mt_out - target_mt) < 1e-2

