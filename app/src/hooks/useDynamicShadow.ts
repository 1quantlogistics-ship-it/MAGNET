/**
 * MAGNET UI Dynamic Shadow Hook
 *
 * VisionOS-style dynamic shadow based on element position and light source.
 * FM4 Compliance: Memoized calculations, throttled at 60fps max.
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { getDPRAdjustedValue, VISIONOS_TIMING } from '../types/common';

/**
 * Light source position
 */
interface LightSource {
  /** X position (0-1, 0 = left, 1 = right) */
  x: number;
  /** Y position (0-1, 0 = top, 1 = bottom) */
  y: number;
  /** Z position (distance, affects intensity) */
  z: number;
}

/**
 * Shadow layer definition
 */
interface ShadowLayer {
  /** X offset in pixels */
  offsetX: number;
  /** Y offset in pixels */
  offsetY: number;
  /** Blur radius in pixels */
  blur: number;
  /** Spread radius in pixels */
  spread: number;
  /** Shadow color with opacity */
  color: string;
}

/**
 * Dynamic shadow configuration
 */
interface UseDynamicShadowConfig {
  /** Light source position */
  lightSource?: LightSource;
  /** Base shadow intensity (0-1) */
  intensity?: number;
  /** Maximum shadow offset */
  maxOffset?: number;
  /** Number of shadow layers (1-3) */
  layers?: 1 | 2 | 3;
  /** Shadow color */
  color?: string;
  /** Enable the effect */
  enabled?: boolean;
  /** Elevation level (affects shadow spread) */
  elevation?: number;
  /** Track pointer as light source */
  trackPointer?: boolean;
}

/**
 * Dynamic shadow return interface
 */
interface UseDynamicShadowReturn {
  /** CSS box-shadow value */
  shadow: string;
  /** CSS styles including shadow */
  style: React.CSSProperties;
  /** Current shadow layers */
  layers: ShadowLayer[];
  /** Set light source position */
  setLightSource: (source: Partial<LightSource>) => void;
  /** Reset to default light source */
  reset: () => void;
}

/**
 * Default light source (top-left, slightly elevated)
 */
const DEFAULT_LIGHT_SOURCE: LightSource = {
  x: 0.3,
  y: 0.2,
  z: 1,
};

/**
 * Shadow layer multipliers for VisionOS-style layered shadows
 */
const LAYER_MULTIPLIERS = [
  { offset: 1, blur: 1, spread: 0, opacity: 0.12 },
  { offset: 2, blur: 2, spread: 0.5, opacity: 0.08 },
  { offset: 4, blur: 4, spread: 1, opacity: 0.04 },
];

/**
 * Parse color and extract base without alpha
 */
function parseColorBase(color: string): string {
  // Handle rgba format
  if (color.startsWith('rgba')) {
    return color.replace(/,\s*[\d.]+\)$/, ')').replace('rgba', 'rgb');
  }
  // Handle rgb format
  if (color.startsWith('rgb')) {
    return color;
  }
  // Handle hex format
  return color;
}

/**
 * Create color with alpha
 */
function colorWithAlpha(baseColor: string, alpha: number): string {
  if (baseColor.startsWith('rgb(')) {
    return baseColor.replace('rgb(', 'rgba(').replace(')', `, ${alpha})`);
  }
  if (baseColor.startsWith('rgba(')) {
    return baseColor.replace(/,\s*[\d.]+\)$/, `, ${alpha})`);
  }
  // Hex color - convert to rgba
  const hex = baseColor.replace('#', '');
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

/**
 * Hook for VisionOS-style dynamic shadows
 */
