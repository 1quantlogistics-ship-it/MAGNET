/**
 * MAGNET UI Geometry Store
 *
 * Authoritative mesh data (synced from backend).
 * Split from viewport per FM7 architectural fix.
 */

import { createStore } from '../contracts/StoreFactory';
import type {
  GeometryState,
  MeshData,
  MeshVisibility,
  BoundingBox3D,
} from '../../types/geometry';
import { INITIAL_GEOMETRY_STATE, getBoundingBoxCenter } from '../../types/geometry';
import type { Point3D } from '../../types/common';
import { UI_SCHEMA_VERSION } from '../../types/schema-version';

/**
 * Create the geometry store
 */
export const geometryStore = createStore<GeometryState>({
  name: 'geometry',
  initialState: INITIAL_GEOMETRY_STATE,
  // These come from backend and should not be locally modified
  readOnlyFields: [
    'schema_version',
    'meshes',
    'rootMeshIds',
    'sceneBounds',
    'geometryHash',
    'lastSyncTimestamp',
  ],
  // UI can modify selection and visibility
  readWriteFields: [
    'selectedMeshIds',
    'highlightedMeshId',
    'emphasizedMeshIds',
    'visibilityOverrides',
    'isLoading',
    'loadingProgress',
  ],
  // Custom reconciliation from backend
  reconcileTransform: (source, current) => {
    return {
      ...current,
      ...source,
      // Preserve UI state when reconciling
      selectedMeshIds: current.selectedMeshIds,
      highlightedMeshId: current.highlightedMeshId,
      emphasizedMeshIds: current.emphasizedMeshIds,
      visibilityOverrides: current.visibilityOverrides,
    };
  },
});

// ============================================================================
// Selection Actions
// ============================================================================

/**
 * Select mesh(es)
 */
export function selectMeshes(
  meshIds: string[],
  mode: 'replace' | 'add' | 'toggle' = 'replace'
): void {
  geometryStore.getState()._update((state) => {
    let newSelection: string[];

    switch (mode) {
      case 'replace':
        newSelection = meshIds;
        break;
      case 'add':
        newSelection = [...new Set([...state.selectedMeshIds, ...meshIds])];
        break;
      case 'toggle':
        const currentSet = new Set(state.selectedMeshIds);
        for (const id of meshIds) {
          if (currentSet.has(id)) {
            currentSet.delete(id);
          } else {
            currentSet.add(id);
          }
        }
        newSelection = Array.from(currentSet);
        break;
    }

    return { selectedMeshIds: newSelection };
  });
}

/**
 * Clear mesh selection
 */
export function clearSelection(): void {
  geometryStore.getState()._update(() => ({
    selectedMeshIds: [],
  }));
}

/**
 * Set highlighted mesh (hover state)
 */
export function setHighlightedMesh(meshId: string | null): void {
  geometryStore.getState()._update(() => ({
    highlightedMeshId: meshId,
  }));
}

/**
 * Set emphasized meshes (from ARS, etc.)
 */
export function setEmphasizedMeshes(meshIds: string[]): void {
  geometryStore.getState()._update(() => ({
    emphasizedMeshIds: meshIds,
  }));
}

/**
 * Clear emphasized meshes
 */
export function clearEmphasizedMeshes(): void {
  geometryStore.getState()._update(() => ({
    emphasizedMeshIds: [],
  }));
}

// ============================================================================
// Visibility Actions
// ============================================================================

/**
 * Set visibility override for a mesh
 */
export function setMeshVisibility(
  meshId: string,
  visibility: MeshVisibility | null
): void {
  geometryStore.getState()._update((state) => {
    const overrides = { ...state.visibilityOverrides };

    if (visibility === null) {
      delete overrides[meshId];
    } else {
      overrides[meshId] = visibility;
    }

    return { visibilityOverrides: overrides };
  });
}

/**
 * Set visibility for multiple meshes
 */
export function setMeshesVisibility(
  meshIds: string[],
  visibility: MeshVisibility | null
): void {
  geometryStore.getState()._update((state) => {
    const overrides = { ...state.visibilityOverrides };

    for (const meshId of meshIds) {
      if (visibility === null) {
        delete overrides[meshId];
      } else {
        overrides[meshId] = visibility;
      }
    }

    return { visibilityOverrides: overrides };
  });
}

/**
 * Clear all visibility overrides
 */
export function clearVisibilityOverrides(): void {
  geometryStore.getState()._update(() => ({
    visibilityOverrides: {},
  }));
}

/**
 * Hide selected meshes
 */
