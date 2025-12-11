/**
 * MAGNET UI - Main Entry Point
 *
 * VisionOS Premium Design System v2.0
 * UI Modules 01-04 Alpha Agent Implementation
 *
 * This module provides:
 * - Core visual components (FloatingMicroWindow, PillButton, GlassCard, OrbPresence)
 * - Domain-bounded state stores with UIStoreContract
 * - UIOrchestrator message broker for state management
 * - UIStateReconciler for backend synchronization
 * - Lifecycle-aware animation hooks
 * - VisionOS design tokens and styles
 */

// =============================================================================
// Types
// =============================================================================

export * from './types';

// =============================================================================
// Styles
// =============================================================================

// Import styles via CSS (consumers should import './styles/index.css')
// Styles are exported as CSS modules with the components

// =============================================================================
// Systems
// =============================================================================

export * from './systems';

// =============================================================================
// Stores
// =============================================================================

export * from './stores/contracts/StoreFactory';
export * from './stores/contracts/UIStoreContract';
export * from './stores/context/errorStore';
export * from './stores/context/snapshotStore';
export * from './stores/geometry/geometryStore';
export * from './stores/geometry/viewportStore';
export * from './stores/domain';

// =============================================================================
// Hooks
// =============================================================================

export * from './hooks';

// =============================================================================
// Components
// =============================================================================

export * from './components';

// =============================================================================
// Version
// =============================================================================

export { UI_SCHEMA_VERSION } from './types/schema-version';
