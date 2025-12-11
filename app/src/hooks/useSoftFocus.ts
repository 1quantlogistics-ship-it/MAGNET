/**
 * MAGNET UI Soft Focus Hook
 *
 * VisionOS-style soft focus management for panels.
 * Handles focus transitions, blur effects, and panel depth.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { PanelId, PanelDepth } from '../types/common';
import {
  focusStore,
  setFocusedPanel,
  clearFocus,
  isPanelFocused,
  shouldPanelBlur,
  getPanelBlurIntensity,
  getPanelOpacity,
  lockFocus,
  unlockFocus,
  isFocusLocked,
} from '../stores/domain/focusStore';
import { useAnimatedValue } from './useAnimatedValue';
import { VISIONOS_TIMING } from '../types/common';

/**
 * Soft focus hook configuration
 */
interface UseSoftFocusConfig {
  /** Panel ID */
  panelId: PanelId;
  /** Panel depth layer */
  depth?: PanelDepth;
  /** Enable focus on hover */
  focusOnHover?: boolean;
  /** Enable focus on click */
  focusOnClick?: boolean;
  /** Blur transition duration */
  blurDuration?: number;
  /** Maximum blur amount in pixels */
  maxBlur?: number;
}

/**
 * Soft focus return interface
 */
interface UseSoftFocusReturn {
  /** Whether this panel is focused */
  isFocused: boolean;
  /** Whether this panel should be blurred */
  isBlurred: boolean;
  /** Current blur intensity (0-1) */
  blurIntensity: number;
  /** Current opacity (0-1) */
  opacity: number;
  /** CSS blur value string */
  blurStyle: string;
  /** CSS styles for focus effect */
  focusStyles: React.CSSProperties;
  /** Focus this panel */
  focus: () => void;
  /** Clear focus */
  blur: () => void;
  /** Lock focus to this panel */
  lock: () => void;
  /** Unlock focus */
  unlock: () => void;
  /** Event handlers for focus behavior */
  handlers: {
    onMouseEnter?: () => void;
    onMouseLeave?: () => void;
    onClick?: () => void;
    onFocus?: () => void;
    onBlur?: () => void;
  };
}

/**
 * Hook for VisionOS-style soft focus
 */
