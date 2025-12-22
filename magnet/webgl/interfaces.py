"""
webgl/interfaces.py - Clean dependency boundaries v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Defines interfaces that decouple geometry generation from StateManager.
Consumers of geometry should depend on these interfaces, not on
StateManager or UI utilities directly.

Addresses: FM4 (Over-coupled to StateManager/UI)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol, runtime_checkable, Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
import logging

if TYPE_CHECKING:
    from magnet.core.state_manager import StateManager
    from magnet.core.design_state import DesignState

logger = logging.getLogger("webgl.interfaces")


# =============================================================================
# GEOMETRY INPUT PROTOCOL
# =============================================================================

@runtime_checkable
class GeometryInputProvider(Protocol):
    """
    Protocol for providing geometry inputs.

    Consumers of geometry should depend on this interface,
    not on StateManager or UI utilities directly.

    This decouples the WebGL module from state implementation details.
    """

    @property
    def loa(self) -> float:
        """Length overall (m)."""
        ...

    @property
    def lwl(self) -> float:
        """Length at waterline (m)."""
        ...

    @property
    def beam(self) -> float:
        """Maximum beam (m)."""
        ...

    @property
    def draft(self) -> float:
        """Design draft (m)."""
        ...

    @property
    def depth(self) -> float:
        """Depth to main deck (m)."""
        ...

    @property
    def cb(self) -> float:
        """Block coefficient."""
        ...

    @property
    def cp(self) -> float:
        """Prismatic coefficient."""
        ...

    @property
    def cwp(self) -> float:
        """Waterplane coefficient."""
        ...

    @property
    def cm(self) -> float:
        """Midship coefficient."""
        ...

    @property
    def deadrise_deg(self) -> float:
        """Deadrise angle at transom (degrees)."""
        ...

    @property
    def transom_width_ratio(self) -> float:
        """Transom width as ratio of beam."""
        ...

    @property
    def bow_angle_deg(self) -> float:
        """Bow entry angle (degrees)."""
        ...

    @property
    def design_id(self) -> str:
        """Design identifier."""
        ...

    def get_parameter(self, path: str, default: Any = None) -> Any:
        """Get any parameter by path."""
        ...


# =============================================================================
# GEOMETRY REFERENCE MODEL PROVIDER
# =============================================================================

@runtime_checkable
class GeometryReferenceModelProvider(Protocol):
    """
    Protocol for providing authoritative geometry reference.

    This is the single source of truth for hull geometry.
    All consumers (physics, structure, WebGL) read from this.
    """

    def get_hull_geometry(self, design_id: str) -> "HullGeometryData":
        """
        Get authoritative hull geometry.

        Args:
            design_id: Design identifier

        Returns:
            HullGeometryData with sections, waterlines, curves

        Raises:
            GeometryUnavailableError if not generated
        """
        ...

    def has_geometry(self, design_id: str) -> bool:
        """Check if geometry is available for design."""
        ...

    def get_geometry_version(self, design_id: str) -> Optional[str]:
        """Get version ID of current geometry."""
        ...


# =============================================================================
# HULL GEOMETRY DATA
# =============================================================================

@dataclass
class Point3D:
    """3D point in MAGNET coordinate system."""
    x: float  # Forward (from AP)
    y: float  # Port (from CL)
    z: float  # Up (from BL)

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float]) -> "Point3D":
        return cls(x=t[0], y=t[1], z=t[2])


@dataclass
class HullSection:
    """Transverse hull section at a given station."""
    station: float  # X position from AP
    points: List[Point3D]  # Points from keel to deck
    is_closed: bool = False


@dataclass
class HullGeometryData:
    """
    Authoritative hull geometry from GRM.

    This is the canonical geometry that all consumers read from.
    """
    design_id: str
    version_id: str

    # Hull sections (transverse)
    sections: List[HullSection]

    # Key curves
    keel_profile: List[Point3D]
    stem_profile: List[Point3D]
    chine_curve: Optional[List[Point3D]] = None
    sheer_curve: Optional[List[Point3D]] = None
    transom_outline: Optional[List[Point3D]] = None

    # Principal dimensions
    loa: float = 0.0
    lwl: float = 0.0
    beam: float = 0.0
    draft: float = 0.0

    # Computed properties
    volume: float = 0.0
    wetted_surface: float = 0.0
    waterplane_area: float = 0.0


# =============================================================================
# STATE GEOMETRY ADAPTER
# =============================================================================

class StateGeometryAdapter:
    """
    Adapter: StateManager/DesignState → GeometryInputProvider.

    Isolates geometry module from state implementation details.
    """

    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager

    @classmethod
    def from_state_manager(cls, state_manager: "StateManager") -> "StateGeometryAdapter":
        """Factory from StateManager."""
        return cls(state_manager)

    def _get_hull_value(self, attr: str, default: float) -> float:
        """Get hull attribute with fallback."""
        try:
            # Try ui.utils path-based access first
            from magnet.ui.utils import get_state_value
            value = get_state_value(self._sm, f"hull.{attr}", default)
            if value is not None:
                return float(value)
        except (ImportError, Exception):
            pass

        # Fallback to direct state access
        try:
            if hasattr(self._sm, 'state') and hasattr(self._sm.state, 'hull'):
                hull = self._sm.state.hull
                if hasattr(hull, attr):
                    value = getattr(hull, attr)
                    if value is not None:
                        return float(value)
        except Exception:
            pass

        return default

    @property
    def loa(self) -> float:
        return self._get_hull_value('loa', 25.0)

    @property
    def lwl(self) -> float:
        return self._get_hull_value('lwl', 23.0)

    @property
    def beam(self) -> float:
        return self._get_hull_value('beam', 6.0)

    @property
    def draft(self) -> float:
        return self._get_hull_value('draft', 1.5)

    @property
    def depth(self) -> float:
        return self._get_hull_value('depth', 3.0)

    @property
    def cb(self) -> float:
        return self._get_hull_value('cb', 0.45)

    @property
    def cp(self) -> float:
        return self._get_hull_value('cp', 0.65)

    @property
    def cwp(self) -> float:
        return self._get_hull_value('cwp', 0.75)

    @property
    def cm(self) -> float:
        return self._get_hull_value('cm', 0.70)

    @property
    def deadrise_deg(self) -> float:
        return self._get_hull_value('deadrise_deg', 15.0)

    @property
    def transom_width_ratio(self) -> float:
        return self._get_hull_value('transom_width_ratio', 0.85)

    @property
    def bow_angle_deg(self) -> float:
        return self._get_hull_value('bow_angle_deg', 25.0)

    @property
    def hull_type(self) -> str:
        """Hull type string."""
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, "hull.hull_type", "hard_chine")
        except Exception:
            return "hard_chine"

    @property
    def hull_spacing(self) -> float:
        """Hull spacing for multihull (m)."""
        # Try both naming conventions
        spacing = self._get_hull_value('hull_spacing_m', 0.0)
        if spacing == 0.0:
            spacing = self._get_hull_value('hull_spacing', 0.0)
        return spacing

    @property
    def design_id(self) -> str:
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, "metadata.design_id", "unknown")
        except Exception:
            return "unknown"

    def get_parameter(self, path: str, default: Any = None) -> Any:
        """Get any parameter by path."""
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, path, default)
        except Exception:
            return default


# =============================================================================
# HULL GENERATOR ADAPTER
# =============================================================================

class HullGeneratorAdapter:
    """
    Adapter: HullGenerator → GeometryReferenceModelProvider.

    Wraps the hull generator to provide authoritative geometry.
    """

    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager
        self._cache: Dict[str, HullGeometryData] = {}

    def get_hull_geometry(self, design_id: str) -> HullGeometryData:
        """Get hull geometry, generating if needed."""
        # Build cache key from design_id + hull-affecting parameters
        # This ensures cache invalidation when hull_type, spacing, or coefficients change
        inputs = StateGeometryAdapter(self._sm)
        cache_key = self._build_cache_key(design_id, inputs)

        # Check cache with versioned key
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try to get from hull generator
        try:
            from magnet.hull_gen.generator import HullGenerator
            from magnet.hull_gen.parameters import (
                HullDefinition,
                MainDimensions,
                FormCoefficients,
                DeadriseProfile,
                HullFeatures,
            )

            # Build HullDefinition object (the correct interface)
            hull_type = self._get_hull_type(inputs)

            definition = HullDefinition(
                hull_id=design_id,
                hull_name=f"Design {design_id}",
                hull_type=hull_type,
                dimensions=MainDimensions(
                    loa=inputs.loa,
                    lwl=inputs.lwl,
                    lpp=inputs.lwl * 0.98,  # PROVISIONAL - approximate LPP
                    beam_max=inputs.beam,
                    beam_wl=inputs.beam * 0.95,   # PROVISIONAL - refine via state or rules
                    beam_chine=inputs.beam * 0.90, # PROVISIONAL - refine via state or rules
                    depth=inputs.depth,
                    draft=inputs.draft,
                    draft_fwd=inputs.draft,  # PROVISIONAL - add trim support later
                    draft_aft=inputs.draft,  # PROVISIONAL - add trim support later
                    freeboard_bow=inputs.depth - inputs.draft + 0.5,
                    freeboard_mid=inputs.depth - inputs.draft,
                    freeboard_stern=inputs.depth - inputs.draft,
                ),
                coefficients=FormCoefficients(
                    cb=inputs.cb,
                    cp=inputs.cp,
                    cm=inputs.cm,
                    cwp=inputs.cwp,
                    # PROVISIONAL DEFAULTS - to be overridden by LLM proposals or rule-based refinement
                    lcb=0.52,  # Slightly aft of midship (typical for displacement hulls)
                    lcf=0.50,  # At midship
                ),
                deadrise=DeadriseProfile.warped(
                    transom=inputs.deadrise_deg,
                    midship=inputs.deadrise_deg + 2,
                    bow=inputs.deadrise_deg + 25,
                ),
                features=HullFeatures(
                    transom_width_fraction=inputs.transom_width_ratio,
                    bow_flare_deg=inputs.bow_angle_deg,
                    hull_spacing=inputs.hull_spacing,
                    num_hulls=2 if inputs.hull_type == "catamaran" else 1,
                ),
            )

            # Validate definition
            errors = definition.validate()
            if errors:
                logger.warning(f"HullDefinition validation warnings: {errors}")

            # Compute derived properties
            definition.compute_displacement()
            definition.compute_waterplane_area()

            # Generate geometry with correct signature
            generator = HullGenerator()
            hull_geom = generator.generate(definition)  # CORRECT

            # Convert to HullGeometryData
            data = self._convert_hull_geometry(hull_geom, design_id)
            self._cache[cache_key] = data  # Cache with versioned key
            return data

        except ImportError as e:
            from magnet.webgl.errors import GeometryUnavailableError
            raise GeometryUnavailableError(
                design_id=design_id,
                reason=f"HullGenerator module not available: {e}",
            )
        except Exception as e:
            from magnet.webgl.errors import GeometryUnavailableError
            logger.error(f"Hull generation failed: {e}", exc_info=True)
            raise GeometryUnavailableError(
                design_id=design_id,
                reason=str(e),
            )

    def _build_cache_key(self, design_id: str, inputs: StateGeometryAdapter) -> str:
        """
        Build cache key that includes hull-affecting parameters.

        Cache invalidates when any geometry-affecting parameter changes.
        This prevents stale geometry when hull_type, spacing, or coefficients update.
        """
        import hashlib

        # Include all parameters that affect hull geometry
        try:
            design_version = self._sm.get("design_version", 0) if hasattr(self._sm, "get") else 0
        except Exception:
            design_version = 0

        key_parts = [
            f"{design_id}:{design_version}",
            str(inputs.hull_type),
            f"{inputs.loa:.3f}",
            f"{inputs.lwl:.3f}",
            f"{inputs.beam:.3f}",
            f"{inputs.draft:.3f}",
            f"{inputs.depth:.3f}",
            f"{inputs.cb:.4f}",
            f"{inputs.cp:.4f}",
            f"{inputs.cwp:.4f}",
            f"{inputs.deadrise_deg:.1f}",
            f"{inputs.hull_spacing:.3f}",
        ]

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()[:16]

    def _get_hull_type(self, inputs: StateGeometryAdapter) -> 'HullType':
        """Get hull type from state, defaulting to HARD_CHINE."""
        from magnet.hull_gen.enums import HullType

        hull_type_str = inputs.hull_type

        # Map string to enum
        type_map = {
            "hard_chine": HullType.HARD_CHINE,
            "round_bilge": HullType.ROUND_BILGE,
            "deep_v": HullType.DEEP_V_PLANING,
            "deep_v_planing": HullType.DEEP_V_PLANING,
            "semi_displacement": HullType.SEMI_DISPLACEMENT,
            "catamaran": HullType.CATAMARAN,
            "trimaran": HullType.TRIMARAN,
            "swath": HullType.SWATH,
        }

        # Warn on unknown hull type (don't silently fall back)
        if hull_type_str.lower() not in type_map:
            logger.warning(f"Unknown hull_type '{hull_type_str}', defaulting to HARD_CHINE")

        return type_map.get(hull_type_str.lower(), HullType.HARD_CHINE)

    def _convert_hull_geometry(self, hull_geom: Any, design_id: str) -> HullGeometryData:
        """Convert HullGenerator output to HullGeometryData."""
        sections = []

        # Convert sections if available
        if hasattr(hull_geom, 'sections'):
            for section in hull_geom.sections:
                points = []
                if hasattr(section, 'points'):
                    for pt in section.points:
                        # Handle SectionPoint objects (have .position attribute)
                        if hasattr(pt, 'position'):
                            pos = pt.position
                            points.append(Point3D(pos.x, pos.y, pos.z))
                        # Handle Point3D directly
                        elif hasattr(pt, 'x'):
                            points.append(Point3D(pt.x, pt.y, pt.z))
                        elif isinstance(pt, (list, tuple)) and len(pt) >= 3:
                            points.append(Point3D(pt[0], pt[1], pt[2]))

                station = getattr(section, 'station', 0.0)
                x_position = getattr(section, 'x_position', station)
                sections.append(HullSection(station=x_position, points=points))

        # Convert curves
        keel_profile = self._extract_curve(hull_geom, 'keel_profile')
        stem_profile = self._extract_curve(hull_geom, 'stem_profile')
        chine_curve = self._extract_curve(hull_geom, 'chine_curve')
        sheer_curve = self._extract_curve(hull_geom, 'sheer_curve')
        transom_outline = self._extract_curve(hull_geom, 'transom_outline')

        return HullGeometryData(
            design_id=design_id,
            version_id=f"{design_id}-v1",
            sections=sections,
            keel_profile=keel_profile,
            stem_profile=stem_profile,
            chine_curve=chine_curve,
            sheer_curve=sheer_curve,
            transom_outline=transom_outline,
            loa=getattr(hull_geom, 'loa', 0.0),
            lwl=getattr(hull_geom, 'lwl', 0.0),
            beam=getattr(hull_geom, 'beam', 0.0),
            draft=getattr(hull_geom, 'draft', 0.0),
            volume=getattr(hull_geom, 'volume', 0.0),
            wetted_surface=getattr(hull_geom, 'wetted_surface', 0.0),
            waterplane_area=getattr(hull_geom, 'waterplane_area', 0.0),
        )

    def _extract_curve(self, hull_geom: Any, attr: str) -> List[Point3D]:
        """Extract curve points from hull geometry."""
        points = []
        if hasattr(hull_geom, attr):
            curve = getattr(hull_geom, attr)
            if curve:
                for pt in curve:
                    if hasattr(pt, 'x'):
                        points.append(Point3D(pt.x, pt.y, pt.z))
                    elif isinstance(pt, (list, tuple)) and len(pt) >= 3:
                        points.append(Point3D(pt[0], pt[1], pt[2]))
        return points

    def has_geometry(self, design_id: str) -> bool:
        """Check if geometry is available."""
        if design_id in self._cache:
            return True

        # Check if hull parameters exist
        try:
            inputs = StateGeometryAdapter(self._sm)
            return inputs.loa > 0 and inputs.beam > 0 and inputs.draft > 0
        except Exception:
            return False

    def get_geometry_version(self, design_id: str) -> Optional[str]:
        """Get version ID of cached geometry."""
        if design_id in self._cache:
            return self._cache[design_id].version_id
        return None

    def invalidate(self, design_id: str) -> None:
        """Invalidate cached geometry for design."""
        if design_id in self._cache:
            del self._cache[design_id]
            logger.info(f"Invalidated geometry cache for {design_id}")

    def invalidate_all(self) -> None:
        """Invalidate all cached geometry."""
        self._cache.clear()
        logger.info("Invalidated all geometry cache")
