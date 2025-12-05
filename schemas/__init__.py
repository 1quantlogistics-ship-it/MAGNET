"""
MAGNET V1 Schemas Module (ALPHA)

Core Pydantic schemas for the MAGNET naval design system.
"""

from .mission import MissionSchema, MissionType
from .hull_params import HullParamsSchema

__all__ = [
    'MissionSchema',
    'MissionType',
    'HullParamsSchema',
]
