"""
hull_gen/generator.py - Parametric hull form generator.

BRAVO OWNS THIS FILE.

Module 16-18 v1.0 - Hull form generation from parameters.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .enums import HullType, ChineType, SectionShape
from .parameters import HullDefinition, MainDimensions, FormCoefficients, DeadriseProfile
from .geometry import Point3D, SectionPoint, HullSection, Waterline, HullGeometry


@dataclass
class GeneratorConfig:
    """Configuration for hull generation."""

    num_sections: int = 21
    """Number of transverse sections to generate."""

    num_waterlines: int = 11
    """Number of waterlines to generate."""

    points_per_section: int = 25
    """Number of points per section (half-section)."""

    include_buttocks: bool = True
    """Whether to generate buttock lines."""

    num_buttocks: int = 5
    """Number of buttock lines per side."""


class HullGenerator:
    """
    Parametric hull form generator.

    Generates hull geometry from parametric definition using
    form coefficient-based interpolation.
    """

    def __init__(self, config: Optional[GeneratorConfig] = None):
        """
        Initialize generator.

        Args:
            config: Generator configuration
        """
        self.config = config or GeneratorConfig()

    def generate(self, definition: HullDefinition) -> HullGeometry:
        """
        Generate hull geometry from definition.

        Args:
            definition: Hull definition parameters

        Returns:
            Complete hull geometry
        """
        geometry = HullGeometry(hull_id=definition.hull_id)

        # Generate sections
        geometry.sections = self._generate_sections(definition)

        # Generate waterlines
        geometry.waterlines = self._generate_waterlines(definition, geometry.sections)

        # Generate key curves
        geometry.keel_profile = self._generate_keel_profile(definition)
        geometry.stem_profile = self._generate_stem_profile(definition)
        geometry.chine_curve = self._generate_chine_curve(definition, geometry.sections)
        geometry.transom_outline = self._generate_transom(definition)

        # Compute properties
        geometry.compute_volume()
        geometry.waterplane_area = self._compute_waterplane_area(definition, geometry)
        geometry.wetted_surface = self._estimate_wetted_surface(definition)

        return geometry

    def _generate_sections(self, definition: HullDefinition) -> List[HullSection]:
        """Generate transverse sections."""
        sections = []
        lwl = definition.dimensions.lwl
        num_sections = self.config.num_sections

        for i in range(num_sections):
            station = i / (num_sections - 1)
            x_pos = station * lwl

            section = self._generate_section_at_station(definition, station, x_pos)
            sections.append(section)

        return sections

    def _generate_section_at_station(
        self,
        definition: HullDefinition,
        station: float,
        x_pos: float,
    ) -> HullSection:
        """
        Generate a single transverse section.

        Args:
            definition: Hull definition
            station: Station position (0=AP, 1=FP)
            x_pos: Longitudinal position in meters
        """
        section = HullSection(station=station, x_position=x_pos)

        # Get section properties
        half_beam = self._get_half_beam_at_station(definition, station)
        draft = self._get_draft_at_station(definition, station)
        deadrise = definition.deadrise.get_deadrise_at(station)

        section.half_beam = half_beam
        section.draft_local = draft
        section.deadrise_deg = deadrise

        # Generate section points based on hull type
        if definition.hull_type in [HullType.DEEP_V_PLANING, HullType.HARD_CHINE]:
            points = self._generate_chine_section(
                half_beam, draft, deadrise, definition, station
            )
        elif definition.hull_type == HullType.ROUND_BILGE:
            points = self._generate_round_section(half_beam, draft, definition, station)
        else:
            points = self._generate_generic_section(
                half_beam, draft, deadrise, definition, station
            )

        section.points = points

        # Compute section area
        section.compute_area(0.0)  # At design waterline

        # Set key points
        if points:
            section.keel_point = points[0].position
            section.waterline_point = self._find_waterline_point(points, 0.0)
            if any(p.is_chine for p in points):
                chine_points = [p for p in points if p.is_chine]
                if chine_points:
                    section.chine_point = chine_points[0].position

        return section

    def _generate_chine_section(
        self,
        half_beam: float,
        draft: float,
        deadrise: float,
        definition: HullDefinition,
        station: float,
    ) -> List[SectionPoint]:
        """Generate hard-chine section profile."""
        points = []
        num_points = self.config.points_per_section

        deadrise_rad = math.radians(deadrise)

        # Keel point
        keel = SectionPoint(
            position=Point3D(x=station * definition.dimensions.lwl, y=0, z=-draft),
            is_keel=True,
        )
        points.append(keel)

        # Chine point
        chine_y = half_beam * 0.9  # Chine slightly inboard of max beam
        chine_z = -draft + chine_y * math.tan(deadrise_rad)

        chine = SectionPoint(
            position=Point3D(
                x=station * definition.dimensions.lwl, y=chine_y, z=chine_z
            ),
            is_chine=True,
        )

        # Points from keel to chine (V-bottom)
        for i in range(1, num_points // 2):
            t = i / (num_points // 2)
            y = t * chine_y
            z = -draft + y * math.tan(deadrise_rad)
            points.append(
                SectionPoint(
                    position=Point3D(x=station * definition.dimensions.lwl, y=y, z=z)
                )
            )

        points.append(chine)

        # Points from chine to deck
        deck_z = definition.dimensions.depth - draft
        flare_angle = math.radians(definition.features.bow_flare_deg * (1 - station))

        for i in range(1, num_points // 2):
            t = i / (num_points // 2)
            y = chine_y + t * (half_beam - chine_y)
            z = chine_z + t * (deck_z - chine_z)
            # Add flare
            y += t * t * math.tan(flare_angle) * (deck_z - chine_z)
            points.append(
                SectionPoint(
                    position=Point3D(x=station * definition.dimensions.lwl, y=y, z=z)
                )
            )

        # Deck edge
        deck_edge = SectionPoint(
            position=Point3D(
                x=station * definition.dimensions.lwl, y=half_beam, z=deck_z
            )
        )
        points.append(deck_edge)

        return points

    def _generate_round_section(
        self,
        half_beam: float,
        draft: float,
        definition: HullDefinition,
        station: float,
    ) -> List[SectionPoint]:
        """Generate round bilge section profile."""
        points = []
        num_points = self.config.points_per_section

        # Use elliptical section approximation
        # Semi-axes: a = half_beam, b = draft

        for i in range(num_points):
            # Parametric angle from keel (bottom) to deck
            theta = i / (num_points - 1) * math.pi / 2

            y = half_beam * math.sin(theta)
            z_underwater = -draft * math.cos(theta)

            # Above waterline, transition to vertical
            if z_underwater > 0:
                deck_z = definition.dimensions.depth - draft
                t = z_underwater / deck_z
                z = z_underwater
            else:
                z = z_underwater

            points.append(
                SectionPoint(
                    position=Point3D(x=station * definition.dimensions.lwl, y=y, z=z),
                    is_keel=(i == 0),
                )
            )

        return points

    def _generate_generic_section(
        self,
        half_beam: float,
        draft: float,
        deadrise: float,
        definition: HullDefinition,
        station: float,
    ) -> List[SectionPoint]:
        """Generate generic section profile."""
        # Default to chine section
        return self._generate_chine_section(
            half_beam, draft, deadrise, definition, station
        )

    def _get_half_beam_at_station(
        self, definition: HullDefinition, station: float
    ) -> float:
        """Get half-beam at longitudinal station."""
        beam_wl = definition.dimensions.beam_wl / 2

        # Sectional area curve approximation
        # Entrance region (bow) narrows
        # Parallel middle body
        # Run (stern) narrows

        cp = definition.coefficients.cp
        lcb = definition.coefficients.lcb

        if station < 0.1:
            # Bow entrance - narrowing
            t = station / 0.1
            return beam_wl * t * t
        elif station < lcb:
            # Forward of LCB - gradual increase
            t = (station - 0.1) / (lcb - 0.1)
            return beam_wl * (0.01 + 0.99 * t ** 0.5)
        elif station < 0.9:
            # Aft of LCB - gradual decrease
            t = (station - lcb) / (0.9 - lcb)
            return beam_wl * (1.0 - 0.2 * t ** 2)
        else:
            # Transom - may be full or reduced
            t = (station - 0.9) / 0.1
            transom_fraction = definition.features.transom_width_fraction
            return beam_wl * (1.0 - (1 - transom_fraction) * t)

    def _get_draft_at_station(
        self, definition: HullDefinition, station: float
    ) -> float:
        """Get draft at longitudinal station."""
        draft_fwd = definition.dimensions.draft_fwd
        draft_aft = definition.dimensions.draft_aft

        if draft_fwd == 0:
            draft_fwd = definition.dimensions.draft
        if draft_aft == 0:
            draft_aft = definition.dimensions.draft

        # Linear interpolation with trim
        return draft_aft + station * (draft_fwd - draft_aft)

    def _find_waterline_point(
        self, points: List[SectionPoint], waterline_z: float
    ) -> Optional[Point3D]:
        """Find point where section crosses waterline."""
        for i in range(len(points) - 1):
            z1 = points[i].position.z
            z2 = points[i + 1].position.z

            if z1 <= waterline_z <= z2 or z2 <= waterline_z <= z1:
                t = (waterline_z - z1) / (z2 - z1) if z2 != z1 else 0
                p1 = points[i].position
                p2 = points[i + 1].position
                return Point3D(
                    x=p1.x + t * (p2.x - p1.x),
                    y=p1.y + t * (p2.y - p1.y),
                    z=waterline_z,
                )
        return None

    def _generate_waterlines(
        self, definition: HullDefinition, sections: List[HullSection]
    ) -> List[Waterline]:
        """Generate waterline cuts."""
        waterlines = []
        num_wl = self.config.num_waterlines
        draft = definition.dimensions.draft

        for i in range(num_wl):
            z = -draft + (i / (num_wl - 1)) * draft

            wl = Waterline(z_position=z)

            # Get points from each section at this height
            for section in sections:
                point = section.get_point_at_z(z)
                if point:
                    wl.points.append(point)

            if wl.points:
                wl.compute_properties()
                waterlines.append(wl)

        return waterlines

    def _generate_keel_profile(self, definition: HullDefinition) -> List[Point3D]:
        """Generate keel profile curve."""
        points = []
        lwl = definition.dimensions.lwl

        for i in range(self.config.num_sections):
            station = i / (self.config.num_sections - 1)
            x = station * lwl
            z = -self._get_draft_at_station(definition, station)
            points.append(Point3D(x=x, y=0, z=z))

        return points

    def _generate_stem_profile(self, definition: HullDefinition) -> List[Point3D]:
        """Generate stem (bow) profile curve."""
        points = []
        lwl = definition.dimensions.lwl
        draft = definition.dimensions.draft_fwd or definition.dimensions.draft
        deck_z = definition.dimensions.depth - definition.dimensions.draft

        stem_rake_rad = math.radians(definition.features.stem_rake_deg)

        num_points = 20
        for i in range(num_points):
            t = i / (num_points - 1)
            z = -draft + t * (deck_z + draft)

            # Rake increases with height
            x_offset = z * math.tan(stem_rake_rad) if z > 0 else 0
            x = lwl + x_offset

            points.append(Point3D(x=x, y=0, z=z))

        return points

    def _generate_chine_curve(
        self, definition: HullDefinition, sections: List[HullSection]
    ) -> List[Point3D]:
        """Generate chine curve from sections."""
        points = []
        for section in sections:
            if section.chine_point:
                points.append(section.chine_point)
        return points

    def _generate_transom(self, definition: HullDefinition) -> List[Point3D]:
        """Generate transom outline."""
        points = []
        draft = definition.dimensions.draft_aft or definition.dimensions.draft
        deck_z = definition.dimensions.depth - definition.dimensions.draft
        half_beam = definition.dimensions.beam_max / 2 * definition.features.transom_width_fraction

        # Generate transom profile (U or V shape)
        num_points = 20
        for i in range(num_points):
            t = i / (num_points - 1)
            y = half_beam * math.sin(t * math.pi / 2)
            z = -draft + (deck_z + draft) * t

            points.append(Point3D(x=0, y=y, z=z))

        return points

    def _compute_waterplane_area(
        self, definition: HullDefinition, geometry: HullGeometry
    ) -> float:
        """Compute waterplane area at design draft."""
        if geometry.waterlines:
            # Find waterline at z=0 (design waterline)
            for wl in geometry.waterlines:
                if abs(wl.z_position) < 0.01:
                    return wl.area

        # Estimate from coefficients
        return (
            definition.coefficients.cwp
            * definition.dimensions.lwl
            * definition.dimensions.beam_wl
        )

    def _estimate_wetted_surface(self, definition: HullDefinition) -> float:
        """Estimate wetted surface area."""
        # Denny-Mumford approximation for high-speed craft
        lwl = definition.dimensions.lwl
        beam = definition.dimensions.beam_wl
        draft = definition.dimensions.draft
        cb = definition.coefficients.cb

        # S = LWL * (2*T + B) * sqrt(Cb) * k
        # k typically 0.85-0.95 for aluminum craft
        k = 0.90
        wetted_surface = lwl * (2 * draft + beam) * math.sqrt(cb) * k

        return wetted_surface


def generate_hull_from_parameters(
    lwl: float,
    beam: float,
    draft: float,
    hull_type: HullType = HullType.HARD_CHINE,
    deadrise_deg: float = 18.0,
) -> HullGeometry:
    """
    Convenience function to generate hull geometry.

    Args:
        lwl: Length on waterline (m)
        beam: Beam (m)
        draft: Draft (m)
        hull_type: Hull type
        deadrise_deg: Deadrise angle at transom (degrees)

    Returns:
        Generated hull geometry
    """
    definition = HullDefinition(
        hull_id=f"HULL-{lwl:.0f}M",
        hull_name=f"{lwl:.0f}m {hull_type.value} hull",
        hull_type=hull_type,
        dimensions=MainDimensions(
            loa=lwl * 1.08,
            lwl=lwl,
            lpp=lwl * 0.98,
            beam_max=beam,
            beam_wl=beam * 0.95,
            beam_chine=beam * 0.90,
            depth=draft * 2.2,
            draft=draft,
        ),
        coefficients=FormCoefficients.for_hull_type(hull_type),
        deadrise=DeadriseProfile.warped(deadrise_deg, deadrise_deg + 2, deadrise_deg + 25),
    )

    definition.compute_displacement()

    generator = HullGenerator()
    return generator.generate(definition)
