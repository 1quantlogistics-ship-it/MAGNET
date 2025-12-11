/**
 * exportHelpers.ts - Export utilities for 3D models v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Client-side export helpers and format conversion.
 */

import * as THREE from 'three';
import type { ExportMetadata, LODLevel } from '../types/schema';

// =============================================================================
// TYPES
// =============================================================================

export type ExportFormat = 'gltf' | 'glb' | 'stl' | 'obj';

export interface ExportOptions {
  format: ExportFormat;
  includeStructure?: boolean;
  includeAnnotations?: boolean;
  binary?: boolean;  // For glTF: binary vs JSON
  lod?: LODLevel;
}

export interface ExportResult {
  blob: Blob;
  filename: string;
  metadata: ExportMetadata;
}

// =============================================================================
// SERVER-SIDE EXPORT
// =============================================================================

/**
 * Request export from server.
 */
export async function requestExport(
  designId: string,
  options: ExportOptions,
  baseUrl: string = '/api/v1',
): Promise<ExportResult> {
  const { format, includeStructure, includeAnnotations, lod } = options;

  // Build query params
  const params = new URLSearchParams({
    include_structure: String(includeStructure ?? true),
    include_annotations: String(includeAnnotations ?? false),
    lod: lod ?? 'medium',
  });

  const url = `${baseUrl}/designs/${designId}/3d/export/${format}?${params}`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Export failed: HTTP ${response.status}`);
  }

  // Get metadata from headers
  const metadataHeader = response.headers.get('X-Export-Metadata');
  const metadata: ExportMetadata = metadataHeader
    ? JSON.parse(metadataHeader)
    : {
      format,
      design_id: designId,
      version_id: '',
      exported_at: new Date().toISOString(),
      schema_version: '1.1.0',
      geometry_mode: 'authoritative',
      file_size: 0,
      checksum: '',
    };

  const blob = await response.blob();
  metadata.file_size = blob.size;

  // Generate filename
  const extension = format === 'gltf' && !options.binary ? 'gltf' : format;
  const filename = `${designId}_${Date.now()}.${extension}`;

  return { blob, filename, metadata };
}

/**
 * Download export file.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export and download in one step.
 */
export async function exportAndDownload(
  designId: string,
  options: ExportOptions,
  baseUrl?: string,
): Promise<ExportMetadata> {
  const result = await requestExport(designId, options, baseUrl);
  downloadBlob(result.blob, result.filename);
  return result.metadata;
}

// =============================================================================
// CLIENT-SIDE EXPORT
// =============================================================================

/**
 * Export Three.js scene to STL (client-side).
 */
export function exportToSTL(scene: THREE.Scene | THREE.Group): Blob {
  const geometries: THREE.BufferGeometry[] = [];

  // Collect all mesh geometries
  scene.traverse((object) => {
    if (object instanceof THREE.Mesh && object.geometry) {
      // Clone and apply world transform
      const cloned = object.geometry.clone();
      cloned.applyMatrix4(object.matrixWorld);
      geometries.push(cloned);
    }
  });

  if (geometries.length === 0) {
    throw new Error('No meshes found to export');
  }

  // Merge geometries
  const merged = mergeGeometries(geometries);

  // Generate STL binary
  const stlData = generateSTLBinary(merged);

  // Cleanup
  for (const geom of geometries) {
    geom.dispose();
  }
  merged.dispose();

  return new Blob([stlData], { type: 'application/octet-stream' });
}

/**
 * Export Three.js scene to OBJ (client-side).
 */
export function exportToOBJ(scene: THREE.Scene | THREE.Group): Blob {
  let vertexOffset = 1;
  let objString = '# MAGNET Export\n';
  objString += `# Exported: ${new Date().toISOString()}\n\n`;

  scene.traverse((object) => {
    if (object instanceof THREE.Mesh && object.geometry) {
      const geometry = object.geometry;
      const position = geometry.getAttribute('position');
      const normal = geometry.getAttribute('normal');
      const index = geometry.getIndex();

      objString += `# Object: ${object.name || 'mesh'}\n`;
      objString += `o ${object.name || 'mesh'}\n`;

      // Vertices
      for (let i = 0; i < position.count; i++) {
        const x = position.getX(i);
        const y = position.getY(i);
        const z = position.getZ(i);
        objString += `v ${x.toFixed(6)} ${y.toFixed(6)} ${z.toFixed(6)}\n`;
      }

      // Normals
      if (normal) {
        for (let i = 0; i < normal.count; i++) {
          const nx = normal.getX(i);
          const ny = normal.getY(i);
          const nz = normal.getZ(i);
          objString += `vn ${nx.toFixed(6)} ${ny.toFixed(6)} ${nz.toFixed(6)}\n`;
        }
      }

      // Faces
      if (index) {
        for (let i = 0; i < index.count; i += 3) {
          const a = index.getX(i) + vertexOffset;
          const b = index.getX(i + 1) + vertexOffset;
          const c = index.getX(i + 2) + vertexOffset;

          if (normal) {
            objString += `f ${a}//${a} ${b}//${b} ${c}//${c}\n`;
          } else {
            objString += `f ${a} ${b} ${c}\n`;
          }
        }
      } else {
        for (let i = 0; i < position.count; i += 3) {
          const a = i + vertexOffset;
          const b = i + 1 + vertexOffset;
          const c = i + 2 + vertexOffset;

          if (normal) {
            objString += `f ${a}//${a} ${b}//${b} ${c}//${c}\n`;
          } else {
            objString += `f ${a} ${b} ${c}\n`;
          }
        }
      }

      vertexOffset += position.count;
      objString += '\n';
    }
  });

  return new Blob([objString], { type: 'text/plain' });
}

