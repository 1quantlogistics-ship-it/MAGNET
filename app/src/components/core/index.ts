/**
 * MAGNET UI Core Components
 *
 * VisionOS-style core UI components.
 */

// Floating Micro Window
export {
  FloatingMicroWindow,
  type FloatingMicroWindowProps,
  type FloatingMicroWindowEvents,
  type FloatingMicroWindowContract,
} from './FloatingMicroWindow';

// Pill Button
export {
  PillButton,
  IconPillButton,
  type PillButtonProps,
} from './PillButton';

// Glass Card
export {
  GlassCard,
  GlassCardWithHeader,
  type GlassCardProps,
  type GlassCardWithHeaderProps,
} from './GlassCard';

// Orb Presence
export {
  OrbPresence,
  MiniOrb,
  type OrbPresenceProps,
  type OrbState,
} from './OrbPresence';

// Scene Lighting
export {
  SceneLighting,
  useSceneLighting,
  type SceneLightingProps,
  type LightConfig,
} from './SceneLighting';
