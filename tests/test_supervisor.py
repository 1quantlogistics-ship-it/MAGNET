"""
Tests for Supervisor agent.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from agents.supervisor import (
    SupervisorAgent,
    create_supervisor,
    SupervisorDecision,
    ConstraintType,
    HardConstraint,
)
from agents.base import AgentResponse
from memory.file_io import MemoryFileIO


class TestSupervisorAgent:
    """Test Supervisor agent basic functionality."""

    def test_creation(self):
        """Test agent creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)
            assert agent.agent_id == "supervisor_001"
            assert agent.agent_type == "supervisor"

    def test_system_prompt(self):
        """Test system prompt exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)
            assert "Supervisor" in agent.system_prompt
            assert "veto" in agent.system_prompt.lower()
            assert "APPROVE" in agent.system_prompt
            assert "REJECT" in agent.system_prompt

    def test_hard_constraints_defined(self):
        """Test hard constraints are defined."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)
            assert len(agent._hard_constraints) > 0

    def test_constraint_types_present(self):
        """Test various constraint types are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            types_present = set()
            for constraint in agent._hard_constraints:
                types_present.add(constraint.constraint_type)

            assert ConstraintType.SAFETY in types_present
            assert ConstraintType.CLASSIFICATION in types_present


class TestHardConstraintEvaluation:
    """Test hard constraint evaluation."""

    def test_gm_constraint_pass(self):
        """Test GM constraint passes with valid GM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"stability_results": {"GM": 1.5}}
            passed, message = agent._check_gm_minimum(data)

            assert passed is True
            assert "meets minimum" in message

    def test_gm_constraint_fail(self):
        """Test GM constraint fails with low GM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"stability_results": {"GM": 0.10}}
            passed, message = agent._check_gm_minimum(data)

            assert passed is False
            assert "below minimum" in message

    def test_gm_constraint_not_calculated(self):
        """Test GM constraint passes when not yet calculated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {}
            passed, message = agent._check_gm_minimum(data)

            assert passed is True
            assert "not yet" in message

    def test_imo_criteria_pass(self):
        """Test IMO criteria constraint passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"stability_results": {"imo_criteria_passed": True}}
            passed, message = agent._check_imo_criteria(data)

            assert passed is True

    def test_imo_criteria_fail(self):
        """Test IMO criteria constraint fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"stability_results": {"imo_criteria_passed": False}}
            passed, message = agent._check_imo_criteria(data)

            assert passed is False

    def test_prohibited_alloy_detected(self):
        """Test prohibited 6061 alloy is detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"structural_design": {"material": {"alloy": "6061-T6"}}}
            passed, message = agent._check_no_prohibited_alloys(data)

            assert passed is False
            assert "PROHIBITED" in message

    def test_approved_alloy_passes(self):
        """Test approved 5083 alloy passes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"structural_design": {"material": {"alloy": "5083-H116"}}}
            passed, message = agent._check_no_prohibited_alloys(data)

            assert passed is True

    def test_positive_displacement(self):
        """Test positive displacement check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"hull_params": {"displacement_tonnes": 180}}
            passed, message = agent._check_positive_displacement(data)

            assert passed is True

    def test_zero_displacement_fails(self):
        """Test zero displacement fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {"hull_params": {"displacement_tonnes": 0}}
            passed, message = agent._check_positive_displacement(data)

            assert passed is False


