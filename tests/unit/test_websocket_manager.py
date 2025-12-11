"""
tests/unit/test_websocket_manager.py - WebSocket Manager Tests
BRAVO OWNS THIS FILE.

Comprehensive tests for WebSocket connection management.
Required for RunPod deployment validation.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_websocket():
    """Create mock WebSocket."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def connection_manager():
    """Create fresh ConnectionManager."""
    from magnet.deployment.websocket import ConnectionManager
    return ConnectionManager(heartbeat_interval=30.0)


# =============================================================================
# MESSAGE TYPE TESTS
# =============================================================================

class TestMessageType:
    """Test MessageType enum."""

    def test_message_types_defined(self):
        """Test all message types are defined."""
        from magnet.deployment.websocket import MessageType

        assert MessageType.CONNECT.value == "connect"
        assert MessageType.DISCONNECT.value == "disconnect"
        assert MessageType.PING.value == "ping"
        assert MessageType.PONG.value == "pong"
        assert MessageType.DESIGN_CREATED.value == "design_created"
        assert MessageType.DESIGN_UPDATED.value == "design_updated"
        assert MessageType.DESIGN_DELETED.value == "design_deleted"
        assert MessageType.PHASE_STARTED.value == "phase_started"
        assert MessageType.PHASE_COMPLETED.value == "phase_completed"
        assert MessageType.PHASE_FAILED.value == "phase_failed"
        assert MessageType.PHASE_APPROVED.value == "phase_approved"
        assert MessageType.JOB_SUBMITTED.value == "job_submitted"
        assert MessageType.JOB_STARTED.value == "job_started"
        assert MessageType.JOB_COMPLETED.value == "job_completed"
        assert MessageType.JOB_FAILED.value == "job_failed"
        assert MessageType.SNAPSHOT_CREATED.value == "snapshot_created"
        assert MessageType.ERROR.value == "error"


# =============================================================================
# WSMESSAGE TESTS
# =============================================================================

class TestWSMessage:
    """Test WSMessage dataclass."""

    def test_message_creation(self):
        """Test basic message creation."""
        from magnet.deployment.websocket import WSMessage

        msg = WSMessage(type="test", design_id="TEST-001")
        assert msg.type == "test"
        assert msg.design_id == "TEST-001"
        assert msg.message_id != ""  # Auto-generated
        assert isinstance(msg.timestamp, datetime)

    def test_message_auto_id(self):
        """Test message_id is auto-generated if not provided."""
        from magnet.deployment.websocket import WSMessage

        msg1 = WSMessage(type="test")
        msg2 = WSMessage(type="test")
        assert msg1.message_id != msg2.message_id

    def test_message_to_dict(self):
        """Test message serialization to dict."""
        from magnet.deployment.websocket import WSMessage

        msg = WSMessage(
            type="design_created",
            design_id="TEST-001",
            payload={"name": "Test Design"}
        )

        d = msg.to_dict()
        assert d["type"] == "design_created"
        assert d["design_id"] == "TEST-001"
        assert d["payload"] == {"name": "Test Design"}
        assert "message_id" in d
        assert "timestamp" in d

    def test_message_to_json(self):
        """Test message serialization to JSON."""
        from magnet.deployment.websocket import WSMessage
        import json

        msg = WSMessage(type="test", payload={"key": "value"})
        json_str = msg.to_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["type"] == "test"
        assert parsed["payload"] == {"key": "value"}

    def test_message_from_dict(self):
        """Test message deserialization from dict."""
        from magnet.deployment.websocket import WSMessage

        data = {
            "type": "phase_completed",
            "message_id": "abc123",
            "design_id": "TEST-001",
            "payload": {"phase": "mission"},
        }

        msg = WSMessage.from_dict(data)
        assert msg.type == "phase_completed"
        assert msg.message_id == "abc123"
        assert msg.design_id == "TEST-001"
        assert msg.payload == {"phase": "mission"}


# =============================================================================
# WSCLIENT TESTS
# =============================================================================

class TestWSClient:
    """Test WSClient dataclass."""

    def test_client_creation(self):
        """Test basic client creation."""
        from magnet.deployment.websocket import WSClient

        client = WSClient(websocket=Mock())
        assert client.client_id != ""  # Auto-generated
        assert client.websocket is not None
        assert isinstance(client.connected_at, datetime)
        assert client.subscriptions == set()

    def test_client_auto_id(self):
        """Test client_id is auto-generated."""
        from magnet.deployment.websocket import WSClient

        client1 = WSClient()
        client2 = WSClient()
        assert client1.client_id != client2.client_id

    def test_client_is_alive_no_ping(self):
        """Test is_alive with no ping."""
        from magnet.deployment.websocket import WSClient

        client = WSClient()
        assert client.is_alive is True  # No ping yet, assume alive

    def test_client_is_alive_recent_ping(self):
        """Test is_alive with recent ping."""
        from magnet.deployment.websocket import WSClient

        client = WSClient()
        client.last_ping = datetime.now(timezone.utc)
        assert client.is_alive is True

    def test_client_is_alive_stale_ping(self):
        """Test is_alive with stale ping."""
        from magnet.deployment.websocket import WSClient

        client = WSClient()
        client.last_ping = datetime.now(timezone.utc) - timedelta(minutes=5)
        assert client.is_alive is False


