"""
magnet/systems/structural/

T6.* (guide): Structural system generators (thin wrappers).

These live under systems/ to match the "systems-as-geometry" organization used by
other systems modules (fuel, electrical, etc.), but they intentionally reuse the
existing `magnet.structural.*` generators rather than duplicating logic.
"""

from .stringer import StringerGenerator
from .bulkhead import BulkheadGenerator
from .frame import FrameGenerator

__all__ = [
    "StringerGenerator",
    "BulkheadGenerator",
    "FrameGenerator",
]

