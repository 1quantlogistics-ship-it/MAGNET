"""
Kernel-owned type schemas for design language resources.

Sacred Invariants:
- Kernel knows geometry, not design
- Any hull form that requires a new language primitive is a failure
- body_type, physics_category are FREEFORM strings (not enums)
- Agents coordinate on geometry only, never on "features"
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FieldSchema:
    """Schema for a single field."""
    name: str
    field_type: str  # "float", "str", "int", "list", "dict", "bool"
    required: bool = False
    default: Any = None
    description: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class TypeSchema:
    """Schema for a resource type."""
    type_name: str
    fields: List[FieldSchema] = field(default_factory=list)
    mirrorable: bool = False
    mirror_fields: List[str] = field(default_factory=list)
    alignable_axes: List[str] = field(default_factory=list)
    deprecated: bool = False
    deprecated_message: str = ""
    
    def validate(self, properties: Dict[str, Any]) -> List[str]:
        """Validate properties against schema. Returns list of errors."""
        errors = []
        
        # Check required fields
        for f in self.fields:
            if f.required and f.name not in properties:
                errors.append(f"Missing required field: {f.name}")
        
        # Check types and bounds
        for key, value in properties.items():
            if key.startswith('_'):
                continue  # Skip internal fields
            
            field_schema = next((f for f in self.fields if f.name == key), None)
            if not field_schema:
                # Allow unknown fields for extensibility
                continue
            
            # Type checking
            if field_schema.field_type == "float" and value is not None:
                if not isinstance(value, (int, float)):
                    errors.append(f"Field {key} must be a number, got {type(value).__name__}")
                elif field_schema.min_value is not None and value < field_schema.min_value:
                    errors.append(f"Field {key} must be >= {field_schema.min_value}")
                elif field_schema.max_value is not None and value > field_schema.max_value:
                    errors.append(f"Field {key} must be <= {field_schema.max_value}")
            
            elif field_schema.field_type == "int" and value is not None:
                if not isinstance(value, int):
                    errors.append(f"Field {key} must be an integer")
            
            elif field_schema.field_type == "list" and value is not None:
                if not isinstance(value, list):
                    errors.append(f"Field {key} must be a list")
            
            elif field_schema.field_type == "bool" and value is not None:
                if not isinstance(value, bool):
                    errors.append(f"Field {key} must be a boolean")
        
        return errors
    
    def apply_defaults(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values from schema."""
        result = dict(properties)
        for f in self.fields:
            if f.name not in result and f.default is not None:
                result[f.name] = f.default
        return result


# =============================================================================
# CANONICAL TYPE REGISTRY
# =============================================================================
# 
# These are the GEOMETRY primitives that agents compose.
# Novel forms emerge from composition, not from adding new types.
#
# body_type, physics_category, surface_type, discontinuity_type, medium
# are ALL FREEFORM STRINGS. The kernel validates physics, not names.
# =============================================================================

