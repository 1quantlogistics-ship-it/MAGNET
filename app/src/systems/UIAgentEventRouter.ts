/**
 * MAGNET UI Agent Event Router
 *
 * Multi-agent stream handler for routing agent events to appropriate stores.
 * FM8 Compliance: Supports real-time multi-agent feedback.
 */

import type {
  AgentMessagePayload,
  AgentThinkingPayload,
  AgentCompletePayload,
  AgentErrorPayload,
} from '../types/events';
import { orchestrator } from './UIOrchestrator';
import { UI_SCHEMA_VERSION } from '../types/schema-version';

/**
 * Agent types in the MAGNET system
 */
export type AgentType =
  | 'conductor'     // Main orchestration agent
  | 'validator'     // Validation/compliance agent
  | 'design'        // Design optimization agent
  | 'analysis'      // Analysis/computation agent
  | 'chat';         // User-facing chat agent

/**
 * Agent stream state
 */
export interface AgentStreamState {
  agentId: string;
  agentType: AgentType;
  isStreaming: boolean;
  currentMessage: string;
  messageHistory: AgentMessagePayload[];
  thinkingState: AgentThinkingPayload | null;
  lastError: AgentErrorPayload | null;
  startedAt: number;
  completedAt: number | null;
}

/**
 * Router configuration
 */
interface RouterConfig {
  /** Maximum concurrent streams */
  maxConcurrentStreams?: number;
  /** Stream timeout (ms) */
  streamTimeout?: number;
  /** Enable debug logging */
  debug?: boolean;
  /** Buffer size for message history per agent */
  historyBufferSize?: number;
}

/**
 * Stream event handler
 */
type StreamEventHandler<T> = (agentId: string, payload: T) => void;

/**
 * UIAgentEventRouter - Routes multi-agent events
 */
class UIAgentEventRouter {
  private static instance: UIAgentEventRouter;
  private config: Required<RouterConfig>;
  private activeStreams: Map<string, AgentStreamState> = new Map();
  private streamTimeouts: Map<string, NodeJS.Timeout> = new Map();

  // Event handlers by agent type
  private messageHandlers: Map<AgentType, Set<StreamEventHandler<AgentMessagePayload>>> =
    new Map();
  private thinkingHandlers: Map<AgentType, Set<StreamEventHandler<AgentThinkingPayload>>> =
    new Map();
  private completeHandlers: Map<AgentType, Set<StreamEventHandler<AgentCompletePayload>>> =
    new Map();
  private errorHandlers: Map<AgentType, Set<StreamEventHandler<AgentErrorPayload>>> =
    new Map();

  private constructor(config: RouterConfig = {}) {
    this.config = {
      maxConcurrentStreams: config.maxConcurrentStreams ?? 5,
      streamTimeout: config.streamTimeout ?? 60000, // 1 minute default
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      historyBufferSize: config.historyBufferSize ?? 100,
    };

    this.setupOrchestratorSubscriptions();
  }

  /**
   * Get singleton instance
   */
  static getInstance(): UIAgentEventRouter {
    if (!UIAgentEventRouter.instance) {
      UIAgentEventRouter.instance = new UIAgentEventRouter();
    }
    return UIAgentEventRouter.instance;
  }

  /**
   * Subscribe to orchestrator agent events
   */
  private setupOrchestratorSubscriptions(): void {
    orchestrator.subscribe('agent:message', (payload) => {
      this.handleAgentMessage(payload as AgentMessagePayload);
    });

    orchestrator.subscribe('agent:thinking', (payload) => {
      this.handleAgentThinking(payload as AgentThinkingPayload);
    });

    orchestrator.subscribe('agent:complete', (payload) => {
      this.handleAgentComplete(payload as AgentCompletePayload);
    });

    orchestrator.subscribe('agent:error', (payload) => {
      this.handleAgentError(payload as AgentErrorPayload);
    });
  }

  /**
   * Register a message handler for specific agent type
   */
  onMessage(
    agentType: AgentType,
    handler: StreamEventHandler<AgentMessagePayload>
  ): () => void {
    if (!this.messageHandlers.has(agentType)) {
      this.messageHandlers.set(agentType, new Set());
    }
    this.messageHandlers.get(agentType)!.add(handler);

    return () => {
      this.messageHandlers.get(agentType)?.delete(handler);
    };
  }

  /**
   * Register a thinking handler for specific agent type
   */
  onThinking(
    agentType: AgentType,
    handler: StreamEventHandler<AgentThinkingPayload>
  ): () => void {
    if (!this.thinkingHandlers.has(agentType)) {
      this.thinkingHandlers.set(agentType, new Set());
    }
    this.thinkingHandlers.get(agentType)!.add(handler);

    return () => {
      this.thinkingHandlers.get(agentType)?.delete(handler);
    };
  }

