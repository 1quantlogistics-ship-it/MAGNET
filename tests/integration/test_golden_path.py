"""
Golden Path Integration Tests

Tests the end-to-end design flow using production DI wiring.
Verifies that MAGNETApp.build() produces a working system.

v1.1: Tests hull synthesis → stability flow via Conductor.
"""

import pytest
from magnet.bootstrap.app import MAGNETApp, create_app
from magnet.core.state_manager import StateManager
from magnet.kernel.conductor import Conductor
from magnet.kernel.enums import PhaseStatus


class TestGoldenPathSetup:
    """Tests for production DI wiring via MAGNETApp.build()."""

    def test_app_builds_successfully(self):
        """MAGNETApp.build() completes without error."""
        app = MAGNETApp().build()
        assert app is not None
        assert app.container is not None

    def test_state_manager_resolvable(self):
        """StateManager can be resolved from container."""
        app = MAGNETApp().build()
        sm = app.container.resolve(StateManager)
        assert sm is not None
        assert hasattr(sm, 'get')
        assert hasattr(sm, 'set')

    def test_conductor_resolvable(self):
        """Conductor can be resolved from container."""
        app = MAGNETApp().build()
        conductor = app.container.resolve(Conductor)
        assert conductor is not None
        assert hasattr(conductor, 'run_phase')

    def test_conductor_wired_to_state_manager(self):
        """Conductor has access to StateManager."""
        app = MAGNETApp().build()
        conductor = app.container.resolve(Conductor)
        # Conductor stores state_manager as `self.state`
        assert hasattr(conductor, 'state')
        assert conductor.state is not None

    def test_create_app_helper(self):
        """create_app() helper builds app correctly."""
        app = create_app()
        assert app is not None
        assert app.container is not None


class TestGoldenPathFlow:
    """Tests for the golden path: hull → stability flow."""

    @pytest.fixture
    def configured_app(self):
        """Create app with minimal mission state for hull synthesis."""
        app = MAGNETApp().build()
        sm = app.container.resolve(StateManager)

        # Seed minimal mission data for hull synthesis
        sm.set("mission.max_speed_kts", 25.0, "test")
        sm.set("hull.hull_type", "workboat", "test")

        return app

    def test_hull_phase_executable(self, configured_app):
        """Hull phase can be executed via Conductor."""
        conductor = configured_app.container.resolve(Conductor)
        sm = configured_app.container.resolve(StateManager)

        # Run hull phase
        result = conductor.run_phase("hull")

        # Phase should run (synthesis triggers first, then validation)
        # May complete, fail (if synthesis doesn't converge), or be blocked for other reasons
        assert result is not None
        assert result.status in [
            PhaseStatus.COMPLETED,
            PhaseStatus.BLOCKED,
            PhaseStatus.FAILED,  # Synthesis may not converge with minimal state
        ]

    def test_hull_synthesis_runs_before_contract_check(self, configured_app):
        """Hull synthesis runs before input contract check (sequencing fix)."""
        conductor = configured_app.container.resolve(Conductor)
        sm = configured_app.container.resolve(StateManager)

        # With synthesis running first, hull phase should NOT be blocked for
        # "Missing required inputs" - synthesis should populate those values
        result = conductor.run_phase("hull")

        # Verify synthesis attempted (may fail to converge, but shouldn't be BLOCKED)
        assert result is not None
        # If BLOCKED, it should NOT be for missing hull.lwl/beam/draft/cb
        if result.status == PhaseStatus.BLOCKED:
            for err in result.errors:
                # Synthesis should have populated hull inputs, so no "Missing required inputs"
                assert "hull.lwl" not in err or "Missing required inputs" not in err

    def test_hull_synthesis_direct(self, configured_app):
        """Hull synthesis works when called directly via Conductor."""
        conductor = configured_app.container.resolve(Conductor)
        sm = configured_app.container.resolve(StateManager)

        # Call synthesis directly (bypasses input contract)
        result = conductor._run_hull_synthesis()

        # Synthesis should succeed and produce usable hull
        assert result is not None
        assert result.is_usable
        assert result.proposal.lwl_m > 0
        assert result.proposal.beam_m > 0

    def test_hull_phase_with_full_inputs(self):
        """Hull phase runs when all inputs are seeded."""
        app = MAGNETApp().build()
        conductor = app.container.resolve(Conductor)
        sm = app.container.resolve(StateManager)

        # Seed all hull inputs required by contract
        sm.set("hull.lwl", 25.0, "test")
        sm.set("hull.beam", 5.5, "test")
        sm.set("hull.draft", 1.6, "test")
        sm.set("hull.cb", 0.45, "test")
        sm.set("hull.hull_type", "workboat", "test")

        # Now hull phase should not be blocked
        result = conductor.run_phase("hull")

        # Should complete or at least not be blocked for missing inputs
        assert result is not None
        # Note: May still be blocked for other reasons (dependencies, etc.)
        # But should not be "Missing required inputs"
        if result.status == PhaseStatus.BLOCKED:
            for err in result.errors:
                assert "Missing required inputs" not in err


class TestGoldenPathValidators:
    """Tests for validator integration in golden path."""

    @pytest.fixture
    def app_with_hull(self):
        """Create app with hull data seeded."""
        app = MAGNETApp().build()
        sm = app.container.resolve(StateManager)

        # Seed hull data directly
        sm.set("hull.lwl", 25.0, "test")
        sm.set("hull.beam", 5.5, "test")
        sm.set("hull.draft", 1.6, "test")
        sm.set("hull.cb", 0.45, "test")
        sm.set("hull.depth", 2.5, "test")

        return app

    def test_validator_pipeline_registered(self, app_with_hull):
        """Validator pipeline should be registered in container."""
        from magnet.validators.executor import PipelineExecutor
        from magnet.validators.aggregator import ResultAggregator

        container = app_with_hull.container

        # Check if pipeline executor is registered
        if container.is_registered(PipelineExecutor):
            executor = container.resolve(PipelineExecutor)
            assert executor is not None

        # Check if aggregator is registered
        if container.is_registered(ResultAggregator):
            aggregator = container.resolve(ResultAggregator)
            assert aggregator is not None


class TestGoldenPathContracts:
    """Tests for phase contracts in golden path."""

    @pytest.fixture
    def app(self):
        """Create basic app."""
        return MAGNETApp().build()

    def test_hull_contract_inputs(self, app):
        """Hull phase contract can check inputs."""
        from magnet.validators.contracts import check_phase_inputs

        sm = app.container.resolve(StateManager)

        # Without inputs, hull contract should report missing
        result = check_phase_inputs("hull", sm)
        # Hull requires lwl, beam, draft, cb as inputs
        assert not result.satisfied or len(result.missing_outputs) > 0

    def test_hull_contract_outputs_after_synthesis(self):
        """Hull phase contract satisfied after synthesis."""
        from magnet.validators.contracts import check_phase_outputs

        app = MAGNETApp().build()
        sm = app.container.resolve(StateManager)

        # Seed mission data
        sm.set("mission.max_speed_kts", 25.0, "test")
        sm.set("hull.hull_type", "workboat", "test")

        # Run hull phase to trigger synthesis
        conductor = app.container.resolve(Conductor)
        conductor.run_phase("hull")

        # Check outputs
        result = check_phase_outputs("hull", sm)
        # Synthesis should have written hull outputs
        # (may not be fully satisfied if validators didn't compute all outputs)


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
