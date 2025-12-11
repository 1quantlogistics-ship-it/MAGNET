/**
 * MAGNET UI Spring Transition Hook
 *
 * VisionOS-style spring physics transitions.
 * Provides natural, fluid motion with configurable spring parameters.
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { animationScheduler } from '../systems/AnimationScheduler';
import { generateId, VISIONOS_TIMING, type SpringConfig } from '../types/common';

/**
 * Spring transition configuration
 */
interface UseSpringTransitionConfig {
  /** Spring stiffness (higher = snappier) */
  stiffness?: number;
  /** Spring damping (higher = less bounce) */
  damping?: number;
  /** Mass (higher = slower) */
  mass?: number;
  /** Velocity threshold for completion */
  velocityThreshold?: number;
  /** Position threshold for completion */
  positionThreshold?: number;
  /** Maximum duration before forcing completion */
  maxDuration?: number;
}

/**
 * Spring state
 */
interface SpringState {
  /** Current value */
  value: number;
  /** Current velocity */
  velocity: number;
  /** Whether spring is active */
  isActive: boolean;
  /** Target value */
  target: number;
}

/**
 * Spring transition return interface
 */
interface UseSpringTransitionReturn {
  /** Current animated value */
  value: number;
  /** Current velocity */
  velocity: number;
  /** Whether animation is active */
  isActive: boolean;
  /** Set new target value */
  set: (target: number) => void;
  /** Set value immediately */
  setImmediate: (value: number) => void;
  /** Stop animation at current position */
  stop: () => void;
  /** Add impulse to spring */
  impulse: (velocity: number) => void;
}

/**
 * Physics-based spring simulation
 */
function simulateSpring(
  current: number,
  target: number,
  velocity: number,
  config: Required<UseSpringTransitionConfig>,
  deltaTime: number
): { position: number; velocity: number } {
  const { stiffness, damping, mass } = config;

  // Calculate spring force
  const displacement = current - target;
  const springForce = -stiffness * displacement;
  const dampingForce = -damping * velocity;
  const acceleration = (springForce + dampingForce) / mass;

  // Update velocity and position
  const newVelocity = velocity + acceleration * deltaTime;
  const newPosition = current + newVelocity * deltaTime;

  return { position: newPosition, velocity: newVelocity };
}

/**
 * Check if spring has settled
 */
function isSpringSettled(
  current: number,
  target: number,
  velocity: number,
  config: Required<UseSpringTransitionConfig>
): boolean {
  const positionDiff = Math.abs(current - target);
  const velocityMag = Math.abs(velocity);

  return (
    positionDiff < config.positionThreshold &&
    velocityMag < config.velocityThreshold
  );
}

/**
 * Hook for spring physics transitions
 */
export function useSpringTransition(
  initialValue: number = 0,
  config: UseSpringTransitionConfig = {}
): UseSpringTransitionReturn {
  const fullConfig: Required<UseSpringTransitionConfig> = {
    stiffness: config.stiffness ?? VISIONOS_TIMING.stiffness,
    damping: config.damping ?? VISIONOS_TIMING.damping,
    mass: config.mass ?? VISIONOS_TIMING.mass,
    velocityThreshold: config.velocityThreshold ?? 0.01,
    positionThreshold: config.positionThreshold ?? 0.001,
    maxDuration: config.maxDuration ?? 3000,
  };

  const [state, setState] = useState<SpringState>({
    value: initialValue,
    velocity: 0,
    isActive: false,
    target: initialValue,
  });

  const stateRef = useRef(state);
  const animationIdRef = useRef<string | null>(null);
  const startTimeRef = useRef(0);
  const lastTimeRef = useRef(0);
  const isMountedRef = useRef(true);

  // Keep state ref current
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

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
   * Run spring simulation
   */
  const runSpring = useCallback(
    (target: number, initialVelocity: number = 0) => {
      // Cancel existing animation
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }

      const id = generateId('spring');
      animationIdRef.current = id;
      startTimeRef.current = performance.now();
      lastTimeRef.current = startTimeRef.current;

      // Set initial state with target
      setState((prev) => ({
        ...prev,
        target,
        velocity: initialVelocity,
        isActive: true,
      }));

      // Use custom animation frame loop for physics
      const tick = () => {
        if (!isMountedRef.current || animationIdRef.current !== id) return;

        const now = performance.now();
        const deltaTime = Math.min((now - lastTimeRef.current) / 1000, 0.064); // Cap at ~15fps
        lastTimeRef.current = now;

        const elapsed = now - startTimeRef.current;
        const current = stateRef.current;

        // Check if max duration exceeded
        if (elapsed > fullConfig.maxDuration) {
          setState({
            value: target,
            velocity: 0,
            isActive: false,
            target,
          });
          animationIdRef.current = null;
          return;
        }

        // Simulate spring physics
        const result = simulateSpring(
          current.value,
          target,
          current.velocity,
          fullConfig,
          deltaTime
        );

        // Check if settled
        if (isSpringSettled(result.position, target, result.velocity, fullConfig)) {
          setState({
            value: target,
            velocity: 0,
            isActive: false,
            target,
          });
          animationIdRef.current = null;
          return;
        }

        // Update state
        setState((prev) => ({
          ...prev,
          value: result.position,
          velocity: result.velocity,
        }));

        // Continue animation
        requestAnimationFrame(tick);
      };

      requestAnimationFrame(tick);
    },
    [fullConfig]
  );

  /**
   * Set new target value
   */
  const set = useCallback(
    (target: number) => {
      runSpring(target, stateRef.current.velocity);
    },
    [runSpring]
  );

  /**
   * Set value immediately without animation
   */
  const setImmediate = useCallback((value: number) => {
    if (animationIdRef.current) {
      animationScheduler.cancel(animationIdRef.current);
      animationIdRef.current = null;
    }

    setState({
      value,
      velocity: 0,
      isActive: false,
      target: value,
    });
  }, []);

  /**
   * Stop animation at current position
   */
  const stop = useCallback(() => {
    if (animationIdRef.current) {
      animationScheduler.cancel(animationIdRef.current);
      animationIdRef.current = null;
    }

    setState((prev) => ({
      ...prev,
      velocity: 0,
      isActive: false,
      target: prev.value,
    }));
  }, []);

  /**
   * Add impulse to spring
   */
  const impulse = useCallback(
    (additionalVelocity: number) => {
      const newVelocity = stateRef.current.velocity + additionalVelocity;
      runSpring(stateRef.current.target, newVelocity);
    },
    [runSpring]
  );

  return {
    value: state.value,
    velocity: state.velocity,
    isActive: state.isActive,
    set,
    setImmediate,
    stop,
    impulse,
  };
}