export function useSoftFocus(config: UseSoftFocusConfig): UseSoftFocusReturn {
  const {
    panelId,
    depth = 'mid',
    focusOnHover = true,
    focusOnClick = true,
    blurDuration = VISIONOS_TIMING.focusTransition,
    maxBlur = 8,
  } = config;

  // Subscribe to focus store
  const [focusState, setFocusState] = useState(() => ({
    isFocused: isPanelFocused(panelId),
    isBlurred: shouldPanelBlur(panelId),
    blurIntensity: getPanelBlurIntensity(panelId),
    opacity: getPanelOpacity(panelId),
    isLocked: isFocusLocked(),
  }));

  // Animated values for smooth transitions
  const blurAnim = useAnimatedValue({
    initial: focusState.blurIntensity,
    duration: blurDuration,
  });

  const opacityAnim = useAnimatedValue({
    initial: focusState.opacity,
    duration: blurDuration,
    clamp: { min: 0, max: 1 },
  });

  // Subscribe to store changes
  useEffect(() => {
    const unsubscribe = focusStore.subscribe((state) => {
      const newFocusState = {
        isFocused: state.focusedPanelId === panelId,
        isBlurred:
          state.isFocusModeActive &&
          state.focusedPanelId !== null &&
          state.focusedPanelId !== panelId &&
          !state.focusExcludedPanels.includes(panelId),
        blurIntensity: getPanelBlurIntensity(panelId),
        opacity: getPanelOpacity(panelId),
        isLocked: state.isFocusLocked,
      };

      setFocusState(newFocusState);

      // Animate blur and opacity changes
      blurAnim.set(newFocusState.blurIntensity);
      opacityAnim.set(newFocusState.opacity);
    });

    return unsubscribe;
  }, [panelId, blurAnim, opacityAnim]);

  // Depth-based z-index calculation
  const depthZIndex = useMemo(() => {
    const baseZ = {
      near: 30,
      mid: 20,
      far: 10,
    }[depth];

    // Focused panel gets boost
    return focusState.isFocused ? baseZ + 5 : baseZ;
  }, [depth, focusState.isFocused]);

  // Focus handlers
  const focus = useCallback(() => {
    if (!focusState.isLocked || isFocusLocked()) {
      setFocusedPanel(panelId);
    }
  }, [panelId, focusState.isLocked]);

  const blur = useCallback(() => {
    if (focusState.isFocused && !focusState.isLocked) {
      clearFocus();
    }
  }, [focusState.isFocused, focusState.isLocked]);

  const lock = useCallback(() => {
    lockFocus(panelId);
  }, [panelId]);

  const unlock = useCallback(() => {
    unlockFocus();
  }, []);

  // Event handlers
  const handlers = useMemo(() => {
    const h: UseSoftFocusReturn['handlers'] = {};

    if (focusOnHover) {
      h.onMouseEnter = focus;
      h.onMouseLeave = () => {
        // Don't blur on mouse leave if locked
        if (!isFocusLocked()) {
          // Optionally keep focus or let it clear naturally
        }
      };
    }

    if (focusOnClick) {
      h.onClick = focus;
    }

    h.onFocus = focus;
    h.onBlur = () => {
      // Handle keyboard focus blur
    };

    return h;
  }, [focusOnHover, focusOnClick, focus]);

  // Compute blur CSS value
  const blurStyle = useMemo(() => {
    const blurAmount = blurAnim.value * maxBlur;
    return blurAmount > 0 ? `blur(${blurAmount}px)` : 'none';
  }, [blurAnim.value, maxBlur]);

  // Compute combined focus styles
  const focusStyles: React.CSSProperties = useMemo(
    () => ({
      filter: blurStyle,
      opacity: opacityAnim.value,
      zIndex: depthZIndex,
      transition: `z-index ${blurDuration}ms ease`,
      willChange: 'filter, opacity',
    }),
    [blurStyle, opacityAnim.value, depthZIndex, blurDuration]
  );

  return {
    isFocused: focusState.isFocused,
    isBlurred: focusState.isBlurred,
    blurIntensity: blurAnim.value,
    opacity: opacityAnim.value,
    blurStyle,
    focusStyles,
    focus,
    blur,
    lock,
    unlock,
    handlers,
  };
}

/**
 * Hook for checking if any panel is focused
 */
export function useHasActiveFocus(): boolean {
  const [hasActive, setHasActive] = useState(
    () => focusStore.getState().focusedPanelId !== null
  );

  useEffect(() => {
    const unsubscribe = focusStore.subscribe((state) => {
      setHasActive(state.focusedPanelId !== null);
    });
    return unsubscribe;
  }, []);

  return hasActive;
}

/**
 * Hook for getting the currently focused panel
 */
export function useFocusedPanel(): PanelId | null {
  const [focused, setFocused] = useState(
    () => focusStore.getState().focusedPanelId
  );

  useEffect(() => {
    const unsubscribe = focusStore.subscribe((state) => {
      setFocused(state.focusedPanelId);
    });
    return unsubscribe;
  }, []);

  return focused;
}

/**
 * Hook for focus mode control
 */
export function useFocusMode(): {
  isActive: boolean;
  toggle: () => void;
  enable: () => void;
  disable: () => void;
} {
  const [isActive, setIsActive] = useState(
    () => focusStore.getState().isFocusModeActive
  );

  useEffect(() => {
    const unsubscribe = focusStore.subscribe((state) => {
      setIsActive(state.isFocusModeActive);
    });
    return unsubscribe;
  }, []);

  const toggle = useCallback(() => {
    focusStore.getState()._update((state) => ({
      isFocusModeActive: !state.isFocusModeActive,
    }));
  }, []);

  const enable = useCallback(() => {
    focusStore.getState()._update(() => ({
      isFocusModeActive: true,
    }));
  }, []);

  const disable = useCallback(() => {
    focusStore.getState()._update(() => ({
      isFocusModeActive: false,
    }));
  }, []);

  return { isActive, toggle, enable, disable };
}
