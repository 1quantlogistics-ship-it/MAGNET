/**
 * MAGNET UI Snapshot Types
 *
 * Type definitions for UI state snapshots.
 * Enables design version playback and session recovery.
 */

import type { UISchemaVersion } from './schema-version';
import type { ARSReadWriteState } from './ars';
import type { GeometryReadWriteState, ViewportState } from './geometry';
import type { PanelId } from './common';
import { UI_SCHEMA_VERSION } from './schema-version';

// ============================================================================
// Snapshot Types
// ============================================================================

/**
 * Snapshot trigger type
 */
export type SnapshotTrigger =
  | 'auto'           // Automatic periodic snapshot
  | 'manual'         // User-initiated
  | 'phase_change'   // Design phase changed
  | 'mutation'       // Significant state mutation
  | 'session_start'  // Session began
  | 'session_end';   // Session ending

/**
 * Snapshot metadata
 */
export interface SnapshotMeta {
  id: string;
  schema_version: UISchemaVersion;
  timestamp: number;
  trigger: SnapshotTrigger;
  label?: string;
  description?: string;

  // Design context
  designId?: string;
  designVersion?: string;
  phase?: string;

  // Size tracking
  sizeBytes?: number;
}

/**
 * Panel state snapshot
 */
export interface PanelStateSnapshot {
  focusedPanelId: PanelId | null;
  collapsedPanels: PanelId[];
  panelPositions?: Record<PanelId, { x: number; y: number }>;
  panelSizes?: Record<PanelId, { width: number; height: number }>;
}

/**
 * Selection state snapshot
 */
export interface SelectionSnapshot {
  selectedComponentIds: string[];
  selectedRecommendationId: string | null;
  highlightedId: string | null;
}

/**
 * Full UI state snapshot
 */
export interface UIStateSnapshot {
  meta: SnapshotMeta;

  // Panel state
  panels: PanelStateSnapshot;

  // Selection state
  selection: SelectionSnapshot;

  // Module states (partial - only UI-specific state, not backend data)
  ars: Pick<ARSReadWriteState, 'selectedId' | 'expandedId' | 'isCollapsed' | 'filters'>;
  geometry: GeometryReadWriteState;
  viewport: ViewportState;

  // Chat history (limited for size)
  chatHistoryIds?: string[];

  // Command palette state
  commandPalette?: {
    recentCommands: string[];
    favorites: string[];
  };
}

// ============================================================================
// Snapshot Store State
// ============================================================================

/**
 * Snapshot store configuration
 */
export interface SnapshotConfig {
  /** Maximum number of snapshots to retain */
  maxSnapshots: number;

  /** Auto-snapshot interval in ms (0 = disabled) */
  autoSnapshotInterval: number;

  /** Snapshot on phase change */
  snapshotOnPhaseChange: boolean;

  /** Maximum snapshot size in bytes before compression */
  maxSnapshotSize: number;
}

/**
 * Snapshot store state
 */
export interface SnapshotStoreState {
  /** All snapshots by ID */
  snapshots: Record<string, UIStateSnapshot>;

  /** Snapshot IDs in chronological order */
  snapshotOrder: string[];

  /** Currently active snapshot (for playback) */
  activeSnapshotId: string | null;

  /** Is playback mode active */
  isPlaybackMode: boolean;

  /** Configuration */
  config: SnapshotConfig;

  /** Last auto-snapshot timestamp */
  lastAutoSnapshotTimestamp: number;
}

// ============================================================================
// Snapshot Actions
// ============================================================================

/**
 * Payload for creating a snapshot
 */
export interface CreateSnapshotPayload {
  trigger: SnapshotTrigger;
  label?: string;
  description?: string;
}

/**
 * Payload for restoring a snapshot
 */
export interface RestoreSnapshotPayload {
  snapshotId: string;
  partial?: boolean;  // Only restore selected parts
  exclude?: (keyof UIStateSnapshot)[];
}

/**
 * Payload for comparing snapshots
 */
export interface CompareSnapshotsPayload {
  snapshotIdA: string;
  snapshotIdB: string;
}

/**
 * Snapshot comparison result
 */
export interface SnapshotComparison {
  snapshotA: SnapshotMeta;
  snapshotB: SnapshotMeta;
  differences: SnapshotDifference[];
}

export interface SnapshotDifference {
  path: string;
  type: 'added' | 'removed' | 'changed';
  valueA?: unknown;
  valueB?: unknown;
}

// ============================================================================
// Default Values
// ============================================================================

export const DEFAULT_SNAPSHOT_CONFIG: SnapshotConfig = {
  maxSnapshots: 50,
  autoSnapshotInterval: 0, // Disabled by default
  snapshotOnPhaseChange: true,
  maxSnapshotSize: 1024 * 1024, // 1MB
};

export const INITIAL_SNAPSHOT_STORE_STATE: SnapshotStoreState = {
  snapshots: {},
  snapshotOrder: [],
  activeSnapshotId: null,
  isPlaybackMode: false,
  config: DEFAULT_SNAPSHOT_CONFIG,
  lastAutoSnapshotTimestamp: 0,
};

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create snapshot metadata
 */
export function createSnapshotMeta(
  trigger: SnapshotTrigger,
  label?: string,
  description?: string
): SnapshotMeta {
  return {
    id: `snap_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    schema_version: UI_SCHEMA_VERSION,
    timestamp: Date.now(),
    trigger,
    label,
    description,
  };
}

/**
 * Calculate approximate snapshot size
 */
export function estimateSnapshotSize(snapshot: UIStateSnapshot): number {
  try {
    return new Blob([JSON.stringify(snapshot)]).size;
  } catch {
    // Fallback for SSR
    return JSON.stringify(snapshot).length * 2;
  }
}

/**
 * Prune old snapshots to meet max limit
 */
export function pruneSnapshots(
  snapshots: Record<string, UIStateSnapshot>,
  order: string[],
  maxSnapshots: number
): { snapshots: Record<string, UIStateSnapshot>; order: string[] } {
  if (order.length <= maxSnapshots) {
    return { snapshots, order };
  }

  const toRemove = order.slice(0, order.length - maxSnapshots);
  const newSnapshots = { ...snapshots };
  toRemove.forEach(id => delete newSnapshots[id]);

  return {
    snapshots: newSnapshots,
    order: order.slice(order.length - maxSnapshots),
  };
}
