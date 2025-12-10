"""
magnet/routing/tests/conftest.py - Test Fixtures

Pytest fixtures for routing tests.
"""

import pytest
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field

# Import routing schema
from magnet.routing.schema.system_type import SystemType, Criticality
from magnet.routing.schema.system_node import (
    SystemNode,
    NodeType,
    generate_node_id,
)
from magnet.routing.schema.trunk_segment import (
    TrunkSegment,
    TrunkSize,
    generate_trunk_id,
)
from magnet.routing.schema.system_topology import SystemTopology
from magnet.routing.schema.routing_layout import RoutingLayout


# =============================================================================
# Mock Space Classes (M59 Integration)
# =============================================================================

@dataclass
class MockBoundingBox:
    """Mock bounding box for testing."""
    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 10.0
    max_y: float = 10.0
    max_z: float = 3.0

    @property
    def center(self) -> Tuple[float, float, float]:
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        )


@dataclass
class MockSpace:
    """Mock space for testing."""
    space_id: str
    space_type: str = "compartment"
    bounds: MockBoundingBox = field(default_factory=MockBoundingBox)
    is_routable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Basic Fixtures
# =============================================================================

@pytest.fixture
def system_types() -> List[SystemType]:
    """Get all system types."""
    return list(SystemType)


@pytest.fixture
def fluid_system_types() -> List[SystemType]:
    """Get fluid system types."""
    return [
        SystemType.FUEL,
        SystemType.FRESHWATER,
        SystemType.SEAWATER,
        SystemType.GREY_WATER,
        SystemType.BLACK_WATER,
        SystemType.LUBE_OIL,
        SystemType.HYDRAULIC,
        SystemType.BILGE,
        SystemType.FIREFIGHTING,
    ]


@pytest.fixture
def electrical_system_types() -> List[SystemType]:
    """Get electrical system types."""
    return [
        SystemType.ELECTRICAL_HV,
        SystemType.ELECTRICAL_LV,
        SystemType.ELECTRICAL_DC,
        SystemType.FIRE_DETECTION,
    ]


@pytest.fixture
def hvac_system_types() -> List[SystemType]:
    """Get HVAC system types."""
    return [
        SystemType.HVAC_SUPPLY,
        SystemType.HVAC_RETURN,
        SystemType.HVAC_EXHAUST,
    ]


# =============================================================================
# Space Fixtures
# =============================================================================

@pytest.fixture
def simple_spaces() -> Dict[str, MockSpace]:
    """Create simple linear space arrangement."""
    return {
        'space_a': MockSpace(
            space_id='space_a',
            space_type='machinery',
            bounds=MockBoundingBox(0, 0, 0, 10, 10, 3),
        ),
        'space_b': MockSpace(
            space_id='space_b',
            space_type='corridor',
            bounds=MockBoundingBox(10, 0, 0, 20, 10, 3),
        ),
        'space_c': MockSpace(
            space_id='space_c',
            space_type='accommodation',
            bounds=MockBoundingBox(20, 0, 0, 30, 10, 3),
        ),
    }


@pytest.fixture
def vessel_spaces() -> Dict[str, MockSpace]:
    """Create realistic vessel space arrangement."""
    return {
        # Engine room
        'er_main': MockSpace(
            space_id='er_main',
            space_type='machinery',
            bounds=MockBoundingBox(0, 0, 0, 20, 15, 6),
        ),
        'er_aux': MockSpace(
            space_id='er_aux',
            space_type='machinery',
            bounds=MockBoundingBox(0, 15, 0, 20, 25, 6),
        ),
        # Corridors
        'corridor_main': MockSpace(
            space_id='corridor_main',
            space_type='corridor',
            bounds=MockBoundingBox(20, 5, 0, 50, 10, 3),
        ),
        'corridor_upper': MockSpace(
            space_id='corridor_upper',
            space_type='corridor',
            bounds=MockBoundingBox(20, 5, 3, 50, 10, 6),
        ),
        # Accommodation
        'cabin_01': MockSpace(
            space_id='cabin_01',
            space_type='accommodation',
            bounds=MockBoundingBox(50, 0, 3, 55, 5, 6),
        ),
        'cabin_02': MockSpace(
            space_id='cabin_02',
            space_type='accommodation',
            bounds=MockBoundingBox(55, 0, 3, 60, 5, 6),
        ),
        'mess': MockSpace(
            space_id='mess',
            space_type='accommodation',
            bounds=MockBoundingBox(50, 10, 3, 60, 20, 6),
        ),
        # Bridge
        'bridge': MockSpace(
            space_id='bridge',
            space_type='bridge',
            bounds=MockBoundingBox(55, 5, 6, 65, 15, 9),
        ),
        # Tanks
        'fuel_tank_1': MockSpace(
            space_id='fuel_tank_1',
            space_type='tank',
            bounds=MockBoundingBox(25, 0, 0, 35, 5, 3),
            is_routable=False,
        ),
        'fw_tank': MockSpace(
            space_id='fw_tank',
            space_type='tank',
            bounds=MockBoundingBox(35, 0, 0, 45, 5, 3),
            is_routable=False,
        ),
    }


# =============================================================================
# Node Fixtures
# =============================================================================

