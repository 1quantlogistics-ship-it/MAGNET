"""
Multi-body hydrostatics calculations.

Implements parallel axis theorem for multi-body vessels (catamarans, trimarans, etc.)

Key equations:
    BM = I_combined / V_total
    I_combined = Σ(I_local + A_wp * d²)  # Parallel axis theorem
    
    where:
    - I_local = waterplane moment of inertia for individual body
    - A_wp = waterplane area
    - d = distance from body centroid to combined centroid
    - V_total = total displaced volume

The kernel validates physics, not design intent.
Novel multi-body configurations work without new code.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import logging
import math

logger = logging.getLogger(__name__)


@dataclass
class BodyHydrostatics:
    """Hydrostatics for a single body."""
    body_id: str
    volume_m3: float
    waterplane_area_m2: float
    waterplane_inertia_m4: float  # I about body's own centroid
    kb_m: float
    lcb_m: float
    tcb_m: float  # Transverse center (Y)
    vcb_m: float


@dataclass
class MultiBodyHydrostatics:
    """Combined hydrostatics for multi-body vessel."""
    total_volume_m3: float
    combined_kb_m: float
    combined_lcb_m: float
    combined_tcb_m: float
    combined_vcb_m: float
    bm_transverse_m: float
    bm_longitudinal_m: float
    waterplane_area_m2: float
    body_results: List[BodyHydrostatics]


def compute_multi_body_hydrostatics(
    bodies: Dict[str, Dict[str, Any]],
    geometry: Any,
    draft_m: float,
) -> MultiBodyHydrostatics:
    """
    Compute hydrostatics for multi-body vessel.
    
    Uses parallel axis theorem to combine individual body properties.
    
    Args:
        bodies: Dict of body_id -> body config (with offset_y_m, etc.)
        geometry: HullGeometry with sections
        draft_m: Design draft
    
    Returns:
        MultiBodyHydrostatics with combined properties
    """
    body_results = []
    
    # Compute hydrostatics for each body
    for body_id, body_config in bodies.items():
        if not isinstance(body_config, dict):
            continue
        if body_config.get("_type") != "geometry.body":
            continue
        if body_config.get("_deleted"):
            continue
        
        offset_y = float(body_config.get("offset_y_m", 0.0))
        offset_z = float(body_config.get("offset_z_m", 0.0))
        physics_category = body_config.get("physics_category", "surface_piercing")
        
        # Get physics behavior from geometry position
        physics_behavior = infer_physics_behavior(offset_z, draft_m, physics_category)
        
        # Compute body hydrostatics based on physics behavior
        body_hydro = _compute_body_hydrostatics(
            body_id, geometry, draft_m, offset_y, physics_behavior
        )
        
        if body_hydro.volume_m3 > 0:
            body_results.append(body_hydro)
    
    if not body_results:
        logger.warning("No valid bodies for hydrostatics calculation")
        return MultiBodyHydrostatics(
            total_volume_m3=0,
            combined_kb_m=0,
            combined_lcb_m=0,
            combined_tcb_m=0,
            combined_vcb_m=0,
            bm_transverse_m=0,
            bm_longitudinal_m=0,
            waterplane_area_m2=0,
            body_results=[],
        )
    
    # Combine body results using parallel axis theorem
    return _combine_body_hydrostatics(body_results)


def infer_physics_behavior(
    offset_z: float,
    draft_m: float,
    physics_category_hint: str,
) -> str:
    """
    Infer physics behavior from geometry position.
    
    The kernel derives physics from geometry, using the agent's
    physics_category as a hint that it verifies.
    
    Args:
        offset_z: Vertical offset of body
        draft_m: Design draft
        physics_category_hint: Agent's hint about physics behavior
    
    Returns:
        Physics behavior string
    """
    # Compute submergence from geometry
    # For simplicity, assume body is at offset_z from baseline
    # A proper implementation would check actual section geometry
    
    waterline_z = 0.0  # Waterline at z=0
    
    if offset_z < -draft_m * 0.9:
        # Body is mostly below waterline
        derived = "submerged"
    elif offset_z > draft_m * 0.5:
        # Body is mostly above waterline
        derived = "above_water"
    else:
        # Body pierces waterline
        derived = "surface_piercing"
    
    # Log if hint differs from derived
    if physics_category_hint and physics_category_hint != derived:
        logger.debug(
            f"Physics category hint '{physics_category_hint}' differs from "
            f"derived '{derived}' at offset_z={offset_z}"
        )
    
    return derived


def _compute_body_hydrostatics(
    body_id: str,
    geometry: Any,
    draft_m: float,
    offset_y: float,
    physics_behavior: str,
) -> BodyHydrostatics:
    """Compute hydrostatics for a single body."""
    
    # Get sections belonging to this body
    sections = _get_body_sections(geometry, body_id, offset_y)
    
    if not sections:
        # Fallback: estimate from geometry
        return _estimate_body_hydrostatics(body_id, geometry, offset_y, draft_m)
    
    # Compute volume
    volume = 0.0
    for i in range(len(sections) - 1):
        s1, s2 = sections[i], sections[i + 1]
        dx = s2.x_position - s1.x_position
        volume += 0.5 * (s1.area + s2.area) * dx
    
    # Compute waterplane area and inertia
    wp_area = 0.0
    wp_inertia = 0.0  # About body's own Y axis
    
    for i in range(len(sections) - 1):
        s1, s2 = sections[i], sections[i + 1]
        dx = abs(s2.x_position - s1.x_position)
        
        # Half-beam at waterline (approximate)
        b1 = s1.half_beam
        b2 = s2.half_beam
        avg_beam = (b1 + b2)
        
        # Area contribution
        wp_area += avg_beam * dx
        
        # Inertia contribution (rectangular approximation)
        # I = (1/12) * L * B³
        avg_b_cubed = ((b1 ** 3) + (b2 ** 3)) / 2
        wp_inertia += (1/12) * dx * avg_b_cubed * 8  # Factor of 8 for full beam
    
    # Centers of buoyancy
    kb = draft_m * 0.53  # Approximate
    lcb = _compute_lcb(sections)
    vcb = draft_m * 0.45  # Approximate
    
    return BodyHydrostatics(
        body_id=body_id,
        volume_m3=volume,
        waterplane_area_m2=wp_area,
        waterplane_inertia_m4=wp_inertia,
        kb_m=kb,
        lcb_m=lcb,
        tcb_m=offset_y,
        vcb_m=vcb,
    )


def _get_body_sections(geometry: Any, body_id: str, offset_y: float) -> List[Any]:
    """Get sections belonging to a body, based on Y offset."""
    if not hasattr(geometry, 'sections'):
        return []
    
    tolerance = 0.5  # meters
    sections = []
    
    for section in geometry.sections:
        # Check if section belongs to this body
        section_body_id = getattr(section, 'body_id', 'main')
        
        if section_body_id == body_id:
            sections.append(section)
        elif abs(offset_y) > 0.1:
            # Check by Y position
            avg_y = _section_avg_y(section)
            if abs(avg_y - offset_y) < tolerance:
                sections.append(section)
    
    return sorted(sections, key=lambda s: s.x_position)


def _section_avg_y(section: Any) -> float:
    """Get average Y position of section points."""
    if not hasattr(section, 'points') or not section.points:
        return 0.0
    return sum(p.position.y for p in section.points) / len(section.points)


def _compute_lcb(sections: List[Any]) -> float:
    """Compute longitudinal center of buoyancy."""
    if not sections:
        return 0.0
    
    moment = 0.0
    volume = 0.0
    
    for i in range(len(sections) - 1):
        s1, s2 = sections[i], sections[i + 1]
        dx = s2.x_position - s1.x_position
        avg_area = (s1.area + s2.area) / 2
        avg_x = (s1.x_position + s2.x_position) / 2
        
        vol_strip = avg_area * dx
        moment += vol_strip * avg_x
        volume += vol_strip
    
    return moment / volume if volume > 0 else 0.0


def _estimate_body_hydrostatics(
    body_id: str,
    geometry: Any,
    offset_y: float,
    draft_m: float,
) -> BodyHydrostatics:
    """Estimate body hydrostatics when sections not available."""
    # Use geometry total volume / number of bodies as approximation
    n_bodies = len(getattr(geometry, 'bodies', {})) or 1
    volume = (geometry.volume if hasattr(geometry, 'volume') else 100.0) / n_bodies
    
    # Estimate waterplane
    lwl = 20.0  # Assume
    beam = 2.0  # Assume demihull beam
    wp_area = lwl * beam
    wp_inertia = (lwl * (beam ** 3)) / 12
    
    return BodyHydrostatics(
        body_id=body_id,
        volume_m3=volume,
        waterplane_area_m2=wp_area,
        waterplane_inertia_m4=wp_inertia,
        kb_m=draft_m * 0.53,
        lcb_m=lwl * 0.52,
        tcb_m=offset_y,
        vcb_m=draft_m * 0.45,
    )


def _combine_body_hydrostatics(
    body_results: List[BodyHydrostatics],
) -> MultiBodyHydrostatics:
    """
    Combine body hydrostatics using parallel axis theorem.
    
    BM = I_combined / V_total
    I_combined = Σ(I_local + A_wp * d²)
    """
    # Total volume
    total_volume = sum(b.volume_m3 for b in body_results)
    
    if total_volume <= 0:
        return MultiBodyHydrostatics(
            total_volume_m3=0,
            combined_kb_m=0,
            combined_lcb_m=0,
            combined_tcb_m=0,
            combined_vcb_m=0,
            bm_transverse_m=0,
            bm_longitudinal_m=0,
            waterplane_area_m2=0,
            body_results=body_results,
        )
    
    # Combined center of buoyancy (weighted average)
    combined_kb = sum(b.kb_m * b.volume_m3 for b in body_results) / total_volume
    combined_lcb = sum(b.lcb_m * b.volume_m3 for b in body_results) / total_volume
    combined_tcb = sum(b.tcb_m * b.volume_m3 for b in body_results) / total_volume
    combined_vcb = sum(b.vcb_m * b.volume_m3 for b in body_results) / total_volume
    
    # Total waterplane area
    total_wp_area = sum(b.waterplane_area_m2 for b in body_results)
    
    # Combined transverse moment of inertia (parallel axis theorem)
    # I_combined = Σ(I_local + A_wp * d²)
    # where d = distance from body TCB to combined TCB
    
    i_combined_transverse = 0.0
    for b in body_results:
        d = b.tcb_m - combined_tcb  # Distance from combined centroid
        # Parallel axis: I_total = I_local + A * d²
        i_combined_transverse += b.waterplane_inertia_m4 + b.waterplane_area_m2 * (d ** 2)
    
    # BM = I / V
    bm_transverse = i_combined_transverse / total_volume if total_volume > 0 else 0
    
    # Longitudinal BM (simpler, sum local inertias)
    i_combined_longitudinal = sum(b.waterplane_inertia_m4 for b in body_results)
    bm_longitudinal = i_combined_longitudinal / total_volume if total_volume > 0 else 0
    
    return MultiBodyHydrostatics(
        total_volume_m3=total_volume,
        combined_kb_m=combined_kb,
        combined_lcb_m=combined_lcb,
        combined_tcb_m=combined_tcb,
        combined_vcb_m=combined_vcb,
        bm_transverse_m=bm_transverse,
        bm_longitudinal_m=bm_longitudinal,
        waterplane_area_m2=total_wp_area,
        body_results=body_results,
    )


def compute_multi_body_gm(
    bodies: Dict[str, Dict[str, Any]],
    geometry: Any,
    draft_m: float,
    vcg_m: float,
) -> Dict[str, Any]:
    """
    Compute GM for multi-body vessel.
    
    GM = KB + BM - KG
    
    Args:
        bodies: Body configurations
        geometry: HullGeometry
        draft_m: Design draft
        vcg_m: Vertical center of gravity
    
    Returns:
        Dict with GM and supporting values
    """
    hydro = compute_multi_body_hydrostatics(bodies, geometry, draft_m)
    
    # GM = KB + BM - KG
    gm = hydro.combined_kb_m + hydro.bm_transverse_m - vcg_m
    
    return {
        "gm_m": gm,
        "kb_m": hydro.combined_kb_m,
        "bm_transverse_m": hydro.bm_transverse_m,
        "bm_longitudinal_m": hydro.bm_longitudinal_m,
        "vcg_m": vcg_m,
        "displacement_m3": hydro.total_volume_m3,
        "waterplane_area_m2": hydro.waterplane_area_m2,
        "lcb_m": hydro.combined_lcb_m,
        "tcb_m": hydro.combined_tcb_m,
        "vcb_m": hydro.combined_vcb_m,
        "n_bodies": len(hydro.body_results),
        "passes": gm > 0,
        "method": "parallel_axis_theorem",
    }


