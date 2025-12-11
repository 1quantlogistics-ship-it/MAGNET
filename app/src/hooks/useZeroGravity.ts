/**
 * MAGNET UI Module 03: useZeroGravity Hook
 *
 * Zero-gravity micro-motion hook for floating UI elements.
 * Provides subtle drift animation with drag inertia support.
 */

import { useRef, useEffect, useState, useCallback } from 'react';
import type { FloatOffset } from '../types/chat';

/**
 * Zero-gravity hook options
 */
export interface ZeroGravityOptions {
  /** Whether the effect is enabled */
  enabled: boolean;
  /** Magnitude of drift in pixels */
  magnitude?: number;
  /** Noise frequency (lower = slower) */
  frequency?: number;
  /** Inertia damping factor (0-1, higher = more momentum) */
  inertia?: number;
}

/**
 * Zero-gravity hook return value
 */
export interface ZeroGravityResult {
  /** Current float offset */
  floatOffset: FloatOffset;
  /** Apply drag inertia from velocity */
  applyDragInertia: (velocity: { x: number; y: number }) => void;
  /** Reset to center */
  reset: () => void;
}

/**
 * Simple 2D noise function for organic motion
 */
function noise2D(x: number, y: number, seed: number): number {
  const n = Math.sin(x * 12.9898 + y * 78.233 + seed) * 43758.5453;
  return (n - Math.floor(n)) * 2 - 1;
}

/**
 * Smoothstep for easing
 */
function smoothstep(t: number): number {
  return t * t * (3 - 2 * t);
}

/**
 * Zero-gravity micro-motion hook
 *
 * Creates subtle floating drift animation for UI elements,
 * simulating weightlessness with perlin-like noise motion.
 *
 * @example
 * ```tsx
 * const { floatOffset, applyDragInertia } = useZeroGravity({
 *   enabled: windowState === 'expanded',
 *   magnitude: 0.5,
 *   frequency: 0.001
 * });
 *
 * return (
 *   <motion.div
 *     style={{
 *       x: floatOffset.x,
 *       y: floatOffset.y
 *     }}
 *   />
 * );
 * ```
 */
export function useZeroGravity({
  enabled,
  magnitude = 0.5,
  frequency = 0.001,
  inertia = 0.92,
}: ZeroGravityOptions): ZeroGravityResult {
  const [floatOffset, setFloatOffset] = useState<FloatOffset>({ x: 0, y: 0 });
  const velocityRef = useRef<FloatOffset>({ x: 0, y: 0 });
  const seedRef = useRef(Math.random() * 1000);
  const animationRef = useRef<number | null>(null);

  // Animation loop
  useEffect(() => {
    if (!enabled) {
      // Reset when disabled
      setFloatOffset({ x: 0, y: 0 });
      velocityRef.current = { x: 0, y: 0 };
      return;
    }

    const startTime = performance.now();

    const animate = (currentTime: number) => {
      const elapsed = (currentTime - startTime) * frequency;

      // Calculate noise-based offset
      const noiseX = noise2D(elapsed, 0, seedRef.current) * magnitude;
      const noiseY = noise2D(0, elapsed, seedRef.current + 100) * magnitude;

      // Apply velocity damping
      velocityRef.current.x *= inertia;
      velocityRef.current.y *= inertia;

      // Kill tiny velocities
      if (Math.abs(velocityRef.current.x) < 0.001) velocityRef.current.x = 0;
      if (Math.abs(velocityRef.current.y) < 0.001) velocityRef.current.y = 0;

      // Combine noise and velocity
      setFloatOffset({
        x: noiseX + velocityRef.current.x,
        y: noiseY + velocityRef.current.y,
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [enabled, magnitude, frequency, inertia]);

  /**
   * Apply drag inertia from drag velocity
   * Called at end of drag to add momentum
   */
  const applyDragInertia = useCallback(
    (velocity: { x: number; y: number }) => {
      // Scale down velocity for subtle effect
      velocityRef.current = {
        x: velocity.x * 0.1,
        y: velocity.y * 0.1,
      };
    },
    []
  );

  /**
   * Reset to center position
   */
  const reset = useCallback(() => {
    setFloatOffset({ x: 0, y: 0 });
    velocityRef.current = { x: 0, y: 0 };
  }, []);

  return {
    floatOffset,
    applyDragInertia,
    reset,
  };
}

export default useZeroGravity;
