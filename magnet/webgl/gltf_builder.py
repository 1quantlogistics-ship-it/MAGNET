"""
webgl/gltf_builder.py - Unified glTF/GLB construction v1.0

Module 67.3: GLTF Export/Viewer Contract Consolidation
ALPHA OWNS THIS FILE.

Single source of truth for glTF/GLB construction.

INVARIANT: All mesh writing goes through write_mesh_primitive().
No other method writes vertex/normal/index data.
This eliminates the divergence bug where _export_scene_gltf() omitted normals.
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import struct
import io
import json
import logging

from .contracts import (
    MeshCategory,
    AttributePolicy,
    PrimitiveRef,
    MeshContractValidator,
)
from .errors import ExportError

if TYPE_CHECKING:
    from .schema import MeshData, ExportMetadata


logger = logging.getLogger("webgl.gltf_builder")


class GLTFBuilder:
    """
    Single source of truth for glTF/GLB construction.

    INVARIANT: All mesh writing goes through write_mesh_primitive().
    No other method writes vertex/normal/index data.
    """

    def __init__(self, metadata: "ExportMetadata"):
        self._buffer = io.BytesIO()
        self._gltf: Dict[str, Any] = {
            "asset": {
                "version": "2.0",
                "generator": "MAGNET v1.2",
                "extras": metadata.to_dict() if hasattr(metadata, 'to_dict') else {},
            },
            "scene": 0,
            "scenes": [{"nodes": []}],
            "nodes": [],
            "meshes": [],
            "accessors": [],
            "bufferViews": [],
            "buffers": [],
        }
        self._attribute_mode = "COMPLETE"

    def _align_buffer(self, alignment: int = 4) -> None:
        """
        Pad buffer to alignment boundary.

        glTF 2.0 requires bufferView byte offsets to be multiples of 4.
        """
        current = self._buffer.tell()
        padding = (alignment - current % alignment) % alignment
        if padding:
            self._buffer.write(b'\x00' * padding)

    def write_mesh_primitive(
        self,
        mesh: "MeshData",
        name: str,
        policy: AttributePolicy,
    ) -> PrimitiveRef:
        """
        Write a single mesh primitive with policy enforcement.

        This is THE ONLY method that writes mesh data to the buffer.

        Args:
            mesh: The mesh data to write
            name: Name for the mesh in the glTF
            policy: Attribute policy defining requirements

        Returns:
            PrimitiveRef with accessor indices

        Raises:
            ExportError: If mesh violates the policy contract
        """
        # 1. Validate against policy - FAIL LOUDLY
        errors = MeshContractValidator.validate(mesh, policy, name)
        if errors:
            raise ExportError(format="gltf", reason="mesh_contract_violation")

        # Log mesh stats for debugging
        logger.debug(
            f"Writing mesh '{name}': vertices={len(mesh.vertices)}, "
            f"normals={len(mesh.normals) if mesh.normals else 0}, "
            f"indices={len(mesh.indices) if mesh.indices else 0}"
        )

        # 2. Write POSITION (always required)
        self._align_buffer(4)
        pos_offset = self._buffer.tell()
        min_pos, max_pos = self._write_positions(mesh.vertices)
        pos_length = self._buffer.tell() - pos_offset

        # 3. Write NORMAL (if required by policy)
        norm_offset = None
        norm_length = 0
        if policy.require_normal and mesh.normals:
            self._align_buffer(4)  # Ensure 4-byte alignment before normals
            norm_offset = self._buffer.tell()
            self._write_normals(mesh.normals)
            norm_length = self._buffer.tell() - norm_offset
        elif policy.require_normal:
            # Policy requires normals but mesh has none - already caught by validator
            self._attribute_mode = "MISSING_NORMALS"

        # 4. Write indices (if required)
        idx_offset = None
        idx_length = 0
        if policy.require_indices and mesh.indices:
            self._align_buffer(4)  # Ensure 4-byte alignment before indices
            idx_offset = self._buffer.tell()
            self._write_indices(mesh.indices)
            idx_length = self._buffer.tell() - idx_offset

        # 5. Create bufferViews and accessors
        pos_bv_idx = len(self._gltf["bufferViews"])
        self._gltf["bufferViews"].append({
            "buffer": 0,
            "byteOffset": pos_offset,
            "byteLength": pos_length,
            "target": 34962,  # ARRAY_BUFFER
        })

        pos_acc_idx = len(self._gltf["accessors"])
        self._gltf["accessors"].append({
            "bufferView": pos_bv_idx,
            "byteOffset": 0,
            "componentType": 5126,  # FLOAT
            "count": len(mesh.vertices) // 3,
            "type": "VEC3",
            "min": list(min_pos),
            "max": list(max_pos),
        })

        norm_acc_idx = None
        if norm_offset is not None:
            norm_bv_idx = len(self._gltf["bufferViews"])
            self._gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": norm_offset,
                "byteLength": norm_length,
                "target": 34962,
            })
            norm_acc_idx = len(self._gltf["accessors"])
            self._gltf["accessors"].append({
                "bufferView": norm_bv_idx,
                "byteOffset": 0,
                "componentType": 5126,
                "count": len(mesh.normals) // 3,
                "type": "VEC3",
                # Normals don't need min/max
            })

        idx_acc_idx = None
        if idx_offset is not None:
            idx_bv_idx = len(self._gltf["bufferViews"])
            self._gltf["bufferViews"].append({
                "buffer": 0,
                "byteOffset": idx_offset,
                "byteLength": idx_length,
                "target": 34963,  # ELEMENT_ARRAY_BUFFER
            })
            idx_acc_idx = len(self._gltf["accessors"])
            self._gltf["accessors"].append({
                "bufferView": idx_bv_idx,
                "byteOffset": 0,
                "componentType": 5125,  # UNSIGNED_INT
                "count": len(mesh.indices),
                "type": "SCALAR",
            })

        # 6. Create primitive
        primitive: Dict[str, Any] = {
            "attributes": {"POSITION": pos_acc_idx},
            "mode": policy.primitive_mode,
        }
        if norm_acc_idx is not None:
            primitive["attributes"]["NORMAL"] = norm_acc_idx
        if idx_acc_idx is not None:
            primitive["indices"] = idx_acc_idx

        # 7. Add to glTF structure
        mesh_idx = len(self._gltf["meshes"])
        self._gltf["meshes"].append({"primitives": [primitive], "name": name})
        self._gltf["nodes"].append({"mesh": mesh_idx, "name": name})
        self._gltf["scenes"][0]["nodes"].append(len(self._gltf["nodes"]) - 1)

        return PrimitiveRef(
            mesh_idx=mesh_idx,
            primitive_idx=0,
            pos_accessor_idx=pos_acc_idx,
            norm_accessor_idx=norm_acc_idx,
            idx_accessor_idx=idx_acc_idx,
        )

    def add_materials(self, materials: List[Any]) -> None:
        """
        Add materials to the glTF.

        Args:
            materials: List of MaterialDef objects
        """
        if not materials:
            return

        self._gltf["materials"] = []
        for mat in materials:
            # Convert hex color to RGB factors
            color_hex = mat.color.lstrip('#')
            if len(color_hex) == 6:
                r = int(color_hex[0:2], 16) / 255.0
                g = int(color_hex[2:4], 16) / 255.0
                b = int(color_hex[4:6], 16) / 255.0
            else:
                r, g, b = 0.7, 0.7, 0.7  # Default gray

            gltf_mat = {
                "name": mat.name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": [r, g, b, mat.opacity],
                    "metallicFactor": mat.metalness,
                    "roughnessFactor": mat.roughness,
                },
            }
            if mat.opacity < 1.0:
                gltf_mat["alphaMode"] = "BLEND"
            self._gltf["materials"].append(gltf_mat)

    def set_primitive_material(self, mesh_idx: int, material_idx: int) -> None:
        """
        Assign a material to a mesh primitive.

        Args:
            mesh_idx: Index of the mesh
            material_idx: Index of the material to assign
        """
        if mesh_idx < len(self._gltf["meshes"]):
            if "materials" in self._gltf and material_idx < len(self._gltf["materials"]):
                self._gltf["meshes"][mesh_idx]["primitives"][0]["material"] = material_idx

    def finalize(self, binary: bool = True) -> bytes:
        """
        Finalize and return GLB or glTF bytes.

        Args:
            binary: If True, return GLB; if False, return glTF JSON with embedded buffer

        Returns:
            Bytes of the complete GLB or glTF file
        """
        # Pad buffer to 4-byte boundary
        self._align_buffer(4)
        buffer_bytes = self._buffer.getvalue()

        self._gltf["buffers"].append({"byteLength": len(buffer_bytes)})

        if binary:
            return self._build_glb(buffer_bytes)
        else:
            return self._build_gltf_json(buffer_bytes)

    @property
    def attribute_mode(self) -> str:
        """Return the attribute mode (COMPLETE or MISSING_NORMALS)."""
        return self._attribute_mode

    def _write_positions(self, vertices: List[float]) -> Tuple[List[float], List[float]]:
        """Write position data, return (min, max) bounds."""
        min_pos = [float('inf')] * 3
        max_pos = [float('-inf')] * 3

        for i in range(0, len(vertices), 3):
            x, y, z = vertices[i], vertices[i+1], vertices[i+2]
            self._buffer.write(struct.pack("<3f", x, y, z))
            min_pos[0] = min(min_pos[0], x)
            min_pos[1] = min(min_pos[1], y)
            min_pos[2] = min(min_pos[2], z)
            max_pos[0] = max(max_pos[0], x)
            max_pos[1] = max(max_pos[1], y)
            max_pos[2] = max(max_pos[2], z)

        return min_pos, max_pos

    def _write_normals(self, normals: List[float]) -> None:
        """Write normal data."""
        for i in range(0, len(normals), 3):
            self._buffer.write(struct.pack("<3f", normals[i], normals[i+1], normals[i+2]))

    def _write_indices(self, indices: List[int]) -> None:
        """Write index data as uint32."""
        for idx in indices:
            self._buffer.write(struct.pack("<I", idx))

    def _build_glb(self, buffer_bytes: bytes) -> bytes:
        """Build binary GLB format."""
        json_str = json.dumps(self._gltf, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')

        # Pad JSON to 4-byte boundary with spaces
        json_padding = (4 - len(json_bytes) % 4) % 4
        json_bytes += b' ' * json_padding

        output = io.BytesIO()

        # Header (12 bytes)
        output.write(b'glTF')
        output.write(struct.pack("<I", 2))  # Version
        total_length = 12 + 8 + len(json_bytes) + 8 + len(buffer_bytes)
        output.write(struct.pack("<I", total_length))

        # JSON chunk
        output.write(struct.pack("<I", len(json_bytes)))
        output.write(struct.pack("<I", 0x4E4F534A))  # "JSON"
        output.write(json_bytes)

        # BIN chunk
        output.write(struct.pack("<I", len(buffer_bytes)))
        output.write(struct.pack("<I", 0x004E4942))  # "BIN\0"
        output.write(buffer_bytes)

        return output.getvalue()

    def _build_gltf_json(self, buffer_bytes: bytes) -> bytes:
        """Build glTF JSON with embedded base64 buffer."""
        import base64
        self._gltf["buffers"][0]["uri"] = (
            "data:application/octet-stream;base64," +
            base64.b64encode(buffer_bytes).decode('ascii')
        )
        return json.dumps(self._gltf, indent=2).encode('utf-8')
