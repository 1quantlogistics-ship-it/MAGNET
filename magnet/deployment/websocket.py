"""
deployment/websocket.py - WebSocket connection management v1.1
BRAVO OWNS THIS FILE.

Section 56: Deployment Infrastructure
Provides real-time updates via WebSocket connections.
Fixes blocker #5: WebSocket task not launched.
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import asyncio
import json
import logging
import uuid

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger("deployment.websocket")


class MessageType(Enum):
    """WebSocket message types."""
    # Connection
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    PING = "ping"
    PONG = "pong"

    # Design events
    DESIGN_CREATED = "design_created"
    DESIGN_UPDATED = "design_updated"
    DESIGN_DELETED = "design_deleted"

    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    PHASE_APPROVED = "phase_approved"

    # Validation events
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"

    # Job events
    JOB_SUBMITTED = "job_submitted"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"

    # Snapshot events
    SNAPSHOT_CREATED = "snapshot_created"

    # Error events
    ERROR = "error"


@dataclass
class WSMessage:
    """WebSocket message."""
    type: str = ""
    design_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    message_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not self.message_id:
            self.message_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "message_id": self.message_id,
            "design_id": self.design_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WSMessage":
        return cls(
            type=data.get("type", ""),
            message_id=data.get("message_id", ""),
            design_id=data.get("design_id"),
            payload=data.get("payload", {}),
        )


@dataclass
class WSClient:
    """WebSocket client connection."""
    client_id: str = ""
    websocket: Any = None  # WebSocket
    design_id: Optional[str] = None
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: Optional[datetime] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.client_id:
            self.client_id = str(uuid.uuid4())[:8]

    @property
    def is_alive(self) -> bool:
        """Check if client connection is likely still alive."""
        if self.last_ping is None:
            return True
        age = (datetime.now(timezone.utc) - self.last_ping).total_seconds()
        return age < 120  # 2 minutes

    async def send(self, message: WSMessage) -> bool:
        """Send message to client."""
        if self.websocket is None:
            return False
        try:
            await self.websocket.send_json(message.to_dict())
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client {self.client_id}: {e}")
            return False


class ConnectionManager:
    """
    WebSocket connection manager.

    v1.1: Proper message processor startup (fixes blocker #5)
    """

    def __init__(self, heartbeat_interval: float = 30.0):
        self._clients: Dict[str, WSClient] = {}
        self._by_design: Dict[str, Set[str]] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._running = False
        self._heartbeat_interval = heartbeat_interval
        self._tasks: List[asyncio.Task] = []

        # Event handlers
        self._handlers: Dict[str, List[Callable]] = {}

    @property
    def client_count(self) -> int:
        """Get number of connected clients."""
        return len(self._clients)

    def get_design_clients(self, design_id: str) -> List[WSClient]:
        """Get all clients subscribed to a design."""
        client_ids = self._by_design.get(design_id, set())
        return [self._clients[cid] for cid in client_ids if cid in self._clients]

    async def connect(
        self,
        websocket: "WebSocket",
        design_id: str = None,
        user_id: str = None,
    ) -> WSClient:
        """Accept new WebSocket connection."""
        await websocket.accept()

        client = WSClient(
            websocket=websocket,
            design_id=design_id,
            user_id=user_id,
        )

        async with self._lock:
            self._clients[client.client_id] = client

            if design_id:
                if design_id not in self._by_design:
                    self._by_design[design_id] = set()
                self._by_design[design_id].add(client.client_id)
                client.subscriptions.add(design_id)

        logger.info(f"Client {client.client_id} connected (design={design_id})")

        # Send connection confirmation
        await client.send(WSMessage(
            type=MessageType.CONNECT.value,
            payload={"client_id": client.client_id},
        ))

        return client

    async def disconnect(self, client_id: str) -> None:
        """Disconnect a client."""
        async with self._lock:
            if client_id not in self._clients:
                return

            client = self._clients.pop(client_id)

            # Remove from design subscriptions
            for design_id in client.subscriptions:
                if design_id in self._by_design:
                    self._by_design[design_id].discard(client_id)
                    if not self._by_design[design_id]:
                        del self._by_design[design_id]

        logger.info(f"Client {client_id} disconnected")

    async def subscribe(self, client_id: str, design_id: str) -> bool:
        """Subscribe client to design updates."""
        async with self._lock:
            if client_id not in self._clients:
                return False

            client = self._clients[client_id]
            client.subscriptions.add(design_id)

            if design_id not in self._by_design:
                self._by_design[design_id] = set()
            self._by_design[design_id].add(client_id)

        logger.debug(f"Client {client_id} subscribed to {design_id}")
        return True

    async def unsubscribe(self, client_id: str, design_id: str) -> bool:
        """Unsubscribe client from design updates."""
        async with self._lock:
            if client_id not in self._clients:
                return False

            client = self._clients[client_id]
            client.subscriptions.discard(design_id)

            if design_id in self._by_design:
                self._by_design[design_id].discard(client_id)

        logger.debug(f"Client {client_id} unsubscribed from {design_id}")
        return True

    def queue_message(self, message: WSMessage) -> None:
        """Queue a message for broadcast."""
        self._message_queue.put_nowait(message)

    async def broadcast(self, message: WSMessage) -> int:
        """Broadcast message to relevant clients."""
        sent = 0

        if message.design_id:
            # Send to clients subscribed to this design
            clients = self.get_design_clients(message.design_id)
        else:
            # Send to all clients
            clients = list(self._clients.values())

        for client in clients:
            if await client.send(message):
                sent += 1

        if sent > 0:
            logger.debug(f"Broadcast {message.type} to {sent} clients")

        return sent

    async def send_to_client(self, client_id: str, message: WSMessage) -> bool:
        """Send message to specific client."""
        client = self._clients.get(client_id)
        if client:
            return await client.send(message)
        return False

    async def process_messages(self) -> None:
        """
        Process queued messages (v1.1: started on API startup).

        This coroutine runs continuously and broadcasts queued messages.
        """
        self._running = True
        logger.info("WebSocket message processor started")

        while self._running:
            try:
                # Get message with timeout
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )
                await self.broadcast(message)

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Message processor error: {e}")

        logger.info("WebSocket message processor stopped")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat pings."""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)

                # Send ping to all clients
                ping = WSMessage(type=MessageType.PING.value)
                disconnected = []

                for client_id, client in list(self._clients.items()):
                    if not await client.send(ping):
                        disconnected.append(client_id)
                    else:
                        client.last_ping = datetime.now(timezone.utc)

                # Clean up disconnected clients
                for client_id in disconnected:
                    await self.disconnect(client_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def start(self) -> None:
        """Start the connection manager background tasks."""
        self._running = True

        # Start message processor
        processor_task = asyncio.create_task(self.process_messages())
        self._tasks.append(processor_task)

        # Start heartbeat
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._tasks.append(heartbeat_task)

        logger.info("Connection manager started")

    async def shutdown(self) -> None:
        """Shutdown connection manager and disconnect all clients."""
        self._running = False
        logger.info("Shutting down connection manager...")

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

        logger.info("Connection manager shutdown complete")

    def on_message(self, message_type: str, handler: Callable) -> None:
        """Register handler for incoming message type."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)

    async def handle_incoming(self, client_id: str, data: Dict[str, Any]) -> None:
        """Handle incoming message from client."""
        message = WSMessage.from_dict(data)

        if message.type == MessageType.PONG.value:
            # Update last ping time
            if client_id in self._clients:
                self._clients[client_id].last_ping = datetime.now(timezone.utc)
            return

        if message.type == "subscribe" and message.design_id:
            await self.subscribe(client_id, message.design_id)
            return

        if message.type == "unsubscribe" and message.design_id:
            await self.unsubscribe(client_id, message.design_id)
            return

        # Call registered handlers
        handlers = self._handlers.get(message.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(client_id, message)
                else:
                    handler(client_id, message)
            except Exception as e:
                logger.error(f"Handler error for {message.type}: {e}")


# Global connection manager
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get global connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


# Convenience functions for emitting events
def emit_design_created(design_id: str, name: str = "") -> None:
    """Emit design created event."""
    manager = get_connection_manager()
    manager.queue_message(WSMessage(
        type=MessageType.DESIGN_CREATED.value,
        design_id=design_id,
        payload={"name": name},
    ))


def emit_phase_completed(design_id: str, phase: str, status: str = "completed") -> None:
    """Emit phase completed event."""
    manager = get_connection_manager()
    manager.queue_message(WSMessage(
        type=MessageType.PHASE_COMPLETED.value,
        design_id=design_id,
        payload={"phase": phase, "status": status},
    ))


def emit_phase_approved(design_id: str, phase: str) -> None:
    """Emit phase approved event."""
    manager = get_connection_manager()
    manager.queue_message(WSMessage(
        type=MessageType.PHASE_APPROVED.value,
        design_id=design_id,
        payload={"phase": phase},
    ))


def emit_validation_completed(design_id: str, phase: str, passed: bool, errors: int = 0) -> None:
    """Emit validation completed event."""
    manager = get_connection_manager()
    manager.queue_message(WSMessage(
        type=MessageType.VALIDATION_COMPLETED.value,
        design_id=design_id,
        payload={"phase": phase, "passed": passed, "errors": errors},
    ))


def emit_job_completed(design_id: str, job_id: str, job_type: str, result: Any = None) -> None:
    """Emit job completed event."""
    manager = get_connection_manager()
    manager.queue_message(WSMessage(
        type=MessageType.JOB_COMPLETED.value,
        design_id=design_id,
        payload={"job_id": job_id, "job_type": job_type, "result": result},
    ))


def emit_error(design_id: str, message: str, code: str = "") -> None:
    """Emit error event."""
    manager = get_connection_manager()
    manager.queue_message(WSMessage(
        type=MessageType.ERROR.value,
        design_id=design_id,
        payload={"message": message, "code": code},
    ))
