"""
hull_gen/modifiers/base.py - Base class for section modifiers.

BRAVO OWNS THIS FILE.

Phase 4: Provides abstract base class for section modification pipeline.
"""

from abc import ABC, abstractmethod
from typing import List

from magnet.hull_gen.geometry import SectionPoint
from magnet.hull_gen.parameters import HullDefinition


class SectionModifier(ABC):
    """
    Base class for section modifiers.
    
    Modifiers transform a list of section points, potentially:
    - Adding new points (spray rails, knuckles)
    - Modifying existing points (tumblehome, flare)
    - Changing edge types (hard/soft)
    
    Modifiers are applied in order after base section generation.
    They must preserve point ordering (keel to deck).
    """
    
    @abstractmethod
    def modify(
        self,
        points: List[SectionPoint],
        station: float,
        definition: HullDefinition,
    ) -> List[SectionPoint]:
        """
        Modify section points.
        
        Args:
            points: Original section points (keel to deck, half-section)
            station: Station position as fraction of LWL (0=AP, 1=FP)
            definition: Hull definition with features
            
        Returns:
            Modified list of section points (must maintain keel-to-deck order)
        """
        pass
    
    def _find_insertion_index(
        self,
        points: List[SectionPoint],
        target_z: float,
    ) -> int:
        """
        Find index where to insert a point at target Z height.
        
        Returns index such that points[index-1].z <= target_z <= points[index].z
        """
        for i, point in enumerate(points):
            if point.position.z >= target_z:
                return i
        return len(points)
    
    def _interpolate_y_at_z(
        self,
        points: List[SectionPoint],
        target_z: float,
    ) -> float:
        """
        Interpolate Y position at given Z height.
        
        Performs linear interpolation between bracketing points.
        """
        if not points:
            return 0.0
        
        # Find bracketing points
        for i in range(len(points) - 1):
            z0 = points[i].position.z
            z1 = points[i + 1].position.z
            
            if z0 <= target_z <= z1:
                # Linear interpolation
                t = (target_z - z0) / (z1 - z0) if z1 != z0 else 0
                y0 = points[i].position.y
                y1 = points[i + 1].position.y
                return y0 + t * (y1 - y0)
        
        # Extrapolate from nearest points
        if target_z < points[0].position.z:
            return points[0].position.y
        return points[-1].position.y
    
    def _get_x_position(self, station: float, lwl: float) -> float:
        """Get X position from station and LWL."""
        return station * lwl

