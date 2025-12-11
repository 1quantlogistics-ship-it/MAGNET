/**
 * MAGNET UI Parallax Hook
 *
 * VisionOS-style parallax effect for spatial depth.
 * FM4 Compliance: Standardized vector math, throttled, lifecycle-safe.
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { getDPRAdjustedValue, VISIONOS_TIMING, type Point3D } from '../types/common';
import { animationScheduler, EASING } from '../systems/AnimationScheduler';
import { generateId } from '../types/common';

/**
 * Parallax configuration
 */
interface UseParallaxConfig {
  /** Maximum X offset in pixels */
  maxOffsetX?: number;
  /** Maximum Y offset in pixels */
  maxOffsetY?: number;
  /** Maximum Z offset (scale) */
  maxOffsetZ?: number;
  /** Effect intensity (0-1) */
  intensity?: number;
  /** Enable the effect */
  enabled?: boolean;
  /** Smooth transition duration */
  smoothing?: number;
  /** Invert the effect direction */
  invert?: boolean;
  /** Use device orientation if available */
  useDeviceOrientation?: boolean;
}

/**
 * Parallax state
 */
interface ParallaxState {
  /** Current X offset */
  offsetX: number;
  /** Current Y offset */
  offsetY: number;
  /** Current Z offset (for scale/depth) */
  offsetZ: number;
  /** Current rotation X (tilt) */
  rotateX: number;
  /** Current rotation Y (tilt) */
  rotateY: number;
  /** Whether parallax is active */
  isActive: boolean;
}

/**
 * Parallax return interface
 */
interface UseParallaxReturn {
  /** Current parallax state */
  parallax: ParallaxState;
  /** CSS transform string */
  transform: string;
  /** CSS styles for parallax effect */
  style: React.CSSProperties;
  /** Reset to neutral position */
  reset: () => void;
  /** Manually set parallax offset */
  setOffset: (offset: Partial<Point3D>) => void;
}

/**
 * Clamp a value between min and max
 */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Normalize a value from one range to another
 */
function normalize(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number
): number {
  const normalized = (value - inMin) / (inMax - inMin);
  return outMin + normalized * (outMax - outMin);
}

/**
 * Hook for VisionOS-style parallax effect
 */
