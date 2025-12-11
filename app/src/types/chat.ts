/**
 * MAGNET UI Module 03: Chat Types
 *
 * Type definitions for the adjustable chat window system.
 * VisionOS-aligned frameless glass window with spatial features.
 */

import { SCHEMA_VERSION } from './schema-version';

// =============================================================================
// Window States
// =============================================================================

/**
 * Chat window display states
 */
export type ChatWindowState = 'expanded' | 'docked' | 'minimized' | 'fullscreen';

/**
 * Dock sides for docked window state
 */
export type DockSide = 'right' | 'left';

// =============================================================================
// Message Types
// =============================================================================

/**
 * Message sender role
 */
export type MessageRole = 'user' | 'assistant' | 'system';

/**
 * Message delivery/processing status
 */
export type MessageStatus = 'sending' | 'sent' | 'error' | 'streaming';

/**
 * Attachment types for messages
 */
export type AttachmentType = 'image' | 'file' | 'component-snapshot';

/**
 * Chat message attachment
 */
export interface ChatAttachment {
  id: string;
  type: AttachmentType;
  name: string;
  url?: string;
  thumbnailUrl?: string;
  size?: number;
  mimeType?: string;
}

/**
 * Chat message
 */
export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  status: MessageStatus;
  /** Related component ID for context */
  relatedComponentId?: string;
  /** Related recommendation ID for context */
  relatedRecommendationId?: string;
  /** Message attachments */
  attachments?: ChatAttachment[];
  /** Error message if status is 'error' */
  error?: string;
}

// =============================================================================
// Position & Size
// =============================================================================

/**
 * 2D position coordinates
 */
export interface ChatWindowPosition {
  x: number;
  y: number;
}

/**
 * Window dimensions
 */
export interface ChatWindowSize {
  width: number;
  height: number;
}

/**
 * Window bounds (position + size)
 */
export interface ChatWindowBounds {
  position: ChatWindowPosition;
  size: ChatWindowSize;
}

// =============================================================================
// Docking System
// =============================================================================

/**
 * Magnetic dock state
 */
export interface DockState {
  /** Whether window is currently docked */
  isDocked: boolean;
  /** Which side is docked to */
  dockSide: DockSide | null;
  /** Magnetic pull strength (0-1) during drag */
  magneticStrength: number;
}

// =============================================================================
// Zero-Gravity Motion
// =============================================================================

/**
 * Float state for zero-gravity micro-motion
 */
export interface FloatState {
  /** Noise-based X offset */
  noiseX: number;
  /** Noise-based Y offset */
  noiseY: number;
  /** Current X velocity */
  velocityX: number;
  /** Current Y velocity */
  velocityY: number;
}

/**
 * Float offset for rendering
 */
export interface FloatOffset {
  x: number;
  y: number;
}

// =============================================================================
// Edge Resize
// =============================================================================

/**
 * Resize edge detection
 */
export type ResizeEdge = 'right' | 'bottom' | 'corner' | null;

/**
 * Resize constraints
 */
export interface ResizeConstraints {
  minWidth: number;
  maxWidth: number;
  minHeight: number;
  maxHeight: number;
}

// =============================================================================
// Chat Context
// =============================================================================

/**
 * Context for chat messages (related components/recommendations)
 */
export interface ChatContext {
  /** Related component ID */
  componentId: string | null;
  /** Related recommendation ID */
  recommendationId: string | null;
  /** Display label for context */
  label?: string;
}

// =============================================================================
// Store State
// =============================================================================

/**
 * Chat store state
 */
export interface ChatStoreState {
  /** Current window display state */
  windowState: ChatWindowState;
  /** Window position */
  position: ChatWindowPosition;
  /** Window size */
  size: ChatWindowSize;
  /** Dock state */
  dock: DockState;
  /** Float state for micro-motion */
  float: FloatState;
  /** Chat messages */
  messages: ChatMessage[];
  /** Whether AI is streaming response */
  isStreaming: boolean;
  /** Current streaming content */
  streamingContent: string;
  /** Input field value */
  inputValue: string;
  /** Current chat context */
  context: ChatContext;
  /** Schema version for compatibility */
  schema_version: string;
}

/**
 * Chat store actions
 */
export interface ChatStoreActions {
  // Window actions
  setWindowState: (state: ChatWindowState) => void;
  setPosition: (position: ChatWindowPosition) => void;
  setSize: (size: ChatWindowSize) => void;
  setDock: (dock: Partial<DockState>) => void;
  setFloat: (float: Partial<FloatState>) => void;

