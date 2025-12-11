/**
 * useAnnotations.ts - Annotation CRUD hook v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Manages 3D annotations with persistence to backend.
 * Addresses: FM6 (Annotation persistence)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { Annotation3D, AnnotationCategory, Measurement3D } from '../types/schema';

// =============================================================================
// TYPES
// =============================================================================

export interface UseAnnotationsOptions {
  phaseFilter?: string;
  categoryFilter?: AnnotationCategory;
  componentFilter?: string;
  visibleOnly?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  baseUrl?: string;
}

export interface UseAnnotationsResult {
  annotations: Annotation3D[];
  isLoading: boolean;
  error: Error | null;
  create: (annotation: Partial<Annotation3D>) => Promise<Annotation3D | null>;
  update: (annotation: Annotation3D) => Promise<Annotation3D | null>;
  remove: (annotationId: string) => Promise<boolean>;
  linkToDecision: (annotationId: string, decisionId: string) => Promise<boolean>;
  refresh: () => Promise<void>;
}

export interface CreateAnnotationInput {
  position: [number, number, number];
  normal?: [number, number, number] | null;
  label: string;
  description?: string;
  category?: AnnotationCategory;
  measurement?: Measurement3D | null;
  linked_phase?: string;
  linked_component?: string;
  color?: string;
  icon?: string;
}

// =============================================================================
// HOOK
// =============================================================================

export function useAnnotations(
  designId: string,
  options: UseAnnotationsOptions = {},
): UseAnnotationsResult {
  const {
    phaseFilter,
    categoryFilter,
    componentFilter,
    visibleOnly = false,
    autoRefresh = false,
    refreshInterval = 30000,
    baseUrl = '/api/v1',
  } = options;

  const [annotations, setAnnotations] = useState<Annotation3D[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Fetch annotations
  const fetchAnnotations = useCallback(async (): Promise<void> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    setError(null);

    try {
      // Build query params
      const params = new URLSearchParams();
      if (phaseFilter) params.set('phase_filter', phaseFilter);
      if (categoryFilter) params.set('category_filter', categoryFilter);
      if (componentFilter) params.set('component_filter', componentFilter);
      if (visibleOnly) params.set('visible_only', 'true');

      const url = `${baseUrl}/designs/${designId}/annotations?${params}`;

      const response = await fetch(url, {
        signal: abortControllerRef.current.signal,
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: Annotation3D[] = await response.json();
      setAnnotations(data);

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      console.error('Failed to fetch annotations:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setIsLoading(false);
    }
  }, [designId, phaseFilter, categoryFilter, componentFilter, visibleOnly, baseUrl]);

  // Initial fetch
  useEffect(() => {
    fetchAnnotations();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchAnnotations]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(fetchAnnotations, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchAnnotations]);

  // Create annotation
  const create = useCallback(async (
    input: Partial<Annotation3D>,
  ): Promise<Annotation3D | null> => {
    try {
      const url = `${baseUrl}/designs/${designId}/annotations`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          design_id: designId,
          ...input,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const annotation: Annotation3D = await response.json();

      // Add to local state
      setAnnotations((prev) => [annotation, ...prev]);

      return annotation;

    } catch (err) {
      console.error('Failed to create annotation:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      return null;
    }
  }, [designId, baseUrl]);

  // Update annotation
  const update = useCallback(async (
    annotation: Annotation3D,
  ): Promise<Annotation3D | null> => {
    try {
      const url = `${baseUrl}/designs/${designId}/annotations/${annotation.annotation_id}`;

      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(annotation),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const updated: Annotation3D = await response.json();

      // Update local state
      setAnnotations((prev) =>
        prev.map((a) => a.annotation_id === updated.annotation_id ? updated : a),
      );

      return updated;

    } catch (err) {
      console.error('Failed to update annotation:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      return null;
    }
  }, [designId, baseUrl]);

  // Delete annotation
  const remove = useCallback(async (annotationId: string): Promise<boolean> => {
    try {
      const url = `${baseUrl}/designs/${designId}/annotations/${annotationId}`;

      const response = await fetch(url, {
        method: 'DELETE',
      });

      if (!response.ok && response.status !== 204) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // Remove from local state
      setAnnotations((prev) =>
        prev.filter((a) => a.annotation_id !== annotationId),
      );

      return true;

    } catch (err) {
      console.error('Failed to delete annotation:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      return false;
    }
  }, [designId, baseUrl]);

  // Link annotation to decision
  const linkToDecision = useCallback(async (
    annotationId: string,
    decisionId: string,
  ): Promise<boolean> => {
    try {
      const url = `${baseUrl}/designs/${designId}/annotations/${annotationId}/link-decision`;

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ decision_id: decisionId }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const updated: Annotation3D = await response.json();

      // Update local state
      setAnnotations((prev) =>
        prev.map((a) => a.annotation_id === annotationId ? updated : a),
      );

      return true;

    } catch (err) {
      console.error('Failed to link annotation to decision:', err);
      setError(err instanceof Error ? err : new Error('Unknown error'));
      return false;
    }
  }, [designId, baseUrl]);

  return {
    annotations,
    isLoading,
    error,
    create,
    update,
    remove,
    linkToDecision,
    refresh: fetchAnnotations,
  };
}

// =============================================================================
// SELECTED ANNOTATION HOOK
// =============================================================================

export interface UseSelectedAnnotationResult {
  selectedId: string | null;
  selectedAnnotation: Annotation3D | null;
  select: (annotationId: string | null) => void;
  isSelected: (annotationId: string) => boolean;
}

/**
 * Manage annotation selection state.
 */
export function useSelectedAnnotation(
  annotations: Annotation3D[],
): UseSelectedAnnotationResult {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selectedAnnotation = annotations.find(
    (a) => a.annotation_id === selectedId,
  ) || null;

  const select = useCallback((annotationId: string | null) => {
    setSelectedId(annotationId);
  }, []);

  const isSelected = useCallback((annotationId: string): boolean => {
    return selectedId === annotationId;
  }, [selectedId]);

  return {
    selectedId,
    selectedAnnotation,
    select,
    isSelected,
  };
}

export default useAnnotations;
