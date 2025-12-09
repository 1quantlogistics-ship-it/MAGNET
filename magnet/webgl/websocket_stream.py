"""
webgl/websocket_stream.py - WebSocket geometry streaming v1.1
BRAVO OWNS THIS FILE.

Module 58: WebGL 3D Visualization
Provides delta-based real-time geometry streaming.
Addresses: FM7 (Streaming under-specified)

Protocol:
- GeometryUpdateMessage: Delta or full geometry updates
- GeometryFailedMessage: Error notification
- Delta tracking via update_id/prev_update_id chain
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import json
import logging
import uuid

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger("webgl.websocket_stream")


# =============================================================================
# MESSAGE TYPES
# =============================================================================

class StreamMessageType(Enum):
    """WebSocket stream message types."""
    GEOMETRY_UPDATE = "geometry_update"
    GEOMETRY_FAILED = "geometry_failed"
    GEOMETRY_INVALIDATED = "geometry_invalidated"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    PONG = "pong"


@dataclass
class GeometryUpdateMessage:
    """
    Geometry update message - delta or full update.

    v1.1: Delta tracking via update chain (FM7)
    - update_id: Unique ID for this update
    - prev_update_id: ID of previous update (for ordering)
    - is_full_update: If true, replace all; ignore delta
    """
    design_id: str
    update_id: str = ""
    prev_update_id: str = ""
    hull: Optional[Dict[str, Any]] = None      # MeshData or null (unchanged)
    deck: Optional[Dict[str, Any]] = None
    structure: Optional[Dict[str, Any]] = None  # StructureSceneData or null
    is_full_update: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_type: str = field(default=StreamMessageType.GEOMETRY_UPDATE.value, init=False)

    def __post_init__(self):
        if not self.update_id:
            self.update_id = str(uuid.uuid4())[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_type": self.message_type,
            "update_id": self.update_id,
            "prev_update_id": self.prev_update_id,
            "design_id": self.design_id,
            "hull": self.hull,
            "deck": self.deck,
            "structure": self.structure,
            "is_full_update": self.is_full_update,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeometryUpdateMessage":
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            timestamp = datetime.now(timezone.utc)

        return cls(
            design_id=data.get("design_id", ""),
            update_id=data.get("update_id", ""),
            prev_update_id=data.get("prev_update_id", ""),
            hull=data.get("hull"),
            deck=data.get("deck"),
            structure=data.get("structure"),
            is_full_update=data.get("is_full_update", False),
            timestamp=timestamp,
        )


@dataclass
class GeometryFailedMessage:
    """
    Geometry failure notification.

    v1.1: Structured error reporting (FM5 integration)
    """
    design_id: str
    error_code: str
    error_message: str
    recovery_hint: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_type: str = field(default=StreamMessageType.GEOMETRY_FAILED.value, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_type": self.message_type,
            "design_id": self.design_id,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "recovery_hint": self.recovery_hint,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class GeometryInvalidatedMessage:
    """Notification that geometry needs refresh."""
    design_id: str
    reason: str = ""
    invalidated_components: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_type: str = field(default=StreamMessageType.GEOMETRY_INVALIDATED.value, init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_type": self.message_type,
            "design_id": self.design_id,
            "reason": self.reason,
            "invalidated_components": self.invalidated_components,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# =============================================================================
# STREAM CLIENT
# =============================================================================

@dataclass
class StreamClient:
    """WebSocket stream client connection."""
    client_id: str = ""
    websocket: Any = None  # WebSocket
    design_subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update_ids: Dict[str, str] = field(default_factory=dict)  # design_id -> last update_id

    def __post_init__(self):
        if not self.client_id:
            self.client_id = str(uuid.uuid4())[:8]

    @property
    def is_stale(self) -> bool:
        """Check if client connection is stale (no activity for 2 minutes)."""
        age = (datetime.now(timezone.utc) - self.last_activity).total_seconds()
        return age > 120

    async def send(self, message: Dict[str, Any]) -> bool:
        """Send message to client."""
        if self.websocket is None:
            return False
        try:
            await self.websocket.send_json(message)
            self.last_activity = datetime.now(timezone.utc)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to stream client {self.client_id}: {e}")
            return False

    def get_last_update_id(self, design_id: str) -> str:
        """Get last received update ID for delta tracking."""
        return self.last_update_ids.get(design_id, "")

    def set_last_update_id(self, design_id: str, update_id: str) -> None:
        """Set last received update ID."""
        self.last_update_ids[design_id] = update_id


# =============================================================================
# STREAM MANAGER
# =============================================================================

class GeometryStreamManager:
    """
    WebSocket geometry stream manager.

    v1.1: Delta-based streaming protocol (FM7)
    - Tracks update chains per design
    - Broadcasts deltas to subscribed clients
    - Handles reconnection with full update
    """

    def __init__(self, heartbeat_interval: float = 30.0):
        self._clients: Dict[str, StreamClient] = {}
        self._by_design: Dict[str, Set[str]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._running = False
        self._heartbeat_interval = heartbeat_interval
        self._tasks: List[asyncio.Task] = []

        # Update tracking for delta protocol
        self._last_updates: Dict[str, str] = {}  # design_id -> last update_id

    @property
    def client_count(self) -> int:
        """Get number of connected clients."""
        return len(self._clients)

    def get_design_clients(self, design_id: str) -> List[StreamClient]:
        """Get all clients subscribed to a design."""
        client_ids = self._by_design.get(design_id, set())
        return [self._clients[cid] for cid in client_ids if cid in self._clients]

    async def connect(self, websocket: "WebSocket") -> StreamClient:
        """Accept new WebSocket connection."""
        await websocket.accept()

        client = StreamClient(websocket=websocket)

        async with self._lock:
            self._clients[client.client_id] = client

        logger.info(f"Stream client {client.client_id} connected")

        # Send connection confirmation
        await client.send({
            "message_type": "connected",
            "client_id": client.client_id,
        })

        return client

    async def disconnect(self, client_id: str) -> None:
        """Disconnect a client."""
        async with self._lock:
            if client_id not in self._clients:
                return

            client = self._clients.pop(client_id)

            # Remove from design subscriptions
            for design_id in client.design_subscriptions:
                if design_id in self._by_design:
                    self._by_design[design_id].discard(client_id)
                    if not self._by_design[design_id]:
                        del self._by_design[design_id]

        logger.info(f"Stream client {client_id} disconnected")

    async def subscribe(self, client_id: str, design_id: str) -> bool:
        """Subscribe client to design geometry updates."""
        async with self._lock:
            if client_id not in self._clients:
                return False

            client = self._clients[client_id]
            client.design_subscriptions.add(design_id)

            if design_id not in self._by_design:
                self._by_design[design_id] = set()
            self._by_design[design_id].add(client_id)

        logger.debug(f"Stream client {client_id} subscribed to geometry for {design_id}")
        return True

    async def unsubscribe(self, client_id: str, design_id: str) -> bool:
        """Unsubscribe client from design geometry updates."""
        async with self._lock:
            if client_id not in self._clients:
                return False

            client = self._clients[client_id]
            client.design_subscriptions.discard(design_id)

            if design_id in self._by_design:
                self._by_design[design_id].discard(client_id)

        logger.debug(f"Stream client {client_id} unsubscribed from {design_id}")
        return True

    def queue_update(self, message: GeometryUpdateMessage) -> None:
        """Queue a geometry update for broadcast."""
        # Track update chain
        message.prev_update_id = self._last_updates.get(message.design_id, "")
        self._last_updates[message.design_id] = message.update_id

        self._message_queue.put_nowait(("update", message))

    def queue_failure(self, message: GeometryFailedMessage) -> None:
        """Queue a failure notification for broadcast."""
        self._message_queue.put_nowait(("failure", message))

    def queue_invalidation(self, message: GeometryInvalidatedMessage) -> None:
        """Queue an invalidation notification for broadcast."""
        self._message_queue.put_nowait(("invalidated", message))

    async def broadcast_update(self, message: GeometryUpdateMessage) -> int:
        """Broadcast geometry update to subscribed clients."""
        sent = 0
        clients = self.get_design_clients(message.design_id)

        for client in clients:
            # Check if client needs full update (missed updates)
            client_last_id = client.get_last_update_id(message.design_id)
            if client_last_id and client_last_id != message.prev_update_id:
                # Client missed updates, mark as full update
                msg_dict = message.to_dict()
                msg_dict["is_full_update"] = True
            else:
                msg_dict = message.to_dict()

            if await client.send(msg_dict):
                client.set_last_update_id(message.design_id, message.update_id)
                sent += 1

        if sent > 0:
            logger.debug(f"Broadcast geometry update for {message.design_id} to {sent} clients")

        return sent

    async def broadcast_failure(self, message: GeometryFailedMessage) -> int:
        """Broadcast failure notification to subscribed clients."""
        sent = 0
        clients = self.get_design_clients(message.design_id)

        for client in clients:
            if await client.send(message.to_dict()):
                sent += 1

        return sent

    async def broadcast_invalidation(self, message: GeometryInvalidatedMessage) -> int:
        """Broadcast invalidation notification to subscribed clients."""
        sent = 0
        clients = self.get_design_clients(message.design_id)

        for client in clients:
            if await client.send(message.to_dict()):
                sent += 1

        return sent

    async def process_messages(self) -> None:
        """Process queued messages."""
        self._running = True
        logger.info("Geometry stream processor started")

        while self._running:
            try:
                msg_type, message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )

                if msg_type == "update":
                    await self.broadcast_update(message)
                elif msg_type == "failure":
                    await self.broadcast_failure(message)
                elif msg_type == "invalidated":
                    await self.broadcast_invalidation(message)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream processor error: {e}")

        logger.info("Geometry stream processor stopped")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat pings."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                ping = {"message_type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()}
                disconnected = []

                for client_id, client in list(self._clients.items()):
                    if client.is_stale:
                        disconnected.append(client_id)
                    elif not await client.send(ping):
                        disconnected.append(client_id)

                # Clean up disconnected clients
                for client_id in disconnected:
                    await self.disconnect(client_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stream heartbeat error: {e}")

    async def start(self) -> None:
        """Start the stream manager background tasks."""
        self._running = True

        processor_task = asyncio.create_task(self.process_messages())
        self._tasks.append(processor_task)

        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._tasks.append(heartbeat_task)

        logger.info("Geometry stream manager started")

    async def shutdown(self) -> None:
        """Shutdown stream manager and disconnect all clients."""
        self._running = False
        logger.info("Shutting down geometry stream manager...")

        # Cancel background tasks
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Disconnect all clients
        for client_id in list(self._clients.keys()):
            client = self._clients.get(client_id)
            if client and client.websocket:
                try:
                    await client.websocket.close()
                except Exception:
                    pass

        self._clients.clear()
        self._by_design.clear()

        logger.info("Geometry stream manager shutdown complete")

    async def handle_incoming(self, client_id: str, data: Dict[str, Any]) -> None:
        """Handle incoming message from client."""
        msg_type = data.get("message_type", "")

        if msg_type == "pong":
            if client_id in self._clients:
                self._clients[client_id].last_activity = datetime.now(timezone.utc)
            return

        if msg_type == "subscribe":
            design_id = data.get("design_id")
            if design_id:
                await self.subscribe(client_id, design_id)
            return

        if msg_type == "unsubscribe":
            design_id = data.get("design_id")
            if design_id:
                await self.unsubscribe(client_id, design_id)
            return

        logger.debug(f"Unknown stream message type: {msg_type}")


# =============================================================================
# GLOBAL MANAGER
# =============================================================================

_stream_manager: Optional[GeometryStreamManager] = None


def get_stream_manager() -> GeometryStreamManager:
    """Get global geometry stream manager."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = GeometryStreamManager()
    return _stream_manager


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def emit_geometry_update(
    design_id: str,
    hull: Optional[Dict[str, Any]] = None,
    deck: Optional[Dict[str, Any]] = None,
    structure: Optional[Dict[str, Any]] = None,
    is_full: bool = False,
) -> None:
    """Emit a geometry update to all subscribed clients."""
    manager = get_stream_manager()
    message = GeometryUpdateMessage(
        design_id=design_id,
        hull=hull,
        deck=deck,
        structure=structure,
        is_full_update=is_full,
    )
    manager.queue_update(message)


def emit_geometry_failure(
    design_id: str,
    error_code: str,
    error_message: str,
    recovery_hint: Optional[str] = None,
) -> None:
    """Emit a geometry failure notification."""
    manager = get_stream_manager()
    message = GeometryFailedMessage(
        design_id=design_id,
        error_code=error_code,
        error_message=error_message,
        recovery_hint=recovery_hint,
    )
    manager.queue_failure(message)


def emit_geometry_invalidated(
    design_id: str,
    reason: str = "",
    components: Optional[List[str]] = None,
) -> None:
    """Emit a geometry invalidation notification."""
    manager = get_stream_manager()
    message = GeometryInvalidatedMessage(
        design_id=design_id,
        reason=reason,
        invalidated_components=components or [],
    )
    manager.queue_invalidation(message)
