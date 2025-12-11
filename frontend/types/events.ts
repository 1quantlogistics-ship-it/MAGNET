/**
 * events.ts - Event type definitions for WebGL visualization v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Defines event types for geometry updates and user interactions.
 */

import type {
  SceneData,
  MeshData,
  GeometryMode,
  Annotation3D,
  Measurement3D,
} from './schema';

// =============================================================================
// GEOMETRY EVENTS
// =============================================================================

export interface GeometryLoadedEvent {
  type: 'geometry_loaded';
  designId: string;
  sceneData: SceneData;
  geometryMode: GeometryMode;
  timestamp: Date;
}

export interface GeometryUpdatedEvent {
  type: 'geometry_updated';
  designId: string;
  updateId: string;
  isFullUpdate: boolean;
  hull?: MeshData | null;
  deck?: MeshData | null;
  timestamp: Date;
}

export interface GeometryInvalidatedEvent {
  type: 'geometry_invalidated';
  designId: string;
  reason: string;
  components: string[];
  timestamp: Date;
}

export interface GeometryErrorEvent {
  type: 'geometry_error';
  designId: string;
  errorCode: string;
  errorMessage: string;
  recoveryHint?: string;
  timestamp: Date;
}

export type GeometryEvent =
  | GeometryLoadedEvent
  | GeometryUpdatedEvent
  | GeometryInvalidatedEvent
  | GeometryErrorEvent;

// =============================================================================
// VIEW EVENTS
// =============================================================================

export type ViewMode = 'solid' | 'wireframe' | 'transparent' | 'xray';

export interface ViewModeChangedEvent {
  type: 'view_mode_changed';
  mode: ViewMode;
  timestamp: Date;
}

export interface CameraChangedEvent {
  type: 'camera_changed';
  position: [number, number, number];
  target: [number, number, number];
  zoom: number;
  timestamp: Date;
}

export type CameraPreset =
  | 'perspective'
  | 'bow'
  | 'stern'
  | 'starboard'
  | 'port'
  | 'top'
  | 'bottom';

export interface CameraPresetEvent {
  type: 'camera_preset';
  preset: CameraPreset;
  timestamp: Date;
}

export type ViewEvent =
  | ViewModeChangedEvent
  | CameraChangedEvent
  | CameraPresetEvent;

// =============================================================================
// SECTION CUT EVENTS
// =============================================================================

export type SectionPlane = 'transverse' | 'longitudinal' | 'waterplane';

export interface SectionCutEnabledEvent {
  type: 'section_cut_enabled';
  plane: SectionPlane;
  position: number;
  timestamp: Date;
}

export interface SectionCutDisabledEvent {
  type: 'section_cut_disabled';
  timestamp: Date;
}

export interface SectionCutMovedEvent {
  type: 'section_cut_moved';
  plane: SectionPlane;
  position: number;
  timestamp: Date;
}

export type SectionCutEvent =
  | SectionCutEnabledEvent
  | SectionCutDisabledEvent
  | SectionCutMovedEvent;

// =============================================================================
// MEASUREMENT EVENTS
// =============================================================================

export interface MeasurementStartedEvent {
  type: 'measurement_started';
  measurementType: 'distance' | 'angle' | 'area';
  timestamp: Date;
}

export interface MeasurementPointAddedEvent {
  type: 'measurement_point_added';
  point: [number, number, number];
  pointIndex: number;
  timestamp: Date;
}

export interface MeasurementCompletedEvent {
  type: 'measurement_completed';
  measurement: Measurement3D;
  timestamp: Date;
}

export interface MeasurementCancelledEvent {
  type: 'measurement_cancelled';
  timestamp: Date;
}

export type MeasurementEvent =
  | MeasurementStartedEvent
  | MeasurementPointAddedEvent
  | MeasurementCompletedEvent
  | MeasurementCancelledEvent;

// =============================================================================
// ANNOTATION EVENTS
// =============================================================================

export interface AnnotationCreatedEvent {
  type: 'annotation_created';
  annotation: Annotation3D;
  timestamp: Date;
}

