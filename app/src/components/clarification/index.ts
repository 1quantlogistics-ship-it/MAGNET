/**
 * MAGNET UI Module 04: Clarification Components
 *
 * AI-initiated clarification system component exports.
 * VisionOS-style spatial prompts and glass form controls.
 */

// ============================================================================
// Clarification UI Components (Bravo)
// ============================================================================

// QuickClarification - Inline spatial chips
export { QuickClarification } from './QuickClarification';

// StandardClarification - Floating spatial card
export { StandardClarification } from './StandardClarification';

// ComplexClarification - Spatial modal form
export { ComplexClarification } from './ComplexClarification';

// ContextualPrompt - Dynamic positioned prompt
export { ContextualPrompt } from './ContextualPrompt';

// ContextualHighlight - 3D selection effect
export { ContextualHighlight } from './ContextualHighlight';
export type { ContextualHighlightProps } from './ContextualHighlight';

// ============================================================================
// Core Components (Alpha)
// ============================================================================

// ClarificationManager - Orchestrator
export {
  ClarificationManager,
  type ClarificationManagerProps,
} from './ClarificationManager';

// CountdownRing - Animated progress ring
export { CountdownRing } from './CountdownRing';

// GlassPicker - Custom dropdown
export { GlassPicker } from './GlassPicker';

// SpatialSlider - Custom range slider
export { SpatialSlider } from './SpatialSlider';

// GlassToggle - Custom toggle switch
export { GlassToggle } from './GlassToggle';

// ============================================================================
// Store & Engine (Bravo)
// ============================================================================

// Store exports
export {
  clarificationStore,
  getClarificationState,
  getActiveRequest,
  getQueueLength,
  getActiveContextualRequest,
  hasClarificationActive,
  requestClarification,
  respondToClarification,
  skipClarification,
  expireClarification,
  resetClarificationStore,
  clearClarificationHistory,
  subscribeToClarification,
} from '../../stores/domain/clarificationStore';

// Engine exports
export { clarify, ClarificationEngineClass } from '../../systems/ClarificationEngine';

// ============================================================================
// Types
// ============================================================================

// Re-export types for convenience
export type {
  ClarificationType,
  ClarificationPriority,
  ClarificationStatus,
  ClarificationOption,
  ClarificationField,
  ClarificationFieldType,
  ClarificationRequest,
  ClarificationStoreState,
  ClarificationStoreActions,
  ClarificationStore,
  ClarificationResolvedEventDetail,
  QuickClarificationProps,
  StandardClarificationProps,
  ComplexClarificationProps,
  ContextualPromptProps,
  CountdownRingProps,
  GlassPickerProps,
  SpatialSliderProps,
  GlassToggleProps,
  OccludableWindowProps,
  SpatialOcclusionContextValue,
  OcclusionState,
  ScreenPosition,
  WorldPosition,
} from '../../types/clarification';

// Re-export constants
export {
  COUNTDOWN_RING_SIZES,
  CLARIFICATION_MOTION,
  DEFAULT_AUTO_DISMISS_MS,
  INITIAL_CLARIFICATION_STATE,
} from '../../types/clarification';
