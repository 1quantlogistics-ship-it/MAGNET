"""
MAGNET V1 Hull Parameters Schema (ALPHA)

Defines principal hull dimensions and form coefficients.
"""

from pydantic import BaseModel, Field, field_validator, computed_field
from typing import Optional
from enum import Enum


class HullType(str, Enum):
    """Hull form classification."""
    MONOHULL = "monohull"
    CATAMARAN = "catamaran"
    TRIMARAN = "trimaran"
    SWATH = "swath"  # Small Waterplane Area Twin Hull
    PLANING = "planing"
    SEMI_DISPLACEMENT = "semi_displacement"
    DISPLACEMENT = "displacement"


class HullParamsSchema(BaseModel):
    """
    Principal hull dimensions and form coefficients.

    This schema captures the fundamental geometric parameters that
    define a vessel's hull form. All coefficients use standard
    naval architecture conventions.

    Reference: Principles of Naval Architecture (SNAME)
    """

    # Hull type classification
    hull_type: HullType = Field(
        default=HullType.SEMI_DISPLACEMENT,
        description="Hull form classification"
    )

    # Principal dimensions (meters)
    length_overall: float = Field(
        ...,
        ge=10,
        le=500,
        description="Length Overall (LOA) in meters"
    )
    length_waterline: float = Field(
        ...,
        ge=10,
        le=500,
        description="Length at Waterline (LWL) in meters"
    )
    length_between_perpendiculars: Optional[float] = Field(
        None,
        ge=10,
        le=500,
        description="Length Between Perpendiculars (LBP) in meters"
    )
    beam: float = Field(
        ...,
        ge=2,
        le=100,
        description="Maximum beam in meters"
    )
    beam_waterline: Optional[float] = Field(
        None,
        ge=2,
        le=100,
        description="Beam at waterline in meters"
    )
    draft: float = Field(
        ...,
        ge=0.5,
        le=30,
        description="Design draft in meters"
    )
    depth: float = Field(
        ...,
        ge=1,
        le=50,
        description="Depth (molded) in meters"
    )
    freeboard: Optional[float] = Field(
        None,
        ge=0.5,
        le=20,
        description="Freeboard at midship in meters"
    )

    # Form coefficients (dimensionless)
    block_coefficient: float = Field(
        ...,
        ge=0.30,
        le=0.90,
        description="Block coefficient (Cb) = V / (L * B * T)"
    )
    prismatic_coefficient: float = Field(
        ...,
        ge=0.50,
        le=0.85,
        description="Prismatic coefficient (Cp) = V / (Am * L)"
    )
    midship_coefficient: float = Field(
        ...,
        ge=0.70,
        le=1.00,
        description="Midship section coefficient (Cm) = Am / (B * T)"
    )
    waterplane_coefficient: float = Field(
        ...,
        ge=0.60,
        le=0.95,
        description="Waterplane coefficient (Cwp) = Awp / (L * B)"
    )

    # Longitudinal position (fraction of LWL from transom)
    lcb_position: float = Field(
        default=0.52,
        ge=0.45,
        le=0.58,
        description="Longitudinal Center of Buoyancy position (fraction of LWL from AP)"
    )
    lcf_position: Optional[float] = Field(
        None,
        ge=0.40,
        le=0.60,
        description="Longitudinal Center of Flotation position (fraction of LWL from AP)"
    )

    # Catamaran-specific (if hull_type is CATAMARAN)
    hull_spacing: Optional[float] = Field(
        None,
        ge=0,
        description="Spacing between catamaran hulls (centerline to centerline) in meters"
    )
    demihull_beam: Optional[float] = Field(
        None,
        ge=1,
        description="Individual demihull beam in meters (for catamaran)"
    )

    # Calculated/cached values
    displacement_tonnes: Optional[float] = Field(
        None,
        ge=0,
        description="Calculated displacement in tonnes"
    )
    wetted_surface_m2: Optional[float] = Field(
        None,
        ge=0,
        description="Calculated wetted surface area in m²"
    )

    @field_validator('length_waterline')
    @classmethod
    def lwl_less_than_loa(cls, v: float, info) -> float:
        """Ensure LWL <= LOA."""
        if 'length_overall' in info.data and v > info.data['length_overall']:
            raise ValueError('Length at waterline (LWL) must be <= Length overall (LOA)')
        return v

    @field_validator('draft')
    @classmethod
    def draft_less_than_depth(cls, v: float, info) -> float:
        """Ensure draft < depth."""
        if 'depth' in info.data and v >= info.data['depth']:
            raise ValueError('Draft must be < Depth')
        return v

    @field_validator('freeboard')
    @classmethod
    def validate_freeboard(cls, v: Optional[float], info) -> Optional[float]:
        """Validate freeboard = depth - draft."""
        if v is not None and 'depth' in info.data and 'draft' in info.data:
            expected = info.data['depth'] - info.data['draft']
            if abs(v - expected) > 0.01:  # 1cm tolerance
                raise ValueError(f'Freeboard ({v}) should equal depth - draft ({expected})')
        return v

    @computed_field
    @property
    def length_beam_ratio(self) -> float:
        """Length-to-beam ratio (L/B)."""
        return self.length_waterline / self.beam

    @computed_field
    @property
    def beam_draft_ratio(self) -> float:
        """Beam-to-draft ratio (B/T)."""
        return self.beam / self.draft

    @computed_field
    @property
    def depth_draft_ratio(self) -> float:
        """Depth-to-draft ratio (D/T)."""
        return self.depth / self.draft

    @computed_field
    @property
    def slenderness_coefficient(self) -> float:
        """
        Slenderness coefficient (L/∇^(1/3)).

        Useful for resistance prediction.
        Typical values: 4-5 (slow), 5-6 (medium), 6-8 (fast)
        """
        volume = self.length_waterline * self.beam * self.draft * self.block_coefficient
        return self.length_waterline / (volume ** (1/3))

    @computed_field
    @property
    def volumetric_coefficient(self) -> float:
        """
        Volumetric coefficient = ∇ / (L/10)^3

        Indicates fullness of hull relative to length.
        """
        volume = self.length_waterline * self.beam * self.draft * self.block_coefficient
        return volume / ((self.length_waterline / 10) ** 3)

    class Config:
        json_schema_extra = {
            "example": {
                "hull_type": "semi_displacement",
                "length_overall": 48.0,
                "length_waterline": 45.0,
                "beam": 12.8,
                "draft": 2.1,
                "depth": 4.5,
                "block_coefficient": 0.45,
                "prismatic_coefficient": 0.65,
                "midship_coefficient": 0.85,
                "waterplane_coefficient": 0.78,
                "lcb_position": 0.52
            }
        }
