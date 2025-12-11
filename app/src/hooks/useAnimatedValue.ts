/**
 * MAGNET UI Animated Value Hook
 *
 * Lifecycle-aware animated value with cancellation support.
 * FM4 Compliance: Prevents stale closures, handles cleanup properly.
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { animationScheduler, EASING } from '../systems/AnimationScheduler';
import { generateId } from '../types/common';
import { VISIONOS_TIMING } from '../types/common';

/**
 * Animated value configuration
 */
interface AnimatedValueConfig {
  /** Initial value */
  initial?: number;
  /** Animation duration in ms */
  duration?: number;
  /** Easing function */
  easing?: (t: number) => number;
  /** Clamp values between min/max */
  clamp?: { min: number; max: number };
  /** Round to specified decimal places */
  precision?: number;
}

/**
 * Animated value control interface
 */
interface AnimatedValueControl {
  /** Current animated value */
  value: number;
  /** Target value */
  target: number;
  /** Whether currently animating */
  isAnimating: boolean;
  /** Set new target value with animation */
  set: (value: number) => void;
  /** Set value immediately without animation */
  setImmediate: (value: number) => void;
  /** Reset to initial value */
  reset: () => void;
}

/**
 * Hook for lifecycle-aware animated values
 */
export function useAnimatedValue(
  config: AnimatedValueConfig = {}
): AnimatedValueControl {
  const {
    initial = 0,
    duration = VISIONOS_TIMING.cardExpand,
    easing = EASING.spring,
    clamp,
    precision,
  } = config;

  const [currentValue, setCurrentValue] = useState(initial);
  const [targetValue, setTargetValue] = useState(initial);
  const [isAnimating, setIsAnimating] = useState(false);

  const animationIdRef = useRef<string | null>(null);
  const startValueRef = useRef(initial);
  const isMountedRef = useRef(true);

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
   * Process value with clamp and precision
   */
  const processValue = useCallback(
    (value: number): number => {
      let processed = value;

      if (clamp) {
        processed = Math.max(clamp.min, Math.min(clamp.max, processed));
      }

      if (precision !== undefined) {
        const factor = Math.pow(10, precision);
        processed = Math.round(processed * factor) / factor;
      }

      return processed;
    },
    [clamp, precision]
  );

  /**
   * Set value with animation
   */
  const setValue = useCallback(
    (newTarget: number) => {
      const processedTarget = processValue(newTarget);

      // Skip if already at target
      if (processedTarget === targetValue && !isAnimating) {
        return;
      }

      setTargetValue(processedTarget);

      // Cancel existing animation
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }

      const id = generateId('animVal');
      animationIdRef.current = id;
      startValueRef.current = currentValue;
      setIsAnimating(true);

      animationScheduler.schedule(id, {
        duration,
        easing,
        onUpdate: (progress) => {
          if (!isMountedRef.current) return;

          const interpolated =
            startValueRef.current +
            (processedTarget - startValueRef.current) * progress;
          setCurrentValue(processValue(interpolated));
        },
        onComplete: () => {
          if (!isMountedRef.current) return;
          setCurrentValue(processedTarget);
          setIsAnimating(false);
          animationIdRef.current = null;
        },
        onCancel: () => {
          if (!isMountedRef.current) return;
          setIsAnimating(false);
        },
      });
    },
    [currentValue, targetValue, isAnimating, duration, easing, processValue]
  );

  /**
   * Set value immediately without animation
   */
  const setImmediate = useCallback(
    (value: number) => {
      const processed = processValue(value);

      // Cancel any running animation
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
        animationIdRef.current = null;
      }

      setCurrentValue(processed);
      setTargetValue(processed);
      setIsAnimating(false);
    },
    [processValue]
  );

  /**
   * Reset to initial value
   */
  const reset = useCallback(() => {
    setValue(initial);
  }, [initial, setValue]);

  return {
    value: currentValue,
    target: targetValue,
    isAnimating,
    set: setValue,
    setImmediate,
    reset,
  };
}

/**
 * Hook for animated vector values (x, y, z)
 */