TYPE_REGISTRY: Dict[str, TypeSchema] = {
    
    # =========================================================================
    # SECTION - Cross-section profile
    # =========================================================================
    "geometry.section": TypeSchema(
        type_name="geometry.section",
        fields=[
            FieldSchema("station", "float", required=True, 
                       description="Position along hull (0=bow, 1=stern)",
                       min_value=0.0, max_value=1.0),
            FieldSchema("body_id", "str", default="main",
                       description="Which body this section belongs to"),
            # Polygon definition (default)
            FieldSchema("points", "list",
                       description="Section profile points [[y, z], ...]"),
            # Optional edge typing along the section curve to control hard edges/chines.
            # Accepts freeform strings but compiler maps common values to EdgeType.
            FieldSchema("edge_types", "list",
                       description="Optional edge types along section curve (e.g., smooth|hard|crease)"),
            # NURBS definition (alternative)
            FieldSchema("definition_type", "str", default="polygon",
                       description="'polygon' or 'nurbs'"),
            FieldSchema("control_points", "list",
                       description="NURBS control points [[y, z, weight], ...]"),
            FieldSchema("knots", "list", description="NURBS knot vector"),
            FieldSchema("degree", "int", default=3, description="NURBS curve degree"),
        ],
        mirrorable=False,  # Sections are symmetric by default
    ),
    
    # =========================================================================
    # BODY - Distinct solid volume (hull, pontoon, outrigger, etc.)
    # =========================================================================
    "geometry.body": TypeSchema(
        type_name="geometry.body",
        fields=[
            # body_type is FREEFORM - agent can use any string
            # "main_hull", "outrigger", "pontoon", "hydrofoil_strut", "sail_keel"
            FieldSchema("body_type", "str", default="hull",
                       description="Freeform body type - any string the agent wants"),
            # physics_category hints at physics behavior, also freeform
            # Common: "surface_piercing", "submerged", "above_water"
            # Novel: "cavitating", "spray_zone", "partially_submerged"
            FieldSchema("physics_category", "str", default="surface_piercing",
                       description="Physics behavior hint - freeform string"),
            FieldSchema("offset_x_m", "float", default=0.0,
                       description="X offset from origin (along hull length)"),
            FieldSchema("offset_y_m", "float", default=0.0,
                       description="Y offset from centerline (positive = port)"),
            FieldSchema("offset_z_m", "float", default=0.0,
                       description="Z offset (positive = up)"),
        ],
        mirrorable=True,
        mirror_fields=["offset_y_m"],  # Y-axis mirrored
    ),
    
    # =========================================================================
    # SURFACE - Lofted or NURBS surface
    # =========================================================================
    "geometry.surface": TypeSchema(
        type_name="geometry.surface",
        fields=[
            # surface_type is FREEFORM - "hull_shell", "deck", "wetdeck", "transom"
            FieldSchema("surface_type", "str", default="hull_shell",
                       description="Freeform surface type"),
            FieldSchema("definition", "str", required=True,
                       description="'lofted' or 'nurbs'"),
            FieldSchema("section_ids", "list",
                       description="Section IDs for lofted surfaces"),
            FieldSchema("control_points", "list",
                       description="NURBS control net for NURBS surfaces"),
            FieldSchema("u_knots", "list", description="U-direction knot vector"),
            FieldSchema("v_knots", "list", description="V-direction knot vector"),
            FieldSchema("u_degree", "int", default=3),
            FieldSchema("v_degree", "int", default=3),
            FieldSchema("body_id", "str", default="main"),
        ],
    ),
    
    # =========================================================================
    # DISCONTINUITY - Steps, chines, spray rails, knuckles
    # =========================================================================
    "geometry.discontinuity": TypeSchema(
        type_name="geometry.discontinuity",
        fields=[
            # discontinuity_type is FREEFORM
            # "transverse_step", "longitudinal_chine", "spray_deflector", "knuckle"
            FieldSchema("discontinuity_type", "str", required=True,
                       description="Freeform discontinuity type"),
            FieldSchema("station_start", "float", required=True,
                       min_value=0.0, max_value=1.0),
            FieldSchema("station_end", "float", required=True,
                       min_value=0.0, max_value=1.0),
            FieldSchema("height_ratio", "float", default=0.5,
                       description="Vertical position as fraction of depth",
                       min_value=0.0, max_value=1.0),
            FieldSchema("depth_m", "float", default=0.05,
                       description="Depth/height of discontinuity"),
            FieldSchema("angle_deg", "float", default=0.0,
                       description="Angle of discontinuity surface"),
            FieldSchema("body_id", "str", default="main"),
            FieldSchema("profile", "str", default="linear",
                       description="Profile shape: 'linear', 'curved', etc."),
        ],
        mirrorable=True,
        mirror_fields=[],  # Usually symmetric about centerline
    ),
    
    # =========================================================================
    # ATTACHMENT - Connection between bodies
    # =========================================================================
    "geometry.attachment": TypeSchema(
        type_name="geometry.attachment",
        fields=[
            FieldSchema("parent_body_id", "str", required=True),
            FieldSchema("child_body_id", "str", required=True),
            # attachment_type is FREEFORM - "rigid", "hinged", "structural_beam"
            FieldSchema("attachment_type", "str", default="rigid",
                       description="Freeform attachment type"),
            FieldSchema("offset_x_m", "float", default=0.0),
            FieldSchema("offset_y_m", "float", default=0.0),
            FieldSchema("offset_z_m", "float", default=0.0),
            # Phase 3B: Optional explicit buoyancy semantics (kept opt-in to avoid implied physics)
            FieldSchema(
                "buoyancy_volume_m3",
                "float",
                description="Optional: explicit buoyant volume contribution (m^3). If set, hydrostatics may apply it.",
                min_value=0.0,
            ),
            FieldSchema(
                "buoyancy_center",
                "list",
                description="Optional: [x,y,z] center for buoyancy_volume_m3 (m). Defaults to offsets if omitted.",
            ),
            # Phase 3C: Optional explicit mass/drag semantics (kept opt-in to avoid implied physics)
            FieldSchema(
                "mass_kg",
                "float",
                description="Optional: explicit mass contribution (kg). If set, weight estimation may incorporate it.",
                min_value=0.0,
            ),
            FieldSchema(
                "mass_center",
                "list",
                description="Optional: [x,y,z] center of mass for mass_kg (m). Defaults to buoyancy_center/offsets if omitted.",
            ),
            FieldSchema(
                "drag_area_m2",
                "float",
                description="Optional: equivalent drag area CdA (m^2) for resistance penalty at design speed.",
                min_value=0.0,
            ),
            FieldSchema(
                "drag_coefficient",
                "float",
                description="Optional: drag coefficient Cd for drag_area_m2 or inferred area; defaults to 1.0 if needed.",
                min_value=0.0,
            ),
        ],
    ),
    
    # =========================================================================
    # FLOW_PATH - Ventilation, cooling, exhaust paths
    # =========================================================================
    "geometry.flow_path": TypeSchema(
        type_name="geometry.flow_path",
        fields=[
            # medium is FREEFORM - "air", "water", "exhaust", "coolant"
            FieldSchema("medium", "str", required=True,
                       description="Freeform medium type"),
            FieldSchema("inlet_point", "list", required=True,
                       description="[x, y, z] inlet position"),
            FieldSchema("outlet_point", "list", required=True,
                       description="[x, y, z] outlet position"),
            FieldSchema("cross_section_m2", "float",
                       description="Flow cross-section area"),
            FieldSchema("body_id", "str", default="main"),
            # Phase 3B: optional explicit volume semantics (rare; default diagnostic-only)
            FieldSchema(
                "void_volume_m3",
                "float",
                description="Optional: explicit void volume (m^3) to subtract from hydrostatics if submerged.",
                min_value=0.0,
            ),
            # Phase 3C: Optional explicit resistance/weight semantics (kept opt-in)
            FieldSchema(
                "loss_coefficient",
                "float",
                description="Optional: dimensionless loss coefficient K for intake/outlet resistance penalty (default model uses K≈2.0 when medium='water').",
                min_value=0.0,
            ),
            FieldSchema(
                "mass_kg",
                "float",
                description="Optional: explicit mass contribution for flow hardware (kg). If set, weight estimation may incorporate it.",
                min_value=0.0,
            ),
            FieldSchema(
                "mass_center",
                "list",
                description="Optional: [x,y,z] center of mass for mass_kg (m). Defaults to inlet_point if omitted.",
            ),
        ],
        mirrorable=True,
        mirror_fields=["inlet_point", "outlet_point"],
    ),
    
    # =========================================================================
    # OPENING - Vents, hatches, intakes, cutouts
    # =========================================================================
    "geometry.opening": TypeSchema(
        type_name="geometry.opening",
        fields=[
            FieldSchema("surface_id", "str", required=True,
                       description="Which surface this opening is in"),
            FieldSchema("position", "list", required=True,
                       description="[x, y, z] center position"),
            FieldSchema("dimensions", "list", required=True,
                       description="[width, height] or [radius]"),
            # shape is FREEFORM - "rectangular", "circular", "custom", "naca_duct"
            FieldSchema("shape", "str", default="rectangular",
                       description="Freeform shape type"),
            FieldSchema("purpose", "str",
                       description="Freeform description of purpose"),
            FieldSchema("body_id", "str", default="main",
                       description="Which body this opening belongs to (defaults to main)"),
            # Phase 3B: Optional explicit buoyancy semantics (kept opt-in to avoid implied physics)
            FieldSchema(
                "through_hull_length_m",
                "float",
                description="Optional: length of void through the hull (m). If set, hydrostatics may subtract area*length when submerged.",
                min_value=0.0,
            ),
            FieldSchema(
                "void_volume_m3",
                "float",
                description="Optional: explicit void volume (m^3) to subtract from hydrostatics if submerged (overrides through_hull_length_m).",
                min_value=0.0,
            ),
            # Phase 3C: Optional explicit resistance/weight semantics (kept opt-in)
            FieldSchema(
                "drag_area_m2",
                "float",
                description="Optional: equivalent drag area CdA (m^2) for resistance penalty at design speed.",
                min_value=0.0,
            ),
            FieldSchema(
                "drag_coefficient",
                "float",
                description="Optional: drag coefficient Cd (for derived area); defaults to 1.0 if needed.",
                min_value=0.0,
            ),
            FieldSchema(
                "loss_coefficient",
                "float",
                description="Optional: dimensionless loss coefficient K for opening-induced resistance penalty (e.g., thruster tunnel).",
                min_value=0.0,
            ),
            FieldSchema(
                "mass_kg",
                "float",
                description="Optional: explicit mass contribution for hardware associated with opening (kg).",
                min_value=0.0,
            ),
            FieldSchema(
                "mass_center",
                "list",
                description="Optional: [x,y,z] center of mass for mass_kg (m). Defaults to position if omitted.",
            ),
        ],
        mirrorable=True,
        mirror_fields=["position"],
    ),
}

