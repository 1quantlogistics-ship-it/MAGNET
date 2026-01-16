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

# LODLevel is used for mesh resolution selection in the authoritative hull generator adapter.
from .schema import LODLevel


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

    def get_hull_geometry(self, design_id: str, lod: Optional[LODLevel] = None) -> "HullGeometryData":
        """
        Get authoritative hull geometry.

        Args:
            design_id: Design identifier
            lod: Optional level-of-detail selector for resolution (low/medium/high/ultra)

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
class SectionVertex:
    """
    Section vertex with optional edge typing (hard edges/chines).

    The WebGL tessellator understands objects with `.position` and `.edge_type`.
    """
    position: Point3D
    edge_type: Any = None


@dataclass
class HullSection:
    """Transverse hull section at a given station."""
    station: float  # X position from AP
    points: List[Any]  # Points from keel to deck (Point3D or SectionVertex)
    is_closed: bool = False
    # Body ownership for multi-body tessellation (design language authority path).
    # Freeform identifier; used only for geometric partitioning, never for design intent.
    body_id: str = "main"


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

    # Universal primitives (Phase 3: diagnostic/pass-through)
    openings: Optional[List[Dict[str, Any]]] = None
    flow_paths: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None


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

    def _get_hull_optional_float(self, attr: str) -> Optional[float]:
        """Get optional hull attribute as float (returns None if unset/missing)."""
        try:
            from magnet.ui.utils import get_state_value
            v = get_state_value(self._sm, f"hull.{attr}", None)
            if v is None:
                return None
            return float(v)
        except Exception:
            try:
                v = self._sm.get(f"hull.{attr}", None) if hasattr(self._sm, "get") else None
                if v is None:
                    return None
                return float(v)
            except Exception:
                return None

    @property
    def loa(self) -> float:
        return self._get_hull_value('loa', 25.0)

    @property
    def lwl(self) -> float:
        """
        Waterline length (LWL).

        IMPORTANT (Hull Form UX): the parametric hull generator spaces stations along LWL.
        If LWL is unset, default it to LOA so that user-facing LOA changes visibly
        regenerate the hull geometry (until a dedicated LWL workflow is implemented).
        """
        # Prefer explicit hull.lwl when present
        try:
            from magnet.ui.utils import get_state_value
            v = get_state_value(self._sm, "hull.lwl", None)
            if v is not None:
                v = float(v)
                if v > 0:
                    return v
        except Exception:
            pass

        # Default LWL from LOA (keeps geometry responsive to LOA edits)
        try:
            loa = float(self.loa)
            if loa > 0:
                return loa
        except Exception:
            pass

        return 23.0

    @property
    def beam(self) -> float:
        return self._get_hull_value('beam', 6.0)

    @property
    def draft(self) -> float:
        return self._get_hull_value('draft', 1.5)

    @property
    def draft_fwd_m(self) -> float:
        """Draft at forward perpendicular (m). Falls back to design draft."""
        v = self._get_hull_optional_float("draft_fwd_m")
        return float(v) if v is not None else float(self.draft)

    @property
    def draft_aft_m(self) -> float:
        """Draft at aft perpendicular (m). Falls back to design draft."""
        v = self._get_hull_optional_float("draft_aft_m")
        return float(v) if v is not None else float(self.draft)

    @property
    def freeboard_m(self) -> Optional[float]:
        """Minimum freeboard at side (m). Optional override for effective depth."""
        return self._get_hull_optional_float("freeboard_m")

    @property
    def depth(self) -> float:
        # If freeboard_m is explicitly set, treat it as authoritative control:
        # effective_depth = max(draft_fwd, draft_aft, draft_mid) + freeboard_m
        fb = self.freeboard_m
        if fb is not None:
            fb = max(0.0, float(fb))
            draft_ref = max(float(self.draft), float(self.draft_fwd_m), float(self.draft_aft_m))
            return float(draft_ref + fb)
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
    def deadrise_transom_deg(self) -> float:
        """Deadrise at transom (deg). Defaults to midship-5deg if unset."""
        v = self._get_hull_optional_float("deadrise_transom_deg")
        if v is not None:
            return float(v)
        return max(0.0, min(30.0, float(self.deadrise_deg) - 5.0))

    @property
    def lcb_fraction(self) -> float:
        """LCB as fraction of LWL from FP (0=bow/FP, 1=stern/AP)."""
        return self._get_hull_value('lcb_fraction', 0.52)

    @property
    def transom_beam_ratio(self) -> float:
        """Transom width fraction (0..1)."""
        return self._get_hull_value('transom_beam_ratio', 0.7)

    @property
    def bow_entrance_deg(self) -> float:
        """Waterline entry half-angle (deg)."""
        return self._get_hull_value('bow_entrance_deg', 25.0)

    @property
    def bow_flare_deg(self) -> float:
        """Bow flare above waterline (deg)."""
        return self._get_hull_value('bow_flare_deg', 15.0)

    @property
    def stem_rake_deg(self) -> float:
        """Stem rake from vertical (deg)."""
        return self._get_hull_value('stem_rake_deg', 10.0)

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

    # =========================================================================
    # Phase 2-6 Geometry Features (State Bridge)
    # =========================================================================

    @property
    def chine_type(self) -> str:
        """Chine type: none, soft, hard, double, triple, reverse, variable."""
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, "hull.chine_type", "soft")
        except Exception:
            return "soft"

    @property
    def chine_count(self) -> int:
        """Number of chines (1-3)."""
        return int(self._get_hull_value('chine_count', 1))

    @property
    def bow_style(self) -> str:
        """Bow style: traditional, wedge, axe, wave_piercing."""
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, "hull.bow_style", "traditional")
        except Exception:
            return "traditional"

    @property
    def bow_facet_count(self) -> int:
        """Number of facets for wedge/axe bow (2-6)."""
        return int(self._get_hull_value('bow_facet_count', 3))

    @property
    def spray_rail_count(self) -> int:
        """Number of spray rails (0-4)."""
        return int(self._get_hull_value('spray_rail_count', 0))

    @property
    def has_spray_rails(self) -> bool:
        """Whether spray rails are enabled."""
        try:
            from magnet.ui.utils import get_state_value
            return bool(get_state_value(self._sm, "hull.has_spray_rails", False))
        except Exception:
            return False

    @property
    def transom_style(self) -> str:
        """Transom style: vertical, raked, stepped, tunneled."""
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, "hull.transom_style", "raked")
        except Exception:
            return "raked"

    @property
    def transom_rake_deg(self) -> float:
        """Transom rake angle (degrees)."""
        return self._get_hull_value('transom_rake_deg', 12.0)

    @property
    def tumblehome_enabled(self) -> bool:
        """Whether tumblehome is enabled."""
        try:
            from magnet.ui.utils import get_state_value
            return bool(get_state_value(self._sm, "hull.tumblehome_enabled", False))
        except Exception:
            return False

    @property
    def tumblehome_angle_deg(self) -> float:
        """Tumblehome angle (degrees inward)."""
        return self._get_hull_value('tumblehome_angle_deg', 0.0)

    @property
    def tumblehome_start_ratio(self) -> float:
        """Tumblehome start height as ratio of depth (0-1)."""
        return self._get_hull_value('tumblehome_start_ratio', 0.5)

    @property
    def panel_style(self) -> str:
        """Panel style: smooth, faceted, developable."""
        try:
            from magnet.ui.utils import get_state_value
            return get_state_value(self._sm, "hull.panel_style", "smooth")
        except Exception:
            return "smooth"

    @property
    def deck_enabled(self) -> bool:
        """Whether deck surface is enabled."""
        try:
            from magnet.ui.utils import get_state_value
            return bool(get_state_value(self._sm, "hull.deck_enabled", True))
        except Exception:
            return True

    @property
    def deck_camber_m(self) -> float:
        """Deck camber (crown) in meters."""
        return self._get_hull_value('deck_camber_m', 0.0)

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

    def get_hull_geometry(self, design_id: str, lod: Optional[LODLevel] = None) -> HullGeometryData:
        """Get hull geometry, generating if needed."""
        lod = lod or LODLevel.MEDIUM

        # Build cache key from design_id + hull-affecting parameters
        # This ensures cache invalidation when hull_type, spacing, or coefficients change
        inputs = StateGeometryAdapter(self._sm)
        cache_key = self._build_cache_key(design_id, inputs, lod)

        # Check cache with versioned key
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try to get from hull generator
        try:
            from magnet.hull_gen.generator import HullGenerator
            from magnet.hull_gen.generator import GeneratorConfig
            from magnet.hull_gen.parameters import (
                HullDefinition,
                MainDimensions,
                FormCoefficients,
                DeadriseProfile,
                HullFeatures,
            )

            # Mesh resolution (authoritative): target ~2k faces on LOW, ~10k+ on MEDIUM, ~15k on HIGH.
            # Faces are ~4 * num_sections * (points_per_section - 1) for monohull (plus small cap overhead).
            if lod == LODLevel.LOW:
                gen_cfg = GeneratorConfig(num_sections=21, points_per_section=25)
            elif lod == LODLevel.MEDIUM:
                gen_cfg = GeneratorConfig(num_sections=51, points_per_section=51)
            elif lod == LODLevel.HIGH:
                gen_cfg = GeneratorConfig(num_sections=61, points_per_section=61)
            else:
                # ULTRA: still reasonable for demos; avoid extreme 100k+ face meshes by default.
                gen_cfg = GeneratorConfig(num_sections=81, points_per_section=81)

            # Build HullDefinition object (the correct interface)
            hull_type = self._get_hull_type(inputs)

            # Draft/trim support (Module Hull Form Completion)
            draft_mid = float(inputs.draft)
            draft_fwd = float(inputs.draft_fwd_m)
            draft_aft = float(inputs.draft_aft_m)
            depth = float(inputs.depth)

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
                    depth=depth,
                    draft=draft_mid,
                    draft_fwd=draft_fwd,
                    draft_aft=draft_aft,
                    freeboard_bow=depth - draft_fwd,
                    freeboard_mid=depth - draft_mid,
                    freeboard_stern=depth - draft_aft,
                ),
                coefficients=FormCoefficients(
                    cb=inputs.cb,
                    cp=inputs.cp,
                    cm=inputs.cm,
                    cwp=inputs.cwp,
                    # LCB engineering control is stored as fraction from FP; hull_gen expects fraction from AP.
                    lcb=max(0.0, min(1.0, 1.0 - float(inputs.lcb_fraction))),
                    lcf=0.50,  # At midship
                ),
                deadrise=DeadriseProfile.warped(
                    transom=inputs.deadrise_transom_deg,
                    midship=inputs.deadrise_deg,
                    bow=min(inputs.deadrise_deg + 25.0, 60.0),
                ),
                features=self._build_hull_features(inputs),
            )

            # Validate definition
            errors = definition.validate()
            if errors:
                logger.warning(f"HullDefinition validation warnings: {errors}")

            # Compute derived properties
            definition.compute_displacement()
            definition.compute_waterplane_area()

            # Generate geometry with correct signature
            generator = HullGenerator(gen_cfg)
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

    def _build_cache_key(
        self,
        design_id: str,
        inputs: StateGeometryAdapter,
        lod: LODLevel = LODLevel.MEDIUM,
    ) -> str:
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

        def _f(value: Any, default: float = 0.0) -> float:
            """Best-effort float coercion for cache-key stability (tests may pass MagicMocks)."""
            try:
                if value is None:
                    return float(default)
                return float(value)
            except Exception:
                return float(default)

        # Robust fallbacks for older/alternate input field names used in tests and legacy adapters
        draft = _f(getattr(inputs, "draft", None), 0.0)
        draft_fwd = _f(getattr(inputs, "draft_fwd_m", getattr(inputs, "draft_fwd", None)), draft)
        draft_aft = _f(getattr(inputs, "draft_aft_m", getattr(inputs, "draft_aft", None)), draft)
        deadrise = _f(getattr(inputs, "deadrise_deg", None), 0.0)
        deadrise_transom = _f(getattr(inputs, "deadrise_transom_deg", None), deadrise)
        lcb_fraction = _f(getattr(inputs, "lcb_fraction", None), 0.5)
        transom_beam_ratio = _f(
            getattr(inputs, "transom_beam_ratio", None),
            _f(getattr(inputs, "transom_width_ratio", None), 1.0),
        )
        bow_entrance_deg = _f(
            getattr(inputs, "bow_entrance_deg", None),
            _f(getattr(inputs, "bow_angle_deg", None), 25.0),
        )
        bow_flare_deg = _f(getattr(inputs, "bow_flare_deg", None), 0.0)
        stem_rake_deg = _f(getattr(inputs, "stem_rake_deg", None), 0.0)
        hull_spacing = _f(getattr(inputs, "hull_spacing", None), 0.0)

        # Phase 2-6 feature values for cache key
        chine_type = getattr(inputs, "chine_type", "soft")
        chine_count = int(getattr(inputs, "chine_count", 1) or 1)
        bow_style = getattr(inputs, "bow_style", "traditional")
        bow_facet_count = int(getattr(inputs, "bow_facet_count", 3) or 3)
        spray_rail_count = int(getattr(inputs, "spray_rail_count", 0) or 0)
        has_spray_rails = bool(getattr(inputs, "has_spray_rails", False))
        transom_style = getattr(inputs, "transom_style", "raked")
        transom_rake_deg = _f(getattr(inputs, "transom_rake_deg", None), 12.0)
        tumblehome_enabled = bool(getattr(inputs, "tumblehome_enabled", False))
        tumblehome_angle_deg = _f(getattr(inputs, "tumblehome_angle_deg", None), 0.0)
        tumblehome_start_ratio = _f(getattr(inputs, "tumblehome_start_ratio", None), 0.5)
        panel_style = getattr(inputs, "panel_style", "smooth")
        deck_enabled = bool(getattr(inputs, "deck_enabled", True))
        deck_camber_m = _f(getattr(inputs, "deck_camber_m", None), 0.0)

        key_parts = [
            f"{design_id}:{design_version}",
            f"lod={lod.value}",
            str(inputs.hull_type),
            f"{inputs.loa:.3f}",
            f"{inputs.lwl:.3f}",
            f"{inputs.beam:.3f}",
            f"{draft:.3f}",
            f"{draft_fwd:.3f}",
            f"{draft_aft:.3f}",
            f"{inputs.depth:.3f}",
            f"{inputs.cb:.4f}",
            f"{inputs.cp:.4f}",
            f"{inputs.cm:.4f}",
            f"{inputs.cwp:.4f}",
            f"{deadrise:.1f}",
            f"{deadrise_transom:.1f}",
            f"{lcb_fraction:.4f}",
            f"{transom_beam_ratio:.3f}",
            f"{bow_entrance_deg:.1f}",
            f"{bow_flare_deg:.1f}",
            f"{stem_rake_deg:.1f}",
            f"{hull_spacing:.3f}",
            # Phase 2-6 features
            f"chine={chine_type}:{chine_count}",
            f"bow={bow_style}:{bow_facet_count}",
            f"spray={has_spray_rails}:{spray_rail_count}",
            f"transom={transom_style}:{transom_rake_deg:.1f}",
            f"tumble={tumblehome_enabled}:{tumblehome_angle_deg:.1f}:{tumblehome_start_ratio:.2f}",
            f"panel={panel_style}",
            f"deck={deck_enabled}:{deck_camber_m:.3f}",
        ]

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()[:16]

    def _get_hull_type(self, inputs: StateGeometryAdapter) -> 'HullType':
        """Get hull type from state, defaulting to HARD_CHINE."""
        from magnet.hull_gen.enums import HullType

        hull_type_str = (inputs.hull_type or "").lower()

        # Map string to enum
        type_map = {
            # Canonical hull_gen types
            "hard_chine": HullType.HARD_CHINE,
            "round_bilge": HullType.ROUND_BILGE,
            "deep_v": HullType.DEEP_V_PLANING,
            "deep_v_planing": HullType.DEEP_V_PLANING,
            "semi_displacement": HullType.SEMI_DISPLACEMENT,
            "catamaran": HullType.CATAMARAN,
            "trimaran": HullType.TRIMARAN,
            "swath": HullType.SWATH,
            # Module 67.x chat/schema vocabulary aliases → generator enums
            "monohull": HullType.HARD_CHINE,
            "planing": HullType.DEEP_V_PLANING,
            "semi_planing": HullType.DEEP_V_PLANING,
            "displacement": HullType.ROUND_BILGE,
        }

        # Warn on unknown hull type (don't silently fall back)
        if hull_type_str and hull_type_str not in type_map:
            logger.warning(f"Unknown hull_type '{hull_type_str}', defaulting to HARD_CHINE")

        return type_map.get(hull_type_str, HullType.HARD_CHINE)

    def _build_hull_features(self, inputs: StateGeometryAdapter) -> 'HullFeatures':
        """
        Build HullFeatures from state, including Phase 2-6 geometry features.
        
        This bridges the state → geometry pipeline for:
        - Phase 2: Chine variations (double, triple, reverse)
        - Phase 3: Bow forms (wedge, axe, wave-piercing)
        - Phase 4: Spray rails and knuckle lines
        - Phase 5: Transom variations
        - Phase 6: Tumblehome, faceted panels, deck
        """
        from magnet.hull_gen.parameters import HullFeatures, SprayRailConfig
        from magnet.hull_gen.enums import ChineType, BowStyle

        # Map chine_type string to enum
        chine_type_map = {
            "none": ChineType.NONE,
            "soft": ChineType.SOFT,
            "hard": ChineType.HARD,
            "single": ChineType.HARD,
            "double": ChineType.DOUBLE,
            "triple": ChineType.TRIPLE,
            "reverse": ChineType.REVERSE,
            "variable": ChineType.VARIABLE,
        }
        chine_type_str = inputs.chine_type.lower() if inputs.chine_type else "soft"
        chine_type = chine_type_map.get(chine_type_str, ChineType.SOFT)

        # Map bow_style string to enum
        bow_style_map = {
            "traditional": BowStyle.TRADITIONAL,
            "wedge": BowStyle.WEDGE,
            "axe": BowStyle.AXE,
            "wave_piercing": BowStyle.WAVE_PIERCING,
            "wave-piercing": BowStyle.WAVE_PIERCING,
            "faceted": BowStyle.FACETED,
        }
        bow_style_str = inputs.bow_style.lower() if inputs.bow_style else "traditional"
        bow_style = bow_style_map.get(bow_style_str, BowStyle.TRADITIONAL)

        # Build spray rail configs if enabled
        spray_rails = []
        if inputs.has_spray_rails and inputs.spray_rail_count > 0:
            # Generate default spray rail configurations
            for i in range(inputs.spray_rail_count):
                height_ratio = 0.2 + (i * 0.15)  # Space rails from 0.2 to 0.5 height
                spray_rails.append(SprayRailConfig(
                    height_ratio=min(height_ratio, 0.5),
                    angle_deg=18.0 - (i * 2),  # Steeper lower, flatter higher
                    width_m=0.06 - (i * 0.01),  # Slightly smaller upper rails
                ))

        # Build HullFeatures with all Phase 2-6 parameters
        features = HullFeatures(
            # Basic features
            transom_width_fraction=inputs.transom_beam_ratio,
            bow_flare_deg=inputs.bow_flare_deg,
            stem_rake_deg=inputs.stem_rake_deg,
            bow_entrance_deg=inputs.bow_entrance_deg,
            hull_spacing=inputs.hull_spacing,
            # TASK-012: derive body count from geometry inputs, not hull_type string
            num_hulls=(
                len(getattr(inputs, "body_ids", []))
                if hasattr(inputs, "body_ids") and getattr(inputs, "body_ids")
                else getattr(inputs, "num_hulls", None)
            ) or (2 if getattr(inputs, "hull_spacing", 0) and getattr(inputs, "hull_spacing", 0) > 0 else 1),
            
            # Phase 2: Chine variations
            chine_type=chine_type,
            chine_count=inputs.chine_count,
            
            # Phase 3: Bow forms
            bow_style=bow_style,
            bow_facet_count=inputs.bow_facet_count,
            
            # Phase 4: Spray rails
            has_spray_rails=inputs.has_spray_rails,
            spray_rail_count=inputs.spray_rail_count,
            spray_rails=spray_rails,
            
            # Phase 5: Transom variations
            transom_rake_deg=inputs.transom_rake_deg,
            
            # Phase 6: Tumblehome, panels, deck
            tumblehome_enabled=inputs.tumblehome_enabled,
            tumblehome_angle_deg=inputs.tumblehome_angle_deg,
            tumblehome_start_ratio=inputs.tumblehome_start_ratio,
            panel_style=inputs.panel_style,
            deck_enabled=inputs.deck_enabled,
            deck_camber_m=inputs.deck_camber_m,
        )

        logger.debug(
            f"Built HullFeatures: chine={chine_type.name}, bow={bow_style.name}, "
            f"tumblehome={inputs.tumblehome_enabled}, spray_rails={len(spray_rails)}"
        )

        return features

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
                            points.append(
                                SectionVertex(
                                    position=Point3D(pos.x, pos.y, pos.z),
                                    edge_type=getattr(pt, "edge_type", None),
                                )
                            )
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


# =============================================================================
# DESIGN LANGUAGE (resources.*) ADAPTER  — NEW AUTHORITY
# =============================================================================

class DesignLanguageAdapter:
    """
    Adapter: design-language resources → GeometryReferenceModelProvider.

    This is the enum-free authority path:
    resources (geometry.* primitives) → kernel/stdlib compiler → HullGeometry
    → HullGeometryData for the WebGL pipeline.

    IMPORTANT:
    - No HullType / HullFamily / "styles" here.
    - No parametric generator heuristics.
    - Pure compilation of declared primitives + post-validation elsewhere.
    """

    def __init__(self, state_manager: "StateManager"):
        self._sm = state_manager
        self._cache: Dict[str, HullGeometryData] = {}

    def _has_resources(self) -> bool:
        try:
            r = self._sm.get("resources", {}) if hasattr(self._sm, "get") else {}
            return isinstance(r, dict) and len(r) > 0
        except Exception:
            return False

    def _resources_have_sections(self) -> bool:
        try:
            r = self._sm.get("resources", {}) if hasattr(self._sm, "get") else {}
            if not isinstance(r, dict):
                return False
            for _, v in r.items():
                if isinstance(v, dict) and v.get("_type") == "geometry.section" and not v.get("_deleted"):
                    return True
            return False
        except Exception:
            return False

    def get_hull_geometry(self, design_id: str, lod: Optional[LODLevel] = None) -> HullGeometryData:
        """
        Compile declared geometry primitives into canonical HullGeometryData.
        LOD is ignored here (tessellation happens later); kept for interface compatibility.
        """
        # Cache by design_version (authoritative invalidation)
        design_version = 0
        try:
            design_version = int(self._sm.get("design_version", 0))
        except Exception:
            design_version = 0

        cache_key = f"{design_id}:{design_version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self._has_resources() or not self._resources_have_sections():
            from magnet.webgl.errors import GeometryUnavailableError
            raise GeometryUnavailableError(
                design_id=design_id,
                reason="No design-language resources available",
            )

        # Compile from resources.* into the canonical hull_gen.geometry.HullGeometry
        try:
            from magnet.kernel.stdlib.compiler import compile_to_geometry
            state = self._sm.to_dict() if hasattr(self._sm, "to_dict") else {}
            hull_geom = compile_to_geometry(state)
        except Exception as e:
            from magnet.webgl.errors import GeometryUnavailableError
            raise GeometryUnavailableError(
                design_id=design_id,
                reason=str(e),
            )

        data = self._convert_hull_geometry(hull_geom, design_id, design_version=design_version)
        self._cache[cache_key] = data
        return data

    def _convert_hull_geometry(self, hull_geom: Any, design_id: str, design_version: int = 0) -> HullGeometryData:
        """Convert compiler output (HullGeometry) to HullGeometryData."""
        sections: List[HullSection] = []

        # Convert sections
        if hasattr(hull_geom, "sections"):
            for section in getattr(hull_geom, "sections") or []:
                pts: List[Any] = []
                if hasattr(section, "points"):
                    for pt in getattr(section, "points") or []:
                        if hasattr(pt, "position"):
                            pos = pt.position
                            pts.append(
                                SectionVertex(
                                    position=Point3D(pos.x, pos.y, pos.z),
                                    edge_type=getattr(pt, "edge_type", None),
                                )
                            )
                        elif hasattr(pt, "x"):
                            pts.append(Point3D(pt.x, pt.y, pt.z))
                        elif isinstance(pt, (list, tuple)) and len(pt) >= 3:
                            pts.append(Point3D(pt[0], pt[1], pt[2]))

                # WebGL HullSection.station is "X from AP" per this module’s docs.
                x_position = getattr(section, "x_position", None)
                if x_position is None:
                    # Fallback: derive from station ratio if present
                    station_ratio = float(getattr(section, "station", 0.0))
                    loa = float(getattr(hull_geom, "loa", 0.0) or 0.0)
                    x_position = station_ratio * loa
                body_id = getattr(section, "body_id", "main")
                sections.append(HullSection(station=float(x_position), points=pts, body_id=str(body_id)))

        keel_profile = self._extract_curve(hull_geom, "keel_profile")
        stem_profile = self._extract_curve(hull_geom, "stem_profile")
        chine_curve = self._extract_curve(hull_geom, "chine_curve")
        sheer_curve = self._extract_curve(hull_geom, "sheer_curve")
        transom_outline = self._extract_curve(hull_geom, "transom_outline")

        return HullGeometryData(
            design_id=design_id,
            version_id=f"{design_id}:v{design_version}",
            sections=sections,
            keel_profile=keel_profile,
            stem_profile=stem_profile,
            chine_curve=chine_curve or None,
            sheer_curve=sheer_curve or None,
            transom_outline=transom_outline or None,
            loa=float(getattr(hull_geom, "loa", 0.0) or 0.0),
            lwl=float(getattr(hull_geom, "lwl", 0.0) or 0.0),
            beam=float(getattr(hull_geom, "beam", 0.0) or 0.0),
            draft=float(getattr(hull_geom, "draft", 0.0) or 0.0),
            volume=float(getattr(hull_geom, "volume", 0.0) or 0.0),
            wetted_surface=float(getattr(hull_geom, "wetted_surface", 0.0) or 0.0),
            waterplane_area=float(getattr(hull_geom, "waterplane_area", 0.0) or 0.0),
            openings=list(getattr(hull_geom, "openings", []) or []) or None,
            flow_paths=list(getattr(hull_geom, "flow_paths", []) or []) or None,
            attachments=list(getattr(hull_geom, "attachments", []) or []) or None,
        )

    def _extract_curve(self, hull_geom: Any, attr: str) -> List[Point3D]:
        points: List[Point3D] = []
        if hasattr(hull_geom, attr):
            curve = getattr(hull_geom, attr)
            if curve:
                for pt in curve:
                    if hasattr(pt, "x"):
                        points.append(Point3D(pt.x, pt.y, pt.z))
                    elif isinstance(pt, (list, tuple)) and len(pt) >= 3:
                        points.append(Point3D(pt[0], pt[1], pt[2]))
        return points

    def has_geometry(self, design_id: str) -> bool:
        # Geometry exists iff resources exist and contain at least one section
        return self._has_resources() and self._resources_have_sections()

    def get_geometry_version(self, design_id: str) -> Optional[str]:
        try:
            v = int(self._sm.get("design_version", 0))
        except Exception:
            v = 0
        return f"{design_id}:v{v}"

    def invalidate(self, design_id: str) -> None:
        keys = [k for k in self._cache.keys() if k.startswith(f"{design_id}:")]
        for k in keys:
            del self._cache[k]

    def invalidate_all(self) -> None:
        self._cache.clear()


class CompositeGeometryProvider:
    """
    Selects the enum-free design-language provider when resources exist,
    otherwise falls back to legacy HullGeneratorAdapter.
    """

    def __init__(self, design_language: DesignLanguageAdapter, legacy: HullGeneratorAdapter, state_manager: Optional["StateManager"] = None):
        self._dl = design_language
        self._legacy = legacy
        self._sm = state_manager

    def _legacy_enabled(self) -> bool:
        """
        Legacy hull generator fallback is for backwards compatibility only.
        New designs should be able to start blank and only become geometric once
        design-language resources exist.
        """
        import os
        # Global kill-switch (default: enabled to avoid breaking existing installs).
        env_enabled = os.environ.get("MAGNET_LEGACY_HULL_GENERATOR_ENABLED", "true").lower() == "true"
        if not env_enabled:
            return False
        # Per-design override
        try:
            if self._sm is not None and hasattr(self._sm, "get"):
                v = self._sm.get("metadata.legacy_geometry_fallback_enabled", True)
                return bool(v)
        except Exception:
            pass
        return True

    def _provider(self, design_id: str):
        if not self._legacy_enabled():
            return self._dl
        return self._dl if self._dl.has_geometry(design_id) else self._legacy

    def get_hull_geometry(self, design_id: str, lod: Optional[LODLevel] = None) -> HullGeometryData:
        return self._provider(design_id).get_hull_geometry(design_id, lod=lod)

    def has_geometry(self, design_id: str) -> bool:
        if not self._legacy_enabled():
            return self._dl.has_geometry(design_id)
        return self._dl.has_geometry(design_id) or self._legacy.has_geometry(design_id)

    def get_geometry_version(self, design_id: str) -> Optional[str]:
        return self._provider(design_id).get_geometry_version(design_id)

    def invalidate(self, design_id: str) -> None:
        self._dl.invalidate(design_id)
        self._legacy.invalidate(design_id)

    def invalidate_all(self) -> None:
        self._dl.invalidate_all()
        self._legacy.invalidate_all()
