"""
Tests for MAGNET Memory Module
==============================

Tests file I/O, schema validation, and memory operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from memory.file_io import MemoryFileIO
from memory.schemas import (
    MissionSchema,
    HullParamsSchema,
    SystemStateSchema,
    AgentVoteSchema,
    VoteType,
    DesignPhase,
)


@pytest.fixture
def temp_memory_dir():
    """Create temporary memory directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_io(temp_memory_dir):
    """Create MemoryFileIO instance with temp directory."""
    return MemoryFileIO(temp_memory_dir)


class TestMissionSchema:
    """Test MissionSchema validation."""

    def test_valid_mission(self):
        """Test creating a valid mission."""
        mission = MissionSchema(
            mission_id="MAGNET-001",
            vessel_type="patrol_catamaran",
            loa_m=22.0,
            beam_m=8.5,
            design_speed_kts=35.0,
            cruise_speed_kts=25.0,
            crew=8,
            endurance_nm=500.0,
        )
        assert mission.mission_id == "MAGNET-001"
        assert mission.loa_m == 22.0
        assert mission.iteration == 1

    def test_mission_with_constraints(self):
        """Test mission with constraints."""
        mission = MissionSchema(
            mission_id="MAGNET-002",
            vessel_type="patrol_catamaran",
            loa_m=22.0,
            beam_m=8.5,
            design_speed_kts=35.0,
            cruise_speed_kts=25.0,
            crew=8,
            endurance_nm=500.0,
            constraints={"max_draft_m": 1.8, "min_freeboard_m": 0.9},
        )
        assert mission.constraints["max_draft_m"] == 1.8

    def test_mission_json_serialization(self):
        """Test mission JSON serialization."""
        mission = MissionSchema(
            mission_id="MAGNET-003",
            vessel_type="patrol_catamaran",
            loa_m=22.0,
            beam_m=8.5,
            design_speed_kts=35.0,
            cruise_speed_kts=25.0,
            crew=8,
            endurance_nm=500.0,
        )
        json_data = mission.model_dump(mode='json')
        assert json_data["mission_id"] == "MAGNET-003"
        assert isinstance(json_data["created_at"], str)


class TestHullParamsSchema:
    """Test HullParamsSchema validation."""

    def test_valid_hull_params(self):
        """Test creating valid hull parameters."""
        hull = HullParamsSchema(
            hull_form="deep_v_catamaran",
            length_wl_m=20.5,
            beam_demihull_m=2.2,
            demihull_spacing_m=4.1,
            deadrise_transom_deg=18.0,
            deadrise_midship_deg=22.0,
            prismatic_coefficient=0.65,
            block_coefficient=0.42,
            lcb_from_transom_pct=42.0,
        )
        assert hull.hull_form == "deep_v_catamaran"
        assert hull.demihull_count == 2

    def test_hull_params_coefficient_bounds(self):
        """Test coefficient bounds validation."""
        with pytest.raises(ValueError):
            HullParamsSchema(
                hull_form="deep_v_catamaran",
                length_wl_m=20.5,
                beam_demihull_m=2.2,
                demihull_spacing_m=4.1,
                deadrise_transom_deg=18.0,
                deadrise_midship_deg=22.0,
                prismatic_coefficient=0.9,  # Invalid - too high
                block_coefficient=0.42,
                lcb_from_transom_pct=42.0,
            )


class TestSystemStateSchema:
    """Test SystemStateSchema."""

    def test_default_system_state(self):
        """Test default system state."""
        state = SystemStateSchema()
        assert state.current_phase == DesignPhase.MISSION
        assert state.phase_iteration == 1
        assert state.design_iteration == 1
        assert state.status == "initializing"

    def test_system_state_with_values(self):
        """Test system state with custom values."""
        state = SystemStateSchema(
            current_phase=DesignPhase.HULL_FORM,
            phase_iteration=2,
            design_iteration=5,
            active_agents=["director_001", "naval_arch_001"],
            status="in_progress",
        )
        assert state.current_phase == DesignPhase.HULL_FORM
        assert len(state.active_agents) == 2


class TestAgentVoteSchema:
    """Test AgentVoteSchema."""

    def test_valid_vote(self):
        """Test creating a valid vote."""
        vote = AgentVoteSchema(
            agent_id="class_reviewer_001",
            proposal_id="hull_params_v3",
            vote=VoteType.APPROVE,
            confidence=0.82,
            reasoning="Scantlings satisfy requirements",
        )
        assert vote.vote == VoteType.APPROVE
        assert vote.confidence == 0.82

    def test_vote_with_concerns(self):
        """Test vote with concerns."""
        vote = AgentVoteSchema(
            agent_id="class_reviewer_001",
            proposal_id="hull_params_v3",
            vote=VoteType.REVISE,
            confidence=0.65,
            reasoning="Minor issues found",
            concerns=["Forward bottom needs +1mm", "Check stiffener spacing"],
        )
        assert len(vote.concerns) == 2