def _normalize_properties(resource_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize equivalent field names to the kernel's canonical schema.

    This is NOT design recognition and NOT enumeration: it only maps
    synonymous *field names* so agents/clients that use older keys
    still compile into the same canonical geometry pipeline.
    """
    if not properties:
        return properties

    p = dict(properties)

    # geometry.section: allow station_fraction as synonym for station (0..1)
    if resource_type == "geometry.section":
        if "station" not in p and "station_fraction" in p:
            p["station"] = p["station_fraction"]
            # Keep state canonical (avoid drift)
            del p["station_fraction"]

        # Normalize points shape:
        # - Canonical: [[y, z], ...]
        # - Also accept [{"y":..,"z":..}, ...] (common LLM output) and normalize.
        pts = p.get("points")
        if isinstance(pts, list) and pts:
            if isinstance(pts[0], dict) and ("y" in pts[0] and "z" in pts[0]):
                norm = []
                for item in pts:
                    if not isinstance(item, dict):
                        continue
                    # Only normalize true 2D points. If an agent emits x/y/z (or other keys),
                    # keep the original shape so validate_resource can surface an error instead
                    # of silently dropping X.
                    if "x" in item:
                        norm.append(item)
                        continue
                    if "y" in item and "z" in item:
                        norm.append([item.get("y"), item.get("z")])
                p["points"] = norm
            # Normalize sign mistakes: section points are half-section magnitudes in body-local frame.
            # If an agent emits negative y (often by "mirroring" manually), convert to abs(y).
            pts2 = p.get("points")
            if isinstance(pts2, list) and pts2 and isinstance(pts2[0], (list, tuple)):
                norm2 = []
                for pt in pts2:
                    # Only canonicalize sign for true 2D pairs; do NOT truncate [x,y,z] triples.
                    if isinstance(pt, (list, tuple)) and len(pt) == 2:
                        y, z = pt[0], pt[1]
                        if isinstance(y, (int, float)) and isinstance(z, (int, float)):
                            norm2.append([abs(float(y)), float(z)])
                        else:
                            norm2.append(list(pt))
                    else:
                        norm2.append(pt)
                p["points"] = norm2

    # geometry.surface: allow definition_type as synonym for definition
    if resource_type == "geometry.surface":
        if "definition" not in p and "definition_type" in p:
            p["definition"] = p["definition_type"]
            del p["definition_type"]

    # geometry.discontinuity: allow type as synonym for discontinuity_type
    if resource_type == "geometry.discontinuity":
        if "discontinuity_type" not in p and "type" in p:
            p["discontinuity_type"] = p["type"]
            del p["type"]

    # geometry.opening / flow_path / attachment: allow mass_center as dict {x,y,z}
    if resource_type in ("geometry.opening", "geometry.flow_path", "geometry.attachment"):
        mc = p.get("mass_center")
        if isinstance(mc, dict) and ("x" in mc and "y" in mc and "z" in mc):
            try:
                p["mass_center"] = [float(mc.get("x")), float(mc.get("y")), float(mc.get("z"))]
            except Exception:
                # Leave as-is if coercion fails; downstream best-effort parsers may still handle it.
                pass

    return p


def get_schema(resource_type: str) -> Optional[TypeSchema]:
    """Get schema for resource type. Returns None for unknown types."""
    return TYPE_REGISTRY.get(resource_type)


def validate_resource(resource_type: str, properties: Dict[str, Any]) -> List[str]:
    """Validate resource properties against schema."""
    schema = get_schema(resource_type)
    if not schema:
        # Unknown types are allowed for extensibility
        # The kernel validates physics, not type names
        return []
    
    if schema.deprecated:
        return [f"Type {resource_type} is deprecated: {schema.deprecated_message}"]
    
    normalized = _normalize_properties(resource_type, properties)
    errors = schema.validate(normalized)

    # Extra structural validation to prevent runtime KeyError(0) and similar.
    # These checks validate the *grammar*, not design intent.
    try:
        if resource_type == "geometry.section":
            definition_type = normalized.get("definition_type", "polygon")
            if definition_type == "nurbs":
                cps = normalized.get("control_points")
                if not isinstance(cps, list) or not cps:
                    errors.append("Field control_points must be a non-empty list for NURBS sections")
            else:
                pts = normalized.get("points")
                if not isinstance(pts, list) or not pts:
                    errors.append("Field points must be a non-empty list of [y, z] pairs")
                else:
                    for i, pt in enumerate(pts):
                        if not isinstance(pt, (list, tuple)):
                            errors.append(
                                f"points[{i}] must be [y, z] (2 numbers). "
                                f"Do not use objects or [x,y,z] triples; X comes from station."
                            )
                            break
                        if len(pt) != 2:
                            errors.append(
                                f"points[{i}] must be [y, z] (exactly 2 numbers). "
                                f"Do not include X in points; X is derived from station."
                            )
                            break
                        y, z = pt[0], pt[1]
                        if not isinstance(y, (int, float)) or not isinstance(z, (int, float)):
                            errors.append(f"points[{i}] entries must be numbers")
                            break
                # edge_types validation (optional)
                et = normalized.get("edge_types")
                if et is not None:
                    if not isinstance(et, list):
                        errors.append("edge_types must be a list if provided")
                    elif pts and len(et) not in (len(pts), len(pts) - 1, 0):
                        errors.append("edge_types length must match points length (or points length - 1)")

        if resource_type == "geometry.surface":
            definition = normalized.get("definition")
            if definition in ("lofted", None):
                # For lofted surfaces, section_ids must be a list of strings
                section_ids = normalized.get("section_ids")
                if section_ids is not None:
                    if not isinstance(section_ids, list) or any(not isinstance(s, str) for s in section_ids):
                        errors.append("section_ids must be a list of strings")

        if resource_type == "geometry.discontinuity":
            try:
                s0 = float(normalized.get("station_start", 0.0))
                s1 = float(normalized.get("station_end", 1.0))
                if s0 > s1:
                    errors.append("station_start must be <= station_end")
            except Exception:
                # schema validation will catch gross type issues
                pass
    except Exception:
        # Never crash validation path; best-effort only.
        pass

    return errors


def get_all_geometry_types() -> List[str]:
    """Get all geometry.* type names."""
    return [k for k in TYPE_REGISTRY.keys() if k.startswith("geometry.")]


