/**
 * StructureMesh.ts - Structural visualization mesh creation v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Creates Three.js meshes for structural elements (frames, stringers, keel).
 */

import * as THREE from 'three';
import type { MeshData, StructureSceneData } from '../types/schema';
import { createBufferGeometry } from './HullMesh';

// =============================================================================
// COLORS
// =============================================================================

const STRUCTURE_COLORS = {
  frame: 0x4a90d9,     // Blue
  stringer: 0x7cb342,  // Green
  keel: 0xf57c00,      // Orange
  girder: 0x9c27b0,    // Purple
  plating: 0x78909c,   // Blue-grey
};

// =============================================================================
// MESH CREATION
// =============================================================================

/**
 * Create structure mesh from MeshData.
 */
function createStructureElement(
  meshData: MeshData,
  color: number,
  name: string,
): THREE.Mesh {
  const geometry = createBufferGeometry(meshData);

  const material = new THREE.MeshStandardMaterial({
    color,
    metalness: 0.8,
    roughness: 0.5,
    side: THREE.DoubleSide,
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.userData.meshId = meshData.mesh_id;
  mesh.userData.meshType = 'structure';

  return mesh;
}

/**
 * Create structure mesh group from StructureSceneData.
 */
export function createStructureMesh(structure: StructureSceneData): THREE.Group {
  const group = new THREE.Group();
  group.name = 'structure_group';

  // Frames
  const framesGroup = new THREE.Group();
  framesGroup.name = 'frames';
  structure.frames.forEach((frame, index) => {
    const mesh = createStructureElement(
      frame,
      STRUCTURE_COLORS.frame,
      `frame_${index}`,
    );
    mesh.userData.structureType = 'frame';
    mesh.userData.structureIndex = index;
    framesGroup.add(mesh);
  });
  group.add(framesGroup);

  // Stringers
  const stringersGroup = new THREE.Group();
  stringersGroup.name = 'stringers';
  structure.stringers.forEach((stringer, index) => {
    const mesh = createStructureElement(
      stringer,
      STRUCTURE_COLORS.stringer,
      `stringer_${index}`,
    );
    mesh.userData.structureType = 'stringer';
    mesh.userData.structureIndex = index;
    stringersGroup.add(mesh);
  });
  group.add(stringersGroup);

  // Keel
  if (structure.keel) {
    const keelMesh = createStructureElement(
      structure.keel,
      STRUCTURE_COLORS.keel,
      'keel',
    );
    keelMesh.userData.structureType = 'keel';
    group.add(keelMesh);
  }

  // Girders
  const girdersGroup = new THREE.Group();
  girdersGroup.name = 'girders';
  structure.girders.forEach((girder, index) => {
    const mesh = createStructureElement(
      girder,
      STRUCTURE_COLORS.girder,
      `girder_${index}`,
    );
    mesh.userData.structureType = 'girder';
    mesh.userData.structureIndex = index;
    girdersGroup.add(mesh);
  });
  group.add(girdersGroup);

  // Plating
  const platingGroup = new THREE.Group();
  platingGroup.name = 'plating';
  structure.plating.forEach((plate, index) => {
    const mesh = createStructureElement(
      plate,
      STRUCTURE_COLORS.plating,
      `plate_${index}`,
    );
    mesh.userData.structureType = 'plating';
    mesh.userData.structureIndex = index;
    platingGroup.add(mesh);
  });
  group.add(platingGroup);

  return group;
}

/**
 * Set visibility of structure elements by type.
 */
export function setStructureVisibility(
  group: THREE.Group,
  type: 'frames' | 'stringers' | 'keel' | 'girders' | 'plating' | 'all',
  visible: boolean,
): void {
  if (type === 'all') {
    group.visible = visible;
    return;
  }

  // Find child group by name
  const childGroup = type === 'keel'
    ? group.getObjectByName('keel')
    : group.getObjectByName(type);

  if (childGroup) {
    childGroup.visible = visible;
  }
}

/**
 * Highlight specific structure element.
 */
export function highlightStructureElement(
  group: THREE.Group,
  meshId: string,
  highlight: boolean,
): void {
  group.traverse((child) => {
    if (
      child instanceof THREE.Mesh &&
      child.userData.meshId === meshId &&
      child.material instanceof THREE.MeshStandardMaterial
    ) {
      if (highlight) {
        child.material.emissive.setHex(0x0044ff);
        child.material.emissiveIntensity = 0.3;
      } else {
        child.material.emissive.setHex(0x000000);
        child.material.emissiveIntensity = 0;
      }
    }
  });
}

/**
 * Set structure opacity.
 */
export function setStructureOpacity(group: THREE.Group, opacity: number): void {
  group.traverse((child) => {
    if (child instanceof THREE.Mesh && child.material instanceof THREE.MeshStandardMaterial) {
      child.material.opacity = opacity;
      child.material.transparent = opacity < 1;
      child.material.needsUpdate = true;
    }
  });
}

/**
 * Set structure color by type.
 */
export function setStructureColor(
  group: THREE.Group,
  type: keyof typeof STRUCTURE_COLORS,
  color: number,
): void {
  group.traverse((child) => {
    if (
      child instanceof THREE.Mesh &&
      child.userData.structureType === type &&
      child.material instanceof THREE.MeshStandardMaterial
    ) {
      child.material.color.setHex(color);
    }
  });
}

/**
 * Dispose structure mesh group.
 */
export function disposeStructureMesh(group: THREE.Group): void {
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
// FRAME VISUALIZATION
// =============================================================================

/**
 * Create frame wireframe from dimensions.
 */
export function createFrameWireframe(
  position: number,
  height: number,
  width: number,
  color: number = STRUCTURE_COLORS.frame,
): THREE.Line {
  const points = [
    new THREE.Vector3(position, -width / 2, 0),
    new THREE.Vector3(position, -width / 2, height),
    new THREE.Vector3(position, width / 2, height),
    new THREE.Vector3(position, width / 2, 0),
    new THREE.Vector3(position, -width / 2, 0),
  ];

  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ color, linewidth: 2 });

  return new THREE.Line(geometry, material);
}

/**
 * Create stringer line.
 */
export function createStringerLine(
  startX: number,
  endX: number,
  y: number,
  z: number,
  color: number = STRUCTURE_COLORS.stringer,
): THREE.Line {
  const points = [
    new THREE.Vector3(startX, y, z),
    new THREE.Vector3(endX, y, z),
  ];

  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({ color, linewidth: 2 });

  return new THREE.Line(geometry, material);
}
