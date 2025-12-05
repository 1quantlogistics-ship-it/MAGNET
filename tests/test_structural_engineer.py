"""
Tests for StructuralEngineer agent.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from agents.structural_engineer import (
    StructuralEngineerAgent,
    create_structural_engineer,
    ALPHA_STRUCTURAL_AVAILABLE,
)
from agents.base import AgentResponse
from memory.file_io import MemoryFileIO

# Skip all tests if ALPHA structural module not available
pytestmark = pytest.mark.skipif(
    not ALPHA_STRUCTURAL_AVAILABLE,
    reason="ALPHA structural module not available"
)


class TestStructuralEngineerAgent:
    """Test StructuralEngineer agent basic functionality."""

    def test_creation(self):
        """Test agent creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            assert agent.agent_id == "structural_engineer_001"
            assert agent.agent_type == "structural_engineer"

    def test_system_prompt(self):
        """Test system prompt exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            assert "Structural Engineer" in agent.system_prompt
            assert "scantling" in agent.system_prompt.lower()
            assert "plate" in agent.system_prompt.lower()

    def test_alloy_default(self):
        """Test default alloy is set."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            assert agent.alloy is not None
            assert "5083" in agent.alloy.value


class TestServiceTypeMapping:
    """Test service type determination from mission."""

    def test_patrol_vessel(self):
        """Test patrol vessel mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            mission = {"vessel_type": "patrol_catamaran"}
            assert agent._get_service_type(mission) == "patrol_vessel"

    def test_passenger_ferry(self):
        """Test passenger ferry mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            mission = {"vessel_type": "passenger_ferry"}
            assert agent._get_service_type(mission) == "passenger_ferry"

    def test_military_vessel(self):
        """Test military vessel mapping."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            mission = {"vessel_type": "military_interceptor"}
            assert agent._get_service_type(mission) == "patrol_vessel"

    def test_default_workboat(self):
        """Test default to workboat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            mission = {"vessel_type": "unknown_type"}
            assert agent._get_service_type(mission) == "workboat"

    def test_none_mission(self):
        """Test None mission defaults to workboat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)
            assert agent._get_service_type(None) == "workboat"


class TestPressureCalculation:
    """Test design pressure calculations."""

    @pytest.fixture
    def memory_with_hull(self):
        """Create memory with hull_params."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.8,
            "draft": 2.1,
            "depth": 4.5,
            "block_coefficient": 0.45,
            "displacement_tonnes": 180,
            "deadrise_angle": 15.0,
        }, validate=False)

        memory.write("mission", {
            "mission_id": "TEST-001",
            "vessel_type": "patrol_catamaran",
            "design_speed_kts": 35,
            "cruise_speed_kts": 25,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_pressure_calculation(self, memory_with_hull):
        """Test pressure calculation runs."""
        agent = StructuralEngineerAgent(memory_path=memory_with_hull)
        hull, mission = agent._read_design_data()

        pressures = agent._calculate_zone_pressures(hull, mission)

        assert len(pressures) > 0
        # Bottom forward should have highest pressure
        from physics.structural.pressure import PressureZone
        assert PressureZone.BOTTOM_FORWARD in pressures
        assert pressures[PressureZone.BOTTOM_FORWARD].design_pressure > 0


class TestPlatingSchedule:
    """Test plating schedule generation."""

    @pytest.fixture
    def memory_with_data(self):
        """Create memory with hull_params and mission."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.8,
            "draft": 2.1,
            "depth": 4.5,
            "block_coefficient": 0.45,
            "displacement_tonnes": 180,
        }, validate=False)

        memory.write("mission", {
            "mission_id": "TEST-001",
            "vessel_type": "patrol_catamaran",
            "design_speed_kts": 35,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_plating_schedule_generation(self, memory_with_data):
        """Test plating schedule is generated."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)
        hull, mission = agent._read_design_data()

        pressures = agent._calculate_zone_pressures(hull, mission)
        schedule = agent._generate_plating_schedule(
            pressures, hull,
            stiffener_spacing=400,
            frame_spacing=500,
        )

        assert schedule is not None
        assert len(schedule.zones) > 0
        assert schedule.bottom_thickness > 0
        assert schedule.side_thickness > 0

    def test_plating_minimum_thickness(self, memory_with_data):
        """Test minimum plate thickness is respected."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)
        hull, mission = agent._read_design_data()

        pressures = agent._calculate_zone_pressures(hull, mission)
        schedule = agent._generate_plating_schedule(
            pressures, hull,
            stiffener_spacing=400,
            frame_spacing=500,
        )

        # All plates should be at least 4mm (ABS minimum)
        for zone_name, result in schedule.zones.items():
            assert result.proposed_thickness >= 4.0


class TestStiffenerSelection:
    """Test stiffener selection."""

    @pytest.fixture
    def memory_with_data(self):
        """Create memory with hull_params and mission."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.8,
            "draft": 2.1,
            "depth": 4.5,
            "displacement_tonnes": 180,
        }, validate=False)

        memory.write("mission", {
            "mission_id": "TEST-001",
            "design_speed_kts": 35,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_stiffener_selection(self, memory_with_data):
        """Test stiffeners are selected."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)
        hull, mission = agent._read_design_data()

        pressures = agent._calculate_zone_pressures(hull, mission)
        stiffeners = agent._calculate_stiffeners(
            pressures,
            stiffener_spacing=400,
            frame_spacing=500,
        )

        assert len(stiffeners) > 0
        # Check at least one stiffener was selected
        selected_count = sum(
            1 for s in stiffeners.values()
            if s.selected_profile is not None
        )
        assert selected_count > 0


class TestStructuralDesign:
    """Test full structural design workflow."""

    @pytest.fixture
    def memory_with_data(self):
        """Create memory with hull_params and mission."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("mission", {
            "mission_id": "TEST-001",
            "vessel_type": "patrol_catamaran",
            "design_speed_kts": 35,
            "cruise_speed_kts": 25,
        }, validate=False)

        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.8,
            "draft": 2.1,
            "depth": 4.5,
            "block_coefficient": 0.45,
            "displacement_tonnes": 180,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_design_structure_with_data(self, memory_with_data):
        """Test structural design with complete input data."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)

        response = agent.design_structure()

        assert isinstance(response, AgentResponse)
        assert response.confidence > 0
        assert "Structural:" in response.content
        assert len(response.proposals) > 0

        structural_design = response.proposals[0]
        assert "material" in structural_design
        assert "plating" in structural_design
        assert "stiffeners" in structural_design
        assert "summary" in structural_design

    def test_design_structure_no_hull(self):
        """Test structural design fails without hull params."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(memory_path=tmpdir)

            response = agent.design_structure()

            assert response.confidence == 0
            assert "hull" in response.content.lower()

    def test_design_structure_writes_to_memory(self, memory_with_data):
        """Test structural design writes to memory."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)
        memory = MemoryFileIO(memory_with_data)

        response = agent.design_structure()

        # Check structural_design was written
        design = memory.read("structural_design")
        assert design is not None
        assert "material" in design
        assert "plating" in design

    def test_design_structure_summary(self, memory_with_data):
        """Test structural design includes summary."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)

        response = agent.design_structure()

        structural_design = response.proposals[0]
        summary = structural_design.get("summary", {})

        assert "bottom_thickness_mm" in summary
        assert "side_thickness_mm" in summary
        assert "deck_thickness_mm" in summary
        assert "estimated_plate_weight_kg" in summary


