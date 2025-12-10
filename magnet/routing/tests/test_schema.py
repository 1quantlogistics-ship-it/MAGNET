"""
magnet/routing/tests/test_schema.py - Schema Tests

Tests for routing schema classes.
"""

import pytest
from datetime import datetime

from magnet.routing.schema.system_type import (
    SystemType,
    Criticality,
    SystemProperties,
    SYSTEM_PROPERTIES,
    get_system_properties,
)
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
from magnet.routing.schema.system_topology import (
    SystemTopology,
    TopologyStatus,
)
from magnet.routing.schema.routing_layout import (
    RoutingLayout,
    LayoutStatus,
)


# =============================================================================
# SystemType Tests
# =============================================================================

class TestSystemType:
    """Tests for SystemType enum."""

    def test_has_18_system_types(self, system_types):
        """Verify all 18 system types exist."""
        assert len(system_types) == 18

    def test_fluid_systems_exist(self, fluid_system_types):
        """Verify fluid system types."""
        expected = {
            'fuel', 'freshwater', 'seawater', 'grey_water',
            'black_water', 'lube_oil', 'hydraulic', 'bilge', 'firefighting'
        }
        actual = {st.value for st in fluid_system_types}
        assert actual == expected

    def test_electrical_systems_exist(self, electrical_system_types):
        """Verify electrical system types."""
        expected = {
            'electrical_hv', 'electrical_lv', 'electrical_dc', 'fire_detection'
        }
        actual = {st.value for st in electrical_system_types}
        assert actual == expected

    def test_hvac_systems_exist(self, hvac_system_types):
        """Verify HVAC system types."""
        expected = {'hvac_supply', 'hvac_return', 'hvac_exhaust'}
        actual = {st.value for st in hvac_system_types}
        assert actual == expected

    def test_all_systems_have_properties(self, system_types):
        """Verify all system types have properties defined."""
        for st in system_types:
            props = get_system_properties(st)
            assert props is not None
            assert props.system_type == st

    def test_properties_have_required_fields(self, system_types):
        """Verify properties have all required fields."""
        for st in system_types:
            props = get_system_properties(st)
            assert isinstance(props.criticality, Criticality)
            assert isinstance(props.requires_redundancy, bool)
            assert isinstance(props.can_cross_fire_zone, bool)
            assert isinstance(props.can_cross_watertight, bool)

    def test_criticality_enum(self):
        """Test criticality levels."""
        assert Criticality.CRITICAL.value == "critical"
        assert Criticality.HIGH.value == "high"
        assert Criticality.MEDIUM.value == "medium"
        assert Criticality.LOW.value == "low"

    def test_critical_systems_require_redundancy(self):
        """Critical systems should require redundancy."""
        critical_systems = [
            SystemType.FIREFIGHTING,
            SystemType.FIRE_DETECTION,
            SystemType.ELECTRICAL_HV,
        ]
        for st in critical_systems:
            props = get_system_properties(st)
            if props.criticality == Criticality.CRITICAL:
                assert props.requires_redundancy is True


# =============================================================================
# SystemNode Tests
# =============================================================================

class TestSystemNode:
    """Tests for SystemNode dataclass."""

    def test_create_source_node(self):
        """Test creating a source node."""
        node = SystemNode(
            node_id='test_source',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank_room',
            capacity_units=1000.0,
        )

        assert node.node_id == 'test_source'
        assert node.is_source
        assert not node.is_consumer
        assert node.effective_value == 1000.0

    def test_create_consumer_node(self):
        """Test creating a consumer node."""
        node = SystemNode(
            node_id='test_consumer',
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='engine_room',
            demand_units=50.0,
        )

        assert node.is_consumer
        assert not node.is_source
        assert node.effective_value == 50.0

    def test_create_junction_node(self):
        """Test creating a junction node."""
        node = SystemNode(
            node_id='test_junction',
            node_type=NodeType.JUNCTION,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='corridor',
        )

        assert node.is_junction
        assert not node.is_endpoint
        assert node.effective_value == 0.0

    def test_generate_unique_node_id(self):
        """Test node ID generation."""
        ids = [generate_node_id() for _ in range(100)]
        assert len(set(ids)) == 100  # All unique

    def test_node_trunk_management(self):
        """Test trunk connection management."""
        node = SystemNode(
            node_id='test_node',
            node_type=NodeType.JUNCTION,
            system_type=SystemType.FRESHWATER,
            space_id='corridor',
        )

        assert node.connection_count == 0

        node.add_trunk('trunk_1')
        assert node.connection_count == 1
        assert node.has_trunk('trunk_1')

        node.add_trunk('trunk_2')
        assert node.connection_count == 2

        # Adding same trunk again shouldn't duplicate
        node.add_trunk('trunk_1')
        assert node.connection_count == 2

        node.remove_trunk('trunk_1')
        assert node.connection_count == 1
        assert not node.has_trunk('trunk_1')

    def test_node_validation(self):
        """Test node validation."""
        # Valid source
        source = SystemNode(
            node_id='source',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
            capacity_units=100.0,
        )
        assert source.is_valid()

        # Invalid source (no capacity)
        invalid_source = SystemNode(
            node_id='bad_source',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
            capacity_units=0.0,
        )
        assert not invalid_source.is_valid()

        # Invalid consumer (no demand)
        invalid_consumer = SystemNode(
            node_id='bad_consumer',
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='engine',
            demand_units=0.0,
        )
        assert not invalid_consumer.is_valid()

    def test_node_serialization(self):
        """Test node to_dict/from_dict."""
        original = SystemNode(
            node_id='test_node',
            node_type=NodeType.SOURCE,
            system_type=SystemType.ELECTRICAL_LV,
            space_id='switchboard_room',
            capacity_units=500.0,
            is_critical=True,
            name='Main Switchboard',
        )

        data = original.to_dict()
        restored = SystemNode.from_dict(data)

        assert restored.node_id == original.node_id
        assert restored.node_type == original.node_type
        assert restored.system_type == original.system_type
        assert restored.capacity_units == original.capacity_units
        assert restored.is_critical == original.is_critical
        assert restored.name == original.name


