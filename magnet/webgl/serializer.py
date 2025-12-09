"""
webgl/serializer.py - Binary serialization for geometry data v1.1

Module 58: WebGL 3D Visualization
ALPHA OWNS THIS FILE.

Provides efficient binary serialization for mesh data transmission.

Addresses: FM2 (Schema drift through versioned binary format)
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Dict, Any, Tuple, BinaryIO
from dataclasses import dataclass
import struct
import io
import logging
import zlib

from .schema import (
    MeshData,
    SceneData,
    MaterialDef,
    BoundingBox,
    SCHEMA_VERSION,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger("webgl.serializer")


# =============================================================================
# BINARY FORMAT CONSTANTS
# =============================================================================

# Magic number: "MNET" (MAGNET NET)
MAGIC = b"MNET"
FORMAT_VERSION = 1

# Section types
SECTION_MESH = 0x01
SECTION_MATERIAL = 0x02
SECTION_BOUNDS = 0x03
SECTION_METADATA = 0x04
SECTION_SCENE = 0x10
SECTION_END = 0xFF

# Compression flags
COMPRESS_NONE = 0x00
COMPRESS_ZLIB = 0x01


# =============================================================================
# HEADER STRUCTURES
# =============================================================================

@dataclass
class BinaryHeader:
    """Binary format header."""
    magic: bytes = MAGIC
    version: int = FORMAT_VERSION
    schema_version: str = SCHEMA_VERSION
    compression: int = COMPRESS_NONE
    flags: int = 0
    section_count: int = 0
    total_size: int = 0


def _write_header(writer: BinaryIO, header: BinaryHeader) -> int:
    """Write binary header. Returns bytes written."""
    # Magic (4 bytes)
    writer.write(header.magic)

    # Version (2 bytes)
    writer.write(struct.pack("<H", header.version))

    # Schema version as length-prefixed string
    schema_bytes = header.schema_version.encode("utf-8")
    writer.write(struct.pack("<B", len(schema_bytes)))
    writer.write(schema_bytes)

    # Compression (1 byte)
    writer.write(struct.pack("<B", header.compression))

    # Flags (2 bytes)
    writer.write(struct.pack("<H", header.flags))

    # Section count (2 bytes)
    writer.write(struct.pack("<H", header.section_count))

    # Total size placeholder (4 bytes) - will be updated
    size_pos = writer.tell()
    writer.write(struct.pack("<I", 0))

    return size_pos


def _read_header(reader: BinaryIO) -> BinaryHeader:
    """Read binary header."""
    magic = reader.read(4)
    if magic != MAGIC:
        raise ValueError(f"Invalid magic number: {magic}")

    version = struct.unpack("<H", reader.read(2))[0]

    schema_len = struct.unpack("<B", reader.read(1))[0]
    schema_version = reader.read(schema_len).decode("utf-8")

    compression = struct.unpack("<B", reader.read(1))[0]
    flags = struct.unpack("<H", reader.read(2))[0]
    section_count = struct.unpack("<H", reader.read(2))[0]
    total_size = struct.unpack("<I", reader.read(4))[0]

    return BinaryHeader(
        magic=magic,
        version=version,
        schema_version=schema_version,
        compression=compression,
        flags=flags,
        section_count=section_count,
        total_size=total_size,
    )


# =============================================================================
# MESH SERIALIZATION
# =============================================================================

def serialize_mesh(mesh: MeshData, compress: bool = True) -> bytes:
    """
    Serialize a MeshData to binary format.

    Format:
    - Header (variable)
    - Vertices section: [type, count, data...]
    - Indices section: [type, count, data...]
    - Normals section: [type, count, data...]
    - UVs section (optional): [type, count, data...]
    - Metadata section: [type, json_data]
    - End marker
    """
    buffer = io.BytesIO()
    section_count = 0

    # Write placeholder header
    header = BinaryHeader(
        compression=COMPRESS_ZLIB if compress else COMPRESS_NONE,
    )
    size_pos = _write_header(buffer, header)

    # Write mesh section header
    buffer.write(struct.pack("<B", SECTION_MESH))
    section_count += 1

    # Mesh ID
    mesh_id_bytes = mesh.mesh_id.encode("utf-8")
    buffer.write(struct.pack("<H", len(mesh_id_bytes)))
    buffer.write(mesh_id_bytes)

    # Vertex count and data
    vertex_count = mesh.vertex_count
    buffer.write(struct.pack("<I", vertex_count))

    # Pack vertices as flat float32 array
    vertex_data = struct.pack(f"<{vertex_count * 3}f", *mesh.vertices)
    buffer.write(vertex_data)

    # Index count and data
    index_count = len(mesh.indices)
    buffer.write(struct.pack("<I", index_count))

    # Pack indices as uint32
    index_data = struct.pack(f"<{index_count}I", *mesh.indices)
    buffer.write(index_data)

    # Normal count and data
    if mesh.normals:
        normal_count = len(mesh.normals) // 3
        buffer.write(struct.pack("<I", normal_count))
        normal_data = struct.pack(f"<{len(mesh.normals)}f", *mesh.normals)
        buffer.write(normal_data)
    else:
        buffer.write(struct.pack("<I", 0))

    # UV count and data
    if mesh.uvs:
        uv_count = len(mesh.uvs) // 2
        buffer.write(struct.pack("<I", uv_count))
        uv_data = struct.pack(f"<{len(mesh.uvs)}f", *mesh.uvs)
        buffer.write(uv_data)
    else:
        buffer.write(struct.pack("<I", 0))

    # Bounding box
    if mesh.bounds:
        buffer.write(struct.pack("<B", SECTION_BOUNDS))
        section_count += 1
        buffer.write(struct.pack("<6f",
            mesh.bounds.min[0], mesh.bounds.min[1], mesh.bounds.min[2],
            mesh.bounds.max[0], mesh.bounds.max[1], mesh.bounds.max[2],
        ))

    # End marker
    buffer.write(struct.pack("<B", SECTION_END))

    # Get raw data
    raw_data = buffer.getvalue()

    # Compress if requested
    if compress:
        # Compress everything after header
        header_size = size_pos + 4  # size_pos is where total_size starts
        compressed = zlib.compress(raw_data[header_size:], level=6)

        # Rebuild with compressed data
        final_buffer = io.BytesIO()
        final_buffer.write(raw_data[:header_size])
        final_buffer.write(compressed)
        raw_data = final_buffer.getvalue()

    # Update header with section count and total size
    final_buffer = io.BytesIO(raw_data)
    final_buffer.seek(size_pos - 2)  # Go to section_count position
    final_buffer.write(struct.pack("<H", section_count))
    final_buffer.write(struct.pack("<I", len(raw_data)))

    return final_buffer.getvalue()


def deserialize_mesh(data: bytes) -> MeshData:
    """Deserialize binary data to MeshData."""
    reader = io.BytesIO(data)

    # Read header
    header = _read_header(reader)

    if header.version > FORMAT_VERSION:
        logger.warning(f"Binary format version {header.version} > {FORMAT_VERSION}")

    # Decompress if needed
    if header.compression == COMPRESS_ZLIB:
        compressed_data = reader.read()
        decompressed = zlib.decompress(compressed_data)
        reader = io.BytesIO(decompressed)

    # Initialize mesh data
    mesh_id = ""
    vertices = []
    indices = []
    normals = []
    uvs = []
    bounds = None

    # Read sections
    while True:
        section_type_data = reader.read(1)
        if not section_type_data:
            break

        section_type = struct.unpack("<B", section_type_data)[0]

        if section_type == SECTION_END:
            break
        elif section_type == SECTION_MESH:
            # Read mesh ID
            id_len = struct.unpack("<H", reader.read(2))[0]
            mesh_id = reader.read(id_len).decode("utf-8")

            # Read vertices
            vertex_count = struct.unpack("<I", reader.read(4))[0]
            vertex_data = reader.read(vertex_count * 3 * 4)
            vertices = list(struct.unpack(f"<{vertex_count * 3}f", vertex_data))

            # Read indices
            index_count = struct.unpack("<I", reader.read(4))[0]
            index_data = reader.read(index_count * 4)
            indices = list(struct.unpack(f"<{index_count}I", index_data))

            # Read normals
            normal_count = struct.unpack("<I", reader.read(4))[0]
            if normal_count > 0:
                normal_data = reader.read(normal_count * 3 * 4)
                normals = list(struct.unpack(f"<{normal_count * 3}f", normal_data))

            # Read UVs
            uv_count = struct.unpack("<I", reader.read(4))[0]
            if uv_count > 0:
                uv_data = reader.read(uv_count * 2 * 4)
                uvs = list(struct.unpack(f"<{uv_count * 2}f", uv_data))

        elif section_type == SECTION_BOUNDS:
            bounds_data = struct.unpack("<6f", reader.read(24))
            bounds = BoundingBox(
                min=(bounds_data[0], bounds_data[1], bounds_data[2]),
                max=(bounds_data[3], bounds_data[4], bounds_data[5]),
            )

    return MeshData(
        mesh_id=mesh_id,
        vertices=vertices,
        indices=indices,
        normals=normals,
        uvs=uvs,
        bounds=bounds,
    )


# =============================================================================
# SCENE SERIALIZATION
# =============================================================================

def serialize_scene(scene: SceneData, compress: bool = True) -> bytes:
    """
    Serialize a SceneData to binary format.

    Format:
    - Header
    - Scene metadata section
    - Hull mesh section
    - Deck mesh section (optional)
    - Structure meshes (optional)
    - Materials section
    - End marker
    """
    import json

    buffer = io.BytesIO()
    section_count = 0

    # Write placeholder header
    header = BinaryHeader(
        compression=COMPRESS_ZLIB if compress else COMPRESS_NONE,
    )
    size_pos = _write_header(buffer, header)

    # Scene section
    buffer.write(struct.pack("<B", SECTION_SCENE))
    section_count += 1

    # Scene metadata as JSON
    metadata = {
        "design_id": scene.design_id,
        "version_id": scene.version_id,
        "geometry_mode": scene.geometry_mode.value if hasattr(scene.geometry_mode, 'value') else scene.geometry_mode,
    }
    metadata_json = json.dumps(metadata).encode("utf-8")
    buffer.write(struct.pack("<I", len(metadata_json)))
    buffer.write(metadata_json)

    # Hull mesh
    if scene.hull:
        hull_bytes = serialize_mesh(scene.hull, compress=False)
        buffer.write(struct.pack("<I", len(hull_bytes)))
        buffer.write(hull_bytes)
    else:
        buffer.write(struct.pack("<I", 0))

    # Deck mesh
    if scene.deck:
        deck_bytes = serialize_mesh(scene.deck, compress=False)
        buffer.write(struct.pack("<I", len(deck_bytes)))
        buffer.write(deck_bytes)
    else:
        buffer.write(struct.pack("<I", 0))

    # Structure count and meshes
    if scene.structure and scene.structure.frames:
        structure_count = len(scene.structure.frames)
        buffer.write(struct.pack("<H", structure_count))

        for frame_mesh in scene.structure.frames:
            frame_bytes = serialize_mesh(frame_mesh, compress=False)
            buffer.write(struct.pack("<I", len(frame_bytes)))
            buffer.write(frame_bytes)
    else:
        buffer.write(struct.pack("<H", 0))

    # Materials
    buffer.write(struct.pack("<B", SECTION_MATERIAL))
    section_count += 1

    material_count = len(scene.materials)
    buffer.write(struct.pack("<H", material_count))

    for material in scene.materials:
        mat_json = json.dumps(material.to_dict()).encode("utf-8")
        buffer.write(struct.pack("<H", len(mat_json)))
        buffer.write(mat_json)

    # End marker
    buffer.write(struct.pack("<B", SECTION_END))

    # Get raw data
    raw_data = buffer.getvalue()

    # Compress if requested
    if compress:
        header_size = size_pos + 4
        compressed = zlib.compress(raw_data[header_size:], level=6)

        final_buffer = io.BytesIO()
        final_buffer.write(raw_data[:header_size])
        final_buffer.write(compressed)
        raw_data = final_buffer.getvalue()

    # Update header
    final_buffer = io.BytesIO(raw_data)
    final_buffer.seek(size_pos - 2)
    final_buffer.write(struct.pack("<H", section_count))
    final_buffer.write(struct.pack("<I", len(raw_data)))

    return final_buffer.getvalue()


def deserialize_scene(data: bytes) -> SceneData:
    """Deserialize binary data to SceneData."""
    import json
    from .schema import GeometryMode, StructureSceneData

    reader = io.BytesIO(data)

    # Read header
    header = _read_header(reader)

    # Decompress if needed
    if header.compression == COMPRESS_ZLIB:
        compressed_data = reader.read()
        decompressed = zlib.decompress(compressed_data)
        reader = io.BytesIO(decompressed)

    # Initialize
    design_id = ""
    version_id = ""
    geometry_mode = GeometryMode.AUTHORITATIVE
    hull = None
    deck = None
    structure = None
    materials = []

    # Read sections
    while True:
        section_type_data = reader.read(1)
        if not section_type_data:
            break

        section_type = struct.unpack("<B", section_type_data)[0]

        if section_type == SECTION_END:
            break
        elif section_type == SECTION_SCENE:
            # Read metadata JSON
            meta_len = struct.unpack("<I", reader.read(4))[0]
            meta_json = reader.read(meta_len).decode("utf-8")
            metadata = json.loads(meta_json)

            design_id = metadata.get("design_id", "")
            version_id = metadata.get("version_id", "")

            mode_str = metadata.get("geometry_mode", "authoritative")
            geometry_mode = GeometryMode(mode_str) if mode_str in [m.value for m in GeometryMode] else GeometryMode.AUTHORITATIVE

            # Read hull
            hull_len = struct.unpack("<I", reader.read(4))[0]
            if hull_len > 0:
                hull_data = reader.read(hull_len)
                hull = deserialize_mesh(hull_data)

            # Read deck
            deck_len = struct.unpack("<I", reader.read(4))[0]
            if deck_len > 0:
                deck_data = reader.read(deck_len)
                deck = deserialize_mesh(deck_data)

            # Read structure
            structure_count = struct.unpack("<H", reader.read(2))[0]
            if structure_count > 0:
                frames = []
                for _ in range(structure_count):
                    frame_len = struct.unpack("<I", reader.read(4))[0]
                    frame_data = reader.read(frame_len)
                    frames.append(deserialize_mesh(frame_data))
                structure = StructureSceneData(frames=frames)

        elif section_type == SECTION_MATERIAL:
            mat_count = struct.unpack("<H", reader.read(2))[0]
            for _ in range(mat_count):
                mat_len = struct.unpack("<H", reader.read(2))[0]
                mat_json = reader.read(mat_len).decode("utf-8")
                mat_dict = json.loads(mat_json)
                materials.append(MaterialDef.from_dict(mat_dict))

    return SceneData(
        design_id=design_id,
        version_id=version_id,
        geometry_mode=geometry_mode,
        hull=hull,
        deck=deck,
        structure=structure,
        materials=materials,
    )


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def estimate_serialized_size(mesh: MeshData) -> int:
    """Estimate serialized size in bytes (uncompressed)."""
    # Header: ~20 bytes
    # Vertices: 4 bytes * 3 * vertex_count
    # Indices: 4 bytes * index_count
    # Normals: 4 bytes * 3 * vertex_count (if present)
    # UVs: 4 bytes * 2 * vertex_count (if present)
    # Bounds: 24 bytes
    # Overhead: ~50 bytes

    size = 70  # Header + overhead
    size += mesh.vertex_count * 12  # Vertices
    size += len(mesh.indices) * 4   # Indices

    if mesh.normals:
        size += len(mesh.normals) * 4
    if mesh.uvs:
        size += len(mesh.uvs) * 4
    if mesh.bounds:
        size += 24

    return size


def get_compression_ratio(original: bytes, compressed: bytes) -> float:
    """Calculate compression ratio."""
    if len(original) == 0:
        return 0.0
    return 1.0 - (len(compressed) / len(original))


def validate_binary_format(data: bytes) -> Tuple[bool, str]:
    """
    Validate binary data format.

    Returns (is_valid, error_message).
    """
    if len(data) < 12:
        return False, "Data too short for header"

    # Check magic
    if data[:4] != MAGIC:
        return False, f"Invalid magic: expected {MAGIC}, got {data[:4]}"

    try:
        reader = io.BytesIO(data)
        header = _read_header(reader)

        if header.version > FORMAT_VERSION:
            return False, f"Unsupported format version: {header.version}"

        if header.total_size != len(data):
            return False, f"Size mismatch: header says {header.total_size}, got {len(data)}"

        return True, ""

    except Exception as e:
        return False, f"Parse error: {str(e)}"
