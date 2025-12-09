"""
deployment/ - Deployment Infrastructure (Module 56)
BRAVO OWNS THIS FILE.

Provides API, Worker, WebSocket, and deployment infrastructure.

v1.1 Changes:
- Worker implementation (fixes blocker #7)
- API with PhaseMachine integration (fixes blockers #5, #8, #11)
- WebSocket message processor startup
- RunPod serverless handler
"""

from .worker import (
    JobStatus,
    Job,
    JobQueue,
    Worker,
    get_job_queue,
    get_job_status,
    submit_job,
)

from .websocket import (
    WSMessage,
    WSClient,
    ConnectionManager,
)

from .api import (
    create_fastapi_app,
)

from .runpod_handler import (
    handler as runpod_handler,
)


__all__ = [
    # Worker
    "JobStatus",
    "Job",
    "JobQueue",
    "Worker",
    "get_job_queue",
    "get_job_status",
    "submit_job",
    # WebSocket
    "WSMessage",
    "WSClient",
    "ConnectionManager",
    # API
    "create_fastapi_app",
    # RunPod
    "runpod_handler",
]
