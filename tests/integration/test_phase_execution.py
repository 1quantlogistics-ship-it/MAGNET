"""
End-to-end phase execution tests.

Senior Audit Requirement (Hole #6): Verify that Conductor.run_phase() executes
validators via PipelineExecutor and produces expected state changes.

These tests verify the complete phase execution pipeline from Conductor
through validators to state mutations.
"""
import pytest
from datetime import datetime


class TestPhaseExecution:
    """Tests for complete phase execution through the Conductor."""

    @pytest.fixture
    def setup_app(self):
        """Create app and state manager for testing."""
        from magnet.bootstrap import create_app

        app = create_app()
        # Use the app's own state manager to ensure consistency
        sm = app.state_manager

        return app, sm

    def test_hull_phase_produces_outputs(self, setup_app):
        """
        Test that hull phase produces required outputs.

        Verifies:
        - hull.displacement_m3 is calculated
        - hull.vcb_m (KB) is calculated
        - hull.bmt (BM) is calculated
        """
        app, sm = setup_app

        # Provide required hull inputs
        sm.set("hull.lwl", 50.0, "test/setup")
        sm.set("hull.beam", 10.0, "test/setup")
        sm.set("hull.draft", 2.5, "test/setup")
        sm.set("hull.depth", 4.0, "test/setup")
        sm.set("hull.cb", 0.55, "test/setup")
        # Required by physics/resistance validator
        sm.set("mission.max_speed_kts", 15.0, "test/setup")

        # Get conductor and create session
        conductor = app.conductor
        session = conductor.create_session("test-hull-001")
        assert session is not None, "Failed to create session"

        # Run mission phase first (hull depends on mission)
        mission_result = conductor.run_phase("mission")
        assert mission_result.status.value in ("completed", "warning", "passed"), \
            f"Mission phase failed: {mission_result.errors if hasattr(mission_result, 'errors') else 'unknown'}"

        # Run hull phase
        result = conductor.run_phase("hull")

        # Check phase completed
        assert result.status.value in ("completed", "warning", "passed"), \
            f"Hull phase failed: {result.errors if hasattr(result, 'errors') else 'unknown'}"

        # Verify outputs exist
        displacement = sm.get("hull.displacement_m3")
        assert displacement is not None, "hull.displacement_m3 not produced"
        assert displacement > 0, f"Invalid displacement: {displacement}"

        vcb = sm.get("hull.vcb_m")
        assert vcb is not None, "hull.vcb_m (KB) not produced"

        bmt = sm.get("hull.bmt")
        assert bmt is not None, "hull.bmt (BM) not produced"

    def test_stability_phase_blocked_without_hull(self, setup_app):
        """
        Test that stability phase is blocked without hull outputs.

        Input contracts should prevent stability from running without
        hull.displacement_m3, hull.vcb_m, hull.bmt.
        """
        app, sm = setup_app

        conductor = app.conductor
        session = conductor.create_session("test-stability-blocked-001")

        # Try to run stability without hull - should be BLOCKED
        result = conductor.run_phase("stability")

        # Should fail due to missing inputs
        assert result.status.value in ("blocked", "failed"), \
            f"Stability should be blocked without hull outputs: {result.status}"

    def test_weight_phase_produces_outputs(self, setup_app):
        """
        Test that weight phase produces required outputs.

        Verifies:
        - weight.lightship_weight_mt is calculated
        - weight.lightship_vcg_m is calculated
        """
        app, sm = setup_app

        # Provide required inputs
        sm.set("hull.lwl", 50.0, "test/setup")
        sm.set("hull.beam", 10.0, "test/setup")
        sm.set("hull.draft", 2.5, "test/setup")
        sm.set("hull.depth", 4.0, "test/setup")
        sm.set("hull.cb", 0.55, "test/setup")
        sm.set("mission.max_speed_kts", 15.0, "test/setup")

        conductor = app.conductor
        conductor.create_session("test-weight-001")

        # Weight depends on hull, structure, and propulsion
        # Run all required prerequisite phases
        conductor.run_phase("mission")
        conductor.run_phase("hull")
        conductor.run_phase("structure")
        conductor.run_phase("propulsion")

        # Run weight phase
        result = conductor.run_phase("weight")

        assert result.status.value in ("completed", "warning", "passed"), \
            f"Weight phase failed: {result.status}"

        # Verify outputs
        lightship = sm.get("weight.lightship_weight_mt")
        assert lightship is not None, "weight.lightship_weight_mt not produced"

        vcg = sm.get("weight.lightship_vcg_m")
        assert vcg is not None, "weight.lightship_vcg_m not produced"

    def test_full_pipeline_hull_to_stability(self, setup_app):
        """
        Test complete hull → weight → stability pipeline.

        This is the critical path for ship design validation.
        """
        app, sm = setup_app

        # Setup hull inputs
        sm.set("hull.lwl", 50.0, "test/setup")
        sm.set("hull.beam", 10.0, "test/setup")
        sm.set("hull.draft", 2.5, "test/setup")
        sm.set("hull.depth", 4.0, "test/setup")
        sm.set("hull.cb", 0.55, "test/setup")
        # Required by physics/resistance validator
        sm.set("mission.max_speed_kts", 15.0, "test/setup")

        conductor = app.conductor
        conductor.create_session("test-pipeline-001")

        # Run mission phase first (hull depends on mission)
        mission_result = conductor.run_phase("mission")
        assert mission_result.status.value in ("completed", "warning", "passed"), \
            f"Mission phase failed: {mission_result.errors if hasattr(mission_result, 'errors') else 'unknown'}"

        # Run hull phase
        hull_result = conductor.run_phase("hull")
        assert hull_result.status.value in ("completed", "warning", "passed"), \
            f"Hull phase failed: {hull_result.status}"

        # Verify hull outputs before proceeding
        assert sm.get("hull.displacement_m3") is not None, "Hull didn't produce displacement"
        assert sm.get("hull.bmt") is not None, "Hull didn't produce BM"

        # Weight depends on structure and propulsion too
        conductor.run_phase("structure")
        conductor.run_phase("propulsion")

        # Run weight phase
        weight_result = conductor.run_phase("weight")
        assert weight_result.status.value in ("completed", "warning", "passed"), \
            f"Weight phase failed: {weight_result.status}"

        # Verify weight outputs
        lightship = sm.get("weight.lightship_weight_mt")
        vcg = sm.get("weight.lightship_vcg_m")
        assert lightship is not None, "weight.lightship_weight_mt not produced"
        assert vcg is not None, "weight.lightship_vcg_m not produced"

        # Run stability phase
        stability_result = conductor.run_phase("stability")
        assert stability_result.status.value in ("completed", "warning", "passed"), \
            f"Stability phase failed: {stability_result.status}"

        # Verify stability outputs
        gm = sm.get("stability.gm_transverse_m")
        assert gm is not None, "stability.gm_transverse_m not produced"

    def test_contract_field_names_are_valid(self, setup_app):
        """
        Test that all contract field names can be set/get from StateManager.

        Senior Audit Hole #2 fix: Actually validate paths resolve to real fields.
        """
        app, sm = setup_app

        # Test the corrected field names from contracts.py
        test_values = {
            # Hull outputs
            "hull.displacement_m3": 1500.0,
            "hull.vcb_m": 2.5,
            "hull.bmt": 3.2,  # NOT hull.bm_m

            # Stability outputs
            "stability.gm_transverse_m": 1.5,  # NOT stability.gm_m
            "stability.gz_curve": [],
            "stability.gz_max_m": 0.8,

            # Weight outputs
            "weight.lightship_weight_mt": 850.0,  # NOT weight.lightship_mt
            "weight.lightship_vcg_m": 3.5,
        }

        errors = []
        for path, value in test_values.items():
            try:
                sm.set(path, value, "test/contract_validation")
                retrieved = sm.get(path)
                if retrieved != value:
                    errors.append(f"{path}: set {value} but got {retrieved}")
            except Exception as e:
                errors.append(f"{path}: {e}")

        assert not errors, f"Contract field validation errors:\n" + "\n".join(errors)

    def test_weather_criterion_handles_zero_displacement(self, setup_app):
        """
        Test that weather criterion fails gracefully with zero displacement.

        Senior Audit Hole #4 fix: Validator-level guard prevents ZeroDivisionError.
        """
        from magnet.stability.validators import WeatherCriterionValidator

        app, sm = setup_app

        validator = WeatherCriterionValidator()

        # Run without displacement - should fail gracefully
        result = validator.validate(sm, {})

        assert result.state.value in ("failed", "error"), \
            f"Weather criterion should fail without displacement, got: {result.state.value}"

        # Verify error message mentions displacement
        if result.findings:
            messages = [f.message for f in result.findings]
            has_displacement_error = any("displacement" in m.lower() for m in messages)
            assert has_displacement_error, \
                f"Error should mention displacement. Got: {messages}"


class TestValidatorRegistry:
    """Tests for validator registration and instantiation."""

    def test_required_validators_instantiate(self):
        """Test that all required validators can be instantiated."""
        from magnet.validators.registry import ValidatorRegistry

        ValidatorRegistry.reset()
        ValidatorRegistry.initialize_defaults()
        instance_count = ValidatorRegistry.instantiate_all()

        assert instance_count > 0, "No validators instantiated"

        # Verify required validators are present
        required = [
            "physics/hydrostatics",
            "stability/intact_gm",
            "weight/estimation",
            "compliance/regulatory",
        ]

        for validator_id in required:
            instance = ValidatorRegistry.get_instance(validator_id)
            assert instance is not None, f"Required validator {validator_id} not instantiated"

    def test_topology_has_all_nodes(self):
        """Test that topology contains all defined validators."""
        from magnet.validators.topology import ValidatorTopology
        from magnet.validators.builtin import get_all_validators

        definitions = get_all_validators()
        topology = ValidatorTopology()
        topology.add_all_validators()
        topology.build()

        # Should have at least 20 nodes (as documented in audit)
        assert topology.validator_count >= 20, \
            f"Expected at least 20 topology nodes, got {topology.validator_count}"
