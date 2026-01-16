"""
hull_gen/generator.py - Parametric hull form generator.

BRAVO OWNS THIS FILE.

Module 16-18 v1.0 - Hull form generation from parameters.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .enums import HullType, ChineType, SectionShape, BowStyle
from .parameters import HullDefinition, MainDimensions, FormCoefficients, DeadriseProfile, HullFeatures, ChineConfig, BowConfig, TransomConfig
from .geometry import Point3D, SectionPoint, HullSection, Waterline, HullGeometry, EdgeType, LongitudinalFeature
from .bow_generator import BowGenerator, BowGeometry
from .transom_generator import TransomGenerator, TransomGeometry
from .deck_generator import DeckGenerator, DeckGeometry
from .modifiers import SprayRailModifier, KnuckleModifier, TumblehomeModifier


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
        self._bow_generator = BowGenerator()
        self._transom_generator = TransomGenerator()
        self._deck_generator = DeckGenerator()  # Phase 6
        self._bow_geometry: Optional[BowGeometry] = None
        self._transom_geometry: Optional[TransomGeometry] = None
        
        # Phase 4/6: Section modifiers (applied in order after base section generation)
        self._section_modifiers = [
            SprayRailModifier(),
            KnuckleModifier(),
            TumblehomeModifier(),  # Phase 6: Apply after spray rails and knuckles
        ]

    def generate(self, definition: HullDefinition) -> HullGeometry:
        """
        Generate hull geometry from definition.

        Args:
            definition: Hull definition parameters

        Returns:
            Complete hull geometry
        """
        geometry = HullGeometry(hull_id=definition.hull_id)

        # Generate sections (may use BowGenerator for non-traditional bow styles)
        geometry.sections = self._generate_sections(definition)
        
        # Copy bow panel edges if BowGenerator was used
        if self._bow_geometry and self._bow_geometry.panel_edges:
            geometry.bow_panel_edges = self._bow_geometry.panel_edges

        # Generate waterlines
        geometry.waterlines = self._generate_waterlines(definition, geometry.sections)

        # Generate key curves
        geometry.keel_profile = self._generate_keel_profile(definition)
        
        # Use bow generator's stem curve if available
        if self._bow_geometry and self._bow_geometry.stem_curve:
            geometry.stem_profile = self._bow_geometry.stem_curve
        else:
            geometry.stem_profile = self._generate_stem_profile(definition)
            
        geometry.chine_curve = self._generate_chine_curve(definition, geometry.sections)
        
        # Phase 5: Generate transom using TransomGenerator for parametric transoms
        geometry.transom_outline = self._generate_transom(definition)
        
        # Store transom hard edges if generated
        if self._transom_geometry and self._transom_geometry.hard_edges:
            geometry.transom_hard_edges = [
                (e.start_vertex_idx, e.end_vertex_idx, e.feature_id)
                for e in self._transom_geometry.hard_edges
            ]

        # Compute properties
        geometry.compute_volume()
        geometry.waterplane_area = self._compute_waterplane_area(definition, geometry)
        geometry.wetted_surface = self._estimate_wetted_surface(definition)
        
        # Phase 4: Collect longitudinal features for mesh rendering
        geometry.longitudinal_features = self._collect_longitudinal_features(geometry.sections)
        
        # Phase 6: Generate deck surface if enabled
        features = definition.features or HullFeatures()
        deck_config = features.get_deck_config()
        if deck_config.enabled:
            geometry.deck_geometry = self._deck_generator.generate(
                geometry.sections, deck_config, definition
            )
        
        # Clear geometry references after generation
        self._bow_geometry = None
        self._transom_geometry = None

        return geometry

    def _generate_sections(self, definition: HullDefinition) -> List[HullSection]:
        """Generate transverse sections."""
        if definition.hull_type == HullType.CATAMARAN:
            return self._generate_catamaran_sections(definition)
        else:
            return self._generate_monohull_sections(definition)

    def _generate_monohull_sections(self, definition: HullDefinition) -> List[HullSection]:
        """
        Generate sections for monohull.
        
        v1.3: Uses BowGenerator for non-traditional bow styles.
        """
        features = definition.features or HullFeatures()
        bow_config = features.get_bow_config()
        
        # Check if we should use specialized bow generation
        use_bow_generator = bow_config.style != BowStyle.TRADITIONAL
        
        if use_bow_generator:
            return self._generate_sections_with_bow(definition, bow_config)
        else:
            return self._generate_standard_sections(definition)
    
    def _generate_standard_sections(self, definition: HullDefinition) -> List[HullSection]:
        """Generate all sections using standard (traditional bow) approach."""
        sections = []
        lwl = definition.dimensions.lwl
        num_sections = self.config.num_sections

        for i in range(num_sections):
            station = i / (num_sections - 1)
            x_pos = station * lwl

            section = self._generate_section_at_station(definition, station, x_pos)
            sections.append(section)

        return sections
    
    def _generate_sections_with_bow(
        self,
        definition: HullDefinition,
        bow_config: BowConfig,
    ) -> List[HullSection]:
        """
        Generate sections using BowGenerator for bow region.
        
        Bow region (forward) is generated by BowGenerator.
        Main body is generated by standard approach.
        """
        lwl = definition.dimensions.lwl
        bow_region_length = bow_config.region_length
        num_sections = self.config.num_sections
        
        # Calculate how many sections for bow vs main body
        num_bow_sections = max(3, int(num_sections * bow_region_length) + 1)
        num_main_sections = num_sections - num_bow_sections + 1  # +1 for overlap at transition
        
        # Generate bow sections using BowGenerator
        self._bow_geometry = self._bow_generator.generate(
            definition, bow_config, num_sections=num_bow_sections
        )
        bow_sections = self._bow_geometry.sections
        
        # Generate main body sections (from end of bow region to stern)
        main_sections = []
        start_station = 1.0 - bow_region_length  # Station where main body starts
        
        for i in range(num_main_sections):
            # Progress from transition point to stern (station 0)
            t = i / (num_main_sections - 1) if num_main_sections > 1 else 0
            station = start_station * (1 - t)  # Goes from start_station down to 0
            x_pos = station * lwl
            
            section = self._generate_section_at_station(definition, station, x_pos)
            main_sections.append(section)
        
        # Combine: main body (stern to transition) + bow (transition to FP)
        # Main sections are from stern (station 0) to transition
        # Bow sections are from transition to FP (station 1)
        # Reverse main sections so they're in order (low station to high station)
        main_sections.reverse()
        
        # Skip the first main section (transition) to avoid duplicate
        all_sections = main_sections[:-1] + bow_sections
        
        return all_sections

    def _generate_catamaran_sections(self, definition: HullDefinition) -> List[HullSection]:
        """
        Generate sections for catamaran.

        Catamaran has two demihulls offset from centerline.
        Each demihull is slender (beam = total_beam / 4 typical).

        The sections represent the PORT demihull only (y > 0).
        The tessellator will mirror to create the starboard demihull.
        """
        import logging
        logger = logging.getLogger("hull_gen.generator")

        sections = []
        lwl = definition.dimensions.lwl
        num_sections = self.config.num_sections

        # Get hull spacing (distance between hull centerlines)
        hull_spacing = definition.features.hull_spacing
        if hull_spacing <= 0:
            # Default: spacing = 0.25 * LOA (typical for catamarans)
            hull_spacing = lwl * 0.25
            logger.debug(f"Using default hull_spacing: {hull_spacing:.2f}m")

        # Demihull beam is typically 1/4 of total beam (PROVISIONAL heuristic)
        demihull_beam = definition.dimensions.beam_max / 4

        # Validation: warn if demihull beam seems unreasonable
        if demihull_beam < 0.1 * definition.dimensions.beam_max:
            logger.warning(f"Demihull beam ({demihull_beam:.2f}m) unusually narrow — check hull_spacing")
        if demihull_beam > 0.4 * definition.dimensions.beam_max:
            logger.warning(f"Demihull beam ({demihull_beam:.2f}m) unusually wide for catamaran")

        # Generate sections for PORT demihull (y > 0)
        # Demihull centerline at y = +hull_spacing/2
        port_offset = hull_spacing / 2

        for i in range(num_sections):
            station = i / (num_sections - 1)
            x_pos = station * lwl

            # Generate demihull section (narrower beam)
            section = self._generate_demihull_section(
                definition, station, x_pos, demihull_beam, port_offset
            )
            sections.append(section)

        return sections

    def _generate_demihull_section(
        self,
        definition: HullDefinition,
        station: float,
        x_pos: float,
        demihull_beam: float,
        y_offset: float,
    ) -> HullSection:
        """
        Generate section for a single demihull.

        The section is generated centered at y=y_offset.
        Points go from keel (centerline of demihull) outward.
        
        v1.1: Sets EdgeType.HARD on chine points when ChineType is HARD/SINGLE.
        """
        section = HullSection(station=station, x_position=x_pos)

        draft = self._get_draft_at_station(definition, station)
        deadrise = definition.deadrise.get_deadrise_at(station)

        # Local beam for this station (scaled to demihull)
        local_demihull_half_beam = demihull_beam / 2

        # Apply longitudinal beam variation
        beam_factor = self._get_beam_factor_at_station(definition, station)
        local_demihull_half_beam *= beam_factor

        section.half_beam = local_demihull_half_beam
        section.draft_local = draft
        section.deadrise_deg = deadrise

        points = []
        num_points = self.config.points_per_section

        deadrise_rad = math.radians(deadrise)
        deck_z = definition.dimensions.depth - draft
        # Coefficients drive section fullness (match monohull behavior).
        cb = definition.coefficients.cb or 0.45
        cm = definition.coefficients.cm or 0.70
        cb = max(0.30, min(0.95, cb))
        cm = max(0.70, min(1.00, cm))
        cb_norm = (cb - 0.35) / (0.60 - 0.35)
        cm_norm = (cm - 0.70) / (0.90 - 0.70)
        cb_norm = max(0.0, min(1.0, cb_norm))
        cm_norm = max(0.0, min(1.0, cm_norm))
        fullness = max(0.0, min(1.0, 0.7 * cb_norm + 0.3 * cm_norm))
        bottom_exp = 1.4 + 6.0 * fullness
        deadrise_scale = 1.0 - 0.7 * fullness

        # v1.1: Determine edge type for chine based on ChineType
        chine_type = definition.features.chine_type if definition.features else ChineType.SOFT
        chine_edge_type = EdgeType.HARD if chine_type in (ChineType.HARD, ChineType.SINGLE) else EdgeType.SMOOTH

        # Generate points from keel to deck for the demihull
        # Keel point (at demihull centerline, offset from ship centerline)
        keel = SectionPoint(
            position=Point3D(x=x_pos, y=y_offset, z=-draft),
            is_keel=True,
            edge_type=EdgeType.SMOOTH,
        )
        points.append(keel)

        # Points from keel outward (increasing y)
        for i in range(1, num_points):
            t = i / (num_points - 1)

            # Y increases from demihull centerline to outer edge
            y = y_offset + t * local_demihull_half_beam

            # Z follows chine/round profile
            if t < 0.5:
                # Bottom section - deadrise with fullness shaping
                u = t * 2.0  # 0..1 over the bottom
                y_local = u * local_demihull_half_beam
                z_v = -draft + y_local * math.tan(deadrise_rad) * deadrise_scale
                bottom_top_z = -draft + local_demihull_half_beam * math.tan(deadrise_rad) * deadrise_scale
                z_flat = -draft + (u ** bottom_exp) * (bottom_top_z + draft)
                z = (1.0 - fullness) * z_v + fullness * z_flat
            else:
                # Upper section - transition to deck
                bottom_top_z = -draft + local_demihull_half_beam * math.tan(deadrise_rad) * deadrise_scale
                z = bottom_top_z + (t - 0.5) * 2 * (deck_z - bottom_top_z)

            is_chine = (0.45 < t < 0.55)  # Mark chine region
            
            # v1.1: Set edge type on chine points
            point_edge_type = chine_edge_type if is_chine else EdgeType.SMOOTH
            feature_id = "chine_main" if (is_chine and chine_edge_type == EdgeType.HARD) else None
            
            points.append(SectionPoint(
                position=Point3D(x=x_pos, y=y, z=z),
                is_chine=is_chine,
                edge_type=point_edge_type,
                feature_id=feature_id,
            ))

        section.points = points
        section.compute_area(0.0)

        return section

    def _get_beam_factor_at_station(self, definition: HullDefinition, station: float) -> float:
        """
        Get beam variation factor at station (0-1 range).

        Coordinate frame: station=0 at AP (stern), station=1 at FP (bow).
        """
        # LCB is an explicit engineering input (fraction from AP); clamp for stability.
        lcb = max(0.35, min(0.75, definition.coefficients.lcb))

        # Cp drives longitudinal fullness (higher Cp → fuller ends, less taper)
        cp = definition.coefficients.cp or 0.65
        cp = max(0.5, min(0.95, cp))
        cp_norm = (cp - 0.5) / (0.95 - 0.5)  # 0..1

        transom_fraction = definition.features.transom_width_fraction
        # Bow entrance angle modulates how sharp the waterline entry is.
        # Smaller angle → sharper/narrower bow; larger angle → blunter/wider bow.
        entrance_deg = getattr(definition.features, "bow_entrance_deg", 25.0) or 25.0
        entrance_deg = max(5.0, min(45.0, float(entrance_deg)))
        entrance_norm = (entrance_deg - 5.0) / (45.0 - 5.0)  # 0..1

        # Bow end factor: minimum beam fraction at the stem (Cp + entrance controlled)
        bow_end_base = 0.02 + 0.43 * cp_norm  # 0.02..0.45
        bow_end = bow_end_base * (0.30 + 0.70 * entrance_norm)

        if station < 0.1:
            # Transom area (stern) - starts at transom fraction
            t = station / 0.1
            return transom_fraction + (1.0 - transom_fraction) * t
        elif station < lcb:
            # Run (aft of midship) - full beam
            return 1.0
        elif station < 0.9:
            # Forward of LCB - gradual reduction toward bow
            t = (station - lcb) / (0.9 - lcb)
            return 1.0 - 0.1 * t
        else:
            # Bow entrance - narrows to fine entry
            t = (station - 0.9) / 0.1
            return 0.9 - (0.9 - bow_end) * t ** 1.5

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
            
        v1.2: Dispatches to appropriate chine generator based on ChineType.
        """
        section = HullSection(station=station, x_position=x_pos)

        # Get section properties
        half_beam = self._get_half_beam_at_station(definition, station)
        draft = self._get_draft_at_station(definition, station)
        deadrise = definition.deadrise.get_deadrise_at(station)

        section.half_beam = half_beam
        section.draft_local = draft
        section.deadrise_deg = deadrise

        # Get chine type from features
        features = definition.features or HullFeatures()
        chine_type = features.chine_type
        chine_style = features.chine_style
        
        # v1.2: Dispatch based on chine type and style
        if chine_style == "variable" or chine_type == ChineType.VARIABLE:
            points = self._generate_variable_chine_section(
                half_beam, draft, deadrise, definition, station
            )
        elif chine_style == "reverse" or chine_type == ChineType.REVERSE:
            points = self._generate_reverse_chine_section(
                half_beam, draft, deadrise, definition, station
            )
        elif chine_type in (ChineType.DOUBLE, ChineType.TRIPLE):
            points = self._generate_multi_chine_section(
                half_beam, draft, deadrise, definition, station
            )
        elif definition.hull_type == HullType.ROUND_BILGE or chine_type in (ChineType.NONE, ChineType.SOFT):
            points = self._generate_round_section(half_beam, draft, definition, station)
        elif definition.hull_type in [HullType.DEEP_V_PLANING, HullType.HARD_CHINE] or chine_type in (ChineType.HARD, ChineType.SINGLE):
            points = self._generate_chine_section(
                half_beam, draft, deadrise, definition, station
            )
        else:
            points = self._generate_generic_section(
                half_beam, draft, deadrise, definition, station
            )

        # Phase 4: Apply section modifiers (spray rails, knuckles, etc.)
        for modifier in self._section_modifiers:
            points = modifier.modify(points, station, definition)

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
        """
        Generate hard-chine section profile.
        
        v1.1: Sets EdgeType.HARD on chine points when ChineType is HARD/SINGLE.
        """
        points = []
        num_points = self.config.points_per_section

        deadrise_rad = math.radians(deadrise)
        # Coefficients drive section fullness.
        # Higher Cb/Cm → flatter, fuller bottom; lower values → finer V.
        cb = definition.coefficients.cb or 0.45
        cm = definition.coefficients.cm or 0.70
        cb = max(0.30, min(0.95, cb))
        cm = max(0.70, min(1.00, cm))
        # Normalize into a sensitive operating band so small coefficient deltas
        # produce visible geometry changes.
        # - Cb: 0.35..0.60 is the primary "fullness" range
        # - Cm: 0.70..0.90 refines midship section shape
        cb_norm = (cb - 0.35) / (0.60 - 0.35)  # unclamped
        cm_norm = (cm - 0.70) / (0.90 - 0.70)  # unclamped
        cb_norm = max(0.0, min(1.0, cb_norm))
        cm_norm = max(0.0, min(1.0, cm_norm))
        fullness = max(0.0, min(1.0, 0.7 * cb_norm + 0.3 * cm_norm))

        # v1.1: Determine edge type for chine based on ChineType
        chine_type = definition.features.chine_type if definition.features else ChineType.SOFT
        chine_edge_type = EdgeType.HARD if chine_type in (ChineType.HARD, ChineType.SINGLE) else EdgeType.SMOOTH

        # Keel point
        keel = SectionPoint(
            position=Point3D(x=station * definition.dimensions.lwl, y=0, z=-draft),
            is_keel=True,
            edge_type=EdgeType.SMOOTH,  # Keel is always smooth
        )
        points.append(keel)

        # Chine point
        chine_y_ratio = 0.75 + 0.20 * fullness  # 0.75..0.95 (fuller hull → chine farther out)
        chine_y = half_beam * chine_y_ratio
        deadrise_scale = 1.0 - 0.7 * fullness  # fuller hull → flatter bottom
        chine_z = -draft + chine_y * math.tan(deadrise_rad) * deadrise_scale

        chine = SectionPoint(
            position=Point3D(
                x=station * definition.dimensions.lwl, y=chine_y, z=chine_z
            ),
            is_chine=True,
            edge_type=chine_edge_type,  # v1.1: Set edge type based on ChineType
            feature_id="chine_main" if chine_edge_type == EdgeType.HARD else None,
        )

        # Points from keel to chine (fullness-aware bottom)
        bottom_exp = 1.4 + 6.0 * fullness  # ~1.4..7.4 (fuller hull → flatter bottom)
        for i in range(1, num_points // 2):
            t = i / (num_points // 2)
            y = t * chine_y
            z_v = -draft + y * math.tan(deadrise_rad) * deadrise_scale
            z_flat = -draft + (t ** bottom_exp) * (chine_z + draft)
            z = (1.0 - fullness) * z_v + fullness * z_flat
            points.append(
                SectionPoint(
                    position=Point3D(x=station * definition.dimensions.lwl, y=y, z=z),
                    edge_type=EdgeType.SMOOTH,  # Bottom points are smooth
                )
            )

        points.append(chine)

        # Points from chine to deck
        deck_z = definition.dimensions.depth - draft
        # Bow flare should be strongest toward the bow (station→1.0).
        flare_angle = math.radians(definition.features.bow_flare_deg * station)

        for i in range(1, num_points // 2):
            t = i / (num_points // 2)
            y = chine_y + t * (half_beam - chine_y)
            z = chine_z + t * (deck_z - chine_z)
            # Add flare
            y += (t * (1.0 - t)) * math.tan(flare_angle) * (deck_z - chine_z)
            points.append(
                SectionPoint(
                    position=Point3D(x=station * definition.dimensions.lwl, y=y, z=z),
                    edge_type=EdgeType.SMOOTH,  # Topsides are smooth
                )
            )

        # Deck edge
        deck_edge = SectionPoint(
            position=Point3D(
                x=station * definition.dimensions.lwl, y=half_beam, z=deck_z
            ),
            edge_type=EdgeType.SMOOTH,
        )
        points.append(deck_edge)

        return points

    # =========================================================================
    # Phase 2: Multi-Chine, Reverse Chine, Variable Chine Generators
    # =========================================================================

    def _generate_multi_chine_section(
        self,
        half_beam: float,
        draft: float,
        deadrise: float,
        definition: HullDefinition,
        station: float,
    ) -> List[SectionPoint]:
        """
        Generate section with multiple chines (double or triple).
        
        Phase 2: Builds section from keel upward, inserting chine points
        at configured heights with appropriate edge types.
        """
        points = []
        features = definition.features or HullFeatures()
        chine_configs = features.get_chine_configs()
        
        # Filter chines active at this station
        active_chines = [
            c for c in chine_configs
            if c.start_station <= station <= c.end_station
        ]
        
        deck_z = definition.dimensions.depth - draft
        x_pos = station * definition.dimensions.lwl
        
        # Keel point
        points.append(SectionPoint(
            position=Point3D(x=x_pos, y=0, z=-draft),
            is_keel=True,
            edge_type=EdgeType.SMOOTH,
        ))
        
        if not active_chines:
            # No active chines at this station, generate round section
            return self._generate_round_section(half_beam, draft, definition, station)
        
        # Sort chines by height
        active_chines = sorted(active_chines, key=lambda c: c.height_ratio)
        
        current_y = 0.0
        current_z = -draft
        num_points_per_segment = max(3, self.config.points_per_section // (len(active_chines) + 2))
        
        # Generate segments between chines
        for i, chine in enumerate(active_chines):
            # Calculate chine position
            chine_z = -draft + chine.height_ratio * draft
            
            # Y at chine based on angle
            if abs(chine.angle_deg) > 1:
                dz = chine_z - current_z
                dy = abs(dz) / math.tan(math.radians(abs(chine.angle_deg)))
                if chine.angle_deg < 0:  # Reverse angle
                    dy = -dy * 0.5  # Extend outward less for reverse
                chine_y = min(half_beam * 0.95, current_y + dy)
            else:
                chine_y = current_y
            
            # Points from current position to chine
            for j in range(1, num_points_per_segment):
                t = j / num_points_per_segment
                y = current_y + t * (chine_y - current_y)
                z = current_z + t * (chine_z - current_z)
                points.append(SectionPoint(
                    position=Point3D(x=x_pos, y=y, z=z),
                    edge_type=EdgeType.SMOOTH,
                ))
            
            # Chine point(s)
            chine_edge_type = EdgeType.HARD if chine.is_hard else EdgeType.SMOOTH
            
            if chine.flat_width_m > 0:
                # Inner edge of chine flat
                points.append(SectionPoint(
                    position=Point3D(x=x_pos, y=chine_y, z=chine_z),
                    is_chine=True,
                    edge_type=chine_edge_type,
                    feature_id=f"chine_{i}_inner",
                ))
                # Outer edge of chine flat
                outer_y = min(half_beam * 0.98, chine_y + chine.flat_width_m)
                points.append(SectionPoint(
                    position=Point3D(x=x_pos, y=outer_y, z=chine_z),
                    is_chine=True,
                    edge_type=chine_edge_type,
                    feature_id=f"chine_{i}_outer",
                ))
                current_y = outer_y
            else:
                points.append(SectionPoint(
                    position=Point3D(x=x_pos, y=chine_y, z=chine_z),
                    is_chine=True,
                    edge_type=chine_edge_type,
                    feature_id=f"chine_{i}",
                ))
                current_y = chine_y
            
            current_z = chine_z
        
        # Points from last chine to deck
        flare_angle = math.radians(features.bow_flare_deg * station)
        for j in range(1, num_points_per_segment + 1):
            t = j / num_points_per_segment
            y = current_y + t * (half_beam - current_y)
            z = current_z + t * (deck_z - current_z)
            # Add flare
            y += (t * (1.0 - t)) * math.tan(flare_angle) * (deck_z - current_z)
            y = min(half_beam, y)
            points.append(SectionPoint(
                position=Point3D(x=x_pos, y=y, z=z),
                edge_type=EdgeType.SMOOTH,
            ))
        
        return points

    def _generate_reverse_chine_section(
        self,
        half_beam: float,
        draft: float,
        deadrise: float,
        definition: HullDefinition,
        station: float,
    ) -> List[SectionPoint]:
        """
        Generate section with reverse (outward-angled) chine.
        
        Phase 2: Reverse chines extend outward, creating a sponson-like
        effect that improves stability and spray deflection.
        
              │
              │   ┌── Reverse chine extends outward
              │  ╱
            ──┼─╱────  Waterline
              │╲
              │ ╲
              │  ╲
              └───────
                 Hull bottom
        """
        points = []
        features = definition.features or HullFeatures()
        
        x_pos = station * definition.dimensions.lwl
        deck_z = definition.dimensions.depth - draft
        
        reverse_height_ratio = features.reverse_chine_height_ratio
        reverse_extension = features.reverse_chine_extension_m
        
        deadrise_rad = math.radians(deadrise)
        num_points = self.config.points_per_section
        
        # Keel point
        points.append(SectionPoint(
            position=Point3D(x=x_pos, y=0, z=-draft),
            is_keel=True,
            edge_type=EdgeType.SMOOTH,
        ))
        
        # Bottom section up to reverse chine height
        chine_z = -draft + reverse_height_ratio * draft
        
        # Calculate Y at chine using deadrise
        if abs(deadrise) > 1:
            base_y = abs(chine_z + draft) / math.tan(deadrise_rad) if deadrise_rad > 0.01 else half_beam * 0.6
        else:
            base_y = half_beam * 0.6
        base_y = min(half_beam * 0.7, base_y)
        
        # Points from keel to chine
        bottom_points = num_points // 3
        for i in range(1, bottom_points):
            t = i / bottom_points
            y = t * base_y
            z = -draft + y * math.tan(deadrise_rad)
            z = min(chine_z, z)
            points.append(SectionPoint(
                position=Point3D(x=x_pos, y=y, z=z),
                edge_type=EdgeType.SMOOTH,
            ))
        
        # Reverse chine - inner edge (where bottom meets reverse)
        points.append(SectionPoint(
            position=Point3D(x=x_pos, y=base_y, z=chine_z),
            is_chine=True,
            edge_type=EdgeType.HARD,
            feature_id="reverse_chine_inner",
        ))
        
        # Reverse chine - tip (maximum outward extension)
        tip_y = base_y + reverse_extension
        tip_z = chine_z + reverse_extension * 0.2  # Slight upward angle
        points.append(SectionPoint(
            position=Point3D(x=x_pos, y=tip_y, z=tip_z),
            is_chine=True,
            edge_type=EdgeType.HARD,
            feature_id="reverse_chine_tip",
        ))
        
        # Reverse chine - outer edge (where reverse meets topside)
        outer_y = base_y + reverse_extension * 0.5
        outer_z = tip_z + reverse_extension * 0.3
        points.append(SectionPoint(
            position=Point3D(x=x_pos, y=outer_y, z=outer_z),
            is_chine=True,
            edge_type=EdgeType.HARD,
            feature_id="reverse_chine_outer",
        ))
        
        # Topside to deck
        flare_angle = math.radians(features.bow_flare_deg * station)
        topside_points = num_points // 3
        for i in range(1, topside_points + 1):
            t = i / topside_points
            y = outer_y + t * (half_beam - outer_y)
            z = outer_z + t * (deck_z - outer_z)
            y += (t * (1.0 - t)) * math.tan(flare_angle) * (deck_z - outer_z)
            y = min(half_beam, y)
            points.append(SectionPoint(
                position=Point3D(x=x_pos, y=y, z=z),
                edge_type=EdgeType.SMOOTH,
            ))
        
        return points

    def _generate_variable_chine_section(
        self,
        half_beam: float,
        draft: float,
        deadrise: float,
        definition: HullDefinition,
        station: float,
    ) -> List[SectionPoint]:
        """
        Generate section with variable chine (soft→hard transition along length).
        
        Phase 2: Common on modern patrol boats - soft/round bow for seakeeping,
        hard chine aft for planing efficiency.
        """
        features = definition.features or HullFeatures()
        
        # Determine chine hardness at this station
        transition_start = features.chine_transition_start
        transition_end = features.chine_transition_end
        
        if station < transition_start:
            # Pure soft chine forward
            hardness = 0.0
        elif station > transition_end:
            # Pure hard chine aft
            hardness = 1.0
        else:
            # Transition zone - smooth interpolation
            t = (station - transition_start) / max(0.01, transition_end - transition_start)
            hardness = self._smooth_step(t)
        
        # Generate section based on hardness
        if hardness < 0.1:
            return self._generate_round_section(half_beam, draft, definition, station)
        elif hardness > 0.9:
            return self._generate_chine_section(half_beam, draft, deadrise, definition, station)
        else:
            return self._generate_blended_chine_section(
                half_beam, draft, deadrise, definition, station, hardness
            )

    def _smooth_step(self, t: float) -> float:
        """Smooth step function for transitions (Hermite interpolation)."""
        t = max(0.0, min(1.0, t))
        return t * t * (3.0 - 2.0 * t)

    def _generate_blended_chine_section(
        self,
        half_beam: float,
        draft: float,
        deadrise: float,
        definition: HullDefinition,
        station: float,
        hardness: float,
    ) -> List[SectionPoint]:
        """
        Generate section with blended soft/hard chine.
        
        Phase 2: hardness 0.0 = pure round, 1.0 = pure hard chine.
        Interpolates positions and edge types between the two.
        """
        # Generate both soft and hard versions
        soft_points = self._generate_round_section(half_beam, draft, definition, station)
        hard_points = self._generate_chine_section(half_beam, draft, deadrise, definition, station)
        
        # Match point counts (use smaller)
        min_len = min(len(soft_points), len(hard_points))
        soft_points = soft_points[:min_len]
        hard_points = hard_points[:min_len]
        
        # Blend positions
        blended_points = []
        for soft, hard in zip(soft_points, hard_points):
            blended_pos = Point3D(
                x=soft.position.x,
                y=soft.position.y * (1.0 - hardness) + hard.position.y * hardness,
                z=soft.position.z * (1.0 - hardness) + hard.position.z * hardness,
            )
            
            # Edge type transitions from smooth to hard at 50% hardness
            is_chine_point = hard.is_chine and hardness > 0.5
            edge_type = EdgeType.HARD if is_chine_point else EdgeType.SMOOTH
            
            blended_points.append(SectionPoint(
                position=blended_pos,
                edge_type=edge_type,
                is_chine=is_chine_point,
                is_keel=soft.is_keel or hard.is_keel,
                feature_id=hard.feature_id if is_chine_point else None,
            ))
        
        return blended_points

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
        """
        Get half-beam at longitudinal station.

        Coordinate frame: station=0 at AP (stern), station=1 at FP (bow).
        - Station 0-0.1: Transom area (stern) - starts at transom width
        - Station 0.1-LCB: Run (aft body) - gradual increase toward midship
        - Station LCB-0.9: Parallel middle body and forward transition
        - Station 0.9-1.0: Entrance (bow) - narrows to fine entry
        """
        beam_wl = definition.dimensions.beam_wl / 2

        # Cp drives longitudinal fullness (higher Cp → fuller ends, less taper)
        cp = definition.coefficients.cp or 0.65
        cp = max(0.5, min(0.95, cp))
        cp_norm = (cp - 0.5) / (0.95 - 0.5)  # 0..1

        # LCB is an explicit engineering input (fraction from AP); clamp for stability.
        lcb = max(0.35, min(0.75, definition.coefficients.lcb))
        transom_fraction = definition.features.transom_width_fraction
        entrance_deg = getattr(definition.features, "bow_entrance_deg", 25.0) or 25.0
        entrance_deg = max(5.0, min(45.0, float(entrance_deg)))
        entrance_norm = (entrance_deg - 5.0) / (45.0 - 5.0)  # 0..1
        bow_end_base = 0.02 + 0.43 * cp_norm  # 0.02..0.45
        bow_end = bow_end_base * (0.30 + 0.70 * entrance_norm)

        if station < 0.1:
            # Transom area (stern) - starts at transom width, expands forward
            t = station / 0.1
            # At station=0 (transom): use transom_fraction
            # At station=0.1: full beam
            return beam_wl * (transom_fraction + (1.0 - transom_fraction) * t)
        elif station < lcb:
            # Run (aft of midship) - full beam region
            return beam_wl
        elif station < 0.9:
            # Forward of LCB - gradual reduction toward bow
            t = (station - lcb) / (0.9 - lcb)
            # Reduce to ~90% beam at station 0.9
            return beam_wl * (1.0 - 0.1 * t)
        else:
            # Bow entrance - narrows to fine entry
            t = (station - 0.9) / 0.1
            # Start at 90% beam (matching previous region), end at bow_end (Cp-controlled)
            return beam_wl * (0.9 - (0.9 - bow_end) * t ** 1.5)

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
        """
        Generate transom outline.
        
        Phase 5: Uses TransomGenerator for parametric transom configurations,
        falls back to simple generation for legacy/simple transoms.
        """
        features = definition.features or HullFeatures()
        transom_config = features.get_transom_config()
        
        # Use TransomGenerator for non-trivial transoms
        use_transom_generator = (
            transom_config.has_segments() or
            transom_config.has_cutouts() or
            transom_config.has_extensions() or
            transom_config.rake_profile is not None or
            transom_config.beam_profile is not None or
            transom_config.curvature != 0 or
            transom_config.corner_radius_m > 0
        )
        
        if use_transom_generator:
            return self._generate_transom_parametric(definition, transom_config)
        else:
            return self._generate_transom_simple(definition, transom_config)
    
    def _generate_transom_simple(
        self,
        definition: HullDefinition,
        config: TransomConfig,
    ) -> List[Point3D]:
        """
        Generate simple transom outline (legacy approach with rake support).
        """
        points = []
        draft = definition.dimensions.draft_aft or definition.dimensions.draft
        depth = definition.dimensions.depth
        deck_z = depth - draft
        half_beam = definition.dimensions.beam_max / 2 * config.beam_at_waterline_ratio
        
        # Apply rake angle
        rake_deg = config.rake_deg
        
        num_points = 20
        for i in range(num_points):
            t = i / (num_points - 1)
            height_ratio = t
            
            # Get beam at this height (interpolate waterline to deck)
            beam_ratio = config.get_beam_ratio_at_height(height_ratio)
            y = half_beam * beam_ratio * math.sin(t * math.pi / 2)
            
            # Calculate Z position
            z = -draft + (deck_z + draft) * t
            
            # Calculate X offset from rake
            height_from_keel = z + draft
            x = height_from_keel * math.tan(math.radians(rake_deg))
            
            points.append(Point3D(x=x, y=y, z=z))
        
        return points
    
    def _generate_transom_parametric(
        self,
        definition: HullDefinition,
        config: TransomConfig,
    ) -> List[Point3D]:
        """
        Generate transom using full TransomGenerator.
        
        Returns outline points from the generated transom section.
        """
        self._transom_geometry = self._transom_generator.generate(config, definition)
        
        # Extract outline points from the main transom section
        points = []
        for section_point in self._transom_geometry.section.points:
            points.append(section_point.position)
        
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

    def _collect_longitudinal_features(
        self, sections: List[HullSection]
    ) -> List[LongitudinalFeature]:
        """
        Collect longitudinal features from sections for mesh edge rendering.
        
        Phase 4: Scans sections for feature points (spray rails, knuckles) and
        groups them into LongitudinalFeature objects for the mesh pipeline.
        """
        from typing import Dict
        
        # Collect points by feature_id across all sections
        feature_points: Dict[str, List[Point3D]] = {}
        
        for section in sections:
            for point in section.points:
                fid = point.feature_id
                if fid and ("spray_rail" in fid or "knuckle" in fid):
                    if fid not in feature_points:
                        feature_points[fid] = []
                    feature_points[fid].append(point.position)
        
        # Create LongitudinalFeature objects
        features = []
        for feature_id, points in feature_points.items():
            if "spray_rail" in feature_id:
                feature_type = "spray_rail"
            elif "knuckle" in feature_id:
                feature_type = "knuckle"
            else:
                feature_type = "unknown"
            
            features.append(LongitudinalFeature(
                feature_type=feature_type,
                feature_id=feature_id,
                points=points,
                is_hard=True,
            ))
        
        return features

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
