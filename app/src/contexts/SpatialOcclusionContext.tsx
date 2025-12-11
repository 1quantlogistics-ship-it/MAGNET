/**
 * MAGNET UI Module 04: SpatialOcclusionContext
 *
 * React context for managing spatial occlusion state across windows.
 * When clarifications are active, other windows dim/blur/shift back.
 */

import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { OcclusionState, SpatialOcclusionContextValue } from '../types/clarification';

/**
 * Default occlusion state
 */
const defaultOcclusionState: OcclusionState = {
  isActive: false,
  excludeIds: [],
};

/**
 * Context with default values
 */
const SpatialOcclusionContext = createContext<SpatialOcclusionContextValue>({
  occlusion: defaultOcclusionState,
  activateOcclusion: () => {},
  releaseOcclusion: () => {},
});

/**
 * SpatialOcclusionProvider props
 */
export interface SpatialOcclusionProviderProps {
  children: React.ReactNode;
}

/**
 * SpatialOcclusionProvider component
 *
 * Provides occlusion state to all child components.
 * Use activateOcclusion when showing clarifications,
 * releaseOcclusion when dismissing them.
 */
export const SpatialOcclusionProvider: React.FC<SpatialOcclusionProviderProps> = ({
  children,
}) => {
  const [occlusion, setOcclusion] = useState<OcclusionState>(defaultOcclusionState);

  /**
   * Activate occlusion, optionally excluding certain windows
   */
  const activateOcclusion = useCallback((excludeIds: string[] = []) => {
    setOcclusion({
      isActive: true,
      excludeIds,
    });
  }, []);

  /**
   * Release occlusion
   */
  const releaseOcclusion = useCallback(() => {
    setOcclusion(defaultOcclusionState);
  }, []);

  const value = useMemo<SpatialOcclusionContextValue>(
    () => ({
      occlusion,
      activateOcclusion,
      releaseOcclusion,
    }),
    [occlusion, activateOcclusion, releaseOcclusion]
  );

  return (
    <SpatialOcclusionContext.Provider value={value}>
      {children}
    </SpatialOcclusionContext.Provider>
  );
};

/**
 * Hook to access spatial occlusion context
 */
export function useSpatialOcclusion(): SpatialOcclusionContextValue {
  const context = useContext(SpatialOcclusionContext);

  if (!context) {
    throw new Error(
      'useSpatialOcclusion must be used within a SpatialOcclusionProvider'
    );
  }

  return context;
}

export default SpatialOcclusionContext;
