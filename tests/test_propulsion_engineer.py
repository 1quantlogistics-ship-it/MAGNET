"""
Tests for PropulsionEngineer agent.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from agents.propulsion_engineer import (
    PropulsionEngineerAgent,
    create_propulsion_engineer,
    ENGINE_DATABASE,
)
from agents.base import AgentResponse
from memory.file_io import MemoryFileIO


class TestPropulsionEngineerAgent:
    """Test PropulsionEngineer agent basic functionality."""

    def test_creation(self):
        """Test agent creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)
            assert agent.agent_id == "propulsion_engineer_001"
            assert agent.agent_type == "propulsion_engineer"

    def test_system_prompt(self):
        """Test system prompt exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)
            assert "Propulsion Engineer" in agent.system_prompt
            assert "engine" in agent.system_prompt.lower()
            assert "propeller" in agent.system_prompt.lower()


class TestEngineSelection:
    """Test engine selection logic."""

    def test_select_engines_finds_match(self):
        """Test engine selection finds appropriate engines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)

            # Need 2500 kW total, should find MTU 12V2000 (2 x 1432 = 2864 kW)
            engine = agent._select_engines(2500, num_engines=2)
            assert engine is not None
            # Selection allows 85% of requirement (slight underpowering)
            assert engine["total_power"] >= 2500 * 0.85

    def test_select_engines_smaller_requirement(self):
        """Test engine selection for smaller power requirement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)

            # Need 1200 kW total, should find Volvo D13-1000 (2 x 736 = 1472 kW)
            engine = agent._select_engines(1200, num_engines=2)
            assert engine is not None
            assert engine["total_power"] >= 1200

    def test_select_engines_no_match(self):
        """Test engine selection when no suitable engine exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)

            # Need 10000 kW total - nothing can provide this
            engine = agent._select_engines(10000, num_engines=2)
            assert engine is None


class TestPropellerSizing:
    """Test propeller sizing calculations."""

    def test_propeller_sizing_basic(self):
        """Test basic propeller sizing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)

            prop = agent._calculate_propeller_size(
                shaft_power_kw=1500,
                rpm=1400,
                draft_m=2.5,
                speed_kts=35
            )

            assert prop["type"] == "fixed_pitch"
            assert prop["diameter_mm"] > 0
            assert prop["pitch_mm"] > 0
            assert prop["blades"] in [4, 5]
            assert "pd_ratio" in prop

    def test_propeller_draft_limit(self):
        """Test propeller diameter limited by draft."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)

            prop = agent._calculate_propeller_size(
                shaft_power_kw=3000,
                rpm=1400,
                draft_m=1.5,  # Shallow draft
                speed_kts=40
            )

            # Max diameter is 70% of draft = 1.05m = 1050mm
            assert prop["diameter_mm"] <= 1.5 * 0.7 * 1000 + 50  # Small tolerance


