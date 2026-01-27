"""
hull_gen/modifiers/spray_rail.py - Spray rail section modifier.

BRAVO OWNS THIS FILE.

Phase 4 Enhanced: Adds spray rails to hull sections with full parametric control:
- Variable width, angle, and height along length
- Multiple cross-section profiles (triangular, rounded, flat_top, sharp)
- Smooth tapering at rail ends
"""

import math
from typing import List, Tuple

from magnet.hull_gen.geometry import Point3D, SectionPoint, EdgeType
from magnet.hull_gen.parameters import HullDefinition, SprayRailConfig, HullFeatures
from magnet.hull_gen.modifiers.base import SectionModifier


class SprayRailModifier(SectionModifier):
    """
    Adds spray rails to hull sections with full parametric control.
    
    Spray rails are small horizontal or angled projections that:
    - Deflect spray away from the hull
    - Provide additional lift at speed
    - Create hard visual edges
    
    Cross-section profiles supported:
    
    TRIANGULAR (default):     ROUNDED:         FLAT_TOP:        SHARP:
            ╱                    ⌒                ─                ╱
           ╱                    ╱ ╲              ╱╲              ╱
          ╱────               ╱   ╲            ╱  ╲            ╱
         │                   │     │          │    │          │
         │                   │     │          │    │          │
    """
    
    def modify(
        self,
        points: List[SectionPoint],
        station: float,
        definition: HullDefinition,
    ) -> List[SectionPoint]:
        """Add spray rails to section points using parametric configuration."""
        features = definition.features
        if not features:
            return points
        
        # Get active spray rails at this station
        active_rails = features.get_active_spray_rails_at_station(station)
        if not active_rails:
            return points
        
        # Sort rails by height at this station (process from bottom to top)
        active_rails = sorted(active_rails, key=lambda r: r.get_height_at_station(station))
        
        # Get dimensions
        draft = definition.dimensions.draft
        lwl = definition.dimensions.lwl
        x_position = self._get_x_position(station, lwl)
        
        # Copy points and insert spray rails
        modified_points = list(points)
        
        for rail_idx, rail in enumerate(active_rails):
            # Get variable parameters at this station
            height_ratio = rail.get_height_at_station(station)
            width = rail.get_width_at_station(station)
            angle = rail.get_angle_at_station(station)
            
            # Skip if width is zero (fully tapered)
            if width <= 0:
                continue
            
            # Calculate rail Z position (relative to draft)
            rail_z = -draft + height_ratio * draft
            
            # Find where to insert rail points
            insert_idx = self._find_insertion_index(modified_points, rail_z)
            
            # Get Y at rail height by interpolation
            base_y = self._interpolate_y_at_z(modified_points, rail_z)
            
            # Create rail points based on profile type
            rail_points = self._create_rail_points(
                x_position=x_position,
                rail=rail,
                rail_z=rail_z,
                base_y=base_y,
                width=width,
                angle_deg=angle,
                rail_idx=rail_idx,
            )
            
            # Insert rail points
            for i, rp in enumerate(rail_points):
                modified_points.insert(insert_idx + i, rp)
        
        return modified_points
    
    def _create_rail_points(
        self,
        x_position: float,
        rail: SprayRailConfig,
        rail_z: float,
        base_y: float,
        width: float,
        angle_deg: float,
        rail_idx: int,
    ) -> List[SectionPoint]:
        """
        Create points for spray rail cross-section based on profile type.
        
        All profiles share bottom/top attachment points; the tip geometry varies.
        """
        profile = rail.profile.lower()
        
        if profile == "rounded":
            return self._create_rounded_profile(
                x_position, rail_z, base_y, width, angle_deg, rail_idx
            )
        elif profile == "flat_top":
            return self._create_flat_top_profile(
                x_position, rail_z, base_y, width, angle_deg, rail_idx
            )
        elif profile == "sharp":
            return self._create_sharp_profile(
                x_position, rail_z, base_y, width, angle_deg, rail_idx
            )
        else:  # Default: triangular
            return self._create_triangular_profile(
                x_position, rail_z, base_y, width, angle_deg, rail_idx
            )
    
    def _create_triangular_profile(
        self,
        x_position: float,
        rail_z: float,
        base_y: float,
        width: float,
        angle_deg: float,
        rail_idx: int,
    ) -> List[SectionPoint]:
        """
        Triangular profile: Simple V-shape with sharp tip.
        
            P1 (tip)
           ╱╲
          ╱  ╲
        P0    P2
        """
        points = []
        
        angle_rad = math.radians(angle_deg)
        rail_half_height = 0.02  # 2cm above and below rail center
        
        # P0: Bottom attachment
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z - rail_half_height),
            edge_type=EdgeType.HARD,
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_bottom",
        ))
        
        # P1: Tip (projects outward and up at angle)
        tip_y = base_y + width * math.cos(angle_rad)
        tip_z = rail_z + width * math.sin(angle_rad)
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=tip_y, z=tip_z),
            edge_type=EdgeType.HARD,
            is_chine=True,  # Mark as chine for hard edge rendering
            feature_id=f"spray_rail_{rail_idx}_tip",
        ))
        
        # P2: Top attachment
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z + rail_half_height),
            edge_type=EdgeType.HARD,
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_top",
        ))
        
        return points
    
    def _create_rounded_profile(
        self,
        x_position: float,
        rail_z: float,
        base_y: float,
        width: float,
        angle_deg: float,
        rail_idx: int,
    ) -> List[SectionPoint]:
        """
        Rounded profile: Arc from bottom to top with smooth transitions.
        
             ⌒
           ╱   ╲
          ╱     ╲
        P0       P4
        
        Uses 5 points to approximate an arc.
        """
        points = []
        
        angle_rad = math.radians(angle_deg)
        rail_half_height = 0.025  # Slightly taller for rounded profile
        
        # Arc parameters
        arc_segments = 3  # Number of intermediate points
        
        # P0: Bottom attachment
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z - rail_half_height),
            edge_type=EdgeType.SMOOTH,  # Smooth for rounded profile
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_bottom",
        ))
        
        # Intermediate arc points
        for i in range(1, arc_segments + 1):
            t = i / (arc_segments + 1)
            # Parabolic arc approximation
            arc_height = 4 * t * (1 - t)  # Peaks at t=0.5
            z_offset = rail_half_height * (2 * t - 1)  # -half to +half
            y_offset = width * arc_height * math.cos(angle_rad)
            z_arc = width * arc_height * math.sin(angle_rad)
            
            edge_type = EdgeType.HARD if t == 0.5 else EdgeType.SMOOTH
            
            points.append(SectionPoint(
                position=Point3D(
                    x=x_position,
                    y=base_y + y_offset,
                    z=rail_z + z_offset + z_arc,
                ),
                edge_type=edge_type,
                is_chine=(t == 0.5),  # Only mark apex as chine
                feature_id=f"spray_rail_{rail_idx}_arc_{i}",
            ))
        
        # P4: Top attachment
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z + rail_half_height),
            edge_type=EdgeType.SMOOTH,
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_top",
        ))
        
        return points
    
    def _create_flat_top_profile(
        self,
        x_position: float,
        rail_z: float,
        base_y: float,
        width: float,
        angle_deg: float,
        rail_idx: int,
    ) -> List[SectionPoint]:
        """
        Flat top profile: Trapezoidal with flat outer surface for max lift.
        
        P2─────P3
         ╲     ╱
          ╲   ╱
         P0   P4
        """
        points = []
        
        angle_rad = math.radians(angle_deg)
        rail_half_height = 0.02
        flat_width = width * 0.4  # 40% of width is flat top
        
        # P0: Bottom attachment
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z - rail_half_height),
            edge_type=EdgeType.HARD,
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_bottom",
        ))
        
        # P1: Bottom corner of flat
        bottom_corner_y = base_y + width * 0.7 * math.cos(angle_rad)
        bottom_corner_z = rail_z + width * 0.7 * math.sin(angle_rad) - flat_width * 0.5
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=bottom_corner_y, z=bottom_corner_z),
            edge_type=EdgeType.HARD,
            is_chine=True,
            feature_id=f"spray_rail_{rail_idx}_flat_bottom",
        ))
        
        # P2: Top corner of flat
        top_corner_y = base_y + width * math.cos(angle_rad)
        top_corner_z = rail_z + width * math.sin(angle_rad) + flat_width * 0.5
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=top_corner_y, z=top_corner_z),
            edge_type=EdgeType.HARD,
            is_chine=True,
            feature_id=f"spray_rail_{rail_idx}_flat_top",
        ))
        
        # P3: Top attachment
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z + rail_half_height),
            edge_type=EdgeType.HARD,
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_top",
        ))
        
        return points
    
    def _create_sharp_profile(
        self,
        x_position: float,
        rail_z: float,
        base_y: float,
        width: float,
        angle_deg: float,
        rail_idx: int,
    ) -> List[SectionPoint]:
        """
        Sharp profile: Knife-edge with minimal vertical extent.
        
        Best for drag reduction while still providing spray deflection.
        
            P1 (sharp tip)
           ╱
          ╱
        P0─P2 (minimal height)
        """
        points = []
        
        angle_rad = math.radians(angle_deg)
        rail_tiny_height = 0.005  # Very small vertical extent (5mm)
        
        # P0: Bottom attachment
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z - rail_tiny_height),
            edge_type=EdgeType.HARD,
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_bottom",
        ))
        
        # P1: Sharp tip
        tip_y = base_y + width * math.cos(angle_rad)
        tip_z = rail_z + width * math.sin(angle_rad)
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=tip_y, z=tip_z),
            edge_type=EdgeType.HARD,
            is_chine=True,
            feature_id=f"spray_rail_{rail_idx}_tip",
        ))
        
        # P2: Top attachment (nearly same height as bottom)
        points.append(SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=rail_z + rail_tiny_height),
            edge_type=EdgeType.HARD,
            is_chine=False,
            feature_id=f"spray_rail_{rail_idx}_top",
        ))
        
        return points

