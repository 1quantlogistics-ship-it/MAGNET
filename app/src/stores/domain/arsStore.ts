/**
 * MAGNET UI ARS Store
 *
 * Auto Recommendation System state management.
 * Uses StoreFactory for domain-bounded store with read-only/read-write separation.
 */

import { createStore } from '../contracts/StoreFactory';
import type {
  ARSRecommendation,
  ARSCategory,
  ARSPriority,
  ARSReadOnlyState,
  ARSReadWriteState,
} from '../../types/ars';
import { UI_SCHEMA_VERSION } from '../../types/schema-version';

/**
 * Combined ARS store state
 */
export interface ARSStoreState extends ARSReadOnlyState, ARSReadWriteState {}

/**
 * Initial ARS state
 */
const initialARSState: ARSStoreState = {
  schema_version: UI_SCHEMA_VERSION,
  recommendations: [],
  lastSyncTimestamp: 0,
  totalCount: 0,
  pendingCount: 0,
  appliedCount: 0,
  dismissedCount: 0,
  selectedRecommendationId: null,
  expandedRecommendationIds: [],
  filterCategory: null,
  filterPriority: null,
  sortBy: 'priority',
  sortDirection: 'desc',
  isLoading: false,
};

/**
 * Create the ARS store
 */
export const arsStore = createStore<ARSStoreState>({
  name: 'ars',
  initialState: initialARSState,
  readOnlyFields: [
    'schema_version',
    'recommendations',
    'lastSyncTimestamp',
    'totalCount',
    'pendingCount',
    'appliedCount',
    'dismissedCount',
  ],
  readWriteFields: [
    'selectedRecommendationId',
    'expandedRecommendationIds',
    'filterCategory',
    'filterPriority',
    'sortBy',
    'sortDirection',
    'isLoading',
  ],
});

// ============================================================================
// Actions
// ============================================================================

/**
 * Select a recommendation
 */
export function selectRecommendation(id: string | null): void {
  arsStore.getState()._update(() => ({
    selectedRecommendationId: id,
  }));
}

/**
 * Toggle recommendation expansion
 */
export function toggleRecommendationExpansion(id: string): void {
  arsStore.getState()._update((state) => {
    const isExpanded = state.expandedRecommendationIds.includes(id);
    return {
      expandedRecommendationIds: isExpanded
        ? state.expandedRecommendationIds.filter((i) => i !== id)
        : [...state.expandedRecommendationIds, id],
    };
  });
}

/**
 * Expand a recommendation
 */
export function expandRecommendation(id: string): void {
  arsStore.getState()._update((state) => {
    if (state.expandedRecommendationIds.includes(id)) {
      return {};
    }
    return {
      expandedRecommendationIds: [...state.expandedRecommendationIds, id],
    };
  });
}

/**
 * Collapse a recommendation
 */
export function collapseRecommendation(id: string): void {
  arsStore.getState()._update((state) => ({
    expandedRecommendationIds: state.expandedRecommendationIds.filter((i) => i !== id),
  }));
}

/**
 * Collapse all recommendations
 */
export function collapseAllRecommendations(): void {
  arsStore.getState()._update(() => ({
    expandedRecommendationIds: [],
  }));
}

/**
 * Set category filter
 */
export function setFilterCategory(category: ARSCategory | null): void {
  arsStore.getState()._update(() => ({
    filterCategory: category,
  }));
}

/**
 * Set priority filter
 */
export function setFilterPriority(priority: ARSPriority | null): void {
  arsStore.getState()._update(() => ({
    filterPriority: priority,
  }));
}

/**
 * Set sort configuration
 */
export function setSortConfig(
  sortBy: 'priority' | 'timestamp' | 'impact',
  sortDirection: 'asc' | 'desc'
): void {
  arsStore.getState()._update(() => ({
    sortBy,
    sortDirection,
  }));
}

/**
 * Set loading state
 */
