/**
 * MAGNET UI Module 03: Chat Components
 *
 * Adjustable chat window component exports.
 * VisionOS-style frameless glass window system.
 */

// AIPresenceOrb - 3-layer concentric field system
export {
  AIPresenceOrb,
  type AIPresenceOrbProps,
} from './AIPresenceOrb';

// ChatBubble - Glass bubble with lighting
export {
  ChatBubble,
  type ChatBubbleProps,
} from './ChatBubble';

// ChatHeader - Minimal chrome header
export {
  ChatHeader,
  type ChatHeaderProps,
} from './ChatHeader';

// ChatInput - Soft floating input
export {
  ChatInput,
  type ChatInputProps,
} from './ChatInput';

// ChatMinimized - Floating hologram pill
export {
  ChatMinimized,
  type ChatMinimizedProps,
} from './ChatMinimized';

// TypingIndicator - Animated dots
export {
  TypingIndicator,
  type TypingIndicatorProps,
} from './TypingIndicator';

// Re-export types from types/chat.ts for convenience
export type {
  ChatWindowState,
  MessageRole,
  MessageStatus,
  ChatMessage,
  ChatAttachment,
  ChatWindowPosition,
  ChatWindowSize,
  DockState,
  FloatState,
  ChatContext,
} from '../../types/chat';

// Re-export motion constants
export { VISIONOS_MOTION, DEFAULT_WINDOW_CONSTRAINTS, DEFAULT_DOCK_SETTINGS } from '../../types/chat';
