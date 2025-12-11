/**
 * MAGNET UI Animation Scheduler Hook
 *
 * React hook for lifecycle-aware animation scheduling.
 * FM4 Compliance: Handles cleanup, cancellation, and stale closure prevention.
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import {
  animationScheduler,
  EASING,
  type AnimationPriority,
} from '../systems/AnimationScheduler';
import { generateId } from '../types/common';

/**
 * Animation config for the hook
 */
interface UseAnimationConfig {
  /** Animation duration in ms */
  duration: number;
  /** Animation priority */
  priority?: AnimationPriority;
  /** Easing function */
  easing?: (t: number) => number;
  /** Start immediately on mount */
  autoStart?: boolean;
  /** Loop the animation */
  loop?: boolean;
  /** Delay before starting (ms) */
  delay?: number;
}

/**
 * Animation control interface
 */
interface AnimationControl {
  /** Current progress (0-1) */
  progress: number;
  /** Whether animation is running */
  isRunning: boolean;
  /** Start the animation */
  start: () => void;
  /** Stop/cancel the animation */
  stop: () => void;
  /** Reset to initial state */
  reset: () => void;
  /** Restart the animation */
  restart: () => void;
}

/**
 * Hook for scheduling lifecycle-aware animations
 */
export function useAnimationScheduler(
  onUpdate: (progress: number) => void,
  config: UseAnimationConfig
): AnimationControl {
  const {
    duration,
    priority = 'normal',
    easing = EASING.easeOut,
    autoStart = false,
    loop = false,
    delay = 0,
  } = config;

  const [progress, setProgress] = useState(0);
  const [isRunning, setIsRunning] = useState(false);

  // Refs for stable references
  const animationIdRef = useRef<string | null>(null);
  const onUpdateRef = useRef(onUpdate);
  const delayTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Keep onUpdate ref current to prevent stale closures
  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;

      // Cancel any pending delay
      if (delayTimerRef.current) {
        clearTimeout(delayTimerRef.current);
      }

      // Cancel running animation
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }
    };
  }, []);

  /**
   * Start the animation
   */
  const startAnimation = useCallback(() => {
    // Cancel any existing animation
    if (animationIdRef.current) {
      animationScheduler.cancel(animationIdRef.current);
    }

    // Clear any pending delay
    if (delayTimerRef.current) {
      clearTimeout(delayTimerRef.current);
      delayTimerRef.current = null;
    }

    const runAnimation = () => {
      if (!isMountedRef.current) return;

      const id = generateId('anim');
      animationIdRef.current = id;
      setIsRunning(true);

      animationScheduler.schedule(id, {
        duration,
        priority,
        easing,
        onUpdate: (p) => {
          if (!isMountedRef.current) return;
          setProgress(p);
          onUpdateRef.current(p);
        },
        onComplete: () => {
          if (!isMountedRef.current) return;
          setIsRunning(false);
          animationIdRef.current = null;

          // Handle looping
          if (loop) {
            runAnimation();
          }
        },
        onCancel: () => {
          if (!isMountedRef.current) return;
          setIsRunning(false);
        },
      });
    };

    // Handle delay
    if (delay > 0) {
      delayTimerRef.current = setTimeout(runAnimation, delay);
    } else {
      runAnimation();
    }
  }, [duration, priority, easing, loop, delay]);

  /**
   * Stop the animation
   */
  const stopAnimation = useCallback(() => {
    if (delayTimerRef.current) {
      clearTimeout(delayTimerRef.current);
      delayTimerRef.current = null;
    }

    if (animationIdRef.current) {
      animationScheduler.cancel(animationIdRef.current);
      animationIdRef.current = null;
    }

    setIsRunning(false);
  }, []);

  /**
   * Reset to initial state
   */
  const resetAnimation = useCallback(() => {
    stopAnimation();
    setProgress(0);
    onUpdateRef.current(0);
  }, [stopAnimation]);

  /**
   * Restart the animation
   */
  const restartAnimation = useCallback(() => {
    resetAnimation();
    startAnimation();
  }, [resetAnimation, startAnimation]);

  // Auto-start on mount
  useEffect(() => {
    if (autoStart) {
      startAnimation();
    }
  }, [autoStart, startAnimation]);

  return {
    progress,
    isRunning,
    start: startAnimation,
    stop: stopAnimation,
    reset: resetAnimation,
    restart: restartAnimation,
  };
}

