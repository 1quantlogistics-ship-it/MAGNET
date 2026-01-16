"""
Compile design language state into HullGeometry.

This is the bridge between the design language and the existing geometry pipeline.

NO SECOND GEOMETRY ENGINE:
- Everything compiles INTO existing HullGeometry, HullSection, etc.
- Novel forms emerge from primitive composition, not new geometry classes
- The kernel validates physics, not design intent
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging

from magnet.hull_gen.geometry import (
    HullGeometry, 
    HullSection, 
    SectionPoint,
    Point3D,
    LongitudinalFeature,
)
from .quality_gates import check_resolution, check_fairness
from .section_compiler import compile_sections, compile_sections_for_bodies


logger = logging.getLogger(__name__)


class CompilationError(Exception):
    """Raised when compilation fails."""
    pass


@dataclass
class CompilationResult:
    """Result of compiling design language state."""
    geometry: HullGeometry
    body_geometries: Dict[str, HullGeometry]  # For multi-body
    warnings: List[str]
    

def compile_to_geometry(
    state: Dict[str, Any],
    loa: Optional[float] = None,
) -> HullGeometry:
    """
    Compile design language state into HullGeometry.
    
    This is the main entry point for converting design language resources
    into the canonical geometry representation.
    
    Args:
        state: Design state with resources, hull params, etc.
        loa: Length overall (extracted from state if not provided)
    
    Returns:
        HullGeometry object for tessellation/hydrostatics/export
    
    Raises:
        CompilationError: If compilation fails
    """
    resources = state.get("resources", {})
    
    # Get LOA from state or default
    if loa is None:
        loa = state.get("hull", {}).get("loa")
        if loa is None:
            loa = state.get("hull", {}).get("lwl")
        if loa is None:
            loa = 25.0  # Reasonable default
    
    loa = float(loa)
    
    # Extract bodies
    bodies = _extract_bodies(resources)
    
    # Decide single vs multi-body compilation
    if len(bodies) > 1:
        geometry = _compile_multi_body(resources, bodies, loa, state)
    else:
        geometry = _compile_single_hull(resources, loa, state)

    _apply_quality_gates(geometry)
    return geometry


def _extract_bodies(resources: Dict[str, Dict]) -> Dict[str, Dict]:
    """Extract geometry.body resources."""
    bodies: Dict[str, Dict] = {}

    # Collect body_ids referenced by live sections (authoritative truth).
    referenced_body_ids = set()
    for _rid, resource in resources.items():
        if resource.get("_type") == "geometry.section" and not resource.get("_deleted"):
            bid = resource.get("body_id")
            if isinstance(bid, str) and bid:
                referenced_body_ids.add(bid)

    for rid, resource in resources.items():
        if resource.get("_type") == "geometry.body":
            if not resource.get("_deleted"):
                bodies[rid] = resource
            else:
                # Control-plane recovery: if a body is marked deleted but still referenced
                # by non-deleted sections, treat it as active for compilation.
                if rid in referenced_body_ids:
                    logger.warning(
                        f"Body {rid} is marked _deleted but is still referenced by live sections; "
                        f"treating as active for compilation."
                    )
                    bodies[rid] = resource

    # If sections reference a body_id with no body resource at all, create a minimal
    # implicit body config so compilation can proceed deterministically.
    for bid in referenced_body_ids:
        if bid not in bodies and bid != "main":
            logger.warning(
                f"Sections reference body_id '{bid}' but no geometry.body exists; "
                f"creating implicit body config with zero offsets."
            )
            bodies[bid] = {
                "_type": "geometry.body",
                "_id": bid,
                "body_type": "implicit_body",
                "physics_category": "surface_piercing",
                "offset_x_m": 0.0,
                "offset_y_m": 0.0,
                "offset_z_m": 0.0,
            }
    return bodies


def _extract_discontinuities(resources: Dict[str, Dict]) -> List[Dict]:
    """Extract geometry.discontinuity resources."""
    discs = []
    for rid, resource in resources.items():
        if resource.get("_type") == "geometry.discontinuity":
            if not resource.get("_deleted"):
                resource["_id"] = rid
                discs.append(resource)
    return discs


def _extract_surfaces(resources: Dict[str, Dict]) -> Dict[str, Dict]:
    """Extract geometry.surface resources."""
    surfaces = {}
    for rid, resource in resources.items():
        if resource.get("_type") == "geometry.surface":
            if not resource.get("_deleted"):
                surfaces[rid] = resource
    return surfaces


def _extract_openings(resources: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Extract geometry.opening resources (pass-through)."""
    openings: List[Dict[str, Any]] = []
    for rid, resource in resources.items():
        if resource.get("_type") == "geometry.opening" and not resource.get("_deleted"):
            r = dict(resource)
            r["_id"] = r.get("_id") or rid
            openings.append(r)
    return sorted(openings, key=lambda r: str(r.get("_id", "")))


