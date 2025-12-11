/**
 * MAGNET UI Contexts
 *
 * React context providers for cross-component state.
 */

// SpatialOcclusionContext - Window occlusion management
export {
  SpatialOcclusionProvider,
  useSpatialOcclusion,
  default as SpatialOcclusionContext,
} from './SpatialOcclusionContext';

// Re-export types
export type {
  SpatialOcclusionContextValue,
  SpatialOcclusionProviderProps,
} from './SpatialOcclusionContext';
