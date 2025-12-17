"""
tests/unit/test_mutation_enforcement.py - Module 62 P0.3 Enforcement Tests

PROOF that the Intent→Action Protocol is now mandatory for refinable paths.
"""

import pytest
from magnet.core.state_manager import StateManager, MutationEnforcementError
from magnet.core.design_state import DesignState
from magnet.core.refinable_schema import is_refinable


class TestEnforcementProof:
    """Proof that enforcement is working correctly."""

    def test_direct_refinable_mutation_blocked(self):
        """Direct set() to refinable path without txn raises MutationEnforcementError."""
        sm = StateManager(DesignState())
        with pytest.raises(MutationEnforcementError) as exc_info:
            sm.set("hull.loa", 100.0, "unauthorized")
        assert "refinable path" in str(exc_info.value).lower()
        assert "hull.loa" in str(exc_info.value)

    def test_transaction_allows_refinable_mutation(self):
        """Active transaction enables refinable path writes."""
        sm = StateManager(DesignState())
        sm.begin_transaction()
        result = sm.set("hull.loa", 100.0, "test")
        sm.commit()
        assert result is True
        assert sm.get("hull.loa") == 100.0

    def test_internal_path_always_allowed(self):
        """Internal kernel paths bypass enforcement - no MutationEnforcementError raised."""
        sm = StateManager(DesignState())
        # Should not raise MutationEnforcementError - kernel paths are exempt
        # Note: set() may return False if path structure doesn't exist, but enforcement passes
        try:
            sm.set("kernel.session", {"id": "test"}, "any_source")
        except MutationEnforcementError:
            pytest.fail("Internal path 'kernel.session' should not raise MutationEnforcementError")

    def test_nested_transaction_fails(self):
        """Nested transactions are rejected."""
        sm = StateManager(DesignState())
        sm.begin_transaction()
        with pytest.raises(RuntimeError) as exc_info:
            sm.begin_transaction()
        assert "already in progress" in str(exc_info.value).lower()
        sm.commit()

    def test_multiple_refinable_paths_blocked_without_transaction(self):
        """Multiple refinable paths all require transaction."""
        sm = StateManager(DesignState())

        refinable_paths = [
            ("hull.loa", 50.0),
            ("hull.beam", 10.0),
            ("mission.max_speed_kts", 25.0),
            ("mission.range_nm", 500.0),
        ]

        for path, value in refinable_paths:
            with pytest.raises(MutationEnforcementError):
                sm.set(path, value, "test")

    def test_multiple_refinable_paths_allowed_in_transaction(self):
        """Multiple refinable paths work within single transaction."""
        sm = StateManager(DesignState())
        sm.begin_transaction()

        sm.set("hull.loa", 50.0, "test")
        sm.set("hull.beam", 10.0, "test")
        sm.set("mission.max_speed_kts", 25.0, "test")

        sm.commit()

        assert sm.get("hull.loa") == 50.0
        assert sm.get("hull.beam") == 10.0
        assert sm.get("mission.max_speed_kts") == 25.0

    def test_internal_prefixes_all_exempted(self):
        """All internal path prefixes bypass enforcement - no MutationEnforcementError raised."""
        sm = StateManager(DesignState())

        # Test a sampling of internal prefixes
        test_cases = [
            ("kernel.status", "active"),
            ("phase_states.hull", {"state": "active"}),
            ("metadata.design_id", "test-123"),
            ("weight.lightship_weight_mt", 100.0),
            ("stability.gm_m", 1.5),
        ]

        for path, value in test_cases:
            # Should not raise MutationEnforcementError - all are internal paths
            # Note: set() may return False if path structure doesn't exist, but enforcement passes
            try:
                sm.set(path, value, "test")
            except MutationEnforcementError:
                pytest.fail(f"Internal path '{path}' should not raise MutationEnforcementError")

    def test_design_version_increments_only_on_commit(self):
        """design_version only changes on commit, not on set."""
        sm = StateManager(DesignState())
        initial_version = sm.design_version

        sm.begin_transaction()
        sm.set("hull.loa", 50.0, "test")
        # Version unchanged during transaction
        assert sm.design_version == initial_version

        sm.commit()
        # Version incremented after commit
        assert sm.design_version == initial_version + 1

    def test_rollback_does_not_increment_version(self):
        """Rollback does not increment design_version."""
        sm = StateManager(DesignState())
        initial_version = sm.design_version

        txn_id = sm.begin_transaction()
        sm.set("hull.loa", 50.0, "test")
        sm.rollback_transaction(txn_id)

        assert sm.design_version == initial_version


class TestEnforcementErrorMessages:
    """Test that enforcement error messages are helpful."""

    def test_error_includes_path(self):
        """Error message includes the problematic path."""
        sm = StateManager(DesignState())
        try:
            sm.set("hull.beam", 15.0, "test")
            pytest.fail("Should have raised MutationEnforcementError")
        except MutationEnforcementError as e:
            assert "hull.beam" in str(e)

    def test_error_includes_source(self):
        """Error message includes the source that attempted the write."""
        sm = StateManager(DesignState())
        try:
            sm.set("hull.loa", 100.0, "my_custom_source")
            pytest.fail("Should have raised MutationEnforcementError")
        except MutationEnforcementError as e:
            assert "my_custom_source" in str(e)

    def test_error_suggests_action_plan(self):
        """Error message suggests using ActionPlan pipeline."""
        sm = StateManager(DesignState())
        try:
            sm.set("mission.max_speed_kts", 30.0, "test")
            pytest.fail("Should have raised MutationEnforcementError")
        except MutationEnforcementError as e:
            assert "ActionPlan" in str(e) or "action" in str(e).lower()


