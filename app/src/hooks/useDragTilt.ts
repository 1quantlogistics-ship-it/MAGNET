/**
 * MAGNET UI Drag Tilt Hook
 *
 * VisionOS-style 3D tilt effect during drag operations.
 * Creates spatial depth feedback when dragging elements.
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { getDPRAdjustedValue, VISIONOS_TIMING } from '../types/common';
import { animationScheduler, EASING } from '../systems/AnimationScheduler';
import { generateId } from '../types/common';

/**
 * Drag tilt configuration
 */
interface UseDragTiltConfig {
  /** Maximum rotation in degrees */
  maxRotation?: number;
  /** Lift amount on drag (translateZ) */
  liftAmount?: number;
  /** Scale factor during drag */
  dragScale?: number;
  /** Enable the effect */
  enabled?: boolean;
  /** Smoothing duration */
  smoothing?: number;
  /** Sensitivity multiplier */
  sensitivity?: number;
}

/**
 * Drag tilt state
 */
interface DragTiltState {
  /** Whether currently dragging */
  isDragging: boolean;
  /** Current rotation X */
  rotateX: number;
  /** Current rotation Y */
  rotateY: number;
  /** Current lift (translateZ) */
  lift: number;
  /** Current scale */
  scale: number;
  /** Drag start position */
  dragStart: { x: number; y: number } | null;
  /** Current drag position */
  dragCurrent: { x: number; y: number } | null;
  /** Drag delta from start */
  delta: { x: number; y: number };
}

/**
 * Drag tilt return interface
 */
interface UseDragTiltReturn {
  /** Ref to attach to draggable element */
  ref: React.RefObject<HTMLElement>;
  /** Current tilt state */
  tilt: DragTiltState;
  /** CSS transform string */
  transform: string;
  /** CSS styles for tilt effect */
  style: React.CSSProperties;
  /** Event handlers */
  handlers: {
    onPointerDown: (e: React.PointerEvent) => void;
    onPointerMove: (e: React.PointerEvent) => void;
    onPointerUp: (e: React.PointerEvent) => void;
    onPointerCancel: (e: React.PointerEvent) => void;
  };
  /** Start drag manually */
  startDrag: (x: number, y: number) => void;
  /** End drag manually */
  endDrag: () => void;
  /** Reset tilt */
  reset: () => void;
}

/**
 * Clamp value between min and max
 */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Hook for VisionOS-style drag tilt effect
 */
