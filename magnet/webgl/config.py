"""
webgl/config.py - Geometry configuration v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides configuration for geometry generation, LOD levels,
and resource limits.

Addresses: FM3 (Performance collapse)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
from enum import Enum
import os
import logging

logger = logging.getLogger("webgl.config")


# Re-export LODLevel from schema for convenience
from .schema import LODLevel


# =============================================================================
# LOD CONFIGURATION
# =============================================================================

@dataclass
class LODConfig:
    """Configuration for a specific LOD level."""

    level: LODLevel

    # Tessellation parameters
    sections_count: int          # Number of hull sections
    waterlines_count: int        # Number of waterlines
    circumferential_points: int  # Points per section curve

    # Resource limits
    max_vertices: int
    max_faces: int
    max_memory_mb: int
    timeout_seconds: int

    # Quality settings
    normal_smoothing: bool = True
    compute_uvs: bool = False
    compute_tangents: bool = False

    def __post_init__(self):
        """Validate configuration."""
        assert self.sections_count > 0, "sections_count must be positive"
        assert self.waterlines_count > 0, "waterlines_count must be positive"
        assert self.circumferential_points > 0, "circumferential_points must be positive"


# Predefined LOD configurations
LOD_CONFIGS: Dict[LODLevel, LODConfig] = {
    LODLevel.LOW: LODConfig(
        level=LODLevel.LOW,
        sections_count=10,
        waterlines_count=5,
        circumferential_points=8,
        max_vertices=5_000,
        max_faces=10_000,
        max_memory_mb=16,
        timeout_seconds=5,
        normal_smoothing=False,
        compute_uvs=False,
    ),
    LODLevel.MEDIUM: LODConfig(
        level=LODLevel.MEDIUM,
        sections_count=20,
        waterlines_count=10,
        circumferential_points=16,
        max_vertices=25_000,
        max_faces=50_000,
        max_memory_mb=64,
        timeout_seconds=15,
        normal_smoothing=True,
        compute_uvs=False,
    ),
    LODLevel.HIGH: LODConfig(
        level=LODLevel.HIGH,
        sections_count=40,
        waterlines_count=20,
        circumferential_points=32,
        max_vertices=100_000,
        max_faces=200_000,
        max_memory_mb=256,
        timeout_seconds=30,
        normal_smoothing=True,
        compute_uvs=True,
    ),
    LODLevel.ULTRA: LODConfig(
        level=LODLevel.ULTRA,
        sections_count=80,
        waterlines_count=40,
        circumferential_points=64,
        max_vertices=500_000,
        max_faces=1_000_000,
        max_memory_mb=1024,
        timeout_seconds=120,
        normal_smoothing=True,
        compute_uvs=True,
        compute_tangents=True,
    ),
}


# =============================================================================
# RESOURCE LIMITS
# =============================================================================

@dataclass
class ResourceLimits:
    """Resource limits for geometry operations."""

    # Memory limits
    max_memory_mb: int = 256
    max_vertex_buffer_mb: int = 64
    max_index_buffer_mb: int = 32

    # Compute limits
    max_concurrent_jobs: int = 4
    job_timeout_seconds: int = 60

    # LOD restrictions
    max_lod_level: LODLevel = LODLevel.HIGH
    default_lod_level: LODLevel = LODLevel.MEDIUM

    # Cache settings
    cache_enabled: bool = True
    cache_max_entries: int = 100
    cache_ttl_seconds: int = 3600

    @classmethod
    def from_env(cls) -> "ResourceLimits":
        """Create resource limits from environment variables."""
        max_lod = os.getenv("MAGNET_WEBGL_MAX_LOD", "high")
        default_lod = os.getenv("MAGNET_WEBGL_DEFAULT_LOD", "medium")

        return cls(
            max_memory_mb=int(os.getenv("MAGNET_WEBGL_MAX_MEMORY_MB", "256")),
            max_vertex_buffer_mb=int(os.getenv("MAGNET_WEBGL_MAX_VERTEX_MB", "64")),
            max_index_buffer_mb=int(os.getenv("MAGNET_WEBGL_MAX_INDEX_MB", "32")),
            max_concurrent_jobs=int(os.getenv("MAGNET_WEBGL_MAX_JOBS", "4")),
            job_timeout_seconds=int(os.getenv("MAGNET_WEBGL_JOB_TIMEOUT", "60")),
            max_lod_level=LODLevel(max_lod),
            default_lod_level=LODLevel(default_lod),
            cache_enabled=os.getenv("MAGNET_WEBGL_CACHE_ENABLED", "true").lower() == "true",
            cache_max_entries=int(os.getenv("MAGNET_WEBGL_CACHE_MAX_ENTRIES", "100")),
            cache_ttl_seconds=int(os.getenv("MAGNET_WEBGL_CACHE_TTL", "3600")),
        )


# =============================================================================
# TESSELLATION CONFIG
# =============================================================================

@dataclass
class TessellationConfig:
    """Configuration for hull tessellation."""

    # Section generation
    sections_count: int = 20
    waterlines_count: int = 10
    circumferential_points: int = 16

    # Mesh quality
    min_edge_length: float = 0.01  # meters
    max_edge_length: float = 2.0   # meters
    angle_tolerance_deg: float = 15.0

    # Feature preservation
    preserve_hard_edges: bool = True
    hard_edge_angle_deg: float = 30.0

    # Deck and transom
    include_deck: bool = True
    include_transom: bool = True
    deck_camber_height: float = 0.0  # meters

    @classmethod
    def from_lod(cls, lod: LODLevel) -> "TessellationConfig":
        """Create tessellation config from LOD level."""
        lod_config = LOD_CONFIGS.get(lod, LOD_CONFIGS[LODLevel.MEDIUM])

        return cls(
            sections_count=lod_config.sections_count,
            waterlines_count=lod_config.waterlines_count,
            circumferential_points=lod_config.circumferential_points,
        )


# =============================================================================
# GEOMETRY CONFIG
# =============================================================================

@dataclass
class GeometryConfig:
    """Main configuration for geometry service."""

    # LOD settings
    lod_configs: Dict[LODLevel, LODConfig] = field(default_factory=lambda: LOD_CONFIGS.copy())
    default_lod: LODLevel = LODLevel.MEDIUM

    # Resource limits
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)

    # Tessellation defaults
    tessellation: TessellationConfig = field(default_factory=TessellationConfig)

    # Visual-only mode
    allow_visual_only_default: bool = False

    # Caching
    enable_geometry_cache: bool = True
    cache_invalidation_on_state_change: bool = True

    # Event emission
    emit_geometry_events: bool = True

    # Export settings
    export_include_metadata: bool = True
    export_default_format: str = "gltf"

    def get_lod_config(self, lod: LODLevel) -> LODConfig:
        """Get configuration for LOD level."""
        return self.lod_configs.get(lod, self.lod_configs[LODLevel.MEDIUM])

    def validate_lod(self, requested: LODLevel) -> LODLevel:
        """
        Validate and potentially downgrade LOD level.

        Returns the actual LOD to use (may be lower than requested
        if resource limits don't allow).
        """
        max_lod = self.resource_limits.max_lod_level

        # Order of LOD levels
        lod_order = [LODLevel.LOW, LODLevel.MEDIUM, LODLevel.HIGH, LODLevel.ULTRA]

        requested_idx = lod_order.index(requested)
        max_idx = lod_order.index(max_lod)

        if requested_idx > max_idx:
            logger.warning(
                f"LOD {requested.value} exceeds max {max_lod.value}, downgrading"
            )
            return max_lod

        return requested

    @classmethod
    def from_env(cls) -> "GeometryConfig":
        """Create configuration from environment variables."""
        resource_limits = ResourceLimits.from_env()

        default_lod = os.getenv("MAGNET_WEBGL_DEFAULT_LOD", "medium")

        return cls(
            default_lod=LODLevel(default_lod),
            resource_limits=resource_limits,
            allow_visual_only_default=os.getenv(
                "MAGNET_WEBGL_ALLOW_VISUAL_ONLY", "false"
            ).lower() == "true",
            enable_geometry_cache=os.getenv(
                "MAGNET_WEBGL_CACHE_ENABLED", "true"
            ).lower() == "true",
            emit_geometry_events=os.getenv(
                "MAGNET_WEBGL_EMIT_EVENTS", "true"
            ).lower() == "true",
            export_default_format=os.getenv(
                "MAGNET_WEBGL_EXPORT_FORMAT", "gltf"
            ),
        )


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

# Singleton default configuration
DEFAULT_GEOMETRY_CONFIG = GeometryConfig.from_env()


def get_geometry_config() -> GeometryConfig:
    """Get the default geometry configuration."""
    return DEFAULT_GEOMETRY_CONFIG


def set_geometry_config(config: GeometryConfig) -> None:
    """Set the default geometry configuration."""
    global DEFAULT_GEOMETRY_CONFIG
    DEFAULT_GEOMETRY_CONFIG = config


# =============================================================================
# DEPLOYMENT TIER PRESETS
# =============================================================================

def get_config_for_tier(tier: str) -> GeometryConfig:
    """
    Get configuration preset for deployment tier.

    Tiers:
    - development: Relaxed limits for local development
    - staging: Moderate limits
    - production: Strict limits for production use
    - runpod: Optimized for RunPod serverless
    """
    if tier == "development":
        return GeometryConfig(
            resource_limits=ResourceLimits(
                max_memory_mb=512,
                max_lod_level=LODLevel.ULTRA,
                default_lod_level=LODLevel.HIGH,
                job_timeout_seconds=300,
            ),
            allow_visual_only_default=True,
        )

    elif tier == "staging":
        return GeometryConfig(
            resource_limits=ResourceLimits(
                max_memory_mb=256,
                max_lod_level=LODLevel.HIGH,
                default_lod_level=LODLevel.MEDIUM,
                job_timeout_seconds=60,
            ),
        )

    elif tier == "production":
        return GeometryConfig(
            resource_limits=ResourceLimits(
                max_memory_mb=128,
                max_lod_level=LODLevel.HIGH,
                default_lod_level=LODLevel.MEDIUM,
                job_timeout_seconds=30,
                max_concurrent_jobs=8,
            ),
            allow_visual_only_default=False,
        )

    elif tier == "runpod":
        return GeometryConfig(
            resource_limits=ResourceLimits(
                max_memory_mb=2048,
                max_lod_level=LODLevel.ULTRA,
                default_lod_level=LODLevel.HIGH,
                job_timeout_seconds=120,
                max_concurrent_jobs=1,  # Single request per worker
            ),
            enable_geometry_cache=False,  # No cross-request caching
        )

    else:
        logger.warning(f"Unknown tier '{tier}', using default config")
        return GeometryConfig()
