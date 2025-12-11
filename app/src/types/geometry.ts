/**
 * MAGNET UI Geometry Types
 *
 * Type definitions for geometry and viewport state.
 * Split from sceneStore per FM7 architectural fix.
 */

import type { UISchemaVersion } from './schema-version';
import type { Point3D, BoundingBox3D } from './common';
import { UI_SCHEMA_VERSION } from './schema-version';

// ============================================================================
// Geometry Types (Authoritative - synced from backend)
// ============================================================================

/**
 * Mesh LOD levels
 */
export type LODLevel = 'high' | 'medium' | 'low' | 'proxy';

/**
 * Mesh visibility state
 */
export type MeshVisibility = 'visible' | 'hidden' | 'wireframe' | 'transparent';

/**
 * Individual mesh data
 */
export interface MeshData {
  id: string;
  name: string;
  parentId?: string;

  // Geometry reference (not actual data - that's in Three.js)
  geometryHash: string;
  lodLevel: LODLevel;

  // Transform
  position: Point3D;
  rotation: Point3D;  // Euler angles in radians
  scale: Point3D;

  // Bounds
  boundingBox: BoundingBox3D;

  // State
  visibility: MeshVisibility;
  selectable: boolean;

  // Metadata
  componentType?: string;
  componentId?: string;
  materialId?: string;
}

/**
 * Geometry store read-only state (from backend)
 */
export interface GeometryReadOnlyState {
  schema_version: UISchemaVersion;

  /** All meshes by ID */
  meshes: Record<string, MeshData>;

  /** Root mesh IDs (no parent) */
  rootMeshIds: string[];

  /** Global bounding box of all geometry */
  sceneBounds: BoundingBox3D | null;

  /** Current geometry hash for change detection */
  geometryHash: string;

  /** Last sync timestamp */
  lastSyncTimestamp: number;
}

/**
 * Geometry store read-write state (UI selections/highlights)
 */
export interface GeometryReadWriteState {
  /** Currently selected mesh IDs */
  selectedMeshIds: string[];

  /** Currently highlighted mesh ID (hover) */
  highlightedMeshId: string | null;

  /** Mesh IDs marked for emphasis (from ARS, etc.) */
  emphasizedMeshIds: string[];

  /** Custom visibility overrides */
  visibilityOverrides: Record<string, MeshVisibility>;

  /** Loading state for async geometry */
  isLoading: boolean;
  loadingProgress: number; // 0-100
}

/**
 * Combined geometry state
 */
export interface GeometryState extends GeometryReadOnlyState, GeometryReadWriteState {}

// ============================================================================
// Viewport Types (UI-only - camera, parallax, focus)
// ============================================================================

/**
 * Camera projection type
 */
export type CameraProjection = 'perspective' | 'orthographic';

/**
 * Camera state
 */
export interface CameraState {
  position: Point3D;
  target: Point3D;      // Look-at point
  up: Point3D;          // Up vector (usually [0, 1, 0])
  fov: number;          // Field of view in degrees
  near: number;         // Near clipping plane
  far: number;          // Far clipping plane
  projection: CameraProjection;
  zoom: number;         // For orthographic
}

/**
 * Camera animation target
 */
export interface CameraAnimationTarget {
  position?: Point3D;
  target?: Point3D;
  fov?: number;
  duration: number;
  easing?: 'linear' | 'ease-out' | 'spring';
}

/**
 * Parallax effect state
 */
export interface ParallaxState {
  enabled: boolean;
  intensity: number;     // 0-1 multiplier
  maxOffset: Point3D;    // Maximum offset in each axis
  currentOffset: Point3D;
}

/**
 * Focus/blur effect state
 */
export interface FocusBlurState {
  enabled: boolean;
  focusedMeshId: string | null;
  blurAmount: number;    // pixels
  transitionDuration: number; // ms
}

/**
 * Viewport store state
 */
export interface ViewportState {
  // Camera
  camera: CameraState;
  cameraAnimating: boolean;
  cameraAnimationTarget: CameraAnimationTarget | null;

  // Parallax
  parallax: ParallaxState;

  // Focus blur
  focusBlur: FocusBlurState;

  // Pointer tracking
  pointerPosition: { x: number; y: number } | null;
  isDragging: boolean;

  // Viewport
  width: number;
  height: number;
  devicePixelRatio: number;

  // Render quality
  renderQuality: 'high' | 'medium' | 'low';
  antialias: boolean;
}

// ============================================================================
// Default States
// ============================================================================

export const DEFAULT_CAMERA_STATE: CameraState = {
  position: { x: 0, y: 5, z: 10 },
  target: { x: 0, y: 0, z: 0 },
  up: { x: 0, y: 1, z: 0 },
  fov: 50,
  near: 0.1,
  far: 1000,
  projection: 'perspective',
  zoom: 1,
};

export const DEFAULT_PARALLAX_STATE: ParallaxState = {
  enabled: true,
  intensity: 0.5,
  maxOffset: { x: 4, y: 4, z: 10 },
  currentOffset: { x: 0, y: 0, z: 0 },
};

export const DEFAULT_FOCUS_BLUR_STATE: FocusBlurState = {
  enabled: true,
  focusedMeshId: null,
  blurAmount: 5,
  transitionDuration: 400,
};

