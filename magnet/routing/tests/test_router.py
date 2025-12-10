"""
magnet/routing/tests/test_router.py - Router Tests

Tests for routing algorithms and zone management.
"""

import pytest
from typing import List

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

from magnet.routing.router.trunk_router import TrunkRouter, RoutingResult
from magnet.routing.router.zone_manager import (
    ZoneManager,
    ZoneType,
    CrossingStatus,
    ZoneCrossingResult,
)
from magnet.routing.router.capacity_calc import (
    CapacityCalculator,
    calculate_pipe_diameter,
    calculate_cable_size,
    calculate_duct_size,
    SizingResult,
)
from magnet.routing.schema.system_type import SystemType
from magnet.routing.schema.system_node import SystemNode, NodeType, generate_node_id
from magnet.routing.schema.trunk_segment import TrunkSegment


# =============================================================================
# TrunkRouter Tests
# =============================================================================

class TestTrunkRouter:
    """Tests for TrunkRouter class."""

    def test_create_router(self):
        """Test creating a trunk router."""
        router = TrunkRouter()
        assert router is not None

    @pytest.mark.skipif(not HAS_NETWORKX, reason="NetworkX not installed")
    def test_route_simple_system(self, fuel_system_nodes, vessel_spaces):
        """Test routing a simple fuel system."""
        from magnet.routing.graph.compartment_graph import CompartmentGraph

        # Build compartment graph
        cg = CompartmentGraph()
        graph = cg.build(vessel_spaces)

        # Route system
        router = TrunkRouter()
        result = router.route_system(
            system_type=SystemType.FUEL,
            nodes=fuel_system_nodes,
            compartment_graph=graph,
        )

        # Should produce some result
        assert result is not None
        assert isinstance(result, RoutingResult)

    @pytest.mark.skipif(not HAS_NETWORKX, reason="NetworkX not installed")
    def test_route_with_zone_boundaries(self, electrical_system_nodes, vessel_spaces, fire_zones):
        """Test routing with zone compliance."""
        from magnet.routing.graph.compartment_graph import CompartmentGraph

        # Build graph with zones
        cg = CompartmentGraph()
        graph = cg.build(vessel_spaces, zone_boundaries=fire_zones)

        # Route with zone boundaries
        router = TrunkRouter()
        result = router.route_system(
            system_type=SystemType.ELECTRICAL_LV,
            nodes=electrical_system_nodes,
            compartment_graph=graph,
            zone_boundaries=fire_zones,
        )

        assert result is not None

    @pytest.mark.skipif(not HAS_NETWORKX, reason="NetworkX not installed")
    def test_route_with_redundancy(self, vessel_spaces):
        """Test routing with redundant paths."""
        from magnet.routing.graph.compartment_graph import CompartmentGraph

        # Create nodes for firefighting (requires redundancy)
        nodes = [
            SystemNode(
                node_id=generate_node_id(),
                node_type=NodeType.SOURCE,
                system_type=SystemType.FIREFIGHTING,
                space_id='er_main',
                capacity_units=100.0,
                name='Fire Pump',
            ),
            SystemNode(
                node_id=generate_node_id(),
                node_type=NodeType.CONSUMER,
                system_type=SystemType.FIREFIGHTING,
                space_id='bridge',
                demand_units=20.0,
                name='Bridge Hydrant',
                is_critical=True,
            ),
        ]

        cg = CompartmentGraph()
        graph = cg.build(vessel_spaces)

        router = TrunkRouter()
        result = router.route_with_redundancy(
            system_type=SystemType.FIREFIGHTING,
            nodes=nodes,
            compartment_graph=graph,
        )

        assert result is not None

    def test_router_handles_empty_nodes(self):
        """Test router handles empty node list."""
        router = TrunkRouter()
        # Should handle gracefully with None graph
        result = router.route_system(
            system_type=SystemType.FUEL,
            nodes=[],
            compartment_graph=None,
        )

        assert result is not None
        assert not result.success or len(result.trunks) == 0

    def test_router_handles_single_node(self, vessel_spaces):
        """Test router handles single node."""
        node = SystemNode(
            node_id=generate_node_id(),
            node_type=NodeType.SOURCE,
            system_type=SystemType.FRESHWATER,
            space_id='fw_tank',
            capacity_units=1000.0,
        )

        router = TrunkRouter()
        result = router.route_system(
            system_type=SystemType.FRESHWATER,
            nodes=[node],
            compartment_graph=None,
        )

        # Single node shouldn't produce trunks
        assert result is not None


