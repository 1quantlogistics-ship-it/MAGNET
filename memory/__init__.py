"""
MAGNET Memory Module
====================

File-based agent communication protocol for MAGNET.
All agent communication persists to JSON files for auditability.

Key Components:
- file_io: JSON file read/write utilities
- schemas: Pydantic schemas for message validation
"""

from .file_io import MemoryFileIO
from .schemas import (
    MissionSchema,
    HullParamsSchema,
    SystemStateSchema,
    AgentVoteSchema,
)

__all__ = [
    "MemoryFileIO",
    "MissionSchema",
    "HullParamsSchema",
    "SystemStateSchema",
    "AgentVoteSchema",
]
