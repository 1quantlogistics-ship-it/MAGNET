"""
MAGNET API Module
=================

FastAPI control plane and REST endpoints for MAGNET.
Provides the user interface for design sessions.

Endpoints:
- /chat: User chat interface
- /status: System status
- /design: Current design state
- /validate: Trigger validation
- /export: Export design
- /rollback: Rollback to previous state
"""

from .control_plane import app, create_app

__all__ = ["app", "create_app"]
