/**
 * MAGNET UI Module 04: Clarification Types
 *
 * Type definitions for the AI-initiated clarification system.
 * Spatial prompts, floating cards, and complex forms.
 */

import { SCHEMA_VERSION } from './schema-version';

// =============================================================================
// Clarification Classification
// =============================================================================

/**
 * Type of clarification UI to show
 */
export type ClarificationType = 'quick' | 'standard' | 'complex' | 'contextual';

/**
 * Priority level for clarification requests
 */
export type ClarificationPriority = 'required' | 'recommended' | 'optional';

/**
 * Status of a clarification request
 */
export type ClarificationStatus = 'pending' | 'answered' | 'skipped' | 'expired';

// =============================================================================
// Options & Fields
// =============================================================================

/**
 * Option for selection-based clarifications
 */
export interface ClarificationOption {
  /** Unique option identifier */
  id: string;
  /** Display label */
  label: string;
  /** Optional description */
  description?: string;
  /** Optional icon name */
  icon?: string;
  /** Value to return when selected */
  value: unknown;
  /** Whether this is the default option */
  isDefault?: boolean;
}

/**
 * Field types for complex clarifications
 */
export type ClarificationFieldType = 'text' | 'number' | 'picker' | 'slider' | 'toggle';

/**
 * Field definition for complex clarifications
 */
export interface ClarificationField {
  /** Unique field identifier */
  id: string;
  /** Field type */
  type: ClarificationFieldType;
  /** Display label */
  label: string;
  /** Placeholder text */
  placeholder?: string;
  /** Default value */
  defaultValue?: unknown;
  /** Options for picker type */
  options?: ClarificationOption[];
  /** Minimum value for number/slider */
  min?: number;
  /** Maximum value for number/slider */
  max?: number;
  /** Step increment for number/slider */
  step?: number;
  /** Unit display (e.g., "m", "kg") */
  unit?: string;
  /** Whether field is required */
  required?: boolean;
}

// =============================================================================
// Position Types
// =============================================================================

/**
 * 2D screen position
 */
export interface ScreenPosition {
  x: number;
  y: number;
}

/**
 * 3D world position
 */
export type WorldPosition = [number, number, number];

// =============================================================================
// Clarification Request
// =============================================================================

/**
 * Complete clarification request
 */
export interface ClarificationRequest {
  /** Unique request identifier */
  id: string;
  /** Type of clarification UI */
  type: ClarificationType;
  /** Priority level */
  priority: ClarificationPriority;
  /** AI's question/prompt */
  question: string;
  /** Additional context */
  context?: string;
  /** Options for quick/standard types */
  options?: ClarificationOption[];
  /** Whether multiple options can be selected */
  allowMultiple?: boolean;
  /** Fields for complex type */
  fields?: ClarificationField[];
  /** Related chat message ID */
  relatedMessageId?: string;
  /** Related component ID for contextual type */
  relatedComponentId?: string;
  /** Screen position to anchor near */
  targetPosition?: ScreenPosition;
  /** 3D world position for contextual type */
  worldPosition?: WorldPosition;
  /** Default value if skipped/expired */
  defaultValue?: unknown;
  /** Auto-dismiss timeout in ms */
  autoDismissMs?: number;
  /** Phrase to show when assuming default (e.g., "I'll proceed with metric units") */
  assumptionPhrase?: string;
  /** Current status */
  status: ClarificationStatus;
  /** User's response */
  response?: unknown;
  /** Request timestamp */
  timestamp: number;
  /** Schema version */
  schema_version: string;
}

// =============================================================================
// Occlusion State
// =============================================================================

/**
 * Spatial occlusion state for window management
 */
export interface OcclusionState {
  /** Whether occlusion is active */
  isActive: boolean;
  /** Window IDs to exclude from occlusion */
  excludeIds: string[];
}

// =============================================================================
// Component Props
// =============================================================================

/**
 * QuickClarification props
 */
export interface QuickClarificationProps {
  /** The clarification request */
  request: ClarificationRequest;
}

/**
 * StandardClarification props
 */
export interface StandardClarificationProps {
  /** The clarification request */
  request: ClarificationRequest;
}

/**
 * ComplexClarification props
 */
