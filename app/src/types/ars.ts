/**
 * MAGNET UI ARS (Auto Recommendation System) Types
 *
 * Type definitions for the ARS module (UI-01).
 * Schema-versioned for backend reconciliation.
 */

import type { UISchemaVersion } from './schema-version';
import type { Point3D, Priority } from './common';
import { UI_SCHEMA_VERSION } from './schema-version';

// ============================================================================
// Core ARS Types
// ============================================================================

/**
 * ARS priority levels
 * 1 = Critical (safety/structural)
 * 2 = High (compliance)
 * 3 = Medium (optimization)
 * 4 = Low (minor improvement)
 * 5 = Info (FYI)
 */
export type ARSPriority = Priority;

/**
 * ARS recommendation categories
 */
export type ARSCategory =
  | 'stability'
  | 'structure'
  | 'propulsion'
  | 'systems'
  | 'compliance'
  | 'optimization'
  | 'weight'
  | 'performance';

/**
 * ARS recommendation status
 */
export type ARSStatus =
  | 'active'     // Currently relevant
  | 'dismissed'  // User dismissed
  | 'applied'    // User applied the recommendation
  | 'expired'    // No longer relevant (design changed)
  | 'superseded'; // Replaced by newer recommendation

/**
 * ARS action types
 */
export type ARSActionType =
  | 'apply'      // Apply the recommendation
  | 'explain'    // Get detailed explanation
  | 'dismiss'    // Dismiss the recommendation
  | 'navigate'   // Navigate to related component
  | 'compare';   // Show before/after comparison

// ============================================================================
// ARS Recommendation
// ============================================================================

/**
 * Action that can be taken on a recommendation
 */
export interface ARSAction {
  id: string;
  label: string;
  type: ARSActionType;
  isPrimary?: boolean;
  disabled?: boolean;
  disabledReason?: string;
}

/**
 * Impact metric for a recommendation
 */
export interface ARSImpact {
  metric: string;      // "GM", "Weight", "Rt", "Cost"
  change: number;      // Percentage change (can be negative)
  unit?: string;       // Optional unit for display
  isPositive: boolean; // Whether change is beneficial
}

/**
 * 3D marker configuration for workspace visualization
 */
export interface ARSMarker {
  position: Point3D;
  normal?: Point3D;    // Surface normal for proper orientation
  scale?: number;      // Marker scale (default 1)
}

/**
 * Mutation payload for applying recommendation
 */
export interface ARSMutation {
  type: string;
  targetPath: string;
  payload: Record<string, unknown>;
  reversible: boolean;
  reversePayload?: Record<string, unknown>;
}

/**
 * Full ARS Recommendation
 */
export interface ARSRecommendation {
  // Identity
  id: string;
  schema_version: UISchemaVersion;

  // Classification
  priority: ARSPriority;
  category: ARSCategory;
  status: ARSStatus;

  // Content
  title: string;           // Max 40 chars
  subtitle?: string;       // Max 60 chars - optional detail
  description?: string;    // Full explanation (shown in expanded view)

  // Impact (single primary metric)
  impact: ARSImpact;

  // Secondary impacts (optional)
  secondaryImpacts?: ARSImpact[];

  // Actions (max 3)
  actions: ARSAction[];

  // Targeting
  targetId?: string;       // Component ID in design
  targetPath?: string;     // Path in design state

  // 3D marker (optional)
  marker?: ARSMarker;

  // Mutation payload (for apply action)
  mutation?: ARSMutation;

  // Metadata
  timestamp: number;
  expiresAt?: number;
  sourceAgent?: string;    // Agent that generated this
  confidence?: number;     // 0-1 confidence score

  // Relationships
  relatedIds?: string[];   // Related recommendation IDs
  supersedes?: string;     // ID of recommendation this supersedes
}

// ============================================================================
// ARS Store State Types
// ============================================================================

/**
 * Read-only state (derived from backend/computations)
 */
export interface ARSReadOnlyState {
  /** Active recommendations sorted by priority */
  activeRecommendations: ARSRecommendation[];
  /** Current telemetry item (highest priority active) */
  currentTelemetryItem: ARSRecommendation | null;
  /** Count by category */
  countByCategory: Record<ARSCategory, number>;
  /** Count by priority */
  countByPriority: Record<ARSPriority, number>;
  /** Has critical recommendations */
  hasCritical: boolean;
}

/**
 * Read-write state (UI-specific)
 */
export interface ARSReadWriteState {
  /** All recommendations by ID */
  recommendations: Record<string, ARSRecommendation>;
  /** Currently selected recommendation ID */
  selectedId: string | null;
  /** Currently expanded recommendation ID */
  expandedId: string | null;
  /** Telemetry queue (priority-sorted IDs) */
  telemetryQueue: string[];
  /** Current telemetry ID being displayed */
  currentTelemetryId: string | null;
  /** Panel collapsed state */
  isCollapsed: boolean;
  /** Filter settings */
  filters: ARSFilters;
}

/**
 * Combined ARS state
 */
export interface ARSState extends ARSReadOnlyState, ARSReadWriteState {}

/**
 * Filter options for ARS panel
 */
export interface ARSFilters {
  categories: ARSCategory[] | 'all';
  minPriority: ARSPriority;
  showDismissed: boolean;
  showApplied: boolean;
  targetComponentId?: string;
}

// ============================================================================
// ARS Actions (for store/orchestrator)
// ============================================================================

/**
 * Payload for adding a recommendation
 */
export interface AddRecommendationPayload {
  recommendation: Omit<ARSRecommendation, 'schema_version'>;
}

/**
 * Payload for updating recommendation status
 */
export interface UpdateStatusPayload {
  id: string;
  status: ARSStatus;
  reason?: string;
}

/**
 * Payload for applying a recommendation action
 */
export interface ApplyActionPayload {
  recommendationId: string;
  actionId: string;
}

/**
 * Payload for selecting a recommendation
 */
export interface SelectRecommendationPayload {
  id: string | null;
  autoExpand?: boolean;
  navigateToTarget?: boolean;
}

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a new ARS recommendation with defaults
 */
export function createARSRecommendation(
  partial: Omit<ARSRecommendation, 'id' | 'schema_version' | 'timestamp' | 'status'> & {
    id?: string;
    status?: ARSStatus;
  }
): ARSRecommendation {
  return {
    id: partial.id || `ars_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    schema_version: UI_SCHEMA_VERSION,
    status: partial.status || 'active',
    timestamp: Date.now(),
    ...partial,
  };
}

/**
 * Default filters
 */
export const DEFAULT_ARS_FILTERS: ARSFilters = {
  categories: 'all',
  minPriority: 5,
  showDismissed: false,
  showApplied: false,
};

/**
 * Initial ARS read-write state
 */
export const INITIAL_ARS_STATE: ARSReadWriteState = {
  recommendations: {},
  selectedId: null,
  expandedId: null,
  telemetryQueue: [],
  currentTelemetryId: null,
  isCollapsed: false,
  filters: DEFAULT_ARS_FILTERS,
};
