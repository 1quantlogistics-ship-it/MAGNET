/**
 * MAGNET UI Common Types
 *
 * Shared type definitions used across the UI layer.
 */

// ============================================================================
// Geometry & Positioning
// ============================================================================

/**
 * 2D point/position
 */
export interface Point2D {
  x: number;
  y: number;
}

/**
 * 3D point/position
 */
export interface Point3D {
  x: number;
  y: number;
  z: number;
}

/**
 * 2D bounding box
 */
export interface BoundingBox2D {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * 3D bounding box
 */
export interface BoundingBox3D {
  min: Point3D;
  max: Point3D;
}

/**
 * Viewport dimensions
 */
export interface ViewportDimensions {
  width: number;
  height: number;
  devicePixelRatio: number;
}

// ============================================================================
// Animation & Motion
// ============================================================================

/**
 * VisionOS timing constants
 */
export const VISIONOS_TIMING = {
  // Pulse animations (Hz - cycles per second)
  markerPulse: 0.25,
  orbBreathe: 0.15,

  // Transition durations (ms)
  panelEnter: 600,
  cardExpand: 400,
  tooltipReveal: 300,
  microBounce: 200,
  focusTransition: 400,

  // Spring physics
  stiffness: 200,
  damping: 28,
  mass: 1,

  // Throttling (ms)
  animationThrottle: 16, // ~60fps
  pointerThrottle: 16,
  scrollThrottle: 32,
} as const;

/**
 * Spring configuration for Framer Motion
 */
export interface SpringConfig {
  stiffness: number;
  damping: number;
  mass?: number;
}

/**
 * Default spring config (VisionOS feel)
 */
export const DEFAULT_SPRING: SpringConfig = {
  stiffness: VISIONOS_TIMING.stiffness,
  damping: VISIONOS_TIMING.damping,
  mass: VISIONOS_TIMING.mass,
};

/**
 * Animation state
 */
export type AnimationState = 'idle' | 'entering' | 'animating' | 'exiting';

// ============================================================================
// Panel & Focus
// ============================================================================

/**
 * Panel identifiers
 */
export type PanelId =
  | 'inspector'
  | 'workspace'
  | 'chat'
  | 'command'
  | 'navigator'
  | 'properties';

/**
 * Focus state for panels
 */
export interface PanelFocusState {
  panelId: PanelId | null;
  previousPanelId: PanelId | null;
  timestamp: number;
}

/**
 * Panel depth for layering
 */
export type PanelDepth = 'near' | 'mid' | 'far';

// ============================================================================
// Status & State
// ============================================================================

/**
 * Generic status type
 */
export type Status = 'idle' | 'loading' | 'success' | 'error';

/**
 * Loading state with optional progress
 */
export interface LoadingState {
  status: Status;
  progress?: number; // 0-100
  message?: string;
  error?: ErrorInfo;
}

/**
 * Error information
 */
export interface ErrorInfo {
  code: string;
  message: string;
  details?: string;
  recoverable: boolean;
  timestamp: number;
}

// ============================================================================
// Design System Colors
// ============================================================================

/**
 * Semantic color names from VisionOS design system
 */
export type SemanticColor =
  | 'primary'    // Blue - interactive elements
  | 'success'    // Green - transient success states
  | 'error'      // Red - critical failures ONLY
  | 'neutral'    // Gray - default text/borders
  | 'surface'    // Glass background
  | 'emphasis';  // Blue subtle - highlights

/**
 * Priority levels (used in ARS, alerts)
 */
export type Priority = 1 | 2 | 3 | 4 | 5;

/**
 * Priority to semantic color mapping
 */
export function getPriorityColor(priority: Priority): SemanticColor {
  switch (priority) {
    case 1: return 'error';      // Critical safety/structural
    case 2: return 'emphasis';   // High - compliance
    case 3: return 'primary';    // Medium - optimization
    case 4: return 'neutral';    // Low
    case 5: return 'neutral';    // Info
  }
}

// ============================================================================
// Component Variants
// ============================================================================

/**
 * Window/card variants
 */
export type WindowVariant = 'default' | 'emphasis' | 'critical';

/**
 * Button variants
 */
export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

/**
 * Size variants
 */
export type Size = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

// ============================================================================
// Utility Types
// ============================================================================

/**
 * Make all properties optional except specified keys
 */
export type PartialExcept<T, K extends keyof T> = Partial<T> & Pick<T, K>;

/**
 * Make specified properties required
 */
export type RequiredKeys<T, K extends keyof T> = T & Required<Pick<T, K>>;

/**
 * Deep partial type
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

/**
 * Extract non-function properties from type
 */
export type DataOnly<T> = {
  [K in keyof T as T[K] extends Function ? never : K]: T[K];
};

// ============================================================================
// DPR Utilities
// ============================================================================

/**
 * Get device pixel ratio adjusted value
 */
export function getDPRAdjustedValue(value: number): number {
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
  return Math.round(value * dpr) / dpr;
}

/**
 * Get current viewport dimensions with DPR
 */
export function getViewportDimensions(): ViewportDimensions {
  if (typeof window === 'undefined') {
    return { width: 0, height: 0, devicePixelRatio: 1 };
  }
  return {
    width: window.innerWidth,
    height: window.innerHeight,
    devicePixelRatio: window.devicePixelRatio || 1,
  };
}

// ============================================================================
// ID Generation
// ============================================================================

/**
 * Generate a unique ID with optional prefix
 */
export function generateId(prefix = 'ui'): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `${prefix}_${timestamp}_${random}`;
}

/**
 * Generate a correlation ID for event tracking
 */
export function generateCorrelationId(): string {
  return generateId('corr');
}
