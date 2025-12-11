"""
magnet/routing/tests/test_v3_features.py - V3 Feature Tests

Tests for V3 enhancements:
- RoutingLineage with geometry/arrangement/input hashing
- Geometry quantization for stable hashing
- RoutingService façade
- Steiner tree routing
- RoutingDiff topology comparison
- Polyline visualization
"""

import pytest
from typing import Dict, Set, Tuple

from magnet.routing.contracts.routing_lineage import (
    RoutingLineage,
    LineageStatus,
    quantize_coordinate,
    quantize_point,
    compute_geometry_hash,
    compute_arrangement_hash,
)
from magnet.routing.contracts.routing_input import (
    RoutingInputContract,
    SpaceInfo,
)
from magnet.routing.schema.system_type import SystemType
from magnet.routing.schema.system_node import SystemNode, NodeType, generate_node_id
from magnet.routing.schema.trunk_segment import TrunkSegment, generate_trunk_id
from magnet.routing.schema.system_topology import SystemTopology
from magnet.routing.schema.routing_layout import RoutingLayout
from magnet.routing.analysis.routing_diff import (
    RoutingDiff,
    DiffType,
    TopologyDiff,
)
from magnet.routing.visualization.polyline_generator import (
    PolylineGenerator,
    CrossingType,
    SYSTEM_COLORS,
)


# =============================================================================
# Geometry Quantization Tests
# =============================================================================

class TestGeometryQuantization:
    """Tests for geometry quantization functions."""

    def test_quantize_coordinate_default_precision(self):
        """Test coordinate quantization with default 1cm precision."""
        # Values within precision should round to same value
        assert quantize_coordinate(1.004) == 1.00
        assert quantize_coordinate(1.006) == 1.01
        assert quantize_coordinate(1.005) == 1.00  # Rounds to even

    def test_quantize_coordinate_custom_precision(self):
        """Test coordinate quantization with custom precision."""
        # 10cm precision
        assert quantize_coordinate(1.04, 0.1) == 1.0
        assert quantize_coordinate(1.06, 0.1) == 1.1

        # 1m precision
        assert quantize_coordinate(1.4, 1.0) == 1.0
        assert quantize_coordinate(1.6, 1.0) == 2.0

    def test_quantize_point(self):
        """Test 3D point quantization."""
        point = (1.004, 2.006, 3.005)
        quantized = quantize_point(point, 0.01)

        # Use approximate comparison for floating point
        assert abs(quantized[0] - 1.00) < 1e-9
        assert abs(quantized[1] - 2.01) < 1e-9
        assert abs(quantized[2] - 3.00) < 1e-9

    def test_quantize_prevents_drift(self):
        """Test that quantization prevents floating point drift issues."""
        # These coordinates have minor floating point differences
        coord1 = 10.000000001
        coord2 = 9.999999999

        q1 = quantize_coordinate(coord1, 0.01)
        q2 = quantize_coordinate(coord2, 0.01)

        assert q1 == q2 == 10.0


# =============================================================================
# Geometry Hash Tests
# =============================================================================

class TestGeometryHash:
    """Tests for geometry hashing."""

    def test_geometry_hash_deterministic(self):
        """Test geometry hash is deterministic."""
        space_centers = {
            'space_a': (0.0, 0.0, 0.0),
            'space_b': (10.0, 0.0, 0.0),
            'space_c': (10.0, 10.0, 0.0),
        }

        hash1 = compute_geometry_hash(space_centers)
        hash2 = compute_geometry_hash(space_centers)

        assert hash1 == hash2
        assert len(hash1) == 32

    def test_geometry_hash_order_independent(self):
        """Test hash is independent of insertion order."""
        centers1 = {'a': (0.0, 0.0, 0.0), 'b': (1.0, 0.0, 0.0)}
        centers2 = {'b': (1.0, 0.0, 0.0), 'a': (0.0, 0.0, 0.0)}

        assert compute_geometry_hash(centers1) == compute_geometry_hash(centers2)

    def test_geometry_hash_changes_with_content(self):
        """Test hash changes when coordinates change significantly."""
        centers1 = {'space_a': (0.0, 0.0, 0.0)}
        centers2 = {'space_a': (1.0, 0.0, 0.0)}

        assert compute_geometry_hash(centers1) != compute_geometry_hash(centers2)

    def test_geometry_hash_stable_with_minor_drift(self):
        """Test hash is stable with minor floating point drift."""
        centers1 = {'space_a': (10.000, 20.000, 5.000)}
        centers2 = {'space_a': (10.004, 20.003, 5.002)}  # Within 1cm

        # With default 1cm precision, should be same hash
        assert compute_geometry_hash(centers1) == compute_geometry_hash(centers2)