# =============================================================================
# CONNECTION MANAGER TESTS
# =============================================================================

class TestConnectionManager:
    """Test ConnectionManager class."""

    def test_manager_creation(self):
        """Test manager creation."""
        from magnet.deployment.websocket import ConnectionManager

        manager = ConnectionManager()
        assert manager.client_count == 0

    @pytest.mark.asyncio
    async def test_connect(self, connection_manager, mock_websocket):
        """Test client connection."""
        client = await connection_manager.connect(mock_websocket, design_id="TEST-001")

        assert connection_manager.client_count == 1
        assert client.design_id == "TEST-001"
        assert "TEST-001" in client.subscriptions
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once()  # Connection confirmation

    @pytest.mark.asyncio
    async def test_disconnect(self, connection_manager, mock_websocket):
        """Test client disconnection."""
        client = await connection_manager.connect(mock_websocket, design_id="TEST-001")
        client_id = client.client_id

        await connection_manager.disconnect(client_id)

        assert connection_manager.client_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_unknown_client(self, connection_manager):
        """Test disconnecting unknown client is safe."""
        # Should not raise
        await connection_manager.disconnect("unknown-client")

    @pytest.mark.asyncio
    async def test_subscribe(self, connection_manager, mock_websocket):
        """Test client subscription."""
        client = await connection_manager.connect(mock_websocket)
        client_id = client.client_id

        result = await connection_manager.subscribe(client_id, "TEST-002")

        assert result is True
        assert "TEST-002" in client.subscriptions

    @pytest.mark.asyncio
    async def test_unsubscribe(self, connection_manager, mock_websocket):
        """Test client unsubscription."""
        client = await connection_manager.connect(mock_websocket, design_id="TEST-001")
        client_id = client.client_id

        result = await connection_manager.unsubscribe(client_id, "TEST-001")

        assert result is True
        assert "TEST-001" not in client.subscriptions

    @pytest.mark.asyncio
    async def test_get_design_clients(self, connection_manager, mock_websocket):
        """Test getting clients for a design."""
        client1 = await connection_manager.connect(mock_websocket, design_id="TEST-001")
        client2 = await connection_manager.connect(AsyncMock(), design_id="TEST-001")

        clients = connection_manager.get_design_clients("TEST-001")

        assert len(clients) == 2
        assert client1 in clients
        assert client2 in clients

    def test_queue_message(self, connection_manager):
        """Test message queuing."""
        from magnet.deployment.websocket import WSMessage

        msg = WSMessage(type="test", design_id="TEST-001")
        connection_manager.queue_message(msg)

        # Should not raise, message queued
        assert connection_manager._message_queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_broadcast_to_design(self, connection_manager, mock_websocket):
        """Test broadcasting to design subscribers."""
        from magnet.deployment.websocket import WSMessage

        # Connect two clients to same design
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock(return_value=None)

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock(return_value=None)

        await connection_manager.connect(ws1, design_id="TEST-001")
        await connection_manager.connect(ws2, design_id="TEST-001")

        msg = WSMessage(type="test", design_id="TEST-001")
        sent = await connection_manager.broadcast(msg)

        assert sent == 2

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, connection_manager):
        """Test broadcasting to all clients."""
        from magnet.deployment.websocket import WSMessage

        # Connect clients without design
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock(return_value=None)

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock(return_value=None)

        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)

        msg = WSMessage(type="test")  # No design_id = broadcast to all
        sent = await connection_manager.broadcast(msg)

        assert sent == 2

    @pytest.mark.asyncio
    async def test_send_to_client(self, connection_manager, mock_websocket):
        """Test sending to specific client."""
        from magnet.deployment.websocket import WSMessage

        client = await connection_manager.connect(mock_websocket)
        client_id = client.client_id

        msg = WSMessage(type="test")
        result = await connection_manager.send_to_client(client_id, msg)

        assert result is True

    @pytest.mark.asyncio
    async def test_send_to_unknown_client(self, connection_manager):
        """Test sending to unknown client returns False."""
        from magnet.deployment.websocket import WSMessage

        msg = WSMessage(type="test")
        result = await connection_manager.send_to_client("unknown", msg)

        assert result is False

    def test_on_message_handler(self, connection_manager):
        """Test registering message handler."""
        handler = Mock()
        connection_manager.on_message("custom_type", handler)

        assert "custom_type" in connection_manager._handlers
        assert handler in connection_manager._handlers["custom_type"]


# =============================================================================
# INCOMING MESSAGE HANDLER TESTS
# =============================================================================

