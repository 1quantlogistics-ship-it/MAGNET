"""
tests/unit/test_deployment.py - Deployment module tests v1.1
BRAVO OWNS THIS FILE.

Tests for deployment infrastructure: worker, websocket, API, and RunPod handler.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch


# =============================================================================
# WORKER TESTS
# =============================================================================

class TestJobStatus:
    """Test job status enum."""

    def test_job_status_values(self):
        from magnet.deployment.worker import JobStatus
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"


class TestJobPriority:
    """Test job priority enum."""

    def test_job_priority_values(self):
        from magnet.deployment.worker import JobPriority
        assert JobPriority.LOW.value == 0
        assert JobPriority.NORMAL.value == 1
        assert JobPriority.HIGH.value == 2
        assert JobPriority.CRITICAL.value == 3


class TestJob:
    """Test job dataclass."""

    def test_job_creation(self):
        from magnet.deployment.worker import Job
        job = Job(job_type="run_phase", payload={"phase": "mission"})
        assert job.job_id != ""
        assert job.job_type == "run_phase"
        assert job.payload == {"phase": "mission"}

    def test_job_auto_id(self):
        from magnet.deployment.worker import Job
        job1 = Job()
        job2 = Job()
        assert job1.job_id != job2.job_id

    def test_job_to_dict(self):
        from magnet.deployment.worker import Job
        job = Job(job_type="test")
        d = job.to_dict()
        assert "job_id" in d
        assert d["type"] == "test"
        assert d["status"] == "pending"

    def test_job_from_dict(self):
        from magnet.deployment.worker import Job, JobStatus
        data = {
            "job_id": "test123",
            "job_type": "run_phase",
            "status": "completed",
        }
        job = Job.from_dict(data)
        assert job.job_id == "test123"
        assert job.status == JobStatus.COMPLETED

    def test_job_is_terminal(self):
        from magnet.deployment.worker import Job, JobStatus
        job = Job()
        assert not job.is_terminal

        job.status = JobStatus.COMPLETED
        assert job.is_terminal

        job.status = JobStatus.FAILED
        assert job.is_terminal

    def test_job_duration(self):
        from magnet.deployment.worker import Job
        job = Job()
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = datetime.now(timezone.utc)
        assert job.duration_seconds is not None
        assert job.duration_seconds >= 0


class TestJobQueue:
    """Test job queue."""

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self):
        from magnet.deployment.worker import JobQueue, Job
        queue = JobQueue()

        job = Job(job_type="test")
        await queue.enqueue(job)

        result = await queue.dequeue(timeout=1.0)
        assert result is not None
        assert result.job_id == job.job_id

    @pytest.mark.asyncio
    async def test_dequeue_timeout(self):
        from magnet.deployment.worker import JobQueue
        queue = JobQueue()

        result = await queue.dequeue(timeout=0.1)
        assert result is None

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        from magnet.deployment.worker import JobQueue, Job, JobPriority
        queue = JobQueue()

        low = Job(job_type="low", priority=JobPriority.LOW)
        high = Job(job_type="high", priority=JobPriority.HIGH)

        await queue.enqueue(low)
        await queue.enqueue(high)

        # Should get high priority first
        result = await queue.dequeue(timeout=0.1)
        assert result.job_type == "high"

    def test_get_job(self):
        from magnet.deployment.worker import JobQueue, Job
        queue = JobQueue()
        job = Job(job_type="test")
        queue._jobs[job.job_id] = job

        result = queue.get_job(job.job_id)
        assert result is not None
        assert result.job_id == job.job_id

    def test_get_pending_count(self):
        from magnet.deployment.worker import JobQueue
        queue = JobQueue()
        assert queue.get_pending_count() == 0


class TestWorker:
    """Test background worker."""

    def test_worker_creation(self):
        from magnet.deployment.worker import Worker
        worker = Worker(concurrency=2)
        assert worker.concurrency == 2
        assert not worker.is_running

    def test_worker_register_handler(self):
        from magnet.deployment.worker import Worker
        worker = Worker()

        async def custom_handler(job):
            return {"result": "ok"}

        worker.register_handler("custom", custom_handler)
        assert "custom" in worker._handlers

    def test_worker_stats(self):
        from magnet.deployment.worker import Worker
        worker = Worker()
        stats = worker.stats
        assert "jobs_processed" in stats
        assert "jobs_failed" in stats
        assert stats["is_running"] is False


class TestWorkerFunctions:
    """Test worker utility functions."""

    def test_get_job_queue(self):
        from magnet.deployment.worker import get_job_queue
        queue1 = get_job_queue()
        queue2 = get_job_queue()
        assert queue1 is queue2  # Singleton

    def test_get_job_status(self):
        from magnet.deployment.worker import get_job_queue, get_job_status, Job
        queue = get_job_queue()
        job = Job(job_type="test")
        queue._jobs[job.job_id] = job

        status = get_job_status(job.job_id)
        assert status is not None
        assert status["type"] == "test"

    def test_get_job_status_not_found(self):
        from magnet.deployment.worker import get_job_status
        status = get_job_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_submit_job(self):
        from magnet.deployment.worker import submit_job, get_job_queue
        job_id = await submit_job("test_type", {"key": "value"})
        assert job_id is not None

        queue = get_job_queue()
        job = queue.get_job(job_id)
        assert job is not None
        assert job.payload == {"key": "value"}


# =============================================================================
# WEBSOCKET TESTS
# =============================================================================

class TestMessageType:
    """Test WebSocket message types."""

    def test_message_types(self):
        from magnet.deployment.websocket import MessageType
        assert MessageType.CONNECT.value == "connect"
        assert MessageType.PHASE_COMPLETED.value == "phase_completed"
        assert MessageType.ERROR.value == "error"


class TestWSMessage:
    """Test WebSocket message."""

    def test_message_creation(self):
        from magnet.deployment.websocket import WSMessage
        msg = WSMessage(
            type="phase_completed",
            design_id="TEST-001",
            payload={"phase": "mission"},
        )
        assert msg.type == "phase_completed"
        assert msg.design_id == "TEST-001"
        assert msg.message_id != ""

    def test_message_to_dict(self):
        from magnet.deployment.websocket import WSMessage
        msg = WSMessage(type="test", payload={"key": "value"})
        d = msg.to_dict()
        assert d["type"] == "test"
        assert d["payload"] == {"key": "value"}

    def test_message_to_json(self):
        from magnet.deployment.websocket import WSMessage
        msg = WSMessage(type="test")
        json_str = msg.to_json()
        assert '"type": "test"' in json_str

    def test_message_from_dict(self):
        from magnet.deployment.websocket import WSMessage
        data = {"type": "test", "design_id": "D-001"}
        msg = WSMessage.from_dict(data)
        assert msg.type == "test"
        assert msg.design_id == "D-001"


class TestWSClient:
    """Test WebSocket client."""

    def test_client_creation(self):
        from magnet.deployment.websocket import WSClient
        client = WSClient(design_id="TEST-001")
        assert client.client_id != ""
        assert client.design_id == "TEST-001"

    def test_client_is_alive(self):
        from magnet.deployment.websocket import WSClient
        client = WSClient()
        assert client.is_alive is True


class TestConnectionManager:
    """Test WebSocket connection manager."""

    def test_manager_creation(self):
        from magnet.deployment.websocket import ConnectionManager
        manager = ConnectionManager()
        assert manager.client_count == 0

    def test_queue_message(self):
        from magnet.deployment.websocket import ConnectionManager, WSMessage
        manager = ConnectionManager()
        msg = WSMessage(type="test")
        manager.queue_message(msg)
        assert manager._message_queue.qsize() == 1


class TestWebSocketEmitters:
    """Test convenience emitter functions."""

    def test_emit_design_created(self):
        from magnet.deployment.websocket import emit_design_created, get_connection_manager
        # Should not raise
        emit_design_created("TEST-001", "Test Design")

    def test_emit_phase_completed(self):
        from magnet.deployment.websocket import emit_phase_completed
        emit_phase_completed("TEST-001", "mission", "completed")

    def test_emit_error(self):
        from magnet.deployment.websocket import emit_error
        emit_error("TEST-001", "Test error", "ERR-001")


# =============================================================================
# API TESTS
# =============================================================================

class TestAPICreation:
    """Test API app creation."""

    def test_create_fastapi_app_no_context(self):
        from magnet.deployment.api import create_fastapi_app
        app = create_fastapi_app(None)
        assert app is not None

    def test_create_fastapi_app_stub(self):
        from magnet.deployment.api import _create_stub_app
        app = _create_stub_app()
        assert hasattr(app, 'get')
        assert hasattr(app, 'post')


# =============================================================================
# RUNPOD HANDLER TESTS
# =============================================================================

class TestRunPodHandler:
    """Test RunPod serverless handler."""

    def test_handler_missing_operation(self):
        from magnet.deployment.runpod_handler import handler
        result = handler({"input": {}})
        # Should handle gracefully
        assert "success" in result

    def test_handler_unknown_operation(self):
        from magnet.deployment.runpod_handler import handler
        result = handler({
            "input": {
                "operation": "unknown_op",
                "parameters": {},
            }
        })
        assert result["success"] is False
        assert "Unknown operation" in result["error"]

    def test_handler_query_operation(self):
        from magnet.deployment.runpod_handler import handler
        # This will fail due to missing app, but should handle gracefully
        result = handler({
            "input": {
                "operation": "query",
                "parameters": {"path": "test"},
            }
        })
        # Result depends on whether bootstrap is fully set up
        assert "success" in result

    def test_operation_constants(self):
        # Import directly from the module to get constants (not the handler function alias)
        from magnet.deployment.runpod_handler import (
            OPERATION_RUN_PHASE,
            OPERATION_VALIDATE,
            OPERATION_QUERY,
        )
        assert OPERATION_RUN_PHASE == "run_phase"
        assert OPERATION_VALIDATE == "validate"
        assert OPERATION_QUERY == "query"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDeploymentIntegration:
    """Integration tests for deployment components."""

    @pytest.mark.asyncio
    async def test_worker_job_lifecycle(self):
        """Test full job lifecycle through worker."""
        from magnet.deployment.worker import (
            Worker, Job, JobStatus, get_job_queue
        )

        queue = get_job_queue()

        # Create job
        job = Job(job_type="run_phase", payload={"phase": "mission"})
        await queue.enqueue(job)

        # Verify enqueued
        assert queue.get_job(job.job_id) is not None
        assert job.status == JobStatus.PENDING

    def test_websocket_manager_integration(self):
        """Test WebSocket manager with message queue."""
        from magnet.deployment.websocket import (
            ConnectionManager, WSMessage, WSClient
        )

        manager = ConnectionManager()

        # Queue multiple messages
        for i in range(3):
            msg = WSMessage(type=f"test_{i}")
            manager.queue_message(msg)

        assert manager._message_queue.qsize() == 3

    def test_module_imports(self):
        """Test that all module exports work."""
        from magnet.deployment import (
            JobStatus,
            Job,
            JobQueue,
            Worker,
            get_job_queue,
            get_job_status,
            submit_job,
            WSMessage,
            WSClient,
            ConnectionManager,
            create_fastapi_app,
            runpod_handler,
        )

        # All should be importable
        assert JobStatus is not None
        assert Job is not None
        assert Worker is not None
        assert WSMessage is not None
        assert ConnectionManager is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
