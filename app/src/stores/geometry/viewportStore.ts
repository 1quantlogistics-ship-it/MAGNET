/**
 * MAGNET UI Viewport Store
 *
 * Camera, parallax, and focus state (UI-only).
 * Split from geometry per FM7 architectural fix.
 */

import { createStore } from '../contracts/StoreFactory';
import type {
  ViewportState,
  CameraState,
  CameraAnimationTarget,
  ParallaxState,
  FocusBlurState,
} from '../../types/geometry';
import {
  INITIAL_VIEWPORT_STATE,
  DEFAULT_CAMERA_STATE,
  DEFAULT_PARALLAX_STATE,
  DEFAULT_FOCUS_BLUR_STATE,
} from '../../types/geometry';
import type { Point3D } from '../../types/common';

/**
 * Create the viewport store
 */
export const viewportStore = createStore<ViewportState>({
  name: 'viewport',
  initialState: INITIAL_VIEWPORT_STATE,
  readOnlyFields: [], // All viewport state is UI-driven
  readWriteFields: [
    'camera',
    'cameraAnimating',
    'cameraAnimationTarget',
    'parallax',
    'focusBlur',
    'pointerPosition',
    'isDragging',
    'width',
    'height',
    'devicePixelRatio',
    'renderQuality',
    'antialias',
  ],
});

// ============================================================================
// Camera Actions
// ============================================================================

/**
 * Update camera state directly
 */
export function updateCamera(updates: Partial<CameraState>): void {
  viewportStore.getState()._update((state) => ({
    camera: {
      ...state.camera,
      ...updates,
    },
  }));
}

/**
 * Animate camera to target position
 */
export function animateCamera(target: CameraAnimationTarget): void {
  viewportStore.getState()._update(() => ({
    cameraAnimating: true,
    cameraAnimationTarget: target,
  }));
}

/**
 * Complete camera animation
 */
export function completeCameraAnimation(): void {
  const state = viewportStore.getState().readOnly;
  const target = state.cameraAnimationTarget;

  if (!target) {
    viewportStore.getState()._update(() => ({
      cameraAnimating: false,
      cameraAnimationTarget: null,
    }));
    return;
  }

  viewportStore.getState()._update((state) => ({
    camera: {
      ...state.camera,
      ...(target.position && { position: target.position }),
      ...(target.target && { target: target.target }),
      ...(target.fov && { fov: target.fov }),
    },
    cameraAnimating: false,
    cameraAnimationTarget: null,
  }));
}

/**
 * Cancel camera animation
 */
export function cancelCameraAnimation(): void {
  viewportStore.getState()._update(() => ({
    cameraAnimating: false,
    cameraAnimationTarget: null,
  }));
}

/**
 * Reset camera to default position
 */
export function resetCamera(): void {
  viewportStore.getState()._update(() => ({
    camera: { ...DEFAULT_CAMERA_STATE },
    cameraAnimating: false,
    cameraAnimationTarget: null,
  }));
}

/**
 * Frame camera on a target position
 */
export function frameCameraOn(
  target: Point3D,
  distance: number = 10,
  duration: number = 600
): void {
  const currentCamera = viewportStore.getState().readOnly.camera;

  // Calculate camera position at specified distance
  const direction = {
    x: currentCamera.position.x - currentCamera.target.x,
    y: currentCamera.position.y - currentCamera.target.y,
    z: currentCamera.position.z - currentCamera.target.z,
  };

  // Normalize direction
  const length = Math.sqrt(
    direction.x ** 2 + direction.y ** 2 + direction.z ** 2
  );
  if (length > 0) {
    direction.x /= length;
    direction.y /= length;
    direction.z /= length;
  } else {
    // Default direction if at target
    direction.x = 0;
    direction.y = 0.3;
    direction.z = 1;
  }

  const newPosition: Point3D = {
    x: target.x + direction.x * distance,
    y: target.y + direction.y * distance,
    z: target.z + direction.z * distance,
  };

  animateCamera({
    position: newPosition,
    target,
    duration,
  });
}

// ============================================================================
// Parallax Actions
// ============================================================================

/**
 * Update parallax state
 */
export function updateParallax(updates: Partial<ParallaxState>): void {
  viewportStore.getState()._update((state) => ({
    parallax: {
      ...state.parallax,
      ...updates,
    },
  }));
}