class TestHandleIncoming:
    """Test incoming message handling."""

    @pytest.mark.asyncio
    async def test_handle_pong(self, connection_manager, mock_websocket):
        """Test handling pong message."""
        from magnet.deployment.websocket import MessageType

        client = await connection_manager.connect(mock_websocket)
        client_id = client.client_id
        old_ping = client.last_ping

        await connection_manager.handle_incoming(client_id, {
            "type": MessageType.PONG.value
        })

        # last_ping should be updated
        assert client.last_ping is not None
        assert client.last_ping != old_ping or old_ping is None

    @pytest.mark.asyncio
    async def test_handle_subscribe(self, connection_manager, mock_websocket):
        """Test handling subscribe message."""
        client = await connection_manager.connect(mock_websocket)
        client_id = client.client_id

        await connection_manager.handle_incoming(client_id, {
            "type": "subscribe",
            "design_id": "TEST-002"
        })

        assert "TEST-002" in client.subscriptions

    @pytest.mark.asyncio
    async def test_handle_unsubscribe(self, connection_manager, mock_websocket):
        """Test handling unsubscribe message."""
        client = await connection_manager.connect(mock_websocket, design_id="TEST-001")
        client_id = client.client_id

        await connection_manager.handle_incoming(client_id, {
            "type": "unsubscribe",
            "design_id": "TEST-001"
        })

        assert "TEST-001" not in client.subscriptions

    @pytest.mark.asyncio
    async def test_handle_custom_handler(self, connection_manager, mock_websocket):
        """Test custom message handler is called."""
        handler = AsyncMock()
        connection_manager.on_message("custom", handler)

        client = await connection_manager.connect(mock_websocket)
        client_id = client.client_id

        await connection_manager.handle_incoming(client_id, {
            "type": "custom",
            "payload": {"key": "value"}
        })

        handler.assert_called_once()


# =============================================================================
# EMIT FUNCTIONS TESTS
# =============================================================================

class TestEmitFunctions:
    """Test convenience emit functions."""

    def test_emit_design_created(self):
        """Test emit_design_created queues message."""
        from magnet.deployment.websocket import emit_design_created, get_connection_manager

        manager = get_connection_manager()
        initial_size = manager._message_queue.qsize()

        emit_design_created("TEST-001", "Test Design")

        assert manager._message_queue.qsize() == initial_size + 1

    def test_emit_phase_completed(self):
        """Test emit_phase_completed queues message."""
        from magnet.deployment.websocket import emit_phase_completed, get_connection_manager

        manager = get_connection_manager()
        initial_size = manager._message_queue.qsize()

        emit_phase_completed("TEST-001", "mission", "completed")

        assert manager._message_queue.qsize() == initial_size + 1

    def test_emit_phase_approved(self):
        """Test emit_phase_approved queues message."""
        from magnet.deployment.websocket import emit_phase_approved, get_connection_manager

        manager = get_connection_manager()
        initial_size = manager._message_queue.qsize()

        emit_phase_approved("TEST-001", "mission")

        assert manager._message_queue.qsize() == initial_size + 1

    def test_emit_validation_completed(self):
        """Test emit_validation_completed queues message."""
        from magnet.deployment.websocket import emit_validation_completed, get_connection_manager

        manager = get_connection_manager()
        initial_size = manager._message_queue.qsize()

        emit_validation_completed("TEST-001", "mission", passed=True, errors=0)

        assert manager._message_queue.qsize() == initial_size + 1

    def test_emit_job_completed(self):
        """Test emit_job_completed queues message."""
        from magnet.deployment.websocket import emit_job_completed, get_connection_manager

        manager = get_connection_manager()
        initial_size = manager._message_queue.qsize()

        emit_job_completed("TEST-001", "job-123", "run_phase", {"status": "ok"})

        assert manager._message_queue.qsize() == initial_size + 1

    def test_emit_error(self):
        """Test emit_error queues message."""
        from magnet.deployment.websocket import emit_error, get_connection_manager

        manager = get_connection_manager()
        initial_size = manager._message_queue.qsize()

        emit_error("TEST-001", "Something went wrong", "ERR_001")

        assert manager._message_queue.qsize() == initial_size + 1


# =============================================================================
# GLOBAL MANAGER TESTS
# =============================================================================

class TestGlobalManager:
    """Test global connection manager."""

    def test_get_connection_manager_singleton(self):
        """Test get_connection_manager returns same instance."""
        from magnet.deployment.websocket import get_connection_manager

        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2


# =============================================================================
# LIFECYCLE TESTS
# =============================================================================

class TestLifecycle:
    """Test manager lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_tasks(self, connection_manager):
        """Test start creates background tasks."""
        await connection_manager.start()

        assert connection_manager._running is True
        assert len(connection_manager._tasks) == 2  # processor + heartbeat

        await connection_manager.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_stops_tasks(self, connection_manager):
        """Test shutdown stops background tasks."""
        await connection_manager.start()
        await connection_manager.shutdown()

        assert connection_manager._running is False
        assert len(connection_manager._tasks) == 0
        assert connection_manager.client_count == 0

    @pytest.mark.asyncio
    async def test_shutdown_closes_websockets(self, connection_manager, mock_websocket):
        """Test shutdown closes all websockets."""
        await connection_manager.connect(mock_websocket)
        await connection_manager.start()

        await connection_manager.shutdown()

        mock_websocket.close.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