class TestRefinableEnforcement:
    """Test that enforcement uses is_refinable() correctly."""

    def test_refinable_paths_require_transaction(self):
        """Paths where is_refinable() returns True require transactions."""
        # These are paths explicitly defined in REFINABLE_SCHEMA
        refinable_paths = [
            "hull.loa",
            "hull.beam",
            "hull.draft",
            "mission.max_speed_kts",
            "mission.range_nm",
            "mission.crew_berthed",
        ]

        for path in refinable_paths:
            assert is_refinable(path), f"Expected '{path}' to be refinable"

    def test_non_refinable_paths_allowed_without_transaction(self):
        """Paths where is_refinable() returns False are always allowed."""
        non_refinable_paths = [
            "kernel.session",
            "phase_states.hull",
            "metadata.design_id",
            "compliance.status",
            "weight.lightship_weight_mt",
            "stability.gm_m",
            "hydrostatics.kb_m",
        ]

        for path in non_refinable_paths:
            assert not is_refinable(path), f"Expected '{path}' to NOT be refinable"

    def test_enforcement_follows_is_refinable(self):
        """StateManager enforcement uses is_refinable() as the sole criterion."""
        sm = StateManager(DesignState())

        # Refinable paths blocked without transaction
        with pytest.raises(MutationEnforcementError):
            sm.set("hull.loa", 100.0, "test")

        # Non-refinable paths allowed without transaction (even if set() returns False)
        try:
            sm.set("kernel.status", "active", "test")
        except MutationEnforcementError:
            pytest.fail("Non-refinable path 'kernel.status' should not raise MutationEnforcementError")


class TestIsRefinableCorrectness:
    """Audit requirement: Verify is_refinable() returns correct values for all path types."""

    def test_all_hull_refinable_paths(self):
        """All hull dimension paths in REFINABLE_SCHEMA are recognized."""
        hull_refinable = [
            "hull.loa",
            "hull.lwl",
            "hull.beam",
            "hull.draft",
            "hull.depth",
            "hull.cb",
            "hull.cm",
            "hull.cp",
            "hull.deadrise_deg",
        ]
        for path in hull_refinable:
            assert is_refinable(path), f"Expected hull path '{path}' to be refinable"

    def test_all_mission_refinable_paths(self):
        """All mission paths in REFINABLE_SCHEMA are recognized."""
        mission_refinable = [
            "mission.max_speed_kts",
            "mission.cruise_speed_kts",
            "mission.range_nm",
            "mission.crew_berthed",
            "mission.passengers",
            "mission.gm_required_m",
        ]
        for path in mission_refinable:
            assert is_refinable(path), f"Expected mission path '{path}' to be refinable"

    def test_all_propulsion_refinable_paths(self):
        """All propulsion paths in REFINABLE_SCHEMA are recognized."""
        propulsion_refinable = [
            "propulsion.num_engines",
            "propulsion.num_propellers",
            "propulsion.propeller_diameter_m",
            "propulsion.total_installed_power_kw",
        ]
        for path in propulsion_refinable:
            assert is_refinable(path), f"Expected propulsion path '{path}' to be refinable"

    def test_kernel_paths_not_refinable(self):
        """Kernel paths are NOT refinable (computed/internal state)."""
        kernel_paths = [
            "kernel.session",
            "kernel.status",
            "kernel.design_id",
        ]
        for path in kernel_paths:
            assert not is_refinable(path), f"Kernel path '{path}' should NOT be refinable"

    def test_phase_states_not_refinable(self):
        """Phase state paths are NOT refinable (phase machine owned)."""
        phase_paths = [
            "phase_states.hull",
            "phase_states.mission",
            "phase_states.propulsion",
        ]
        for path in phase_paths:
            assert not is_refinable(path), f"Phase state path '{path}' should NOT be refinable"

    def test_metadata_not_refinable(self):
        """Metadata paths are NOT refinable (system-managed)."""
        metadata_paths = [
            "metadata.design_id",
            "metadata.created_at",
            "metadata.updated_at",
        ]
        for path in metadata_paths:
            assert not is_refinable(path), f"Metadata path '{path}' should NOT be refinable"

    def test_computed_outputs_not_refinable(self):
        """Computed output paths are NOT refinable (synthesis results)."""
        computed_paths = [
            "weight.lightship_weight_mt",
            "stability.gm_m",
            "hydrostatics.kb_m",
            "resistance.total_resistance_kn",
            "compliance.status",
        ]
        for path in computed_paths:
            assert not is_refinable(path), f"Computed path '{path}' should NOT be refinable"

    def test_mission_vessel_type_not_refinable(self):
        """mission.vessel_type is NOT in REFINABLE_SCHEMA (initial config only)."""
        # This is intentional - vessel_type is set once during mission creation
        # and affects downstream synthesis but should not be casually refined
        assert not is_refinable("mission.vessel_type"), \
            "mission.vessel_type should NOT be refinable"

    def test_arbitrary_paths_not_refinable(self):
        """Arbitrary/invalid paths are NOT refinable."""
        invalid_paths = [
            "foo.bar",
            "random.path",
            "hull",  # Missing second component
            "mission",  # Missing second component
            "",  # Empty string
        ]
        for path in invalid_paths:
            assert not is_refinable(path), f"Invalid path '{path}' should NOT be refinable"
