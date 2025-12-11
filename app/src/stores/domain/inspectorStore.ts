/**
 * MAGNET UI Inspector Store
 *
 * Inspector panel state management for component inspection.
 * Uses StoreFactory for domain-bounded store with read-only/read-write separation.
 */

import { createStore } from '../contracts/StoreFactory';
import { UI_SCHEMA_VERSION } from '../../types/schema-version';
import type { UISchemaVersion } from '../../types/schema-version';

/**
 * Inspector tab types
 */
export type InspectorTab = 'properties' | 'hierarchy' | 'materials' | 'constraints' | 'history';

/**
 * Property value types
 */
export type PropertyValue = string | number | boolean | null | undefined;

/**
 * Property definition
 */
export interface PropertyDefinition {
  id: string;
  name: string;
  category: string;
  value: PropertyValue;
  unit?: string;
  editable: boolean;
  type: 'string' | 'number' | 'boolean' | 'enum' | 'color' | 'vector';
  enumOptions?: string[];
  min?: number;
  max?: number;
  step?: number;
  description?: string;
}

/**
 * Hierarchy node
 */
export interface HierarchyNode {
  id: string;
  name: string;
  type: string;
  parentId: string | null;
  childIds: string[];
  depth: number;
  isExpanded: boolean;
  isSelected: boolean;
  icon?: string;
}

/**
 * History entry
 */
export interface HistoryEntry {
  id: string;
  timestamp: number;
  action: string;
  description: string;
  componentId: string;
  previousValue?: PropertyValue;
  newValue?: PropertyValue;
  undoable: boolean;
}

/**
 * Inspector read-only state (synced from backend)
 */
export interface InspectorReadOnlyState {
  schema_version: UISchemaVersion;

  /** Currently inspected component ID */
  inspectedComponentId: string | null;

  /** Component name */
  componentName: string;

  /** Component type */
  componentType: string;

  /** Properties of the inspected component */
  properties: PropertyDefinition[];

  /** Property categories */
  propertyCategories: string[];

  /** Hierarchy nodes */
  hierarchyNodes: HierarchyNode[];

  /** Root hierarchy node IDs */
  rootNodeIds: string[];

  /** Change history */
  history: HistoryEntry[];

  /** Last sync timestamp */
  lastSyncTimestamp: number;
}

/**
 * Inspector read-write state (UI-only)
 */
export interface InspectorReadWriteState {
  /** Currently active tab */
  activeTab: InspectorTab;

  /** Expanded property categories */
  expandedCategories: string[];

  /** Expanded hierarchy node IDs */
  expandedNodeIds: string[];

  /** Search query for properties */
  searchQuery: string;

  /** Show only editable properties */
  showEditableOnly: boolean;

  /** Property editing in progress */
  editingPropertyId: string | null;

  /** Pending property value (before commit) */
  pendingPropertyValue: PropertyValue;

  /** Inspector panel width */
  panelWidth: number;

  /** Show hierarchy panel */
  showHierarchy: boolean;

  /** Show history panel */
  showHistory: boolean;

  /** Loading state */
  isLoading: boolean;
}

/**
 * Combined inspector store state
 */
export interface InspectorStoreState extends InspectorReadOnlyState, InspectorReadWriteState {}

/**
 * Initial inspector state
 */
const initialInspectorState: InspectorStoreState = {
  schema_version: UI_SCHEMA_VERSION,
  inspectedComponentId: null,
  componentName: '',
  componentType: '',
  properties: [],
  propertyCategories: [],
  hierarchyNodes: [],
  rootNodeIds: [],
  history: [],
  lastSyncTimestamp: 0,
  activeTab: 'properties',
  expandedCategories: [],
  expandedNodeIds: [],
  searchQuery: '',
  showEditableOnly: false,
  editingPropertyId: null,
  pendingPropertyValue: null,
  panelWidth: 320,
  showHierarchy: true,
  showHistory: false,
  isLoading: false,
};

/**
 * Create the inspector store
 */
export const inspectorStore = createStore<InspectorStoreState>({
  name: 'inspector',
  initialState: initialInspectorState,
  readOnlyFields: [
    'schema_version',
    'inspectedComponentId',
    'componentName',
    'componentType',
    'properties',
    'propertyCategories',
    'hierarchyNodes',
    'rootNodeIds',
    'history',
    'lastSyncTimestamp',
  ],
  readWriteFields: [
    'activeTab',
    'expandedCategories',
    'expandedNodeIds',
    'searchQuery',
    'showEditableOnly',
    'editingPropertyId',
    'pendingPropertyValue',
    'panelWidth',
    'showHierarchy',
    'showHistory',
    'isLoading',
  ],
});

// ============================================================================
// Actions
// ============================================================================

/**
 * Set active tab
 */
export function setActiveTab(tab: InspectorTab): void {
  inspectorStore.getState()._update(() => ({
    activeTab: tab,
  }));
}

/**
 * Toggle category expansion
 */
export function toggleCategory(category: string): void {
  inspectorStore.getState()._update((state) => {
    const isExpanded = state.expandedCategories.includes(category);
    return {
      expandedCategories: isExpanded
        ? state.expandedCategories.filter((c) => c !== category)
        : [...state.expandedCategories, category],
    };
  });
}

/**
 * Expand all categories
 */
export function expandAllCategories(): void {
  const categories = inspectorStore.getState().readOnly.propertyCategories;
  inspectorStore.getState()._update(() => ({
    expandedCategories: [...categories],
  }));
}

/**
 * Collapse all categories
 */
export function collapseAllCategories(): void {
  inspectorStore.getState()._update(() => ({
    expandedCategories: [],
  }));
}