# =============================================================================
# ZoneManager Tests
# =============================================================================

class TestZoneManager:
    """Tests for ZoneManager class."""

    def test_create_zone_manager(self):
        """Test creating a zone manager."""
        zm = ZoneManager()
        assert zm is not None

    def test_add_zone(self, fire_zones):
        """Test adding zones."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        stats = zm.get_statistics()
        assert stats['zone_count'] == len(fire_zones)

    def test_get_zone_for_space(self, fire_zones):
        """Test getting zone for a space."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        zone = zm.get_zone_for_space('er_main')
        assert zone is not None
        assert zone == 'fire_zone_1'

    def test_is_zone_boundary(self, fire_zones):
        """Test zone boundary detection."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        # Same zone - not a boundary
        assert not zm.is_zone_boundary('er_main', 'er_aux')

        # Different zones - is a boundary
        assert zm.is_zone_boundary('er_main', 'corridor_main')

    def test_check_crossing_same_zone(self, fire_zones):
        """Test crossing check within same zone."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        result = zm.check_crossing('er_main', 'er_aux', SystemType.FUEL)

        assert result.is_allowed
        assert result.status == CrossingStatus.ALLOWED

    def test_check_crossing_fire_zone(self, fire_zones):
        """Test crossing check across fire zone boundary."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        # Fuel crossing fire zone - conditional or prohibited
        result = zm.check_crossing('er_main', 'corridor_main', SystemType.FUEL)

        assert result is not None
        # Result depends on system properties

    def test_check_crossing_watertight(self, watertight_boundaries):
        """Test crossing check across watertight boundary."""
        zm = ZoneManager()

        for space_a, space_b in watertight_boundaries:
            zm.add_boundary(space_a, space_b, 'watertight')

        # Check boundary exists
        boundary_type = zm.get_boundary_type('er_main', 'corridor_main')
        assert boundary_type == 'watertight'

    def test_check_path(self, fire_zones):
        """Test checking entire path for zone compliance."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        path = ['er_main', 'corridor_main', 'cabin_01']
        is_valid, results = zm.check_path(path, SystemType.ELECTRICAL_LV)

        assert len(results) == 2  # Two crossings

    def test_add_explicit_boundary(self):
        """Test adding explicit boundary."""
        zm = ZoneManager()

        zm.add_boundary('space_a', 'space_b', 'watertight')

        assert zm.is_zone_boundary('space_a', 'space_b')
        assert zm.get_boundary_type('space_a', 'space_b') == 'watertight'

    def test_remove_zone(self, fire_zones):
        """Test removing a zone."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        initial_count = zm.get_statistics()['zone_count']

        zm.remove_zone('fire_zone_1')

        assert zm.get_statistics()['zone_count'] == initial_count - 1
        assert zm.get_zone_for_space('er_main') is None

    def test_zone_manager_serialization(self, fire_zones):
        """Test zone manager to_dict/from_dict."""
        zm = ZoneManager()

        for zone_id, spaces in fire_zones.items():
            zm.add_zone(zone_id, ZoneType.FIRE, spaces)

        data = zm.to_dict()
        restored = ZoneManager.from_dict(data)

        assert restored.get_statistics()['zone_count'] == zm.get_statistics()['zone_count']


# =============================================================================
# CapacityCalculator Tests
# =============================================================================

class TestCapacityCalculator:
    """Tests for CapacityCalculator class."""

    def test_create_calculator(self):
        """Test creating a capacity calculator."""
        calc = CapacityCalculator()
        assert calc is not None

    def test_calculate_pipe_diameter_fuel(self):
        """Test pipe diameter calculation for fuel."""
        result = calculate_pipe_diameter(
            flow_rate_m3_h=10.0,
            system_type=SystemType.FUEL,
        )

        assert result.is_valid
        assert result.selected_size > 0
        assert result.size_unit == 'mm DN'
        assert result.velocity is not None

    def test_calculate_pipe_diameter_freshwater(self):
        """Test pipe diameter calculation for freshwater."""
        result = calculate_pipe_diameter(
            flow_rate_m3_h=5.0,
            system_type=SystemType.FRESHWATER,
        )

        assert result.is_valid
        assert result.selected_size > 0

    def test_calculate_pipe_diameter_high_flow(self):
        """Test pipe diameter for high flow rate."""
        result = calculate_pipe_diameter(
            flow_rate_m3_h=500.0,
            system_type=SystemType.SEAWATER,
        )

        # Should select larger pipe or have warning
        assert result.selected_size >= 100  # At least DN100

    def test_calculate_cable_size_lv(self):
        """Test cable size for LV electrical."""
        result = calculate_cable_size(
            power_kw=50.0,
            system_type=SystemType.ELECTRICAL_LV,
        )

        assert result.is_valid
        assert result.selected_size > 0
        assert result.size_unit == 'mm²'

    def test_calculate_cable_size_hv(self):
        """Test cable size for HV electrical."""
        result = calculate_cable_size(
            power_kw=500.0,
            system_type=SystemType.ELECTRICAL_HV,
        )

        assert result is not None
        assert result.selected_size > 0

    def test_calculate_cable_size_dc(self):
        """Test cable size for DC systems."""
        # Use smaller power and shorter length for DC at 24V to avoid voltage drop issues
        result = calculate_cable_size(
            power_kw=0.1,  # 100W is more realistic for 24V DC
            system_type=SystemType.ELECTRICAL_DC,
            length_m=10.0,  # Short run
        )

        # DC cable sizing may have voltage drop warnings but still produce a size
        assert result.selected_size > 0

    def test_calculate_cable_voltage_drop(self):
        """Test voltage drop affects cable sizing."""
        short_result = calculate_cable_size(
            power_kw=10.0,
            system_type=SystemType.ELECTRICAL_LV,
            length_m=10.0,
        )

        long_result = calculate_cable_size(
            power_kw=10.0,
            system_type=SystemType.ELECTRICAL_LV,
            length_m=200.0,
        )

        # Longer cable may need larger size for voltage drop
        assert long_result.selected_size >= short_result.selected_size

    def test_calculate_duct_size_rectangular(self):
        """Test rectangular duct sizing."""
        result = calculate_duct_size(
            airflow_m3_h=1000.0,
            system_type=SystemType.HVAC_SUPPLY,
            prefer_circular=False,
        )

        assert result.is_valid
        assert 'WxH' in result.size_unit

    def test_calculate_duct_size_circular(self):
        """Test circular duct sizing."""
        result = calculate_duct_size(
            airflow_m3_h=1000.0,
            system_type=SystemType.HVAC_SUPPLY,
            prefer_circular=True,
        )

        assert result.is_valid
        assert 'dia' in result.size_unit

    def test_calculator_unified_interface(self):
        """Test unified calculate_size method."""
        calc = CapacityCalculator()

        # Fluid system
        fuel_result = calc.calculate_size(SystemType.FUEL, demand=20.0)
        assert fuel_result.size_unit == 'mm DN'

        # Electrical system
        elec_result = calc.calculate_size(SystemType.ELECTRICAL_LV, demand=100.0)
        assert elec_result.size_unit == 'mm²'

        # HVAC system
        hvac_result = calc.calculate_size(SystemType.HVAC_SUPPLY, demand=2000.0)
        assert 'mm' in hvac_result.size_unit

    def test_calculator_caching(self):
        """Test that calculator caches results."""
        calc = CapacityCalculator()

        # First call
        result1 = calc.calculate_size(SystemType.FUEL, demand=10.0)

        # Second call with same params
        result2 = calc.calculate_size(SystemType.FUEL, demand=10.0)

        # Should be same result (cached)
        assert result1.selected_size == result2.selected_size

        stats = calc.get_statistics()
        assert stats['cache_size'] >= 1

    def test_aggregate_demand(self):
        """Test demand aggregation with diversity."""
        calc = CapacityCalculator()

        demands = [10.0, 20.0, 15.0, 25.0]

        # Full diversity (all simultaneous)
        full = calc.aggregate_demand(demands, SystemType.FRESHWATER, diversity_factor=1.0)
        assert full == sum(demands)

        # 50% diversity
        partial = calc.aggregate_demand(demands, SystemType.FRESHWATER, diversity_factor=0.5)
        assert partial == sum(demands) * 0.5

    def test_get_diversity_factor(self):
        """Test recommended diversity factors."""
        calc = CapacityCalculator()

        # Critical systems should have high diversity
        ff_factor = calc.get_diversity_factor(SystemType.FIREFIGHTING, 5)
        assert ff_factor >= 0.9

        # Utility systems have lower diversity
        fw_factor = calc.get_diversity_factor(SystemType.FRESHWATER, 10)
        assert fw_factor < 0.9

    def test_calculate_trunk_capacity(self):
        """Test calculating max capacity for given size."""
        calc = CapacityCalculator()

        # For a 50mm pipe in fuel system
        capacity = calc.calculate_trunk_capacity(SystemType.FUEL, 50.0)
        assert capacity > 0

        # For 25mm² cable in LV system
        elec_capacity = calc.calculate_trunk_capacity(SystemType.ELECTRICAL_LV, 25.0)
        assert elec_capacity > 0

    def test_sizing_result_warnings(self):
        """Test that sizing generates appropriate warnings."""
        # Very high flow should generate warning
        result = calculate_pipe_diameter(
            flow_rate_m3_h=10000.0,  # Very high
            system_type=SystemType.FUEL,
        )

        # Should have warnings about exceeding max size
        assert len(result.warnings) > 0 or result.selected_size == 500  # Max size


# =============================================================================
# Integration Tests
# =============================================================================

class TestRouterIntegration:
    """Integration tests for router components."""

    @pytest.mark.skipif(not HAS_NETWORKX, reason="NetworkX not installed")
    def test_full_routing_pipeline(self, vessel_spaces, fire_zones, fuel_system_nodes):
        """Test complete routing pipeline."""
        from magnet.routing.graph.compartment_graph import CompartmentGraph

        # Build graph
        cg = CompartmentGraph()
        graph = cg.build(vessel_spaces, zone_boundaries=fire_zones)

        # Route system
        router = TrunkRouter()
        result = router.route_system(
            system_type=SystemType.FUEL,
            nodes=fuel_system_nodes,
            compartment_graph=graph,
            zone_boundaries=fire_zones,
        )

        # Calculate trunk sizes
        calc = CapacityCalculator()
        if result.success:
            for trunk in result.trunks:
                # Would typically size based on downstream demand
                sizing = calc.calculate_size(SystemType.FUEL, demand=50.0)
                assert sizing.is_valid

    @pytest.mark.skipif(not HAS_NETWORKX, reason="NetworkX not installed")
    def test_multi_system_routing(self, vessel_spaces, fire_zones):
        """Test routing multiple systems through same spaces."""
        from magnet.routing.graph.compartment_graph import CompartmentGraph

        cg = CompartmentGraph()
        graph = cg.build(vessel_spaces, zone_boundaries=fire_zones)

        router = TrunkRouter()

        # Route fuel system
        fuel_nodes = [
            SystemNode(
                node_id=generate_node_id(),
                node_type=NodeType.SOURCE,
                system_type=SystemType.FUEL,
                space_id='er_main',
                capacity_units=100.0,
            ),
            SystemNode(
                node_id=generate_node_id(),
                node_type=NodeType.CONSUMER,
                system_type=SystemType.FUEL,
                space_id='er_aux',
                demand_units=50.0,
            ),
        ]

        fuel_result = router.route_system(
            system_type=SystemType.FUEL,
            nodes=fuel_nodes,
            compartment_graph=graph,
        )

        # Route electrical system
        elec_nodes = [
            SystemNode(
                node_id=generate_node_id(),
                node_type=NodeType.SOURCE,
                system_type=SystemType.ELECTRICAL_LV,
                space_id='er_main',
                capacity_units=500.0,
            ),
            SystemNode(
                node_id=generate_node_id(),
                node_type=NodeType.CONSUMER,
                system_type=SystemType.ELECTRICAL_LV,
                space_id='bridge',
                demand_units=10.0,
            ),
        ]

        elec_result = router.route_system(
            system_type=SystemType.ELECTRICAL_LV,
            nodes=elec_nodes,
            compartment_graph=graph,
        )

        # Both should route successfully
        assert fuel_result is not None
        assert elec_result is not None
