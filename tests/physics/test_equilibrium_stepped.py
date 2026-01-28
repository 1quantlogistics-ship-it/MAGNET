"""
T5.8 / E0.4 regression:
Newton-Raphson can oscillate near stepped/discontinuous waterplane behavior.

This test forces a "bad local derivative" situation (wrong-sign slope) and
asserts the solver still converges by rejecting unsafe Newton proposals and
falling back to bracket bisection.
"""

import pytest

from magnet.physics.equilibrium import solve_equilibrium_draft


def test_equilibrium_solver_rejects_wrong_sign_newton_step_and_converges():
    import magnet.physics.equilibrium as eq

    # Root at 1.0m. Residual is smooth, but the derivative surrogate is wrong-sign
    # above the root, which would drive Newton away unless rejected.
    def _fake_eval(_geometry, draft_m, target_displacement_mt, seawater_density):
        _ = target_displacement_mt
        _ = seawater_density
        x = float(draft_m)
        residual = x - 1.0
        disp = 0.0
        # Wrong-sign derivative on one side (mimics stepped/discontinuous Aw(T) behavior).
        d = 1.0 if x < 1.0 else -1.0
        return float(residual), float(disp), float(d)

    orig = eq._eval_residual
    eq._eval_residual = _fake_eval
    try:
        sol = solve_equilibrium_draft(
            geometry=None,  # ignored by fake evaluator
            target_displacement_mt=1.0,
            draft_guess_m=1.6,
            depth_m=3.0,
            tol_residual_mt=1e-6,
            tol_draft_m=1e-8,
            max_iter=60,
        )
        assert sol.converged is True
        assert sol.draft_m == pytest.approx(1.0, abs=1e-6)
    finally:
        eq._eval_residual = orig

