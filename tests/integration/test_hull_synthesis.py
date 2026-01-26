"""
Hull Synthesis Integration Tests (Enum-free).

Phase 3 (Enum Deletion):
- No legacy family/type priors
- No enum-driven synthesis request
- Use geometry-based synthesis request only
"""

import pytest

from magnet.core.state_manager import StateManager
from tests.conftest import refinable_write_context

from magnet.kernel.conductor import Conductor
from magnet.kernel.synthesis import HullSynthesizer, GeometrySynthesisRequest
from magnet.kernel.synthesis_lock import SynthesisLock, SynthesisLockError


class TestSynthesisLock:
    def test_acquire_release(self):
        sm = StateManager()
        lock = SynthesisLock(sm)

        assert not lock.is_locked
        lock.acquire("test")
        assert lock.is_locked
        assert lock.owner == "test"
        lock.release("test")
        assert not lock.is_locked

    def test_double_acquire_fails(self):
        sm = StateManager()
        lock = SynthesisLock(sm)

        lock.acquire("owner1")
        with pytest.raises(SynthesisLockError, match="cannot acquire"):
            lock.acquire("owner2")

    def test_wrong_owner_release_fails(self):
        sm = StateManager()
        lock = SynthesisLock(sm)

        lock.acquire("owner1")
        with pytest.raises(SynthesisLockError, match="owned by owner1"):
            lock.release("owner2")


class TestGeometrySynthesisRequest:
    def test_valid_request(self):
        req = GeometrySynthesisRequest(max_speed_kts=30.0, loa_m=20.0, max_iterations=5)
        assert req.max_speed_kts == 30.0
        assert req.loa_m == 20.0
        assert req.max_iterations == 5

    def test_invalid_speed_rejected(self):
        with pytest.raises(ValueError, match="max_speed_kts must be positive"):
            GeometrySynthesisRequest(max_speed_kts=0.0)

    def test_invalid_iterations_rejected(self):
        with pytest.raises(ValueError, match="max_iterations must be >= 1"):
            GeometrySynthesisRequest(max_speed_kts=30.0, max_iterations=0)


class TestHullSynthesizer:
    def test_synthesizer_instantiation(self):
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)
        assert synthesizer is not None

    def test_synthesis_from_geometry_request(self):
        sm = StateManager()
        synthesizer = HullSynthesizer(executor=None, state_manager=sm)

        req = GeometrySynthesisRequest(max_speed_kts=35.0, loa_m=20.0, max_iterations=5)
        result = synthesizer.synthesize_from_geometry(req)
        assert result is not None
        assert result.is_usable
        assert result.proposal.is_complete
        assert result.iterations_used <= 5


class TestConductorIntegration:
    def test_build_geometry_synthesis_request(self):
        sm = StateManager()
        conductor = Conductor(sm)

        # Without max_speed_kts, should return None
        assert conductor._build_geometry_synthesis_request() is None

        with refinable_write_context(sm):
            sm.set("mission.max_speed_kts", 30.0, "test")
            sm.set("hull.loa", 20.0, "test")
            sm.set("mission.crew_berthed", 8, "test")
            sm.set("mission.passengers", 20, "test")
            sm.set("mission.cargo_capacity_mt", 10.0, "test")

        req = conductor._build_geometry_synthesis_request()
        assert req is not None
        assert req.max_speed_kts == 30.0
        assert req.loa_m == 20.0
        assert req.crew_count == 28
        assert req.payload_kg == pytest.approx(10000.0, abs=1e-6)

    def test_run_hull_synthesis_writes_state(self):
        sm = StateManager()
        conductor = Conductor(sm)

        with refinable_write_context(sm):
            sm.set("mission.max_speed_kts", 25.0, "test")
            sm.set("hull.loa", 20.0, "test")

        result = conductor._run_hull_synthesis()
        assert result is not None
        assert result.is_usable

        # Hull was written to state by the synthesis lock write path.
        assert float(sm.get("hull.lwl") or 0.0) > 0
        assert float(sm.get("hull.beam") or 0.0) > 0
        assert float(sm.get("hull.draft") or 0.0) > 0