@pytest.fixture
def fuel_system_nodes() -> List[SystemNode]:
    """Create nodes for fuel system."""
    return [
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='fuel_tank_1',
            capacity_units=5000.0,  # liters
            name='Main Fuel Tank',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.JUNCTION,
            system_type=SystemType.FUEL,
            space_id='er_main',
            name='Fuel Manifold',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='er_main',
            demand_units=50.0,  # liters/hour
            name='Main Engine',
            is_critical=True,
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='er_aux',
            demand_units=25.0,
            name='Generator 1',
        ),
    ]


@pytest.fixture
def electrical_system_nodes() -> List[SystemNode]:
    """Create nodes for electrical system."""
    return [
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.SOURCE,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='er_main',
            capacity_units=500.0,  # kW
            name='Main Switchboard',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.JUNCTION,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='corridor_main',
            name='Distribution Panel',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='cabin_01',
            demand_units=2.0,  # kW
            name='Cabin 01 Load',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='cabin_02',
            demand_units=2.0,
            name='Cabin 02 Load',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='mess',
            demand_units=15.0,
            name='Galley Load',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='bridge',
            demand_units=10.0,
            name='Navigation Equipment',
            is_critical=True,
            requires_redundant_feed=True,
        ),
    ]


@pytest.fixture
def hvac_system_nodes() -> List[SystemNode]:
    """Create nodes for HVAC supply system."""
    return [
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.SOURCE,
            system_type=SystemType.HVAC_SUPPLY,
            space_id='er_aux',
            capacity_units=5000.0,  # m³/h
            name='AHU 1',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.JUNCTION,
            system_type=SystemType.HVAC_SUPPLY,
            space_id='corridor_upper',
            name='Supply Duct Junction',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.HVAC_SUPPLY,
            space_id='cabin_01',
            demand_units=100.0,
            name='Cabin 01 Diffuser',
        ),
        SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.CONSUMER,
            system_type=SystemType.HVAC_SUPPLY,
            space_id='bridge',
            demand_units=500.0,
            name='Bridge HVAC',
        ),
    ]


# =============================================================================
# Topology Fixtures
# =============================================================================

@pytest.fixture
def simple_topology(fuel_system_nodes) -> SystemTopology:
    """Create simple fuel system topology."""
    topology = SystemTopology(system_type=SystemType.FUEL)

    for node in fuel_system_nodes:
        topology.add_node(node)

    # Create simple trunk connections
    trunk1 = TrunkSegment(
        trunk_id=generate_trunk_id(),
        system_type=SystemType.FUEL,
        from_node_id=fuel_system_nodes[0].node_id,
        to_node_id=fuel_system_nodes[1].node_id,
        path_spaces=['fuel_tank_1', 'er_main'],
        size=TrunkSize(diameter_mm=50.0),
    )

    trunk2 = TrunkSegment(
        trunk_id=generate_trunk_id(),
        system_type=SystemType.FUEL,
        from_node_id=fuel_system_nodes[1].node_id,
        to_node_id=fuel_system_nodes[2].node_id,
        path_spaces=['er_main'],
        size=TrunkSize(diameter_mm=32.0),
    )

    trunk3 = TrunkSegment(
        trunk_id=generate_trunk_id(),
        system_type=SystemType.FUEL,
        from_node_id=fuel_system_nodes[1].node_id,
        to_node_id=fuel_system_nodes[3].node_id,
        path_spaces=['er_main', 'er_aux'],
        size=TrunkSize(diameter_mm=25.0),
    )

    topology.add_trunk(trunk1)
    topology.add_trunk(trunk2)
    topology.add_trunk(trunk3)

    return topology


@pytest.fixture
def routing_layout(simple_topology) -> RoutingLayout:
    """Create routing layout with fuel system."""
    layout = RoutingLayout(design_id='test_design')
    layout.add_topology(simple_topology)
    return layout


# =============================================================================
# Graph Fixtures
# =============================================================================

@pytest.fixture
def simple_adjacency() -> Dict[str, Set[str]]:
    """Simple space adjacency for testing."""
    return {
        'space_a': {'space_b'},
        'space_b': {'space_a', 'space_c'},
        'space_c': {'space_b'},
    }


@pytest.fixture
def vessel_adjacency() -> Dict[str, Set[str]]:
    """Vessel space adjacency."""
    return {
        'er_main': {'er_aux', 'corridor_main', 'fuel_tank_1'},
        'er_aux': {'er_main', 'corridor_main'},
        'corridor_main': {'er_main', 'er_aux', 'corridor_upper', 'fw_tank'},
        'corridor_upper': {'corridor_main', 'cabin_01', 'cabin_02', 'mess', 'bridge'},
        'cabin_01': {'corridor_upper', 'cabin_02'},
        'cabin_02': {'corridor_upper', 'cabin_01'},
        'mess': {'corridor_upper'},
        'bridge': {'corridor_upper'},
        'fuel_tank_1': {'er_main'},
        'fw_tank': {'corridor_main'},
    }


# =============================================================================
# Zone Fixtures
# =============================================================================

@pytest.fixture
def fire_zones() -> Dict[str, Set[str]]:
    """Fire zone definitions."""
    return {
        'fire_zone_1': {'er_main', 'er_aux'},  # Machinery
        'fire_zone_2': {'corridor_main', 'corridor_upper'},  # Circulation
        'fire_zone_3': {'cabin_01', 'cabin_02', 'mess'},  # Accommodation
        'fire_zone_4': {'bridge'},  # Navigation
    }


@pytest.fixture
def watertight_boundaries() -> Set[Tuple[str, str]]:
    """Watertight boundary pairs."""
    return {
        ('er_main', 'corridor_main'),
        ('corridor_main', 'cabin_01'),
    }
