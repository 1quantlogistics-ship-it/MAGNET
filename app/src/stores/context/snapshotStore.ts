/**
 * MAGNET UI Snapshot Store
 *
 * Manages UI state snapshots for version playback and session recovery.
 */

import { createStore } from '../contracts/StoreFactory';
import type {
  SnapshotStoreState,
  UIStateSnapshot,
  SnapshotMeta,
  SnapshotTrigger,
  SnapshotConfig,
} from '../../types/snapshot';
import {
  INITIAL_SNAPSHOT_STORE_STATE,
  DEFAULT_SNAPSHOT_CONFIG,
  createSnapshotMeta,
  pruneSnapshots,
  estimateSnapshotSize,
} from '../../types/snapshot';

/**
 * Create the snapshot store
 */
export const snapshotStore = createStore<SnapshotStoreState>({
  name: 'snapshot',
  initialState: INITIAL_SNAPSHOT_STORE_STATE,
  readOnlyFields: ['snapshots', 'snapshotOrder'],
  readWriteFields: [
    'activeSnapshotId',
    'isPlaybackMode',
    'config',
    'lastAutoSnapshotTimestamp',
  ],
});

// ============================================================================
// Snapshot Actions
// ============================================================================

/**
 * Create a new snapshot
 */
export function createSnapshot(
  trigger: SnapshotTrigger,
  snapshotData: Omit<UIStateSnapshot, 'meta'>,
  options?: { label?: string; description?: string }
): string {
  const meta = createSnapshotMeta(trigger, options?.label, options?.description);

  const snapshot: UIStateSnapshot = {
    meta: {
      ...meta,
      sizeBytes: 0, // Will be calculated
    },
    ...snapshotData,
  };

  // Calculate size
  snapshot.meta.sizeBytes = estimateSnapshotSize(snapshot);

  snapshotStore.getState()._update((state) => {
    const { snapshots: prunedSnapshots, order: prunedOrder } = pruneSnapshots(
      { ...state.snapshots, [meta.id]: snapshot },
      [...state.snapshotOrder, meta.id],
      state.config.maxSnapshots
    );

    return {
      snapshots: prunedSnapshots,
      snapshotOrder: prunedOrder,
      lastAutoSnapshotTimestamp:
        trigger === 'auto' ? Date.now() : state.lastAutoSnapshotTimestamp,
    };
  });

  return meta.id;
}

/**
 * Delete a snapshot
 */
export function deleteSnapshot(snapshotId: string): void {
  snapshotStore.getState()._update((state) => {
    if (!state.snapshots[snapshotId]) return {};

    const { [snapshotId]: _, ...rest } = state.snapshots;
    const order = state.snapshotOrder.filter((id) => id !== snapshotId);

    return {
      snapshots: rest,
      snapshotOrder: order,
      activeSnapshotId:
        state.activeSnapshotId === snapshotId ? null : state.activeSnapshotId,
    };
  });
}

/**
 * Update snapshot metadata
 */
export function updateSnapshotMeta(
  snapshotId: string,
  updates: Partial<Pick<SnapshotMeta, 'label' | 'description'>>
): void {
  snapshotStore.getState()._update((state) => {
    const snapshot = state.snapshots[snapshotId];
    if (!snapshot) return {};

    return {
      snapshots: {
        ...state.snapshots,
        [snapshotId]: {
          ...snapshot,
          meta: {
            ...snapshot.meta,
            ...updates,
          },
        },
      },
    };
  });
}

/**
 * Enter playback mode with a specific snapshot
 */
export function enterPlaybackMode(snapshotId: string): UIStateSnapshot | null {
  const state = snapshotStore.getState().readOnly;
  const snapshot = state.snapshots[snapshotId];

  if (!snapshot) {
    console.warn(`[SnapshotStore] Snapshot "${snapshotId}" not found`);
    return null;
  }

  snapshotStore.getState()._update(() => ({
    isPlaybackMode: true,
    activeSnapshotId: snapshotId,
  }));

  return snapshot;
}