export function setARSLoading(isLoading: boolean): void {
  arsStore.getState()._update(() => ({
    isLoading,
  }));
}

/**
 * Clear all filters
 */
export function clearFilters(): void {
  arsStore.getState()._update(() => ({
    filterCategory: null,
    filterPriority: null,
  }));
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get all recommendations
 */
export function getRecommendations(): ARSRecommendation[] {
  return arsStore.getState().readOnly.recommendations;
}

/**
 * Get selected recommendation
 */
export function getSelectedRecommendation(): ARSRecommendation | null {
  const state = arsStore.getState().readOnly;
  if (!state.selectedRecommendationId) return null;
  return state.recommendations.find((r) => r.id === state.selectedRecommendationId) ?? null;
}

/**
 * Get filtered and sorted recommendations
 */
export function getFilteredRecommendations(): ARSRecommendation[] {
  const state = arsStore.getState().readOnly;
  let filtered = [...state.recommendations];

  // Apply category filter
  if (state.filterCategory) {
    filtered = filtered.filter((r) => r.category === state.filterCategory);
  }

  // Apply priority filter
  if (state.filterPriority) {
    filtered = filtered.filter((r) => r.priority === state.filterPriority);
  }

  // Apply sort
  const sortMultiplier = state.sortDirection === 'asc' ? 1 : -1;

  filtered.sort((a, b) => {
    switch (state.sortBy) {
      case 'priority': {
        // Priority 1 is highest, so reverse for descending
        const priorityOrder: Record<ARSPriority, number> = {
          critical: 1,
          high: 2,
          medium: 3,
          low: 4,
          info: 5,
        };
        return (priorityOrder[a.priority] - priorityOrder[b.priority]) * sortMultiplier;
      }
      case 'timestamp':
        return (a.timestamp - b.timestamp) * sortMultiplier;
      case 'impact':
        return ((a.impact?.value ?? 0) - (b.impact?.value ?? 0)) * sortMultiplier;
      default:
        return 0;
    }
  });

  return filtered;
}

/**
 * Get recommendations by category
 */
export function getRecommendationsByCategory(
  category: ARSCategory
): ARSRecommendation[] {
  return arsStore.getState().readOnly.recommendations.filter(
    (r) => r.category === category
  );
}

/**
 * Get recommendations by priority
 */
export function getRecommendationsByPriority(
  priority: ARSPriority
): ARSRecommendation[] {
  return arsStore.getState().readOnly.recommendations.filter(
    (r) => r.priority === priority
  );
}

/**
 * Check if a recommendation is expanded
 */
export function isRecommendationExpanded(id: string): boolean {
  return arsStore.getState().readOnly.expandedRecommendationIds.includes(id);
}

/**
 * Get pending recommendations count
 */
export function getPendingCount(): number {
  return arsStore.getState().readOnly.pendingCount;
}

/**
 * Get ARS summary
 */
export function getARSSummary(): {
  total: number;
  pending: number;
  applied: number;
  dismissed: number;
  byCategory: Record<ARSCategory, number>;
  byPriority: Record<ARSPriority, number>;
} {
  const state = arsStore.getState().readOnly;
  const byCategory: Record<ARSCategory, number> = {
    structural: 0,
    performance: 0,
    compliance: 0,
    cost: 0,
    manufacturing: 0,
    safety: 0,
  };
  const byPriority: Record<ARSPriority, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  };

  for (const rec of state.recommendations) {
    byCategory[rec.category]++;
    byPriority[rec.priority]++;
  }

  return {
    total: state.totalCount,
    pending: state.pendingCount,
    applied: state.appliedCount,
    dismissed: state.dismissedCount,
    byCategory,
    byPriority,
  };
}

/**
 * Check if any critical recommendations exist
 */
export function hasCriticalRecommendations(): boolean {
  return arsStore.getState().readOnly.recommendations.some(
    (r) => r.priority === 'critical' && r.status === 'pending'
  );
}