/**
 * Toggle hierarchy node expansion
 */
export function toggleHierarchyNode(nodeId: string): void {
  inspectorStore.getState()._update((state) => {
    const isExpanded = state.expandedNodeIds.includes(nodeId);
    return {
      expandedNodeIds: isExpanded
        ? state.expandedNodeIds.filter((id) => id !== nodeId)
        : [...state.expandedNodeIds, nodeId],
    };
  });
}

/**
 * Set search query
 */
export function setSearchQuery(query: string): void {
  inspectorStore.getState()._update(() => ({
    searchQuery: query,
  }));
}

/**
 * Toggle editable only filter
 */
export function toggleEditableOnly(): void {
  inspectorStore.getState()._update((state) => ({
    showEditableOnly: !state.showEditableOnly,
  }));
}

/**
 * Start editing a property
 */
export function startPropertyEdit(propertyId: string): void {
  const property = inspectorStore
    .getState()
    .readOnly.properties.find((p) => p.id === propertyId);

  if (property?.editable) {
    inspectorStore.getState()._update(() => ({
      editingPropertyId: propertyId,
      pendingPropertyValue: property.value,
    }));
  }
}

/**
 * Update pending property value
 */
export function updatePendingValue(value: PropertyValue): void {
  inspectorStore.getState()._update(() => ({
    pendingPropertyValue: value,
  }));
}

/**
 * Cancel property edit
 */
export function cancelPropertyEdit(): void {
  inspectorStore.getState()._update(() => ({
    editingPropertyId: null,
    pendingPropertyValue: null,
  }));
}

/**
 * Set panel width
 */
export function setPanelWidth(width: number): void {
  inspectorStore.getState()._update(() => ({
    panelWidth: Math.max(240, Math.min(600, width)),
  }));
}

/**
 * Toggle hierarchy panel visibility
 */
export function toggleHierarchy(): void {
  inspectorStore.getState()._update((state) => ({
    showHierarchy: !state.showHierarchy,
  }));
}

/**
 * Toggle history panel visibility
 */
export function toggleHistory(): void {
  inspectorStore.getState()._update((state) => ({
    showHistory: !state.showHistory,
  }));
}

/**
 * Set loading state
 */
export function setInspectorLoading(isLoading: boolean): void {
  inspectorStore.getState()._update(() => ({
    isLoading,
  }));
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get current inspected component info
 */
export function getInspectedComponent(): {
  id: string | null;
  name: string;
  type: string;
} {
  const state = inspectorStore.getState().readOnly;
  return {
    id: state.inspectedComponentId,
    name: state.componentName,
    type: state.componentType,
  };
}

/**
 * Get filtered properties
 */
export function getFilteredProperties(): PropertyDefinition[] {
  const state = inspectorStore.getState().readOnly;
  let filtered = [...state.properties];

  // Apply search filter
  if (state.searchQuery) {
    const query = state.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (p) =>
        p.name.toLowerCase().includes(query) ||
        p.category.toLowerCase().includes(query) ||
        String(p.value).toLowerCase().includes(query)
    );
  }

  // Apply editable filter
  if (state.showEditableOnly) {
    filtered = filtered.filter((p) => p.editable);
  }

  return filtered;
}

/**
 * Get properties grouped by category
 */
export function getPropertiesByCategory(): Map<string, PropertyDefinition[]> {
  const properties = getFilteredProperties();
  const grouped = new Map<string, PropertyDefinition[]>();

  for (const prop of properties) {
    const existing = grouped.get(prop.category) ?? [];
    grouped.set(prop.category, [...existing, prop]);
  }

  return grouped;
}

/**
 * Get hierarchy tree
 */
export function getHierarchyTree(): HierarchyNode[] {
  const state = inspectorStore.getState().readOnly;
  return state.rootNodeIds
    .map((id) => state.hierarchyNodes.find((n) => n.id === id))
    .filter((n): n is HierarchyNode => n !== undefined);
}

/**
 * Get children of a hierarchy node
 */
export function getNodeChildren(nodeId: string): HierarchyNode[] {
  const state = inspectorStore.getState().readOnly;
  const node = state.hierarchyNodes.find((n) => n.id === nodeId);
  if (!node) return [];

  return node.childIds
    .map((id) => state.hierarchyNodes.find((n) => n.id === id))
    .filter((n): n is HierarchyNode => n !== undefined);
}

/**
 * Check if a category is expanded
 */
export function isCategoryExpanded(category: string): boolean {
  return inspectorStore.getState().readOnly.expandedCategories.includes(category);
}

/**
 * Check if a hierarchy node is expanded
 */
export function isNodeExpanded(nodeId: string): boolean {
  return inspectorStore.getState().readOnly.expandedNodeIds.includes(nodeId);
}

/**
 * Get property by ID
 */
export function getPropertyById(propertyId: string): PropertyDefinition | null {
  return (
    inspectorStore.getState().readOnly.properties.find((p) => p.id === propertyId) ??
    null
  );
}

/**
 * Get recent history entries
 */
export function getRecentHistory(limit: number = 10): HistoryEntry[] {
  return inspectorStore.getState().readOnly.history.slice(0, limit);
}

/**
 * Check if currently editing
 */
export function isEditing(): boolean {
  return inspectorStore.getState().readOnly.editingPropertyId !== null;
}

/**
 * Get editing state
 */
export function getEditingState(): {
  propertyId: string | null;
  pendingValue: PropertyValue;
} {
  const state = inspectorStore.getState().readOnly;
  return {
    propertyId: state.editingPropertyId,
    pendingValue: state.pendingPropertyValue,
  };
}
