/**
 * HullMesh.ts - Hull geometry mesh creation v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Creates Three.js mesh from MeshData schema.
 */

import * as THREE from 'three';
import type { MeshData, SceneData, MaterialDef } from '../types/schema';
import { MaterialLibrary } from './MaterialLibrary';

// =============================================================================
// TYPES
// =============================================================================

export interface HullMeshOptions {
  castShadow?: boolean;
  receiveShadow?: boolean;
  transparent?: boolean;
  opacity?: number;
}

const DEFAULT_OPTIONS: HullMeshOptions = {
  castShadow: true,
  receiveShadow: true,
  transparent: false,
  opacity: 1.0,
};

// =============================================================================
// MESH CREATION
// =============================================================================

/**
 * Create BufferGeometry from MeshData.
 */
export function createBufferGeometry(meshData: MeshData): THREE.BufferGeometry {
  const geometry = new THREE.BufferGeometry();

  // Convert flat arrays to Float32Array
  const vertices = new Float32Array(meshData.vertices);
  const normals = new Float32Array(meshData.normals);
  const indices = new Uint32Array(meshData.indices);

  // Set attributes
  geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));

  // Optional UVs
  if (meshData.uvs && meshData.uvs.length > 0) {
    const uvs = new Float32Array(meshData.uvs);
    geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  }

  // Optional vertex colors
  if (meshData.colors && meshData.colors.length > 0) {
    const colors = new Float32Array(meshData.colors);
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 4));
  }

  // Compute bounding box/sphere
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();

  return geometry;
}

/**
 * Create Three.js mesh from MeshData.
 */
export function createMesh(
  meshData: MeshData,
  material: THREE.Material,
  options: HullMeshOptions = {},
): THREE.Mesh {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const geometry = createBufferGeometry(meshData);
  const mesh = new THREE.Mesh(geometry, material);

  mesh.castShadow = opts.castShadow ?? false;
  mesh.receiveShadow = opts.receiveShadow ?? false;
  mesh.name = meshData.mesh_id || 'hull_mesh';

  // Store mesh ID in userData
  mesh.userData.meshId = meshData.mesh_id;
  mesh.userData.meshType = 'hull';

  return mesh;
}

/**
 * Create hull mesh group from SceneData.
 */
export function createHullMesh(
  sceneData: SceneData,
  materialLib: MaterialLibrary,
): THREE.Group {
  const group = new THREE.Group();
  group.name = 'hull_group';

  // Main hull
  if (sceneData.hull) {
    const hullMaterial = materialLib.get('hull') || materialLib.getDefaultHullMaterial();
    const hullMesh = createMesh(sceneData.hull, hullMaterial, {
      castShadow: true,
      receiveShadow: true,
    });
    hullMesh.name = 'hull';
    group.add(hullMesh);
  }

  // Deck
  if (sceneData.deck) {
    const deckMaterial = materialLib.get('deck') || materialLib.getDefaultDeckMaterial();
    const deckMesh = createMesh(sceneData.deck, deckMaterial);
    deckMesh.name = 'deck';
    deckMesh.userData.meshType = 'deck';
    group.add(deckMesh);
  }

  // Transom
  if (sceneData.transom) {
    const transomMaterial = materialLib.get('transom') || materialLib.getDefaultHullMaterial();
    const transomMesh = createMesh(sceneData.transom, transomMaterial);
    transomMesh.name = 'transom';
    transomMesh.userData.meshType = 'transom';
    group.add(transomMesh);
  }

  return group;
}

/**
 * Update existing hull mesh with new geometry.
 */
export function updateHullMesh(
  group: THREE.Group,
  sceneData: SceneData,
): void {
  // Update hull geometry
  if (sceneData.hull) {
    const hullMesh = group.getObjectByName('hull') as THREE.Mesh | undefined;
    if (hullMesh) {
      const oldGeometry = hullMesh.geometry;
      hullMesh.geometry = createBufferGeometry(sceneData.hull);
      oldGeometry.dispose();
    }
  }

  // Update deck geometry
  if (sceneData.deck) {
    const deckMesh = group.getObjectByName('deck') as THREE.Mesh | undefined;
    if (deckMesh) {
      const oldGeometry = deckMesh.geometry;
      deckMesh.geometry = createBufferGeometry(sceneData.deck);
      oldGeometry.dispose();
    }
  }

  // Update transom geometry
  if (sceneData.transom) {
    const transomMesh = group.getObjectByName('transom') as THREE.Mesh | undefined;
    if (transomMesh) {
      const oldGeometry = transomMesh.geometry;
      transomMesh.geometry = createBufferGeometry(sceneData.transom);
      oldGeometry.dispose();
    }
  }
}

/**
 * Set view mode for hull mesh group.
 */
export function setHullViewMode(
  group: THREE.Group,
  mode: 'solid' | 'wireframe' | 'transparent' | 'xray',
): void {
  group.traverse((child) => {
    if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
      const material = child.material;

      switch (mode) {
        case 'wireframe':
          material.wireframe = true;
          material.opacity = 1.0;
          material.transparent = false;
          material.side = THREE.FrontSide;
          break;
        case 'transparent':
          material.wireframe = false;
          material.opacity = 0.6;
          material.transparent = true;
          material.side = THREE.FrontSide;
          break;
        case 'xray':
          material.wireframe = false;
          material.opacity = 0.3;
          material.transparent = true;
          material.side = THREE.DoubleSide;
          break;
        default: // solid
          material.wireframe = false;
          material.opacity = 1.0;
          material.transparent = false;
          material.side = THREE.FrontSide;
      }

      material.needsUpdate = true;
    }
  });
}

/**
 * Dispose hull mesh group and all resources.
 */
export function disposeHullMesh(group: THREE.Group): void {
  group.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry?.dispose();
      if (child.material instanceof THREE.Material) {
        child.material.dispose();
      } else if (Array.isArray(child.material)) {
        child.material.forEach((m) => m.dispose());
      }
    }
  });
}

// =============================================================================
// WATERLINE CREATION
// =============================================================================

/**
 * Create waterline visualization.
 */
export function createWaterline(
  points: [number, number, number][],
  color: number = 0x0088ff,
  closed: boolean = true,
): THREE.Line {
  const geometry = new THREE.BufferGeometry();

  // Create points array
  const vertices: number[] = [];
  for (const point of points) {
    vertices.push(point[0], point[1], point[2]);
  }

  // Close the loop if needed
  if (closed && points.length > 0) {
    vertices.push(points[0][0], points[0][1], points[0][2]);
  }

  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));

  const material = new THREE.LineBasicMaterial({
    color,
    linewidth: 2,
  });

  const line = new THREE.Line(geometry, material);
  line.name = 'waterline';

  return line;
}

/**
 * Create waterplane surface.
 */
export function createWaterplaneSurface(
  bounds: { min: [number, number, number]; max: [number, number, number] },
  waterlineZ: number,
  color: number = 0x0088ff,
  opacity: number = 0.3,
): THREE.Mesh {
  const width = bounds.max[0] - bounds.min[0];
  const depth = bounds.max[1] - bounds.min[1];

  const geometry = new THREE.PlaneGeometry(width * 1.2, depth * 1.2);
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    side: THREE.DoubleSide,
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.set(
    (bounds.min[0] + bounds.max[0]) / 2,
    (bounds.min[1] + bounds.max[1]) / 2,
    waterlineZ,
  );
  mesh.name = 'waterplane';

  return mesh;
}
