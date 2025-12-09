"""
webgl/schema.py - Canonical data contracts v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Single source of truth for all mesh/scene data structures.
All API responses and frontend parsing MUST use these schemas.
Schema version changes require backwards compatibility or explicit migration.

Addresses: FM2 (Mesh schema drift)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger("webgl.schema")

# =============================================================================
# SCHEMA VERSION — Increment on breaking changes
# =============================================================================
SCHEMA_VERSION = "1.1.0"


# =============================================================================
# ENUMS
# =============================================================================

class CoordinateSystem(Enum):
    """Coordinate system definition."""
    MAGNET_STANDARD = "magnet_standard"  # X=fwd, Y=port, Z=up, origin at AP/CL/BL


class Units(Enum):
    """Unit system."""
    METERS = "meters"
    MILLIMETERS = "millimeters"


class GeometryMode(Enum):
    """
    Geometry source mode — v1.1 addition for FM1.

    AUTHORITATIVE: Geometry from GRM/HullGenerator (accurate for engineering)
    VISUAL_ONLY: Approximation for display only (must be flagged in UI)
    """
    AUTHORITATIVE = "authoritative"
    VISUAL_ONLY = "visual_only"


class LODLevel(Enum):
    """Level of detail settings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


# =============================================================================
# CORE DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class SchemaMetadata:
    """Schema metadata included in every payload."""
    schema_version: str = SCHEMA_VERSION
    coordinate_system: CoordinateSystem = CoordinateSystem.MAGNET_STANDARD
    units: Units = Units.METERS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "coordinate_system": self.coordinate_system.value,
            "units": self.units.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaMetadata":
        return cls(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            coordinate_system=CoordinateSystem(data.get("coordinate_system", "magnet_standard")),
            units=Units(data.get("units", "meters")),
        )


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    min: Tuple[float, float, float]
    max: Tuple[float, float, float]

    @property
    def center(self) -> Tuple[float, float, float]:
        return tuple((a + b) / 2 for a, b in zip(self.min, self.max))

    @property
    def size(self) -> Tuple[float, float, float]:
        return tuple(b - a for a, b in zip(self.min, self.max))

    @property
    def diagonal(self) -> float:
        """Diagonal length of bounding box."""
        import math
        s = self.size
        return math.sqrt(s[0]**2 + s[1]**2 + s[2]**2)

    def to_dict(self) -> Dict[str, Any]:
        return {"min": list(self.min), "max": list(self.max)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoundingBox":
        return cls(
            min=tuple(data["min"]),
            max=tuple(data["max"]),
        )


@dataclass
class MeshData:
    """
    Triangle mesh data — canonical format for WebGL.

    Vertex data is interleaved: [x0,y0,z0, x1,y1,z1, ...]
    Indices are 32-bit unsigned integers (supports >65k vertices)
    Normals are per-vertex, normalized
    UVs are optional, 2 components per vertex

    Binary Format:
    - Header (24 bytes):
      - magic: 4 bytes "MNET"
      - version: 4 bytes uint32 (1)
      - vertex_count: 4 bytes uint32
      - face_count: 4 bytes uint32
      - flags: 4 bytes uint32 (bit 0=has_uvs, bit 1=has_colors, bit 2=has_tangents)
      - reserved: 4 bytes
    - Vertices: vertex_count * 3 * 4 bytes (float32)
    - Indices: face_count * 3 * 4 bytes (uint32)
    - Normals: vertex_count * 3 * 4 bytes (float32)
    - UVs (if flag): vertex_count * 2 * 4 bytes (float32)
    - Colors (if flag): vertex_count * 4 * 4 bytes (float32)
    - Tangents (if flag): vertex_count * 4 * 4 bytes (float32)
    """

    # Required fields - stored as lists for JSON compatibility
    vertices: List[float] = field(default_factory=list)  # [x,y,z, x,y,z, ...]
    indices: List[int] = field(default_factory=list)     # Triangle indices
    normals: List[float] = field(default_factory=list)   # Per-vertex normals

    # Optional fields
    uvs: Optional[List[float]] = None      # [u,v, u,v, ...]
    colors: Optional[List[float]] = None   # [r,g,b,a, r,g,b,a, ...]
    tangents: Optional[List[float]] = None # [x,y,z,w, x,y,z,w, ...]

    # Metadata
    mesh_id: str = ""
    bounds: Optional[BoundingBox] = None

    # Binary format constants
    MAGIC = b'MNET'
    BINARY_VERSION = 1
    FLAG_HAS_UVS = 1
    FLAG_HAS_COLORS = 2
    FLAG_HAS_TANGENTS = 4

    def __post_init__(self):
        """Validate mesh data on creation."""
        # Compute bounds if not provided and we have vertices
        if self.bounds is None and len(self.vertices) >= 3:
            self._compute_bounds()

    def _compute_bounds(self) -> None:
        """Compute bounding box from vertices."""
        if len(self.vertices) < 3:
            return

        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')

        for i in range(0, len(self.vertices), 3):
            x, y, z = self.vertices[i], self.vertices[i+1], self.vertices[i+2]
            min_x, max_x = min(min_x, x), max(max_x, x)
            min_y, max_y = min(min_y, y), max(max_y, y)
            min_z, max_z = min(min_z, z), max(max_z, z)

        self.bounds = BoundingBox(
            min=(min_x, min_y, min_z),
            max=(max_x, max_y, max_z),
        )

    @property
    def vertex_count(self) -> int:
        return len(self.vertices) // 3

    @property
    def face_count(self) -> int:
        return len(self.indices) // 3

    @property
    def is_empty(self) -> bool:
        return self.vertex_count == 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        result = {
            "mesh_id": self.mesh_id,
            "vertices": self.vertices,
            "indices": self.indices,
            "normals": self.normals,
            "metadata": {
                "vertex_count": self.vertex_count,
                "face_count": self.face_count,
                "bounds": self.bounds.to_dict() if self.bounds else None,
                "has_uvs": self.uvs is not None,
                "has_colors": self.colors is not None,
                "has_tangents": self.tangents is not None,
            },
        }

        if self.uvs is not None:
            result["uvs"] = self.uvs
        if self.colors is not None:
            result["colors"] = self.colors
        if self.tangents is not None:
            result["tangents"] = self.tangents

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeshData":
        """Deserialize from dict."""
        bounds = None
        if data.get("metadata", {}).get("bounds"):
            bounds = BoundingBox.from_dict(data["metadata"]["bounds"])

        return cls(
            vertices=data.get("vertices", []),
            indices=data.get("indices", []),
            normals=data.get("normals", []),
            uvs=data.get("uvs"),
            colors=data.get("colors"),
            tangents=data.get("tangents"),
            mesh_id=data.get("mesh_id", ""),
            bounds=bounds,
        )

    def to_binary(self) -> bytes:
        """Serialize to binary format for efficient transfer."""
        import struct

        try:
            import numpy as np
            HAS_NUMPY = True
        except ImportError:
            HAS_NUMPY = False

        flags = 0
        if self.uvs is not None:
            flags |= self.FLAG_HAS_UVS
        if self.colors is not None:
            flags |= self.FLAG_HAS_COLORS
        if self.tangents is not None:
            flags |= self.FLAG_HAS_TANGENTS

        header = struct.pack(
            '<4sIIIII',
            self.MAGIC,
            self.BINARY_VERSION,
            self.vertex_count,
            self.face_count,
            flags,
            0,  # Reserved
        )

        data = bytearray(header)

        if HAS_NUMPY:
            data.extend(np.array(self.vertices, dtype=np.float32).tobytes())
            data.extend(np.array(self.indices, dtype=np.uint32).tobytes())
            data.extend(np.array(self.normals, dtype=np.float32).tobytes())

            if self.uvs is not None:
                data.extend(np.array(self.uvs, dtype=np.float32).tobytes())
            if self.colors is not None:
                data.extend(np.array(self.colors, dtype=np.float32).tobytes())
            if self.tangents is not None:
                data.extend(np.array(self.tangents, dtype=np.float32).tobytes())
        else:
            # Fallback without numpy
            for v in self.vertices:
                data.extend(struct.pack('<f', v))
            for i in self.indices:
                data.extend(struct.pack('<I', i))
            for n in self.normals:
                data.extend(struct.pack('<f', n))

            if self.uvs is not None:
                for u in self.uvs:
                    data.extend(struct.pack('<f', u))
            if self.colors is not None:
                for c in self.colors:
                    data.extend(struct.pack('<f', c))
            if self.tangents is not None:
                for t in self.tangents:
                    data.extend(struct.pack('<f', t))

        return bytes(data)

    @classmethod
    def from_binary(cls, data: bytes) -> "MeshData":
        """Deserialize from binary format."""
        import struct

        try:
            import numpy as np
            HAS_NUMPY = True
        except ImportError:
            HAS_NUMPY = False

        if len(data) < 24:
            raise ValueError(f"Invalid binary data: too short ({len(data)} bytes)")

        magic, version, vertex_count, face_count, flags, _ = struct.unpack(
            '<4sIIIII', data[:24]
        )

        if magic != cls.MAGIC:
            raise ValueError(f"Invalid magic: {magic}, expected {cls.MAGIC}")
        if version != cls.BINARY_VERSION:
            raise ValueError(f"Unsupported version: {version}, expected {cls.BINARY_VERSION}")

        offset = 24

        if HAS_NUMPY:
            # Read vertices
            vertices_size = vertex_count * 3 * 4
            vertices = np.frombuffer(data[offset:offset + vertices_size], dtype=np.float32).tolist()
            offset += vertices_size

            # Read indices
            indices_size = face_count * 3 * 4
            indices = np.frombuffer(data[offset:offset + indices_size], dtype=np.uint32).tolist()
            offset += indices_size

            # Read normals
            normals_size = vertex_count * 3 * 4
            normals = np.frombuffer(data[offset:offset + normals_size], dtype=np.float32).tolist()
            offset += normals_size

            # Read optional data
            uvs = None
            if flags & cls.FLAG_HAS_UVS:
                uvs_size = vertex_count * 2 * 4
                uvs = np.frombuffer(data[offset:offset + uvs_size], dtype=np.float32).tolist()
                offset += uvs_size

            colors = None
            if flags & cls.FLAG_HAS_COLORS:
                colors_size = vertex_count * 4 * 4
                colors = np.frombuffer(data[offset:offset + colors_size], dtype=np.float32).tolist()
                offset += colors_size

            tangents = None
            if flags & cls.FLAG_HAS_TANGENTS:
                tangents_size = vertex_count * 4 * 4
                tangents = np.frombuffer(data[offset:offset + tangents_size], dtype=np.float32).tolist()
                offset += tangents_size
        else:
            # Fallback without numpy
            vertices = []
            for _ in range(vertex_count * 3):
                v, = struct.unpack('<f', data[offset:offset+4])
                vertices.append(v)
                offset += 4

            indices = []
            for _ in range(face_count * 3):
                i, = struct.unpack('<I', data[offset:offset+4])
                indices.append(i)
                offset += 4

            normals = []
            for _ in range(vertex_count * 3):
                n, = struct.unpack('<f', data[offset:offset+4])
                normals.append(n)
                offset += 4

            uvs = None
            if flags & cls.FLAG_HAS_UVS:
                uvs = []
                for _ in range(vertex_count * 2):
                    u, = struct.unpack('<f', data[offset:offset+4])
                    uvs.append(u)
                    offset += 4

            colors = None
            if flags & cls.FLAG_HAS_COLORS:
                colors = []
                for _ in range(vertex_count * 4):
                    c, = struct.unpack('<f', data[offset:offset+4])
                    colors.append(c)
                    offset += 4

            tangents = None
            if flags & cls.FLAG_HAS_TANGENTS:
                tangents = []
                for _ in range(vertex_count * 4):
                    t, = struct.unpack('<f', data[offset:offset+4])
                    tangents.append(t)
                    offset += 4

        return cls(
            vertices=vertices,
            indices=indices,
            normals=normals,
            uvs=uvs,
            colors=colors,
            tangents=tangents,
        )


@dataclass
class LineData:
    """Line/curve data for waterlines, sections, etc."""
    points: List[Tuple[float, float, float]] = field(default_factory=list)
    closed: bool = False
    line_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "line_id": self.line_id,
            "points": [list(p) for p in self.points],
            "closed": self.closed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LineData":
        return cls(
            points=[tuple(p) for p in data.get("points", [])],
            closed=data.get("closed", False),
            line_id=data.get("line_id", ""),
        )


@dataclass
class StructureSceneData:
    """Structural visualization data."""
    frames: List[MeshData] = field(default_factory=list)
    stringers: List[MeshData] = field(default_factory=list)
    keel: Optional[MeshData] = None
    girders: List[MeshData] = field(default_factory=list)
    plating: List[MeshData] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frames": [f.to_dict() for f in self.frames],
            "stringers": [s.to_dict() for s in self.stringers],
            "keel": self.keel.to_dict() if self.keel else None,
            "girders": [g.to_dict() for g in self.girders],
            "plating": [p.to_dict() for p in self.plating],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StructureSceneData":
        return cls(
            frames=[MeshData.from_dict(f) for f in data.get("frames", [])],
            stringers=[MeshData.from_dict(s) for s in data.get("stringers", [])],
            keel=MeshData.from_dict(data["keel"]) if data.get("keel") else None,
            girders=[MeshData.from_dict(g) for g in data.get("girders", [])],
            plating=[MeshData.from_dict(p) for p in data.get("plating", [])],
        )


@dataclass
class HydrostaticSceneData:
    """Hydrostatic visualization data."""
    waterlines: List[LineData] = field(default_factory=list)
    sectional_areas: List[LineData] = field(default_factory=list)
    bonjean_curves: List[LineData] = field(default_factory=list)
    displacement_volume: Optional[MeshData] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "waterlines": [w.to_dict() for w in self.waterlines],
            "sectional_areas": [s.to_dict() for s in self.sectional_areas],
            "bonjean_curves": [b.to_dict() for b in self.bonjean_curves],
            "displacement_volume": self.displacement_volume.to_dict() if self.displacement_volume else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HydrostaticSceneData":
        return cls(
            waterlines=[LineData.from_dict(w) for w in data.get("waterlines", [])],
            sectional_areas=[LineData.from_dict(s) for s in data.get("sectional_areas", [])],
            bonjean_curves=[LineData.from_dict(b) for b in data.get("bonjean_curves", [])],
            displacement_volume=MeshData.from_dict(data["displacement_volume"]) if data.get("displacement_volume") else None,
        )


@dataclass
class MaterialDef:
    """Material definition for Three.js MeshStandardMaterial."""
    name: str
    type: str = "MeshStandardMaterial"
    color: str = "#B8B8B8"
    metalness: float = 0.9
    roughness: float = 0.4
    opacity: float = 1.0
    transparent: bool = False
    side: str = "front"  # front, back, double
    emissive: str = "#000000"
    emissiveIntensity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "color": self.color,
            "metalness": self.metalness,
            "roughness": self.roughness,
            "opacity": self.opacity,
            "transparent": self.transparent,
            "side": self.side,
            "emissive": self.emissive,
            "emissiveIntensity": self.emissiveIntensity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaterialDef":
        return cls(
            name=data["name"],
            type=data.get("type", "MeshStandardMaterial"),
            color=data.get("color", "#B8B8B8"),
            metalness=data.get("metalness", 0.9),
            roughness=data.get("roughness", 0.4),
            opacity=data.get("opacity", 1.0),
            transparent=data.get("transparent", False),
            side=data.get("side", "front"),
            emissive=data.get("emissive", "#000000"),
            emissiveIntensity=data.get("emissiveIntensity", 0.0),
        )


@dataclass
class SceneData:
    """
    Complete scene data — canonical response format for /3d/scene endpoint.

    All WebGL API responses use this schema.
    """

    # Schema metadata (always included)
    schema: SchemaMetadata = field(default_factory=SchemaMetadata)

    # Design identification
    design_id: str = ""
    version_id: str = ""  # v1.1: For traceability (FM8)

    # v1.1: Geometry authority (FM1)
    geometry_mode: GeometryMode = GeometryMode.AUTHORITATIVE

    # Mesh data
    hull: Optional[MeshData] = None
    deck: Optional[MeshData] = None
    transom: Optional[MeshData] = None
    structure: Optional[StructureSceneData] = None
    hydrostatics: Optional[HydrostaticSceneData] = None

    # Materials
    materials: List[MaterialDef] = field(default_factory=list)

    # Design metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "schema": self.schema.to_dict(),
            "design_id": self.design_id,
            "version_id": self.version_id,
            "geometry_mode": self.geometry_mode.value,
            "hull": self.hull.to_dict() if self.hull else None,
            "deck": self.deck.to_dict() if self.deck else None,
            "transom": self.transom.to_dict() if self.transom else None,
            "structure": self.structure.to_dict() if self.structure else None,
            "hydrostatics": self.hydrostatics.to_dict() if self.hydrostatics else None,
            "materials": [m.to_dict() for m in self.materials],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneData":
        """Deserialize from dict."""
        return cls(
            schema=SchemaMetadata.from_dict(data.get("schema", {})),
            design_id=data.get("design_id", ""),
            version_id=data.get("version_id", ""),
            geometry_mode=GeometryMode(data.get("geometry_mode", "authoritative")),
            hull=MeshData.from_dict(data["hull"]) if data.get("hull") else None,
            deck=MeshData.from_dict(data["deck"]) if data.get("deck") else None,
            transom=MeshData.from_dict(data["transom"]) if data.get("transom") else None,
            structure=StructureSceneData.from_dict(data["structure"]) if data.get("structure") else None,
            hydrostatics=HydrostaticSceneData.from_dict(data["hydrostatics"]) if data.get("hydrostatics") else None,
            materials=[MaterialDef.from_dict(m) for m in data.get("materials", [])],
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# TYPESCRIPT TYPE GENERATION
# =============================================================================

def generate_typescript_types() -> str:
    """
    Generate TypeScript interfaces from Python schema.

    Run this after schema changes:
        python -c "from magnet.webgl.schema import generate_typescript_types; print(generate_typescript_types())" > frontend/types/schema.ts
    """
    timestamp = datetime.utcnow().isoformat()

    return f'''// AUTO-GENERATED from webgl/schema.py — DO NOT EDIT
// Schema version: {SCHEMA_VERSION}
// Generated at: {timestamp}Z

export const SCHEMA_VERSION = "{SCHEMA_VERSION}";

// =============================================================================
// ENUMS
// =============================================================================

export type CoordinateSystem = "magnet_standard";
export type Units = "meters" | "millimeters";
export type GeometryMode = "authoritative" | "visual_only";
export type LODLevel = "low" | "medium" | "high" | "ultra";
export type MaterialSide = "front" | "back" | "double";

// =============================================================================
// CORE INTERFACES
// =============================================================================

export interface SchemaMetadata {{
  schema_version: string;
  coordinate_system: CoordinateSystem;
  units: Units;
}}

export interface BoundingBox {{
  min: [number, number, number];
  max: [number, number, number];
}}

export interface MeshMetadata {{
  vertex_count: number;
  face_count: number;
  bounds: BoundingBox | null;
  has_uvs: boolean;
  has_colors: boolean;
  has_tangents: boolean;
}}

export interface MeshData {{
  mesh_id: string;
  vertices: number[];      // Interleaved [x,y,z, x,y,z, ...]
  indices: number[];       // Triangle indices
  normals: number[];       // Per-vertex normals
  uvs?: number[];          // Optional UV coordinates
  colors?: number[];       // Optional RGBA colors
  tangents?: number[];     // Optional tangent vectors
  metadata: MeshMetadata;
}}

export interface LineData {{
  line_id: string;
  points: [number, number, number][];
  closed: boolean;
}}

// =============================================================================
// COMPOSITE STRUCTURES
// =============================================================================

export interface StructureSceneData {{
  frames: MeshData[];
  stringers: MeshData[];
  keel: MeshData | null;
  girders: MeshData[];
  plating: MeshData[];
}}

export interface HydrostaticSceneData {{
  waterlines: LineData[];
  sectional_areas: LineData[];
  bonjean_curves: LineData[];
  displacement_volume: MeshData | null;
}}

export interface MaterialDef {{
  name: string;
  type: string;
  color: string;
  metalness: number;
  roughness: number;
  opacity: number;
  transparent: boolean;
  side: MaterialSide;
  emissive: string;
  emissiveIntensity: number;
}}

// =============================================================================
// SCENE DATA — Main API Response Type
// =============================================================================

export interface SceneData {{
  schema: SchemaMetadata;
  design_id: string;
  version_id: string;
  geometry_mode: GeometryMode;
  hull: MeshData | null;
  deck: MeshData | null;
  transom: MeshData | null;
  structure: StructureSceneData | null;
  hydrostatics: HydrostaticSceneData | null;
  materials: MaterialDef[];
  metadata: Record<string, unknown>;
}}

// =============================================================================
// ERROR TYPES
// =============================================================================

export interface GeometryError {{
  code: string;
  category: string;
  severity: string;
  message: string;
  details: Record<string, unknown>;
  recovery_hint: string | null;
}}

export interface GeometryErrorResponse {{
  error: GeometryError;
}}

// =============================================================================
// WEBSOCKET MESSAGES
// =============================================================================

export interface GeometryUpdateMessage {{
  message_type: "geometry_update";
  update_id: string;
  prev_update_id: string;
  design_id: string;
  hull: MeshData | null;
  deck: MeshData | null;
  structure: StructureSceneData | null;
  is_full_update: boolean;
  timestamp: string;
}}

export interface GeometryFailedMessage {{
  message_type: "geometry_failed";
  error_code: string;
  error_message: string;
  recovery_hint: string | null;
}}

export type WebSocketMessage = GeometryUpdateMessage | GeometryFailedMessage;

// =============================================================================
// ANNOTATION TYPES
// =============================================================================

export interface Measurement3D {{
  type: "distance" | "angle" | "area";
  points: [number, number, number][];
  value: number;
  unit: string;
}}

export interface Annotation3D {{
  annotation_id: string;
  design_id: string;
  position: [number, number, number];
  normal: [number, number, number] | null;
  label: string;
  description: string;
  category: "general" | "measurement" | "issue" | "note";
  measurement: Measurement3D | null;
  created_by: string;
  created_at: string;
  linked_decision_id: string | null;
  linked_phase: string | null;
}}

// =============================================================================
// API REQUEST TYPES
// =============================================================================

export interface SectionCutRequest {{
  plane: "transverse" | "longitudinal" | "waterplane";
  position: number;  // 0.0 - 1.0
}}

export interface SectionCutResponse {{
  plane: string;
  position: number;
  curves: LineData[];
  metadata: Record<string, unknown>;
}}

// =============================================================================
// TYPE GUARDS
// =============================================================================

export function isGeometryErrorResponse(obj: unknown): obj is GeometryErrorResponse {{
  return typeof obj === "object" && obj !== null && "error" in obj;
}}

export function isGeometryUpdateMessage(msg: WebSocketMessage): msg is GeometryUpdateMessage {{
  return msg.message_type === "geometry_update";
}}

export function isGeometryFailedMessage(msg: WebSocketMessage): msg is GeometryFailedMessage {{
  return msg.message_type === "geometry_failed";
}}
'''


# =============================================================================
# VALIDATION UTILITIES
# =============================================================================

def validate_mesh_data(mesh: MeshData) -> List[str]:
    """Validate MeshData and return list of issues (empty if valid)."""
    issues = []

    if mesh.vertex_count == 0:
        issues.append("Mesh has no vertices")

    if mesh.face_count == 0:
        issues.append("Mesh has no faces")

    # Check vertex data length
    if len(mesh.vertices) % 3 != 0:
        issues.append(f"Vertices length {len(mesh.vertices)} is not a multiple of 3")

    # Check index data length
    if len(mesh.indices) % 3 != 0:
        issues.append(f"Indices length {len(mesh.indices)} is not a multiple of 3")

    # Check normals length matches vertices
    if len(mesh.normals) != len(mesh.vertices):
        issues.append(f"Normals length {len(mesh.normals)} does not match vertices {len(mesh.vertices)}")

    # Check index bounds
    if mesh.indices:
        max_index = max(mesh.indices)
        if max_index >= mesh.vertex_count:
            issues.append(f"Index {max_index} out of bounds (vertex_count={mesh.vertex_count})")

    # Check for degenerate triangles
    for i in range(0, len(mesh.indices), 3):
        if i + 2 < len(mesh.indices):
            a, b, c = mesh.indices[i], mesh.indices[i+1], mesh.indices[i+2]
            if a == b or b == c or a == c:
                issues.append(f"Degenerate triangle at face {i//3}: ({a}, {b}, {c})")
                if len(issues) > 10:
                    issues.append("... (more issues truncated)")
                    break

    # Check UV length if present
    if mesh.uvs is not None and len(mesh.uvs) != mesh.vertex_count * 2:
        issues.append(f"UVs length {len(mesh.uvs)} should be {mesh.vertex_count * 2}")

    # Check colors length if present
    if mesh.colors is not None and len(mesh.colors) != mesh.vertex_count * 4:
        issues.append(f"Colors length {len(mesh.colors)} should be {mesh.vertex_count * 4}")

    return issues


def validate_scene_data(scene: SceneData) -> List[str]:
    """Validate SceneData and return list of issues."""
    issues = []

    if scene.schema.schema_version != SCHEMA_VERSION:
        issues.append(f"Schema version mismatch: {scene.schema.schema_version} != {SCHEMA_VERSION}")

    if not scene.design_id:
        issues.append("Missing design_id")

    if scene.hull:
        hull_issues = validate_mesh_data(scene.hull)
        issues.extend([f"hull: {i}" for i in hull_issues])

    if scene.deck:
        deck_issues = validate_mesh_data(scene.deck)
        issues.extend([f"deck: {i}" for i in deck_issues])

    if scene.transom:
        transom_issues = validate_mesh_data(scene.transom)
        issues.extend([f"transom: {i}" for i in transom_issues])

    return issues
