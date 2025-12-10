"""
config.py - Routing configuration v1.1
BRAVO OWNS THIS FILE.

Module 60: Systems Routing
Configuration dataclass for routing module.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, FrozenSet
import logging

__all__ = [
    'RoutingConfig',
    'DEFAULT_CONFIG',
]

logger = logging.getLogger(__name__)


# =============================================================================
# ROUTING CONFIGURATION
# =============================================================================

@dataclass
class RoutingConfig:
    """
    Configuration for the routing module.

    Controls routing algorithm behavior, validation thresholds,
    and optimization parameters.
    """

    # =========================================================================
    # ROUTING ALGORITHM
    # =========================================================================

    # Use MST-based routing (vs greedy)
    use_mst_routing: bool = True

    # Maximum path length before considering alternate routes
    max_path_length_m: float = 100.0

    # Maximum zone crossings per trunk
    max_zone_crossings: int = 2

    # Prioritize shorter paths over fewer crossings
    prefer_length_over_crossings: bool = False

    # =========================================================================
    # ZONE COMPLIANCE
    # =========================================================================

    # Strict zone enforcement (fail on any violation)
    strict_zone_enforcement: bool = True

    # Allow penetrations through fire zones
    allow_fire_zone_penetrations: bool = False

    # Allow penetrations through watertight boundaries
    allow_watertight_penetrations: bool = True

    # Max penetrations per boundary
    max_penetrations_per_boundary: int = 5

    # =========================================================================
    # SEPARATION RULES
    # =========================================================================

    # Default minimum separation distance (meters)
    default_min_separation_m: float = 0.15

    # Enforce separation rules strictly
    strict_separation_enforcement: bool = True

    # =========================================================================
    # REDUNDANCY
    # =========================================================================

    # Require redundancy for critical systems
    require_critical_redundancy: bool = True

    # Minimum path diversity score for redundancy
    min_diversity_score: float = 0.5

    # Critical systems that require redundancy
    critical_systems: FrozenSet[str] = field(default_factory=lambda: frozenset({
        'electrical_hv',
        'firefighting',
        'fire_detection',
        'bilge',
    }))

    # =========================================================================
    # CAPACITY
    # =========================================================================

    # Capacity safety factor (multiply demand by this)
    capacity_safety_factor: float = 1.25

    # Default trunk sizes by system type (mm or amps)
    default_trunk_sizes: Dict[str, float] = field(default_factory=lambda: {
        'fuel': 50.0,
        'freshwater': 40.0,
        'seawater': 65.0,
        'hvac_supply': 300.0,
        'electrical_hv': 100.0,
        'electrical_lv': 50.0,
        'firefighting': 65.0,
    })

    # =========================================================================
    # OPTIMIZATION
    # =========================================================================

    # Enable automatic route optimization
    enable_optimization: bool = True

    # Optimization objective weights
    length_weight: float = 1.0
    crossing_weight: float = 2.0
    conflict_weight: float = 5.0

    # Maximum optimization iterations
    max_optimization_iterations: int = 100

    # =========================================================================
    # MULTI-SYSTEM
    # =========================================================================

    # Enable automatic conflict resolution
    auto_resolve_conflicts: bool = True

    # Maximum conflict resolution attempts
    max_resolution_attempts: int = 3

    # Systems that can share routing (pairs)
    shareable_systems: List[tuple] = field(default_factory=lambda: [
        ('freshwater', 'firefighting'),
        ('electrical_lv', 'fire_detection'),
    ])

    # =========================================================================
    # VALIDATION
    # =========================================================================

    # Run validation after each routing operation
    validate_after_routing: bool = True

    # Treat warnings as errors
    strict_validation: bool = False

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            # Routing
            'use_mst_routing': self.use_mst_routing,
            'max_path_length_m': self.max_path_length_m,
            'max_zone_crossings': self.max_zone_crossings,
            'prefer_length_over_crossings': self.prefer_length_over_crossings,

            # Zone compliance
            'strict_zone_enforcement': self.strict_zone_enforcement,
            'allow_fire_zone_penetrations': self.allow_fire_zone_penetrations,
            'allow_watertight_penetrations': self.allow_watertight_penetrations,
            'max_penetrations_per_boundary': self.max_penetrations_per_boundary,

            # Separation
            'default_min_separation_m': self.default_min_separation_m,
            'strict_separation_enforcement': self.strict_separation_enforcement,

            # Redundancy
            'require_critical_redundancy': self.require_critical_redundancy,
            'min_diversity_score': self.min_diversity_score,
            'critical_systems': list(self.critical_systems),

            # Capacity
            'capacity_safety_factor': self.capacity_safety_factor,
            'default_trunk_sizes': self.default_trunk_sizes,

            # Optimization
            'enable_optimization': self.enable_optimization,
            'length_weight': self.length_weight,
            'crossing_weight': self.crossing_weight,
            'conflict_weight': self.conflict_weight,
            'max_optimization_iterations': self.max_optimization_iterations,

            # Multi-system
            'auto_resolve_conflicts': self.auto_resolve_conflicts,
            'max_resolution_attempts': self.max_resolution_attempts,
            'shareable_systems': self.shareable_systems,

            # Validation
            'validate_after_routing': self.validate_after_routing,
            'strict_validation': self.strict_validation,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RoutingConfig":
        """Deserialize from dictionary."""
        # Handle critical_systems frozenset
        critical = data.get('critical_systems')
        if critical is not None:
            data = dict(data)
            data['critical_systems'] = frozenset(critical)

        # Filter to known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}

        return cls(**filtered)


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = RoutingConfig()
