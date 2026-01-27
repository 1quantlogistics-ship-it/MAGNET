# MAGNET Geometry Generator Expansion Architecture

<!-- AGENT_CONTEXT
Purpose: [TODO: Add purpose description]
Authoritative: No
Keywords: [geometry, expansion, design]
Depends_On: None
Used_By: [TODO: Add users]
Status: current
Last_Verified: 2026-01-15
-->


## Overview

This document outlines the architecture for expanding MAGNET's hull geometry generator from smooth parametric forms to support complex hull primitives including hard chines, faceted panels, spray rails, angular bows, and other features found on modern high-performance craft.

**Target:** Enable parametric generation of vessels like Metal Shark patrol boats with multiple hard chines, faceted panels, and angular bow forms—all kernel-controlled.

---

## Part 1: Current Generator Audit

### 1.1 Generator Structure

**Location:** `magnet/hull_gen/generator.py`

The `HullGenerator` class generates hull geometry through:
1. Section generation (21 transverse sections by default)
2. Waterline generation
3. Key curve generation (keel, stem, chine, transom)
4. Property computation (volume, wetted surface)

**Key Methods:**
- `_generate_section_at_station()` - dispatches to section type methods
- `_generate_chine_section()` - hard chine sections with deadrise
- `_generate_round_section()` - elliptical bilge sections
- `_generate_generic_section()` - fallback (currently = chine)

### 1.2 Section Generation Method

**Type:** Point-by-point parametric (NOT spline-based)

Sections are generated using parametric formulas:

```python
# From _generate_chine_section():
fullness = max(0.0, min(1.0, 0.7 * cb_norm + 0.3 * cm_norm))
bottom_exp = 1.4 + 6.0 * fullness  # 1.4 (fine V) to 7.4 (flat)
deadrise_scale = 1.0 - 0.7 * fullness

# Z profile from keel to chine
z_v = -draft + y * math.tan(deadrise_rad) * deadrise_scale
z_flat = -draft + (t ** bottom_exp) * (chine_z + draft)
z = (1.0 - fullness) * z_v + fullness * z_flat
```

**Points per section:** 25 (configurable)
**Points represent:** Half-section from keel (y=0) to deck edge (y=half_beam)

### 1.3 Section Point Data Structure

```python
@dataclass
class SectionPoint:
    position: Point3D
    normal: Optional[Point3D] = None
    curvature: float = 0.0
    is_chine: bool = False    # ← Currently used but not for edge handling
    is_keel: bool = False
```

**Missing:** Edge type flag for hard/soft edge rendering

### 1.4 Mesh Assembly

**Location:** `magnet/webgl/geometry_pipeline.py`

Hull is tessellated by `HullGeometryPipeline._tessellate_from_sections()`:
1. Creates separate port/starboard vertex grids
2. Triangulates between adjacent sections
3. Adds end caps at bow/stern

**Normal computation:** Smooth vertex normals via angle-weighted averaging
- **No support for split normals** at hard edges
- All edges render smooth regardless of `is_chine` flag

### 1.5 Existing Enums (Declared but Not Fully Wired)

```python
# hull_gen/enums.py - EXISTS but not all used in geometry generation
class ChineType(Enum):      # NONE, SINGLE, DOUBLE, TRIPLE, SOFT, HARD
class StemProfile(Enum):    # VERTICAL, RAKED, WAVE_PIERCING, BULBOUS, AXEBOW
class SternProfile(Enum):   # TRANSOM, CRUISER, CANOE, TUNNEL
class TransomType(Enum):    # DRY, IMMERSED, SEMI_IMMERSED
class KeelType(Enum):       # FLAT, BAR, SKEG, TWIN_SKEG
class SectionShape(Enum):   # V_SHAPE, U_SHAPE, ROUND, FLAT_BOTTOM, WARPED
```

**Gap:** `HullFeatures.chine_type` exists but generator doesn't branch on it

---

## Part 2: Gap Analysis