/**
 * Exit playback mode
 */
export function exitPlaybackMode(): void {
  snapshotStore.getState()._update(() => ({
    isPlaybackMode: false,
    activeSnapshotId: null,
  }));
}

/**
 * Navigate to adjacent snapshot in playback mode
 */
export function navigateSnapshot(
  direction: 'prev' | 'next'
): UIStateSnapshot | null {
  const state = snapshotStore.getState().readOnly;

  if (!state.isPlaybackMode || !state.activeSnapshotId) {
    return null;
  }

  const currentIndex = state.snapshotOrder.indexOf(state.activeSnapshotId);
  if (currentIndex === -1) return null;

  const newIndex =
    direction === 'prev'
      ? Math.max(0, currentIndex - 1)
      : Math.min(state.snapshotOrder.length - 1, currentIndex + 1);

  if (newIndex === currentIndex) return null;

  const newSnapshotId = state.snapshotOrder[newIndex];
  const snapshot = state.snapshots[newSnapshotId];

  snapshotStore.getState()._update(() => ({
    activeSnapshotId: newSnapshotId,
  }));

  return snapshot || null;
}

/**
 * Update snapshot configuration
 */
export function updateSnapshotConfig(
  updates: Partial<SnapshotConfig>
): void {
  snapshotStore.getState()._update((state) => ({
    config: {
      ...state.config,
      ...updates,
    },
  }));
}

/**
 * Clear all snapshots
 */
export function clearAllSnapshots(): void {
  snapshotStore.getState()._update(() => ({
    snapshots: {},
    snapshotOrder: [],
    activeSnapshotId: null,
    isPlaybackMode: false,
  }));
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get a snapshot by ID
 */
export function getSnapshot(snapshotId: string): UIStateSnapshot | null {
  return snapshotStore.getState().readOnly.snapshots[snapshotId] || null;
}

/**
 * Get all snapshots in chronological order
 */
export function getAllSnapshots(): UIStateSnapshot[] {
  const state = snapshotStore.getState().readOnly;
  return state.snapshotOrder
    .map((id) => state.snapshots[id])
    .filter((s): s is UIStateSnapshot => s !== undefined);
}

/**
 * Get snapshots by trigger type
 */
export function getSnapshotsByTrigger(
  trigger: SnapshotTrigger
): UIStateSnapshot[] {
  return getAllSnapshots().filter(
    (snapshot) => snapshot.meta.trigger === trigger
  );
}

/**
 * Get the active snapshot (in playback mode)
 */
export function getActiveSnapshot(): UIStateSnapshot | null {
  const state = snapshotStore.getState().readOnly;
  if (!state.activeSnapshotId) return null;
  return state.snapshots[state.activeSnapshotId] || null;
}

/**
 * Get snapshot count
 */
export function getSnapshotCount(): number {
  return snapshotStore.getState().readOnly.snapshotOrder.length;
}

/**
 * Check if auto-snapshot is due
 */
export function isAutoSnapshotDue(): boolean {
  const state = snapshotStore.getState().readOnly;
  const { config, lastAutoSnapshotTimestamp } = state;

  if (config.autoSnapshotInterval === 0) return false;

  return Date.now() - lastAutoSnapshotTimestamp >= config.autoSnapshotInterval;
}

/**
 * Get playback position (index and total)
 */
export function getPlaybackPosition(): { current: number; total: number } | null {
  const state = snapshotStore.getState().readOnly;

  if (!state.isPlaybackMode || !state.activeSnapshotId) {
    return null;
  }

  const currentIndex = state.snapshotOrder.indexOf(state.activeSnapshotId);
  if (currentIndex === -1) return null;

  return {
    current: currentIndex + 1,
    total: state.snapshotOrder.length,
  };
}

/**
 * Calculate total storage used by snapshots
 */
export function getTotalSnapshotSize(): number {
  const snapshots = getAllSnapshots();
  return snapshots.reduce(
    (total, snapshot) => total + (snapshot.meta.sizeBytes || 0),
    0
  );
}