class TestConstraintBundleEvaluation:
    """Test evaluating all constraints together."""

    def test_all_constraints_pass(self):
        """Test all constraints passing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {
                "stability_results": {"GM": 1.5, "imo_criteria_passed": True},
                "structural_design": {
                    "material": {"alloy": "5083-H116"},
                    "summary": {"all_plating_compliant": True},
                },
                "hull_params": {"displacement_tonnes": 180},
            }

            all_passed, results = agent._evaluate_constraints(data)

            assert all_passed is True
            assert all(r["passed"] for r in results)

    def test_single_constraint_fails(self):
        """Test single constraint failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {
                "stability_results": {"GM": 0.10, "imo_criteria_passed": True},  # GM fails
                "structural_design": {
                    "material": {"alloy": "5083-H116"},
                    "summary": {"all_plating_compliant": True},
                },
                "hull_params": {"displacement_tonnes": 180},
            }

            all_passed, results = agent._evaluate_constraints(data)

            assert all_passed is False
            failed = [r for r in results if not r["passed"]]
            assert len(failed) == 1
            assert "gm" in failed[0]["name"]

    def test_multiple_constraints_fail(self):
        """Test multiple constraint failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {
                "stability_results": {"GM": 0.10, "imo_criteria_passed": False},  # Both fail
                "structural_design": {
                    "material": {"alloy": "5083-H116"},
                    "summary": {"all_plating_compliant": True},
                },
                "hull_params": {"displacement_tonnes": 180},
            }

            all_passed, results = agent._evaluate_constraints(data)

            assert all_passed is False
            failed = [r for r in results if not r["passed"]]
            assert len(failed) == 2


class TestSupervisionDecision:
    """Test supervision decision making."""

    @pytest.fixture
    def memory_with_valid_design(self):
        """Create memory with valid design data."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("stability_results", {
            "GM": 1.5,
            "imo_criteria_passed": True,
        }, validate=False)

        memory.write("structural_design", {
            "material": {"alloy": "5083-H116"},
            "summary": {"all_plating_compliant": True},
        }, validate=False)

        memory.write("hull_params", {
            "displacement_tonnes": 180,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    @pytest.fixture
    def memory_with_invalid_design(self):
        """Create memory with invalid design data."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("stability_results", {
            "GM": 0.10,  # Too low
            "imo_criteria_passed": False,
        }, validate=False)

        memory.write("structural_design", {
            "material": {"alloy": "5083-H116"},
            "summary": {"all_plating_compliant": True},
        }, validate=False)

        memory.write("hull_params", {
            "displacement_tonnes": 180,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_approve_valid_design(self, memory_with_valid_design):
        """Test valid design is approved."""
        agent = SupervisorAgent(memory_path=memory_with_valid_design)

        response = agent.supervise_design()

        assert response.metadata["decision"] == "approve"
        assert response.metadata["violations"] == 0

    def test_reject_invalid_design(self, memory_with_invalid_design):
        """Test invalid design is rejected."""
        agent = SupervisorAgent(memory_path=memory_with_invalid_design)

        response = agent.supervise_design()

        assert response.metadata["decision"] == "reject"
        assert response.metadata["violations"] > 0

    def test_supervision_logs_decision(self, memory_with_valid_design):
        """Test supervision logs decision."""
        agent = SupervisorAgent(memory_path=memory_with_valid_design)
        memory = MemoryFileIO(memory_with_valid_design)

        response = agent.supervise_design()

        # Check supervisor_decisions log
        decisions = memory.read_log("supervisor_decisions")
        assert len(decisions) > 0
        assert decisions[-1]["decision"] == "approve"


class TestVetoAndOverride:
    """Test veto and override functionality."""

    def test_veto_proposal(self):
        """Test veto proposal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            veto = agent.veto_proposal(
                proposal_id="test_proposal_001",
                reason="Violates safety requirement"
            )

            assert veto["action"] == "veto"
            assert veto["proposal_id"] == "test_proposal_001"
            assert "safety" in veto["reason"]

    def test_veto_is_logged(self):
        """Test veto is logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)
            agent = SupervisorAgent(memory_path=tmpdir)

            agent.veto_proposal(
                proposal_id="test_proposal_001",
                reason="Violates safety requirement"
            )

            decisions = memory.read_log("supervisor_decisions")
            assert len(decisions) > 0
            assert decisions[-1]["action"] == "veto"

    def test_override_consensus(self):
        """Test override consensus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            override = agent.override_consensus(
                decision=SupervisorDecision.REJECT,
                reason="Safety concern overrides consensus"
            )

            assert override["action"] == "override"
            assert override["decision"] == "reject"

    def test_override_is_logged(self):
        """Test override is logged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)
            agent = SupervisorAgent(memory_path=tmpdir)

            agent.override_consensus(
                decision=SupervisorDecision.REVISE,
                reason="Needs modification"
            )

            decisions = memory.read_log("supervisor_decisions")
            assert len(decisions) > 0
            assert decisions[-1]["action"] == "override"


class TestConsensusOverride:
    """Test consensus override detection."""

    def test_no_override_without_reviews(self):
        """Test no override needed without reviews."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            needed, reason = agent._check_consensus_override_needed({})

            assert needed is False

    def test_override_on_class_reviewer_reject(self):
        """Test override triggered by class reviewer rejection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = SupervisorAgent(memory_path=tmpdir)

            data = {
                "reviews": {
                    "vote": "reject",
                    "summary": {"failed": 2},
                }
            }

            needed, reason = agent._check_consensus_override_needed(data)

            assert needed is True
            assert "rejected" in reason


class TestProcessMethod:
    """Test the process() entry point."""

    def test_process_reads_from_memory(self):
        """Test process reads from memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)

            memory.write("stability_results", {
                "GM": 1.5,
                "imo_criteria_passed": True,
            }, validate=False)

            memory.write("hull_params", {
                "displacement_tonnes": 180,
            }, validate=False)

            agent = SupervisorAgent(memory_path=tmpdir)
            response = agent.process({})

            assert isinstance(response, AgentResponse)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_supervisor(self):
        """Test create_supervisor function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_supervisor(memory_path=tmpdir)

            assert isinstance(agent, SupervisorAgent)
            assert agent.agent_type == "supervisor"


class TestMetadata:
    """Test response metadata."""

    @pytest.fixture
    def memory_with_design(self):
        """Create memory with design data."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("stability_results", {
            "GM": 1.5,
            "imo_criteria_passed": True,
        }, validate=False)

        memory.write("structural_design", {
            "material": {"alloy": "5083-H116"},
            "summary": {"all_plating_compliant": True},
        }, validate=False)

        memory.write("hull_params", {
            "displacement_tonnes": 180,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_metadata_includes_decision(self, memory_with_design):
        """Test metadata includes decision."""
        agent = SupervisorAgent(memory_path=memory_with_design)
        response = agent.supervise_design()

        assert "decision" in response.metadata
        assert response.metadata["decision"] in ["approve", "reject", "revise", "defer", "escalate"]

    def test_metadata_includes_violations(self, memory_with_design):
        """Test metadata includes violation count."""
        agent = SupervisorAgent(memory_path=memory_with_design)
        response = agent.supervise_design()

        assert "violations" in response.metadata
        assert response.metadata["violations"] >= 0

    def test_metadata_includes_constraint_count(self, memory_with_design):
        """Test metadata includes constraints checked count."""
        agent = SupervisorAgent(memory_path=memory_with_design)
        response = agent.supervise_design()

        assert "constraints_checked" in response.metadata
        assert response.metadata["constraints_checked"] > 0


class TestProposalOutput:
    """Test proposal output structure."""

    @pytest.fixture
    def memory_with_design(self):
        """Create memory with design data."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("stability_results", {
            "GM": 1.5,
            "imo_criteria_passed": True,
        }, validate=False)

        memory.write("hull_params", {
            "displacement_tonnes": 180,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_proposal_includes_constraint_results(self, memory_with_design):
        """Test proposal includes constraint results."""
        agent = SupervisorAgent(memory_path=memory_with_design)
        response = agent.supervise_design()

        proposal = response.proposals[0]
        assert "constraint_results" in proposal
        assert len(proposal["constraint_results"]) > 0

    def test_proposal_includes_violations(self, memory_with_design):
        """Test proposal includes violations list."""
        agent = SupervisorAgent(memory_path=memory_with_design)
        response = agent.supervise_design()

        proposal = response.proposals[0]
        assert "violations" in proposal

    def test_proposal_includes_timestamp(self, memory_with_design):
        """Test proposal includes timestamp."""
        agent = SupervisorAgent(memory_path=memory_with_design)
        response = agent.supervise_design()

        proposal = response.proposals[0]
        assert "timestamp" in proposal
        assert "supervised_by" in proposal
