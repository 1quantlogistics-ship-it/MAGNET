/**
 * MAGNET UI WebSocket Client
 *
 * WebSocket wrapper with automatic reconnection, ACK retry,
 * and chain tracking support.
 */

import type { Domain, DomainHashes } from '../types/domainHashes';
import type { ChainTrackingMeta } from '../types/events';

// ============================================================================
// Types
// ============================================================================

/**
 * WebSocket connection states
 */
export type WebSocketState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'
  | 'buffering'  // Connected but buffering until stores ready
  | 'error';

/**
 * WebSocket message with chain tracking
 */
export interface WebSocketMessage<T = unknown> {
  /** Message type */
  type: string;
  /** Message payload */
  payload: T;
  /** Chain tracking metadata */
  chain?: ChainTrackingMeta;
  /** Message ID for ACK */
  messageId?: string;
}

/**
 * ACK message sent to backend
 */
export interface AckMessage {
  type: 'ack';
  messageId: string;
  domain: Domain;
  updateId: string;
}

/**
 * WebSocket event handlers
 */
export interface WebSocketEventHandlers {
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (error: Event) => void;
  onMessage?: <T>(message: WebSocketMessage<T>) => void;
  onStateChange?: (state: WebSocketState) => void;
  onReconnect?: (attempt: number) => void;
}

/**
 * ACK retry configuration
 */
export interface AckRetryConfig {
  /** Maximum retry attempts */
  maxRetries: number;
  /** Base delay in ms */
  baseDelay: number;
  /** Delay multiplier for exponential backoff */
  multiplier: number;
  /** Maximum delay in ms */
  maxDelay: number;
}

/**
 * WebSocket client configuration
 */
export interface WebSocketClientConfig {
  /** WebSocket URL */
  url: string;
  /** Protocols to use */
  protocols?: string[];
  /** Auto-reconnect on disconnect */
  autoReconnect: boolean;
  /** Maximum reconnect attempts (0 = infinite) */
  maxReconnectAttempts: number;
  /** Base reconnect delay in ms */
  reconnectDelay: number;
  /** Reconnect delay multiplier */
  reconnectMultiplier: number;
  /** Maximum reconnect delay in ms */
  maxReconnectDelay: number;
  /** Heartbeat interval in ms (0 = disabled) */
  heartbeatInterval: number;
  /** ACK retry configuration */
  ackRetry: AckRetryConfig;
  /** Event handlers */
  handlers: WebSocketEventHandlers;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Default ACK retry configuration
 */
export const DEFAULT_ACK_RETRY_CONFIG: AckRetryConfig = {
  maxRetries: 3,
  baseDelay: 1000,
  multiplier: 2,
  maxDelay: 8000,
};

/**
 * Default WebSocket configuration
 */
const DEFAULT_CONFIG: Omit<WebSocketClientConfig, 'url'> = {
  autoReconnect: true,
  maxReconnectAttempts: 0, // Infinite
  reconnectDelay: 1000,
  reconnectMultiplier: 1.5,
  maxReconnectDelay: 30000,
  heartbeatInterval: 30000,
  ackRetry: DEFAULT_ACK_RETRY_CONFIG,
  handlers: {},
};

// ============================================================================
// Pending ACK Tracker
// ============================================================================

interface PendingAck {
  messageId: string;
  domain: Domain;
  updateId: string;
  retryCount: number;
  lastAttempt: number;
  timeoutId: ReturnType<typeof setTimeout> | null;
}

// ============================================================================
// WebSocketClient
// ============================================================================

/**
 * WebSocket client with ACK retry and reconnection
 */
export class WebSocketClient {
  private config: WebSocketClientConfig;
  private socket: WebSocket | null = null;
  private state: WebSocketState = 'disconnected';
  private reconnectAttempt = 0;
  private reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private heartbeatIntervalId: ReturnType<typeof setInterval> | null = null;
  private pendingAcks: Map<string, PendingAck> = new Map();
  private messageBuffer: WebSocketMessage[] = [];
  private isBuffering = false;

  constructor(config: Partial<WebSocketClientConfig> & { url: string }) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Get current connection state
   */
  getState(): WebSocketState {
    return this.state;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.state === 'connected' || this.state === 'buffering';
  }

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.setState('connecting');

