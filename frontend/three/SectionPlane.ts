/**
 * SectionPlane.ts - Section cut plane visualization v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Creates clipping planes for section cuts (transverse, longitudinal, waterplane).
 */

import * as THREE from 'three';

// =============================================================================
// TYPES
// =============================================================================

export type SectionPlaneType = 'transverse' | 'longitudinal' | 'waterplane';

export interface SectionPlaneConfig {
  plane: SectionPlaneType;
  position: number;  // 0.0 - 1.0 normalized position
  bounds: {
    min: [number, number, number];
    max: [number, number, number];
  };
  draft?: number;    // For waterplane calculations
}

// =============================================================================
// CLIPPING PLANE CREATION
// =============================================================================

/**
 * Create a Three.js clipping plane from section config.
 */
export function createClippingPlane(config: SectionPlaneConfig): THREE.Plane {
  const { plane, position, bounds, draft = 0 } = config;

  const loa = bounds.max[0] - bounds.min[0];
  const beam = bounds.max[1] - bounds.min[1];
  const depth = bounds.max[2] - bounds.min[2];

  switch (plane) {
    case 'transverse': {
      // X-axis clipping (stations along length)
      const x = bounds.min[0] + position * loa;
      return new THREE.Plane(new THREE.Vector3(1, 0, 0), -x);
    }

    case 'longitudinal': {
      // Y-axis clipping (centerline to side)
      const y = position * beam / 2;
      return new THREE.Plane(new THREE.Vector3(0, 1, 0), -y);
    }

    case 'waterplane': {
      // Z-axis clipping (waterlines)
      // Position 0 = keel, position 1 = deck
      const z = bounds.min[2] + position * depth;
      return new THREE.Plane(new THREE.Vector3(0, 0, 1), -z);
    }

    default:
      // Default to transverse at midship
      const midX = (bounds.min[0] + bounds.max[0]) / 2;
      return new THREE.Plane(new THREE.Vector3(1, 0, 0), -midX);
  }
}

/**
 * Create section plane helper visualization.
 */
export function createSectionPlaneHelper(
  config: SectionPlaneConfig,
  color: number = 0x00ff00,
  opacity: number = 0.2,
): THREE.Mesh {
  const { plane, position, bounds } = config;

  const loa = bounds.max[0] - bounds.min[0];
  const beam = bounds.max[1] - bounds.min[1];
  const depth = bounds.max[2] - bounds.min[2];

  let geometry: THREE.PlaneGeometry;
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    side: THREE.DoubleSide,
  });

  const mesh = new THREE.Mesh();

  switch (plane) {
    case 'transverse': {
      // YZ plane (showing beam x depth)
      geometry = new THREE.PlaneGeometry(beam * 1.2, depth * 1.2);
      mesh.geometry = geometry;
      mesh.material = material;
      mesh.rotation.y = Math.PI / 2;
      mesh.position.set(
        bounds.min[0] + position * loa,
        (bounds.min[1] + bounds.max[1]) / 2,
        (bounds.min[2] + bounds.max[2]) / 2,
      );
      break;
    }

    case 'longitudinal': {
      // XZ plane (showing length x depth)
      geometry = new THREE.PlaneGeometry(loa * 1.2, depth * 1.2);
      mesh.geometry = geometry;
      mesh.material = material;
      mesh.rotation.x = Math.PI / 2;
      mesh.rotation.z = Math.PI / 2;
      mesh.position.set(
        (bounds.min[0] + bounds.max[0]) / 2,
        position * beam / 2,
        (bounds.min[2] + bounds.max[2]) / 2,
      );
      break;
    }

    case 'waterplane': {
      // XY plane (showing length x beam)
      geometry = new THREE.PlaneGeometry(loa * 1.2, beam * 1.2);
      mesh.geometry = geometry;
      mesh.material = material;
      mesh.rotation.x = -Math.PI / 2;
      mesh.position.set(
        (bounds.min[0] + bounds.max[0]) / 2,
        (bounds.min[1] + bounds.max[1]) / 2,
        bounds.min[2] + position * depth,
      );
      break;
    }
  }

  mesh.name = `section_plane_${plane}`;
  mesh.userData.sectionPlane = plane;
  mesh.userData.sectionPosition = position;

  return mesh;
}

// =============================================================================
// SECTION CUT VISUALIZATION
// =============================================================================

/**
 * Create stencil materials for section cut rendering.
 */
