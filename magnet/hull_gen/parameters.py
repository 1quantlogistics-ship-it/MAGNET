"""
hull_gen/parameters.py - Parametric hull definition data structures.

BRAVO OWNS THIS FILE.

Module 16 v1.0 - Parametric hull definition.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MainDimensions:
    """
    Principal hull dimensions.

    All dimensions in meters.
    """

    # === LENGTH ===
    loa: float = 0.0
    """Length overall (m)."""

    lwl: float = 0.0
    """Length on waterline (m)."""

    lpp: float = 0.0
    """Length between perpendiculars (m)."""

    # === BEAM ===
    beam_max: float = 0.0
    """Maximum beam (m)."""

    beam_wl: float = 0.0
    """Beam at waterline (m)."""

    beam_chine: float = 0.0
    """Beam at chine (m) - for chine hulls."""

    # === DEPTH & DRAFT ===
    depth: float = 0.0
    """Moulded depth (m)."""

    draft: float = 0.0
    """Design draft (m)."""

    draft_fwd: float = 0.0
    """Draft at forward perpendicular (m)."""

    draft_aft: float = 0.0
    """Draft at aft perpendicular (m)."""

    # === FREEBOARD ===
    freeboard_bow: float = 0.0
    """Freeboard at bow (m)."""

    freeboard_mid: float = 0.0
    """Freeboard amidships (m)."""

    freeboard_stern: float = 0.0
    """Freeboard at stern (m)."""

    def validate(self) -> List[str]:
        """Validate dimensions for consistency."""
        errors = []

        if self.lwl <= 0:
            errors.append("LWL must be positive")
        if self.loa < self.lwl:
            errors.append("LOA must be >= LWL")
        if self.beam_max <= 0:
            errors.append("Beam must be positive")
        if self.draft <= 0:
            errors.append("Draft must be positive")
        if self.depth < self.draft:
            errors.append("Depth must be >= Draft")

        # Ratio checks
        lb_ratio = self.lwl / self.beam_max if self.beam_max > 0 else 0
        if lb_ratio < 2.0 or lb_ratio > 10.0:
            errors.append(f"L/B ratio {lb_ratio:.2f} outside typical range [2-10]")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "loa": round(self.loa, 3),
            "lwl": round(self.lwl, 3),
            "lpp": round(self.lpp, 3),
            "beam_max": round(self.beam_max, 3),
            "beam_wl": round(self.beam_wl, 3),
            "beam_chine": round(self.beam_chine, 3),
            "depth": round(self.depth, 3),
            "draft": round(self.draft, 3),
            "draft_fwd": round(self.draft_fwd, 3),
            "draft_aft": round(self.draft_aft, 3),
            "freeboard_bow": round(self.freeboard_bow, 3),
            "freeboard_mid": round(self.freeboard_mid, 3),
            "freeboard_stern": round(self.freeboard_stern, 3),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MainDimensions':
        """Create from dictionary."""
        return cls(
            loa=data.get("loa", 0.0),
            lwl=data.get("lwl", 0.0),
            lpp=data.get("lpp", 0.0),
            beam_max=data.get("beam_max", 0.0),
            beam_wl=data.get("beam_wl", 0.0),
            beam_chine=data.get("beam_chine", 0.0),
            depth=data.get("depth", 0.0),
            draft=data.get("draft", 0.0),
            draft_fwd=data.get("draft_fwd", 0.0),
            draft_aft=data.get("draft_aft", 0.0),
            freeboard_bow=data.get("freeboard_bow", 0.0),
            freeboard_mid=data.get("freeboard_mid", 0.0),
            freeboard_stern=data.get("freeboard_stern", 0.0),
        )


@dataclass
class FormCoefficients:
    """
    Hull form coefficients.

    Non-dimensional parameters defining hull fullness.
    """

    # === PRIMARY COEFFICIENTS ===
    cb: float = 0.0
    """Block coefficient (nabla / L×B×T)."""

    cp: float = 0.0
    """Prismatic coefficient (nabla / Am×L)."""

    cm: float = 0.0
    """Midship section coefficient (Am / B×T)."""

    cwp: float = 0.0
    """Waterplane coefficient (Awp / L×B)."""

    # === VERTICAL COEFFICIENTS ===
    cvp: float = 0.0
    """Vertical prismatic coefficient."""

    # === CENTER POSITIONS (as fraction of L from AP) ===
    lcb: float = 0.5
    """Longitudinal center of buoyancy (fraction of LWL from AP)."""

    lcf: float = 0.5
    """Longitudinal center of flotation (fraction of LWL from AP)."""

    def validate(self) -> List[str]:
        """Validate coefficient ranges."""
        errors = []

        if not 0.2 <= self.cb <= 0.9:
            errors.append(f"Cb {self.cb:.3f} outside range [0.2-0.9]")
        if not 0.4 <= self.cp <= 0.9:
            errors.append(f"Cp {self.cp:.3f} outside range [0.4-0.9]")
        if not 0.5 <= self.cm <= 1.0:
            errors.append(f"Cm {self.cm:.3f} outside range [0.5-1.0]")
        if not 0.5 <= self.cwp <= 1.0:
            errors.append(f"Cwp {self.cwp:.3f} outside range [0.5-1.0]")

        # Consistency check: Cb = Cp × Cm
        cb_check = self.cp * self.cm
        if abs(self.cb - cb_check) > 0.05:
            errors.append(f"Cb ({self.cb:.3f}) inconsistent with Cp×Cm ({cb_check:.3f})")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cb": round(self.cb, 4),
            "cp": round(self.cp, 4),
            "cm": round(self.cm, 4),
            "cwp": round(self.cwp, 4),
            "cvp": round(self.cvp, 4),
            "lcb": round(self.lcb, 4),
            "lcf": round(self.lcf, 4),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormCoefficients':
        """Create from dictionary."""
        return cls(
            cb=data.get("cb", 0.0),
            cp=data.get("cp", 0.0),
            cm=data.get("cm", 0.0),
            cwp=data.get("cwp", 0.0),
            cvp=data.get("cvp", 0.0),
            lcb=data.get("lcb", 0.5),
            lcf=data.get("lcf", 0.5),
        )


@dataclass
class ChineConfig:
    """
    Configuration for a single chine line.
    
    Phase 2: Supports multi-chine, reverse chine, and variable chine hulls.
    """
    
    height_ratio: float = 0.3
    """Height as fraction of draft (0=keel, 1=waterline)."""
    
    angle_deg: float = 45.0
    """Chine angle in degrees (positive=standard, negative=reverse)."""
    
    is_hard: bool = True
    """Whether this is a hard edge (True) or soft/rounded (False)."""
    
    flat_width_m: float = 0.0
    """Horizontal flat width at chine (m), 0 for no flat."""
    
    start_station: float = 0.0
    """Station where chine starts (0=stern, 1=bow)."""
    
    end_station: float = 1.0
    """Station where chine ends (0=stern, 1=bow)."""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "height_ratio": round(self.height_ratio, 3),
            "angle_deg": round(self.angle_deg, 1),
            "is_hard": self.is_hard,
            "flat_width_m": round(self.flat_width_m, 4),
            "start_station": round(self.start_station, 3),
            "end_station": round(self.end_station, 3),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChineConfig':
        """Create from dictionary."""
        return cls(
            height_ratio=data.get("height_ratio", 0.3),
            angle_deg=data.get("angle_deg", 45.0),
            is_hard=data.get("is_hard", True),
            flat_width_m=data.get("flat_width_m", 0.0),
            start_station=data.get("start_station", 0.0),
            end_station=data.get("end_station", 1.0),
        )


@dataclass
class SprayRailConfig:
    """
    Configuration for a single spray rail with full geometric control.
    
    Phase 4 Enhanced: Supports variable width, angle, and height along length,
    plus multiple cross-section shapes. All parameters can be constant or
    specified as profiles for full parametric control.
    
    Cross-section shapes:
    - triangular: Sharp V shape (default, best spray deflection)
    - rounded: Rounded profile (softer appearance)
    - flat_top: Flat deflector surface (maximum lift)
    - sharp: Knife-edge (minimal drag)
    """
    
    # === VERTICAL POSITION ===
    height_ratio: float = 0.25
    """Height as fraction of draft (0=keel, 1=waterline)."""
    
    height_profile: Optional[List[Tuple[float, float]]] = None
    """Variable height: [(station, height_ratio), ...] for height that changes along length."""
    
    # === LONGITUDINAL EXTENT ===
    start_station: float = 0.15
    """Where rail begins (fraction of LWL, 0=stern, 1=bow)."""
    
    end_station: float = 0.95
    """Where rail ends (fraction of LWL)."""
    
    # === CROSS-SECTION SHAPE ===
    profile: str = "triangular"
    """Cross-section shape: 'triangular' | 'rounded' | 'flat_top' | 'sharp'."""
    
    # === WIDTH (projection from hull) ===
    width_m: float = 0.05
    """Constant width (used if no variable width specified)."""
    
    width_profile: Optional[List[Tuple[float, float]]] = None
    """Full variable width: [(station, width_m), ...] for custom profile."""
    
    width_at_start_m: Optional[float] = None
    """Width at start (for simple 3-point taper)."""
    
    width_at_mid_m: Optional[float] = None
    """Width at midpoint (for simple 3-point taper)."""
    
    width_at_end_m: Optional[float] = None
    """Width at end (for simple 3-point taper)."""
    
    # === ANGLE (deflection from hull surface) ===
    angle_deg: float = 15.0
    """Constant angle (used if no variable angle specified)."""
    
    angle_profile: Optional[List[Tuple[float, float]]] = None
    """Full variable angle: [(station, angle_deg), ...] for custom profile."""
    
    angle_at_start_deg: Optional[float] = None
    """Angle at start (for simple linear interpolation)."""
    
    angle_at_end_deg: Optional[float] = None
    """Angle at end (for simple linear interpolation)."""
    
    # === TAPER CONTROL ===
    taper_start_length: float = 0.1
    """Fraction of rail length for start taper (0-0.5)."""
    
    taper_end_length: float = 0.1
    """Fraction of rail length for end taper (0-0.5)."""
    
    taper_style: str = "linear"
    """Taper interpolation: 'linear' | 'smooth' | 'none'."""
    
    # === EDGE HARDNESS ===
    is_hard: bool = True
    """Whether this is a hard edge (always true for spray rails)."""
    
    def is_active_at_station(self, station: float) -> bool:
        """Check if rail is active at given station."""
        return self.start_station <= station <= self.end_station
    
    def get_width_at_station(self, station: float) -> float:
        """Get rail width at given station, interpolating as needed."""
        if not self.is_active_at_station(station):
            return 0.0
        
        # Normalize station to rail-local coordinate (0=start, 1=end)
        rail_length = self.end_station - self.start_station
        if rail_length <= 0:
            return self.width_m
        rail_t = (station - self.start_station) / rail_length
        
        # Use explicit profile if provided
        if self.width_profile:
            return self._interpolate_profile(self.width_profile, station)
        
        # Use start/mid/end overrides for simple variable width
        if self.width_at_start_m is not None or self.width_at_end_m is not None or self.width_at_mid_m is not None:
            return self._interpolate_three_point(
                rail_t,
                self.width_at_start_m if self.width_at_start_m is not None else self.width_m * 0.3,
                self.width_at_mid_m if self.width_at_mid_m is not None else self.width_m,
                self.width_at_end_m if self.width_at_end_m is not None else self.width_m * 0.5,
            )
        
        # Apply taper to constant width
        taper = self._calculate_taper(rail_t)
        return self.width_m * taper
    
    def get_angle_at_station(self, station: float) -> float:
        """Get rail angle at given station, interpolating as needed."""
        if not self.is_active_at_station(station):
            return 0.0
        
        rail_length = self.end_station - self.start_station
        if rail_length <= 0:
            return self.angle_deg
        rail_t = (station - self.start_station) / rail_length
        
        # Use explicit profile if provided
        if self.angle_profile:
            return self._interpolate_profile(self.angle_profile, station)
        
        # Use start/end overrides for linear interpolation
        if self.angle_at_start_deg is not None or self.angle_at_end_deg is not None:
            start_angle = self.angle_at_start_deg if self.angle_at_start_deg is not None else self.angle_deg
            end_angle = self.angle_at_end_deg if self.angle_at_end_deg is not None else self.angle_deg
            return start_angle + rail_t * (end_angle - start_angle)
        
        return self.angle_deg
    
    def get_height_at_station(self, station: float) -> float:
        """Get rail height ratio at given station."""
        if self.height_profile:
            return self._interpolate_profile(self.height_profile, station)
        return self.height_ratio
    
    def _calculate_taper(self, rail_t: float) -> float:
        """Calculate taper multiplier at rail-local position (0=start, 1=end)."""
        if self.taper_style == "none":
            return 1.0
        
        # Taper in at start
        if rail_t < self.taper_start_length and self.taper_start_length > 0:
            t = rail_t / self.taper_start_length
            return t if self.taper_style == "linear" else self._smooth_step(t)
        
        # Taper out at end
        if rail_t > (1 - self.taper_end_length) and self.taper_end_length > 0:
            t = (1 - rail_t) / self.taper_end_length
            return t if self.taper_style == "linear" else self._smooth_step(t)
        
        return 1.0
    
    def _interpolate_three_point(self, t: float, start: float, mid: float, end: float) -> float:
        """Interpolate through start, mid, end using quadratic Bezier."""
        # Quadratic Bezier: B(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
        return (1-t)**2 * start + 2*(1-t)*t * mid + t**2 * end
    
    def _interpolate_profile(self, profile: List[Tuple[float, float]], station: float) -> float:
        """Interpolate value from station-value profile."""
        if not profile:
            return 0.0
        
        # Sort by station
        sorted_profile = sorted(profile, key=lambda x: x[0])
        
        # Find bracketing points
        for i in range(len(sorted_profile) - 1):
            s0, v0 = sorted_profile[i]
            s1, v1 = sorted_profile[i + 1]
            if s0 <= station <= s1:
                t = (station - s0) / (s1 - s0) if s1 != s0 else 0
                return v0 + t * (v1 - v0)
        
        # Extrapolate from nearest end
        if station < sorted_profile[0][0]:
            return sorted_profile[0][1]
        return sorted_profile[-1][1]
    
    def _smooth_step(self, t: float) -> float:
        """Smooth step function (Hermite interpolation)."""
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "height_ratio": round(self.height_ratio, 3),
            "height_profile": self.height_profile,
            "start_station": round(self.start_station, 3),
            "end_station": round(self.end_station, 3),
            "profile": self.profile,
            "width_m": round(self.width_m, 4),
            "width_profile": self.width_profile,
            "width_at_start_m": self.width_at_start_m,
            "width_at_mid_m": self.width_at_mid_m,
            "width_at_end_m": self.width_at_end_m,
            "angle_deg": round(self.angle_deg, 1),
            "angle_profile": self.angle_profile,
            "angle_at_start_deg": self.angle_at_start_deg,
            "angle_at_end_deg": self.angle_at_end_deg,
            "taper_start_length": round(self.taper_start_length, 3),
            "taper_end_length": round(self.taper_end_length, 3),
            "taper_style": self.taper_style,
            "is_hard": self.is_hard,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SprayRailConfig':
        """Create from dictionary."""
        return cls(
            height_ratio=data.get("height_ratio", 0.25),
            height_profile=data.get("height_profile"),
            start_station=data.get("start_station", 0.15),
            end_station=data.get("end_station", 0.95),
            profile=data.get("profile", "triangular"),
            width_m=data.get("width_m", 0.05),
            width_profile=data.get("width_profile"),
            width_at_start_m=data.get("width_at_start_m"),
            width_at_mid_m=data.get("width_at_mid_m"),
            width_at_end_m=data.get("width_at_end_m"),
            angle_deg=data.get("angle_deg", 15.0),
            angle_profile=data.get("angle_profile"),
            angle_at_start_deg=data.get("angle_at_start_deg"),
            angle_at_end_deg=data.get("angle_at_end_deg"),
            taper_start_length=data.get("taper_start_length", 0.1),
            taper_end_length=data.get("taper_end_length", 0.1),
            taper_style=data.get("taper_style", "linear"),
            is_hard=data.get("is_hard", True),
        )


@dataclass
class KnuckleLineConfig:
    """
    Configuration for a knuckle line (hard longitudinal edge).
    
    Phase 4: Knuckle lines are hard longitudinal edges where the hull
    surface changes direction abruptly (unlike spray rails, they don't
    project outward - they're just a change in surface angle).
    """
    
    height_ratio: float = 0.7
    """Height as fraction of depth (0=keel level, 1=deck level)."""
    
    angle_deg: float = 5.0
    """Outward angle change at knuckle."""
    
    start_station: float = 0.0
    """Where knuckle begins (fraction of LWL)."""
    
    end_station: float = 1.0
    """Where knuckle ends (fraction of LWL)."""
    
    is_hard: bool = True
    """Whether this is a hard edge (True) or soft/rounded (False)."""
    
    def is_active_at_station(self, station: float) -> bool:
        """Check if knuckle is active at given station."""
        return self.start_station <= station <= self.end_station
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "height_ratio": round(self.height_ratio, 3),
            "angle_deg": round(self.angle_deg, 1),
            "start_station": round(self.start_station, 3),
            "end_station": round(self.end_station, 3),
            "is_hard": self.is_hard,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnuckleLineConfig':
        """Create from dictionary."""
        return cls(
            height_ratio=data.get("height_ratio", 0.7),
            angle_deg=data.get("angle_deg", 5.0),
            start_station=data.get("start_station", 0.0),
            end_station=data.get("end_station", 1.0),
            is_hard=data.get("is_hard", True),
        )


@dataclass
class BowConfig:
    """
    Configuration for bow form generation.
    
    Phase 3: Added for angular/faceted bow forms.
    """
    
    # Faceted bow parameters
    facet_count: int = 0
    """Panels per side. 0 => smooth/lofted bow (no planar facets)."""
    
    planarity: float = 0.0
    """0=smooth blend, 1=sharp planar edges (only meaningful when facet_count>=1)."""
    
    # Entry angle
    half_angle_deg: float = 25.0
    """Half-angle of bow entry (narrower = sharper)."""
    
    # Stem configuration
    stem_rake_deg: float = 15.0
    """Degrees from vertical (positive = aft rake, negative = forward)."""
    
    stem_curvature: float = 0.0
    """-1..+1 curvature shaping along the stem (continuous)."""
    
    stem_bulb_volume_m3: float = 0.0
    """0 => no bulb. Continuous bulb volume control."""
    
    stem_bulb_position: float = 0.0
    """Relative vertical position of bulb vs WL (m). Negative => below WL."""
    
    stem_radius_m: float = 0.0
    """Rounding radius at stem edge (0 = sharp)."""
    
    # Region extent
    region_length: float = 0.20
    """Fraction of LWL that is 'bow region'."""
    
    # Above-waterline shaping
    flare_deg: float = 10.0
    """Flare angle at bow (negative = tumblehome)."""
    
    freeboard_ratio: float = 1.2
    """Bow freeboard / midship freeboard."""
    
    def is_angular(self) -> bool:
        """Check if bow config requests planar facets/hard edges."""
        return float(self.planarity or 0.0) > 0.5 and int(self.facet_count or 0) >= 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "facet_count": self.facet_count,
            "planarity": round(self.planarity, 2),
            "half_angle_deg": round(self.half_angle_deg, 1),
            "stem_rake_deg": round(self.stem_rake_deg, 1),
            "stem_curvature": round(self.stem_curvature, 3),
            "stem_bulb_volume_m3": round(self.stem_bulb_volume_m3, 6),
            "stem_bulb_position": round(self.stem_bulb_position, 3),
            "stem_radius_m": round(self.stem_radius_m, 3),
            "region_length": round(self.region_length, 2),
            "flare_deg": round(self.flare_deg, 1),
            "freeboard_ratio": round(self.freeboard_ratio, 2),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BowConfig':
        """Create from dictionary."""
        return cls(
            facet_count=data.get("facet_count", 0),
            planarity=data.get("planarity", 0.0),
            half_angle_deg=data.get("half_angle_deg", 25.0),
            stem_rake_deg=data.get("stem_rake_deg", 15.0),
            stem_curvature=data.get("stem_curvature", 0.0),
            stem_bulb_volume_m3=data.get("stem_bulb_volume_m3", 0.0),
            stem_bulb_position=data.get("stem_bulb_position", 0.0),
            stem_radius_m=data.get("stem_radius_m", 0.0),
            region_length=data.get("region_length", 0.20),
            flare_deg=data.get("flare_deg", 10.0),
            freeboard_ratio=data.get("freeboard_ratio", 1.2),
        )


@dataclass(frozen=True)
class KeelAttachment:
    """
    Keel as an attachment (enum-free).

    NOTE: This is a lightweight param stub. The true geometry lives as a
    `geometry.body` resource in DesignState and is attached via DSL/operators.
    """

    body_id: str
    station_start: float = 0.0
    station_end: float = 1.0
    depth_m: float = 0.0
    width_m: float = 0.0


@dataclass(frozen=True)
class SternConfig:
    """Stern configuration (all continuous; no profile enums)."""

    transom_width_ratio: float = 0.85
    transom_height_ratio: float = 0.8
    transom_immersion_m: float = 0.0  # negative => dry
    transom_rake_deg: float = 12.0
    run_angle_deg: float = 15.0
    tunnel_count: int = 0
    tunnel_width_m: float = 0.0
    tunnel_depth_m: float = 0.0


# =============================================================================
# PHASE 5: TRANSOM CONFIGURATION
# =============================================================================

@dataclass
class TransomEdgeConfig:
    """Configuration for an edge (top, bottom, sides of transom)."""
    
    type: str = "hard"
    """Edge type: 'hard' | 'soft' | 'rounded' | 'chamfered' | 'bullnose'."""
    
    radius_m: float = 0.0
    """Radius for rounded/bullnose edges (m)."""
    
    chamfer_m: float = 0.0
    """Chamfer size for chamfered edges (m)."""
    
    angle_deg: float = 45.0
    """Chamfer angle (degrees)."""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "radius_m": round(self.radius_m, 4),
            "chamfer_m": round(self.chamfer_m, 4),
            "angle_deg": round(self.angle_deg, 1),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransomEdgeConfig':
        return cls(
            type=data.get("type", "hard"),
            radius_m=data.get("radius_m", 0.0),
            chamfer_m=data.get("chamfer_m", 0.0),
            angle_deg=data.get("angle_deg", 45.0),
        )


@dataclass
class TransomSegment:
    """
    A vertical segment of the transom (for stepped/complex profiles).
    
    Phase 5: Enables stepped transoms where different vertical regions
    have different rake angles or offsets.
    """
    
    height_start: float
    """Start height as fraction (0=keel, 1=deck)."""
    
    height_end: float
    """End height as fraction."""
    
    rake_deg: float = 12.0
    """Rake angle for this segment (degrees from vertical)."""
    
    offset_aft_m: float = 0.0
    """Offset aft from base transom plane (m)."""
    
    offset_outboard_m: float = 0.0
    """Offset outboard (for flared segments) (m)."""
    
    curvature: float = 0.0
    """Athwartships curvature (0=flat, +convex, -concave)."""
    
    edge_type: str = "hard"
    """Edge between segments: 'hard' | 'soft' | 'rounded'."""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "height_start": round(self.height_start, 3),
            "height_end": round(self.height_end, 3),
            "rake_deg": round(self.rake_deg, 1),
            "offset_aft_m": round(self.offset_aft_m, 4),
            "offset_outboard_m": round(self.offset_outboard_m, 4),
            "curvature": round(self.curvature, 3),
            "edge_type": self.edge_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransomSegment':
        return cls(
            height_start=data.get("height_start", 0.0),
            height_end=data.get("height_end", 1.0),
            rake_deg=data.get("rake_deg", 12.0),
            offset_aft_m=data.get("offset_aft_m", 0.0),
            offset_outboard_m=data.get("offset_outboard_m", 0.0),
            curvature=data.get("curvature", 0.0),
            edge_type=data.get("edge_type", "hard"),
        )


@dataclass
class TransomCutout:
    """
    A cutout in the transom (tunnel, notch, window, etc.).
    
    Phase 5: Enables jet tunnels, outboard wells, or decorative cutouts.
    """
    
    shape: str = "rectangular"
    """Cutout shape: 'rectangular' | 'semicircle' | 'ellipse' | 'custom'."""
    
    # Position (relative to transom)
    center_y_ratio: float = 0.0
    """Y position as fraction of half-beam (-1 to 1, 0=centerline)."""
    
    height_start_ratio: float = 0.0
    """Bottom of cutout as fraction of transom height."""
    
    height_end_ratio: float = 0.5
    """Top of cutout as fraction of transom height."""
    
    # Dimensions
    width_m: float = 0.5
    """Cutout width (m)."""
    
    height_m: float = 0.4
    """Cutout height (m)."""
    
    depth_m: float = 0.8
    """How far forward the cutout extends (0=surface notch) (m)."""
    
    # Shape refinement
    corner_radius_m: float = 0.0
    """Corner radius for rectangular cutouts (m)."""
    
    draft_angle_deg: float = 0.0
    """Taper of cutout walls (degrees)."""
    
    # Custom shape (if shape='custom')
    custom_profile: Optional[List[Tuple[float, float]]] = None
    """Custom outline: [(y, z), ...] points defining cutout shape."""
    
    # Edge treatment
    edge_type: str = "hard"
    """Edge type: 'hard' | 'soft' | 'filleted'."""
    
    fillet_radius_m: float = 0.0
    """Fillet radius for filleted edges (m)."""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shape": self.shape,
            "center_y_ratio": round(self.center_y_ratio, 3),
            "height_start_ratio": round(self.height_start_ratio, 3),
            "height_end_ratio": round(self.height_end_ratio, 3),
            "width_m": round(self.width_m, 4),
            "height_m": round(self.height_m, 4),
            "depth_m": round(self.depth_m, 4),
            "corner_radius_m": round(self.corner_radius_m, 4),
            "draft_angle_deg": round(self.draft_angle_deg, 1),
            "custom_profile": self.custom_profile,
            "edge_type": self.edge_type,
            "fillet_radius_m": round(self.fillet_radius_m, 4),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransomCutout':
        return cls(
            shape=data.get("shape", "rectangular"),
            center_y_ratio=data.get("center_y_ratio", 0.0),
            height_start_ratio=data.get("height_start_ratio", 0.0),
            height_end_ratio=data.get("height_end_ratio", 0.5),
            width_m=data.get("width_m", 0.5),
            height_m=data.get("height_m", 0.4),
            depth_m=data.get("depth_m", 0.8),
            corner_radius_m=data.get("corner_radius_m", 0.0),
            draft_angle_deg=data.get("draft_angle_deg", 0.0),
            custom_profile=data.get("custom_profile"),
            edge_type=data.get("edge_type", "hard"),
            fillet_radius_m=data.get("fillet_radius_m", 0.0),
        )


@dataclass
class TransomExtension:
    """
    An extension from the transom (platform, step, bracket, etc.).
    
    Phase 5: Enables swim platforms, boarding steps, engine brackets.
    """
    
    type: str = "platform"
    """Extension type: 'platform' | 'step' | 'bracket' | 'swim_platform' | 'custom'."""
    
    # Vertical extent
    height_start: float = 0.0
    """Start height as fraction of transom height."""
    
    height_end: float = 0.5
    """End height as fraction of transom height."""
    
    # Horizontal extent
    depth_m: float = 1.0
    """How far aft the extension projects (m)."""
    
    width_ratio: float = 0.8
    """Width as fraction of transom width at that height."""
    
    # Shape
    curvature: float = 0.0
    """Athwartships curvature (0=flat, +convex, -concave)."""
    
    slope_deg: float = 0.0
    """Fore-aft slope (degrees, 0=horizontal)."""
    
    # Edge treatment
    edge_radius_m: float = 0.05
    """Edge rounding radius (m)."""
    
    # Custom geometry
    custom_profile: Optional[List[Tuple[float, float, float]]] = None
    """Custom geometry: [(x, y, z), ...] points."""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "height_start": round(self.height_start, 3),
            "height_end": round(self.height_end, 3),
            "depth_m": round(self.depth_m, 4),
            "width_ratio": round(self.width_ratio, 3),
            "curvature": round(self.curvature, 3),
            "slope_deg": round(self.slope_deg, 1),
            "edge_radius_m": round(self.edge_radius_m, 4),
            "custom_profile": self.custom_profile,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransomExtension':
        return cls(
            type=data.get("type", "platform"),
            height_start=data.get("height_start", 0.0),
            height_end=data.get("height_end", 0.5),
            depth_m=data.get("depth_m", 1.0),
            width_ratio=data.get("width_ratio", 0.8),
            curvature=data.get("curvature", 0.0),
            slope_deg=data.get("slope_deg", 0.0),
            edge_radius_m=data.get("edge_radius_m", 0.05),
            custom_profile=data.get("custom_profile"),
        )


@dataclass
class TransomConfig:
    """
    Full parametric transom configuration.
    
    Phase 5: Presets provide starting points, but every parameter is
    individually overridable for custom designs. The philosophy is:
    enums are convenient presets, but the underlying system supports
    arbitrary configurations.
    
    Examples:
    - TransomConfig.from_preset("raked") → Standard raked transom
    - TransomConfig(rake_deg=14, corner_radius_m=0.3) → Custom
    - TransomConfig.from_preset("tunneled") → Twin jet tunnels
    """
    
    # === PRESET (optional starting point) ===
    preset: Optional[str] = None
    """Preset name if created from preset: 'vertical' | 'raked' | 'reverse_raked' |
       'stepped' | 'tunneled' | 'sugar_scoop' | 'notched' | None."""
    
    # === PROFILE (side view shape) ===
    rake_deg: float = 12.0
    """Angle from vertical (positive=aft rake, negative=forward) (degrees)."""
    
    rake_profile: Optional[List[Tuple[float, float]]] = None
    """Variable rake: [(height_ratio, rake_deg), ...] for curved profiles."""
    
    # Vertical segments (for stepped transoms)
    vertical_segments: List[TransomSegment] = field(default_factory=list)
    """Segments for stepped or complex transoms (overrides rake_deg)."""
    
    # === PLAN VIEW (top-down shape) ===
    beam_at_waterline_ratio: float = 1.0
    """Fraction of max beam at waterline."""
    
    beam_at_deck_ratio: float = 1.0
    """Fraction of max beam at deck."""
    
    beam_profile: Optional[List[Tuple[float, float]]] = None
    """Variable beam: [(height_ratio, beam_ratio), ...] for shaped transoms."""
    
    # Corner radius
    corner_radius_m: float = 0.0
    """Corner rounding (0=sharp corners) (m)."""
    
    corner_radius_profile: Optional[List[Tuple[float, float]]] = None
    """Variable corners: [(height_ratio, radius_m), ...]."""
    
    # === CURVATURE (athwartships) ===
    curvature: float = 0.0
    """Athwartships curvature: 0=flat, +convex, -concave."""
    
    curvature_profile: Optional[List[Tuple[float, float]]] = None
    """Variable curvature: [(height_ratio, curvature), ...]."""
    
    # === CUTOUTS (tunnels, notches, etc.) ===
    cutouts: List[TransomCutout] = field(default_factory=list)
    """Cutouts for tunnels, notches, or openings."""
    
    # === EXTENSIONS (platforms, steps, etc.) ===
    extensions: List[TransomExtension] = field(default_factory=list)
    """Extensions like swim platforms or engine brackets."""
    
    # === EDGE TREATMENT ===
    top_edge: TransomEdgeConfig = field(default_factory=TransomEdgeConfig)
    """Configuration for top edge."""
    
    bottom_edge: TransomEdgeConfig = field(default_factory=TransomEdgeConfig)
    """Configuration for bottom edge."""
    
    side_edges: TransomEdgeConfig = field(default_factory=TransomEdgeConfig)
    """Configuration for side edges."""
    
    # === INTEGRATION ===
    blend_to_hull_length_m: float = 0.5
    """How far forward transom shape blends into hull (m)."""
    
    # === HELPER METHODS ===
    
    def get_rake_at_height(self, height_ratio: float) -> float:
        """Get rake angle at given height, interpolating profiles if needed."""
        if self.vertical_segments:
            # Find segment containing this height
            for seg in self.vertical_segments:
                if seg.height_start <= height_ratio <= seg.height_end:
                    return seg.rake_deg
            # Default to last segment
            if self.vertical_segments:
                return self.vertical_segments[-1].rake_deg
        
        if self.rake_profile:
            return self._interpolate_profile(self.rake_profile, height_ratio)
        
        return self.rake_deg
    
    def get_beam_ratio_at_height(self, height_ratio: float) -> float:
        """Get beam ratio at given height."""
        if self.beam_profile:
            return self._interpolate_profile(self.beam_profile, height_ratio)
        
        # Linear interpolation between waterline and deck
        return self.beam_at_waterline_ratio + height_ratio * (
            self.beam_at_deck_ratio - self.beam_at_waterline_ratio
        )
    
    def get_curvature_at_height(self, height_ratio: float) -> float:
        """Get athwartships curvature at given height."""
        if self.curvature_profile:
            return self._interpolate_profile(self.curvature_profile, height_ratio)
        return self.curvature
    
    def get_corner_radius_at_height(self, height_ratio: float) -> float:
        """Get corner radius at given height."""
        if self.corner_radius_profile:
            return self._interpolate_profile(self.corner_radius_profile, height_ratio)
        return self.corner_radius_m
    
    def _interpolate_profile(
        self,
        profile: List[Tuple[float, float]],
        position: float,
    ) -> float:
        """Interpolate value from position-value profile."""
        if not profile:
            return 0.0
        
        sorted_profile = sorted(profile, key=lambda x: x[0])
        
        for i in range(len(sorted_profile) - 1):
            p0, v0 = sorted_profile[i]
            p1, v1 = sorted_profile[i + 1]
            if p0 <= position <= p1:
                t = (position - p0) / (p1 - p0) if p1 != p0 else 0
                return v0 + t * (v1 - v0)
        
        if position < sorted_profile[0][0]:
            return sorted_profile[0][1]
        return sorted_profile[-1][1]
    
    def has_segments(self) -> bool:
        """Check if transom has vertical segments (stepped)."""
        return len(self.vertical_segments) > 0
    
    def has_cutouts(self) -> bool:
        """Check if transom has cutouts."""
        return len(self.cutouts) > 0
    
    def has_extensions(self) -> bool:
        """Check if transom has extensions."""
        return len(self.extensions) > 0
    
    @classmethod
    def from_preset(cls, preset: str, **overrides) -> 'TransomConfig':
        """
        Create configuration from preset with optional overrides.
        
        Presets:
        - 'vertical': Vertical transom (Fn < 0.3)
        - 'raked': Standard raked transom (default)
        - 'reverse_raked': Forward-raking transom (rare)
        - 'stepped': Stepped transom for outboard engines
        - 'tunneled': Twin jet tunnel transom
        - 'sugar_scoop': Sugar scoop stern with platform
        - 'notched': Center notch for single outboard/IO
        """
        presets: Dict[str, 'TransomConfig'] = {
            "vertical": cls(preset="vertical", rake_deg=0),
            
            "raked": cls(preset="raked", rake_deg=12),
            
            "reverse_raked": cls(preset="reverse_raked", rake_deg=-8),
            
            "stepped": cls(
                preset="stepped",
                rake_deg=10,
                vertical_segments=[
                    TransomSegment(height_start=0.0, height_end=0.6, rake_deg=10),
                    TransomSegment(height_start=0.6, height_end=0.65, rake_deg=90),  # Vertical step
                    TransomSegment(height_start=0.65, height_end=1.0, rake_deg=10, offset_aft_m=0.3),
                ],
            ),
            
            "tunneled": cls(
                preset="tunneled",
                rake_deg=8,
                cutouts=[
                    TransomCutout(
                        shape="semicircle",
                        center_y_ratio=0.3,
                        width_m=0.5,
                        height_m=0.4,
                        depth_m=0.8,
                    ),
                    TransomCutout(
                        shape="semicircle",
                        center_y_ratio=-0.3,
                        width_m=0.5,
                        height_m=0.4,
                        depth_m=0.8,
                    ),
                ],
            ),
            
            "sugar_scoop": cls(
                preset="sugar_scoop",
                rake_deg=15,
                extensions=[
                    TransomExtension(
                        type="platform",
                        height_start=0.3,
                        height_end=0.5,
                        depth_m=1.2,
                        curvature=-0.3,  # Concave scoop
                    ),
                ],
            ),
            
            "notched": cls(
                preset="notched",
                rake_deg=10,
                cutouts=[
                    TransomCutout(
                        shape="rectangular",
                        center_y_ratio=0.0,
                        width_m=1.0,
                        height_m=0.8,
                        depth_m=0.0,  # Just a notch, not a tunnel
                        height_start_ratio=0.0,
                    ),
                ],
            ),
        }
        
        config = presets.get(preset.lower(), cls())
        
        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset": self.preset,
            "rake_deg": round(self.rake_deg, 1),
            "rake_profile": self.rake_profile,
            "vertical_segments": [s.to_dict() for s in self.vertical_segments],
            "beam_at_waterline_ratio": round(self.beam_at_waterline_ratio, 3),
            "beam_at_deck_ratio": round(self.beam_at_deck_ratio, 3),
            "beam_profile": self.beam_profile,
            "corner_radius_m": round(self.corner_radius_m, 4),
            "corner_radius_profile": self.corner_radius_profile,
            "curvature": round(self.curvature, 3),
            "curvature_profile": self.curvature_profile,
            "cutouts": [c.to_dict() for c in self.cutouts],
            "extensions": [e.to_dict() for e in self.extensions],
            "top_edge": self.top_edge.to_dict(),
            "bottom_edge": self.bottom_edge.to_dict(),
            "side_edges": self.side_edges.to_dict(),
            "blend_to_hull_length_m": round(self.blend_to_hull_length_m, 4),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransomConfig':
        """Create from dictionary."""
        return cls(
            preset=data.get("preset"),
            rake_deg=data.get("rake_deg", 12.0),
            rake_profile=data.get("rake_profile"),
            vertical_segments=[
                TransomSegment.from_dict(s) for s in data.get("vertical_segments", [])
            ],
            beam_at_waterline_ratio=data.get("beam_at_waterline_ratio", 1.0),
            beam_at_deck_ratio=data.get("beam_at_deck_ratio", 1.0),
            beam_profile=data.get("beam_profile"),
            corner_radius_m=data.get("corner_radius_m", 0.0),
            corner_radius_profile=data.get("corner_radius_profile"),
            curvature=data.get("curvature", 0.0),
            curvature_profile=data.get("curvature_profile"),
            cutouts=[
                TransomCutout.from_dict(c) for c in data.get("cutouts", [])
            ],
            extensions=[
                TransomExtension.from_dict(e) for e in data.get("extensions", [])
            ],
            top_edge=TransomEdgeConfig.from_dict(data.get("top_edge", {})),
            bottom_edge=TransomEdgeConfig.from_dict(data.get("bottom_edge", {})),
            side_edges=TransomEdgeConfig.from_dict(data.get("side_edges", {})),
            blend_to_hull_length_m=data.get("blend_to_hull_length_m", 0.5),
        )


# =============================================================================
# PHASE 6: TUMBLEHOME, PANELS, DECK CONFIGURATION
# =============================================================================

@dataclass
class TumblehomeConfig:
    """
    Configuration for tumblehome (inward lean above waterline).
    
    Phase 6: Tumblehome is the inverse of flare — the hull leans inward
    as it rises above the waterline. Common on military vessels to reduce
    radar signature and topside weight.
    
    Cross-section:
                    
        │      │     ← Deck (narrower than waterline)
         │    │      ← Tumblehome zone
          │  │
        ──┼──┼──     ← Waterline (maximum beam)
          │  │
           ││        ← Below waterline (normal hull)
    """
    
    # Enable/disable
    enabled: bool = False
    
    # Vertical extent
    start_height_ratio: float = 0.0
    """Height above waterline where tumblehome begins (0.0=waterline, 0.5=halfway to deck)."""
    
    # Angle control
    angle_deg: float = 5.0
    """Max inward angle at deck (positive=inward lean)."""
    
    # Variable angle by height (within tumblehome zone)
    angle_by_height: Optional[List[Tuple[float, float]]] = None
    """[(height_ratio, angle_deg), ...] where height_ratio is 0-1 within tumblehome zone."""
    
    # Variable by station
    angle_by_station: Optional[List[Tuple[float, float]]] = None
    """[(station, angle_deg), ...] to vary tumblehome along hull length."""
    
    # Transition
    transition_length: float = 0.1
    """Smooth transition zone (fraction of tumblehome height)."""
    
    transition_style: str = "smooth"
    """Transition interpolation: 'linear' | 'smooth'."""
    
    # Regional control
    start_station: float = 0.0
    """Where tumblehome begins longitudinally (0=stern, 1=bow)."""
    
    end_station: float = 1.0
    """Where tumblehome ends longitudinally."""
    
    def get_angle_at(self, station: float, height_in_zone: float) -> float:
        """
        Get tumblehome angle at given station and height within zone.
        
        Args:
            station: Position along hull (0=stern, 1=bow)
            height_in_zone: Position within tumblehome zone (0=start, 1=deck)
            
        Returns:
            Tumblehome angle in degrees (positive=inward lean)
        """
        if not self.enabled:
            return 0.0
        
        if station < self.start_station or station > self.end_station:
            return 0.0
        
        # Base angle
        base_angle = self.angle_deg
        
        # Modify by station if profile provided
        if self.angle_by_station:
            base_angle = self._interpolate_profile(self.angle_by_station, station)
        
        # Modify by height if profile provided
        if self.angle_by_height:
            height_factor = self._interpolate_profile(self.angle_by_height, height_in_zone)
            base_angle *= height_factor / self.angle_deg if self.angle_deg != 0 else 1
        else:
            # Default: linear increase from 0 at start to full at deck
            base_angle *= height_in_zone
        
        # Apply transition smoothing at start of zone
        if height_in_zone < self.transition_length and self.transition_length > 0:
            t = height_in_zone / self.transition_length
            if self.transition_style == "smooth":
                t = t * t * (3 - 2 * t)  # Hermite smoothstep
            base_angle *= t
        
        return base_angle
    
    def _interpolate_profile(self, profile: List[Tuple[float, float]], t: float) -> float:
        """Linear interpolation through profile points."""
        if not profile:
            return 0.0
        
        sorted_profile = sorted(profile, key=lambda x: x[0])
        
        if t <= sorted_profile[0][0]:
            return sorted_profile[0][1]
        if t >= sorted_profile[-1][0]:
            return sorted_profile[-1][1]
        
        for i in range(len(sorted_profile) - 1):
            t0, v0 = sorted_profile[i]
            t1, v1 = sorted_profile[i + 1]
            if t0 <= t <= t1:
                s = (t - t0) / (t1 - t0) if t1 != t0 else 0
                return v0 + s * (v1 - v0)
        
        return sorted_profile[-1][1]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "start_height_ratio": round(self.start_height_ratio, 3),
            "angle_deg": round(self.angle_deg, 1),
            "angle_by_height": self.angle_by_height,
            "angle_by_station": self.angle_by_station,
            "transition_length": round(self.transition_length, 3),
            "transition_style": self.transition_style,
            "start_station": round(self.start_station, 3),
            "end_station": round(self.end_station, 3),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TumblehomeConfig':
        return cls(
            enabled=data.get("enabled", False),
            start_height_ratio=data.get("start_height_ratio", 0.0),
            angle_deg=data.get("angle_deg", 5.0),
            angle_by_height=data.get("angle_by_height"),
            angle_by_station=data.get("angle_by_station"),
            transition_length=data.get("transition_length", 0.1),
            transition_style=data.get("transition_style", "smooth"),
            start_station=data.get("start_station", 0.0),
            end_station=data.get("end_station", 1.0),
        )


@dataclass
class PanelConfig:
    """
    Configuration for hull panel style.
    
    Phase 6: Controls whether hull surfaces are smooth (averaged normals) or
    faceted (flat panels with hard edges between them).
    
    Faceted mode is appropriate for aluminum construction where panels
    are actually flat sheet material.
    """
    
    # Panel style
    style: str = "smooth"
    """Panel style: 'smooth' | 'faceted' | 'developable'."""
    
    # For faceted mode
    longitudinal_panels: int = 0
    """Number of panels along length (0=use section count)."""
    
    circumferential_panels: int = 0
    """Number of panels around section (0=use point count)."""
    
    # Edge treatment between panels
    panel_edges_hard: bool = True
    """Whether edges between panels are hard (for faceted mode)."""
    
    # For developable mode (single curvature constraint)
    developable_tolerance: float = 0.01
    """Max deviation from developable surface (for developable mode)."""
    
    def is_faceted(self) -> bool:
        """Check if panel style is faceted or developable."""
        return self.style in ("faceted", "developable")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "style": self.style,
            "longitudinal_panels": self.longitudinal_panels,
            "circumferential_panels": self.circumferential_panels,
            "panel_edges_hard": self.panel_edges_hard,
            "developable_tolerance": round(self.developable_tolerance, 4),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PanelConfig':
        return cls(
            style=data.get("style", "smooth"),
            longitudinal_panels=data.get("longitudinal_panels", 0),
            circumferential_panels=data.get("circumferential_panels", 0),
            panel_edges_hard=data.get("panel_edges_hard", True),
            developable_tolerance=data.get("developable_tolerance", 0.01),
        )


@dataclass
class DeckConfig:
    """
    Configuration for deck surface generation.
    
    Phase 6: Simple flat or cambered deck to close hull mesh.
    Complex features (cockpits, hatches, cabins) deferred to post-scantlings.
    """
    
    # Enable deck generation
    enabled: bool = True
    
    # Camber (crown)
    camber_m: float = 0.0
    """Height of crown at centerline (0=flat) (m)."""
    
    camber_profile: str = "parabolic"
    """Camber profile: 'flat' | 'parabolic' | 'circular'."""
    
    # Sheer adjustment (deck edge height variation)
    sheer_adjustment_bow_m: float = 0.0
    """Additional deck height at bow (m)."""
    
    sheer_adjustment_stern_m: float = 0.0
    """Additional deck height at stern (m)."""
    
    def is_flat(self) -> bool:
        """Check if deck is flat (no camber)."""
        return self.camber_m == 0.0 or self.camber_profile == "flat"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "camber_m": round(self.camber_m, 4),
            "camber_profile": self.camber_profile,
            "sheer_adjustment_bow_m": round(self.sheer_adjustment_bow_m, 4),
            "sheer_adjustment_stern_m": round(self.sheer_adjustment_stern_m, 4),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeckConfig':
        return cls(
            enabled=data.get("enabled", True),
            camber_m=data.get("camber_m", 0.0),
            camber_profile=data.get("camber_profile", "parabolic"),
            sheer_adjustment_bow_m=data.get("sheer_adjustment_bow_m", 0.0),
            sheer_adjustment_stern_m=data.get("sheer_adjustment_stern_m", 0.0),
        )


@dataclass
class DeadriseProfile:
    """
    Deadrise angle distribution along hull length.

    Deadrise is the angle between the hull bottom and horizontal.
    """

    # === KEY STATIONS (angle in degrees) ===
    deadrise_transom: float = 0.0
    """Deadrise at transom (deg)."""

    deadrise_midship: float = 0.0
    """Deadrise amidships (deg)."""

    deadrise_bow: float = 0.0
    """Deadrise at forward sections (deg)."""

    # === DISTRIBUTION CURVE ===
    stations: List[float] = field(default_factory=list)
    """Station positions (fraction of LWL from AP)."""

    angles: List[float] = field(default_factory=list)
    """Deadrise angles at stations (deg)."""

    @classmethod
    def constant(cls, angle: float) -> 'DeadriseProfile':
        """Create constant deadrise profile."""
        return cls(
            deadrise_transom=angle,
            deadrise_midship=angle,
            deadrise_bow=angle,
            stations=[0.0, 0.5, 1.0],
            angles=[angle, angle, angle],
        )

    @classmethod
    def warped(cls, transom: float, midship: float, bow: float) -> 'DeadriseProfile':
        """Create warped deadrise profile (typical for planing hulls)."""
        stations = [0.0, 0.25, 0.5, 0.75, 1.0]

        # Interpolate with forward sections having more deadrise
        angles = [
            transom,
            transom + 0.25 * (midship - transom),
            midship,
            midship + 0.5 * (bow - midship),
            bow,
        ]

        return cls(
            deadrise_transom=transom,
            deadrise_midship=midship,
            deadrise_bow=bow,
            stations=stations,
            angles=angles,
        )

    def get_deadrise_at(self, x_fraction: float) -> float:
        """
        Get deadrise angle at longitudinal position.

        Args:
            x_fraction: Position as fraction of LWL from AP (0=AP, 1=FP)

        Returns:
            Deadrise angle in degrees
        """
        if not self.stations or not self.angles:
            return self.deadrise_midship

        # Clamp to range
        x_fraction = max(0.0, min(1.0, x_fraction))

        # Linear interpolation
        for i in range(len(self.stations) - 1):
            if self.stations[i] <= x_fraction <= self.stations[i + 1]:
                t = (x_fraction - self.stations[i]) / (self.stations[i + 1] - self.stations[i])
                return self.angles[i] + t * (self.angles[i + 1] - self.angles[i])

        return self.angles[-1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deadrise_transom": round(self.deadrise_transom, 1),
            "deadrise_midship": round(self.deadrise_midship, 1),
            "deadrise_bow": round(self.deadrise_bow, 1),
            "stations": self.stations,
            "angles": [round(a, 1) for a in self.angles],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeadriseProfile':
        """Create from dictionary."""
        return cls(
            deadrise_transom=data.get("deadrise_transom", 0.0),
            deadrise_midship=data.get("deadrise_midship", 0.0),
            deadrise_bow=data.get("deadrise_bow", 0.0),
            stations=data.get("stations", []),
            angles=data.get("angles", []),
        )


@dataclass
class HullFeatures:
    """
    Hull feature definitions.
    
    v1.1: Extended chine configuration for Phase 2.
    """

    # === CHINE ===
    chine_width_mm: float = 0.0
    """Spray rail / chine flat width (mm)."""
    
    # === Phase 2: Extended chine configuration ===
    chine_count: int = 1
    """Number of chines per side (1, 2, or 3)."""
    
    chine_style: str = "standard"
    """Chine style: 'standard', 'reverse', or 'variable'."""
    
    chines: List[ChineConfig] = field(default_factory=list)
    """Explicit chine configurations (overrides generated defaults)."""
    
    # Variable chine control
    chine_transition_start: float = 0.0
    """Station where soft→hard transition begins (for variable chine)."""
    
    chine_transition_end: float = 0.0
    """Station where transition completes (for variable chine)."""
    
    # Reverse chine (sponson) specific
    reverse_chine_height_ratio: float = 0.0
    """Height of reverse chine as fraction of draft."""
    
    reverse_chine_extension_m: float = 0.0
    """How far reverse chine extends outward (m)."""
    
    # Chine flat
    chine_flat_width_m: float = 0.0
    """Width of horizontal flat at main chine (m)."""

    # === BOW ===
    stem_rake_deg: float = 15.0
    """Stem rake angle from vertical (deg)."""

    bow_flare_deg: float = 0.0
    """Bow flare angle (deg)."""

    bow_entrance_deg: float = 25.0
    """Waterline entry half-angle (deg)."""
    
    # === Phase 3: Bow form configuration ===
    bow_config: Optional['BowConfig'] = None
    """Explicit bow configuration (preferred; enum-free)."""
    
    bow_facet_count: int = 2
    """Number of facets per side for FACETED bow style."""
    
    bow_region_length: float = 0.20
    """Fraction of LWL that is bow region."""
    
    # === Phase 4: Spray Rails ===
    spray_rails: List['SprayRailConfig'] = field(default_factory=list)
    """Explicit spray rail configurations."""
    
    spray_rail_count: int = 0
    """Number of spray rails per side (generates default configurations)."""
    
    spray_rail_spacing: float = 0.15
    """Vertical spacing between auto-generated spray rails."""
    
    has_spray_rails: bool = False
    """Feature flag for spray rails."""
    
    # === Phase 4: Knuckle Lines ===
    knuckle_lines: List['KnuckleLineConfig'] = field(default_factory=list)
    """Knuckle line configurations."""
    
    has_knuckle_lines: bool = False
    """Feature flag for knuckle lines."""

    # === STERN ===
    transom_rake_deg: float = 12.0
    """Transom rake angle from vertical (deg)."""

    transom_width_fraction: float = 0.85
    """Transom width as fraction of max beam."""
    
    # === Phase 5: Transom configuration ===
    transom_config: Optional['TransomConfig'] = None
    """Full parametric transom configuration (overrides simple transom params)."""
    
    transom_preset: Optional[str] = None
    """Transom preset name: 'vertical' | 'raked' | 'stepped' | 'tunneled' | 'sugar_scoop'."""

    stern: Optional[SternConfig] = None
    """Optional stern configuration (preferred; enum-free)."""

    # === Phase 6: Tumblehome ===
    tumblehome_enabled: bool = False
    """Enable tumblehome (inward lean above waterline)."""
    
    tumblehome_angle_deg: float = 5.0
    """Tumblehome angle at deck (degrees, positive=inward)."""
    
    tumblehome_start_ratio: float = 0.0
    """Height above waterline where tumblehome begins (0-1)."""
    
    tumblehome_config: Optional['TumblehomeConfig'] = None
    """Full parametric tumblehome configuration."""
    
    # === Phase 6: Panel Style ===
    panel_style: str = "smooth"
    """Panel style: 'smooth' | 'faceted' | 'developable'."""
    
    panel_config: Optional['PanelConfig'] = None
    """Full parametric panel configuration."""
    
    # === Phase 6: Deck ===
    deck_enabled: bool = True
    """Enable deck surface generation."""
    
    deck_camber_m: float = 0.0
    """Deck camber (crown height at centerline) (m)."""
    
    deck_config: Optional['DeckConfig'] = None
    """Full parametric deck configuration."""

    # === KEEL ===
    skeg_height_m: float = 0.0
    """Skeg height if applicable (m)."""

    keel_attachments: List[KeelAttachment] = field(default_factory=list)
    """Optional keel attachments (preferred; enum-free)."""

    # === TUNNELS ===
    has_tunnels: bool = False
    tunnel_width_m: float = 0.0
    tunnel_depth_m: float = 0.0

    # === MULTIHULL ===
    hull_spacing: float = 0.0
    """Distance between hull centerlines for catamaran/trimaran (m)."""

    num_hulls: int = 1
    """Number of hulls (1=mono, 2=cat, 3=tri)."""

    def get_chine_configs(self) -> List[ChineConfig]:
        """
        Get chine configurations, generating defaults if not explicit.
        
        Returns list of ChineConfig sorted by height (keel to waterline).
        """
        if self.chines:
            return sorted(self.chines, key=lambda c: c.height_ratio)
        
        # Generate default configs from continuous controls (enum-free)
        flat_width = self.chine_flat_width_m or (self.chine_width_mm / 1000.0)

        # Reverse chine enabled (outward-angled): require explicit style + nonzero params.
        if (
            str(self.chine_style or "standard") == "reverse"
            and float(self.reverse_chine_height_ratio or 0.0) > 0.0
            and float(self.reverse_chine_extension_m or 0.0) > 0.0
        ):
            return [
                ChineConfig(
                    height_ratio=float(self.reverse_chine_height_ratio),
                    angle_deg=-30,  # Negative = outward angle
                    is_hard=True,
                    flat_width_m=flat_width,
                )
            ]

        count = int(self.chine_count or 0)
        if count <= 0:
            return []
        if count == 1:
            return [
                ChineConfig(
                    height_ratio=0.3,
                    angle_deg=45,
                    is_hard=True,
                    flat_width_m=flat_width,
                )
            ]
        if count == 2:
            return [
                ChineConfig(height_ratio=0.20, angle_deg=50, is_hard=True),
                ChineConfig(height_ratio=0.50, angle_deg=35, is_hard=True, flat_width_m=flat_width),
            ]
        # 3+ => triple (cap at three configs)
        return [
            ChineConfig(height_ratio=0.15, angle_deg=55, is_hard=True),
            ChineConfig(height_ratio=0.35, angle_deg=45, is_hard=True),
            ChineConfig(height_ratio=0.60, angle_deg=30, is_hard=True, flat_width_m=flat_width),
        ]

    def get_bow_config(self) -> 'BowConfig':
        """
        Get bow configuration, generating defaults if not explicit.
        
        Returns BowConfig based on explicit bow_config, or a traditional default.
        """
        if self.bow_config:
            return self.bow_config
        
        # Default: traditional bow derived from continuous parameters.
        return BowConfig(
            facet_count=0,
            planarity=0.0,
            half_angle_deg=self.bow_entrance_deg,
            stem_rake_deg=self.stem_rake_deg,
            region_length=self.bow_region_length,
            flare_deg=self.bow_flare_deg,
        )

    def get_spray_rails(self) -> List['SprayRailConfig']:
        """
        Get spray rail configurations, generating defaults if count specified.
        
        Returns list of SprayRailConfig sorted by height.
        """
        if self.spray_rails:
            return sorted(self.spray_rails, key=lambda r: r.height_ratio)
        
        if self.spray_rail_count > 0:
            # Generate evenly spaced spray rails
            rails = []
            for i in range(self.spray_rail_count):
                height = 0.15 + i * self.spray_rail_spacing
                rails.append(SprayRailConfig(
                    height_ratio=min(height, 0.9),
                    angle_deg=15.0 - i * 2,  # Slightly less angle for upper rails
                    width_m=0.05 - i * 0.01,  # Slightly narrower upper rails
                ))
            return rails
        
        return []

    def get_knuckle_lines(self) -> List['KnuckleLineConfig']:
        """Get knuckle line configurations."""
        return sorted(self.knuckle_lines, key=lambda k: k.height_ratio) if self.knuckle_lines else []

    def get_active_spray_rails_at_station(self, station: float) -> List['SprayRailConfig']:
        """Get spray rails active at given station."""
        return [r for r in self.get_spray_rails() if r.is_active_at_station(station)]

    def get_active_knuckles_at_station(self, station: float) -> List['KnuckleLineConfig']:
        """Get knuckle lines active at given station."""
        return [k for k in self.get_knuckle_lines() if k.is_active_at_station(station)]

    def get_transom_config(self) -> 'TransomConfig':
        """
        Get transom configuration, generating from preset or defaults if not explicit.
        
        Priority:
        1. Explicit transom_config
        2. transom_preset (creates from preset)
        3. Default based on transom_rake_deg and transom_width_fraction
        """
        if self.transom_config:
            return self.transom_config
        
        if self.transom_preset:
            return TransomConfig.from_preset(
                self.transom_preset,
                rake_deg=self.transom_rake_deg,
                beam_at_waterline_ratio=self.transom_width_fraction,
                beam_at_deck_ratio=self.transom_width_fraction,
            )
        
        # Generate default based on simple parameters
        return TransomConfig(
            rake_deg=self.transom_rake_deg,
            beam_at_waterline_ratio=self.transom_width_fraction,
            beam_at_deck_ratio=self.transom_width_fraction,
        )
    
    # === Phase 6 config getters ===
    
    def get_tumblehome_config(self) -> 'TumblehomeConfig':
        """
        Get tumblehome configuration.
        
        Priority:
        1. Explicit tumblehome_config
        2. Generate from simple parameters if enabled
        3. Disabled config if not enabled
        """
        if self.tumblehome_config:
            return self.tumblehome_config
        
        if self.tumblehome_enabled:
            return TumblehomeConfig(
                enabled=True,
                angle_deg=self.tumblehome_angle_deg,
                start_height_ratio=self.tumblehome_start_ratio,
            )
        
        return TumblehomeConfig(enabled=False)
    
    def get_panel_config(self) -> 'PanelConfig':
        """
        Get panel configuration.
        
        Priority:
        1. Explicit panel_config
        2. Generate from panel_style
        """
        if self.panel_config:
            return self.panel_config
        
        return PanelConfig(style=self.panel_style)
    
    def get_deck_config(self) -> 'DeckConfig':
        """
        Get deck configuration.
        
        Priority:
        1. Explicit deck_config
        2. Generate from simple parameters
        """
        if self.deck_config:
            return self.deck_config
        
        return DeckConfig(
            enabled=self.deck_enabled,
            camber_m=self.deck_camber_m,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chine_width_mm": self.chine_width_mm,
            "chine_count": self.chine_count,
            "chine_style": self.chine_style,
            "chines": [c.to_dict() for c in self.chines],
            "chine_transition_start": self.chine_transition_start,
            "chine_transition_end": self.chine_transition_end,
            "reverse_chine_height_ratio": self.reverse_chine_height_ratio,
            "reverse_chine_extension_m": self.reverse_chine_extension_m,
            "chine_flat_width_m": self.chine_flat_width_m,
            "stem_rake_deg": self.stem_rake_deg,
            "bow_flare_deg": self.bow_flare_deg,
            "bow_entrance_deg": self.bow_entrance_deg,
            "bow_config": self.bow_config.to_dict() if self.bow_config else None,
            "bow_facet_count": self.bow_facet_count,
            "bow_region_length": self.bow_region_length,
            "spray_rails": [r.to_dict() for r in self.spray_rails],
            "spray_rail_count": self.spray_rail_count,
            "spray_rail_spacing": self.spray_rail_spacing,
            "has_spray_rails": self.has_spray_rails,
            "knuckle_lines": [k.to_dict() for k in self.knuckle_lines],
            "has_knuckle_lines": self.has_knuckle_lines,
            "transom_rake_deg": self.transom_rake_deg,
            "transom_width_fraction": self.transom_width_fraction,
            "transom_config": self.transom_config.to_dict() if self.transom_config else None,
            "transom_preset": self.transom_preset,
            "stern": self.stern.__dict__ if self.stern else None,
            # Phase 6: Tumblehome
            "tumblehome_enabled": self.tumblehome_enabled,
            "tumblehome_angle_deg": self.tumblehome_angle_deg,
            "tumblehome_start_ratio": self.tumblehome_start_ratio,
            "tumblehome_config": self.tumblehome_config.to_dict() if self.tumblehome_config else None,
            # Phase 6: Panels
            "panel_style": self.panel_style,
            "panel_config": self.panel_config.to_dict() if self.panel_config else None,
            # Phase 6: Deck
            "deck_enabled": self.deck_enabled,
            "deck_camber_m": self.deck_camber_m,
            "deck_config": self.deck_config.to_dict() if self.deck_config else None,
            "skeg_height_m": self.skeg_height_m,
            "keel_attachments": [k.__dict__ for k in self.keel_attachments],
            "has_tunnels": self.has_tunnels,
            "tunnel_width_m": self.tunnel_width_m,
            "tunnel_depth_m": self.tunnel_depth_m,
            "hull_spacing": self.hull_spacing,
            "num_hulls": self.num_hulls,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HullFeatures':
        """Create from dictionary."""
        chines_data = data.get("chines", [])
        chines = [ChineConfig.from_dict(c) for c in chines_data] if chines_data else []
        
        bow_config_data = data.get("bow_config")
        bow_config = BowConfig.from_dict(bow_config_data) if bow_config_data else None
        
        spray_rails_data = data.get("spray_rails", [])
        spray_rails = [SprayRailConfig.from_dict(r) for r in spray_rails_data] if spray_rails_data else []
        
        knuckle_lines_data = data.get("knuckle_lines", [])
        knuckle_lines = [KnuckleLineConfig.from_dict(k) for k in knuckle_lines_data] if knuckle_lines_data else []
        
        transom_config_data = data.get("transom_config")
        transom_config = TransomConfig.from_dict(transom_config_data) if transom_config_data else None

        stern_data = data.get("stern")
        stern = SternConfig(**stern_data) if isinstance(stern_data, dict) else None

        keel_attachments_data = data.get("keel_attachments") or []
        keel_attachments = []
        if isinstance(keel_attachments_data, list):
            for k in keel_attachments_data:
                if isinstance(k, dict) and k.get("body_id"):
                    keel_attachments.append(KeelAttachment(**k))
        
        # Phase 6 configs
        tumblehome_config_data = data.get("tumblehome_config")
        tumblehome_config = TumblehomeConfig.from_dict(tumblehome_config_data) if tumblehome_config_data else None
        
        panel_config_data = data.get("panel_config")
        panel_config = PanelConfig.from_dict(panel_config_data) if panel_config_data else None
        
        deck_config_data = data.get("deck_config")
        deck_config = DeckConfig.from_dict(deck_config_data) if deck_config_data else None
        
        return cls(
            chine_width_mm=data.get("chine_width_mm", 0.0),
            chine_count=data.get("chine_count", 1),
            chine_style=data.get("chine_style", "standard"),
            chines=chines,
            chine_transition_start=data.get("chine_transition_start", 0.0),
            chine_transition_end=data.get("chine_transition_end", 0.0),
            reverse_chine_height_ratio=data.get("reverse_chine_height_ratio", 0.0),
            reverse_chine_extension_m=data.get("reverse_chine_extension_m", 0.0),
            chine_flat_width_m=data.get("chine_flat_width_m", 0.0),
            stem_rake_deg=data.get("stem_rake_deg", 15.0),
            bow_flare_deg=data.get("bow_flare_deg", 0.0),
            bow_entrance_deg=data.get("bow_entrance_deg", 25.0),
            bow_config=bow_config,
            bow_facet_count=data.get("bow_facet_count", 2),
            bow_region_length=data.get("bow_region_length", 0.20),
            spray_rails=spray_rails,
            spray_rail_count=data.get("spray_rail_count", 0),
            spray_rail_spacing=data.get("spray_rail_spacing", 0.15),
            has_spray_rails=data.get("has_spray_rails", False),
            knuckle_lines=knuckle_lines,
            has_knuckle_lines=data.get("has_knuckle_lines", False),
            transom_rake_deg=data.get("transom_rake_deg", 12.0),
            transom_width_fraction=data.get("transom_width_fraction", 0.85),
            transom_config=transom_config,
            transom_preset=data.get("transom_preset"),
            stern=stern,
            # Phase 6: Tumblehome
            tumblehome_enabled=data.get("tumblehome_enabled", False),
            tumblehome_angle_deg=data.get("tumblehome_angle_deg", 5.0),
            tumblehome_start_ratio=data.get("tumblehome_start_ratio", 0.0),
            tumblehome_config=tumblehome_config,
            # Phase 6: Panels
            panel_style=data.get("panel_style", "smooth"),
            panel_config=panel_config,
            # Phase 6: Deck
            deck_enabled=data.get("deck_enabled", True),
            deck_camber_m=data.get("deck_camber_m", 0.0),
            deck_config=deck_config,
            skeg_height_m=data.get("skeg_height_m", 0.0),
            keel_attachments=keel_attachments,
            has_tunnels=data.get("has_tunnels", False),
            tunnel_width_m=data.get("tunnel_width_m", 0.0),
            tunnel_depth_m=data.get("tunnel_depth_m", 0.0),
            hull_spacing=data.get("hull_spacing", 0.0),
            num_hulls=data.get("num_hulls", 1),
        )


@dataclass
class HullDefinition:
    """
    Complete parametric hull definition.
    """

    # === IDENTIFICATION ===
    hull_id: str = ""
    hull_name: str = ""

    # === PARAMETERS ===
    dimensions: MainDimensions = field(default_factory=MainDimensions)
    coefficients: FormCoefficients = field(default_factory=FormCoefficients)
    deadrise: DeadriseProfile = field(default_factory=DeadriseProfile)
    features: HullFeatures = field(default_factory=HullFeatures)

    # === COMPUTED ===
    displacement_m3: float = 0.0
    wetted_surface_m2: float = 0.0
    waterplane_area_m2: float = 0.0

    def compute_displacement(self) -> float:
        """Compute displacement volume from coefficients."""
        self.displacement_m3 = (
            self.coefficients.cb *
            self.dimensions.lwl *
            self.dimensions.beam_wl *
            self.dimensions.draft
        )
        return self.displacement_m3

    def compute_waterplane_area(self) -> float:
        """Compute waterplane area from coefficients."""
        self.waterplane_area_m2 = (
            self.coefficients.cwp *
            self.dimensions.lwl *
            self.dimensions.beam_wl
        )
        return self.waterplane_area_m2

    def validate(self) -> List[str]:
        """Validate complete hull definition."""
        errors = []
        errors.extend(self.dimensions.validate())
        errors.extend(self.coefficients.validate())
        return errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hull_id": self.hull_id,
            "hull_name": self.hull_name,
            "dimensions": self.dimensions.to_dict(),
            "coefficients": self.coefficients.to_dict(),
            "deadrise": self.deadrise.to_dict(),
            "features": self.features.to_dict(),
            "displacement_m3": round(self.displacement_m3, 3),
            "wetted_surface_m2": round(self.wetted_surface_m2, 3),
            "waterplane_area_m2": round(self.waterplane_area_m2, 3),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HullDefinition':
        """Create from dictionary."""
        return cls(
            hull_id=data.get("hull_id", ""),
            hull_name=data.get("hull_name", ""),
            dimensions=MainDimensions.from_dict(data.get("dimensions", {})),
            coefficients=FormCoefficients.from_dict(data.get("coefficients", {})),
            deadrise=DeadriseProfile.from_dict(data.get("deadrise", {})),
            features=HullFeatures.from_dict(data.get("features", {})),
            displacement_m3=data.get("displacement_m3", 0.0),
            wetted_surface_m2=data.get("wetted_surface_m2", 0.0),
            waterplane_area_m2=data.get("waterplane_area_m2", 0.0),
        )