class TestProcessMethod:
    """Test the process() entry point."""

    def test_process_reads_from_memory(self):
        """Test process method reads data from memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)

            memory.write("mission", {
                "mission_id": "TEST-002",
                "design_speed_kts": 30,
            }, validate=False)

            memory.write("hull_params", {
                "hull_type": "displacement",
                "length_waterline": 40.0,
                "beam": 10.0,
                "draft": 2.0,
                "depth": 4.0,
                "displacement_tonnes": 150,
            }, validate=False)

            agent = StructuralEngineerAgent(memory_path=tmpdir)
            response = agent.process({})

            assert response.confidence > 0


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_structural_engineer(self):
        """Test create_structural_engineer function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = create_structural_engineer(memory_path=tmpdir)

            assert isinstance(agent, StructuralEngineerAgent)
            assert agent.agent_type == "structural_engineer"


class TestCompliance:
    """Test compliance checking."""

    @pytest.fixture
    def memory_with_data(self):
        """Create memory with hull_params and mission."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.8,
            "draft": 2.1,
            "depth": 4.5,
            "displacement_tonnes": 180,
        }, validate=False)

        memory.write("mission", {
            "mission_id": "TEST-001",
            "design_speed_kts": 35,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_compliance_check_in_summary(self, memory_with_data):
        """Test compliance is checked in summary."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)
        response = agent.design_structure()

        structural_design = response.proposals[0]
        summary = structural_design.get("summary", {})

        assert "all_plating_compliant" in summary
        assert "all_stiffeners_compliant" in summary


class TestMaterialSelection:
    """Test material selection."""

    def test_custom_alloy(self):
        """Test custom alloy can be specified."""
        from physics.structural.materials import AluminumAlloy

        with tempfile.TemporaryDirectory() as tmpdir:
            agent = StructuralEngineerAgent(
                memory_path=tmpdir,
                alloy=AluminumAlloy.AL_5456_H116
            )
            assert agent.alloy == AluminumAlloy.AL_5456_H116

    def test_alloy_in_output(self):
        """Test alloy is recorded in output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            memory = MemoryFileIO(tmpdir)

            memory.write("hull_params", {
                "hull_type": "displacement",
                "length_waterline": 40.0,
                "beam": 10.0,
                "draft": 2.0,
                "depth": 4.0,
                "displacement_tonnes": 150,
            }, validate=False)

            memory.write("mission", {
                "mission_id": "TEST-001",
                "design_speed_kts": 25,
            }, validate=False)

            agent = StructuralEngineerAgent(memory_path=tmpdir)
            response = agent.design_structure()

            structural_design = response.proposals[0]
            assert structural_design["material"]["alloy"] == agent.alloy.value


class TestMetadata:
    """Test metadata in response."""

    @pytest.fixture
    def memory_with_data(self):
        """Create memory with hull_params and mission."""
        tmpdir = tempfile.mkdtemp()
        memory = MemoryFileIO(tmpdir)

        memory.write("hull_params", {
            "hull_type": "semi_displacement",
            "length_overall": 48.0,
            "length_waterline": 45.0,
            "beam": 12.8,
            "draft": 2.1,
            "depth": 4.5,
            "displacement_tonnes": 180,
        }, validate=False)

        memory.write("mission", {
            "mission_id": "TEST-001",
            "design_speed_kts": 35,
        }, validate=False)

        yield tmpdir
        shutil.rmtree(tmpdir)

    def test_metadata_includes_key_values(self, memory_with_data):
        """Test metadata includes key design values."""
        agent = StructuralEngineerAgent(memory_path=memory_with_data)
        response = agent.design_structure()

        assert "alloy" in response.metadata
        assert "bottom_thickness_mm" in response.metadata
        assert "side_thickness_mm" in response.metadata
        assert "plate_weight_kg" in response.metadata
        assert "frame_spacing_mm" in response.metadata