class TestRangeCalculation:
    """Test range and endurance calculations."""

    def test_range_calculation_basic(self):
        """Test basic range calculation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)

            range_data = agent._calculate_range(
                fuel_capacity_l=4500,
                consumption_lph=500,
                speed_kts=25,
                reserve_fraction=0.10
            )

            # Usable fuel = 4500 * 0.9 = 4050 L
            # Endurance = 4050 / 500 = 8.1 hrs
            # Range = 8.1 * 25 = 202.5 nm
            assert range_data["usable_fuel_l"] == 4050
            assert abs(range_data["endurance_hrs"] - 8.1) < 0.1
            assert abs(range_data["range_nm"] - 202) < 5


class TestPropulsionDesign:
    """Test full propulsion design workflow."""

    @pytest.fixture
    def memory_with_data(self):
        """Create memory with hull_params and mission."""
        tmpdir = tempfile.mkdtemp()

        memory = MemoryFileIO(tmpdir)

        # Write mission
        memory.write("mission", {
            "mission_id": "TEST-001",
            "vessel_type": "patrol_catamaran",
            "design_speed_kts": 35,
            "cruise_speed_kts": 25,
            "endurance_nm": 300,
            "crew": 8,
            "fuel_capacity_l": 4500,
        }, validate=False)

        # Write hull_params with resistance data
        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.8,
            "draft": 2.1,
            "depth": 4.5,
            "block_coefficient": 0.45,
            "displacement_tonnes": 180,
            "resistance": {
                "design_speed_kts": 35,
                "delivered_power_kW": 2500,
            }
        }, validate=False)

        yield tmpdir

        # Cleanup
        shutil.rmtree(tmpdir)

    def test_design_propulsion_with_data(self, memory_with_data):
        """Test propulsion design with complete input data."""
        agent = PropulsionEngineerAgent(memory_path=memory_with_data)

        response = agent.design_propulsion()

        assert isinstance(response, AgentResponse)
        assert response.confidence > 0
        assert "Propulsion:" in response.content
        assert len(response.proposals) > 0

        propulsion_config = response.proposals[0]
        assert "main_engines" in propulsion_config
        assert "propellers" in propulsion_config
        assert "performance" in propulsion_config

    def test_design_propulsion_no_hull(self):
        """Test propulsion design fails without hull params."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = PropulsionEngineerAgent(memory_path=tmpdir)

            response = agent.design_propulsion()

            assert response.confidence == 0
            assert "hull" in response.content.lower()

    def test_design_propulsion_no_mission(self):
        """Test propulsion design fails without mission."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)
            memory.write("hull_params", {"hull_type": "test"}, validate=False)

            agent = PropulsionEngineerAgent(memory_path=tmpdir)
            response = agent.design_propulsion()

            assert response.confidence == 0
            assert "mission" in response.content.lower()

    def test_design_propulsion_writes_to_memory(self, memory_with_data):
        """Test propulsion design writes config to memory."""
        agent = PropulsionEngineerAgent(memory_path=memory_with_data)
        memory = MemoryFileIO(memory_with_data)

        response = agent.design_propulsion()

        # Check propulsion_config was written
        config = memory.read("propulsion_config")
        assert config is not None
        assert "main_engines" in config
        assert "propulsion_type" in config

    def test_design_propulsion_range_warning(self, memory_with_data):
        """Test propulsion design warns when range insufficient."""
        memory = MemoryFileIO(memory_with_data)

        # Update mission to require very long range
        memory.write("mission", {
            "mission_id": "TEST-001",
            "design_speed_kts": 35,
            "cruise_speed_kts": 25,
            "endurance_nm": 1000,  # Very long range requirement
            "fuel_capacity_l": 2000,  # Limited fuel
        }, validate=False)

        agent = PropulsionEngineerAgent(memory_path=memory_with_data)
        response = agent.design_propulsion()

        # Should have range concern
        assert any("range" in c.lower() for c in response.concerns)


class TestProcessMethod:
    """Test the process() entry point."""

    def test_process_reads_from_memory(self):
        """Test process method reads data from memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)

            # Write required data
            memory.write("mission", {
                "mission_id": "TEST-002",
                "design_speed_kts": 30,
                "cruise_speed_kts": 20,
            }, validate=False)

            memory.write("hull_params", {
                "hull_type": "displacement",
                "draft": 2.0,
                "resistance": {"delivered_power_kW": 1500},
            }, validate=False)

            agent = PropulsionEngineerAgent(memory_path=tmpdir)
            response = agent.process({})

            assert response.confidence > 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_propulsion_engineer(self):
        """Test create_propulsion_engineer function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_propulsion_engineer(memory_path=tmpdir)

            assert isinstance(agent, PropulsionEngineerAgent)
            assert agent.agent_type == "propulsion_engineer"


class TestEngineDatabase:
    """Test engine database contents."""

    def test_engine_database_not_empty(self):
        """Test engine database has entries."""
        assert len(ENGINE_DATABASE) > 0

    def test_engine_database_structure(self):
        """Test engine database entries have required fields."""
        required_fields = [
            "manufacturer",
            "model",
            "power_kw",
            "weight_kg",
            "fuel_consumption_full_lph",
            "fuel_consumption_75_lph",
        ]

        for engine in ENGINE_DATABASE:
            for field in required_fields:
                assert field in engine, f"Engine {engine.get('model', 'unknown')} missing {field}"

    def test_engine_database_power_range(self):
        """Test engine database covers useful power range."""
        powers = [e["power_kw"] for e in ENGINE_DATABASE]

        assert min(powers) < 1000  # Some smaller options
        assert max(powers) > 1500  # Some larger options