export interface AnnotationUpdatedEvent {
  type: 'annotation_updated';
  annotation: Annotation3D;
  timestamp: Date;
}

export interface AnnotationDeletedEvent {
  type: 'annotation_deleted';
  annotationId: string;
  designId: string;
  timestamp: Date;
}

export interface AnnotationSelectedEvent {
  type: 'annotation_selected';
  annotationId: string;
  timestamp: Date;
}

export interface AnnotationDeselectedEvent {
  type: 'annotation_deselected';
  timestamp: Date;
}

export type AnnotationEvent =
  | AnnotationCreatedEvent
  | AnnotationUpdatedEvent
  | AnnotationDeletedEvent
  | AnnotationSelectedEvent
  | AnnotationDeselectedEvent;

// =============================================================================
// SELECTION EVENTS
// =============================================================================

export interface MeshSelectedEvent {
  type: 'mesh_selected';
  meshId: string;
  meshType: 'hull' | 'deck' | 'structure' | 'frame' | 'stringer';
  position: [number, number, number];
  timestamp: Date;
}

export interface MeshDeselectedEvent {
  type: 'mesh_deselected';
  timestamp: Date;
}

export interface HoverStartEvent {
  type: 'hover_start';
  meshId: string;
  position: [number, number, number];
  timestamp: Date;
}

export interface HoverEndEvent {
  type: 'hover_end';
  timestamp: Date;
}

export type SelectionEvent =
  | MeshSelectedEvent
  | MeshDeselectedEvent
  | HoverStartEvent
  | HoverEndEvent;

// =============================================================================
// EXPORT EVENTS
// =============================================================================

export interface ExportStartedEvent {
  type: 'export_started';
  format: 'gltf' | 'glb' | 'stl' | 'obj';
  timestamp: Date;
}

export interface ExportCompletedEvent {
  type: 'export_completed';
  format: string;
  fileSize: number;
  downloadUrl: string;
  timestamp: Date;
}

export interface ExportFailedEvent {
  type: 'export_failed';
  format: string;
  errorMessage: string;
  timestamp: Date;
}

export type ExportEvent =
  | ExportStartedEvent
  | ExportCompletedEvent
  | ExportFailedEvent;

// =============================================================================
// ALL EVENTS
// =============================================================================

export type ViewerEvent =
  | GeometryEvent
  | ViewEvent
  | SectionCutEvent
  | MeasurementEvent
  | AnnotationEvent
  | SelectionEvent
  | ExportEvent;

// =============================================================================
// EVENT EMITTER TYPES
// =============================================================================

export type EventCallback<T extends ViewerEvent = ViewerEvent> = (event: T) => void;

export interface EventEmitter {
  on<T extends ViewerEvent>(type: T['type'], callback: EventCallback<T>): () => void;
  off<T extends ViewerEvent>(type: T['type'], callback: EventCallback<T>): void;
  emit<T extends ViewerEvent>(event: T): void;
}

// =============================================================================
// TYPE GUARDS
// =============================================================================

export function isGeometryEvent(event: ViewerEvent): event is GeometryEvent {
  return (
    event.type === 'geometry_loaded' ||
    event.type === 'geometry_updated' ||
    event.type === 'geometry_invalidated' ||
    event.type === 'geometry_error'
  );
}

export function isViewEvent(event: ViewerEvent): event is ViewEvent {
  return (
    event.type === 'view_mode_changed' ||
    event.type === 'camera_changed' ||
    event.type === 'camera_preset'
  );
}

export function isMeasurementEvent(event: ViewerEvent): event is MeasurementEvent {
  return (
    event.type === 'measurement_started' ||
    event.type === 'measurement_point_added' ||
    event.type === 'measurement_completed' ||
    event.type === 'measurement_cancelled'
  );
}

export function isAnnotationEvent(event: ViewerEvent): event is AnnotationEvent {
  return (
    event.type === 'annotation_created' ||
    event.type === 'annotation_updated' ||
    event.type === 'annotation_deleted' ||
    event.type === 'annotation_selected' ||
    event.type === 'annotation_deselected'
  );
}