# =============================================================================
# Arrangement Hash Tests
# =============================================================================

class TestArrangementHash:
    """Tests for arrangement hashing."""

    def test_arrangement_hash_deterministic(self):
        """Test arrangement hash is deterministic."""
        adjacency = {
            'space_a': {'space_b', 'space_c'},
            'space_b': {'space_a'},
            'space_c': {'space_a'},
        }
        fire_zones = {'zone_1': {'space_a', 'space_b'}}
        wt_boundaries = {('space_b', 'space_c')}

        hash1 = compute_arrangement_hash(adjacency, fire_zones, wt_boundaries)
        hash2 = compute_arrangement_hash(adjacency, fire_zones, wt_boundaries)

        assert hash1 == hash2

    def test_arrangement_hash_changes_with_adjacency(self):
        """Test hash changes when adjacency changes."""
        adj1 = {'space_a': {'space_b'}}
        adj2 = {'space_a': {'space_b', 'space_c'}}

        assert compute_arrangement_hash(adj1) != compute_arrangement_hash(adj2)


# =============================================================================
# RoutingLineage Tests
# =============================================================================

class TestRoutingLineage:
    """Tests for RoutingLineage dataclass."""

    def test_lineage_creation(self):
        """Test lineage creation and hash computation."""
        lineage = RoutingLineage(source_design_id='test_design')

        space_centers = {
            'space_a': (0.0, 0.0, 0.0),
            'space_b': (10.0, 0.0, 0.0),
        }
        adjacency = {'space_a': {'space_b'}, 'space_b': {'space_a'}}

        lineage.compute_from_inputs(
            space_centers=space_centers,
            adjacency=adjacency,
        )

        assert lineage.geometry_hash is not None
        assert lineage.arrangement_hash is not None
        assert lineage.computed_at is not None
        assert lineage.status == LineageStatus.CURRENT

    def test_lineage_staleness_detection(self):
        """Test staleness detection."""
        lineage = RoutingLineage()

        space_centers = {'space_a': (0.0, 0.0, 0.0)}
        adjacency = {'space_a': set()}

        lineage.compute_from_inputs(space_centers, adjacency)

        # Same inputs - not stale
        current_geo_hash = compute_geometry_hash(space_centers)
        status = lineage.check_staleness(current_geometry_hash=current_geo_hash)
        assert status == LineageStatus.CURRENT

        # Changed geometry - stale
        new_centers = {'space_a': (100.0, 0.0, 0.0)}
        new_geo_hash = compute_geometry_hash(new_centers)
        status = lineage.check_staleness(current_geometry_hash=new_geo_hash)
        assert status == LineageStatus.STALE_GEOMETRY

    def test_lineage_serialization(self):
        """Test lineage serialization roundtrip."""
        lineage = RoutingLineage(
            source_design_id='test',
            source_version=5,
        )
        lineage.compute_from_inputs(
            space_centers={'a': (0, 0, 0)},
            adjacency={'a': set()},
        )

        data = lineage.to_dict()
        restored = RoutingLineage.from_dict(data)

        assert restored.geometry_hash == lineage.geometry_hash
        assert restored.arrangement_hash == lineage.arrangement_hash
        assert restored.source_design_id == 'test'
        assert restored.source_version == 5


# =============================================================================
# RoutingDiff Tests
# =============================================================================

