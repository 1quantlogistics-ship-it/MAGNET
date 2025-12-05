"""
Tests for MAGNET Orchestration Module
=====================================

Tests Coordinator and ConsensusEngine functionality.
"""

import pytest
import tempfile
import shutil
from datetime import datetime

from orchestration import Coordinator, create_coordinator, ConsensusEngine, ConsensusResult
from orchestration.consensus import ConsensusStatus
from memory.file_io import MemoryFileIO
from memory.schemas import DesignPhase, VoteType, AgentVoteSchema


@pytest.fixture
def temp_memory_dir():
    """Create temporary memory directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory(temp_memory_dir):
    """Create memory instance."""
    return MemoryFileIO(temp_memory_dir)


@pytest.fixture
def sample_mission():
    """Sample mission data for testing."""
    return {
        "mission_id": "TEST-001",
        "vessel_type": "patrol_catamaran",
        "loa_m": 25.0,
        "beam_m": 8.5,
        "design_speed_kts": 35.0,
        "cruise_speed_kts": 25.0,
        "crew": 8,
        "endurance_nm": 600.0,
    }


class TestConsensusEngine:
    """Test ConsensusEngine functionality."""

    def test_creation(self):
        """Test creating consensus engine."""
        engine = ConsensusEngine()
        assert engine.threshold == 0.66
        assert engine.min_votes == 2

    def test_custom_threshold(self):
        """Test custom threshold."""
        engine = ConsensusEngine(threshold=0.75)
        assert engine.threshold == 0.75

    def test_insufficient_votes(self):
        """Test with insufficient votes."""
        engine = ConsensusEngine(min_votes=2)

        votes = [
            AgentVoteSchema(
                agent_id="agent1",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.9,
                reasoning="Looks good",
            )
        ]

        result = engine.evaluate(votes)
        assert result.status == ConsensusStatus.INSUFFICIENT_VOTES
        assert not result.is_approved

    def test_unanimous_approval(self):
        """Test unanimous approval."""
        engine = ConsensusEngine(min_votes=2)

        votes = [
            AgentVoteSchema(
                agent_id="agent1",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.9,
                reasoning="Approved",
            ),
            AgentVoteSchema(
                agent_id="agent2",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.85,
                reasoning="Approved",
            ),
        ]

        result = engine.evaluate(votes)
        assert result.status == ConsensusStatus.ACHIEVED
        assert result.is_approved
        assert result.approval_ratio == 1.0

    def test_mixed_votes_approved(self):
        """Test mixed votes that still pass threshold."""
        engine = ConsensusEngine(min_votes=2, threshold=0.66)

        votes = [
            AgentVoteSchema(
                agent_id="agent1",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.9,
                reasoning="Approved",
            ),
            AgentVoteSchema(
                agent_id="agent2",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.85,
                reasoning="Approved",
            ),
            AgentVoteSchema(
                agent_id="agent3",
                proposal_id="test",
                vote=VoteType.REVISE,
                confidence=0.7,
                reasoning="Minor issues",
            ),
        ]

        result = engine.evaluate(votes)
        assert result.status == ConsensusStatus.ACHIEVED
        assert result.approval_ratio == 2/3

    def test_revision_needed(self):
        """Test when revision is needed."""
        engine = ConsensusEngine(min_votes=2, threshold=0.66)

        votes = [
            AgentVoteSchema(
                agent_id="agent1",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.7,
                reasoning="OK",
            ),
            AgentVoteSchema(
                agent_id="agent2",
                proposal_id="test",
                vote=VoteType.REVISE,
                confidence=0.8,
                reasoning="Needs changes",
                concerns=["Issue 1", "Issue 2"],
            ),
            AgentVoteSchema(
                agent_id="agent3",
                proposal_id="test",
                vote=VoteType.REVISE,
                confidence=0.75,
                reasoning="More work needed",
            ),
        ]

        result = engine.evaluate(votes)
        assert result.status == ConsensusStatus.REVISION_NEEDED
        assert result.needs_revision
        assert len(result.concerns) == 2

    def test_rejection(self):
        """Test rejection scenario."""
        engine = ConsensusEngine(min_votes=2, threshold=0.66)

        votes = [
            AgentVoteSchema(
                agent_id="agent1",
                proposal_id="test",
                vote=VoteType.REJECT,
                confidence=0.9,
                reasoning="Critical failure",
            ),
            AgentVoteSchema(
                agent_id="agent2",
                proposal_id="test",
                vote=VoteType.REJECT,
                confidence=0.85,
                reasoning="Cannot approve",
            ),
        ]

        result = engine.evaluate(votes)
        assert result.status == ConsensusStatus.REJECTED

    def test_weighted_voting(self):
        """Test confidence-weighted voting."""
        engine = ConsensusEngine(min_votes=2, use_weighted=True)

        # High confidence approval, low confidence revise
        votes = [
            AgentVoteSchema(
                agent_id="agent1",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.95,
                reasoning="Strong approval",
            ),
            AgentVoteSchema(
                agent_id="agent2",
                proposal_id="test",
                vote=VoteType.REVISE,
                confidence=0.4,
                reasoning="Weak concern",
            ),
        ]

        result = engine.evaluate(votes)
        # Weighted should favor high-confidence approval
        assert result.weighted_approval > 0.5

    def test_result_to_dict(self):
        """Test result serialization."""
        engine = ConsensusEngine(min_votes=2)

        votes = [
            AgentVoteSchema(
                agent_id="agent1",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.9,
                reasoning="OK",
            ),
            AgentVoteSchema(
                agent_id="agent2",
                proposal_id="test",
                vote=VoteType.APPROVE,
                confidence=0.85,
                reasoning="OK",
            ),
        ]

        result = engine.evaluate(votes)
        result_dict = result.to_dict()

        assert "status" in result_dict
        assert "approval_ratio" in result_dict
        assert "timestamp" in result_dict

    def test_vote_history(self):
        """Test vote history tracking."""
        engine = ConsensusEngine()

        vote = AgentVoteSchema(
            agent_id="agent1",
            proposal_id="proposal_1",
            vote=VoteType.APPROVE,
            confidence=0.9,
            reasoning="OK",
        )

        engine.add_vote(vote)
        votes = engine.get_votes_for_proposal("proposal_1")

        assert len(votes) == 1
        assert votes[0].agent_id == "agent1"


class TestCoordinator:
    """Test Coordinator functionality."""

    def test_creation(self, temp_memory_dir):
        """Test creating coordinator."""
        coord = Coordinator(memory_path=temp_memory_dir)
        assert coord.memory_path == temp_memory_dir

    def test_get_current_phase(self, temp_memory_dir):
        """Test getting current phase."""
        coord = Coordinator(memory_path=temp_memory_dir)
        phase = coord.get_current_phase()
        assert phase == DesignPhase.MISSION

    def test_get_workflow_step(self, temp_memory_dir):
        """Test getting workflow step."""
        coord = Coordinator(memory_path=temp_memory_dir)
        step = coord.get_workflow_step(DesignPhase.MISSION)

        assert step is not None
        assert step.agent_type == "director"
        assert "mission" in step.outputs

    def test_check_inputs_available(self, temp_memory_dir, memory, sample_mission):
        """Test input availability check."""
        coord = Coordinator(memory_path=temp_memory_dir)

        # Hull form requires mission
        step = coord.get_workflow_step(DesignPhase.HULL_FORM)

        # Initially mission not available
        assert not coord.check_inputs_available(step)

        # Write mission
        memory.write("mission", sample_mission)

        # Now should be available
        assert coord.check_inputs_available(step)

    def test_process_message_mission_phase(self, temp_memory_dir):
        """Test processing message in mission phase."""
        coord = Coordinator(memory_path=temp_memory_dir)

        result = coord.process_message("Design a 30m patrol boat with 35 knots")

        assert result["success"] is True
        assert result["agent"] == "director"
        assert result["phase"] == "mission"

    def test_process_message_hull_form_phase(self, temp_memory_dir, memory, sample_mission):
        """Test processing message in hull form phase."""
        # Write mission first
        memory.write("mission", sample_mission)
        memory.update_system_state(current_phase=DesignPhase.HULL_FORM)

        coord = Coordinator(memory_path=temp_memory_dir)

        result = coord.process_message("Design the hull")

        assert result["success"] is True
        assert result["agent"] == "naval_architect"
        assert result["phase"] == "hull_form"

    def test_process_message_missing_inputs(self, temp_memory_dir, memory):
        """Test processing when inputs are missing."""
        # Advance to hull form without mission
        memory.update_system_state(current_phase=DesignPhase.HULL_FORM)

        coord = Coordinator(memory_path=temp_memory_dir)

        result = coord.process_message("Design the hull")

        assert result["success"] is False
        assert "Missing required inputs" in result["error"]

    def test_advance_phase_success(self, temp_memory_dir, memory, sample_mission):
        """Test successful phase advancement."""
        memory.write("mission", sample_mission)

        coord = Coordinator(memory_path=temp_memory_dir)

        result = coord.advance_phase()

        assert result["success"] is True
        assert result["previous_phase"] == "mission"
        assert result["current_phase"] == "hull_form"

    def test_advance_phase_missing_output(self, temp_memory_dir):
        """Test phase advancement fails when output missing."""
        coord = Coordinator(memory_path=temp_memory_dir)

        result = coord.advance_phase()

        assert result["success"] is False
        assert "missing output" in result["error"]

    def test_get_design_status(self, temp_memory_dir, memory, sample_mission):
        """Test getting design status."""
        memory.write("mission", sample_mission)

        coord = Coordinator(memory_path=temp_memory_dir)

        status = coord.get_design_status()

        assert status["current_phase"] == "mission"
        assert "mission" in status["completed_outputs"]
        assert "hull_params" in status["pending_outputs"]


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_coordinator(self, temp_memory_dir):
        """Test create_coordinator convenience function."""
        coord = create_coordinator(memory_path=temp_memory_dir)
        assert isinstance(coord, Coordinator)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