export function useAnimatedVector(
  config: {
    initial?: { x: number; y: number; z?: number };
    duration?: number;
    easing?: (t: number) => number;
  } = {}
): {
  value: { x: number; y: number; z: number };
  isAnimating: boolean;
  set: (value: { x?: number; y?: number; z?: number }) => void;
  setImmediate: (value: { x?: number; y?: number; z?: number }) => void;
  reset: () => void;
} {
  const {
    initial = { x: 0, y: 0, z: 0 },
    duration = VISIONOS_TIMING.cardExpand,
    easing = EASING.spring,
  } = config;

  const [current, setCurrent] = useState({
    x: initial.x,
    y: initial.y,
    z: initial.z ?? 0,
  });
  const [target, setTarget] = useState({
    x: initial.x,
    y: initial.y,
    z: initial.z ?? 0,
  });
  const [isAnimating, setIsAnimating] = useState(false);

  const animationIdRef = useRef<string | null>(null);
  const startRef = useRef(current);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }
    };
  }, []);

  const setValue = useCallback(
    (newTarget: { x?: number; y?: number; z?: number }) => {
      const fullTarget = {
        x: newTarget.x ?? target.x,
        y: newTarget.y ?? target.y,
        z: newTarget.z ?? target.z,
      };

      setTarget(fullTarget);

      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }

      const id = generateId('animVec');
      animationIdRef.current = id;
      startRef.current = current;
      setIsAnimating(true);

      animationScheduler.schedule(id, {
        duration,
        easing,
        onUpdate: (progress) => {
          if (!isMountedRef.current) return;

          setCurrent({
            x: startRef.current.x + (fullTarget.x - startRef.current.x) * progress,
            y: startRef.current.y + (fullTarget.y - startRef.current.y) * progress,
            z: startRef.current.z + (fullTarget.z - startRef.current.z) * progress,
          });
        },
        onComplete: () => {
          if (!isMountedRef.current) return;
          setCurrent(fullTarget);
          setIsAnimating(false);
          animationIdRef.current = null;
        },
        onCancel: () => {
          if (!isMountedRef.current) return;
          setIsAnimating(false);
        },
      });
    },
    [current, target, duration, easing]
  );

  const setImmediate = useCallback(
    (value: { x?: number; y?: number; z?: number }) => {
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
        animationIdRef.current = null;
      }

      const newValue = {
        x: value.x ?? current.x,
        y: value.y ?? current.y,
        z: value.z ?? current.z,
      };

      setCurrent(newValue);
      setTarget(newValue);
      setIsAnimating(false);
    },
    [current]
  );

  const reset = useCallback(() => {
    setValue({
      x: initial.x,
      y: initial.y,
      z: initial.z ?? 0,
    });
  }, [initial, setValue]);

  return {
    value: current,
    isAnimating,
    set: setValue,
    setImmediate,
    reset,
  };
}

/**
 * Hook for animating CSS transform values
 */
export function useAnimatedTransform(
  config: {
    initial?: {
      x?: number;
      y?: number;
      scale?: number;
      rotate?: number;
      opacity?: number;
    };
    duration?: number;
    easing?: (t: number) => number;
  } = {}
): {
  style: React.CSSProperties;
  isAnimating: boolean;
  set: (value: {
    x?: number;
    y?: number;
    scale?: number;
    rotate?: number;
    opacity?: number;
  }) => void;
  setImmediate: (value: {
    x?: number;
    y?: number;
    scale?: number;
    rotate?: number;
    opacity?: number;
  }) => void;
  reset: () => void;
} {
  const {
    initial = {},
    duration = VISIONOS_TIMING.cardExpand,
    easing = EASING.spring,
  } = config;

  const defaultValues = {
    x: initial.x ?? 0,
    y: initial.y ?? 0,
    scale: initial.scale ?? 1,
    rotate: initial.rotate ?? 0,
    opacity: initial.opacity ?? 1,
  };

  const [current, setCurrent] = useState(defaultValues);
  const [target, setTarget] = useState(defaultValues);
  const [isAnimating, setIsAnimating] = useState(false);

  const animationIdRef = useRef<string | null>(null);
  const startRef = useRef(current);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }
    };
  }, []);

  const setValue = useCallback(
    (newTarget: typeof defaultValues) => {
      const fullTarget = {
        x: newTarget.x ?? target.x,
        y: newTarget.y ?? target.y,
        scale: newTarget.scale ?? target.scale,
        rotate: newTarget.rotate ?? target.rotate,
        opacity: newTarget.opacity ?? target.opacity,
      };

      setTarget(fullTarget);

      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }

      const id = generateId('animTrans');
      animationIdRef.current = id;
      startRef.current = current;
      setIsAnimating(true);

      animationScheduler.schedule(id, {
        duration,
        easing,
        onUpdate: (progress) => {
          if (!isMountedRef.current) return;

          setCurrent({
            x: startRef.current.x + (fullTarget.x - startRef.current.x) * progress,
            y: startRef.current.y + (fullTarget.y - startRef.current.y) * progress,
            scale:
              startRef.current.scale +
              (fullTarget.scale - startRef.current.scale) * progress,
            rotate:
              startRef.current.rotate +
              (fullTarget.rotate - startRef.current.rotate) * progress,
            opacity:
              startRef.current.opacity +
              (fullTarget.opacity - startRef.current.opacity) * progress,
          });
        },
        onComplete: () => {
          if (!isMountedRef.current) return;
          setCurrent(fullTarget);
          setIsAnimating(false);
          animationIdRef.current = null;
        },
        onCancel: () => {
          if (!isMountedRef.current) return;
          setIsAnimating(false);
        },
      });
    },
    [current, target, duration, easing]
  );

  const setImmediate = useCallback(
    (value: typeof defaultValues) => {
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
        animationIdRef.current = null;
      }

      const newValue = {
        x: value.x ?? current.x,
        y: value.y ?? current.y,
        scale: value.scale ?? current.scale,
        rotate: value.rotate ?? current.rotate,
        opacity: value.opacity ?? current.opacity,
      };

      setCurrent(newValue);
      setTarget(newValue);
      setIsAnimating(false);
    },
    [current]
  );

  const reset = useCallback(() => {
    setValue(defaultValues);
  }, [defaultValues, setValue]);

  const style: React.CSSProperties = useMemo(
    () => ({
      transform: `translate(${current.x}px, ${current.y}px) scale(${current.scale}) rotate(${current.rotate}deg)`,
      opacity: current.opacity,
    }),
    [current]
  );

  return {
    style,
    isAnimating,
    set: setValue,
    setImmediate,
    reset,
  };
}