### 2.1 What's Missing

| Feature | Current State | Impact |
|---------|--------------|--------|
| Hard edge normals | All edges smooth | Can't render crisp chines |
| Multiple chines | Single chine only | Can't model spray rails/double chines |
| Faceted panels | Smooth interpolation | Can't model modern angular craft |
| Tumblehome | Always vertical/flared | Can't model Navy craft topsides |
| Angular bow forms | Smooth lofted only | Can't model wedge/axe bows |
| Transom variations | Simple vertical/raked | Can't model steps/tunnels |
| Spray rails | Not supported | Can't model performance features |

### 2.2 Questions Answered

1. **What's the current section generation method?**
   - Point-by-point parametric using Cb/Cm-derived fullness
   - NOT Bezier or NURBS (though `nurbs.py` exists for curves)

2. **How is the mesh assembled from sections?**
   - Triangle strips between adjacent sections
   - Separate port/starboard grids, then triangulated

3. **Are normals computed per-face or per-vertex?**
   - Per-vertex with angle-weighted averaging (always smooth)

4. **What's the path from generator to Three.js?**
   - `HullGenerator` → `HullGeometry` → `HullGeometryPipeline` → `MeshData` → GLB export → Three.js

5. **Can we add arbitrary points to a section?**
   - Yes, `points: List[SectionPoint]` is flexible

6. **Is there existing support for feature lines/creases?**
   - `is_chine: bool` exists but not used for rendering
   - No edge crease/hard edge support in mesh builder

---

## Part 3: Extension Architecture

### 3.1 Core Principle: Modular Section Generator

Replace monolithic section generation with a pipeline of modular modifiers:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Section Generation Pipeline                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. BaseSectionGenerator                                            │
│     └─ Generates base section shape from Cb/Cm/deadrise             │
│     └─ Output: List[SectionPoint] with base geometry                │
│                                                                     │
│  2. ChineModifier                                                   │
│     └─ Adds/modifies chine points based on ChineConfig              │
│     └─ Sets edge_type flags (SMOOTH, HARD, CREASE)                  │
│                                                                     │
│  3. SprayRailModifier                                               │
│     └─ Inserts spray rail geometry at configured positions          │
│     └─ Adds hard edges at rail boundaries                           │
│                                                                     │
│  4. TumblehomeModifier                                              │
│     └─ Applies tumblehome/flare to topsides                         │
│                                                                     │
│  5. KnuckleModifier                                                 │
│     └─ Adds knuckle lines at configured heights                     │
│                                                                     │
│  Output: List[SectionPoint] with edge_type[] annotations            │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Enhanced Section Point Data Structure

```python
class EdgeType(Enum):
    """Edge rendering type for mesh generation."""
    SMOOTH = "smooth"      # Averaged normals (current behavior)
    HARD = "hard"          # Split normals (sharp visual edge)
    CREASE = "crease"      # Hard edge with specified crease angle

@dataclass
class SectionPoint:
    position: Point3D
    normal: Optional[Point3D] = None
    curvature: float = 0.0
    
    # Feature flags (existing)
    is_chine: bool = False
    is_keel: bool = False
    
    # NEW: Edge rendering control
    edge_type: EdgeType = EdgeType.SMOOTH
    crease_angle: float = 0.0  # Only used if edge_type == CREASE
    
    # NEW: Feature identification
    feature_id: Optional[str] = None  # e.g., "spray_rail_1", "chine_main"
```

### 3.3 Bow Generator Module

