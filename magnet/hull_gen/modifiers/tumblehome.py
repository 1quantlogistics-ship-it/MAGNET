"""
hull_gen/modifiers/tumblehome.py - Tumblehome section modifier.

BRAVO OWNS THIS FILE.

Phase 6: Applies tumblehome (inward lean) to hull sections above waterline.
"""

import math
from typing import List

from magnet.hull_gen.geometry import Point3D, SectionPoint
from magnet.hull_gen.parameters import HullDefinition, TumblehomeConfig
from magnet.hull_gen.modifiers.base import SectionModifier


class TumblehomeModifier(SectionModifier):
    """
    Applies tumblehome (inward lean) to hull sections above waterline.
    
    Tumblehome is the inverse of flare — the hull leans inward as it
    rises above the waterline. Common on military vessels to reduce
    radar signature and topside weight.
    
    Tumblehome shifts points inward (reduces Y) based on their height
    above the tumblehome start line. The amount of shift increases
    with height according to the configured angle.
    
    Cross-section effect:
        Before (flare):    After (tumblehome):
           /      \\           \\      /
          /        \\           \\    /
        ─┼──────────┼─       ─┼──────┼─
          \\        /           │    │
           │      │            │    │
    """
    
    def modify(
        self,
        points: List[SectionPoint],
        station: float,
        definition: HullDefinition,
    ) -> List[SectionPoint]:
        """
        Apply tumblehome to section points.
        
        Args:
            points: Original section points (keel to deck, half-section)
            station: Station position as fraction of LWL (0=AP, 1=FP)
            definition: Hull definition with features
            
        Returns:
            Modified list of section points with tumblehome applied
        """
        features = definition.features
        if not features:
            return points
        
        config = features.get_tumblehome_config()
        if not config or not config.enabled:
            return points
        
        # Check station is in tumblehome range
        if station < config.start_station or station > config.end_station:
            return points
        
        # Calculate tumblehome start Z
        draft = definition.dimensions.draft
        depth = definition.dimensions.depth
        waterline_z = 0.0  # Z=0 is waterline
        deck_z = depth - draft  # Height above waterline to deck
        
        # Start height is relative to above-waterline portion
        tumblehome_start_z = waterline_z + config.start_height_ratio * deck_z
        tumblehome_height = deck_z - tumblehome_start_z
        
        if tumblehome_height <= 0:
            return points
        
        # Modify points above tumblehome start
        modified_points = []
        
        for point in points:
            z = point.position.z
            
            if z <= tumblehome_start_z:
                # Below tumblehome zone — no change
                modified_points.append(point)
            else:
                # In tumblehome zone — apply inward shift
                height_in_zone = (z - tumblehome_start_z) / tumblehome_height
                height_in_zone = min(1.0, max(0.0, height_in_zone))
                
                angle_deg = config.get_angle_at(station, height_in_zone)
                angle_rad = math.radians(angle_deg)
                
                # Calculate inward offset: y_offset = height_above_start * tan(angle)
                height_above_start = z - tumblehome_start_z
                y_offset = height_above_start * math.tan(angle_rad)
                
                # Reduce Y (move inward), but don't go negative
                new_y = max(0.0, point.position.y - y_offset)
                
                modified_points.append(SectionPoint(
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
                ))
        
        return modified_points