export function useDynamicShadow(
  config: UseDynamicShadowConfig = {}
): UseDynamicShadowReturn {
  const {
    lightSource: initialLightSource = DEFAULT_LIGHT_SOURCE,
    intensity = 1,
    maxOffset = 20,
    layers = 3,
    color = '#000000',
    enabled = true,
    elevation = 1,
    trackPointer = false,
  } = config;

  const [lightSource, setLightSourceState] = useState<LightSource>(initialLightSource);
  const lastUpdateRef = useRef(0);
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  /**
   * Set light source with partial update
   */
  const setLightSource = useCallback((source: Partial<LightSource>) => {
    setLightSourceState((prev) => ({
      ...prev,
      ...source,
    }));
  }, []);

  /**
   * Reset to default light source
   */
  const reset = useCallback(() => {
    setLightSourceState(DEFAULT_LIGHT_SOURCE);
  }, []);

  /**
   * Handle pointer move for light tracking
   */
  const handlePointerMove = useCallback(
    (event: PointerEvent) => {
      if (!trackPointer || !enabled || !isMountedRef.current) return;

      // Throttle to ~60fps
      const now = performance.now();
      if (now - lastUpdateRef.current < VISIONOS_TIMING.animationThrottle) return;
      lastUpdateRef.current = now;

      // Normalize pointer position to 0-1
      const x = event.clientX / window.innerWidth;
      const y = event.clientY / window.innerHeight;

      setLightSourceState((prev) => ({
        ...prev,
        x,
        y,
      }));
    },
    [trackPointer, enabled]
  );

  // Set up pointer tracking
  useEffect(() => {
    if (!trackPointer || !enabled) return;

    window.addEventListener('pointermove', handlePointerMove);
    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
    };
  }, [trackPointer, enabled, handlePointerMove]);

  /**
   * Calculate shadow layers based on light source
   */
  const shadowLayers = useMemo((): ShadowLayer[] => {
    if (!enabled) return [];

    const baseColor = parseColorBase(color);
    const layerCount = Math.min(layers, 3);
    const result: ShadowLayer[] = [];

    // Calculate offset direction (opposite of light source)
    const offsetDirX = (lightSource.x - 0.5) * -2;
    const offsetDirY = (lightSource.y - 0.5) * -2;

    // Distance factor affects shadow softness
    const distanceFactor = Math.max(0.5, lightSource.z);

    for (let i = 0; i < layerCount; i++) {
      const multiplier = LAYER_MULTIPLIERS[i];
      const layerIntensity = intensity * multiplier.opacity * distanceFactor;

      // Scale offset by elevation
      const elevationScale = elevation * multiplier.offset;
      const offsetX = getDPRAdjustedValue(offsetDirX * maxOffset * elevationScale);
      const offsetY = getDPRAdjustedValue(offsetDirY * maxOffset * elevationScale);

      // Blur increases with layer depth and elevation
      const blur = getDPRAdjustedValue(maxOffset * multiplier.blur * elevation * distanceFactor);
      const spread = getDPRAdjustedValue(multiplier.spread * elevation);

      result.push({
        offsetX,
        offsetY,
        blur,
        spread,
        color: colorWithAlpha(baseColor, layerIntensity),
      });
    }

    return result;
  }, [enabled, lightSource, intensity, maxOffset, layers, color, elevation]);

  /**
   * Generate CSS box-shadow value
   */
  const shadow = useMemo(() => {
    if (shadowLayers.length === 0) return 'none';

    return shadowLayers
      .map(
        (layer) =>
          `${layer.offsetX}px ${layer.offsetY}px ${layer.blur}px ${layer.spread}px ${layer.color}`
      )
      .join(', ');
  }, [shadowLayers]);

  /**
   * CSS styles including shadow
   */
  const style: React.CSSProperties = useMemo(
    () => ({
      boxShadow: shadow,
      willChange: trackPointer ? 'box-shadow' : 'auto',
    }),
    [shadow, trackPointer]
  );

  return {
    shadow,
    style,
    layers: shadowLayers,
    setLightSource,
    reset,
  };
}

/**
 * Hook for elevation-based static shadows
 */
export function useElevationShadow(
  elevation: number = 1,
  config: {
    color?: string;
    intensity?: number;
    enabled?: boolean;
  } = {}
): {
  shadow: string;
  style: React.CSSProperties;
} {
  const { color = '#000000', intensity = 1, enabled = true } = config;

  const shadow = useMemo(() => {
    if (!enabled || elevation <= 0) return 'none';

    const baseColor = parseColorBase(color);
    const layers: string[] = [];

    // Generate elevation-based layers
    const clampedElevation = Math.min(Math.max(elevation, 0), 5);

    // Layer 1: Tight shadow
    const offset1 = getDPRAdjustedValue(clampedElevation * 2);
    const blur1 = getDPRAdjustedValue(clampedElevation * 4);
    layers.push(
      `0 ${offset1}px ${blur1}px ${colorWithAlpha(baseColor, 0.12 * intensity)}`
    );

    // Layer 2: Medium shadow (only for elevation > 1)
    if (clampedElevation > 1) {
      const offset2 = getDPRAdjustedValue(clampedElevation * 4);
      const blur2 = getDPRAdjustedValue(clampedElevation * 8);
      layers.push(
        `0 ${offset2}px ${blur2}px ${colorWithAlpha(baseColor, 0.08 * intensity)}`
      );
    }

    // Layer 3: Ambient shadow (only for elevation > 2)
    if (clampedElevation > 2) {
      const offset3 = getDPRAdjustedValue(clampedElevation * 8);
      const blur3 = getDPRAdjustedValue(clampedElevation * 16);
      layers.push(
        `0 ${offset3}px ${blur3}px ${colorWithAlpha(baseColor, 0.04 * intensity)}`
      );
    }

    return layers.join(', ');
  }, [elevation, color, intensity, enabled]);

  const style: React.CSSProperties = useMemo(
    () => ({
      boxShadow: shadow,
    }),
    [shadow]
  );

  return { shadow, style };
}

/**
 * Hook for inset shadows (depth effect)
 */
export function useInsetShadow(
  depth: number = 1,
  config: {
    color?: string;
    enabled?: boolean;
  } = {}
): {
  shadow: string;
  style: React.CSSProperties;
} {
  const { color = '#000000', enabled = true } = config;

  const shadow = useMemo(() => {
    if (!enabled || depth <= 0) return 'none';

    const baseColor = parseColorBase(color);
    const blur = getDPRAdjustedValue(depth * 4);
    const spread = getDPRAdjustedValue(depth * -1);

    return `inset 0 ${depth}px ${blur}px ${spread}px ${colorWithAlpha(baseColor, 0.1)}`;
  }, [depth, color, enabled]);

  const style: React.CSSProperties = useMemo(
    () => ({
      boxShadow: shadow,
    }),
    [shadow]
  );

  return { shadow, style };
}