export const INITIAL_GEOMETRY_STATE: GeometryState = {
  schema_version: UI_SCHEMA_VERSION,
  meshes: {},
  rootMeshIds: [],
  sceneBounds: null,
  geometryHash: '',
  lastSyncTimestamp: 0,
  selectedMeshIds: [],
  highlightedMeshId: null,
  emphasizedMeshIds: [],
  visibilityOverrides: {},
  isLoading: false,
  loadingProgress: 0,
};

export const INITIAL_VIEWPORT_STATE: ViewportState = {
  camera: DEFAULT_CAMERA_STATE,
  cameraAnimating: false,
  cameraAnimationTarget: null,
  parallax: DEFAULT_PARALLAX_STATE,
  focusBlur: DEFAULT_FOCUS_BLUR_STATE,
  pointerPosition: null,
  isDragging: false,
  width: 0,
  height: 0,
  devicePixelRatio: 1,
  renderQuality: 'high',
  antialias: true,
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Calculate center of bounding box
 */
export function getBoundingBoxCenter(box: BoundingBox3D): Point3D {
  return {
    x: (box.min.x + box.max.x) / 2,
    y: (box.min.y + box.max.y) / 2,
    z: (box.min.z + box.max.z) / 2,
  };
}

/**
 * Calculate size of bounding box
 */
export function getBoundingBoxSize(box: BoundingBox3D): Point3D {
  return {
    x: box.max.x - box.min.x,
    y: box.max.y - box.min.y,
    z: box.max.z - box.min.z,
  };
}

/**
 * Calculate optimal camera position to frame bounding box
 */
export function calculateFramingCamera(
  box: BoundingBox3D,
  fov: number = 50,
  padding: number = 1.2
): Partial<CameraState> {
  const center = getBoundingBoxCenter(box);
  const size = getBoundingBoxSize(box);
  const maxDim = Math.max(size.x, size.y, size.z);

  // Calculate distance needed to frame the object
  const fovRad = (fov * Math.PI) / 180;
  const distance = (maxDim / 2 / Math.tan(fovRad / 2)) * padding;

  return {
    position: {
      x: center.x,
      y: center.y + distance * 0.3,
      z: center.z + distance,
    },
    target: center,
  };
}

// ============================================================================
// WebGL Buffer Types (V1.4 Integration)
// ============================================================================

/**
 * WebGL buffer data type
 */
export type WebGLBufferType = 'float32' | 'uint16' | 'uint32' | 'int16' | 'int32';

/**
 * WebGL buffer attribute
 */
export interface WebGLBufferAttribute {
  /** Attribute name (e.g., 'position', 'normal', 'uv') */
  name: string;
  /** Number of components per vertex (e.g., 3 for xyz) */
  size: number;
  /** Data type */
  type: WebGLBufferType;
  /** Whether values are normalized */
  normalized?: boolean;
  /** Byte offset in interleaved buffer */
  offset?: number;
  /** Byte stride between consecutive values */
  stride?: number;
}

/**
 * WebGL buffer descriptor
 */
export interface WebGLBufferDescriptor {
  /** Unique buffer identifier */
  id: string;
  /** Buffer usage hint */
  usage: 'static' | 'dynamic' | 'stream';
  /** Total byte length */
  byteLength: number;
  /** Buffer attributes (for vertex buffers) */
  attributes?: WebGLBufferAttribute[];
  /** Whether this is an index buffer */
  isIndexBuffer?: boolean;
  /** Index type for index buffers */
  indexType?: 'uint16' | 'uint32';
}

/**
 * Geometry update payload from WebSocket
 */
export interface GeometryUpdatePayload {
  /** Update type */
  updateType: 'full' | 'incremental' | 'lod_switch';
  /** Mesh IDs affected by this update */
  affectedMeshIds: string[];
  /** Buffer descriptors for new/updated buffers */
  buffers: WebGLBufferDescriptor[];
  /** Base64-encoded buffer data (when inline) */
  bufferData?: Record<string, string>;
  /** URLs for buffer data (when external) */
  bufferUrls?: Record<string, string>;
  /** New geometry hash after update */
  geometryHash: string;
  /** Timestamp of update */
  timestamp: number;
}

/**
 * Incremental mesh update
 */
export interface MeshIncrementalUpdate {
  /** Mesh ID to update */
  meshId: string;
  /** Transform updates */
  transform?: {
    position?: Point3D;
    rotation?: Point3D;
    scale?: Point3D;
  };
  /** Visibility update */
  visibility?: MeshVisibility;
  /** Material update */
  materialId?: string;
  /** LOD level change */
  lodLevel?: LODLevel;
}

/**
 * Geometry stream message types
 */
export type GeometryStreamMessageType =
  | 'geometry:full_update'
  | 'geometry:incremental'
  | 'geometry:lod_switch'
  | 'geometry:buffer_ready'
  | 'geometry:error';

/**
 * Geometry stream message
 */
export interface GeometryStreamMessage {
  /** Message type */
  type: GeometryStreamMessageType;
  /** Message payload */
  payload: GeometryUpdatePayload | MeshIncrementalUpdate | GeometryStreamError;
  /** Chain tracking */
  update_id: string;
  prev_update_id: string | null;
}

/**
 * Geometry stream error
 */
export interface GeometryStreamError {
  code: string;
  message: string;
  meshId?: string;
  recoverable: boolean;
}
