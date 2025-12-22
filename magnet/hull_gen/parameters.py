"""
hull_gen/parameters.py - Parametric hull definition data structures.

BRAVO OWNS THIS FILE.

Module 16 v1.0 - Parametric hull definition.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .enums import (
    HullType, ChineType, StemProfile, SternProfile,
    TransomType, KeelType, SectionShape
)


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

    @classmethod
    def for_hull_type(cls, hull_type: HullType, speed_length_ratio: float = 1.0) -> 'FormCoefficients':
        """
        Generate typical coefficients for hull type.

        Args:
            hull_type: Type of hull
            speed_length_ratio: V/sqrt(L) (knots/sqrt(ft)) for tuning
        """
        if hull_type == HullType.DEEP_V_PLANING:
            return cls(
                cb=0.35 + 0.05 * (1 - speed_length_ratio / 3),
                cp=0.55 + 0.05 * (1 - speed_length_ratio / 3),
                cm=0.65,
                cwp=0.70,
                lcb=0.40,  # Forward for planing
                lcf=0.42,
            )
        elif hull_type == HullType.SEMI_DISPLACEMENT:
            return cls(
                cb=0.45,
                cp=0.62,
                cm=0.72,
                cwp=0.75,
                lcb=0.48,
                lcf=0.50,
            )
        elif hull_type == HullType.ROUND_BILGE:
            return cls(
                cb=0.55,
                cp=0.68,
                cm=0.80,
                cwp=0.78,
                lcb=0.52,
                lcf=0.53,
            )
        elif hull_type == HullType.HARD_CHINE:
            return cls(
                cb=0.40,
                cp=0.58,
                cm=0.70,
                cwp=0.72,
                lcb=0.45,
                lcf=0.47,
            )
        else:
            return cls(
                cb=0.45,
                cp=0.60,
                cm=0.75,
                cwp=0.72,
                lcb=0.50,
                lcf=0.50,
            )

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
    """

    # === CHINE ===
    chine_type: ChineType = ChineType.NONE
    chine_width_mm: float = 0.0
    """Spray rail / chine flat width (mm)."""

    # === BOW ===
    stem_profile: StemProfile = StemProfile.RAKED
    stem_rake_deg: float = 15.0
    """Stem rake angle from vertical (deg)."""

    bow_flare_deg: float = 0.0
    """Bow flare angle (deg)."""

    # === STERN ===
    stern_profile: SternProfile = SternProfile.TRANSOM
    transom_type: TransomType = TransomType.DRY
    transom_rake_deg: float = 12.0
    """Transom rake angle from vertical (deg)."""

    transom_width_fraction: float = 0.85
    """Transom width as fraction of max beam."""

    # === KEEL ===
    keel_type: KeelType = KeelType.FLAT
    skeg_height_m: float = 0.0
    """Skeg height if applicable (m)."""

    # === TUNNELS ===
    has_tunnels: bool = False
    tunnel_width_m: float = 0.0
    tunnel_depth_m: float = 0.0

    # === MULTIHULL ===
    hull_spacing: float = 0.0
    """Distance between hull centerlines for catamaran/trimaran (m)."""

    num_hulls: int = 1
    """Number of hulls (1=mono, 2=cat, 3=tri)."""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chine_type": self.chine_type.value,
            "chine_width_mm": self.chine_width_mm,
            "stem_profile": self.stem_profile.value,
            "stem_rake_deg": self.stem_rake_deg,
            "bow_flare_deg": self.bow_flare_deg,
            "stern_profile": self.stern_profile.value,
            "transom_type": self.transom_type.value,
            "transom_rake_deg": self.transom_rake_deg,
            "transom_width_fraction": self.transom_width_fraction,
            "keel_type": self.keel_type.value,
            "skeg_height_m": self.skeg_height_m,
            "has_tunnels": self.has_tunnels,
            "tunnel_width_m": self.tunnel_width_m,
            "tunnel_depth_m": self.tunnel_depth_m,
            "hull_spacing": self.hull_spacing,
            "num_hulls": self.num_hulls,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HullFeatures':
        """Create from dictionary."""
        return cls(
            chine_type=ChineType(data.get("chine_type", "none")),
            chine_width_mm=data.get("chine_width_mm", 0.0),
            stem_profile=StemProfile(data.get("stem_profile", "raked")),
            stem_rake_deg=data.get("stem_rake_deg", 15.0),
            bow_flare_deg=data.get("bow_flare_deg", 0.0),
            stern_profile=SternProfile(data.get("stern_profile", "transom")),
            transom_type=TransomType(data.get("transom_type", "dry")),
            transom_rake_deg=data.get("transom_rake_deg", 12.0),
            transom_width_fraction=data.get("transom_width_fraction", 0.85),
            keel_type=KeelType(data.get("keel_type", "flat")),
            skeg_height_m=data.get("skeg_height_m", 0.0),
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

    # === TYPE ===
    hull_type: HullType = HullType.HARD_CHINE

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
            "hull_type": self.hull_type.value,
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
            hull_type=HullType(data.get("hull_type", "hard_chine")),
            dimensions=MainDimensions.from_dict(data.get("dimensions", {})),
            coefficients=FormCoefficients.from_dict(data.get("coefficients", {})),
            deadrise=DeadriseProfile.from_dict(data.get("deadrise", {})),
            features=HullFeatures.from_dict(data.get("features", {})),
            displacement_m3=data.get("displacement_m3", 0.0),
            wetted_surface_m2=data.get("wetted_surface_m2", 0.0),
            waterplane_area_m2=data.get("waterplane_area_m2", 0.0),
        )