export function hideSelectedMeshes(): void {
  const state = geometryStore.getState().readOnly;
  setMeshesVisibility(state.selectedMeshIds, 'hidden');
}

/**
 * Show only selected meshes (isolate)
 */
export function isolateSelectedMeshes(): void {
  const state = geometryStore.getState().readOnly;
  const selectedSet = new Set(state.selectedMeshIds);

  geometryStore.getState()._update((state) => {
    const overrides: Record<string, MeshVisibility> = {};

    for (const meshId of Object.keys(state.meshes)) {
      if (!selectedSet.has(meshId)) {
        overrides[meshId] = 'hidden';
      }
    }

    return { visibilityOverrides: overrides };
  });
}

/**
 * Show all meshes
 */
export function showAllMeshes(): void {
  clearVisibilityOverrides();
}

// ============================================================================
// Loading State Actions
// ============================================================================

/**
 * Set loading state
 */
export function setLoading(isLoading: boolean, progress: number = 0): void {
  geometryStore.getState()._update(() => ({
    isLoading,
    loadingProgress: isLoading ? progress : 0,
  }));
}

/**
 * Update loading progress
 */
export function updateLoadingProgress(progress: number): void {
  geometryStore.getState()._update(() => ({
    loadingProgress: Math.min(100, Math.max(0, progress)),
  }));
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get mesh by ID
 */
export function getMesh(meshId: string): MeshData | null {
  return geometryStore.getState().readOnly.meshes[meshId] || null;
}

/**
 * Get all meshes
 */
export function getAllMeshes(): MeshData[] {
  return Object.values(geometryStore.getState().readOnly.meshes);
}

/**
 * Get root meshes (no parent)
 */
export function getRootMeshes(): MeshData[] {
  const state = geometryStore.getState().readOnly;
  return state.rootMeshIds
    .map((id) => state.meshes[id])
    .filter((m): m is MeshData => m !== undefined);
}

/**
 * Get children of a mesh
 */
export function getChildMeshes(parentId: string): MeshData[] {
  return getAllMeshes().filter((mesh) => mesh.parentId === parentId);
}

/**
 * Get selected meshes
 */
export function getSelectedMeshes(): MeshData[] {
  const state = geometryStore.getState().readOnly;
  return state.selectedMeshIds
    .map((id) => state.meshes[id])
    .filter((m): m is MeshData => m !== undefined);
}

/**
 * Get emphasized meshes
 */
export function getEmphasizedMeshes(): MeshData[] {
  const state = geometryStore.getState().readOnly;
  return state.emphasizedMeshIds
    .map((id) => state.meshes[id])
    .filter((m): m is MeshData => m !== undefined);
}

/**
 * Get effective visibility of a mesh (with override)
 */
export function getEffectiveVisibility(meshId: string): MeshVisibility {
  const state = geometryStore.getState().readOnly;

  // Check override first
  if (state.visibilityOverrides[meshId]) {
    return state.visibilityOverrides[meshId];
  }

  // Fall back to mesh's default visibility
  const mesh = state.meshes[meshId];
  return mesh?.visibility || 'visible';
}

/**
 * Get scene bounds
 */
export function getSceneBounds(): BoundingBox3D | null {
  return geometryStore.getState().readOnly.sceneBounds;
}

/**
 * Get scene center
 */
export function getSceneCenter(): Point3D | null {
  const bounds = getSceneBounds();
  return bounds ? getBoundingBoxCenter(bounds) : null;
}

/**
 * Check if mesh is selected
 */
export function isMeshSelected(meshId: string): boolean {
  return geometryStore.getState().readOnly.selectedMeshIds.includes(meshId);
}

/**
 * Check if mesh is highlighted
 */
export function isMeshHighlighted(meshId: string): boolean {
  return geometryStore.getState().readOnly.highlightedMeshId === meshId;
}

/**
 * Check if mesh is emphasized
 */
export function isMeshEmphasized(meshId: string): boolean {
  return geometryStore.getState().readOnly.emphasizedMeshIds.includes(meshId);
}

/**
 * Get mesh count
 */
export function getMeshCount(): number {
  return Object.keys(geometryStore.getState().readOnly.meshes).length;
}

/**
 * Check if geometry is loaded
 */
export function isGeometryLoaded(): boolean {
  const state = geometryStore.getState().readOnly;
  return !state.isLoading && state.geometryHash !== '';
}

/**
 * Get current geometry hash
 */
export function getGeometryHash(): string {
  return geometryStore.getState().readOnly.geometryHash;
}