/**
 * Set parallax offset based on pointer position
 */
export function setParallaxOffset(offset: Point3D): void {
  viewportStore.getState()._update((state) => ({
    parallax: {
      ...state.parallax,
      currentOffset: offset,
    },
  }));
}

/**
 * Enable/disable parallax
 */
export function setParallaxEnabled(enabled: boolean): void {
  viewportStore.getState()._update((state) => ({
    parallax: {
      ...state.parallax,
      enabled,
      currentOffset: enabled ? state.parallax.currentOffset : { x: 0, y: 0, z: 0 },
    },
  }));
}

/**
 * Reset parallax to defaults
 */
export function resetParallax(): void {
  viewportStore.getState()._update(() => ({
    parallax: { ...DEFAULT_PARALLAX_STATE },
  }));
}

// ============================================================================
// Focus Blur Actions
// ============================================================================

/**
 * Update focus blur state
 */
export function updateFocusBlur(updates: Partial<FocusBlurState>): void {
  viewportStore.getState()._update((state) => ({
    focusBlur: {
      ...state.focusBlur,
      ...updates,
    },
  }));
}

/**
 * Set focused mesh (for depth of field effect)
 */
export function setFocusedMesh(meshId: string | null): void {
  viewportStore.getState()._update((state) => ({
    focusBlur: {
      ...state.focusBlur,
      focusedMeshId: meshId,
    },
  }));
}

/**
 * Enable/disable focus blur
 */
export function setFocusBlurEnabled(enabled: boolean): void {
  viewportStore.getState()._update((state) => ({
    focusBlur: {
      ...state.focusBlur,
      enabled,
    },
  }));
}

/**
 * Reset focus blur to defaults
 */
export function resetFocusBlur(): void {
  viewportStore.getState()._update(() => ({
    focusBlur: { ...DEFAULT_FOCUS_BLUR_STATE },
  }));
}

// ============================================================================
// Pointer & Drag Actions
// ============================================================================

/**
 * Update pointer position
 */
export function setPointerPosition(
  position: { x: number; y: number } | null
): void {
  viewportStore.getState()._update(() => ({
    pointerPosition: position,
  }));
}

/**
 * Set dragging state
 */
export function setDragging(isDragging: boolean): void {
  viewportStore.getState()._update(() => ({
    isDragging,
  }));
}

// ============================================================================
// Viewport Dimension Actions
// ============================================================================

/**
 * Update viewport dimensions
 */
export function updateViewportDimensions(
  width: number,
  height: number,
  devicePixelRatio?: number
): void {
  viewportStore.getState()._update((state) => ({
    width,
    height,
    devicePixelRatio: devicePixelRatio ?? state.devicePixelRatio,
  }));
}

/**
 * Set render quality
 */
export function setRenderQuality(
  quality: 'high' | 'medium' | 'low'
): void {
  viewportStore.getState()._update(() => ({
    renderQuality: quality,
  }));
}

/**
 * Toggle antialiasing
 */
export function setAntialias(enabled: boolean): void {
  viewportStore.getState()._update(() => ({
    antialias: enabled,
  }));
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get current camera state
 */
export function getCamera(): CameraState {
  return { ...viewportStore.getState().readOnly.camera };
}

/**
 * Get parallax state
 */
export function getParallax(): ParallaxState {
  return { ...viewportStore.getState().readOnly.parallax };
}

/**
 * Get focus blur state
 */
export function getFocusBlur(): FocusBlurState {
  return { ...viewportStore.getState().readOnly.focusBlur };
}

/**
 * Check if camera is animating
 */
export function isCameraAnimating(): boolean {
  return viewportStore.getState().readOnly.cameraAnimating;
}

/**
 * Get viewport aspect ratio
 */
export function getAspectRatio(): number {
  const { width, height } = viewportStore.getState().readOnly;
  return height > 0 ? width / height : 1;
}

/**
 * Get viewport size in device pixels
 */
export function getDevicePixelSize(): { width: number; height: number } {
  const state = viewportStore.getState().readOnly;
  return {
    width: state.width * state.devicePixelRatio,
    height: state.height * state.devicePixelRatio,
  };
}
