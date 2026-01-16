"""
Hull Synthesis Integration Tests

Tests the hull synthesis engine as a kernel primitive.
Verifies propose→validate→mutate loop and fallback paths.

Module 62.4: Uses refinable_write_context for transaction-wrapped writes.
"""

import pytest
from magnet.core.state_manager import StateManager, MISSING, InvalidPathError
from tests.conftest import refinable_write_context
from magnet.kernel.conductor import Conductor
from magnet.kernel.synthesis import (
    HullSynthesizer,
    SynthesisRequest,
    SynthesisProposal,
    SynthesisResult,
    ConvergenceCriteria,
    TerminationReason,
)
from magnet.kernel.synthesis_lock import SynthesisLock, SynthesisLockError
from magnet.kernel.synthesis_fallback import create_fallback_proposal, FallbackMode
from magnet.kernel.priors.hull_families import HullFamily, get_family_prior


class TestHullFamilyPriors:
    """Tests for hull family priors."""

    def test_all_families_have_priors(self):
        """All hull families have defined priors."""
        for family in HullFamily:
            prior = get_family_prior(family)
            assert prior is not None
            assert "lwl_beam" in prior
            assert "cb" in prior
            assert "froude_design" in prior

    def test_patrol_prior_values(self):
        """Patrol family has reasonable values."""
        prior = get_family_prior(HullFamily.PATROL)
        assert prior["lwl_beam"] == 5.5  # L/B ratio
        assert prior["cb"] == 0.45  # Block coefficient
        # Patrol craft target semi-planing regime (Fn ~0.55-1.0+)
        assert prior["froude_design"] > 0.7

    def test_workboat_prior_values(self):
        """Workboat family has displacement-type values."""
        prior = get_family_prior(HullFamily.WORKBOAT)
        assert prior["lwl_beam"] < 5.0  # Fuller beam
        assert prior["cb"] > 0.5  # Higher block coefficient
        # Workboats target semi-displacement regime (Fn ~0.35-0.55)
        assert 0.35 <= prior["froude_design"] <= 0.55


class TestSynthesisRequest:
    """Tests for SynthesisRequest contract."""

    def test_valid_request(self):
        """Valid request creates successfully."""
        req = SynthesisRequest(
            hull_family=HullFamily.PATROL,
            max_speed_kts=35.0,
        )
        assert req.hull_family == HullFamily.PATROL
        assert req.max_speed_kts == 35.0
        assert req.max_iterations == 15  # Default

    def test_request_with_constraints(self):
        """Request with optional constraints."""
        req = SynthesisRequest(
            hull_family=HullFamily.WORKBOAT,
            max_speed_kts=12.0,
            loa_m=25.0,
            range_nm=500.0,
            gm_min_m=0.5,
        )
        assert req.loa_m == 25.0
        assert req.range_nm == 500.0
        assert req.gm_min_m == 0.5

    def test_invalid_speed_rejected(self):
        """Zero or negative speed is rejected."""
        with pytest.raises(ValueError, match="max_speed_kts must be positive"):
            SynthesisRequest(
                hull_family=HullFamily.PATROL,
                max_speed_kts=0,
            )

    def test_invalid_iterations_rejected(self):
        """Zero iterations is rejected."""
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            SynthesisRequest(
                hull_family=HullFamily.PATROL,
                max_speed_kts=30.0,
                max_iterations=0,
            )


class TestSynthesisProposal:
    """Tests for SynthesisProposal contract."""

    def test_complete_proposal(self):
        """Complete proposal is valid."""
        proposal = SynthesisProposal(
            lwl_m=23.75,
            beam_m=5.0,
            draft_m=1.5,
            depth_m=2.4,
            cb=0.45,
            cp=0.62,
            cm=0.82,
            cwp=0.72,
            displacement_m3=80.0,
            confidence=0.8,
            iteration=3,
            source="mutated",
        )
        assert proposal.is_complete
        assert proposal.confidence == 0.8

    def test_state_dict_output(self):
        """Proposal converts to state dict correctly."""
        proposal = SynthesisProposal(
            lwl_m=25.0,
            beam_m=5.5,
            draft_m=1.6,
            depth_m=2.56,
            cb=0.45,
            cp=0.62,
            cm=0.82,
            cwp=0.72,
            displacement_m3=99.0,
            confidence=0.7,
            iteration=0,
            source="prior",
        )
        state_dict = proposal.to_state_dict()
        assert state_dict["hull.lwl"] == 25.0
        assert state_dict["hull.beam"] == 5.5
        assert state_dict["hull.cb"] == 0.45
        assert state_dict["hull.depth"] == 2.56
        assert "hull.displacement_m3" in state_dict