class TestRoutingDiff:
    """Tests for RoutingDiff comparison."""

    @pytest.fixture
    def sample_layout(self):
        """Create a sample routing layout."""
        layout = RoutingLayout(design_id='test')

        topology = SystemTopology(system_type=SystemType.FUEL)
        node1 = SystemNode(
            node_id='node_1',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
            capacity_units=1000.0,
        )
        node2 = SystemNode(
            node_id='node_2',
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='engine',
            demand_units=100.0,
        )
        topology.add_node(node1)
        topology.add_node(node2)

        trunk = TrunkSegment(
            trunk_id='trunk_1',
            system_type=SystemType.FUEL,
            from_node_id='node_1',
            to_node_id='node_2',
        )
        trunk.set_path(['tank', 'corridor', 'engine'])
        trunk.length_m = 15.0
        topology.add_trunk(trunk)

        layout.add_topology(topology)
        return layout

    def test_diff_identical_layouts(self, sample_layout):
        """Test diff of identical layouts."""
        diff_analyzer = RoutingDiff()
        result = diff_analyzer.compare_layouts(sample_layout, sample_layout)

        # Should have entry for FUEL but no changes
        assert SystemType.FUEL in result
        assert not result[SystemType.FUEL].has_changes

    def test_diff_added_trunk(self, sample_layout):
        """Test diff when trunk is added."""
        diff_analyzer = RoutingDiff()

        # Create modified layout with additional trunk
        modified = RoutingLayout(design_id='test')
        topology = SystemTopology(system_type=SystemType.FUEL)

        # Copy original nodes
        for node in sample_layout.topologies[SystemType.FUEL].nodes.values():
            topology.add_node(node)

        # Add node_3 for the new trunk
        node3 = SystemNode(
            node_id='node_3',
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='pump_room',
            demand_units=50.0,
        )
        topology.add_node(node3)

        # Copy original trunk
        for trunk in sample_layout.topologies[SystemType.FUEL].trunks.values():
            topology.add_trunk(trunk)

        # Add new trunk
        new_trunk = TrunkSegment(
            trunk_id='trunk_2',
            system_type=SystemType.FUEL,
            from_node_id='node_1',
            to_node_id='node_3',
        )
        new_trunk.set_path(['tank', 'pump_room'])
        topology.add_trunk(new_trunk)

        modified.add_topology(topology)

        result = diff_analyzer.compare_layouts(sample_layout, modified)

        fuel_diff = result[SystemType.FUEL]
        assert fuel_diff.has_changes
        assert 'trunk_2' in fuel_diff.trunks_added

    def test_diff_summary(self, sample_layout):
        """Test diff summary generation."""
        diff_analyzer = RoutingDiff()

        # Create modified layout
        modified = RoutingLayout(design_id='test')
        topology = SystemTopology(system_type=SystemType.FUEL)
        topology.add_node(sample_layout.topologies[SystemType.FUEL].nodes['node_1'])
        # Remove node_2 - so node removed
        modified.add_topology(topology)

        result = diff_analyzer.compare_layouts(sample_layout, modified)
        summary = diff_analyzer.summarize(result)

        assert summary['has_changes'] is True
        assert summary['total_changes'] > 0


# =============================================================================
# Polyline Generator Tests
# =============================================================================

