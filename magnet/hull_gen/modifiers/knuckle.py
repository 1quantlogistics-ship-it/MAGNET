"""
hull_gen/modifiers/knuckle.py - Knuckle line section modifier.

BRAVO OWNS THIS FILE.

Phase 4: Adds knuckle lines to hull sections as hard longitudinal edges.
"""

import math
from typing import List

from magnet.hull_gen.geometry import Point3D, SectionPoint, EdgeType
from magnet.hull_gen.parameters import HullDefinition, KnuckleLineConfig, HullFeatures
from magnet.hull_gen.modifiers.base import SectionModifier


class KnuckleModifier(SectionModifier):
    """
    Adds knuckle lines to hull sections.
    
    A knuckle is a hard longitudinal edge where the hull surface
    changes direction abruptly. Unlike spray rails, knuckles don't
    project outward - they're just a change in surface angle.
    
    Cross-section at knuckle:
    
            │   Above knuckle (different angle)
            │  ╱
            │ ╱
            │╱ ← Knuckle point (hard edge)
            │
            │   Below knuckle
            │
    """
    
    def modify(
        self,
        points: List[SectionPoint],
        station: float,
        definition: HullDefinition,
    ) -> List[SectionPoint]:
        """Add knuckle lines to section points."""
        features = definition.features
        if not features:
            return points
        
        # Get active knuckles at this station
        active_knuckles = features.get_active_knuckles_at_station(station)
        if not active_knuckles:
            return points
        
        # Sort knuckles by height (process from bottom to top)
        active_knuckles = sorted(active_knuckles, key=lambda k: k.height_ratio)
        
        # Get dimensions
        draft = definition.dimensions.draft
        depth = definition.dimensions.depth
        lwl = definition.dimensions.lwl
        x_position = self._get_x_position(station, lwl)
        
        modified_points = list(points)
        
        for knuckle_idx, knuckle in enumerate(active_knuckles):
            # Calculate knuckle Z position (relative to depth, not draft)
            # Knuckles are typically above waterline
            knuckle_z = -draft + knuckle.height_ratio * (depth + draft)
            
            # Find insertion point
            insert_idx = self._find_insertion_index(modified_points, knuckle_z)
            
            # Get Y at knuckle height
            base_y = self._interpolate_y_at_z(modified_points, knuckle_z)
            
            # Create knuckle point
            knuckle_point = self._create_knuckle_point(
                x_position=x_position,
                knuckle=knuckle,
                knuckle_z=knuckle_z,
                base_y=base_y,
                knuckle_idx=knuckle_idx,
            )
            
            # Check if there's already a point very close to this Z
            should_insert = True
            if insert_idx < len(modified_points):
                existing_z = modified_points[insert_idx].position.z
                if abs(existing_z - knuckle_z) < 0.01:
                    # Replace existing point with knuckle point
                    modified_points[insert_idx] = knuckle_point
                    should_insert = False
            
            if should_insert:
                # Insert knuckle point
                modified_points.insert(insert_idx, knuckle_point)
            
            # Optionally adjust surrounding points to create angle change
            if knuckle.angle_deg != 0:
                self._apply_angle_change(
                    modified_points,
                    insert_idx if should_insert else insert_idx,
                    knuckle,
                    definition,
                )
        
        return modified_points
    
    def _create_knuckle_point(
        self,
        x_position: float,
        knuckle: KnuckleLineConfig,
        knuckle_z: float,
        base_y: float,
        knuckle_idx: int,
    ) -> SectionPoint:
        """Create a knuckle point."""
        edge_type = EdgeType.HARD if knuckle.is_hard else EdgeType.SMOOTH
        
        return SectionPoint(
            position=Point3D(x=x_position, y=base_y, z=knuckle_z),
            edge_type=edge_type,
            is_chine=knuckle.is_hard,  # Treat hard knuckles like chines
            feature_id=f"knuckle_{knuckle_idx}",
        )
    
    def _apply_angle_change(
        self,
        points: List[SectionPoint],
        knuckle_idx: int,
        knuckle: KnuckleLineConfig,
        definition: HullDefinition,
    ) -> None:
        """
        Apply angle change to points above the knuckle.
        
        This shifts points above the knuckle outward (or inward for negative angle).
        """
        if knuckle_idx >= len(points) - 1:
            return
        
        knuckle_point = points[knuckle_idx]
        knuckle_z = knuckle_point.position.z
        angle_rad = math.radians(knuckle.angle_deg)
        
        # Modify points above knuckle
        for i in range(knuckle_idx + 1, len(points)):
            point = points[i]
            dz = point.position.z - knuckle_z
            
            if dz > 0:
                # Calculate outward shift based on height above knuckle
                dy = dz * math.tan(angle_rad)
                new_y = point.position.y + dy
                
                # Clamp to reasonable bounds
                max_y = definition.dimensions.beam_max * 0.6
                new_y = max(0, min(new_y, max_y))
                
                # Create new point with modified position
                points[i] = SectionPoint(
                    position=Point3D(
                        x=point.position.x,
                        y=new_y,
                        z=point.position.z,
                    ),
                    edge_type=point.edge_type,
                    is_chine=point.is_chine,
                    is_keel=point.is_keel,
                    feature_id=point.feature_id,
                    normal=point.normal,
                    curvature=point.curvature,
                    crease_angle_deg=point.crease_angle_deg,
                )