export function useDragTilt(config: UseDragTiltConfig = {}): UseDragTiltReturn {
  const {
    maxRotation = 15,
    liftAmount = 20,
    dragScale = 1.02,
    enabled = true,
    smoothing = 100,
    sensitivity = 0.1,
  } = config;

  const ref = useRef<HTMLElement>(null);
  const animationIdRef = useRef<string | null>(null);
  const isMountedRef = useRef(true);

  const [tilt, setTilt] = useState<DragTiltState>({
    isDragging: false,
    rotateX: 0,
    rotateY: 0,
    lift: 0,
    scale: 1,
    dragStart: null,
    dragCurrent: null,
    delta: { x: 0, y: 0 },
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
   * Animate tilt values
   */
  const animateTilt = useCallback(
    (targetRotateX: number, targetRotateY: number, targetLift: number, targetScale: number) => {
      if (!isMountedRef.current) return;

      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }

      const startRotateX = tilt.rotateX;
      const startRotateY = tilt.rotateY;
      const startLift = tilt.lift;
      const startScale = tilt.scale;

      const id = generateId('tilt');
      animationIdRef.current = id;

      animationScheduler.schedule(id, {
        duration: smoothing,
        easing: EASING.spring,
        onUpdate: (progress) => {
          if (!isMountedRef.current) return;

          setTilt((prev) => ({
            ...prev,
            rotateX: startRotateX + (targetRotateX - startRotateX) * progress,
            rotateY: startRotateY + (targetRotateY - startRotateY) * progress,
            lift: startLift + (targetLift - startLift) * progress,
            scale: startScale + (targetScale - startScale) * progress,
          }));
        },
        onComplete: () => {
          animationIdRef.current = null;
        },
      });
    },
    [tilt.rotateX, tilt.rotateY, tilt.lift, tilt.scale, smoothing]
  );

  /**
   * Start drag
   */
  const startDrag = useCallback(
    (x: number, y: number) => {
      if (!enabled || !isMountedRef.current) return;

      setTilt((prev) => ({
        ...prev,
        isDragging: true,
        dragStart: { x, y },
        dragCurrent: { x, y },
        delta: { x: 0, y: 0 },
      }));

      // Animate to lifted state
      animateTilt(0, 0, liftAmount, dragScale);
    },
    [enabled, liftAmount, dragScale, animateTilt]
  );

  /**
   * Update drag position
   */
  const updateDrag = useCallback(
    (x: number, y: number) => {
      if (!tilt.isDragging || !tilt.dragStart || !isMountedRef.current) return;

      const deltaX = x - tilt.dragStart.x;
      const deltaY = y - tilt.dragStart.y;

      // Calculate rotation based on drag velocity
      const rotateY = clamp(deltaX * sensitivity, -maxRotation, maxRotation);
      const rotateX = clamp(-deltaY * sensitivity, -maxRotation, maxRotation);

      setTilt((prev) => ({
        ...prev,
        dragCurrent: { x, y },
        delta: { x: deltaX, y: deltaY },
        rotateX,
        rotateY,
        lift: liftAmount,
        scale: dragScale,
      }));
    },
    [tilt.isDragging, tilt.dragStart, maxRotation, liftAmount, dragScale, sensitivity]
  );

  /**
   * End drag
   */
  const endDrag = useCallback(() => {
    if (!isMountedRef.current) return;

    setTilt((prev) => ({
      ...prev,
      isDragging: false,
      dragStart: null,
      dragCurrent: null,
    }));

    // Animate back to neutral
    animateTilt(0, 0, 0, 1);
  }, [animateTilt]);

  /**
   * Reset tilt
   */
  const reset = useCallback(() => {
    setTilt({
      isDragging: false,
      rotateX: 0,
      rotateY: 0,
      lift: 0,
      scale: 1,
      dragStart: null,
      dragCurrent: null,
      delta: { x: 0, y: 0 },
    });
  }, []);

  /**
   * Pointer event handlers
   */
  const handlers = useMemo(
    () => ({
      onPointerDown: (e: React.PointerEvent) => {
        if (!enabled) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        startDrag(e.clientX, e.clientY);
      },
      onPointerMove: (e: React.PointerEvent) => {
        if (!enabled || !tilt.isDragging) return;
        updateDrag(e.clientX, e.clientY);
      },
      onPointerUp: (e: React.PointerEvent) => {
        if (!enabled) return;
        e.currentTarget.releasePointerCapture(e.pointerId);
        endDrag();
      },
      onPointerCancel: (e: React.PointerEvent) => {
        if (!enabled) return;
        e.currentTarget.releasePointerCapture(e.pointerId);
        endDrag();
      },
    }),
    [enabled, tilt.isDragging, startDrag, updateDrag, endDrag]
  );

  /**
   * Generate CSS transform string
   */
  const transform = useMemo(() => {
    const lift = getDPRAdjustedValue(tilt.lift);
    return `perspective(1000px) rotateX(${tilt.rotateX}deg) rotateY(${tilt.rotateY}deg) translateZ(${lift}px) scale(${tilt.scale})`;
  }, [tilt.rotateX, tilt.rotateY, tilt.lift, tilt.scale]);

  /**
   * CSS styles for tilt effect
   */
  const style: React.CSSProperties = useMemo(
    () => ({
      transform,
      transformStyle: 'preserve-3d' as const,
      cursor: tilt.isDragging ? 'grabbing' : 'grab',
      willChange: tilt.isDragging ? 'transform' : 'auto',
      transition: tilt.isDragging ? 'none' : `transform ${VISIONOS_TIMING.microBounce}ms ease`,
      touchAction: 'none',
    }),
    [transform, tilt.isDragging]
  );

  return {
    ref: ref as React.RefObject<HTMLElement>,
    tilt,
    transform,
    style,
    handlers,
    startDrag,
    endDrag,
    reset,
  };
}

/**
 * Hook for hover-based tilt (no drag)
 */
export function useHoverTilt(
  config: {
    maxRotation?: number;
    enabled?: boolean;
    smoothing?: number;
  } = {}
): {
  ref: React.RefObject<HTMLElement>;
  style: React.CSSProperties;
  handlers: {
    onMouseMove: (e: React.MouseEvent) => void;
    onMouseLeave: () => void;
  };
} {
  const { maxRotation = 10, enabled = true, smoothing = 100 } = config;

  const ref = useRef<HTMLElement>(null);
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
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

  const animateRotation = useCallback(
    (targetX: number, targetY: number) => {
      if (!isMountedRef.current) return;

      if (animationIdRef.current) {
        animationScheduler.cancel(animationIdRef.current);
      }

      const startX = rotation.x;
      const startY = rotation.y;

      const id = generateId('hoverTilt');
      animationIdRef.current = id;

      animationScheduler.schedule(id, {
        duration: smoothing,
        easing: EASING.easeOut,
        onUpdate: (progress) => {
          if (!isMountedRef.current) return;
          setRotation({
            x: startX + (targetX - startX) * progress,
            y: startY + (targetY - startY) * progress,
          });
        },
        onComplete: () => {
          animationIdRef.current = null;
        },
      });
    },
    [rotation.x, rotation.y, smoothing]
  );

  const handlers = useMemo(
    () => ({
      onMouseMove: (e: React.MouseEvent) => {
        if (!enabled || !ref.current) return;

        const rect = ref.current.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;

        const rotateX = -y * maxRotation * 2;
        const rotateY = x * maxRotation * 2;

        animateRotation(rotateX, rotateY);
      },
      onMouseLeave: () => {
        animateRotation(0, 0);
      },
    }),
    [enabled, maxRotation, animateRotation]
  );

  const style: React.CSSProperties = useMemo(
    () => ({
      transform: `perspective(1000px) rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
      transformStyle: 'preserve-3d' as const,
      transition: 'transform 0.1s ease',
    }),
    [rotation.x, rotation.y]
  );

  return {
    ref: ref as React.RefObject<HTMLElement>,
    style,
    handlers,
  };
}