class TestMemoryFileIO:
    """Test MemoryFileIO operations."""

    def test_initialization(self, memory_io):
        """Test memory initialization."""
        assert memory_io.memory_path.exists()
        assert (memory_io.memory_path / "decisions").exists()

    def test_write_and_read(self, memory_io):
        """Test write and read operations."""
        mission_data = {
            "mission_id": "TEST-001",
            "vessel_type": "patrol_catamaran",
            "loa_m": 22.0,
            "beam_m": 8.5,
            "design_speed_kts": 35.0,
            "cruise_speed_kts": 25.0,
            "crew": 8,
            "endurance_nm": 500.0,
        }

        memory_io.write("mission", mission_data)
        read_data = memory_io.read("mission")

        assert read_data["mission_id"] == "TEST-001"
        assert read_data["loa_m"] == 22.0

    def test_write_schema(self, memory_io):
        """Test writing a validated schema."""
        mission = MissionSchema(
            mission_id="TEST-002",
            vessel_type="patrol_catamaran",
            loa_m=22.0,
            beam_m=8.5,
            design_speed_kts=35.0,
            cruise_speed_kts=25.0,
            crew=8,
            endurance_nm=500.0,
        )

        memory_io.write_schema("mission", mission)
        read_data = memory_io.read("mission")

        assert read_data["mission_id"] == "TEST-002"

    def test_read_validated(self, memory_io):
        """Test reading with validation."""
        mission_data = {
            "mission_id": "TEST-003",
            "vessel_type": "patrol_catamaran",
            "loa_m": 22.0,
            "beam_m": 8.5,
            "design_speed_kts": 35.0,
            "cruise_speed_kts": 25.0,
            "crew": 8,
            "endurance_nm": 500.0,
        }

        memory_io.write("mission", mission_data)
        mission = memory_io.read_validated("mission", MissionSchema)

        assert isinstance(mission, MissionSchema)
        assert mission.mission_id == "TEST-003"

    def test_read_nonexistent(self, memory_io):
        """Test reading non-existent file."""
        result = memory_io.read("mission")
        assert result is None

    def test_append_log(self, memory_io):
        """Test appending to log file."""
        vote_data = {
            "agent_id": "test_agent",
            "proposal_id": "test_proposal",
            "vote": "approve",
            "confidence": 0.9,
            "reasoning": "Looks good",
        }

        memory_io.append_log("voting_history", vote_data)
        memory_io.append_log("voting_history", vote_data)

        entries = memory_io.read_log("voting_history")
        assert len(entries) == 2
        assert all(e["agent_id"] == "test_agent" for e in entries)

    def test_append_vote(self, memory_io):
        """Test appending a vote schema."""
        vote = AgentVoteSchema(
            agent_id="class_reviewer_001",
            proposal_id="hull_params_v1",
            vote=VoteType.APPROVE,
            confidence=0.85,
            reasoning="All checks pass",
        )

        memory_io.append_vote(vote)

        entries = memory_io.read_log("voting_history")
        assert len(entries) == 1
        assert entries[0]["agent_id"] == "class_reviewer_001"

    def test_system_state(self, memory_io):
        """Test system state management."""
        state = memory_io.get_system_state()
        assert state.current_phase == DesignPhase.MISSION

        updated = memory_io.update_system_state(
            current_phase=DesignPhase.HULL_FORM,
            status="designing",
        )
        assert updated.current_phase == DesignPhase.HULL_FORM
        assert updated.status == "designing"

    def test_list_files(self, memory_io):
        """Test listing files."""
        files = memory_io.list_files()
        assert "mission" in files
        assert "hull_params" in files
        assert files["mission"] is False  # Doesn't exist yet

    def test_exists(self, memory_io):
        """Test file existence check."""
        assert not memory_io.exists("mission")

        memory_io.write("mission", {
            "mission_id": "TEST",
            "vessel_type": "test",
            "loa_m": 10.0,
            "beam_m": 5.0,
            "design_speed_kts": 20.0,
            "cruise_speed_kts": 15.0,
            "crew": 2,
            "endurance_nm": 100.0,
        })

        assert memory_io.exists("mission")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
