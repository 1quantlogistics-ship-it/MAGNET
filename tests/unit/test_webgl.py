"""
tests/unit/test_webgl.py - WebGL module tests v1.1
BRAVO OWNS THIS FILE.

Tests for WebGL 3D visualization: websocket streaming and annotations.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch


# =============================================================================
# WEBSOCKET STREAM TESTS
# =============================================================================

class TestStreamMessageType:
    """Test stream message type enum."""

    def test_message_types(self):
        from magnet.webgl.websocket_stream import StreamMessageType
        assert StreamMessageType.GEOMETRY_UPDATE.value == "geometry_update"
        assert StreamMessageType.GEOMETRY_FAILED.value == "geometry_failed"
        assert StreamMessageType.GEOMETRY_INVALIDATED.value == "geometry_invalidated"


class TestGeometryUpdateMessage:
    """Test geometry update message."""

    def test_message_creation(self):
        from magnet.webgl.websocket_stream import GeometryUpdateMessage
        msg = GeometryUpdateMessage(design_id="TEST-001")
        assert msg.design_id == "TEST-001"
        assert msg.update_id != ""
        assert msg.message_type == "geometry_update"

    def test_message_with_hull(self):
        from magnet.webgl.websocket_stream import GeometryUpdateMessage
        hull_data = {"vertices": [0, 0, 0, 1, 0, 0], "indices": [0, 1, 2]}
        msg = GeometryUpdateMessage(
            design_id="TEST-001",
            hull=hull_data,
            is_full_update=True,
        )
        assert msg.hull == hull_data
        assert msg.is_full_update is True

    def test_message_to_dict(self):
        from magnet.webgl.websocket_stream import GeometryUpdateMessage
        msg = GeometryUpdateMessage(design_id="TEST-001")
        d = msg.to_dict()
        assert d["message_type"] == "geometry_update"
        assert d["design_id"] == "TEST-001"
        assert "update_id" in d
        assert "timestamp" in d

    def test_message_to_json(self):
        from magnet.webgl.websocket_stream import GeometryUpdateMessage
        msg = GeometryUpdateMessage(design_id="TEST-001")
        json_str = msg.to_json()
        assert '"message_type": "geometry_update"' in json_str
        assert '"design_id": "TEST-001"' in json_str

    def test_message_from_dict(self):
        from magnet.webgl.websocket_stream import GeometryUpdateMessage
        data = {
            "design_id": "TEST-002",
            "update_id": "abc123",
            "prev_update_id": "xyz789",
            "is_full_update": True,
        }
        msg = GeometryUpdateMessage.from_dict(data)
        assert msg.design_id == "TEST-002"
        assert msg.update_id == "abc123"
        assert msg.prev_update_id == "xyz789"
        assert msg.is_full_update is True


class TestGeometryFailedMessage:
    """Test geometry failed message."""

    def test_message_creation(self):
        from magnet.webgl.websocket_stream import GeometryFailedMessage
        msg = GeometryFailedMessage(
            design_id="TEST-001",
            error_code="GEOM_001",
            error_message="Geometry generation failed",
            recovery_hint="Check hull parameters",
        )
        assert msg.design_id == "TEST-001"
        assert msg.error_code == "GEOM_001"
        assert msg.message_type == "geometry_failed"

    def test_message_to_dict(self):
        from magnet.webgl.websocket_stream import GeometryFailedMessage
        msg = GeometryFailedMessage(
            design_id="TEST-001",
            error_code="ERR_001",
            error_message="Test error",
        )
        d = msg.to_dict()
        assert d["error_code"] == "ERR_001"
        assert d["error_message"] == "Test error"


class TestStreamClient:
    """Test stream client."""

    def test_client_creation(self):
        from magnet.webgl.websocket_stream import StreamClient
        client = StreamClient()
        assert client.client_id != ""
        assert len(client.design_subscriptions) == 0

    def test_client_auto_id(self):
        from magnet.webgl.websocket_stream import StreamClient
        c1 = StreamClient()
        c2 = StreamClient()
        assert c1.client_id != c2.client_id

    def test_client_is_stale(self):
        from magnet.webgl.websocket_stream import StreamClient
        client = StreamClient()
        assert not client.is_stale

    def test_client_update_tracking(self):
        from magnet.webgl.websocket_stream import StreamClient
        client = StreamClient()
        client.set_last_update_id("design-1", "update-123")
        assert client.get_last_update_id("design-1") == "update-123"
        assert client.get_last_update_id("design-2") == ""


class TestGeometryStreamManager:
    """Test geometry stream manager."""

    def test_manager_creation(self):
        from magnet.webgl.websocket_stream import GeometryStreamManager
        manager = GeometryStreamManager()
        assert manager.client_count == 0

    def test_manager_get_design_clients_empty(self):
        from magnet.webgl.websocket_stream import GeometryStreamManager
        manager = GeometryStreamManager()
        clients = manager.get_design_clients("TEST-001")
        assert len(clients) == 0

    @pytest.mark.asyncio
    async def test_manager_subscribe(self):
        from magnet.webgl.websocket_stream import GeometryStreamManager, StreamClient
        manager = GeometryStreamManager()

        # Manually add client
        client = StreamClient()
        manager._clients[client.client_id] = client

        result = await manager.subscribe(client.client_id, "TEST-001")
        assert result is True
        assert "TEST-001" in client.design_subscriptions

    @pytest.mark.asyncio
    async def test_manager_unsubscribe(self):
        from magnet.webgl.websocket_stream import GeometryStreamManager, StreamClient
        manager = GeometryStreamManager()

        client = StreamClient()
        client.design_subscriptions.add("TEST-001")
        manager._clients[client.client_id] = client
        manager._by_design["TEST-001"] = {client.client_id}

        result = await manager.unsubscribe(client.client_id, "TEST-001")
        assert result is True
        assert "TEST-001" not in client.design_subscriptions

    def test_queue_update(self):
        from magnet.webgl.websocket_stream import (
            GeometryStreamManager,
            GeometryUpdateMessage,
        )
        manager = GeometryStreamManager()
        msg = GeometryUpdateMessage(design_id="TEST-001")
        manager.queue_update(msg)
        assert manager._message_queue.qsize() == 1

    def test_update_chain_tracking(self):
        from magnet.webgl.websocket_stream import (
            GeometryStreamManager,
            GeometryUpdateMessage,
        )
        manager = GeometryStreamManager()

        msg1 = GeometryUpdateMessage(design_id="TEST-001")
        manager.queue_update(msg1)

        msg2 = GeometryUpdateMessage(design_id="TEST-001")
        manager.queue_update(msg2)

        # Second message should have prev_update_id set to first
        assert msg2.prev_update_id == msg1.update_id


class TestStreamManagerFunctions:
    """Test stream manager convenience functions."""

    def test_get_stream_manager(self):
        from magnet.webgl.websocket_stream import get_stream_manager
        m1 = get_stream_manager()
        m2 = get_stream_manager()
        assert m1 is m2  # Singleton

    def test_emit_geometry_update(self):
        from magnet.webgl.websocket_stream import (
            emit_geometry_update,
            get_stream_manager,
        )
        manager = get_stream_manager()
        initial_size = manager._message_queue.qsize()

        emit_geometry_update("TEST-001", hull={"vertices": []})

        assert manager._message_queue.qsize() == initial_size + 1

    def test_emit_geometry_failure(self):
        from magnet.webgl.websocket_stream import (
            emit_geometry_failure,
            get_stream_manager,
        )
        manager = get_stream_manager()
        initial_size = manager._message_queue.qsize()

        emit_geometry_failure("TEST-001", "ERR_001", "Test error")

        assert manager._message_queue.qsize() == initial_size + 1

    def test_emit_geometry_invalidated(self):
        from magnet.webgl.websocket_stream import (
            emit_geometry_invalidated,
            get_stream_manager,
        )
        manager = get_stream_manager()
        initial_size = manager._message_queue.qsize()

        emit_geometry_invalidated("TEST-001", "Parameter changed", ["hull"])

        assert manager._message_queue.qsize() == initial_size + 1


# =============================================================================
# ANNOTATION TESTS
# =============================================================================

class TestAnnotationCategory:
    """Test annotation category enum."""

    def test_category_values(self):
        from magnet.webgl.annotations import AnnotationCategory
        assert AnnotationCategory.GENERAL.value == "general"
        assert AnnotationCategory.MEASUREMENT.value == "measurement"
        assert AnnotationCategory.ISSUE.value == "issue"


class TestMeasurementType:
    """Test measurement type enum."""

    def test_measurement_types(self):
        from magnet.webgl.annotations import MeasurementType
        assert MeasurementType.DISTANCE.value == "distance"
        assert MeasurementType.ANGLE.value == "angle"
        assert MeasurementType.AREA.value == "area"


class TestMeasurement3D:
    """Test 3D measurement dataclass."""

    def test_measurement_creation(self):
        from magnet.webgl.annotations import Measurement3D, MeasurementType
        m = Measurement3D(
            type=MeasurementType.DISTANCE,
            points=[(0, 0, 0), (1, 0, 0)],
            value=1.0,
            unit="m",
        )
        assert m.type == MeasurementType.DISTANCE
        assert m.value == 1.0

    def test_measurement_formatted_value(self):
        from magnet.webgl.annotations import Measurement3D, MeasurementType
        m = Measurement3D(
            type=MeasurementType.DISTANCE,
            points=[(0, 0, 0), (1, 0, 0)],
            value=1.234,
            unit="m",
            precision=2,
        )
        assert m.formatted_value == "1.23 m"

    def test_measurement_to_dict(self):
        from magnet.webgl.annotations import Measurement3D, MeasurementType
        m = Measurement3D(
            type=MeasurementType.DISTANCE,
            points=[(0, 0, 0), (1, 0, 0)],
            value=1.0,
        )
        d = m.to_dict()
        assert d["type"] == "distance"
        assert d["value"] == 1.0

    def test_measurement_from_dict(self):
        from magnet.webgl.annotations import Measurement3D
        data = {
            "type": "angle",
            "points": [[0, 0, 0], [1, 0, 0], [1, 1, 0]],
            "value": 90.0,
            "unit": "deg",
        }
        m = Measurement3D.from_dict(data)
        assert m.value == 90.0
        assert m.unit == "deg"


class TestAnnotation3D:
    """Test 3D annotation dataclass."""

    def test_annotation_creation(self):
        from magnet.webgl.annotations import Annotation3D
        ann = Annotation3D(
            design_id="TEST-001",
            position=(10.0, 5.0, 2.0),
            label="Test Point",
        )
        assert ann.annotation_id != ""
        assert ann.design_id == "TEST-001"
        assert ann.position == (10.0, 5.0, 2.0)

    def test_annotation_auto_id(self):
        from magnet.webgl.annotations import Annotation3D
        a1 = Annotation3D(design_id="TEST-001")
        a2 = Annotation3D(design_id="TEST-001")
        assert a1.annotation_id != a2.annotation_id

    def test_annotation_to_dict(self):
        from magnet.webgl.annotations import Annotation3D, AnnotationCategory
        ann = Annotation3D(
            design_id="TEST-001",
            position=(1.0, 2.0, 3.0),
            label="Test",
            category=AnnotationCategory.NOTE,
        )
        d = ann.to_dict()
        assert d["design_id"] == "TEST-001"
        assert d["position"] == [1.0, 2.0, 3.0]
        assert d["category"] == "note"

    def test_annotation_from_dict(self):
        from magnet.webgl.annotations import Annotation3D
        data = {
            "annotation_id": "ann-123",
            "design_id": "TEST-001",
            "position": [5.0, 6.0, 7.0],
            "label": "From Dict",
            "category": "issue",
        }
        ann = Annotation3D.from_dict(data)
        assert ann.annotation_id == "ann-123"
        assert ann.position == (5.0, 6.0, 7.0)

    def test_annotation_with_measurement(self):
        from magnet.webgl.annotations import (
            Annotation3D,
            Measurement3D,
            MeasurementType,
            AnnotationCategory,
        )
        measurement = Measurement3D(
            type=MeasurementType.DISTANCE,
            points=[(0, 0, 0), (10, 0, 0)],
            value=10.0,
        )
        ann = Annotation3D(
            design_id="TEST-001",
            position=(5.0, 0.0, 0.0),
            label="Length",
            category=AnnotationCategory.MEASUREMENT,
            measurement=measurement,
        )
        assert ann.measurement is not None
        assert ann.measurement.value == 10.0


class TestAnnotationStore:
    """Test annotation store."""

    def test_store_creation(self):
        from magnet.webgl.annotations import AnnotationStore
        store = AnnotationStore()
        assert store is not None

    def test_store_create(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()
        ann = Annotation3D(
            design_id="TEST-001",
            position=(1.0, 2.0, 3.0),
            label="Test",
        )
        created = store.create(ann)
        assert created.annotation_id != ""

    def test_store_get(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()
        ann = Annotation3D(design_id="TEST-001", label="Test")
        created = store.create(ann)

        retrieved = store.get("TEST-001", created.annotation_id)
        assert retrieved is not None
        assert retrieved.label == "Test"

    def test_store_list(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()

        store.create(Annotation3D(design_id="TEST-001", label="Ann 1"))
        store.create(Annotation3D(design_id="TEST-001", label="Ann 2"))
        store.create(Annotation3D(design_id="TEST-002", label="Ann 3"))

        list1 = store.list("TEST-001")
        list2 = store.list("TEST-002")

        assert len(list1) == 2
        assert len(list2) == 1

    def test_store_update(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()
        ann = store.create(Annotation3D(design_id="TEST-001", label="Original"))

        ann.label = "Updated"
        updated = store.update(ann)

        assert updated is not None
        assert updated.label == "Updated"
        assert updated.updated_at is not None

    def test_store_delete(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()
        ann = store.create(Annotation3D(design_id="TEST-001", label="ToDelete"))

        result = store.delete("TEST-001", ann.annotation_id)
        assert result is True

        retrieved = store.get("TEST-001", ann.annotation_id)
        assert retrieved is None

    def test_store_delete_all(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()

        store.create(Annotation3D(design_id="TEST-001", label="Ann 1"))
        store.create(Annotation3D(design_id="TEST-001", label="Ann 2"))

        count = store.delete_all("TEST-001")
        assert count == 2
        assert len(store.list("TEST-001")) == 0

    def test_store_link_to_decision(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()
        ann = store.create(Annotation3D(design_id="TEST-001", label="Test"))

        result = store.link_to_decision("TEST-001", ann.annotation_id, "decision-123")
        assert result is not None
        assert result.linked_decision_id == "decision-123"

    def test_store_phase_filter(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()

        store.create(Annotation3D(
            design_id="TEST-001",
            label="Mission",
            linked_phase="mission",
        ))
        store.create(Annotation3D(
            design_id="TEST-001",
            label="Hull",
            linked_phase="hull_form",
        ))

        mission_anns = store.list("TEST-001", phase_filter="mission")
        hull_anns = store.list("TEST-001", phase_filter="hull_form")

        assert len(mission_anns) == 1
        assert len(hull_anns) == 1

    def test_store_export_import_json(self):
        from magnet.webgl.annotations import AnnotationStore, Annotation3D
        store = AnnotationStore()

        store.create(Annotation3D(design_id="TEST-001", label="Ann 1"))
        store.create(Annotation3D(design_id="TEST-001", label="Ann 2"))

        # Export
        json_data = store.export_to_json("TEST-001")
        assert "Ann 1" in json_data
        assert "Ann 2" in json_data

        # Import to new design
        new_store = AnnotationStore()
        count = new_store.import_from_json("TEST-002", json_data)
        assert count == 2
        assert len(new_store.list("TEST-002")) == 2


class TestAnnotationHelperFunctions:
    """Test annotation helper functions."""

    def test_create_distance_measurement(self):
        from magnet.webgl.annotations import create_distance_measurement
        ann = create_distance_measurement(
            design_id="TEST-001",
            point1=(0, 0, 0),
            point2=(10, 0, 0),
            label="Length",
        )
        assert ann.measurement is not None
        assert ann.measurement.value == 10.0
        assert ann.position == (5.0, 0.0, 0.0)  # Midpoint

    def test_create_angle_measurement(self):
        from magnet.webgl.annotations import create_angle_measurement
        ann = create_angle_measurement(
            design_id="TEST-001",
            vertex=(0, 0, 0),
            point1=(1, 0, 0),
            point2=(0, 1, 0),
        )
        assert ann.measurement is not None
        assert abs(ann.measurement.value - 90.0) < 0.1  # 90 degrees


class TestAnnotationStoreGlobal:
    """Test global annotation store."""

    def test_get_annotation_store(self):
        from magnet.webgl.annotations import get_annotation_store
        s1 = get_annotation_store()
        s2 = get_annotation_store()
        assert s1 is s2  # Singleton


# =============================================================================
# MODULE IMPORT TESTS
# =============================================================================

class TestWebGLModuleImports:
    """Test that all module exports work."""

    def test_websocket_imports(self):
        from magnet.webgl import (
            GeometryStreamManager,
            get_stream_manager,
            GeometryUpdateMessage,
            GeometryFailedMessage,
        )
        assert GeometryStreamManager is not None
        assert get_stream_manager is not None
        assert GeometryUpdateMessage is not None
        assert GeometryFailedMessage is not None

    def test_annotation_imports(self):
        from magnet.webgl import (
            Annotation3D,
            Measurement3D,
            AnnotationCategory,
            AnnotationStore,
            get_annotation_store,
        )
        assert Annotation3D is not None
        assert Measurement3D is not None
        assert AnnotationCategory is not None
        assert AnnotationStore is not None
        assert get_annotation_store is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