```python
class BowStyle(Enum):
    TRADITIONAL = "traditional"  # Smooth lofted (current)
    WEDGE = "wedge"              # Two planar panels meeting at stem
    FACETED = "faceted"          # N planar panels with hard edges
    AXEBOW = "axebow"            # Vertical stem, sharp entry
    WAVE_PIERCING = "wave_piercing"  # Fine entry, tumblehome

@dataclass
class BowConfig:
    style: BowStyle = BowStyle.TRADITIONAL
    facet_count: int = 2         # For FACETED mode
    stem_rake_deg: float = 15.0
    entrance_angle_deg: float = 25.0
    is_planar: bool = False      # Force planar panels

class BowGenerator:
    """Generates bow region geometry."""
    
    def generate(
        self,
        bow_config: BowConfig,
        first_sections: List[HullSection],  # First N sections
        stem_profile: List[Point3D],
    ) -> BowMesh:
        """Generate bow mesh patch with connection edges."""
        
        if bow_config.style == BowStyle.WEDGE:
            return self._generate_wedge_bow(...)
        elif bow_config.style == BowStyle.FACETED:
            return self._generate_faceted_bow(...)
        # ... etc
```

### 3.4 Transom Generator Module

```python
class TransomStyle(Enum):
    VERTICAL = "vertical"
    RAKED = "raked"
    STEPPED = "stepped"       # For outboard mounting
    TUNNELED = "tunneled"     # Water jet tunnels
    NOTCHED = "notched"       # Center notch
    SUGAR_SCOOP = "sugar_scoop"

@dataclass
class TransomConfig:
    style: TransomStyle = TransomStyle.VERTICAL
    rake_deg: float = 12.0
    step_height_m: float = 0.0
    tunnel_count: int = 0
    tunnel_diameter_m: float = 0.0
    notch_width_m: float = 0.0

class TransomGenerator:
    """Generates transom geometry with variations."""
    
    def generate(
        self,
        config: TransomConfig,
        aft_section: HullSection,
        transom_beam: float,
        draft: float,
    ) -> TransomMesh:
        """Generate transom mesh with correct topology."""
```

### 3.5 Hard Edge Support in Mesh Builder

```python
# webgl/mesh_builder.py - EXTENDED

class MeshBuilder:
    def __init__(self):
        self._vertices: List[float] = []
        self._indices: List[int] = []
        self._normals: List[float] = []    # Pre-allocated
        self._edge_creases: List[int] = [] # NEW: pairs of vertex indices
        self._vertex_count = 0
    
    def add_vertex_with_normal(
        self, 
        x: float, y: float, z: float,
        nx: float, ny: float, nz: float,
    ) -> int:
        """Add vertex with explicit normal (for hard edges)."""
        self._vertices.extend([x, y, z])
        self._normals.extend([nx, ny, nz])
        idx = self._vertex_count
        self._vertex_count += 1
        return idx
    
    def mark_hard_edge(self, v0: int, v1: int) -> None:
        """Mark edge between v0 and v1 as hard (for rendering)."""
        self._edge_creases.extend([v0, v1])
    
    def build(self, compute_normals: bool = True) -> MeshData:
        """Build mesh, respecting hard edge markers."""
        if compute_normals and not self._normals:
            self._normals = self._compute_split_normals()
        return MeshData(
            vertices=self._vertices,
            indices=self._indices,
            normals=self._normals,
            edge_creases=self._edge_creases,  # NEW
        )
    
    def _compute_split_normals(self) -> List[float]:
        """Compute normals with splits at hard edges."""
        # 1. Compute face normals
        # 2. For each vertex, if on hard edge, duplicate with face normal
        # 3. Otherwise, average adjacent face normals
```

---

## Part 4: Schema Extension

### 4.1 New State Paths

