/**
 * binaryParser.ts - Binary mesh data parser v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Parses binary mesh format for efficient transfer.
 */

import type { MeshData, BoundingBox } from '../types/schema';
import { BINARY_MAGIC, BINARY_VERSION, FLAG_HAS_UVS, FLAG_HAS_COLORS, FLAG_HAS_TANGENTS } from '../types/schema';

// =============================================================================
// TYPES
// =============================================================================

export interface BinaryHeader {
  magic: number;
  version: number;
  vertexCount: number;
  faceCount: number;
  flags: number;
  reserved: number;
}

export interface ParsedMeshData {
  vertices: Float32Array;
  indices: Uint32Array;
  normals: Float32Array;
  uvs: Float32Array | null;
  colors: Float32Array | null;
  tangents: Float32Array | null;
  vertexCount: number;
  faceCount: number;
}

// =============================================================================
// PARSING
// =============================================================================

/**
 * Parse binary header from ArrayBuffer.
 */
export function parseHeader(buffer: ArrayBuffer): BinaryHeader {
  if (buffer.byteLength < 24) {
    throw new Error(`Invalid binary data: too short (${buffer.byteLength} bytes)`);
  }

  const view = new DataView(buffer);

  return {
    magic: view.getUint32(0, true),
    version: view.getUint32(4, true),
    vertexCount: view.getUint32(8, true),
    faceCount: view.getUint32(12, true),
    flags: view.getUint32(16, true),
    reserved: view.getUint32(20, true),
  };
}

/**
 * Validate binary header.
 */
export function validateHeader(header: BinaryHeader): void {
  if (header.magic !== BINARY_MAGIC) {
    throw new Error(`Invalid magic: 0x${header.magic.toString(16)}, expected 0x${BINARY_MAGIC.toString(16)}`);
  }

  if (header.version !== BINARY_VERSION) {
    throw new Error(`Unsupported version: ${header.version}, expected ${BINARY_VERSION}`);
  }

  if (header.vertexCount === 0) {
    throw new Error('Invalid mesh: vertex count is 0');
  }

  if (header.faceCount === 0) {
    throw new Error('Invalid mesh: face count is 0');
  }
}

/**
 * Parse binary mesh data from ArrayBuffer.
 */
export function parseBinaryMesh(buffer: ArrayBuffer): ParsedMeshData {
  const header = parseHeader(buffer);
  validateHeader(header);

  const { vertexCount, faceCount, flags } = header;
  let offset = 24; // Header size

  // Calculate expected sizes
  const verticesSize = vertexCount * 3 * 4;
  const indicesSize = faceCount * 3 * 4;
  const normalsSize = vertexCount * 3 * 4;

  // Read vertices
  const vertices = new Float32Array(buffer, offset, vertexCount * 3);
  offset += verticesSize;

  // Read indices
  const indices = new Uint32Array(buffer, offset, faceCount * 3);
  offset += indicesSize;

  // Read normals
  const normals = new Float32Array(buffer, offset, vertexCount * 3);
  offset += normalsSize;

  // Read optional UVs
  let uvs: Float32Array | null = null;
  if (flags & FLAG_HAS_UVS) {
    const uvsSize = vertexCount * 2 * 4;
    uvs = new Float32Array(buffer, offset, vertexCount * 2);
    offset += uvsSize;
  }

  // Read optional colors
  let colors: Float32Array | null = null;
  if (flags & FLAG_HAS_COLORS) {
    const colorsSize = vertexCount * 4 * 4;
    colors = new Float32Array(buffer, offset, vertexCount * 4);
    offset += colorsSize;
  }

  // Read optional tangents
  let tangents: Float32Array | null = null;
  if (flags & FLAG_HAS_TANGENTS) {
    const tangentsSize = vertexCount * 4 * 4;
    tangents = new Float32Array(buffer, offset, vertexCount * 4);
    offset += tangentsSize;
  }

  return {
    vertices,
    indices,
    normals,
    uvs,
    colors,
    tangents,
    vertexCount,
    faceCount,
  };
}

/**
 * Convert parsed binary data to MeshData schema format.
 */
export function toMeshData(parsed: ParsedMeshData, meshId: string = ''): MeshData {
  // Calculate bounding box
  const bounds = calculateBounds(parsed.vertices);

  return {
    mesh_id: meshId,
    vertices: Array.from(parsed.vertices),
    indices: Array.from(parsed.indices),
    normals: Array.from(parsed.normals),
    uvs: parsed.uvs ? Array.from(parsed.uvs) : undefined,
    colors: parsed.colors ? Array.from(parsed.colors) : undefined,
    tangents: parsed.tangents ? Array.from(parsed.tangents) : undefined,
    metadata: {
      vertex_count: parsed.vertexCount,
      face_count: parsed.faceCount,
      bounds,
      has_uvs: parsed.uvs !== null,
      has_colors: parsed.colors !== null,
      has_tangents: parsed.tangents !== null,
    },
  };
}

/**
 * Calculate bounding box from vertices.
 */
export function calculateBounds(vertices: Float32Array): BoundingBox {
  if (vertices.length === 0) {
    return {
      min: [0, 0, 0],
      max: [0, 0, 0],
    };
  }

  let minX = Infinity, minY = Infinity, minZ = Infinity;
  let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;

  for (let i = 0; i < vertices.length; i += 3) {
    const x = vertices[i];
    const y = vertices[i + 1];
    const z = vertices[i + 2];

    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    minZ = Math.min(minZ, z);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
    maxZ = Math.max(maxZ, z);
  }

  return {
    min: [minX, minY, minZ],
    max: [maxX, maxY, maxZ],
  };
}

// =============================================================================
// STREAMING
// =============================================================================

/**
 * Parse binary mesh from a stream (chunked transfer).
 */
export async function parseBinaryStream(
  stream: ReadableStream<Uint8Array>,
  onProgress?: (bytesLoaded: number) => void,
): Promise<ParsedMeshData> {
  const reader = stream.getReader();
  const chunks: Uint8Array[] = [];
  let totalBytes = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      chunks.push(value);
      totalBytes += value.length;
      onProgress?.(totalBytes);
    }

    // Combine chunks into single buffer
    const buffer = new ArrayBuffer(totalBytes);
    const view = new Uint8Array(buffer);
    let offset = 0;

    for (const chunk of chunks) {
      view.set(chunk, offset);
      offset += chunk.length;
    }

    return parseBinaryMesh(buffer);
  } finally {
    reader.releaseLock();
  }
}

// =============================================================================
// UTILITIES
// =============================================================================

/**
 * Check if buffer is a valid binary mesh.
 */
export function isValidBinaryMesh(buffer: ArrayBuffer): boolean {
  try {
    const header = parseHeader(buffer);
    validateHeader(header);
    return true;
  } catch {
    return false;
  }
}

/**
 * Get expected buffer size from header.
 */
export function getExpectedBufferSize(header: BinaryHeader): number {
  let size = 24; // Header

  // Required data
  size += header.vertexCount * 3 * 4; // Vertices
  size += header.faceCount * 3 * 4;   // Indices
  size += header.vertexCount * 3 * 4; // Normals

  // Optional data
  if (header.flags & FLAG_HAS_UVS) {
    size += header.vertexCount * 2 * 4;
  }
  if (header.flags & FLAG_HAS_COLORS) {
    size += header.vertexCount * 4 * 4;
  }
  if (header.flags & FLAG_HAS_TANGENTS) {
    size += header.vertexCount * 4 * 4;
  }

  return size;
}

/**
 * Format bytes as human-readable string.
 */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
