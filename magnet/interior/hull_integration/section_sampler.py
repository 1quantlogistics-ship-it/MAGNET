"""
section_sampler.py - Hull section sampling utilities v1.1
BRAVO OWNS THIS FILE.

Module 59: Critical Architecture Fixes
Provides sampling utilities to extract hull cross-sections from hull parameters
for use in interior layout hull boundary calculations.

Integrates with M16-20 hull definition modules.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable, Dict, Any, TYPE_CHECKING
import math
import logging

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager

__all__ = [
    'SectionSampler',
    'SamplingConfig',
    'SampledSection',
    'HullFormType',
]

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class SamplingConfig:
    """Configuration for hull section sampling."""

    # Number of sections to sample along vessel length
    num_sections: int = 21

    # Number of points per half-breadth curve
    points_per_curve: int = 20

    # Sampling range (normalized 0.0 = AP, 1.0 = FP)
    x_start: float = 0.0
    x_end: float = 1.0

    # Include additional stations at key positions
    include_key_stations: bool = True

    # Key station positions (normalized)
    key_stations: List[float] = field(default_factory=lambda: [
        0.0,    # AP
        0.1,    # Aft quarter
        0.25,   # Quarter length aft
        0.5,    # Midship
        0.75,   # Quarter length fwd
        0.9,    # Fwd quarter
        1.0,    # FP
    ])

    # Deadrise angle interpolation
    deadrise_at_transom_deg: float = 15.0
    deadrise_at_midship_deg: float = 10.0
    deadrise_at_bow_deg: float = 25.0


# =============================================================================
# HULL FORM TYPES
# =============================================================================

class HullFormType:
    """Hull form type identifiers for section shape generation."""

    PLANING = "planing"
    SEMI_DISPLACEMENT = "semi_displacement"
    DISPLACEMENT = "displacement"
    ROUND_BILGE = "round_bilge"
    HARD_CHINE = "hard_chine"
    CATAMARAN = "catamaran"


# =============================================================================
# SAMPLED SECTION
# =============================================================================

@dataclass
class SampledSection:
    """
    A sampled hull cross-section at a specific longitudinal position.

    Stores half-breadth curve (y as function of z) for starboard side.
    Port side is symmetric (mirrored).
    """

    # Longitudinal position from AP (meters)
    x_position: float

    # Normalized position (0.0 = AP, 1.0 = FP)
    x_normalized: float

    # Half-breadth points: (z, y) tuples for starboard side
    # z = vertical position from baseline, y = half-breadth at that height
    half_breadth_points: List[Tuple[float, float]] = field(default_factory=list)

    # Section properties
    beam_at_waterline: float = 0.0
    beam_max: float = 0.0
    draft_at_section: float = 0.0
    depth_at_section: float = 0.0

    # Interpolation function (built from points)
    _interp_func: Optional[Callable[[float], float]] = field(
        default=None, repr=False
    )

    def __post_init__(self):
        """Build interpolator after initialization."""
        if self.half_breadth_points and len(self.half_breadth_points) >= 2:
            self._build_interpolator()

    def _build_interpolator(self) -> None:
        """Build interpolation function from half-breadth points."""
        try:
            from scipy import interpolate

            points = sorted(self.half_breadth_points, key=lambda p: p[0])
            z_vals = [p[0] for p in points]
            y_vals = [p[1] for p in points]

            self._interp_func = interpolate.interp1d(
                z_vals, y_vals,
                kind='linear',
                bounds_error=False,
                fill_value=(y_vals[0], y_vals[-1])
            )
        except ImportError:
            # Fallback to linear interpolation without scipy
            self._interp_func = self._linear_interp

    def _linear_interp(self, z: float) -> float:
        """Simple linear interpolation fallback."""
        if not self.half_breadth_points:
            return 0.0

        points = sorted(self.half_breadth_points, key=lambda p: p[0])

        if z <= points[0][0]:
            return points[0][1]
        if z >= points[-1][0]:
            return points[-1][1]

        for i in range(len(points) - 1):
            z0, y0 = points[i]
            z1, y1 = points[i + 1]
            if z0 <= z <= z1:
                t = (z - z0) / (z1 - z0) if z1 != z0 else 0.0
                return y0 + t * (y1 - y0)

        return points[-1][1]

    def half_breadth_at_z(self, z: float) -> float:
        """
        Get half-breadth (max Y) at given Z height.

        Args:
            z: Vertical position from baseline (meters)

        Returns:
            Half-breadth at that height (meters)
        """
        if self._interp_func is None:
            if self.half_breadth_points:
                return max(p[1] for p in self.half_breadth_points)
            return 0.0

        result = self._interp_func(z)
        return float(result) if hasattr(result, '__float__') else result

    def is_inside(self, y: float, z: float) -> bool:
        """
        Check if point is inside hull at this section.

        Args:
            y: Transverse position (meters, positive = starboard)
            z: Vertical position from baseline (meters)

        Returns:
            True if point is inside hull boundary
        """
        half_breadth = self.half_breadth_at_z(z)
        return abs(y) <= half_breadth

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "x_position": self.x_position,
            "x_normalized": self.x_normalized,
            "half_breadth_points": self.half_breadth_points,
            "beam_at_waterline": self.beam_at_waterline,
            "beam_max": self.beam_max,
            "draft_at_section": self.draft_at_section,
            "depth_at_section": self.depth_at_section,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SampledSection":
        """Deserialize from dictionary."""
        return cls(
            x_position=data.get("x_position", 0.0),
            x_normalized=data.get("x_normalized", 0.0),
            half_breadth_points=[tuple(p) for p in data.get("half_breadth_points", [])],
            beam_at_waterline=data.get("beam_at_waterline", 0.0),
            beam_max=data.get("beam_max", 0.0),
            draft_at_section=data.get("draft_at_section", 0.0),
            depth_at_section=data.get("depth_at_section", 0.0),
        )


# =============================================================================
# SECTION SAMPLER
# =============================================================================

class SectionSampler:
    """
    Samples hull cross-sections from hull parameters.

    Generates SampledSection objects at specified longitudinal positions
    based on hull form coefficients and principal dimensions.
    """

    def __init__(self, config: Optional[SamplingConfig] = None):
        """
        Initialize section sampler.

        Args:
            config: Sampling configuration (uses defaults if None)
        """
        self.config = config or SamplingConfig()
        self._cache: Dict[str, List[SampledSection]] = {}

    def sample_from_state(
        self,
        state_manager: "StateManager",
        cache_key: Optional[str] = None,
    ) -> List[SampledSection]:
        """
        Sample sections from StateManager hull data.

        Args:
            state_manager: MAGNET state manager with hull data
            cache_key: Optional key for caching results

        Returns:
            List of SampledSection objects
        """
        # Check cache
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        # Extract hull parameters
        hull_params = self._extract_hull_params(state_manager)

        # Generate sections
        sections = self.sample_from_params(hull_params)

        # Cache results
        if cache_key:
            self._cache[cache_key] = sections

        return sections

    def sample_from_params(
        self,
        params: Dict[str, Any],
    ) -> List[SampledSection]:
        """
        Sample sections from hull parameter dictionary.

        Args:
            params: Dictionary with hull parameters:
                - loa/lwl/lbp: Length (meters)
                - beam: Beam (meters)
                - draft: Draft (meters)
                - depth: Depth (meters)
                - cb: Block coefficient
                - hull_type: Hull form type
                - deadrise_deg: Deadrise angle (degrees)

        Returns:
            List of SampledSection objects
        """
        # Extract and validate parameters
        loa = params.get("loa", 25.0)
        lwl = params.get("lwl") or loa * 0.95
        beam = params.get("beam", 6.0)
        draft = params.get("draft", 1.5)
        depth = params.get("depth") or draft * 2.0
        cb = params.get("cb", 0.45)
        hull_type = params.get("hull_type", HullFormType.SEMI_DISPLACEMENT)
        deadrise = params.get("deadrise_deg", 15.0)
        transom_ratio = params.get("transom_width_ratio", 0.85)

        # Generate sampling positions
        positions = self._generate_positions()

        # Generate section at each position
        sections: List[SampledSection] = []

        for x_norm in positions:
            section = self._generate_section(
                x_normalized=x_norm,
                loa=loa,
                lwl=lwl,
                beam=beam,
                draft=draft,
                depth=depth,
                cb=cb,
                hull_type=hull_type,
                deadrise_deg=deadrise,
                transom_ratio=transom_ratio,
            )
            sections.append(section)

        # Sort by position
        sections.sort(key=lambda s: s.x_position)

        logger.debug(f"Generated {len(sections)} hull sections")
        return sections

    def _extract_hull_params(
        self,
        state_manager: "StateManager",
    ) -> Dict[str, Any]:
        """Extract hull parameters from state manager."""
        try:
            from magnet.ui.utils import get_state_value

            return {
                "loa": get_state_value(state_manager, "hull.loa", 25.0),
                "lwl": get_state_value(state_manager, "hull.lwl", None),
                "lbp": get_state_value(state_manager, "hull.lbp", None),
                "beam": get_state_value(state_manager, "hull.beam", 6.0),
                "draft": get_state_value(state_manager, "hull.draft", 1.5),
                "depth": get_state_value(state_manager, "hull.depth", 3.0),
                "cb": get_state_value(state_manager, "hull.cb", 0.45),
                "hull_type": get_state_value(
                    state_manager, "hull.hull_type", HullFormType.SEMI_DISPLACEMENT
                ),
                "deadrise_deg": get_state_value(
                    state_manager, "hull.deadrise_deg", 15.0
                ),
                "transom_width_ratio": get_state_value(
                    state_manager, "hull.transom_width_ratio", 0.85
                ),
            }
        except ImportError:
            logger.warning("Could not import ui.utils, using defaults")
            return {
                "loa": 25.0,
                "beam": 6.0,
                "draft": 1.5,
                "depth": 3.0,
                "cb": 0.45,
                "hull_type": HullFormType.SEMI_DISPLACEMENT,
                "deadrise_deg": 15.0,
                "transom_width_ratio": 0.85,
            }

    def _generate_positions(self) -> List[float]:
        """Generate normalized sampling positions."""
        positions = set()

        # Regular spacing
        for i in range(self.config.num_sections):
            t = i / max(1, self.config.num_sections - 1)
            x_norm = self.config.x_start + t * (self.config.x_end - self.config.x_start)
            positions.add(round(x_norm, 6))

        # Add key stations
        if self.config.include_key_stations:
            for station in self.config.key_stations:
                if self.config.x_start <= station <= self.config.x_end:
                    positions.add(round(station, 6))

        return sorted(positions)

    def _generate_section(
        self,
        x_normalized: float,
        loa: float,
        lwl: float,
        beam: float,
        draft: float,
        depth: float,
        cb: float,
        hull_type: str,
        deadrise_deg: float,
        transom_ratio: float,
    ) -> SampledSection:
        """
        Generate a single section at the specified position.

        Uses parametric hull form model based on hull type and coefficients.
        """
        x_position = x_normalized * loa
        half_beam = beam / 2.0

        # Calculate local section properties based on position
        # Entry/run shaping
        if x_normalized < 0.1:
            # Aft (transom) region
            local_width_factor = transom_ratio
            local_deadrise = deadrise_deg
        elif x_normalized > 0.85:
            # Forward (bow) region - narrowing entry
            bow_factor = (x_normalized - 0.85) / 0.15
            local_width_factor = 1.0 - 0.6 * bow_factor  # Narrows to 40% at FP
            local_deadrise = deadrise_deg + 10.0 * bow_factor
        else:
            # Parallel midbody
            mid_factor = 1.0 - abs(x_normalized - 0.5) * 0.1
            local_width_factor = mid_factor
            local_deadrise = deadrise_deg * 0.7  # Less deadrise at midship

        local_half_beam = half_beam * local_width_factor

        # Generate half-breadth curve based on hull type
        if hull_type == HullFormType.HARD_CHINE:
            points = self._hard_chine_curve(
                local_half_beam, draft, depth, local_deadrise
            )
        elif hull_type == HullFormType.ROUND_BILGE:
            points = self._round_bilge_curve(
                local_half_beam, draft, depth, local_deadrise
            )
        elif hull_type == HullFormType.PLANING:
            points = self._planing_curve(
                local_half_beam, draft, depth, local_deadrise
            )
        else:
            # Semi-displacement default
            points = self._semi_displacement_curve(
                local_half_beam, draft, depth, local_deadrise, cb
            )

        # Calculate section properties
        beam_at_wl = 2.0 * self._interp_half_breadth(points, draft)
        beam_max = 2.0 * max(p[1] for p in points) if points else 0.0

        return SampledSection(
            x_position=x_position,
            x_normalized=x_normalized,
            half_breadth_points=points,
            beam_at_waterline=beam_at_wl,
            beam_max=beam_max,
            draft_at_section=draft,
            depth_at_section=depth,
        )

    def _hard_chine_curve(
        self,
        half_beam: float,
        draft: float,
        depth: float,
        deadrise_deg: float,
    ) -> List[Tuple[float, float]]:
        """Generate hard chine section curve."""
        deadrise_rad = math.radians(deadrise_deg)

        # Keel point
        keel_y = 0.0

        # Chine point
        chine_z = draft * 0.4
        chine_y = half_beam * 0.95

        # Sheer point
        sheer_z = depth
        sheer_y = half_beam

        points = [
            (0.0, keel_y),
            (chine_z, chine_y),
            (draft, half_beam),
            (sheer_z, sheer_y),
        ]

        return points

    def _round_bilge_curve(
        self,
        half_beam: float,
        draft: float,
        depth: float,
        deadrise_deg: float,
    ) -> List[Tuple[float, float]]:
        """Generate round bilge section curve."""
        num_points = self.config.points_per_curve
        points = []

        bilge_radius = min(half_beam, draft) * 0.3

        for i in range(num_points):
            t = i / (num_points - 1)
            z = t * depth

            if z < bilge_radius:
                # Keel to bilge - curved transition
                angle = math.acos(1 - z / bilge_radius) if bilge_radius > 0 else 0
                y = bilge_radius * math.sin(angle)
            elif z < draft:
                # Bilge to waterline
                t_local = (z - bilge_radius) / (draft - bilge_radius)
                y = bilge_radius + t_local * (half_beam - bilge_radius)
            else:
                # Above waterline
                t_local = (z - draft) / (depth - draft) if depth > draft else 0
                y = half_beam * (1.0 + 0.02 * t_local)  # Slight flare

            points.append((z, y))

        return points

    def _planing_curve(
        self,
        half_beam: float,
        draft: float,
        depth: float,
        deadrise_deg: float,
    ) -> List[Tuple[float, float]]:
        """Generate planing hull section curve with deadrise."""
        deadrise_rad = math.radians(deadrise_deg)
        num_points = self.config.points_per_curve
        points = []

        # Planing hulls have flat bottom with deadrise, then hard chine
        chine_z = draft * 0.5

        for i in range(num_points):
            t = i / (num_points - 1)
            z = t * depth

            if z < chine_z:
                # Below chine - deadrise panel
                y = z / math.tan(deadrise_rad) if deadrise_rad > 0.01 else half_beam
                y = min(y, half_beam)
            else:
                # Above chine - straight side
                y = half_beam

            points.append((z, y))

        return points

    def _semi_displacement_curve(
        self,
        half_beam: float,
        draft: float,
        depth: float,
        deadrise_deg: float,
        cb: float,
    ) -> List[Tuple[float, float]]:
        """Generate semi-displacement section curve."""
        num_points = self.config.points_per_curve
        points = []

        # Blend between round and hard chine based on Cb
        # Lower Cb = more round, higher Cb = more boxy
        fullness = min(1.0, cb * 1.5)

        deadrise_rad = math.radians(deadrise_deg)
        bilge_radius = min(half_beam, draft) * (0.4 - 0.2 * fullness)

        for i in range(num_points):
            t = i / (num_points - 1)
            z = t * depth

            if z < draft * 0.2:
                # Bottom with deadrise
                base_y = z / math.tan(deadrise_rad) if deadrise_rad > 0.01 else 0
                y = min(base_y, half_beam * fullness)
            elif z < draft * 0.6:
                # Transition to bilge
                t_local = (z - draft * 0.2) / (draft * 0.4)
                start_y = min(
                    draft * 0.2 / math.tan(deadrise_rad) if deadrise_rad > 0.01 else 0,
                    half_beam * fullness
                )
                end_y = half_beam * (0.8 + 0.2 * fullness)
                y = start_y + t_local * (end_y - start_y)
            elif z < draft:
                # Bilge to waterline
                t_local = (z - draft * 0.6) / (draft * 0.4)
                y = half_beam * (0.8 + 0.2 * fullness) + t_local * half_beam * 0.2
            else:
                # Above waterline with slight flare
                t_local = (z - draft) / (depth - draft) if depth > draft else 0
                y = half_beam * (1.0 + 0.03 * t_local * (1.0 - fullness))

            points.append((z, min(y, half_beam * 1.05)))

        return points

    def _interp_half_breadth(
        self,
        points: List[Tuple[float, float]],
        z: float,
    ) -> float:
        """Linear interpolation of half-breadth at height z."""
        if not points:
            return 0.0

        sorted_points = sorted(points, key=lambda p: p[0])

        if z <= sorted_points[0][0]:
            return sorted_points[0][1]
        if z >= sorted_points[-1][0]:
            return sorted_points[-1][1]

        for i in range(len(sorted_points) - 1):
            z0, y0 = sorted_points[i]
            z1, y1 = sorted_points[i + 1]
            if z0 <= z <= z1:
                t = (z - z0) / (z1 - z0) if z1 != z0 else 0.0
                return y0 + t * (y1 - y0)

        return sorted_points[-1][1]

    def clear_cache(self) -> None:
        """Clear section cache."""
        self._cache.clear()

    def get_cached_keys(self) -> List[str]:
        """Get list of cached design keys."""
        return list(self._cache.keys())
