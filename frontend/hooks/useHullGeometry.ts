/**
 * useHullGeometry.ts - React hook for fetching hull geometry v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Fetches typed SceneData from API with caching and error handling.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  SceneData,
  GeometryErrorResponse,
  LODLevel,
} from '../types/schema';
import { isGeometryErrorResponse } from '../types/schema';

// =============================================================================
// TYPES
// =============================================================================

export interface UseHullGeometryOptions {
  includeStructure?: boolean;
  includeHydrostatics?: boolean;
  lod?: LODLevel;
  allowVisualOnly?: boolean;
  autoRefresh?: boolean;
  refreshInterval?: number;
  baseUrl?: string;
}

export interface UseHullGeometryResult {
  data: SceneData | null;
  isLoading: boolean;
  error: GeometryErrorResponse | null;
  refresh: () => Promise<void>;
  invalidate: () => void;
}

// =============================================================================
// CACHE
// =============================================================================

interface CacheEntry {
  data: SceneData;
  timestamp: number;
}

const CACHE = new Map<string, CacheEntry>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function getCacheKey(designId: string, options: UseHullGeometryOptions): string {
  return `${designId}:${options.includeStructure}:${options.includeHydrostatics}:${options.lod}:${options.allowVisualOnly}`;
}

function getCachedData(key: string): SceneData | null {
  const entry = CACHE.get(key);
  if (!entry) return null;

  if (Date.now() - entry.timestamp > CACHE_TTL) {
    CACHE.delete(key);
    return null;
  }

  return entry.data;
}

function setCachedData(key: string, data: SceneData): void {
  CACHE.set(key, { data, timestamp: Date.now() });
}

// =============================================================================
// HOOK
// =============================================================================

export function useHullGeometry(
  designId: string,
  options: UseHullGeometryOptions = {},
): UseHullGeometryResult {
  const {
    includeStructure = true,
    includeHydrostatics = false,
    lod = 'medium',
    allowVisualOnly = false,
    autoRefresh = false,
    refreshInterval = 30000,
    baseUrl = '/api/v1',
  } = options;

  const [data, setData] = useState<SceneData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<GeometryErrorResponse | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const cacheKey = getCacheKey(designId, options);

  // Fetch function
  const fetchGeometry = useCallback(async (skipCache: boolean = false): Promise<void> => {
    // Check cache first
    if (!skipCache) {
      const cached = getCachedData(cacheKey);
      if (cached) {
        setData(cached);
        setIsLoading(false);
        return;
      }
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    setError(null);

    try {
      // Build query params
      const params = new URLSearchParams({
        include_structure: String(includeStructure),
        include_hydrostatics: String(includeHydrostatics),
        lod,
        allow_visual_only: String(allowVisualOnly),
      });

      const url = `${baseUrl}/designs/${designId}/3d/scene?${params}`;

      const response = await fetch(url, {
        signal: abortControllerRef.current.signal,
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        if (isGeometryErrorResponse(errorData)) {
          setError(errorData);
          setData(null);
          return;
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const sceneData: SceneData = await response.json();

      // Cache the result
      setCachedData(cacheKey, sceneData);
      setData(sceneData);
      setError(null);

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return; // Request was cancelled
      }

      console.error('Failed to fetch hull geometry:', err);
      setError({
        error: {
          code: 'FETCH_ERROR',
          category: 'network',
          severity: 'error',
          message: err instanceof Error ? err.message : 'Unknown error',
          details: {},
          recovery_hint: 'Check your network connection and try again.',
        },
      });
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [designId, includeStructure, includeHydrostatics, lod, allowVisualOnly, baseUrl, cacheKey]);

  // Initial fetch
  useEffect(() => {
    fetchGeometry();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchGeometry]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      fetchGeometry(true);
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchGeometry]);

  // Refresh function (skips cache)
  const refresh = useCallback(async () => {
    await fetchGeometry(true);
  }, [fetchGeometry]);

  // Invalidate cache
  const invalidate = useCallback(() => {
    CACHE.delete(cacheKey);
    fetchGeometry(true);
  }, [cacheKey, fetchGeometry]);

  return {
    data,
    isLoading,
    error,
    refresh,
    invalidate,
  };
}

// =============================================================================
// BINARY FETCH HOOK
// =============================================================================

export interface UseBinaryGeometryOptions {
  lod?: LODLevel;
  allowVisualOnly?: boolean;
  baseUrl?: string;
}

export interface UseBinaryGeometryResult {
  data: ArrayBuffer | null;
  isLoading: boolean;
  error: GeometryErrorResponse | null;
  refresh: () => Promise<void>;
}

/**
 * Fetch binary mesh data for efficient transfer.
 */
export function useBinaryGeometry(
  designId: string,
  options: UseBinaryGeometryOptions = {},
): UseBinaryGeometryResult {
  const {
    lod = 'medium',
    allowVisualOnly = false,
    baseUrl = '/api/v1',
  } = options;

  const [data, setData] = useState<ArrayBuffer | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<GeometryErrorResponse | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchBinary = useCallback(async (): Promise<void> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        format: 'binary',
        lod,
        allow_visual_only: String(allowVisualOnly),
      });

      const url = `${baseUrl}/designs/${designId}/3d/hull?${params}`;

      const response = await fetch(url, {
        signal: abortControllerRef.current.signal,
        headers: {
          'Accept': 'application/octet-stream',
        },
      });

      if (!response.ok) {
        if (response.headers.get('Content-Type')?.includes('application/json')) {
          const errorData = await response.json();
          if (isGeometryErrorResponse(errorData)) {
            setError(errorData);
            setData(null);
            return;
          }
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const buffer = await response.arrayBuffer();
      setData(buffer);
      setError(null);

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      console.error('Failed to fetch binary geometry:', err);
      setError({
        error: {
          code: 'FETCH_ERROR',
          category: 'network',
          severity: 'error',
          message: err instanceof Error ? err.message : 'Unknown error',
          details: {},
          recovery_hint: 'Check your network connection and try again.',
        },
      });
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [designId, lod, allowVisualOnly, baseUrl]);

  useEffect(() => {
    fetchBinary();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchBinary]);

  return {
    data,
    isLoading,
    error,
    refresh: fetchBinary,
  };
}

export default useHullGeometry;
