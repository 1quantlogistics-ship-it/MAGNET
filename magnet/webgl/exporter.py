"""
webgl/exporter.py - Geometry export with traceability v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides export to glTF/GLB, STL, OBJ formats with version traceability.

Addresses: FM8 (Export not versioned)
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any, List, Tuple, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import struct
import io
import json
import base64
import logging
import math

from .schema import MeshData, SceneData, MaterialDef, BoundingBox, GeometryMode
from .errors import ExportError
from .contracts import MeshCategory, AttributePolicy
from .gltf_builder import GLTFBuilder

if TYPE_CHECKING:
    pass

logger = logging.getLogger("webgl.exporter")


# =============================================================================
# EXPORT METADATA (FM8)
# =============================================================================

@dataclass
class ExportMetadata:
    """
    Export traceability metadata (FM8 resolution).

    All exports include version tracking for reproducibility.
    """
    export_id: str
    design_id: str
    exported_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Version tracking
    schema_version: str = "1.1.0"
    geometry_version: int = 1
    source_branch: str = "main"
    commit_hash: Optional[str] = None

    # Export details
    format: str = ""
    lod: str = "medium"
    geometry_mode: str = "authoritative"

    # Statistics
    vertex_count: int = 0
    face_count: int = 0
    file_size_bytes: int = 0

    # Coordinate system
    units: str = "meters"
    up_axis: str = "Z"
    forward_axis: str = "X"

    # Custom metadata
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "export_id": self.export_id,
            "design_id": self.design_id,
            "exported_at": self.exported_at,
            "schema_version": self.schema_version,
            "geometry_version": self.geometry_version,
            "source_branch": self.source_branch,
            "commit_hash": self.commit_hash,
            "format": self.format,
            "lod": self.lod,
            "geometry_mode": self.geometry_mode,
            "vertex_count": self.vertex_count,
            "face_count": self.face_count,
            "file_size_bytes": self.file_size_bytes,
            "units": self.units,
            "up_axis": self.up_axis,
            "forward_axis": self.forward_axis,
            "custom": self.custom,
        }


# =============================================================================
# EXPORT FORMATS
# =============================================================================

class ExportFormat(Enum):
    """Supported export formats."""
    GLTF = "gltf"      # JSON format with external buffers
    GLB = "glb"        # Binary glTF (single file)
    STL = "stl"        # Stereolithography (binary)
    STL_ASCII = "stl_ascii"  # STL ASCII format
    OBJ = "obj"        # Wavefront OBJ


@dataclass
class ExportResult:
    """Result of an export operation."""
    success: bool
    format: ExportFormat
    data: bytes
    metadata: ExportMetadata
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def file_extension(self) -> str:
        extensions = {
            ExportFormat.GLTF: ".gltf",
            ExportFormat.GLB: ".glb",
            ExportFormat.STL: ".stl",
            ExportFormat.STL_ASCII: ".stl",
            ExportFormat.OBJ: ".obj",
        }
        return extensions.get(self.format, ".bin")


# =============================================================================
# GEOMETRY EXPORTER
# =============================================================================

class GeometryExporter:
    """
    Exports geometry to various formats with traceability.

    All exports include metadata for version tracking (FM8).
    """

    def __init__(self, design_id: str = "", source_branch: str = "main"):
        self._design_id = design_id
        self._source_branch = source_branch
        self._commit_hash: Optional[str] = None

    def set_version_info(self, branch: str, commit_hash: Optional[str] = None) -> None:
        """Set version control information for exports."""
        self._source_branch = branch
        self._commit_hash = commit_hash

    def export(
        self,
        mesh: MeshData,
        format: ExportFormat,
        design_id: Optional[str] = None,
        lod: str = "medium",
        geometry_mode: GeometryMode = GeometryMode.AUTHORITATIVE,
    ) -> ExportResult:
        """
        Export a mesh to the specified format.

        Args:
            mesh: The mesh data to export
            format: Target export format
            design_id: Design identifier (uses instance default if not provided)
            lod: Level of detail used
            geometry_mode: Source geometry mode

        Returns:
            ExportResult with data and metadata
        """
        import uuid

        design_id = design_id or self._design_id

        # Create metadata
        metadata = ExportMetadata(
            export_id=str(uuid.uuid4()),
            design_id=design_id,
            format=format.value,
            lod=lod,
            geometry_mode=geometry_mode.value,
            vertex_count=mesh.vertex_count,
            face_count=mesh.face_count,
            source_branch=self._source_branch,
            commit_hash=self._commit_hash,
        )

        try:
            if format == ExportFormat.GLTF:
                data = self._export_gltf(mesh, metadata, binary=False)
            elif format == ExportFormat.GLB:
                data = self._export_gltf(mesh, metadata, binary=True)
            elif format == ExportFormat.STL:
                data = self._export_stl(mesh, binary=True)
            elif format == ExportFormat.STL_ASCII:
                data = self._export_stl(mesh, binary=False)
            elif format == ExportFormat.OBJ:
                data = self._export_obj(mesh)
            else:
                raise ExportError(format=format.value if hasattr(format, "value") else str(format), reason="unsupported_format")

            metadata.file_size_bytes = len(data)

            return ExportResult(
                success=True,
                format=format,
                data=data,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                success=False,
                format=format,
                data=b"",
                metadata=metadata,
                errors=[str(e)],
            )

    def export_scene(
        self,
        scene: SceneData,
        format: ExportFormat,
        include_structure: bool = True,
    ) -> ExportResult:
        """
        Export a complete scene to the specified format.

        For formats that don't support scenes (STL, OBJ), combines all meshes.
        """
        import uuid

        # Collect all meshes
        meshes: List[Tuple[str, MeshData]] = []

        if scene.hull:
            meshes.append(("hull", scene.hull))
        if scene.deck:
            meshes.append(("deck", scene.deck))

        if include_structure and scene.structure:
            for i, frame in enumerate(scene.structure.frames or []):
                meshes.append((f"frame_{i}", frame))
            for i, stringer in enumerate(scene.structure.stringers or []):
                meshes.append((f"stringer_{i}", stringer))
            if scene.structure.keel:
                meshes.append(("keel", scene.structure.keel))

        if not meshes:
            return ExportResult(
                success=False,
                format=format,
                data=b"",
                metadata=ExportMetadata(
                    export_id=str(uuid.uuid4()),
                    design_id=scene.design_id,
                    format=format.value,
                ),
                errors=["No meshes in scene"],
            )

        # Calculate totals
        total_vertices = sum(m.vertex_count for _, m in meshes)
        total_faces = sum(m.face_count for _, m in meshes)

        metadata = ExportMetadata(
            export_id=str(uuid.uuid4()),
            design_id=scene.design_id,
            format=format.value,
            lod="medium",  # Default LOD - SceneData doesn't have lod attribute
            geometry_mode=scene.geometry_mode.value if hasattr(scene.geometry_mode, 'value') else str(scene.geometry_mode),
            vertex_count=total_vertices,
            face_count=total_faces,
            source_branch=self._source_branch,
            commit_hash=self._commit_hash,
        )

        try:
            if format in (ExportFormat.GLTF, ExportFormat.GLB):
                data = self._export_scene_gltf(meshes, scene.materials, metadata, binary=(format == ExportFormat.GLB))
            elif format in (ExportFormat.STL, ExportFormat.STL_ASCII):
                # Combine meshes for STL
                combined = self._combine_meshes(meshes)
                data = self._export_stl(combined, binary=(format == ExportFormat.STL))
            elif format == ExportFormat.OBJ:
                data = self._export_scene_obj(meshes)
            else:
                raise ExportError(format=format.value if hasattr(format, "value") else str(format), reason="unsupported_format")

            metadata.file_size_bytes = len(data)

            return ExportResult(
                success=True,
                format=format,
                data=data,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Scene export failed: {e}")
            return ExportResult(
                success=False,
                format=format,
                data=b"",
                metadata=metadata,
                errors=[str(e)],
            )

    # =========================================================================
    # glTF/GLB EXPORT (Module 67.3: Unified via GLTFBuilder)
    # =========================================================================

    def _export_gltf(self, mesh: MeshData, metadata: ExportMetadata, binary: bool = True) -> bytes:
        """
        Export mesh to glTF/GLB format using unified GLTFBuilder.

        Module 67.3: All mesh writing now goes through GLTFBuilder.write_mesh_primitive()
        to prevent divergence bugs like missing normals.
        """
        builder = GLTFBuilder(metadata)

        # Use hull policy by default for single mesh export
        policy = AttributePolicy.for_category(MeshCategory.HULL)
        builder.write_mesh_primitive(mesh, mesh.mesh_id or "hull", policy)

        return builder.finalize(binary=binary)

    def _export_scene_gltf(
        self,
        meshes: List[Tuple[str, MeshData]],
        materials: List[MaterialDef],
        metadata: ExportMetadata,
        binary: bool = True,
    ) -> bytes:
        """
        Export multiple meshes to glTF/GLB using unified GLTFBuilder.

        Module 67.3: All mesh writing now goes through GLTFBuilder.write_mesh_primitive()
        to prevent divergence bugs like missing normals.
        """
        builder = GLTFBuilder(metadata)

        # Add materials if present
        if materials:
            builder.add_materials(materials)

        # Write each mesh with appropriate policy
        for mesh_idx, (name, mesh) in enumerate(meshes):
            # Log mesh stats for debugging (data path verification)
            logger.debug(
                f"Scene mesh '{name}': vertices={len(mesh.vertices)}, "
                f"normals={len(mesh.normals) if mesh.normals else 0}"
            )

            # Determine mesh category from name
            if "hull" in name.lower():
                category = MeshCategory.HULL
            elif "deck" in name.lower():
                category = MeshCategory.DECK
            else:
                category = MeshCategory.STRUCTURE

            policy = AttributePolicy.for_category(category)
            builder.write_mesh_primitive(mesh, name, policy)

            # Assign material based on mesh name
            if materials:
                if "hull" in name.lower():
                    builder.set_primitive_material(mesh_idx, 0)
                elif "deck" in name.lower() and len(materials) > 1:
                    builder.set_primitive_material(mesh_idx, 1)
                elif "frame" in name.lower() or "structure" in name.lower():
                    builder.set_primitive_material(mesh_idx, min(2, len(materials) - 1))

        return builder.finalize(binary=binary)

    # =========================================================================
    # STL EXPORT
    # =========================================================================

    def _export_stl(self, mesh: MeshData, binary: bool = True) -> bytes:
        """Export mesh to STL format."""
        if binary:
            return self._export_stl_binary(mesh)
        else:
            return self._export_stl_ascii(mesh)

    def _export_stl_binary(self, mesh: MeshData) -> bytes:
        """Export to binary STL."""
        output = io.BytesIO()

        # Header (80 bytes)
        header = b"MAGNET WebGL Exporter v1.1" + b'\x00' * 54
        output.write(header[:80])

        # Triangle count
        triangle_count = len(mesh.indices) // 3
        output.write(struct.pack("<I", triangle_count))

        # Triangles
        for i in range(0, len(mesh.indices), 3):
            i0, i1, i2 = mesh.indices[i], mesh.indices[i+1], mesh.indices[i+2]

            # Get vertices
            v0 = (mesh.vertices[i0*3], mesh.vertices[i0*3+1], mesh.vertices[i0*3+2])
            v1 = (mesh.vertices[i1*3], mesh.vertices[i1*3+1], mesh.vertices[i1*3+2])
            v2 = (mesh.vertices[i2*3], mesh.vertices[i2*3+1], mesh.vertices[i2*3+2])

            # Calculate face normal
            e1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
            e2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
            n = (
                e1[1]*e2[2] - e1[2]*e2[1],
                e1[2]*e2[0] - e1[0]*e2[2],
                e1[0]*e2[1] - e1[1]*e2[0],
            )
            length = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
            if length > 0:
                n = (n[0]/length, n[1]/length, n[2]/length)
            else:
                n = (0, 0, 1)

            # Write normal
            output.write(struct.pack("<3f", n[0], n[1], n[2]))

            # Write vertices
            output.write(struct.pack("<3f", v0[0], v0[1], v0[2]))
            output.write(struct.pack("<3f", v1[0], v1[1], v1[2]))
            output.write(struct.pack("<3f", v2[0], v2[1], v2[2]))

            # Attribute byte count (unused)
            output.write(struct.pack("<H", 0))

        return output.getvalue()

    def _export_stl_ascii(self, mesh: MeshData) -> bytes:
        """Export to ASCII STL."""
        lines = ["solid hull"]

        for i in range(0, len(mesh.indices), 3):
            i0, i1, i2 = mesh.indices[i], mesh.indices[i+1], mesh.indices[i+2]

            v0 = (mesh.vertices[i0*3], mesh.vertices[i0*3+1], mesh.vertices[i0*3+2])
            v1 = (mesh.vertices[i1*3], mesh.vertices[i1*3+1], mesh.vertices[i1*3+2])
            v2 = (mesh.vertices[i2*3], mesh.vertices[i2*3+1], mesh.vertices[i2*3+2])

            # Calculate normal
            e1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
            e2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
            n = (
                e1[1]*e2[2] - e1[2]*e2[1],
                e1[2]*e2[0] - e1[0]*e2[2],
                e1[0]*e2[1] - e1[1]*e2[0],
            )
            length = math.sqrt(n[0]**2 + n[1]**2 + n[2]**2)
            if length > 0:
                n = (n[0]/length, n[1]/length, n[2]/length)
            else:
                n = (0, 0, 1)

            lines.append(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
            lines.append("    outer loop")
            lines.append(f"      vertex {v0[0]:.6e} {v0[1]:.6e} {v0[2]:.6e}")
            lines.append(f"      vertex {v1[0]:.6e} {v1[1]:.6e} {v1[2]:.6e}")
            lines.append(f"      vertex {v2[0]:.6e} {v2[1]:.6e} {v2[2]:.6e}")
            lines.append("    endloop")
            lines.append("  endfacet")

        lines.append("endsolid hull")

        return "\n".join(lines).encode('ascii')

    # =========================================================================
    # OBJ EXPORT
    # =========================================================================

    def _export_obj(self, mesh: MeshData) -> bytes:
        """Export mesh to OBJ format."""
        lines = [
            "# MAGNET WebGL Exporter v1.1",
            f"# Vertices: {mesh.vertex_count}",
            f"# Faces: {mesh.face_count}",
            "",
            "o hull",
        ]

        # Vertices
        for i in range(0, len(mesh.vertices), 3):
            x, y, z = mesh.vertices[i], mesh.vertices[i+1], mesh.vertices[i+2]
            lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")

        # Normals
        if mesh.normals:
            lines.append("")
            for i in range(0, len(mesh.normals), 3):
                nx, ny, nz = mesh.normals[i], mesh.normals[i+1], mesh.normals[i+2]
                lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")

        # Faces (OBJ is 1-indexed)
        lines.append("")
        if mesh.normals:
            for i in range(0, len(mesh.indices), 3):
                i0, i1, i2 = mesh.indices[i]+1, mesh.indices[i+1]+1, mesh.indices[i+2]+1
                lines.append(f"f {i0}//{i0} {i1}//{i1} {i2}//{i2}")
        else:
            for i in range(0, len(mesh.indices), 3):
                i0, i1, i2 = mesh.indices[i]+1, mesh.indices[i+1]+1, mesh.indices[i+2]+1
                lines.append(f"f {i0} {i1} {i2}")

        return "\n".join(lines).encode('utf-8')

    def _export_scene_obj(self, meshes: List[Tuple[str, MeshData]]) -> bytes:
        """Export multiple meshes to OBJ format."""
        lines = [
            "# MAGNET WebGL Exporter v1.1",
            f"# Objects: {len(meshes)}",
            "",
        ]

        vertex_offset = 0
        normal_offset = 0

        for name, mesh in meshes:
            lines.append(f"o {name}")

            # Vertices
            for i in range(0, len(mesh.vertices), 3):
                x, y, z = mesh.vertices[i], mesh.vertices[i+1], mesh.vertices[i+2]
                lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")

            # Normals
            if mesh.normals:
                for i in range(0, len(mesh.normals), 3):
                    nx, ny, nz = mesh.normals[i], mesh.normals[i+1], mesh.normals[i+2]
                    lines.append(f"vn {nx:.6f} {ny:.6f} {nz:.6f}")

            # Faces
            lines.append(f"g {name}")
            if mesh.normals:
                for i in range(0, len(mesh.indices), 3):
                    i0 = mesh.indices[i] + 1 + vertex_offset
                    i1 = mesh.indices[i+1] + 1 + vertex_offset
                    i2 = mesh.indices[i+2] + 1 + vertex_offset
                    n0 = mesh.indices[i] + 1 + normal_offset
                    n1 = mesh.indices[i+1] + 1 + normal_offset
                    n2 = mesh.indices[i+2] + 1 + normal_offset
                    lines.append(f"f {i0}//{n0} {i1}//{n1} {i2}//{n2}")
            else:
                for i in range(0, len(mesh.indices), 3):
                    i0 = mesh.indices[i] + 1 + vertex_offset
                    i1 = mesh.indices[i+1] + 1 + vertex_offset
                    i2 = mesh.indices[i+2] + 1 + vertex_offset
                    lines.append(f"f {i0} {i1} {i2}")

            vertex_offset += mesh.vertex_count
            if mesh.normals:
                normal_offset += len(mesh.normals) // 3

            lines.append("")

        return "\n".join(lines).encode('utf-8')

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _combine_meshes(self, meshes: List[Tuple[str, MeshData]]) -> MeshData:
        """Combine multiple meshes into one."""
        combined_vertices = []
        combined_indices = []
        combined_normals = []

        vertex_offset = 0

        for name, mesh in meshes:
            combined_vertices.extend(mesh.vertices)

            for idx in mesh.indices:
                combined_indices.append(idx + vertex_offset)

            if mesh.normals:
                combined_normals.extend(mesh.normals)

            vertex_offset += mesh.vertex_count

        return MeshData(
            mesh_id="combined",
            vertices=combined_vertices,
            indices=combined_indices,
            normals=combined_normals if combined_normals else None,
        )
