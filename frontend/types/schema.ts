/**
 * schema.ts - TypeScript type definitions for WebGL visualization v1.1
 * BRAVO OWNS THIS FILE.
 *
 * AUTO-GENERATED from webgl/schema.py
 * Schema version: 1.1.0
 *
 * Run to regenerate:
 *   python -c "from webgl.schema import generate_typescript_types; print(generate_typescript_types())" > frontend/types/schema.ts
 */

export const SCHEMA_VERSION = "1.1.0";

// =============================================================================
// ENUMS
// =============================================================================

export type CoordinateSystem = "magnet_standard";
export type Units = "meters" | "millimeters";
export type GeometryMode = "authoritative" | "visual_only";
export type LODLevel = "low" | "medium" | "high" | "ultra";
export type MaterialSide = "front" | "back" | "double";

// =============================================================================
// CORE INTERFACES
// =============================================================================

export interface SchemaMetadata {
  schema_version: string;
  coordinate_system: CoordinateSystem;
  units: Units;
}

export interface BoundingBox {
  min: [number, number, number];
  max: [number, number, number];
}

export interface MeshMetadata {
  vertex_count: number;
  face_count: number;
  bounds: BoundingBox | null;
  has_uvs: boolean;
  has_colors: boolean;
  has_tangents: boolean;
}

export interface MeshData {
  mesh_id: string;
  vertices: number[];      // Interleaved [x,y,z, x,y,z, ...]
  indices: number[];       // Triangle indices
  normals: number[];       // Per-vertex normals
  uvs?: number[];          // Optional UV coordinates
  colors?: number[];       // Optional RGBA colors
  tangents?: number[];     // Optional tangent vectors
  metadata: MeshMetadata;
}

export interface LineData {
  line_id: string;
  points: [number, number, number][];
  closed: boolean;
}

// =============================================================================
// COMPOSITE STRUCTURES
// =============================================================================

export interface StructureSceneData {
  frames: MeshData[];
  stringers: MeshData[];
  keel: MeshData | null;
  girders: MeshData[];
  plating: MeshData[];
}

export interface HydrostaticSceneData {
  waterlines: LineData[];
  sectional_areas: LineData[];
  bonjean_curves: LineData[];
  displacement_volume: MeshData | null;
}

export interface MaterialDef {
  name: string;
  type: string;
  color: string;
  metalness: number;
  roughness: number;
  opacity: number;
  transparent: boolean;
  side: MaterialSide;
  emissive: string;
  emissiveIntensity: number;
}

// =============================================================================
// SCENE DATA - Main API Response Type
// =============================================================================

export interface SceneData {
  schema: SchemaMetadata;
  design_id: string;
  version_id: string;
  geometry_mode: GeometryMode;
  hull: MeshData | null;
  deck: MeshData | null;
  transom: MeshData | null;
  structure: StructureSceneData | null;
  hydrostatics: HydrostaticSceneData | null;
  materials: MaterialDef[];
  metadata: Record<string, unknown>;
}

// =============================================================================
// ERROR TYPES
// =============================================================================

export interface GeometryError {
  code: string;
  category: string;
  severity: string;
  message: string;
  details: Record<string, unknown>;
  recovery_hint: string | null;
}

export interface GeometryErrorResponse {
  error: GeometryError;
}

// Type guard for error responses
export function isGeometryErrorResponse(obj: unknown): obj is GeometryErrorResponse {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'error' in obj &&
    typeof (obj as GeometryErrorResponse).error === 'object' &&
    'code' in (obj as GeometryErrorResponse).error
  );
}

// =============================================================================
// WEBSOCKET MESSAGES
// =============================================================================

export interface GeometryUpdateMessage {
  message_type: "geometry_update";
  update_id: string;
  prev_update_id: string;
  design_id: string;
  hull: MeshData | null;
  deck: MeshData | null;
  structure: StructureSceneData | null;
  is_full_update: boolean;
  timestamp: string;
}

export interface GeometryFailedMessage {
  message_type: "geometry_failed";
  design_id: string;
  error_code: string;
  error_message: string;
  recovery_hint: string | null;
  timestamp: string;
}

export interface GeometryInvalidatedMessage {
  message_type: "geometry_invalidated";
  design_id: string;
  reason: string;
  invalidated_components: string[];
  timestamp: string;
}

export type WebSocketMessage =
  | GeometryUpdateMessage
  | GeometryFailedMessage
  | GeometryInvalidatedMessage;

// Type guards for WebSocket messages
export function isGeometryUpdateMessage(msg: WebSocketMessage): msg is GeometryUpdateMessage {
  return msg.message_type === "geometry_update";
}

export function isGeometryFailedMessage(msg: WebSocketMessage): msg is GeometryFailedMessage {
  return msg.message_type === "geometry_failed";
}

export function isGeometryInvalidatedMessage(msg: WebSocketMessage): msg is GeometryInvalidatedMessage {
  return msg.message_type === "geometry_invalidated";
}

// =============================================================================
// ANNOTATION TYPES
// =============================================================================

export type MeasurementType = "distance" | "angle" | "area" | "volume";
export type AnnotationCategory = "general" | "measurement" | "issue" | "note" | "question" | "decision";

export interface Measurement3D {
  type: MeasurementType;
  points: [number, number, number][];
  value: number;
  unit: string;
  precision: number;
}

export interface Annotation3D {
  annotation_id: string;
  design_id: string;
  position: [number, number, number];
  normal: [number, number, number] | null;
  label: string;
  description: string;
  category: AnnotationCategory;
  measurement: Measurement3D | null;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  linked_decision_id: string | null;
  linked_phase: string | null;
  linked_component: string | null;
  visible: boolean;
  color: string;
  icon: string;
}

// =============================================================================
// API REQUEST TYPES
// =============================================================================

export interface SectionCutRequest {
  plane: "transverse" | "longitudinal" | "waterplane";
  position: number;  // 0.0 - 1.0
}

export interface SectionCutResponse {
  plane: string;
  position: number;
  curves: LineData[];
  metadata: Record<string, unknown>;
}

export interface ExportRequest {
  format: "gltf" | "glb" | "stl" | "obj";
  include_structure?: boolean;
  include_annotations?: boolean;
  lod?: LODLevel;
}

export interface ExportMetadata {
  format: string;
  design_id: string;
  version_id: string;
  exported_at: string;
  schema_version: string;
  geometry_mode: GeometryMode;
  file_size: number;
  checksum: string;
}

// =============================================================================
// BINARY FORMAT CONSTANTS
// =============================================================================

export const BINARY_MAGIC = 0x54454E4D; // "MNET" in little-endian
export const BINARY_VERSION = 1;
export const FLAG_HAS_UVS = 1;
export const FLAG_HAS_COLORS = 2;
export const FLAG_HAS_TANGENTS = 4;
