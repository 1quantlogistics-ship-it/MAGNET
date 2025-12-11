"""
magnet/routing/tests/test_determinism.py - Determinism Tests

Tests to verify routing produces deterministic, reproducible results.
"""

import pytest
from typing import List

from magnet.routing.schema.system_type import SystemType
from magnet.routing.schema.system_node import SystemNode, NodeType, generate_node_id
from magnet.routing.schema.trunk_segment import TrunkSegment, TrunkSize, generate_trunk_id
from magnet.routing.schema.system_topology import SystemTopology
from magnet.routing.schema.routing_layout import RoutingLayout


# =============================================================================
# Deterministic ID Generation Tests
# =============================================================================

class TestDeterministicIdGeneration:
    """Tests for deterministic ID generation."""

    def test_node_id_deterministic_with_params(self):
        """Test node ID is deterministic when parameters provided."""
        id1 = generate_node_id(
            system_type='fuel',
            node_type='source',
            space_id='tank_room',
            name='Main Tank',
        )
        id2 = generate_node_id(
            system_type='fuel',
            node_type='source',
            space_id='tank_room',
            name='Main Tank',
        )

        assert id1 == id2
        assert id1.startswith('node_')

    def test_node_id_different_for_different_params(self):
        """Test different parameters produce different IDs."""
        id1 = generate_node_id(
            system_type='fuel',
            node_type='source',
            space_id='tank_room_1',
        )
        id2 = generate_node_id(
            system_type='fuel',
            node_type='source',
            space_id='tank_room_2',
        )

        assert id1 != id2

    def test_trunk_id_deterministic_with_params(self):
        """Test trunk ID is deterministic when parameters provided."""
        id1 = generate_trunk_id(
            system_type='fuel',
            from_node_id='node_a',
            to_node_id='node_b',
            path_spaces=['space1', 'space2'],
        )
        id2 = generate_trunk_id(
            system_type='fuel',
            from_node_id='node_a',
            to_node_id='node_b',
            path_spaces=['space1', 'space2'],
        )

        assert id1 == id2
        assert id1.startswith('trunk_')

    def test_trunk_id_bidirectional_consistency(self):
        """Test trunk ID is same regardless of endpoint order."""
        id1 = generate_trunk_id(
            system_type='fuel',
            from_node_id='node_a',
            to_node_id='node_b',
            path_spaces=['space1', 'space2'],
        )
        id2 = generate_trunk_id(
            system_type='fuel',
            from_node_id='node_b',  # Swapped
            to_node_id='node_a',    # Swapped
            path_spaces=['space1', 'space2'],
        )

        assert id1 == id2

    def test_trunk_id_different_for_different_paths(self):
        """Test different paths produce different IDs."""
        id1 = generate_trunk_id(
            system_type='fuel',
            from_node_id='node_a',
            to_node_id='node_b',
            path_spaces=['space1', 'space2'],
        )
        id2 = generate_trunk_id(
            system_type='fuel',
            from_node_id='node_a',
            to_node_id='node_b',
            path_spaces=['space1', 'space3'],  # Different path
        )

        assert id1 != id2

    def test_fallback_sequential_id(self):
        """Test fallback sequential IDs when params not provided."""
        # Without parameters, should generate sequential IDs
        id1 = generate_node_id()
        id2 = generate_node_id()

        assert id1 != id2
        assert id1.startswith('node_')
        assert id2.startswith('node_')


# =============================================================================
# Content Hashing Tests
# =============================================================================