```yaml
# hull.* namespace extensions

# Chine Configuration
hull.chine_type: "hard"              # soft | hard | double | triple | reverse
hull.chine_count: 2                  # Number of chines per side
hull.chine_angles: [45, 30]          # Angle at each chine (deg)
hull.chine_heights: [0.3, 0.6]       # Height as fraction of draft

# Spray Rails (array of configs)
hull.spray_rails: [
  { height_ratio: 0.3, angle_deg: 15, width_m: 0.05, start_station: 0.2 },
  { height_ratio: 0.5, angle_deg: 20, width_m: 0.04, start_station: 0.3 },
]

# Bow Form
hull.bow_style: "wedge"              # traditional | wedge | axe | faceted
hull.bow_facet_count: 3              # For faceted bow
hull.bow_planarity: 0.8              # 0=smooth, 1=fully planar panels

# Panel Style
hull.panel_style: "faceted"          # smooth | developable | faceted
hull.facet_count_per_side: 4         # For faceted hulls

# Transom
hull.transom_style: "stepped"        # vertical | raked | stepped | tunneled
hull.transom_rake_deg: 12
hull.transom_step_height_m: 0.3
hull.tunnel_count: 2
hull.tunnel_diameter_m: 0.4

# Sheer Profile
hull.sheer_style: "angular"          # traditional | flat | angular | stepped
hull.sheer_break_stations: [0.3, 0.7]  # Station positions of sheer breaks

# Topsides
hull.tumblehome_deg: 8               # Inward lean above WL (negative = flare)
hull.tumblehome_start_height: 0.5    # Height ratio where tumblehome starts

# Knuckle Lines
hull.knuckle_lines: [
  { height_ratio: 0.7, angle_deg: 5 }
]
```

### 4.2 Feature Flags

```yaml
hull.features.hard_chines: true
hull.features.spray_rails: true
hull.features.faceted_panels: false
hull.features.tunnels: false
hull.features.tumblehome: false
```

---

## Part 5: Rendering Considerations

### 5.1 Normal Handling for Hard Edges

```
Smooth regions:    Averaged vertex normals (current behavior)
Hard edges:        Split normals (duplicate vertex, face normal each side)
Faceted panels:    Flat shading per panel (face normal for all vertices)
```

**Implementation:**

```python
def _compute_split_normals(vertices, indices, edge_creases):
    """
    Compute normals with splits at hard edges.
    
    For vertices on hard edges:
    1. Duplicate the vertex for each adjacent face group
    2. Assign face normal to each duplicate
    3. Update indices to reference correct duplicate
    """
    # Group faces by crease boundaries
    # For each crease edge, duplicate shared vertices
    # Return expanded vertex/normal arrays
```

### 5.2 Three.js Implementation

```javascript
// For hard edges, split normals are already baked into GLB
// No additional Three.js code needed

// For visible hard edge lines (optional):
const edges = new THREE.EdgesGeometry(geometry, thresholdAngle);
const edgeMaterial = new THREE.LineBasicMaterial({ color: 0x000000 });
const edgeMesh = new THREE.LineSegments(edges, edgeMaterial);
scene.add(edgeMesh);

// For true faceted look:
geometry.computeVertexNormals();  // Already per-face if verts not shared
```

### 5.3 LOD Considerations

```
LOD High:    Full facet detail, all spray rails, all knuckles
LOD Medium:  Simplified chines (merge spray rails into single chine)
LOD Low:     Basic hull envelope, no feature details
```

---

## Part 6: Hydrostatics Compatibility

### 6.1 Section Integration (Unchanged)

Hard/faceted sections still have:
- Definite area (integrate point cloud)
- Centroid (moment calculation)
- Simpson's rule integration works regardless of shape

### 6.2 Wetted Surface Adjustments

```python
def compute_wetted_surface(sections, features):
    base_ws = simpson_integrate_sections(sections)
    
    # Add spray rail contributions
    if features.spray_rails:
        for rail in features.spray_rails:
            base_ws += rail.length * rail.width * 2  # Both sides
    
    # Subtract tunnel areas
    if features.tunnels:
        base_ws -= sum(math.pi * (t.diameter/2)**2 for t in features.tunnels)
    
    return base_ws
```

### 6.3 Stability Considerations

Hard chines improve form stability:
- Higher BM at heel angles
- Reverse chines significantly affect heeled waterplane
- May need heeled hydrostatics for hard-chine craft

---

## Part 7: Implementation Roadmap