export function createSectionCutMaterials(): {
  front: THREE.MeshBasicMaterial;
  back: THREE.MeshBasicMaterial;
  cap: THREE.MeshBasicMaterial;
} {
  // Front faces (stencil write)
  const front = new THREE.MeshBasicMaterial({
    colorWrite: false,
    depthWrite: false,
    stencilWrite: true,
    stencilRef: 1,
    stencilFunc: THREE.AlwaysStencilFunc,
    stencilFail: THREE.KeepStencilOp,
    stencilZFail: THREE.IncrementWrapStencilOp,
    stencilZPass: THREE.KeepStencilOp,
    side: THREE.FrontSide,
  });

  // Back faces (stencil write)
  const back = new THREE.MeshBasicMaterial({
    colorWrite: false,
    depthWrite: false,
    stencilWrite: true,
    stencilRef: 1,
    stencilFunc: THREE.AlwaysStencilFunc,
    stencilFail: THREE.KeepStencilOp,
    stencilZFail: THREE.DecrementWrapStencilOp,
    stencilZPass: THREE.KeepStencilOp,
    side: THREE.BackSide,
  });

  // Cap (fill the cut area)
  const cap = new THREE.MeshBasicMaterial({
    color: 0xff8800,
    stencilWrite: false,
    stencilRef: 1,
    stencilFunc: THREE.NotEqualStencilFunc,
    side: THREE.DoubleSide,
  });

  return { front, back, cap };
}

// =============================================================================
// SECTION CURVE EXTRACTION
// =============================================================================

export interface SectionCurve {
  points: [number, number, number][];
  plane: SectionPlaneType;
  position: number;
  closed: boolean;
}

/**
 * Create line from section curve data.
 */
export function createSectionCurveLine(
  curve: SectionCurve,
  color: number = 0xffff00,
): THREE.Line {
  const points = curve.points.map((p) => new THREE.Vector3(p[0], p[1], p[2]));

  if (curve.closed && points.length > 1) {
    points.push(points[0].clone());
  }

  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({
    color,
    linewidth: 2,
  });

  const line = new THREE.Line(geometry, material);
  line.name = `section_curve_${curve.plane}_${curve.position.toFixed(2)}`;

  return line;
}

/**
 * Create section curve group.
 */
export function createSectionCurveGroup(
  curves: SectionCurve[],
  color: number = 0xffff00,
): THREE.Group {
  const group = new THREE.Group();
  group.name = 'section_curves';

  for (const curve of curves) {
    const line = createSectionCurveLine(curve, color);
    group.add(line);
  }

  return group;
}

// =============================================================================
// INTERACTIVE SECTION PLANE
// =============================================================================

/**
 * Create interactive section plane with drag handles.
 */
export function createInteractiveSectionPlane(
  config: SectionPlaneConfig,
  planeColor: number = 0x00ff00,
  handleColor: number = 0xffffff,
): THREE.Group {
  const group = new THREE.Group();
  group.name = 'interactive_section_plane';

  // Create plane helper
  const planeHelper = createSectionPlaneHelper(config, planeColor, 0.3);
  group.add(planeHelper);

  // Create edge outline
  const edgeGeometry = new THREE.EdgesGeometry(planeHelper.geometry);
  const edgeMaterial = new THREE.LineBasicMaterial({ color: planeColor });
  const edges = new THREE.LineSegments(edgeGeometry, edgeMaterial);
  edges.position.copy(planeHelper.position);
  edges.rotation.copy(planeHelper.rotation);
  group.add(edges);

  // Create drag handle (sphere at center)
  const handleGeometry = new THREE.SphereGeometry(0.3, 16, 16);
  const handleMaterial = new THREE.MeshBasicMaterial({
    color: handleColor,
  });
  const handle = new THREE.Mesh(handleGeometry, handleMaterial);
  handle.position.copy(planeHelper.position);
  handle.name = 'section_handle';
  handle.userData.isDraggable = true;
  group.add(handle);

  // Store config
  group.userData.sectionConfig = config;

  return group;
}

/**
 * Update section plane position.
 */
export function updateSectionPlanePosition(
  group: THREE.Group,
  position: number,
): THREE.Plane {
  const config = group.userData.sectionConfig as SectionPlaneConfig;
  config.position = Math.max(0, Math.min(1, position));

  // Get new clipping plane
  const clippingPlane = createClippingPlane(config);

  // Update visual helper
  const helper = group.getObjectByName(`section_plane_${config.plane}`);
  if (helper) {
    const newHelper = createSectionPlaneHelper(config);
    helper.position.copy(newHelper.position);
    newHelper.geometry.dispose();
  }

  // Update handle position
  const handle = group.getObjectByName('section_handle');
  if (handle && helper) {
    handle.position.copy(helper.position);
  }

  return clippingPlane;
}