/**
 * Hook for simple value transitions
 */
export function useAnimatedTransition<T extends number | { [key: string]: number }>(
  targetValue: T,
  duration: number = 400,
  easing: (t: number) => number = EASING.spring
): T {
  const [currentValue, setCurrentValue] = useState<T>(targetValue);
  const previousValueRef = useRef<T>(targetValue);
  const animationIdRef = useRef<string | null>(null);
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

  useEffect(() => {
    const from = previousValueRef.current;
    const to = targetValue;

    // Skip if values are the same
    if (JSON.stringify(from) === JSON.stringify(to)) return;

    // Cancel previous animation
    if (animationIdRef.current) {
      animationScheduler.cancel(animationIdRef.current);
    }

    const id = generateId('trans');
    animationIdRef.current = id;

    animationScheduler.schedule(id, {
      duration,
      easing,
      onUpdate: (progress) => {
        if (!isMountedRef.current) return;

        if (typeof from === 'number' && typeof to === 'number') {
          setCurrentValue((from + (to - from) * progress) as T);
        } else if (typeof from === 'object' && typeof to === 'object') {
          const interpolated: Record<string, number> = {};
          for (const key of Object.keys(to as object)) {
            const fromVal = (from as Record<string, number>)[key] ?? 0;
            const toVal = (to as Record<string, number>)[key] ?? 0;
            interpolated[key] = fromVal + (toVal - fromVal) * progress;
          }
          setCurrentValue(interpolated as T);
        }
      },
      onComplete: () => {
        if (!isMountedRef.current) return;
        previousValueRef.current = to;
        setCurrentValue(to);
        animationIdRef.current = null;
      },
    });

    return () => {
      if (animationIdRef.current === id) {
        animationScheduler.cancel(id);
      }
    };
  }, [targetValue, duration, easing]);

  return currentValue;
}

/**
 * Hook for presence animations (enter/exit)
 */
export function usePresenceAnimation(
  isPresent: boolean,
  config: {
    enterDuration?: number;
    exitDuration?: number;
    enterEasing?: (t: number) => number;
    exitEasing?: (t: number) => number;
    onExitComplete?: () => void;
  } = {}
): {
  isVisible: boolean;
  progress: number;
  isEntering: boolean;
  isExiting: boolean;
} {
  const {
    enterDuration = 400,
    exitDuration = 300,
    enterEasing = EASING.spring,
    exitEasing = EASING.easeOut,
    onExitComplete,
  } = config;

  const [isVisible, setIsVisible] = useState(isPresent);
  const [progress, setProgress] = useState(isPresent ? 1 : 0);
  const [isEntering, setIsEntering] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  const animationIdRef = useRef<string | null>(null);
  const onExitCompleteRef = useRef(onExitComplete);
  const isMountedRef = useRef(true);

  useEffect(() => {
    onExitCompleteRef.current = onExitComplete;
  }, [onExitComplete]);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }
    };
  }, []);

  useEffect(() => {
    // Cancel previous animation
    if (animationIdRef.current) {
      animationScheduler.cancel(animationIdRef.current);
    }

    const id = generateId('presence');
    animationIdRef.current = id;

    if (isPresent) {
      // Enter animation
      setIsVisible(true);
      setIsEntering(true);
      setIsExiting(false);

      animationScheduler.schedule(id, {
        duration: enterDuration,
        easing: enterEasing,
        onUpdate: (p) => {
          if (!isMountedRef.current) return;
          setProgress(p);
        },
        onComplete: () => {
          if (!isMountedRef.current) return;
          setIsEntering(false);
          animationIdRef.current = null;
        },
      });
    } else {
      // Exit animation
      setIsEntering(false);
      setIsExiting(true);

      animationScheduler.schedule(id, {
        duration: exitDuration,
        easing: exitEasing,
        onUpdate: (p) => {
          if (!isMountedRef.current) return;
          setProgress(1 - p);
        },
        onComplete: () => {
          if (!isMountedRef.current) return;
          setIsVisible(false);
          setIsExiting(false);
          onExitCompleteRef.current?.();
          animationIdRef.current = null;
        },
      });
    }

    return () => {
      if (animationIdRef.current === id) {
        animationScheduler.cancel(id);
      }
    };
  }, [isPresent, enterDuration, exitDuration, enterEasing, exitEasing]);

  return {
    isVisible,
    progress,
    isEntering,
    isExiting,
  };
}

export { EASING };
