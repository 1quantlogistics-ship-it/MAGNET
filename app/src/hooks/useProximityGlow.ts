/**
 * MAGNET UI Proximity Glow Hook
 *
 * Creates VisionOS-style proximity glow effect based on pointer position.
 * FM4 Compliance: Throttled, DPR-aware, lifecycle-safe.
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { getDPRAdjustedValue, VISIONOS_TIMING } from '../types/common';

/**
 * Proximity glow configuration
 */
interface UseProximityGlowConfig {
  /** Maximum glow radius in pixels */
  maxRadius?: number;
  /** Maximum glow intensity (0-1) */
  maxIntensity?: number;
  /** Glow color */
  color?: string;
  /** Distance threshold for activation */
  threshold?: number;
  /** Enable the effect */
  enabled?: boolean;
  /** Throttle interval in ms */
  throttleMs?: number;
}

/**
 * Glow state
 */
interface GlowState {
  /** Glow X position relative to element */
  x: number;
  /** Glow Y position relative to element */
  y: number;
  /** Current glow intensity (0-1) */
  intensity: number;
  /** Whether pointer is within threshold */
  isActive: boolean;
}

/**
 * Proximity glow return interface
 */
interface UseProximityGlowReturn {
  /** Ref to attach to the target element */
  ref: React.RefObject<HTMLElement>;
  /** Current glow state */
  glow: GlowState;
  /** CSS styles for the glow effect */
  glowStyle: React.CSSProperties;
  /** CSS background for glow overlay */
  glowBackground: string;
  /** Reset glow state */
  reset: () => void;
}

/**
 * Calculate distance between two points
 */
function calculateDistance(
  x1: number,
  y1: number,
  x2: number,
  y2: number
): number {
  return Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
}

/**
 * Hook for VisionOS-style proximity glow effect
 */
