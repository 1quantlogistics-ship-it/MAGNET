/**
 * MAGNET UI Hooks
 *
 * Lifecycle-aware hooks for VisionOS-style animations and effects.
 */

// Animation Scheduler
export {
  useAnimationScheduler,
  useAnimatedTransition,
  usePresenceAnimation,
  EASING,
} from './useAnimationScheduler';

// Animated Value
export {
  useAnimatedValue,
  useAnimatedVector,
  useAnimatedTransform,
} from './useAnimatedValue';

// Soft Focus
export {
  useSoftFocus,
  useHasActiveFocus,
  useFocusedPanel,
  useFocusMode,
} from './useSoftFocus';

// Proximity Glow
export {
  useProximityGlow,
  useHoverGlow,
} from './useProximityGlow';

// Parallax
export {
  useParallax,
  useLayerParallax,
} from './useParallax';

// Drag Tilt
export {
  useDragTilt,
  useHoverTilt,
} from './useDragTilt';

// Dynamic Shadow
export {
  useDynamicShadow,
  useElevationShadow,
  useInsetShadow,
} from './useDynamicShadow';

// Spring Transition
export {
  useSpringTransition,
  useSpringPresence,
  useSpringVector,
  SPRING_PRESETS,
} from './useSpringTransition';