### Phase 1: Foundation (1-2 weeks)
- [ ] Add `EdgeType` to `SectionPoint`
- [ ] Implement normal splitting in `MeshBuilder`
- [ ] Wire `ChineType.HARD` to generate hard edge flags
- [ ] Verify hydrostatics still compute correctly
- [ ] Add basic tests for edge type propagation

### Phase 2: Chine Variations (1 week)
- [ ] Double hard chine support
- [ ] Reverse chine (outward-angled)
- [ ] Variable chine (soft→hard along length)
- [ ] Chine flat geometry (horizontal extension)
- [ ] Update priors with chine type parameters

### Phase 3: Bow Forms (1-2 weeks)
- [ ] `BowGenerator` class with style dispatch
- [ ] Wedge bow (2 planar panels)
- [ ] Faceted bow with configurable panel count
- [ ] Axe bow (vertical stem, sharp entry)
- [ ] Stem profile options integration

### Phase 4: Longitudinal Features (1 week)
- [ ] `SprayRailModifier` for section pipeline
- [ ] Knuckle line support
- [ ] Angular sheer profile options
- [ ] Feature line visualization in Three.js

### Phase 5: Transom Variations (1 week)
- [ ] `TransomGenerator` class
- [ ] Rake angle control
- [ ] Stepped transom for outboards
- [ ] Tunnel cutouts for jets
- [ ] Notched transom option

### Phase 6: Advanced (2+ weeks)
- [ ] Full faceted/developable panel mode
- [ ] Tumblehome control above waterline
- [ ] Bulwark/gunwale generation
- [ ] Deck surface generation
- [ ] Superstructure hooks

---

## Part 8: File Changes Summary

### New Files

```
magnet/hull_gen/
├── section_pipeline.py      # Modular section generation pipeline
├── modifiers/
│   ├── __init__.py
│   ├── base.py              # SectionModifier base class
│   ├── chine.py             # ChineModifier
│   ├── spray_rail.py        # SprayRailModifier
│   ├── tumblehome.py        # TumblehomeModifier
│   └── knuckle.py           # KnuckleModifier
├── bow_generator.py         # BowGenerator class
└── transom_generator.py     # TransomGenerator class
```

### Modified Files

```
magnet/hull_gen/
├── geometry.py              # Add EdgeType, update SectionPoint
├── generator.py             # Wire pipeline, dispatch to modifiers
├── parameters.py            # Add BowConfig, TransomConfig, etc.
├── enums.py                 # Add new enums (BowStyle, TransomStyle)

magnet/webgl/
├── mesh_builder.py          # Add split normal support, edge creases
├── geometry_pipeline.py     # Pass edge types to tessellation
├── schema.py                # Add edge_creases to MeshData

magnet/core/
├── dataclasses.py           # Add new hull state fields
├── state_manager.py         # Register new valid paths
```

---

## Appendix A: Target Hull Form Reference

### Metal Shark Defiant 45

```
Features to model:
- Triple hard chines
- 22° deadrise at transom
- Wedge/angular bow form
- Stepped transom for outboards
- Minimal tumblehome (straight topsides)
- Spray rails at waterline
```

### Swedish Combat Boat CB90

```
Features to model:
- Double reverse chines (sponson-like)
- Axe bow (vertical stem)
- Faceted topside panels
- Stepped planing hull
- Tunnel stern for jets
```

### Reference Data Sources

1. Metal Shark published LOA/beam/draft specs
2. Savitsky planing hull theory for chine geometry
3. DNV GL HSLC rules for hull form requirements
4. USN DDG-1000 tumblehome data (public domain)

---

## Appendix B: Validation Checklist

Before each phase merge:

- [ ] All existing tests pass
- [ ] New feature has unit tests
- [ ] Hydrostatics compute within 5% of baseline
- [ ] GLB export produces valid mesh
- [ ] Three.js renders correctly
- [ ] No NaN/Inf in vertex data
- [ ] Edge creases render as intended (if applicable)
- [ ] Priors updated for new parameters
- [ ] State paths registered in state_manager