def _extract_flow_paths(resources: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Extract geometry.flow_path resources (pass-through)."""
    fps: List[Dict[str, Any]] = []
    for rid, resource in resources.items():
        if resource.get("_type") == "geometry.flow_path" and not resource.get("_deleted"):
            r = dict(resource)
            r["_id"] = r.get("_id") or rid
            fps.append(r)
    return sorted(fps, key=lambda r: str(r.get("_id", "")))


def _extract_attachments(resources: Dict[str, Dict]) -> List[Dict[str, Any]]:
    """Extract geometry.attachment resources (pass-through)."""
    atts: List[Dict[str, Any]] = []
    for rid, resource in resources.items():
        if resource.get("_type") == "geometry.attachment" and not resource.get("_deleted"):
            r = dict(resource)
            r["_id"] = r.get("_id") or rid
            atts.append(r)
    return sorted(atts, key=lambda r: str(r.get("_id", "")))


def _compile_single_hull(
    resources: Dict[str, Dict],
    loa: float,
    state: Dict[str, Any],
) -> HullGeometry:
    """Compile single-body hull geometry."""
    
    # Compile sections
    sections = compile_sections(resources, loa)
    
    if not sections:
        raise CompilationError("No sections defined - cannot create geometry")
    
    # Update x positions
    for section in sections:
        for pt in section.points:
            pt.position.x = section.x_position
    
    # Get hull parameters
    hull_params = state.get("hull", {})
    beam = hull_params.get("beam", _estimate_beam(sections))
    draft = hull_params.get("draft", _estimate_draft(sections))
    
    # Create geometry
    geometry = HullGeometry(
        sections=sections,
    )
    
    # Set properties
    geometry.hull_id = state.get("design_id", "")
    
    # Compile discontinuities into longitudinal features
    discontinuities = _extract_discontinuities(resources)
    geometry.longitudinal_features = _compile_discontinuities(
        discontinuities, sections, loa
    )

    # Phase 3: universal primitives (pass-through storage)
    geometry.openings = _extract_openings(resources)
    geometry.flow_paths = _extract_flow_paths(resources)
    geometry.attachments = _extract_attachments(resources)
    
    # Compute volume and other properties
    for section in sections:
        section.compute_area(waterline_z=0.0)
    
    # Sort sections by x_position for correct volume integration
    geometry.sections = sorted(geometry.sections, key=lambda s: s.x_position)
    geometry.compute_volume()
    
    # Take absolute value of volume (geometry is correct, sign comes from integration direction)
    geometry.volume = abs(geometry.volume)
    
    return geometry


def _compile_multi_body(
    resources: Dict[str, Dict],
    bodies: Dict[str, Dict],
    loa: float,
    state: Dict[str, Any],
) -> HullGeometry:
    """
    Compile multi-body hull geometry.
    
    Multi-body vessels are created by composing geometry.body primitives.
    Novel configurations work without new code.
    """
    
    # Group sections by body_id
    body_sections = compile_sections_for_bodies(resources, bodies, loa)
    
    if not body_sections:
        raise CompilationError("No sections defined for any body")
    
    # Apply body offsets to sections
    all_sections = []
    for body_id, body_config in bodies.items():
        sections = body_sections.get(body_id, [])
        
        if not sections:
            logger.warning(f"Body {body_id} has no sections")
            continue
        
        # Get offsets
        offset_y = float(body_config.get("offset_y_m", 0.0))
        offset_z = float(body_config.get("offset_z_m", 0.0))
        offset_x = float(body_config.get("offset_x_m", 0.0))
        
        # Apply offsets to section points
        for section in sections:
            section.x_position += offset_x
            for pt in section.points:
                pt.position.x = section.x_position
                pt.position.y += offset_y
                pt.position.z += offset_z
            
            # Update key points
            if section.keel_point:
                section.keel_point = Point3D(
                    section.keel_point.x + offset_x,
                    section.keel_point.y + offset_y,
                    section.keel_point.z + offset_z,
                )
        
        all_sections.extend(sections)
    
    # Sort all sections by x position
    all_sections.sort(key=lambda s: s.x_position)
    
    # Create combined geometry
    geometry = HullGeometry(
        sections=all_sections,
    )
    
    geometry.hull_id = state.get("design_id", "")
    
    # Store body configuration for hydrostatics
    # This is crucial for parallel axis theorem BM calculation
    geometry.bodies = bodies  # type: ignore
    
    # Compile discontinuities
    discontinuities = _extract_discontinuities(resources)
    geometry.longitudinal_features = _compile_discontinuities(
        discontinuities, all_sections, loa
    )

    # Phase 3: universal primitives (pass-through storage)
    geometry.openings = _extract_openings(resources)
    geometry.flow_paths = _extract_flow_paths(resources)
    geometry.attachments = _extract_attachments(resources)
    
    # Compute areas and volume
    for section in all_sections:
        section.compute_area(waterline_z=0.0)
    
    # Sort sections by x_position for correct volume integration
    geometry.sections = sorted(geometry.sections, key=lambda s: s.x_position)
    geometry.compute_volume()
    
    # Take absolute value of volume (geometry is correct, sign comes from integration direction)
    geometry.volume = abs(geometry.volume)
    
    return geometry


def _apply_quality_gates(geometry: HullGeometry) -> None:
    """
    Run advisory quality gates (resolution, fairness) and attach warnings to metadata.
    """
    sections = geometry.sections or []
    resolution_warnings = check_resolution(sections)
    fairness_warnings = check_fairness(sections)

    if not geometry.metadata:
        geometry.metadata = {}
    quality_list = geometry.metadata.setdefault("quality_warnings", [])

    # Store as dicts for serialization
    for w in resolution_warnings + fairness_warnings:
        quality_list.append(w.to_dict())


def _compile_discontinuities(
    discontinuities: List[Dict],
    sections: List[HullSection],
    loa: float,
) -> List[LongitudinalFeature]:
    """
    Compile discontinuity resources into LongitudinalFeature objects.
    
    Discontinuities (steps, chines, spray deflectors) become hard edges
    in the mesh for rendering.
    """
    features = []
    
    for disc in discontinuities:
        disc_type = disc.get("discontinuity_type", "generic")
        disc_id = disc.get("_id", f"disc_{len(features)}")
        
        station_start = float(disc.get("station_start", 0.0))
        station_end = float(disc.get("station_end", 1.0))
        height_ratio = float(disc.get("height_ratio", 0.5))
        depth_m = float(disc.get("depth_m", 0.05))
        
        # Generate feature points along the discontinuity
        points = []
        for section in sections:
            if station_start <= section.station <= station_end:
                # Find point at height_ratio
                if section.points:
                    # Interpolate to find Y at given height
                    z_target = _interpolate_z_from_height_ratio(section, height_ratio)
                    y_at_height = _interpolate_y_at_z(section, z_target)
                    
                    if y_at_height is not None:
                        points.append(Point3D(
                            x=section.x_position,
                            y=y_at_height,
                            z=z_target,
                        ))
        
        if points:
            feature = LongitudinalFeature(
                feature_type=disc_type,
                feature_id=disc_id,
                points=points,
                is_hard=True,  # Discontinuities are hard edges
            )
            features.append(feature)
    
    return features


def _interpolate_z_from_height_ratio(
    section: HullSection, 
    height_ratio: float
) -> float:
    """Get Z coordinate from height ratio (0=keel, 1=deck)."""
    if not section.points:
        return 0.0
    
    z_min = min(p.position.z for p in section.points)
    z_max = max(p.position.z for p in section.points)
    
    return z_min + height_ratio * (z_max - z_min)


def _interpolate_y_at_z(section: HullSection, z: float) -> Optional[float]:
    """Interpolate Y coordinate at given Z."""
    if len(section.points) < 2:
        return None
    
    # Find bracketing points
    for i in range(len(section.points) - 1):
        z1 = section.points[i].position.z
        z2 = section.points[i + 1].position.z
        
        if min(z1, z2) <= z <= max(z1, z2):
            # Linear interpolation
            if z2 != z1:
                t = (z - z1) / (z2 - z1)
            else:
                t = 0.5
            y1 = section.points[i].position.y
            y2 = section.points[i + 1].position.y
            return y1 + t * (y2 - y1)
    
    return None


def _estimate_beam(sections: List[HullSection]) -> float:
    """Estimate beam from sections."""
    max_beam = 0.0
    for section in sections:
        for pt in section.points:
            max_beam = max(max_beam, abs(pt.position.y) * 2)
    return max_beam if max_beam > 0 else 6.0


def _estimate_draft(sections: List[HullSection]) -> float:
    """Estimate draft from sections."""
    min_z = 0.0
    for section in sections:
        for pt in section.points:
            min_z = min(min_z, pt.position.z)
    return abs(min_z) if min_z < 0 else 1.5

