"""
Tests for MAGNET Naval Architect Agent
======================================

Tests NavalArchitectAgent hull form design functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from agents.naval_architect import NavalArchitectAgent, create_naval_architect
from agents.base import AgentResponse
from memory.file_io import MemoryFileIO
from memory.schemas import DesignPhase


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
        "sea_state_operational": 5,
        "payload_kg": 5000,
    }


class TestNavalArchitectAgent:
    """Test NavalArchitectAgent functionality."""

    def test_creation(self, temp_memory_dir):
        """Test creating a naval architect agent."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )
        assert agent.agent_id == "naval_arch_test"
        assert agent.agent_type == "naval_architect"

    def test_system_prompt(self, temp_memory_dir):
        """Test naval architect has proper system prompt."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )
        assert "Naval Architect" in agent.system_prompt
        assert "hull" in agent.system_prompt.lower()

    def test_generate_proposal_id(self, temp_memory_dir):
        """Test proposal ID generation."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )
        id1 = agent._generate_proposal_id()
        id2 = agent._generate_proposal_id()

        assert id1 == "hull_params_v1"
        assert id2 == "hull_params_v2"

    def test_extract_json_from_response(self, temp_memory_dir):
        """Test JSON extraction from LLM response."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        # Test with HULL_PARAMS_JSON marker
        response1 = """
        Based on the mission requirements:

        HULL_PARAMS_JSON:
        {"hull_type": "semi_displacement", "length_overall": 30.0, "beam": 6.0}
        """
        result1 = agent._extract_json_from_response(response1)
        assert result1["hull_type"] == "semi_displacement"

        # Test with code block
        response2 = """
        Analysis complete.

        ```json
        {"hull_type": "catamaran", "length_overall": 25.0}
        ```
        """
        result2 = agent._extract_json_from_response(response2)
        assert result2["hull_type"] == "catamaran"


class TestNavalArchitectFallback:
    """Test fallback design functionality."""

    def test_fallback_design_basic(self, temp_memory_dir, sample_mission):
        """Test fallback design without LLM."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        response = agent._fallback_design(sample_mission)

        assert response.confidence > 0
        assert len(response.proposals) > 0

        hull = response.proposals[0]
        assert "hull_type" in hull
        assert "length_overall" in hull
        assert "beam" in hull
        assert "draft" in hull
        assert "block_coefficient" in hull

    def test_fallback_high_speed(self, temp_memory_dir):
        """Test fallback for high-speed vessel."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        mission = {
            "design_speed_kts": 45.0,
            "endurance_nm": 500,
            "payload_kg": 3000,
            "sea_state_operational": 4,
        }

        response = agent._fallback_design(mission)
        hull = response.proposals[0]

        # High speed should give planing or semi-displacement hull
        assert hull["hull_type"] in ["planing", "semi_displacement"]
        # Lower block coefficient for speed
        assert hull["block_coefficient"] <= 0.45

    def test_fallback_heavy_payload(self, temp_memory_dir):
        """Test fallback for heavy payload vessel."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        mission = {
            "design_speed_kts": 25.0,
            "endurance_nm": 1000,
            "payload_kg": 60000,
            "sea_state_operational": 7,
        }

        response = agent._fallback_design(mission)
        hull = response.proposals[0]

        # Heavy payload with high sea state should give catamaran
        assert hull["hull_type"] == "catamaran"


class TestNavalArchitectMemoryIntegration:
    """Test Naval Architect memory integration."""

    def test_no_mission_error(self, temp_memory_dir):
        """Test error when mission not available."""
        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        response = agent.design_hull()

        assert response.confidence == 0.0
        assert "No mission data" in response.content

    def test_design_from_memory(self, temp_memory_dir, memory, sample_mission):
        """Test designing hull from mission in memory."""
        # Write mission to memory
        memory.write("mission", sample_mission)

        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        response = agent.design_hull()

        assert response.confidence > 0
        assert len(response.proposals) > 0

        # Check hull params were written to memory
        hull_params = memory.read("hull_params")
        assert hull_params is not None
        assert "hull_type" in hull_params

    def test_updates_system_state(self, temp_memory_dir, memory, sample_mission):
        """Test agent updates system state."""
        memory.write("mission", sample_mission)

        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        agent.design_hull()

        state = memory.get_system_state()
        assert state.current_phase == DesignPhase.HULL_FORM
        assert "hull" in state.status.lower()

    def test_process_method(self, temp_memory_dir, memory, sample_mission):
        """Test process method entry point."""
        memory.write("mission", sample_mission)

        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        response = agent.process({})

        assert isinstance(response, AgentResponse)
        assert response.confidence > 0


class TestNavalArchitectValidation:
    """Test hull parameter validation."""

    def test_coefficient_consistency(self, temp_memory_dir, memory, sample_mission):
        """Test coefficient consistency validation."""
        memory.write("mission", sample_mission)

        agent = NavalArchitectAgent(
            agent_id="naval_arch_test",
            memory_path=temp_memory_dir,
        )

        response = agent.design_hull()
        hull = response.proposals[0]

        # Check Cb = Cp * Cm relationship
        cb = hull.get("block_coefficient", 0)
        cp = hull.get("prismatic_coefficient", 0)
        cm = hull.get("midship_coefficient", 0)

        # Should be approximately equal
        expected_cb = cp * cm
        assert abs(cb - expected_cb) < 0.05, f"Cb={cb} but Cp*Cm={expected_cb}"


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_naval_architect(self, temp_memory_dir):
        """Test create_naval_architect convenience function."""
        agent = create_naval_architect(memory_path=temp_memory_dir)
        assert isinstance(agent, NavalArchitectAgent)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