class TestContentHashing:
    """Tests for routing layout content hashing."""

    def test_empty_layout_hash(self):
        """Test hash of empty layout."""
        layout = RoutingLayout(design_id='test')
        hash1 = layout.compute_content_hash()
        hash2 = layout.compute_content_hash()

        assert hash1 == hash2
        assert len(hash1) == 32

    def test_hash_changes_with_content(self):
        """Test hash changes when content added."""
        layout = RoutingLayout(design_id='test')
        hash_empty = layout.compute_content_hash()

        # Add a topology
        topology = SystemTopology(system_type=SystemType.FUEL)
        node = SystemNode(
            node_id='test_node',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
            capacity_units=100.0,
        )
        topology.add_node(node)
        layout.add_topology(topology)

        hash_with_content = layout.compute_content_hash()

        assert hash_empty != hash_with_content

    def test_hash_stable_across_calls(self):
        """Test hash is stable when content unchanged."""
        topology = SystemTopology(system_type=SystemType.FUEL)
        node = SystemNode(
            node_id='test_node',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
            capacity_units=100.0,
        )
        topology.add_node(node)

        layout = RoutingLayout(design_id='test')
        layout.add_topology(topology)

        # Multiple calls should return same hash
        hashes = [layout.compute_content_hash() for _ in range(10)]
        assert len(set(hashes)) == 1

    def test_update_hash_increments_version(self):
        """Test update_hash increments version on change."""
        layout = RoutingLayout(design_id='test')
        initial_version = layout.version

        # First update should increment version
        changed = layout.update_hash()
        assert changed is True
        assert layout.version == initial_version + 1
        assert layout.content_hash is not None

        # Second update with same content should not change
        changed = layout.update_hash()
        assert changed is False
        assert layout.version == initial_version + 1

    def test_verify_hash_integrity(self):
        """Test hash verification."""
        layout = RoutingLayout(design_id='test')
        layout.update_hash()

        # Should verify OK
        assert layout.verify_hash() is True

        # Corrupt hash
        layout.content_hash = 'corrupted'
        assert layout.verify_hash() is False

    def test_hash_serialization_roundtrip(self):
        """Test hash survives serialization."""
        topology = SystemTopology(system_type=SystemType.FUEL)
        node = SystemNode(
            node_id='test_node',
            node_type=NodeType.SOURCE,
            system_type=SystemType.FUEL,
            space_id='tank',
            capacity_units=100.0,
        )
        topology.add_node(node)

        layout = RoutingLayout(design_id='test')
        layout.add_topology(topology)
        layout.update_hash()

        original_hash = layout.content_hash
        original_version = layout.version

        # Roundtrip
        data = layout.to_dict()
        restored = RoutingLayout.from_dict(data)

        assert restored.content_hash == original_hash
        assert restored.version == original_version
        assert restored.verify_hash() is True


# =============================================================================
# Zone Cost Multiplier Tests
# =============================================================================

class TestZoneCostMultipliers:
    """Tests for zone cost multiplier functionality."""

    def test_zone_manager_cost_multipliers_exist(self):
        """Test zone manager has cost multiplier constants."""
        from magnet.routing.router.zone_manager import ZoneManager

        manager = ZoneManager()

        assert 'fire' in ZoneManager.ZONE_CROSSING_COSTS
        assert 'watertight' in ZoneManager.ZONE_CROSSING_COSTS
        assert ZoneManager.ZONE_CROSSING_COSTS['fire'] > 1.0
        assert ZoneManager.ZONE_CROSSING_COSTS['watertight'] > 1.0

    def test_get_edge_cost_no_boundary(self):
        """Test cost multiplier is 1.0 with no boundary."""
        from magnet.routing.router.zone_manager import ZoneManager, ZoneType

        manager = ZoneManager()
        manager.add_zone('zone1', ZoneType.FIRE, {'space_a', 'space_b'})

        # Same zone - no boundary
        cost = manager.get_edge_cost_multiplier('space_a', 'space_b', SystemType.FUEL)
        assert cost == 1.0

    def test_get_edge_cost_fire_boundary(self):
        """Test cost multiplier for fire boundary."""
        from magnet.routing.router.zone_manager import ZoneManager, ZoneType

        manager = ZoneManager()
        manager.add_zone('zone1', ZoneType.FIRE, {'space_a'})
        manager.add_zone('zone2', ZoneType.FIRE, {'space_b'})

        # Different zones - fire boundary
        cost = manager.get_edge_cost_multiplier('space_a', 'space_b', SystemType.ELECTRICAL_LV)
        assert cost == ZoneManager.ZONE_CROSSING_COSTS['fire']

    def test_get_edge_cost_prohibited(self):
        """Test cost is infinite for prohibited crossings."""
        from magnet.routing.router.zone_manager import ZoneManager, ZoneType

        manager = ZoneManager()
        manager.add_zone('zone1', ZoneType.FIRE, {'space_a'})
        manager.add_zone('zone2', ZoneType.FIRE, {'space_b'})

        # FIREFIGHTING cannot cross fire zones
        cost = manager.get_edge_cost_multiplier('space_a', 'space_b', SystemType.FIREFIGHTING)
        # Should be allowed with high cost (fire fighting CAN cross fire zones)
        assert cost < float('inf')

    def test_get_path_cost_multiplier(self):
        """Test path cost multiplier accumulates."""
        from magnet.routing.router.zone_manager import ZoneManager, ZoneType

        manager = ZoneManager()
        manager.add_zone('zone1', ZoneType.FIRE, {'space_a', 'space_b'})
        manager.add_zone('zone2', ZoneType.FIRE, {'space_c'})

        # Path within same zone, then crossing
        path_cost = manager.get_path_cost_multiplier(
            ['space_a', 'space_b', 'space_c'],
            SystemType.ELECTRICAL_LV,
        )

        # Should be 1.0 * fire_crossing_cost
        expected = ZoneManager.ZONE_CROSSING_COSTS['fire']
        assert path_cost == expected
