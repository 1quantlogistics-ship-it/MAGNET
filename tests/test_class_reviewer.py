"""
Tests for ClassReviewer agent.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from agents.class_reviewer import (
    ClassReviewerAgent,
    create_class_reviewer,
    ComplianceStandard,
    ALPHA_VALIDATION_AVAILABLE,
)
from agents.base import AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import VoteType


class TestClassReviewerAgent:
    """Test ClassReviewer agent basic functionality."""

    def test_creation(self):
        """Test agent creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)
            assert agent.agent_id == "class_reviewer_001"
            assert agent.agent_type == "class_reviewer"

    def test_system_prompt(self):
        """Test system prompt exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)
            assert "Class Reviewer" in agent.system_prompt
            assert "APPROVE" in agent.system_prompt
            assert "REJECT" in agent.system_prompt

    def test_default_standards(self):
        """Test default compliance standards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)
            assert ComplianceStandard.ABS_HSNC in agent.standards
            assert ComplianceStandard.IMO_A749 in agent.standards

    def test_custom_standards(self):
        """Test custom standards can be specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(
                memory_path=tmpdir,
                standards=[ComplianceStandard.DNV_HSLC]
            )
            assert ComplianceStandard.DNV_HSLC in agent.standards
            assert len(agent.standards) == 1


class TestDesignDataReading:
    """Test reading design data from memory."""

    def test_read_empty_memory(self):
        """Test reading from empty memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)
            data = agent._read_design_data()

            assert data["mission"] is None
            assert data["hull_params"] is None
            assert data["stability_results"] is None

    def test_read_populated_memory(self):
        """Test reading from populated memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)
            memory.write("mission", {"mission_id": "TEST-001"}, validate=False)
            memory.write("hull_params", {"length_waterline": 40.0}, validate=False)

            agent = ClassReviewerAgent(memory_path=tmpdir)
            data = agent._read_design_data()

            assert data["mission"] is not None
            assert data["hull_params"] is not None


class TestStructuralCompliance:
    """Test structural compliance checking."""

    def test_approved_alloy(self):
        """Test approved 5083 alloy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            structural = {
                "material": {"alloy": "5083-H116"},
                "summary": {"all_plating_compliant": True, "all_stiffeners_compliant": True},
            }

            findings = agent._check_structural_compliance(structural)

            # Should have PASS for alloy
            alloy_findings = [f for f in findings if "2-4-1" in f.get("rule", "")]
            assert len(alloy_findings) > 0
            assert any(f["status"] == "PASS" for f in alloy_findings)

    def test_prohibited_alloy(self):
        """Test prohibited 6061 alloy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            structural = {
                "material": {"alloy": "6061-T6"},
                "summary": {"all_plating_compliant": True, "all_stiffeners_compliant": True},
            }

            findings = agent._check_structural_compliance(structural)

            # Should have FAIL for 6061
            alloy_findings = [f for f in findings if "6061" in f.get("notes", "") or "PROHIBITED" in f.get("notes", "")]
            assert len(alloy_findings) > 0
            assert any(f["status"] == "FAIL" for f in alloy_findings)

    def test_non_compliant_plating(self):
        """Test non-compliant plating detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            structural = {
                "material": {"alloy": "5083-H116"},
                "summary": {"all_plating_compliant": False, "all_stiffeners_compliant": True},
            }

            findings = agent._check_structural_compliance(structural)

            # Should have FAIL for plating
            plating_findings = [f for f in findings if "3-3-2" in f.get("rule", "")]
            assert any(f["status"] == "FAIL" for f in plating_findings)