    try {
      this.socket = new WebSocket(this.config.url, this.config.protocols);
      this.setupSocketHandlers();
    } catch (error) {
      this.setState('error');
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect from server
   */
  disconnect(): void {
    this.cleanup();
    this.socket?.close();
    this.socket = null;
    this.setState('disconnected');
  }

  /**
   * Start buffering mode (until stores ready)
   */
  startBuffering(): void {
    this.isBuffering = true;
    if (this.state === 'connected') {
      this.setState('buffering');
    }
  }

  /**
   * Stop buffering and process buffered messages
   */
  stopBuffering(): void {
    this.isBuffering = false;
    if (this.state === 'buffering') {
      this.setState('connected');
    }

    // Process buffered messages
    const messages = [...this.messageBuffer];
    this.messageBuffer = [];

    for (const message of messages) {
      this.config.handlers.onMessage?.(message);
    }
  }

  /**
   * Send message to server
   */
  send<T>(message: WebSocketMessage<T>): boolean {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      this.socket.send(JSON.stringify(message));
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Send ACK for a message with retry support
   */
  sendAck(messageId: string, domain: Domain, updateId: string): void {
    const ack: AckMessage = {
      type: 'ack',
      messageId,
      domain,
      updateId,
    };

    const success = this.send(ack);

    if (!success) {
      // Queue ACK for retry
      this.queueAckRetry(messageId, domain, updateId);
    }
  }

  /**
   * Queue ACK for retry with exponential backoff
   */
  private queueAckRetry(messageId: string, domain: Domain, updateId: string): void {
    const existing = this.pendingAcks.get(messageId);

    if (existing && existing.retryCount >= this.config.ackRetry.maxRetries) {
      // Max retries exceeded
      this.pendingAcks.delete(messageId);
      console.error(`ACK failed after ${this.config.ackRetry.maxRetries} retries:`, messageId);
      return;
    }

    const retryCount = existing ? existing.retryCount + 1 : 1;
    const delay = Math.min(
      this.config.ackRetry.baseDelay * Math.pow(this.config.ackRetry.multiplier, retryCount - 1),
      this.config.ackRetry.maxDelay
    );

    const pending: PendingAck = {
      messageId,
      domain,
      updateId,
      retryCount,
      lastAttempt: Date.now(),
      timeoutId: setTimeout(() => this.retryAck(messageId), delay),
    };

    this.pendingAcks.set(messageId, pending);
  }

  /**
   * Retry sending ACK
   */
  private retryAck(messageId: string): void {
    const pending = this.pendingAcks.get(messageId);
    if (!pending) return;

    const success = this.send<AckMessage>({
      type: 'ack',
      payload: {
        type: 'ack',
        messageId: pending.messageId,
        domain: pending.domain,
        updateId: pending.updateId,
      },
    });

    if (success) {
      this.pendingAcks.delete(messageId);
    } else {
      this.queueAckRetry(pending.messageId, pending.domain, pending.updateId);
    }
  }

  /**
   * Set connection state
   */
  private setState(state: WebSocketState): void {
    if (this.state !== state) {
      this.state = state;
      this.config.handlers.onStateChange?.(state);
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  private setupSocketHandlers(): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.setState(this.isBuffering ? 'buffering' : 'connected');
      this.startHeartbeat();
      this.config.handlers.onOpen?.();

      // Retry pending ACKs
      this.retryPendingAcks();
    };

    this.socket.onclose = (event) => {
      this.cleanup();
      this.setState('disconnected');
      this.config.handlers.onClose?.(event);

      if (this.config.autoReconnect && !event.wasClean) {
        this.scheduleReconnect();
      }
    };

    this.socket.onerror = (error) => {
      this.setState('error');
      this.config.handlers.onError?.(error);
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WebSocketMessage;

        if (this.isBuffering) {
          // Buffer message until stores ready
          this.messageBuffer.push(message);
        } else {
          this.config.handlers.onMessage?.(message);
        }

        // Auto-ACK if chain tracking present
        if (message.chain && message.messageId) {
          this.sendAck(message.messageId, message.chain.domain, message.chain.update_id);
        }
      } catch {
        console.error('Failed to parse WebSocket message:', event.data);
      }
    };
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (
      this.config.maxReconnectAttempts > 0 &&
      this.reconnectAttempt >= this.config.maxReconnectAttempts
    ) {
      this.setState('error');
      return;
    }

    this.setState('reconnecting');
    this.reconnectAttempt++;

    const delay = Math.min(
      this.config.reconnectDelay * Math.pow(this.config.reconnectMultiplier, this.reconnectAttempt - 1),
      this.config.maxReconnectDelay
    );

    this.config.handlers.onReconnect?.(this.reconnectAttempt);

    this.reconnectTimeoutId = setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Start heartbeat interval
   */
  private startHeartbeat(): void {
    if (this.config.heartbeatInterval <= 0) return;

    this.stopHeartbeat();
    this.heartbeatIntervalId = setInterval(() => {
      this.send({ type: 'ping', payload: { timestamp: Date.now() } });
    }, this.config.heartbeatInterval);
  }

  /**
   * Stop heartbeat interval
   */
  private stopHeartbeat(): void {
    if (this.heartbeatIntervalId) {
      clearInterval(this.heartbeatIntervalId);
      this.heartbeatIntervalId = null;
    }
  }

  /**
   * Retry all pending ACKs
   */
  private retryPendingAcks(): void {
    for (const [messageId, pending] of this.pendingAcks) {
      if (pending.timeoutId) {
        clearTimeout(pending.timeoutId);
      }
      this.retryAck(messageId);
    }
  }

  /**
   * Cleanup resources
   */
  private cleanup(): void {
    this.stopHeartbeat();

    if (this.reconnectTimeoutId) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }

    // Clear pending ACK timeouts
    for (const pending of this.pendingAcks.values()) {
      if (pending.timeoutId) {
        clearTimeout(pending.timeoutId);
      }
    }
  }
}

// ============================================================================
// Factory Function
// ============================================================================

/**
 * Create WebSocket client with configuration
 */
export function createWebSocketClient(
  url: string,
  handlers: WebSocketEventHandlers,
  config: Partial<Omit<WebSocketClientConfig, 'url' | 'handlers'>> = {}
): WebSocketClient {
  return new WebSocketClient({
    url,
    handlers,
    ...config,
  });
}