class TestPolylineGenerator:
    """Tests for polyline visualization generation."""

    @pytest.fixture
    def sample_topology(self):
        """Create sample topology with trunk."""
        topology = SystemTopology(system_type=SystemType.FUEL)

        node1 = SystemNode(
            node_id='node_1',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
        )
        node2 = SystemNode(
            node_id='node_2',
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='engine',
        )
        topology.add_node(node1)
        topology.add_node(node2)

        trunk = TrunkSegment(
            trunk_id='trunk_1',
            system_type=SystemType.FUEL,
            from_node_id='node_1',
            to_node_id='node_2',
        )
        trunk.set_path(['tank', 'corridor', 'engine'])
        topology.add_trunk(trunk)

        return topology

    @pytest.fixture
    def space_centers(self):
        """Sample space centers."""
        return {
            'tank': (0.0, 0.0, 0.0),
            'corridor': (5.0, 0.0, 0.0),
            'engine': (10.0, 0.0, 0.0),
        }

    def test_polyline_generation(self, sample_topology, space_centers):
        """Test basic polyline generation."""
        generator = PolylineGenerator()
        polylines = generator.generate_for_system(
            topology=sample_topology,
            space_centers=space_centers,
        )

        assert len(polylines) == 1
        polyline = polylines[0]

        assert polyline.trunk_id == 'trunk_1'
        assert polyline.system_type == SystemType.FUEL
        assert len(polyline.points) == 3
        assert polyline.length_m > 0

    def test_polyline_color_mapping(self, sample_topology, space_centers):
        """Test system color assignment."""
        generator = PolylineGenerator()
        polylines = generator.generate_for_system(
            topology=sample_topology,
            space_centers=space_centers,
        )

        assert polylines[0].color == SYSTEM_COLORS[SystemType.FUEL]

    def test_crossing_marker_detection(self, sample_topology, space_centers):
        """Test crossing marker detection."""
        generator = PolylineGenerator(show_crossing_markers=True)

        zone_boundaries = {
            'zone_1': {'tank', 'corridor'},
            'zone_2': {'engine'},
        }

        polylines = generator.generate_for_system(
            topology=sample_topology,
            space_centers=space_centers,
            zone_boundaries=zone_boundaries,
        )

        # Should detect fire zone crossing between corridor and engine
        polyline = polylines[0]
        fire_crossings = [
            c for c in polyline.crossings
            if c.crossing_type == CrossingType.FIRE_ZONE
        ]

        assert len(fire_crossings) >= 1

    def test_visualization_data_generation(self, space_centers):
        """Test full visualization data generation."""
        layout = RoutingLayout(design_id='test')

        topology = SystemTopology(system_type=SystemType.FUEL)
        node1 = SystemNode(
            node_id='node_1',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
        )
        node2 = SystemNode(
            node_id='node_2',
            node_type=NodeType.CONSUMER,
            system_type=SystemType.FUEL,
            space_id='engine',
        )
        topology.add_node(node1)
        topology.add_node(node2)

        trunk = TrunkSegment(
            trunk_id='trunk_1',
            system_type=SystemType.FUEL,
            from_node_id='node_1',
            to_node_id='node_2',
        )
        trunk.set_path(['tank', 'engine'])
        topology.add_trunk(trunk)

        layout.add_topology(topology)

        generator = PolylineGenerator()
        vis_data = generator.generate(
            layout=layout,
            space_centers=space_centers,
        )

        assert vis_data.design_id == 'test'
        assert len(vis_data.polylines) == 1
        assert vis_data.systems == ['fuel']
        assert vis_data.total_length_m > 0

    def test_polyline_serialization(self, sample_topology, space_centers):
        """Test polyline serialization to dict."""
        generator = PolylineGenerator()
        polylines = generator.generate_for_system(
            topology=sample_topology,
            space_centers=space_centers,
        )

        data = polylines[0].to_dict()

        assert 'trunk_id' in data
        assert 'points' in data
        assert 'color' in data
        assert data['system_type'] == 'fuel'


# =============================================================================
# Integration Tests
# =============================================================================

class TestRoutingLayoutWithLineage:
    """Test RoutingLayout with lineage integration."""

    def test_layout_lineage_serialization(self):
        """Test layout serialization includes lineage."""
        layout = RoutingLayout(design_id='test')

        lineage = RoutingLineage(source_design_id='test')
        lineage.compute_from_inputs(
            space_centers={'a': (0, 0, 0)},
            adjacency={'a': set()},
        )
        layout.lineage = lineage

        data = layout.to_dict()
        assert 'lineage' in data
        assert data['lineage'] is not None

        restored = RoutingLayout.from_dict(data)
        assert restored.lineage is not None
        assert restored.lineage.geometry_hash == lineage.geometry_hash

    def test_layout_without_lineage(self):
        """Test layout serialization without lineage."""
        layout = RoutingLayout(design_id='test')

        data = layout.to_dict()
        assert data['lineage'] is None

        restored = RoutingLayout.from_dict(data)
        assert restored.lineage is None