class TestStabilityCompliance:
    """Test stability compliance checking."""

    def test_stability_pass(self):
        """Test passing stability check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            stability = {
                "GM": 1.23,
                "imo_criteria_passed": True,
            }

            findings = agent._check_stability_compliance(stability)

            # Should all pass
            gm_findings = [f for f in findings if "GM" in f.get("rule", "") or "A.749" in f.get("rule", "")]
            assert all(f["status"] == "PASS" for f in gm_findings)

    def test_low_gm_fails(self):
        """Test low GM detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            stability = {
                "GM": 0.10,  # Below 0.15m minimum
                "imo_criteria_passed": False,
            }

            findings = agent._check_stability_compliance(stability)

            # Should have failures
            assert any(f["status"] == "FAIL" for f in findings)

    def test_imo_criteria_failed(self):
        """Test IMO criteria failure detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            stability = {
                "GM": 0.20,
                "imo_criteria_passed": False,
                "imo_criteria_details": {
                    "area_30": {"passed": False, "value": 0.05, "required": 0.055},
                },
            }

            findings = agent._check_stability_compliance(stability)

            # Should have failures for IMO
            imo_findings = [f for f in findings if "A.749" in f.get("rule", "")]
            assert any(f["status"] == "FAIL" for f in imo_findings)


class TestVoteDetermination:
    """Test vote determination logic."""

    def test_approve_on_all_pass(self):
        """Test approval when all checks pass."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            findings = [
                {"status": "PASS", "severity": "ok", "notes": "Test passed"},
            ]

            vote, confidence, concerns = agent._determine_vote(findings, None, [])

            assert vote == VoteType.APPROVE
            assert confidence >= 0.7

    def test_reject_on_error(self):
        """Test rejection on errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            findings = [
                {"status": "FAIL", "severity": "error", "notes": "Critical failure"},
            ]

            vote, confidence, concerns = agent._determine_vote(findings, None, [])

            assert vote == VoteType.REJECT
            assert "Critical failure" in concerns

    def test_abstain_on_many_warnings(self):
        """Test abstention on many warnings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ClassReviewerAgent(memory_path=tmpdir)

            # Use bounds violations for warnings since findings use severity == "warning"
            from validation.bounds import BoundsCheckResult
            bounds_violations = [
                BoundsCheckResult(
                    field=f"test_{i}",
                    value=100,
                    in_bounds=False,
                    bounds=(0, 50),
                    unit="",
                    message=f"Warning {i}",
                    severity="warning"
                )
                for i in range(5)
            ]

            vote, confidence, concerns = agent._determine_vote([], None, bounds_violations)

            assert vote == VoteType.REVISE


