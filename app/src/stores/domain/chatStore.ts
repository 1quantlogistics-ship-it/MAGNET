/**
 * MAGNET UI Module 03: Chat Store
 *
 * Domain-bounded Zustand store for chat window state.
 * Manages window state, messages, streaming, and context.
 */

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import { createStoreFactory, type UIStoreContract } from '../contracts/StoreFactory';
import type {
  ChatStore,
  ChatStoreState,
  ChatWindowState,
  ChatWindowPosition,
  ChatWindowSize,
  DockState,
  FloatState,
  ChatMessage,
  ChatContext,
  INITIAL_CHAT_STATE,
} from '../../types/chat';
import { SCHEMA_VERSION } from '../../types/schema-version';

// =============================================================================
// Initial State
// =============================================================================

const initialState: ChatStoreState = {
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

// =============================================================================
// Store Creation
// =============================================================================

export const useChatStore = create<ChatStore>()(
  subscribeWithSelector((set, get) => ({
    ...initialState,

    // =========================================================================
    // Window Actions
    // =========================================================================

    setWindowState: (windowState: ChatWindowState) => {
      set({ windowState });

      // Update dock state based on window state
      if (windowState === 'docked') {
        set({
          dock: {
            isDocked: true,
            dockSide: 'right',
            magneticStrength: 0,
          },
        });
      } else if (windowState !== 'docked') {
        set({
          dock: {
            isDocked: false,
            dockSide: null,
            magneticStrength: 0,
          },
        });
      }
    },

    setPosition: (position: ChatWindowPosition) => {
      set({ position });
    },

    setSize: (size: ChatWindowSize) => {
      set({ size });
    },

    setDock: (dock: Partial<DockState>) => {
      set((state) => ({
        dock: { ...state.dock, ...dock },
      }));
    },

    setFloat: (float: Partial<FloatState>) => {
      set((state) => ({
        float: { ...state.float, ...float },
      }));
    },

    // =========================================================================
    // Message Actions
    // =========================================================================

    addMessage: (message: ChatMessage) => {
      set((state) => ({
        messages: [...state.messages, message],
      }));
    },

    updateMessage: (id: string, updates: Partial<ChatMessage>) => {
      set((state) => ({
        messages: state.messages.map((msg) =>
          msg.id === id ? { ...msg, ...updates } : msg
        ),
      }));
    },

    removeMessage: (id: string) => {
      set((state) => ({
        messages: state.messages.filter((msg) => msg.id !== id),
      }));
    },

    clearMessages: () => {
      set({ messages: [] });
    },

    // =========================================================================
    // Input Actions
    // =========================================================================

    setInputValue: (inputValue: string) => {
      set({ inputValue });
    },

    sendMessage: (content: string) => {
      const { context, addMessage, startStreaming } = get();

      // Create user message
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        role: 'user',
        content,
        timestamp: Date.now(),
        status: 'sent',
        relatedComponentId: context.componentId || undefined,
        relatedRecommendationId: context.recommendationId || undefined,
      };

      // Add message and clear input
      addMessage(userMessage);
      set({ inputValue: '' });

      // Start streaming response
      startStreaming();

      // Trigger AI response (this would connect to backend in production)
      simulateAIResponse(get);
    },

    // =========================================================================
    // Streaming Actions
    // =========================================================================

    startStreaming: () => {
      set({
        isStreaming: true,
        streamingContent: '',
      });
    },

    appendStreamContent: (content: string) => {
      set((state) => ({
        streamingContent: state.streamingContent + content,
      }));
    },

    finishStreaming: () => {
      const { streamingContent, addMessage } = get();

      // Create AI message from streamed content
      const aiMessage: ChatMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        role: 'assistant',
        content: streamingContent,
        timestamp: Date.now(),
        status: 'sent',
      };

      addMessage(aiMessage);
      set({
        isStreaming: false,
        streamingContent: '',
      });
    },

    cancelStreaming: () => {
      set({
        isStreaming: false,
        streamingContent: '',
      });
    },

    // =========================================================================
    // Context Actions
    // =========================================================================

    setContext: (context: Partial<ChatContext>) => {
      set((state) => ({
        context: { ...state.context, ...context },
      }));
    },

    clearContext: () => {
      set({
        context: {
          componentId: null,
          recommendationId: null,
        },
      });
    },

    // =========================================================================
    // Reset
    // =========================================================================

    reset: () => {
      set(initialState);
    },
  }))
);

// =============================================================================
// Simulated AI Response (Development Only)
// =============================================================================

async function simulateAIResponse(get: () => ChatStore): Promise<void> {
  const responses = [
    "I understand you're asking about the vessel design. ",
    "Based on the current configuration, ",
    "the hull parameters look optimal for the specified requirements. ",
    "Would you like me to run a stability analysis?",
  ];

  // Simulate typing delay before starting
  await new Promise((resolve) => setTimeout(resolve, 500));

  for (const chunk of responses) {
    // Check if streaming was cancelled
    if (!get().isStreaming) return;

    // Type each character with natural delay
    for (const char of chunk) {
      if (!get().isStreaming) return;

      await new Promise((resolve) =>
        setTimeout(resolve, 15 + Math.random() * 25)
      );
      get().appendStreamContent(char);
    }

    // Pause between chunks
    await new Promise((resolve) =>
      setTimeout(resolve, 80 + Math.random() * 120)
    );
  }

  // Finish streaming
  await new Promise((resolve) => setTimeout(resolve, 200));
  if (get().isStreaming) {
    get().finishStreaming();
  }
}

// =============================================================================
// Store Contract Implementation
// =============================================================================

/**
 * Chat store contract for UIOrchestrator integration
 */
export const chatStoreContract: UIStoreContract<ChatStoreState> = {
  readOnly: {
    get messages() {
      return useChatStore.getState().messages;
    },
    get isStreaming() {
      return useChatStore.getState().isStreaming;
    },
    get windowState() {
      return useChatStore.getState().windowState;
    },
  } as ChatStoreState,

  readWrite: {
    windowState: useChatStore.getState().windowState,
    position: useChatStore.getState().position,
    size: useChatStore.getState().size,
    inputValue: useChatStore.getState().inputValue,
  },

  reconcile: (source: ChatStoreState) => {
    useChatStore.setState({
      messages: source.messages,
      windowState: source.windowState,
      position: source.position,
      size: source.size,
    });
  },

  reset: () => {
    useChatStore.getState().reset();
  },
};

// =============================================================================
// Selectors
// =============================================================================

/**
 * Select only window state
 */
export const selectWindowState = (state: ChatStore) => state.windowState;

/**
 * Select only messages
 */
export const selectMessages = (state: ChatStore) => state.messages;

/**
 * Select streaming state
 */
export const selectStreamingState = (state: ChatStore) => ({
  isStreaming: state.isStreaming,
  streamingContent: state.streamingContent,
});

/**
 * Select context
 */
export const selectContext = (state: ChatStore) => state.context;

/**
 * Select window bounds
 */
export const selectWindowBounds = (state: ChatStore) => ({
  position: state.position,
  size: state.size,
});

export default useChatStore;
