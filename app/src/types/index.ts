/**
 * MAGNET UI Types - Public Exports
 *
 * Central export point for all UI type definitions.
 */

// Schema versioning
export {
  UI_SCHEMA_VERSION,
  SCHEMA_META,
  isCompatibleVersion,
  type UISchemaVersion,
  type SchemaVersionMeta,
} from './schema-version';

// Contracts
export type {
  UIEventType,
  UIEventHandler,
  Unsubscribe,
  BackendStateSnapshot,
  UIOrchestratorContract,
  OrchestratorStatus,
  UIStoreContract,
  ComponentLifecycle,
  ComponentContract,
  UIEvent,
  UIEventSource,
  StoreConfig,
  AnimationPriority,
  AnimationTask,
  AnimationSchedulerContract,
} from './contracts';

// Events
export {
  createUIEvent,
  isEventType,
  getEventPayload,
  USER_EVENT_TYPES,
  BACKEND_EVENT_TYPES,
  AGENT_EVENT_TYPES,
  UI_EVENT_TYPES,
  RECONCILER_EVENT_TYPES,
  isUserEvent,
  isBackendEvent,
  isAgentEvent,
  type UIEventPayloadMap,
  type UserSelectPayload,
  type UserHoverPayload,
  type UserClickPayload,
  type UserInputPayload,
  type UserDragPayload,
  type UserFocusPayload,
  type BackendStateChangedPayload,
  type BackendPhaseCompletedPayload,
  type BackendValidationResultPayload,
  type BackendGeometryUpdatedPayload,
  type AgentMessagePayload,
  type AgentThinkingPayload,
  type AgentCompletePayload,
  type AgentErrorPayload,
  type UIPanelFocusPayload,
  type UIPanelBlurPayload,
  type UIAnimationStartPayload,
  type UIAnimationCompletePayload,
  type UIErrorPayload,
  type UISnapshotCreatedPayload,
  type ReconcilerSyncStartPayload,
  type ReconcilerSyncCompletePayload,
  type ReconcilerConflictPayload,
} from './events';

// Common types
export {
  VISIONOS_TIMING,
  DEFAULT_SPRING,
  getDPRAdjustedValue,
  getViewportDimensions,
  generateId,
  generateCorrelationId,
  getPriorityColor,
  type Point2D,
  type Point3D,
  type BoundingBox2D,
  type BoundingBox3D,
  type ViewportDimensions,
  type SpringConfig,
  type AnimationState,
  type PanelId,
  type PanelFocusState,
  type PanelDepth,
  type Status,
  type LoadingState,
  type ErrorInfo,
  type SemanticColor,
  type Priority,
  type WindowVariant,
  type ButtonVariant,
  type Size,
  type PartialExcept,
  type RequiredKeys,
  type DeepPartial,
  type DataOnly,
} from './common';

// ARS types
export {
  createARSRecommendation,
  DEFAULT_ARS_FILTERS,
  INITIAL_ARS_STATE,
  type ARSPriority,
  type ARSCategory,
  type ARSStatus,
  type ARSActionType,
  type ARSAction,
  type ARSImpact,
  type ARSMarker,
  type ARSMutation,
  type ARSRecommendation,
  type ARSReadOnlyState,
  type ARSReadWriteState,
  type ARSState,
  type ARSFilters,
  type AddRecommendationPayload,
  type UpdateStatusPayload,
  type ApplyActionPayload,
  type SelectRecommendationPayload,
} from './ars';

// Geometry types
export {
  DEFAULT_CAMERA_STATE,
  DEFAULT_PARALLAX_STATE,
  DEFAULT_FOCUS_BLUR_STATE,
  INITIAL_GEOMETRY_STATE,
  INITIAL_VIEWPORT_STATE,
  getBoundingBoxCenter,
  getBoundingBoxSize,
  calculateFramingCamera,
  type LODLevel,
  type MeshVisibility,
  type MeshData,
  type GeometryReadOnlyState,
  type GeometryReadWriteState,
  type GeometryState,
  type CameraProjection,
  type CameraState,
  type CameraAnimationTarget,
  type ParallaxState,
  type FocusBlurState,
  type ViewportState,
} from './geometry';

// Snapshot types
export {
  DEFAULT_SNAPSHOT_CONFIG,
  INITIAL_SNAPSHOT_STORE_STATE,
  createSnapshotMeta,
  estimateSnapshotSize,
  pruneSnapshots,
  type SnapshotTrigger,
  type SnapshotMeta,
  type PanelStateSnapshot,
  type SelectionSnapshot,
  type UIStateSnapshot,
  type SnapshotConfig,
  type SnapshotStoreState,
  type CreateSnapshotPayload,
  type RestoreSnapshotPayload,
  type CompareSnapshotsPayload,
  type SnapshotComparison,
  type SnapshotDifference,
} from './snapshot';

// Command types
export {
  INITIAL_COMMAND_STATE,
  createCommand,
  createSuccessResult,
  createErrorResult,
  scoreCommand,
  searchCommands,
  type CommandCategory,
  type CommandStatus,
  type CommandParamType,
  type CommandParam,
  type Command,
  type CommandResult,
  type PaletteMode,
  type CommandHistoryEntry,
  type CommandReadOnlyState,
  type CommandReadWriteState,
  type CommandState,
} from './command';

// Domain hashes (V1.4 Integration)
export {
  DOMAINS,
  MAX_CHAIN_DEPTH,
  INITIAL_CHAIN_STATE,
  INITIAL_DOMAIN_CHAIN_STATES,
  type Domain,
  type DomainHashes,
  type PartialDomainHashes,
  type ChainState,
  type DomainChainStates,
  type HashComparisonResult,
  type ChainValidationResult,
} from './domainHashes';

// Transaction types (V1.4 Integration)
export {
  DEFAULT_ROLLBACK_CONFIG,
  INITIAL_TRANSACTION_MANAGER_STATE,
  type TransactionStatus,
  type TransactionSnapshot,
  type Transaction,
  type TransactionManagerState,
  type TransactionEventType,
  type TransactionEventPayload,
  type RollbackConfig,
} from './transaction';

// Chain-tracked events (V1.4 Integration)
export {
  createChainTrackedEvent,
  hasChainTracking,
  getEventDomain,
  type ChainTrackingMeta,
  type ChainTrackedUIEvent,
  type BackendChainEvent,
} from './events';

// WebGL buffer types (V1.4 Integration)
export type {
  WebGLBufferType,
  WebGLBufferAttribute,
  WebGLBufferDescriptor,
  GeometryUpdatePayload,
  MeshIncrementalUpdate,
  GeometryStreamMessageType,
  GeometryStreamMessage,
  GeometryStreamError,
} from './geometry';