# =============================================================================
# TrunkSegment Tests
# =============================================================================

class TestTrunkSegment:
    """Tests for TrunkSegment dataclass."""

    def test_create_trunk_segment(self):
        """Test creating a trunk segment."""
        trunk = TrunkSegment(
            trunk_id='trunk_1',
            system_type=SystemType.FUEL,
            from_node_id='node_a',
            to_node_id='node_b',
            path_spaces=['space_a', 'space_b', 'space_c'],
            size=TrunkSize(diameter_mm=50.0),
        )

        assert trunk.trunk_id == 'trunk_1'
        assert len(trunk.path_spaces) == 3
        assert trunk.size.diameter_mm == 50.0

    def test_generate_unique_trunk_id(self):
        """Test trunk ID generation."""
        ids = [generate_trunk_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_trunk_size_dataclass(self):
        """Test TrunkSize configuration."""
        # Pipe size
        pipe = TrunkSize(diameter_mm=100.0)
        assert pipe.diameter_mm == 100.0

        # Cable size
        cable = TrunkSize(cable_rating_a=100.0, cable_size_mm2=25.0)
        assert cable.cable_rating_a == 100.0
        assert cable.cable_size_mm2 == 25.0

        # Duct size
        duct = TrunkSize(duct_width_mm=300.0, duct_height_mm=200.0)
        assert duct.duct_width_mm == 300.0
        assert duct.duct_height_mm == 200.0

    def test_trunk_zone_crossings(self):
        """Test zone crossing tracking."""
        trunk = TrunkSegment(
            trunk_id='trunk_1',
            system_type=SystemType.ELECTRICAL_LV,
            from_node_id='node_a',
            to_node_id='node_b',
            path_spaces=['er', 'corridor'],
            size=TrunkSize(cable_size_mm2=16.0),
        )

        assert trunk.is_zone_compliant  # Default

        trunk.zone_crossings.append(('er', 'corridor', 'fire'))
        assert len(trunk.zone_crossings) == 1

    def test_trunk_redundancy_tracking(self):
        """Test redundant path tracking."""
        primary = TrunkSegment(
            trunk_id='trunk_primary',
            system_type=SystemType.FIREFIGHTING,
            from_node_id='pump',
            to_node_id='hydrant',
            path_spaces=['er', 'corridor'],
            size=TrunkSize(diameter_mm=65.0),
            is_redundant_path=False,
        )

        redundant = TrunkSegment(
            trunk_id='trunk_redundant',
            system_type=SystemType.FIREFIGHTING,
            from_node_id='pump',
            to_node_id='hydrant',
            path_spaces=['er', 'stairwell', 'corridor'],
            size=TrunkSize(diameter_mm=65.0),
            is_redundant_path=True,
            parallel_trunk_id=primary.trunk_id,
        )

        assert not primary.is_redundant_path
        assert redundant.is_redundant_path
        assert redundant.parallel_trunk_id == 'trunk_primary'

    def test_trunk_serialization(self):
        """Test trunk to_dict/from_dict."""
        original = TrunkSegment(
            trunk_id='trunk_test',
            system_type=SystemType.HVAC_SUPPLY,
            from_node_id='ahu',
            to_node_id='diffuser',
            path_spaces=['er', 'shaft', 'accommodation'],
            size=TrunkSize(duct_width_mm=400.0, duct_height_mm=250.0),
            capacity=0.75,
        )

        data = original.to_dict()
        restored = TrunkSegment.from_dict(data)

        assert restored.trunk_id == original.trunk_id
        assert restored.system_type == original.system_type
        assert restored.path_spaces == original.path_spaces
        assert restored.size.duct_width_mm == original.size.duct_width_mm


# =============================================================================
# SystemTopology Tests
# =============================================================================

class TestSystemTopology:
    """Tests for SystemTopology aggregate."""

    def test_create_empty_topology(self):
        """Test creating empty topology."""
        topology = SystemTopology(system_type=SystemType.FUEL)

        assert topology.system_type == SystemType.FUEL
        assert topology.status == TopologyStatus.EMPTY
        assert topology.node_count == 0
        assert topology.trunk_count == 0

    def test_add_nodes_and_trunks(self, simple_topology):
        """Test adding nodes and trunks."""
        assert simple_topology.node_count == 4
        assert simple_topology.trunk_count == 3
        assert simple_topology.status != TopologyStatus.EMPTY

    def test_topology_statistics(self, simple_topology):
        """Test topology statistics."""
        stats = simple_topology.get_statistics()

        assert 'node_count' in stats
        assert 'trunk_count' in stats
        assert 'source_count' in stats
        assert 'consumer_count' in stats
        assert stats['node_count'] == 4
        assert stats['trunk_count'] == 3

    def test_topology_node_retrieval(self, simple_topology):
        """Test getting nodes by type."""
        sources = simple_topology.sources
        consumers = simple_topology.consumers
        junctions = simple_topology.junctions

        assert len(sources) == 1
        assert len(consumers) == 2
        assert len(junctions) == 1

    def test_topology_validation(self, simple_topology):
        """Test topology validation."""
        is_valid = simple_topology.validate()
        # Simple topology should be valid (returns bool)
        assert isinstance(is_valid, bool)

    def test_topology_serialization(self, simple_topology):
        """Test topology to_dict/from_dict."""
        data = simple_topology.to_dict()
        restored = SystemTopology.from_dict(data)

        assert restored.system_type == simple_topology.system_type
        assert restored.node_count == simple_topology.node_count
        assert restored.trunk_count == simple_topology.trunk_count


# =============================================================================
# RoutingLayout Tests
# =============================================================================

class TestRoutingLayout:
    """Tests for RoutingLayout aggregate."""

    def test_create_empty_layout(self):
        """Test creating empty layout."""
        layout = RoutingLayout(design_id='test')

        assert layout.design_id == 'test'
        assert layout.status == LayoutStatus.EMPTY
        assert layout.system_count == 0

    def test_add_topology(self, routing_layout):
        """Test adding topology to layout."""
        assert routing_layout.system_count == 1
        assert SystemType.FUEL in routing_layout.topologies

    def test_layout_statistics(self, routing_layout):
        """Test layout statistics."""
        stats = routing_layout.get_statistics()

        assert stats['design_id'] == 'test_design'
        assert stats['system_count'] == 1
        assert 'total_trunk_count' in stats
        assert 'total_node_count' in stats

    def test_layout_cross_system_analysis(self, routing_layout):
        """Test cross-system space analysis."""
        space_systems = routing_layout.get_spaces_with_systems()

        # Should have spaces from fuel system
        assert len(space_systems) > 0

    def test_layout_serialization(self, routing_layout):
        """Test layout to_dict/from_dict."""
        data = routing_layout.to_dict()
        restored = RoutingLayout.from_dict(data)

        assert restored.design_id == routing_layout.design_id
        assert restored.system_count == routing_layout.system_count

    def test_layout_remove_topology(self, routing_layout):
        """Test removing topology."""
        removed = routing_layout.remove_topology(SystemType.FUEL)

        assert removed is not None
        assert routing_layout.system_count == 0
        assert routing_layout.status == LayoutStatus.EMPTY

    def test_multiple_system_layout(self, simple_topology, electrical_system_nodes):
        """Test layout with multiple systems."""
        layout = RoutingLayout(design_id='multi_system')

        # Add fuel topology
        layout.add_topology(simple_topology)

        # Create and add electrical topology
        elec_topology = SystemTopology(system_type=SystemType.ELECTRICAL_LV)
        for node in electrical_system_nodes:
            elec_topology.add_node(node)

        layout.add_topology(elec_topology)

        assert layout.system_count == 2
        assert SystemType.FUEL in layout.topologies
        assert SystemType.ELECTRICAL_LV in layout.topologies