/**
 * Hook for spring-based presence (enter/exit)
 */
export function useSpringPresence(
  isPresent: boolean,
  config: UseSpringTransitionConfig = {}
): {
  value: number;
  isVisible: boolean;
  isAnimating: boolean;
} {
  const spring = useSpringTransition(isPresent ? 1 : 0, config);
  const [isVisible, setIsVisible] = useState(isPresent);

  useEffect(() => {
    if (isPresent) {
      setIsVisible(true);
      spring.set(1);
    } else {
      spring.set(0);
    }
  }, [isPresent, spring]);

  // Hide when fully exited
  useEffect(() => {
    if (!isPresent && spring.value < 0.01 && !spring.isActive) {
      setIsVisible(false);
    }
  }, [isPresent, spring.value, spring.isActive]);

  return {
    value: spring.value,
    isVisible,
    isAnimating: spring.isActive,
  };
}

/**
 * Hook for spring-based vector transitions
 */
export function useSpringVector(
  initial: { x: number; y: number; z?: number } = { x: 0, y: 0, z: 0 },
  config: UseSpringTransitionConfig = {}
): {
  value: { x: number; y: number; z: number };
  isActive: boolean;
  set: (target: { x?: number; y?: number; z?: number }) => void;
  setImmediate: (value: { x?: number; y?: number; z?: number }) => void;
  stop: () => void;
} {
  const springX = useSpringTransition(initial.x, config);
  const springY = useSpringTransition(initial.y, config);
  const springZ = useSpringTransition(initial.z ?? 0, config);

  const value = useMemo(
    () => ({
      x: springX.value,
      y: springY.value,
      z: springZ.value,
    }),
    [springX.value, springY.value, springZ.value]
  );

  const isActive = springX.isActive || springY.isActive || springZ.isActive;

  const set = useCallback(
    (target: { x?: number; y?: number; z?: number }) => {
      if (target.x !== undefined) springX.set(target.x);
      if (target.y !== undefined) springY.set(target.y);
      if (target.z !== undefined) springZ.set(target.z);
    },
    [springX, springY, springZ]
  );

  const setImmediate = useCallback(
    (newValue: { x?: number; y?: number; z?: number }) => {
      if (newValue.x !== undefined) springX.setImmediate(newValue.x);
      if (newValue.y !== undefined) springY.setImmediate(newValue.y);
      if (newValue.z !== undefined) springZ.setImmediate(newValue.z);
    },
    [springX, springY, springZ]
  );

  const stop = useCallback(() => {
    springX.stop();
    springY.stop();
    springZ.stop();
  }, [springX, springY, springZ]);

  return {
    value,
    isActive,
    set,
    setImmediate,
    stop,
  };
}

/**
 * Preset spring configurations
 */
export const SPRING_PRESETS = {
  /** Default VisionOS feel */
  default: {
    stiffness: VISIONOS_TIMING.stiffness,
    damping: VISIONOS_TIMING.damping,
    mass: VISIONOS_TIMING.mass,
  },
  /** Snappy, responsive feel */
  snappy: {
    stiffness: 400,
    damping: 30,
    mass: 0.8,
  },
  /** Gentle, floating feel */
  gentle: {
    stiffness: 100,
    damping: 20,
    mass: 1.2,
  },
  /** Bouncy, playful feel */
  bouncy: {
    stiffness: 300,
    damping: 15,
    mass: 1,
  },
  /** Heavy, deliberate feel */
  heavy: {
    stiffness: 150,
    damping: 35,
    mass: 2,
  },
} as const;