export interface ComplexClarificationProps {
  /** The clarification request */
  request: ClarificationRequest;
}

/**
 * ContextualPrompt props
 */
export interface ContextualPromptProps {
  /** The clarification request */
  request: ClarificationRequest;
}

/**
 * CountdownRing props
 */
export interface CountdownRingProps {
  /** Total duration in ms */
  duration: number;
  /** Remaining time in ms */
  remaining: number;
  /** Whether countdown is paused */
  isPaused?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional class name */
  className?: string;
}

/**
 * GlassPicker props
 */
export interface GlassPickerProps {
  /** Current value */
  value: string;
  /** Available options */
  options: ClarificationOption[];
  /** Change handler */
  onChange: (value: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Additional class name */
  className?: string;
}

/**
 * SpatialSlider props
 */
export interface SpatialSliderProps {
  /** Current value */
  value: number;
  /** Minimum value */
  min: number;
  /** Maximum value */
  max: number;
  /** Step increment */
  step?: number;
  /** Unit display */
  unit?: string;
  /** Change handler */
  onChange: (value: number) => void;
  /** Additional class name */
  className?: string;
}

/**
 * GlassToggle props
 */
export interface GlassToggleProps {
  /** Current value */
  value: boolean;
  /** Change handler */
  onChange: (value: boolean) => void;
  /** Label text */
  label?: string;
  /** Additional class name */
  className?: string;
}

/**
 * OccludableWindow props
 */
export interface OccludableWindowProps {
  /** Unique window identifier */
  id: string;
  /** Window content */
  children: React.ReactNode;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Context Types
// =============================================================================

/**
 * Spatial occlusion context value
 */
export interface SpatialOcclusionContextValue {
  /** Current occlusion state */
  occlusion: OcclusionState;
  /** Activate occlusion with optional exclusions */
  activateOcclusion: (excludeIds?: string[]) => void;
  /** Release occlusion */
  releaseOcclusion: () => void;
}

// =============================================================================
// Store Types
// =============================================================================

/**
 * Clarification store state
 */
export interface ClarificationStoreState {
  /** Queue of pending requests */
  queue: ClarificationRequest[];
  /** Currently active request */
  activeRequest: ClarificationRequest | null;
  /** History of completed requests */
  history: ClarificationRequest[];
  /** Active contextual selection request */
  activeContextualRequest: ClarificationRequest | null;
  /** Schema version */
  schema_version: string;
}

/**
 * Clarification store actions
 */
export interface ClarificationStoreActions {
  /** Add a clarification request to the queue */
  requestClarification: (request: Omit<ClarificationRequest, 'id' | 'status' | 'timestamp' | 'schema_version'>) => string;
  /** Respond to the active clarification */
  respondToClarification: (requestId: string, response: unknown) => void;
  /** Skip the active clarification */
  skipClarification: (requestId: string) => void;
  /** Reset store */
  reset: () => void;
}

/**
 * Complete clarification store
 */
export type ClarificationStore = ClarificationStoreState & ClarificationStoreActions;

// =============================================================================
// Event Types
// =============================================================================

/**
 * Clarification resolved event detail
 */
export interface ClarificationResolvedEventDetail {
  /** Request ID */
  requestId: string;
  /** Final status */
  status: ClarificationStatus;
  /** User response or default value */
  response: unknown;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Default auto-dismiss timeout in ms
 */
export const DEFAULT_AUTO_DISMISS_MS = 30000;

/**
 * CountdownRing size configurations
 */
export const COUNTDOWN_RING_SIZES = {
  sm: 24,
  md: 32,
  lg: 48,
} as const;

/**
 * Motion constants for clarification animations
 */
export const CLARIFICATION_MOTION = {
  spring: {
    stiffness: 140,
    damping: 24,
    mass: 0.8,
  },
  chipBounce: {
    overshoot: 1.08,
    duration: 0.5,
  },
  staggerDelay: 0.05,
} as const;

/**
 * Initial clarification store state
 */
export const INITIAL_CLARIFICATION_STATE: ClarificationStoreState = {
  queue: [],
  activeRequest: null,
  history: [],
  activeContextualRequest: null,
  schema_version: SCHEMA_VERSION,
};
