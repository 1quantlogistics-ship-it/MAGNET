"""
hull_gen/modifiers - Section modifiers for hull geometry generation.

Phase 4: Provides modular section modification pipeline for adding
longitudinal features like spray rails and knuckle lines.

Phase 6: Added TumblehomeModifier for above-waterline inward lean.
"""

from magnet.hull_gen.modifiers.base import SectionModifier
from magnet.hull_gen.modifiers.spray_rail import SprayRailModifier
from magnet.hull_gen.modifiers.knuckle import KnuckleModifier
from magnet.hull_gen.modifiers.tumblehome import TumblehomeModifier

__all__ = [
    'SectionModifier',
    'SprayRailModifier',
    'KnuckleModifier',
    'TumblehomeModifier',
]

