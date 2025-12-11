/**
 * MAGNET UI Focus Store
 *
 * Panel focus state management for VisionOS-style soft focus.
 */

import { createStore } from '../contracts/StoreFactory';
import type { PanelId, PanelFocusState } from '../../types/common';

/**
 * Focus store state
 */
export interface FocusStoreState {
  /** Currently focused panel */
  focusedPanelId: PanelId | null;

  /** Previously focused panel */
  previousPanelId: PanelId | null;

  /** Timestamp of last focus change */
  lastFocusChangeTimestamp: number;

  /** Whether focus mode is active (blurs unfocused panels) */
  isFocusModeActive: boolean;

  /** Panels that are excluded from focus blur */
  focusExcludedPanels: PanelId[];

  /** Focus lock (prevents focus changes) */
  isFocusLocked: boolean;

  /** Locked focus target */
  lockedPanelId: PanelId | null;
}

/**
 * Initial focus state
 */
const initialFocusState: FocusStoreState = {
  focusedPanelId: null,
  previousPanelId: null,
  lastFocusChangeTimestamp: 0,
  isFocusModeActive: true,
  focusExcludedPanels: [],
  isFocusLocked: false,
  lockedPanelId: null,
};

/**
 * Create the focus store
 */
export const focusStore = createStore<FocusStoreState>({
  name: 'focus',
  initialState: initialFocusState,
  readOnlyFields: [],
  readWriteFields: [
    'focusedPanelId',
    'previousPanelId',
    'lastFocusChangeTimestamp',
    'isFocusModeActive',
    'focusExcludedPanels',
    'isFocusLocked',
    'lockedPanelId',
  ],
});

// ============================================================================
// Focus Actions
// ============================================================================

/**
 * Set focused panel
 */
export function setFocusedPanel(panelId: PanelId | null): void {
  const state = focusStore.getState().readOnly;

  // Ignore if locked
  if (state.isFocusLocked && panelId !== state.lockedPanelId) {
    return;
  }

  // Ignore if already focused
  if (state.focusedPanelId === panelId) {
    return;
  }

  focusStore.getState()._update((prev) => ({
    previousPanelId: prev.focusedPanelId,
    focusedPanelId: panelId,
    lastFocusChangeTimestamp: Date.now(),
  }));
}

/**
 * Clear focus (no panel focused)
 */
export function clearFocus(): void {
  const state = focusStore.getState().readOnly;

  // Can't clear if locked
  if (state.isFocusLocked) {
    return;
  }

  focusStore.getState()._update((prev) => ({
    previousPanelId: prev.focusedPanelId,
    focusedPanelId: null,
    lastFocusChangeTimestamp: Date.now(),
  }));
}

/**
 * Restore previous focus
 */
export function restorePreviousFocus(): void {
  const state = focusStore.getState().readOnly;

  if (state.previousPanelId && !state.isFocusLocked) {
    setFocusedPanel(state.previousPanelId);
  }
}

/**
 * Toggle focus mode (blur effect)
 */
export function setFocusModeActive(active: boolean): void {
  focusStore.getState()._update(() => ({
    isFocusModeActive: active,
  }));
}

/**
 * Add panel to focus exclusion list
 */
export function excludePanelFromFocus(panelId: PanelId): void {
  focusStore.getState()._update((state) => {
    if (state.focusExcludedPanels.includes(panelId)) {
      return {};
    }
    return {
      focusExcludedPanels: [...state.focusExcludedPanels, panelId],
    };
  });
}

/**
 * Remove panel from focus exclusion list
 */
export function includePanelInFocus(panelId: PanelId): void {
  focusStore.getState()._update((state) => ({
    focusExcludedPanels: state.focusExcludedPanels.filter((id) => id !== panelId),
  }));
}

/**
 * Lock focus to a specific panel
 */
export function lockFocus(panelId: PanelId): void {
  focusStore.getState()._update(() => ({
    isFocusLocked: true,
    lockedPanelId: panelId,
    focusedPanelId: panelId,
    lastFocusChangeTimestamp: Date.now(),
  }));
}

/**
 * Unlock focus
 */
export function unlockFocus(): void {
  focusStore.getState()._update(() => ({
    isFocusLocked: false,
    lockedPanelId: null,
  }));
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get current focus state
 */
export function getFocusState(): PanelFocusState {
  const state = focusStore.getState().readOnly;
  return {
    panelId: state.focusedPanelId,
    previousPanelId: state.previousPanelId,
    timestamp: state.lastFocusChangeTimestamp,
  };
}

/**
 * Check if a panel is focused
 */
export function isPanelFocused(panelId: PanelId): boolean {
  const state = focusStore.getState().readOnly;
  return state.focusedPanelId === panelId;
}

/**
 * Check if a panel should be blurred
 */
export function shouldPanelBlur(panelId: PanelId): boolean {
  const state = focusStore.getState().readOnly;

  // No blur if focus mode is off
  if (!state.isFocusModeActive) {
    return false;
  }

  // No blur if nothing is focused
  if (state.focusedPanelId === null) {
    return false;
  }

  // No blur if this panel is focused
  if (state.focusedPanelId === panelId) {
    return false;
  }

  // No blur if panel is excluded
  if (state.focusExcludedPanels.includes(panelId)) {
    return false;
  }

  return true;
}

/**
 * Check if focus is locked
 */
export function isFocusLocked(): boolean {
  return focusStore.getState().readOnly.isFocusLocked;
}

/**
 * Get focused panel ID
 */
export function getFocusedPanelId(): PanelId | null {
  return focusStore.getState().readOnly.focusedPanelId;
}

/**
 * Check if any panel is focused
 */
export function hasActiveFocus(): boolean {
  return focusStore.getState().readOnly.focusedPanelId !== null;
}

// ============================================================================
// Computed Values
// ============================================================================

/**
 * Get blur intensity for a panel (0-1)
 */
export function getPanelBlurIntensity(panelId: PanelId): number {
  if (!shouldPanelBlur(panelId)) {
    return 0;
  }

  // Could implement distance-based blur intensity here
  // For now, return fixed blur for unfocused panels
  return 1;
}

/**
 * Get opacity for a panel (0-1)
 */
export function getPanelOpacity(panelId: PanelId): number {
  if (!shouldPanelBlur(panelId)) {
    return 1;
  }

  // VisionOS uses reduced opacity for unfocused panels
  return 0.65;
}