class TestSynthesisLock:
    """Tests for synthesis lock mechanism."""

    def test_acquire_release(self):
        """Lock can be acquired and released."""
        sm = StateManager()
        lock = SynthesisLock(sm)

        assert not lock.is_locked
        lock.acquire("test")
        assert lock.is_locked
        assert lock.owner == "test"
        lock.release("test")
        assert not lock.is_locked

    def test_double_acquire_fails(self):
        """Cannot acquire lock twice."""
        sm = StateManager()
        lock = SynthesisLock(sm)

        lock.acquire("owner1")
        with pytest.raises(SynthesisLockError, match="cannot acquire"):
            lock.acquire("owner2")

    def test_wrong_owner_release_fails(self):
        """Cannot release lock with wrong owner."""
        sm = StateManager()
        lock = SynthesisLock(sm)

        lock.acquire("owner1")
        with pytest.raises(SynthesisLockError, match="owned by owner1"):
            lock.release("owner2")

    def test_context_manager(self):
        """Lock works as context manager."""
        sm = StateManager()
        lock = SynthesisLock(sm)

        with lock.exclusive_access("test"):
            assert lock.is_locked
            assert lock.owner == "test"

        assert not lock.is_locked

    def test_write_hull_params(self):
        """Lock allows writing hull params."""
        sm = StateManager()
        lock = SynthesisLock(sm)

        with lock.exclusive_access("test"):
            params = {
                "hull.lwl": 25.0,
                "hull.beam": 5.0,
                "hull.draft": 1.5,
            }
            lock.write_hull_params(params, "test")

        assert sm.get("hull.lwl") == 25.0
        assert sm.get("hull.beam") == 5.0


class TestFallbackPath:
    """Tests for synthesis fallback mechanism."""

    def test_fallback_creates_usable_hull(self):
        """Fallback always produces usable hull."""
        fallback = create_fallback_proposal(
            hull_family=HullFamily.WORKBOAT,
            max_speed_kts=12.0,
            reason="Test fallback",
        )
        assert fallback.is_complete
        assert fallback.lwl_m > 0
        assert fallback.beam_m > 0
        assert fallback.confidence == 0.3  # Low confidence
        assert fallback.mode == FallbackMode.ESTIMATOR_ONLY

    def test_fallback_with_loa_constraint(self):
        """Fallback respects LOA constraint."""
        fallback = create_fallback_proposal(
            hull_family=HullFamily.FERRY,
            max_speed_kts=15.0,
            loa_m=30.0,
            reason="LOA constrained",
        )
        # LWL should be ~95% of LOA
        assert 28.0 < fallback.lwl_m < 30.0