// =============================================================================
// SCREENSHOT
// =============================================================================

/**
 * Take screenshot of renderer.
 */
export function takeScreenshot(
  renderer: THREE.WebGLRenderer,
  type: string = 'image/png',
  quality: number = 1.0,
): string {
  return renderer.domElement.toDataURL(type, quality);
}

/**
 * Download screenshot.
 */
export function downloadScreenshot(
  renderer: THREE.WebGLRenderer,
  filename: string = 'screenshot.png',
): void {
  const dataURL = takeScreenshot(renderer);
  const link = document.createElement('a');
  link.href = dataURL;
  link.download = filename;
  link.click();
}

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Merge multiple geometries into one.
 */
function mergeGeometries(geometries: THREE.BufferGeometry[]): THREE.BufferGeometry {
  // Calculate total vertex count
  let totalVertices = 0;
  for (const geom of geometries) {
    const pos = geom.getAttribute('position');
    totalVertices += pos.count;
  }

  // Create merged arrays
  const positions = new Float32Array(totalVertices * 3);
  const normals = new Float32Array(totalVertices * 3);
  const indices: number[] = [];

  let vertexOffset = 0;
  let indexOffset = 0;

  for (const geom of geometries) {
    const pos = geom.getAttribute('position');
    const norm = geom.getAttribute('normal');
    const idx = geom.getIndex();

    // Copy positions
    for (let i = 0; i < pos.count; i++) {
      positions[(vertexOffset + i) * 3] = pos.getX(i);
      positions[(vertexOffset + i) * 3 + 1] = pos.getY(i);
      positions[(vertexOffset + i) * 3 + 2] = pos.getZ(i);
    }

    // Copy normals
    if (norm) {
      for (let i = 0; i < norm.count; i++) {
        normals[(vertexOffset + i) * 3] = norm.getX(i);
        normals[(vertexOffset + i) * 3 + 1] = norm.getY(i);
        normals[(vertexOffset + i) * 3 + 2] = norm.getZ(i);
      }
    }

    // Copy indices
    if (idx) {
      for (let i = 0; i < idx.count; i++) {
        indices.push(idx.getX(i) + indexOffset);
      }
    } else {
      for (let i = 0; i < pos.count; i++) {
        indices.push(i + indexOffset);
      }
    }

    vertexOffset += pos.count;
    indexOffset = vertexOffset;
  }

  const merged = new THREE.BufferGeometry();
  merged.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  merged.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
  merged.setIndex(indices);

  return merged;
}

/**
 * Generate binary STL from geometry.
 */
function generateSTLBinary(geometry: THREE.BufferGeometry): ArrayBuffer {
  const position = geometry.getAttribute('position');
  const normal = geometry.getAttribute('normal');
  const index = geometry.getIndex();

  const triangleCount = index
    ? index.count / 3
    : position.count / 3;

  // STL format: 80 byte header + 4 byte triangle count + (50 bytes per triangle)
  const bufferSize = 84 + triangleCount * 50;
  const buffer = new ArrayBuffer(bufferSize);
  const view = new DataView(buffer);

  // Header (80 bytes)
  const header = 'MAGNET Export - Binary STL';
  for (let i = 0; i < 80; i++) {
    view.setUint8(i, i < header.length ? header.charCodeAt(i) : 0);
  }

  // Triangle count
  view.setUint32(80, triangleCount, true);

  let offset = 84;

  for (let i = 0; i < triangleCount; i++) {
    let a: number, b: number, c: number;

    if (index) {
      a = index.getX(i * 3);
      b = index.getX(i * 3 + 1);
      c = index.getX(i * 3 + 2);
    } else {
      a = i * 3;
      b = i * 3 + 1;
      c = i * 3 + 2;
    }

    // Normal (use first vertex normal or compute)
    let nx = 0, ny = 0, nz = 1;
    if (normal) {
      nx = normal.getX(a);
      ny = normal.getY(a);
      nz = normal.getZ(a);
    }

    view.setFloat32(offset, nx, true); offset += 4;
    view.setFloat32(offset, ny, true); offset += 4;
    view.setFloat32(offset, nz, true); offset += 4;

    // Vertex 1
    view.setFloat32(offset, position.getX(a), true); offset += 4;
    view.setFloat32(offset, position.getY(a), true); offset += 4;
    view.setFloat32(offset, position.getZ(a), true); offset += 4;

    // Vertex 2
    view.setFloat32(offset, position.getX(b), true); offset += 4;
    view.setFloat32(offset, position.getY(b), true); offset += 4;
    view.setFloat32(offset, position.getZ(b), true); offset += 4;

    // Vertex 3
    view.setFloat32(offset, position.getX(c), true); offset += 4;
    view.setFloat32(offset, position.getY(c), true); offset += 4;
    view.setFloat32(offset, position.getZ(c), true); offset += 4;

    // Attribute byte count (unused)
    view.setUint16(offset, 0, true); offset += 2;
  }

  return buffer;
}