class TestFullReview:
    """Test full design review workflow."""

    @pytest.fixture
    def memory_with_design(self):
        """Create memory with complete design data."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("mission", {
            "mission_id": "TEST-001",
            "vessel_type": "patrol_catamaran",
            "design_speed_kts": 35,
            "range_nm": 300,
            "speed_max_kts": 35,
            "speed_cruise_kts": 25,
        }, validate=False)

        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.0,
            "draft": 2.5,
            "depth": 4.5,
            "block_coefficient": 0.45,
            "displacement_tonnes": 180,
        }, validate=False)

        memory.write("stability_results", {
            "GM": 1.23,
            "imo_criteria_passed": True,
        }, validate=False)

        memory.write("structural_design", {
            "material": {"alloy": "5083-H116"},
            "summary": {"all_plating_compliant": True, "all_stiffeners_compliant": True},
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_full_review_returns_response(self, memory_with_design):
        """Test full review returns valid response."""
        agent = ClassReviewerAgent(memory_path=memory_with_design)

        response = agent.review_design()

        assert isinstance(response, AgentResponse)
        assert response.confidence > 0
        assert len(response.proposals) > 0

    def test_full_review_writes_to_memory(self, memory_with_design):
        """Test full review writes results to memory."""
        agent = ClassReviewerAgent(memory_path=memory_with_design)
        memory = MemoryFileIO(memory_with_design)

        response = agent.review_design()

        # Check reviews file was written
        reviews = memory.read("reviews")
        assert reviews is not None
        assert "vote" in reviews
        assert "summary" in reviews

    def test_full_review_submits_vote(self, memory_with_design):
        """Test full review submits vote."""
        agent = ClassReviewerAgent(memory_path=memory_with_design)
        memory = MemoryFileIO(memory_with_design)

        response = agent.review_design()

        # Check voting history
        votes = memory.read_log("voting_history")
        assert len(votes) > 0
        assert votes[-1]["agent_id"] == agent.agent_id

    def test_compliant_design_approved(self, memory_with_design):
        """Test compliant design gets approved."""
        agent = ClassReviewerAgent(memory_path=memory_with_design)

        response = agent.review_design()

        assert response.metadata["vote"] == "approve"
        assert response.metadata["passed"] > 0
        assert response.metadata["failed"] == 0


class TestIncompleteDesign:
    """Test handling of incomplete designs."""

    def test_no_structural_design(self):
        """Test review without structural design."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)
            memory.write("hull_params", {"length_waterline": 40.0}, validate=False)

            agent = ClassReviewerAgent(memory_path=tmpdir)
            response = agent.review_design()

            # Should handle gracefully
            assert isinstance(response, AgentResponse)
            assert response.metadata["incomplete"] > 0

    def test_no_stability_results(self):
        """Test review without stability results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)
            memory.write("hull_params", {"length_waterline": 40.0}, validate=False)
            memory.write("structural_design", {
                "material": {"alloy": "5083-H116"},
                "summary": {"all_plating_compliant": True, "all_stiffeners_compliant": True},
            }, validate=False)

            agent = ClassReviewerAgent(memory_path=tmpdir)
            response = agent.review_design()

            assert isinstance(response, AgentResponse)


class TestProcessMethod:
    """Test the process() entry point."""

    def test_process_reads_from_memory(self):
        """Test process method reads from memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)

            memory.write("hull_params", {
                "length_waterline": 40.0,
                "beam": 10.0,
                "draft": 2.0,
                "depth": 4.0,
                "block_coefficient": 0.45,
            }, validate=False)

            agent = ClassReviewerAgent(memory_path=tmpdir)
            response = agent.process({})

            assert isinstance(response, AgentResponse)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_class_reviewer(self):
        """Test create_class_reviewer function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_class_reviewer(memory_path=tmpdir)

            assert isinstance(agent, ClassReviewerAgent)
            assert agent.agent_type == "class_reviewer"

    def test_create_with_standards(self):
        """Test create with custom standards."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_class_reviewer(
                memory_path=tmpdir,
                standards=[ComplianceStandard.LLOYDS_SSC]
            )

            assert ComplianceStandard.LLOYDS_SSC in agent.standards


class TestMetadata:
    """Test response metadata."""

    @pytest.fixture
    def memory_with_design(self):
        """Create memory with design data."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("hull_params", {
            "length_waterline": 45.0,
            "beam": 12.0,
            "draft": 2.0,
            "depth": 4.0,
            "block_coefficient": 0.45,
        }, validate=False)

        memory.write("stability_results", {
            "GM": 1.5,
            "imo_criteria_passed": True,
        }, validate=False)

        memory.write("structural_design", {
            "material": {"alloy": "5083-H116"},
            "summary": {"all_plating_compliant": True, "all_stiffeners_compliant": True},
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_metadata_includes_vote(self, memory_with_design):
        """Test metadata includes vote decision."""
        agent = ClassReviewerAgent(memory_path=memory_with_design)
        response = agent.review_design()

        assert "vote" in response.metadata
        assert response.metadata["vote"] in ["approve", "reject", "abstain"]

    def test_metadata_includes_counts(self, memory_with_design):
        """Test metadata includes pass/fail counts."""
        agent = ClassReviewerAgent(memory_path=memory_with_design)
        response = agent.review_design()

        assert "passed" in response.metadata
        assert "failed" in response.metadata
        assert "incomplete" in response.metadata

    def test_metadata_includes_standards(self, memory_with_design):
        """Test metadata includes standards list."""
        agent = ClassReviewerAgent(memory_path=memory_with_design)
        response = agent.review_design()

        assert "standards" in response.metadata
        assert len(response.metadata["standards"]) > 0