class TestHullSynthesizer:
    """Tests for the main hull synthesizer."""

    def test_synthesizer_instantiation(self):
        """Synthesizer can be instantiated."""
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)
        assert synthesizer is not None

    def test_synthesis_from_request(self):
        """Synthesis produces result from request."""
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        request = SynthesisRequest(
            hull_family=HullFamily.PATROL,
            max_speed_kts=35.0,
            max_iterations=5,
        )

        result = synthesizer.synthesize(request)

        assert result is not None
        assert result.is_usable
        assert result.proposal.is_complete
        assert result.iterations_used <= 5

    def test_synthesis_with_loa_constraint(self):
        """Synthesis respects LOA constraint."""
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        request = SynthesisRequest(
            hull_family=HullFamily.WORKBOAT,
            max_speed_kts=12.0,
            loa_m=20.0,
            max_iterations=3,
        )

        result = synthesizer.synthesize(request)

        # LWL should be ~95% of LOA
        assert result.proposal.lwl_m < 20.0
        assert result.proposal.lwl_m > 18.0

    def test_loa_locked_prevents_lwl_scaling_in_displacement_clamp(self):
        """
        Regression: when loa_is_hard_constraint=True, displacement bounds clamping must
        NOT scale LWL (it must remain ~0.95×LOA).
        """
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        request = SynthesisRequest(
            hull_family=HullFamily.WORKBOAT,
            max_speed_kts=12.0,
            loa_m=20.0,
            loa_is_hard_constraint=True,
            max_iterations=1,
        )

        # Build an intentionally oversized proposal so displacement > family max,
        # triggering the displacement clamp path in _clamp_to_bounds().
        lwl = 0.95 * 20.0
        cb = 0.60
        beam = 20.0
        draft = 5.0
        displacement_m3 = lwl * beam * draft * cb

        proposal = SynthesisProposal(
            lwl_m=lwl,
            beam_m=beam,
            draft_m=draft,
            depth_m=8.0,
            cb=cb,
            cp=0.68,
            cm=0.88,
            cwp=0.78,
            displacement_m3=displacement_m3,
            confidence=0.5,
            iteration=0,
            source="test",
            loa_m=20.0,
        )

        clamped, _warnings = synthesizer._clamp_to_bounds(proposal, HullFamily.WORKBOAT, request=request)
        assert clamped.lwl_m == pytest.approx(lwl, abs=1e-6)

    def test_synthesis_iterates_and_does_not_fallback(self):
        """
        Regression: synthesis loop should iterate without throwing and falling back.

        We force non-convergence by setting min_score unrealistically high, which
        ensures the loop runs until max_iterations (exercising _mutate()).
        """
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        criteria = ConvergenceCriteria(min_score=1e9)  # impossible to reach
        request = SynthesisRequest(
            hull_family=HullFamily.PATROL,
            max_speed_kts=35.0,
            loa_m=20.0,
            crew_count=8,
            range_nm=300.0,
            max_iterations=5,
            convergence_criteria=criteria,
        )

        result = synthesizer.synthesize(request)
        assert result is not None
        assert result.is_usable
        assert not result.is_fallback
        assert result.termination == TerminationReason.MAX_ITERATIONS
        assert result.iterations_used == 5

    def test_displacement_estimate_realistic_for_20m_patrol(self):
        """
        P0 regression: LOA-based lightship scaling should produce an engineering-realistic
        displacement estimate for a normal patrol craft (no longer ~4m³).
        """
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        request = SynthesisRequest(
            hull_family=HullFamily.PATROL,
            max_speed_kts=35.0,
            loa_m=20.0,
            crew_count=8,
            range_nm=300.0,
        )

        disp_m3, _warnings = synthesizer._estimate_required_displacement_m3(request)
        assert disp_m3 is not None
        assert 25.0 <= disp_m3 <= 50.0, f"Expected 25-50 m³, got {disp_m3:.1f} m³"

    def test_normal_patrol_not_clamped_to_family_min(self):
        """
        P0 regression: Normal 20m patrol missions should not be forced up to the
        family minimum displacement via clamping.
        """
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        request = SynthesisRequest(
            hull_family=HullFamily.PATROL,
            max_speed_kts=35.0,
            loa_m=20.0,
            crew_count=8,
            range_nm=300.0,
            max_iterations=1,
        )

        result = synthesizer.synthesize(request)
        assert result is not None
        assert result.is_usable

        # Specifically ensure the displacement target was not clamped.
        assert not any(("disp_target" in w and "clamped" in w) for w in (result.warnings or [])), (
            f"Unexpected displacement clamp warnings: {result.warnings}"
        )

    def test_displacement_estimate_scales_with_loa(self):
        """P0 regression: larger LOA should imply larger lightship → larger displacement estimate."""
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        req_10 = SynthesisRequest(hull_family=HullFamily.PATROL, max_speed_kts=25.0, loa_m=10.0)
        req_20 = SynthesisRequest(hull_family=HullFamily.PATROL, max_speed_kts=25.0, loa_m=20.0)
        req_30 = SynthesisRequest(hull_family=HullFamily.PATROL, max_speed_kts=25.0, loa_m=30.0)

        disp10, _ = synthesizer._estimate_required_displacement_m3(req_10)
        disp20, _ = synthesizer._estimate_required_displacement_m3(req_20)
        disp30, _ = synthesizer._estimate_required_displacement_m3(req_30)

        assert disp10 is not None and disp20 is not None and disp30 is not None
        assert disp30 > disp20 > disp10, f"Expected disp30>disp20>disp10, got {disp30}, {disp20}, {disp10}"

    def test_catamaran_demihull_beam_not_extreme(self):
        """
        P0 regression: catamaran beam semantics should not yield absurd demihull widths.

        Note: hull_gen currently derives demihull_beam ≈ beam_max / 4 for cats; we enforce
        that implied demihull beam stays in a sane range for a mid-size cat.
        """
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        request = SynthesisRequest(
            hull_family=HullFamily.CATAMARAN,
            max_speed_kts=35.0,
            loa_m=40.0,
            crew_count=12,
            range_nm=500.0,
            max_iterations=1,
        )

        result = synthesizer.synthesize(request)
        assert result is not None
        assert result.is_usable

        demihull_beam = result.proposal.beam_m / 4.0
        assert 1.5 <= demihull_beam <= 3.5, (
            f"Demihull beam {demihull_beam:.2f}m out of expected range for 40m cat"
        )