  // Message actions
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  removeMessage: (id: string) => void;
  clearMessages: () => void;

  // Input actions
  setInputValue: (value: string) => void;
  sendMessage: (content: string) => void;

  // Streaming actions
  startStreaming: () => void;
  appendStreamContent: (content: string) => void;
  finishStreaming: () => void;
  cancelStreaming: () => void;

  // Context actions
  setContext: (context: Partial<ChatContext>) => void;
  clearContext: () => void;

  // Reset
  reset: () => void;
}

/**
 * Complete chat store
 */
export type ChatStore = ChatStoreState & ChatStoreActions;

// =============================================================================
// Component Props
// =============================================================================

/**
 * ChatWindow component props
 */
export interface ChatWindowProps {
  /** Optional initial position */
  initialPosition?: ChatWindowPosition;
  /** Optional initial size */
  initialSize?: ChatWindowSize;
  /** Optional initial window state */
  initialWindowState?: ChatWindowState;
  /** Callback when window closes */
  onClose?: () => void;
  /** Additional class name */
  className?: string;
}

/**
 * ChatBubble component props
 */
export interface ChatBubbleProps {
  /** Message data */
  message: ChatMessage;
  /** Whether this is the last message */
  isLast: boolean;
  /** Blur depth for depth-based blur modulation (0-1) */
  blurDepth?: number;
  /** Callback when component link clicked */
  onComponentClick?: (componentId: string) => void;
}

/**
 * ChatInput component props
 */
export interface ChatInputProps {
  /** Placeholder text */
  placeholder?: string;
  /** Whether input is disabled */
  disabled?: boolean;
  /** Maximum character length */
  maxLength?: number;
  /** Callback when message submitted */
  onSubmit?: (content: string) => void;
}

/**
 * ChatHeader component props
 */
export interface ChatHeaderProps {
  /** Current window state */
  windowState: ChatWindowState;
  /** Drag start handler */
  onDragStart: (e: React.PointerEvent) => void;
  /** Minimize handler */
  onMinimize: () => void;
  /** Maximize/restore handler */
  onMaximize: () => void;
  /** Undock handler (for docked state) */
  onUndock: () => void;
}

/**
 * ChatMinimized component props
 */
export interface ChatMinimizedProps {
  /** Expand handler */
  onExpand: () => void;
  /** Whether AI is streaming */
  isStreaming?: boolean;
}

/**
 * TypingIndicator component props
 */
export interface TypingIndicatorProps {
  /** Animation speed multiplier */
  speed?: number;
}

/**
 * AIPresenceOrb component props
 */
export interface AIPresenceOrbProps {
  /** Whether AI is streaming/active */
  isStreaming?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
}

// =============================================================================
// Motion Constants
// =============================================================================

/**
 * VisionOS motion constants
 */
export const VISIONOS_MOTION = {
  spring: {
    calm: { stiffness: 120, damping: 24, mass: 0.8 },
    default: { stiffness: 160, damping: 26, mass: 0.7 },
    responsive: { stiffness: 200, damping: 28, mass: 0.6 },
  },
  presence: {
    breatheDuration: 6,
    scaleRange: [1, 1.018] as const,
    opacityRange: [0.06, 0.16] as const,
  },
  float: {
    noiseMagnitude: 0.5,
    noiseFrequency: 0.001,
    dragInertia: 0.92,
  },
} as const;

/**
 * Default window constraints
 */
export const DEFAULT_WINDOW_CONSTRAINTS: ResizeConstraints = {
  minWidth: 360,
  maxWidth: 560,
  minHeight: 400,
  maxHeight: 800,
};

/**
 * Default dock settings
 */
export const DEFAULT_DOCK_SETTINGS = {
  edgeGap: 24,
  cornerRadius: 20,
  magneticThreshold: 60,
  tiltDegrees: -1,
} as const;

// =============================================================================
// Initial States
// =============================================================================

/**
 * Initial chat store state
 */
export const INITIAL_CHAT_STATE: ChatStoreState = {
  windowState: 'expanded',
  position: { x: 0, y: 60 },
  size: { width: 420, height: 580 },
  dock: {
    isDocked: false,
    dockSide: null,
    magneticStrength: 0,
  },
  float: {
    noiseX: 0,
    noiseY: 0,
    velocityX: 0,
    velocityY: 0,
  },
  messages: [],
  isStreaming: false,
  streamingContent: '',
  inputValue: '',
  context: {
    componentId: null,
    recommendationId: null,
  },
  schema_version: SCHEMA_VERSION,
};