export function useParallax(config: UseParallaxConfig = {}): UseParallaxReturn {
  const {
    maxOffsetX = 20,
    maxOffsetY = 20,
    maxOffsetZ = 0.05,
    intensity = 1,
    enabled = true,
    smoothing = 150,
    invert = false,
    useDeviceOrientation = false,
  } = config;

  const animationIdRef = useRef<string | null>(null);
  const targetRef = useRef({ x: 0, y: 0, z: 0 });
  const isMountedRef = useRef(true);

  const [parallax, setParallax] = useState<ParallaxState>({
    offsetX: 0,
    offsetY: 0,
    offsetZ: 0,
    rotateX: 0,
    rotateY: 0,
    isActive: false,
  });

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }
    };
  }, []);

  /**
   * Animate to target offset
   */
  const animateToTarget = useCallback(
    (targetX: number, targetY: number, targetZ: number) => {
      if (!isMountedRef.current) return;

      // Cancel previous animation
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }

      const startX = parallax.offsetX;
      const startY = parallax.offsetY;
      const startZ = parallax.offsetZ;

      const id = generateId('parallax');
      animationIdRef.current = id;

      animationScheduler.schedule(id, {
        duration: smoothing,
        easing: EASING.easeOut,
        onUpdate: (progress) => {
          if (!isMountedRef.current) return;

          const x = startX + (targetX - startX) * progress;
          const y = startY + (targetY - startY) * progress;
          const z = startZ + (targetZ - startZ) * progress;

          // Calculate rotation based on offset
          const rotateY = (x / maxOffsetX) * 5 * intensity;
          const rotateX = -(y / maxOffsetY) * 5 * intensity;

          setParallax({
            offsetX: getDPRAdjustedValue(x),
            offsetY: getDPRAdjustedValue(y),
            offsetZ: z,
            rotateX,
            rotateY,
            isActive: true,
          });
        },
        onComplete: () => {
          animationIdRef.current = null;
        },
      });
    },
    [parallax.offsetX, parallax.offsetY, parallax.offsetZ, maxOffsetX, maxOffsetY, intensity, smoothing]
  );

  /**
   * Handle pointer move for parallax
   */
  const handlePointerMove = useCallback(
    (event: PointerEvent) => {
      if (!enabled || !isMountedRef.current) return;

      // Calculate normalized position (-1 to 1)
      const normalizedX = normalize(event.clientX, 0, window.innerWidth, -1, 1);
      const normalizedY = normalize(event.clientY, 0, window.innerHeight, -1, 1);

      // Apply intensity and inversion
      const multiplier = invert ? -1 : 1;
      const targetX = normalizedX * maxOffsetX * intensity * multiplier;
      const targetY = normalizedY * maxOffsetY * intensity * multiplier;
      const targetZ = Math.abs(normalizedX * normalizedY) * maxOffsetZ * intensity;

      targetRef.current = { x: targetX, y: targetY, z: targetZ };
      animateToTarget(targetX, targetY, targetZ);
    },
    [enabled, maxOffsetX, maxOffsetY, maxOffsetZ, intensity, invert, animateToTarget]
  );

  /**
   * Handle device orientation for parallax
   */
  const handleDeviceOrientation = useCallback(
    (event: DeviceOrientationEvent) => {
      if (!enabled || !useDeviceOrientation || !isMountedRef.current) return;

      const { beta, gamma } = event;
      if (beta === null || gamma === null) return;

      // Normalize device orientation (-1 to 1)
      const normalizedX = clamp(gamma / 45, -1, 1);
      const normalizedY = clamp((beta - 45) / 45, -1, 1);

      const multiplier = invert ? -1 : 1;
      const targetX = normalizedX * maxOffsetX * intensity * multiplier;
      const targetY = normalizedY * maxOffsetY * intensity * multiplier;
      const targetZ = Math.abs(normalizedX * normalizedY) * maxOffsetZ * intensity;

      targetRef.current = { x: targetX, y: targetY, z: targetZ };
      animateToTarget(targetX, targetY, targetZ);
    },
    [enabled, useDeviceOrientation, maxOffsetX, maxOffsetY, maxOffsetZ, intensity, invert, animateToTarget]
  );

  /**
   * Handle pointer leave - reset to neutral
   */
  const handlePointerLeave = useCallback(() => {
    if (!isMountedRef.current) return;

    targetRef.current = { x: 0, y: 0, z: 0 };
    animateToTarget(0, 0, 0);

    // Mark as inactive after animation
    setTimeout(() => {
      if (isMountedRef.current) {
        setParallax((prev) => ({ ...prev, isActive: false }));
      }
    }, smoothing);
  }, [animateToTarget, smoothing]);

  // Set up event listeners
  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerleave', handlePointerLeave);

    if (useDeviceOrientation && 'DeviceOrientationEvent' in window) {
      window.addEventListener('deviceorientation', handleDeviceOrientation);
    }

    return () => {
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerleave', handlePointerLeave);

      if (useDeviceOrientation) {
        window.removeEventListener('deviceorientation', handleDeviceOrientation);
      }
    };
  }, [enabled, useDeviceOrientation, handlePointerMove, handlePointerLeave, handleDeviceOrientation]);

  /**
   * Reset to neutral position
   */
  const reset = useCallback(() => {
    targetRef.current = { x: 0, y: 0, z: 0 };
    animateToTarget(0, 0, 0);
  }, [animateToTarget]);

  /**
   * Manually set parallax offset
   */
  const setOffset = useCallback(
    (offset: Partial<Point3D>) => {
      const targetX = offset.x !== undefined ? clamp(offset.x, -maxOffsetX, maxOffsetX) : targetRef.current.x;
      const targetY = offset.y !== undefined ? clamp(offset.y, -maxOffsetY, maxOffsetY) : targetRef.current.y;
      const targetZ = offset.z !== undefined ? clamp(offset.z, 0, maxOffsetZ) : targetRef.current.z;

      targetRef.current = { x: targetX, y: targetY, z: targetZ };
      animateToTarget(targetX, targetY, targetZ);
    },
    [maxOffsetX, maxOffsetY, maxOffsetZ, animateToTarget]
  );

  /**
   * Generate CSS transform string
   */
  const transform = useMemo(() => {
    const scale = 1 + parallax.offsetZ;
    return `translate3d(${parallax.offsetX}px, ${parallax.offsetY}px, 0) scale(${scale}) rotateX(${parallax.rotateX}deg) rotateY(${parallax.rotateY}deg)`;
  }, [parallax.offsetX, parallax.offsetY, parallax.offsetZ, parallax.rotateX, parallax.rotateY]);

  /**
   * CSS styles for parallax element
   */
  const style: React.CSSProperties = useMemo(
    () => ({
      transform,
      transformStyle: 'preserve-3d' as const,
      willChange: 'transform',
    }),
    [transform]
  );

  return {
    parallax,
    transform,
    style,
    reset,
    setOffset,
  };
}

/**
 * Hook for simple layer-based parallax (different depths)
 */
export function useLayerParallax(
  depth: number = 1,
  config: {
    maxOffset?: number;
    enabled?: boolean;
  } = {}
): {
  transform: string;
  style: React.CSSProperties;
} {
  const { maxOffset = 30, enabled = true } = config;

  const { parallax } = useParallax({
    maxOffsetX: maxOffset * depth,
    maxOffsetY: maxOffset * depth,
    maxOffsetZ: 0,
    intensity: depth,
    enabled,
  });

  const transform = useMemo(
    () => `translate3d(${parallax.offsetX}px, ${parallax.offsetY}px, 0)`,
    [parallax.offsetX, parallax.offsetY]
  );

  const style: React.CSSProperties = useMemo(
    () => ({
      transform,
      willChange: 'transform',
    }),
    [transform]
  );

  return { transform, style };
}