class TestConductorIntegration:
    """Tests for conductor integration with synthesis."""

    def test_hull_exists_check(self):
        """Conductor correctly detects hull existence."""
        sm = StateManager()
        conductor = Conductor(sm)

        assert not conductor._hull_exists()

        # Module 62.4: Wrap refinable writes in transaction
        with refinable_write_context(sm):
            sm.set("hull.lwl", 25.0, "test")
            sm.set("hull.beam", 5.0, "test")
            sm.set("hull.draft", 1.5, "test")

        assert conductor._hull_exists()

    def test_build_synthesis_request(self):
        """Conductor builds synthesis request from state."""
        sm = StateManager()
        conductor = Conductor(sm)

        # Without max_speed_kts, should return None
        request = conductor._build_synthesis_request()
        assert request is None

        # Module 62.4: Wrap refinable writes in transaction
        with refinable_write_context(sm):
            sm.set("mission.max_speed_kts", 30.0, "test")
            sm.set("hull.hull_type", "patrol", "test")
            sm.set("mission.crew_berthed", 8, "test")
            sm.set("mission.passengers", 20, "test")
            sm.set("mission.cargo_capacity_mt", 10.0, "test")

        request = conductor._build_synthesis_request()
        assert request is not None
        assert request.hull_family == HullFamily.PATROL
        assert request.max_speed_kts == 30.0
        assert request.crew_count == 28  # 8 crew + 20 passengers
        assert request.payload_kg == pytest.approx(10000.0, abs=1e-6)

    def test_run_hull_synthesis(self):
        """Conductor runs synthesis and writes to state."""
        sm = StateManager()
        conductor = Conductor(sm)

        # Module 62.4: Wrap refinable writes in transaction
        with refinable_write_context(sm):
            sm.set("mission.max_speed_kts", 25.0, "test")
            sm.set("hull.hull_type", "workboat", "test")

        result = conductor._run_hull_synthesis()

        assert result is not None
        assert result.is_usable

        # Check hull was written to state
        assert sm.get("hull.lwl") > 0
        assert sm.get("hull.beam") > 0
        assert sm.get("hull.draft") > 0


class TestStateManagerPathStrict:
    """Tests for path-strict StateManager features."""

    def test_missing_sentinel(self):
        """MISSING sentinel is distinct from None."""
        sm = StateManager()

        # Unset field returns None via get()
        assert sm.get("hull.lwl") is None

        # But get_strict() navigates to dataclass field with None default
        # (because HullState().lwl = None)
        val = sm.get_strict("hull.lwl")
        assert val is None  # Dataclass field exists with None default

    def test_invalid_path_error(self):
        """Invalid paths raise InvalidPathError."""
        sm = StateManager()

        with pytest.raises(InvalidPathError, match="Unknown path"):
            sm.get_strict("hull.invalid_xyz")

    def test_exists_method(self):
        """exists() correctly checks path presence."""
        sm = StateManager()

        # Dataclass fields with None default "exist"
        assert sm.exists("hull.lwl")  # HullState().lwl = None

        # Invalid paths raise error
        with pytest.raises(InvalidPathError):
            sm.exists("hull.nonexistent")


class TestConvergenceCriteria:
    """Tests for convergence criteria."""

    def test_default_criteria(self):
        """Default criteria have reasonable values."""
        criteria = ConvergenceCriteria()
        assert criteria.min_validators_passed == 2
        assert criteria.min_score == 85.0
        assert criteria.gm_margin_m == 0.1

    def test_convergence_check(self):
        """Convergence is correctly evaluated."""
        criteria = ConvergenceCriteria(
            min_validators_passed=1,
            min_score=80.0,
        )

        converged, reason = criteria.is_converged(
            score=90.0,
            validators_passed=2,
            max_finding_severity="warning",
            gm_actual=0.7,
            gm_required=0.5,
            score_history=[85.0, 88.0, 90.0],
        )

        assert converged
        assert "met" in reason.lower() or "plateau" in reason.lower()

    def test_not_converged_low_score(self):
        """Low score prevents convergence."""
        criteria = ConvergenceCriteria(min_score=90.0)

        converged, reason = criteria.is_converged(
            score=75.0,
            validators_passed=2,
            max_finding_severity="info",
            gm_actual=0.7,
            gm_required=0.5,
            score_history=[70.0, 72.0, 75.0],
        )

        assert not converged
        assert "score" in reason.lower()


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