  /**
   * Register a complete handler for specific agent type
   */
  onComplete(
    agentType: AgentType,
    handler: StreamEventHandler<AgentCompletePayload>
  ): () => void {
    if (!this.completeHandlers.has(agentType)) {
      this.completeHandlers.set(agentType, new Set());
    }
    this.completeHandlers.get(agentType)!.add(handler);

    return () => {
      this.completeHandlers.get(agentType)?.delete(handler);
    };
  }

  /**
   * Register an error handler for specific agent type
   */
  onError(
    agentType: AgentType,
    handler: StreamEventHandler<AgentErrorPayload>
  ): () => void {
    if (!this.errorHandlers.has(agentType)) {
      this.errorHandlers.set(agentType, new Set());
    }
    this.errorHandlers.get(agentType)!.add(handler);

    return () => {
      this.errorHandlers.get(agentType)?.delete(handler);
    };
  }

  /**
   * Handle incoming agent message
   */
  private handleAgentMessage(payload: AgentMessagePayload): void {
    const { agentId } = payload;
    const agentType = this.getAgentType(agentId);

    // Ensure stream exists
    if (!this.activeStreams.has(agentId)) {
      this.initializeStream(agentId, agentType);
    }

    const stream = this.activeStreams.get(agentId)!;

    // Update stream state
    stream.isStreaming = payload.isStreaming;
    stream.currentMessage = payload.content;
    stream.messageHistory.push(payload);

    // Trim history if needed
    if (stream.messageHistory.length > this.config.historyBufferSize) {
      stream.messageHistory = stream.messageHistory.slice(-this.config.historyBufferSize);
    }

    // Reset timeout
    this.resetStreamTimeout(agentId);

    // Notify handlers
    const handlers = this.messageHandlers.get(agentType);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(agentId, payload);
        } catch (error) {
          this.logError('Message handler error', error);
        }
      }
    }

    if (this.config.debug) {
      console.log(`[UIAgentEventRouter] Message from ${agentType}:${agentId}`, {
        streaming: payload.isStreaming,
        complete: payload.isComplete,
      });
    }
  }

  /**
   * Handle agent thinking state
   */
  private handleAgentThinking(payload: AgentThinkingPayload): void {
    const { agentId } = payload;
    const agentType = this.getAgentType(agentId);

    // Ensure stream exists
    if (!this.activeStreams.has(agentId)) {
      this.initializeStream(agentId, agentType);
    }

    const stream = this.activeStreams.get(agentId)!;
    stream.thinkingState = payload;

    // Reset timeout
    this.resetStreamTimeout(agentId);

    // Notify handlers
    const handlers = this.thinkingHandlers.get(agentType);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(agentId, payload);
        } catch (error) {
          this.logError('Thinking handler error', error);
        }
      }
    }

    if (this.config.debug) {
      console.log(`[UIAgentEventRouter] Thinking from ${agentType}:${agentId}`, payload.stage);
    }
  }

  /**
   * Handle agent completion
   */
  private handleAgentComplete(payload: AgentCompletePayload): void {
    const { agentId } = payload;
    const agentType = this.getAgentType(agentId);

    const stream = this.activeStreams.get(agentId);
    if (stream) {
      stream.isStreaming = false;
      stream.completedAt = Date.now();
      stream.thinkingState = null;
    }

    // Clear timeout
    this.clearStreamTimeout(agentId);

    // Notify handlers
    const handlers = this.completeHandlers.get(agentType);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(agentId, payload);
        } catch (error) {
          this.logError('Complete handler error', error);
        }
      }
    }

    if (this.config.debug) {
      console.log(`[UIAgentEventRouter] Complete from ${agentType}:${agentId}`, {
        success: payload.success,
        duration: payload.duration,
      });
    }
  }

  /**
   * Handle agent error
   */
  private handleAgentError(payload: AgentErrorPayload): void {
    const { agentId } = payload;
    const agentType = this.getAgentType(agentId);

    const stream = this.activeStreams.get(agentId);
    if (stream) {
      stream.lastError = payload;
      stream.isStreaming = false;
    }

    // Clear timeout
    this.clearStreamTimeout(agentId);

    // Notify handlers
    const handlers = this.errorHandlers.get(agentType);
    if (handlers) {
      for (const handler of handlers) {
        try {
          handler(agentId, payload);
        } catch (error) {
          this.logError('Error handler error', error);
        }
      }
    }

    if (this.config.debug) {
      console.log(`[UIAgentEventRouter] Error from ${agentType}:${agentId}`, {
        code: payload.errorCode,
        recoverable: payload.recoverable,
      });
    }
  }

  /**
   * Initialize a new stream
   */
  private initializeStream(agentId: string, agentType: AgentType): void {
    // Check concurrent stream limit
    if (this.activeStreams.size >= this.config.maxConcurrentStreams) {
      // Remove oldest completed stream
      const oldestCompleted = this.findOldestCompletedStream();
      if (oldestCompleted) {
        this.activeStreams.delete(oldestCompleted);
      } else {
        console.warn('[UIAgentEventRouter] Max concurrent streams reached');
      }
    }

    const stream: AgentStreamState = {
      agentId,
      agentType,
      isStreaming: true,
      currentMessage: '',
      messageHistory: [],
      thinkingState: null,
      lastError: null,
      startedAt: Date.now(),
      completedAt: null,
    };

    this.activeStreams.set(agentId, stream);
    this.resetStreamTimeout(agentId);

    if (this.config.debug) {
      console.log(`[UIAgentEventRouter] Stream initialized: ${agentType}:${agentId}`);
    }
  }

  /**
   * Reset stream timeout
   */
  private resetStreamTimeout(agentId: string): void {
    this.clearStreamTimeout(agentId);

    const timeout = setTimeout(() => {
      this.handleStreamTimeout(agentId);
    }, this.config.streamTimeout);

    this.streamTimeouts.set(agentId, timeout);
  }

  /**
   * Clear stream timeout
   */
  private clearStreamTimeout(agentId: string): void {
    const timeout = this.streamTimeouts.get(agentId);
    if (timeout) {
      clearTimeout(timeout);
      this.streamTimeouts.delete(agentId);
    }
  }

  /**
   * Handle stream timeout
   */
  private handleStreamTimeout(agentId: string): void {
    const stream = this.activeStreams.get(agentId);
    if (stream && stream.isStreaming) {
      console.warn(`[UIAgentEventRouter] Stream timeout: ${agentId}`);

      // Emit timeout error
      const errorPayload: AgentErrorPayload = {
        agentId,
        errorCode: 'STREAM_TIMEOUT',
        errorMessage: `Agent stream timed out after ${this.config.streamTimeout}ms`,
        recoverable: true,
      };

      this.handleAgentError(errorPayload);
    }
  }

  /**
   * Find oldest completed stream
   */
  private findOldestCompletedStream(): string | null {
    let oldest: { id: string; time: number } | null = null;

    for (const [id, stream] of this.activeStreams) {
      if (stream.completedAt !== null) {
        if (!oldest || stream.completedAt < oldest.time) {
          oldest = { id, time: stream.completedAt };
        }
      }
    }

    return oldest?.id ?? null;
  }

  /**
   * Determine agent type from ID
   */
  private getAgentType(agentId: string): AgentType {
    // Extract type from agentId format: "type_timestamp_random"
    const parts = agentId.split('_');
    const prefix = parts[0]?.toLowerCase();

    switch (prefix) {
      case 'conductor':
        return 'conductor';
      case 'validator':
        return 'validator';
      case 'design':
        return 'design';
      case 'analysis':
        return 'analysis';
      case 'chat':
        return 'chat';
      default:
        // Default to chat for unknown types
        return 'chat';
    }
  }

  /**
   * Get stream state for an agent
   */
  getStreamState(agentId: string): AgentStreamState | null {
    return this.activeStreams.get(agentId) ?? null;
  }

  /**
   * Get all active streams
   */
  getActiveStreams(): AgentStreamState[] {
    return Array.from(this.activeStreams.values()).filter((s) => s.isStreaming);
  }

  /**
   * Get streams by agent type
   */
  getStreamsByType(agentType: AgentType): AgentStreamState[] {
    return Array.from(this.activeStreams.values()).filter(
      (s) => s.agentType === agentType
    );
  }

  /**
   * Check if any agent is currently streaming
   */
  isAnyAgentStreaming(): boolean {
    return Array.from(this.activeStreams.values()).some((s) => s.isStreaming);
  }

  /**
   * Clear all streams
   */
  clearAllStreams(): void {
    // Clear all timeouts
    for (const timeout of this.streamTimeouts.values()) {
      clearTimeout(timeout);
    }
    this.streamTimeouts.clear();
    this.activeStreams.clear();

    if (this.config.debug) {
      console.log('[UIAgentEventRouter] All streams cleared');
    }
  }

  /**
   * Log error
   */
  private logError(message: string, error: unknown): void {
    console.error(`[UIAgentEventRouter] ${message}:`, error);
  }
}

/**
 * Export singleton instance
 */
export const agentRouter = UIAgentEventRouter.getInstance();

/**
 * Hook for using agent router in React components
 */
export function useAgentRouter() {
  const router = UIAgentEventRouter.getInstance();
  return {
    onMessage: router.onMessage.bind(router),
    onThinking: router.onThinking.bind(router),
    onComplete: router.onComplete.bind(router),
    onError: router.onError.bind(router),
    getStreamState: router.getStreamState.bind(router),
    getActiveStreams: router.getActiveStreams.bind(router),
    getStreamsByType: router.getStreamsByType.bind(router),
    isAnyAgentStreaming: router.isAnyAgentStreaming.bind(router),
  };
}

export { UIAgentEventRouter };