export function useProximityGlow(
  config: UseProximityGlowConfig = {}
): UseProximityGlowReturn {
  const {
    maxRadius = 200,
    maxIntensity = 0.15,
    color = 'rgba(255, 255, 255, 0.5)',
    threshold = 300,
    enabled = true,
    throttleMs = VISIONOS_TIMING.pointerThrottle,
  } = config;

  const ref = useRef<HTMLElement>(null);
  const lastUpdateRef = useRef(0);
  const rafIdRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);

  const [glow, setGlow] = useState<GlowState>({
    x: 0,
    y: 0,
    intensity: 0,
    isActive: false,
  });

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, []);

  /**
   * Update glow based on pointer position
   */
  const updateGlow = useCallback(
    (clientX: number, clientY: number) => {
      if (!ref.current || !enabled || !isMountedRef.current) return;

      // Throttle updates
      const now = performance.now();
      if (now - lastUpdateRef.current < throttleMs) return;
      lastUpdateRef.current = now;

      // Use RAF for smooth updates
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }

      rafIdRef.current = requestAnimationFrame(() => {
        if (!ref.current || !isMountedRef.current) return;

        const rect = ref.current.getBoundingClientRect();

        // Calculate position relative to element center
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        // Calculate distance from pointer to center
        const distance = calculateDistance(clientX, clientY, centerX, centerY);

        // Calculate position relative to element (for gradient position)
        const relativeX = getDPRAdjustedValue(clientX - rect.left);
        const relativeY = getDPRAdjustedValue(clientY - rect.top);

        // Check if within element bounds (with threshold)
        const isWithinBounds =
          clientX >= rect.left - threshold &&
          clientX <= rect.right + threshold &&
          clientY >= rect.top - threshold &&
          clientY <= rect.bottom + threshold;

        if (isWithinBounds) {
          // Calculate intensity based on distance (closer = stronger)
          const maxDistance = Math.max(rect.width, rect.height) / 2 + threshold;
          const normalizedDistance = Math.min(distance / maxDistance, 1);
          const intensity = maxIntensity * (1 - normalizedDistance);

          setGlow({
            x: relativeX,
            y: relativeY,
            intensity,
            isActive: true,
          });
        } else {
          setGlow((prev) => ({
            ...prev,
            intensity: 0,
            isActive: false,
          }));
        }
      });
    },
    [enabled, maxIntensity, threshold, throttleMs]
  );

  /**
   * Handle pointer move
   */
  const handlePointerMove = useCallback(
    (event: PointerEvent) => {
      updateGlow(event.clientX, event.clientY);
    },
    [updateGlow]
  );

  /**
   * Handle pointer leave (from window)
   */
  const handlePointerLeave = useCallback(() => {
    if (isMountedRef.current) {
      setGlow((prev) => ({
        ...prev,
        intensity: 0,
        isActive: false,
      }));
    }
  }, []);

  // Set up global pointer listeners
  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerleave', handlePointerLeave);

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerleave', handlePointerLeave);
    };
  }, [enabled, handlePointerMove, handlePointerLeave]);

  /**
   * Reset glow state
   */
  const reset = useCallback(() => {
    setGlow({
      x: 0,
      y: 0,
      intensity: 0,
      isActive: false,
    });
  }, []);

  /**
   * Generate CSS background gradient for glow
   */
  const glowBackground = useMemo(() => {
    if (!glow.isActive || glow.intensity <= 0) {
      return 'transparent';
    }

    // Radial gradient from pointer position
    const adjustedRadius = getDPRAdjustedValue(maxRadius);
    const alpha = glow.intensity;

    // Parse color and apply intensity
    const colorWithAlpha = color.replace(
      /[\d.]+\)$/,
      `${alpha})`
    );

    return `radial-gradient(${adjustedRadius}px circle at ${glow.x}px ${glow.y}px, ${colorWithAlpha}, transparent)`;
  }, [glow.x, glow.y, glow.intensity, glow.isActive, maxRadius, color]);

  /**
   * CSS styles for glow overlay
   */
  const glowStyle: React.CSSProperties = useMemo(
    () => ({
      position: 'absolute' as const,
      inset: 0,
      pointerEvents: 'none' as const,
      background: glowBackground,
      borderRadius: 'inherit',
      transition: `opacity ${VISIONOS_TIMING.tooltipReveal}ms ease`,
      opacity: glow.isActive ? 1 : 0,
      zIndex: 1,
    }),
    [glowBackground, glow.isActive]
  );

  return {
    ref: ref as React.RefObject<HTMLElement>,
    glow,
    glowStyle,
    glowBackground,
    reset,
  };
}

/**
 * Hook for element-specific hover glow (simpler version)
 */
export function useHoverGlow(
  config: {
    color?: string;
    intensity?: number;
    radius?: number;
    enabled?: boolean;
  } = {}
): {
  isHovered: boolean;
  glowStyle: React.CSSProperties;
  handlers: {
    onMouseEnter: () => void;
    onMouseLeave: () => void;
  };
} {
  const {
    color = 'rgba(255, 255, 255, 0.1)',
    intensity = 0.1,
    radius = 100,
    enabled = true,
  } = config;

  const [isHovered, setIsHovered] = useState(false);

  const handlers = useMemo(
    () => ({
      onMouseEnter: () => enabled && setIsHovered(true),
      onMouseLeave: () => setIsHovered(false),
    }),
    [enabled]
  );

  const glowStyle: React.CSSProperties = useMemo(
    () => ({
      boxShadow: isHovered
        ? `0 0 ${radius}px ${radius / 2}px ${color.replace(
            /[\d.]+\)$/,
            `${intensity})`
          )}`
        : 'none',
      transition: `box-shadow ${VISIONOS_TIMING.tooltipReveal}ms ease`,
    }),
    [isHovered, color, intensity, radius]
  );

  return {
    isHovered,
    glowStyle,
    handlers,
  };
}
