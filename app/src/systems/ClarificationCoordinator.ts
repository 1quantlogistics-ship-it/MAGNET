/**
 * MAGNET UI Clarification Coordinator
 * BRAVO OWNS THIS FILE.
 *
 * V1.4 Agent Clarification System with ACK Retry Protocol.
 * Manages clarification requests from agents with:
 * - Priority queue based on agent priority
 * - ACK retry with exponential backoff (FIX #5)
 * - Request lifecycle tracking
 * - Timeout handling
 */

import { eventBus } from './UIEventBus';
import {
  agentsAPI,
  isTerminalAck,
  sortByPriority,
  type AckType,
  type AgentPriority,
  type ClarificationRequest,
  type AckResponse,
} from '../api/agents';

// ============================================================================
// Types
// ============================================================================

/**
 * ACK retry configuration (V1.4 FIX #5)
 */
export interface AckRetryConfig {
  /** Maximum retry attempts */
  maxRetries: number;
  /** Initial delay in ms */
  initialDelayMs: number;
  /** Backoff multiplier */
  backoffMultiplier: number;
  /** Maximum delay in ms */
  maxDelayMs: number;
}

/**
 * Default ACK retry config
 */
export const DEFAULT_ACK_RETRY_CONFIG: AckRetryConfig = {
  maxRetries: 3,
  initialDelayMs: 1000,
  backoffMultiplier: 2,
  maxDelayMs: 10000,
};

/**
 * Pending ACK operation
 */
interface PendingAck {
  requestId: string;
  agentId: string;
  requestToken: string;
  ackType: AckType;
  attempts: number;
  lastAttemptAt: number;
  nextRetryAt: number;
  reason?: string;
}

/**
 * Coordinator state
 */
export interface CoordinatorState {
  /** Active clarifications (not terminal) */
  activeClarifications: ClarificationRequest[];
  /** Currently presented clarification */
  currentClarification: ClarificationRequest | null;
  /** Pending ACK operations */
  pendingAcks: PendingAck[];
  /** Loading state */
  isLoading: boolean;
  /** Error state */
  error: string | null;
}

/**
 * Clarification event types
 */
export type ClarificationEventType =
  | 'clarification:received'
  | 'clarification:presented'
  | 'clarification:responded'
  | 'clarification:skipped'
  | 'clarification:cancelled'
  | 'clarification:timeout'
  | 'clarification:ack_failed'
  | 'clarification:ack_retry';

// ============================================================================
// Initial State
// ============================================================================

const INITIAL_STATE: CoordinatorState = {
  activeClarifications: [],
  currentClarification: null,
  pendingAcks: [],
  isLoading: false,
  error: null,
};

// ============================================================================
// Clarification Coordinator
// ============================================================================

/**
 * Clarification Coordinator
 *
 * Manages agent clarification requests with priority queuing
 * and ACK retry with exponential backoff.
 */
export class ClarificationCoordinator {
  private state: CoordinatorState;
  private listeners: Set<(state: CoordinatorState) => void>;
  private retryConfig: AckRetryConfig;
  private retryTimer: ReturnType<typeof setInterval> | null;
  private timeoutTimer: ReturnType<typeof setInterval> | null;

  constructor(config?: Partial<AckRetryConfig>) {
    this.state = { ...INITIAL_STATE };
    this.listeners = new Set();
    this.retryConfig = { ...DEFAULT_ACK_RETRY_CONFIG, ...config };
    this.retryTimer = null;
    this.timeoutTimer = null;
  }

  // -------------------------------------------------------------------------
  // State Management
  // -------------------------------------------------------------------------

  /**
   * Get current state
   */
  getState(): CoordinatorState {
    return { ...this.state };
  }

  /**
   * Subscribe to state changes
   */
  subscribe(listener: (state: CoordinatorState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /**
   * Update state and notify listeners
   */
  private setState(updates: Partial<CoordinatorState>): void {
    this.state = { ...this.state, ...updates };
    this.listeners.forEach(listener => listener(this.state));
  }

  /**
   * Emit event to event bus
   */
  private emit(type: ClarificationEventType, payload: Record<string, unknown>): void {
    eventBus.emit({
      type: type as any,
      payload,
      source: 'ui',
      domain: 'arrangement', // Clarifications affect arrangement domain
    });
  }

  // -------------------------------------------------------------------------
  // Lifecycle
  // -------------------------------------------------------------------------

  /**
   * Start the coordinator
   */
  start(): void {
    // Start retry processor
    this.retryTimer = setInterval(() => this.processRetries(), 1000);

    // Start timeout checker
    this.timeoutTimer = setInterval(() => this.checkTimeouts(), 5000);
  }

  /**
   * Stop the coordinator
   */
  stop(): void {
    if (this.retryTimer) {
      clearInterval(this.retryTimer);
      this.retryTimer = null;
    }
    if (this.timeoutTimer) {
      clearInterval(this.timeoutTimer);
      this.timeoutTimer = null;
    }
  }

  /**
   * Reset coordinator
   */
  reset(): void {
    this.stop();
    this.state = { ...INITIAL_STATE };
    this.listeners.forEach(listener => listener(this.state));
  }

  // -------------------------------------------------------------------------
  // Clarification Queue Management
  // -------------------------------------------------------------------------

  /**
   * Add a clarification to the queue
   */
  async addClarification(clarification: ClarificationRequest): Promise<void> {
    const activeClarifications = sortByPriority([
      ...this.state.activeClarifications,
      clarification,
    ]);

    this.setState({ activeClarifications });

    // Send queued ACK
    await this.sendAck(
      clarification.agentId,
      clarification.requestId,
      clarification.requestToken,
      'queued'
    );

    this.emit('clarification:received', {
      requestId: clarification.requestId,
      agentId: clarification.agentId,
      priority: clarification.priority,
    });

    // Auto-present if nothing is currently shown
    if (!this.state.currentClarification) {
      this.presentNext();
    }
  }

  /**
   * Present next clarification in queue
   */
  async presentNext(): Promise<ClarificationRequest | null> {
    const { activeClarifications } = this.state;
    if (activeClarifications.length === 0) {
      this.setState({ currentClarification: null });
      return null;
    }

    // Get highest priority non-presented clarification
    const next = activeClarifications.find(
      c => c.currentAck === 'queued'
    );

    if (!next) {
      this.setState({ currentClarification: null });
      return null;
    }

    this.setState({ currentClarification: next });

    // Send presented ACK
    await this.sendAck(
      next.agentId,
      next.requestId,
      next.requestToken,
      'presented'
    );

    this.emit('clarification:presented', {
      requestId: next.requestId,
      agentId: next.agentId,
    });

    return next;
  }

  /**
   * Respond to current clarification
   */
  async respond(response: string, responseData?: Record<string, unknown>): Promise<void> {
    const { currentClarification } = this.state;
    if (!currentClarification) {
      throw new Error('No clarification to respond to');
    }

    this.setState({ isLoading: true });

    try {
      await agentsAPI.respond(
        currentClarification.agentId,
        currentClarification.requestId,
        { response, responseData }
      );

      // Remove from active list
      const activeClarifications = this.state.activeClarifications.filter(
        c => c.requestId !== currentClarification.requestId
      );

      this.setState({
        activeClarifications,
        currentClarification: null,
        isLoading: false,
      });

      this.emit('clarification:responded', {
        requestId: currentClarification.requestId,
        response,
      });

      // Present next
      this.presentNext();
    } catch (error) {
      this.setState({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to respond',
      });
    }
  }

  /**
   * Skip current clarification
   */
  async skip(reason?: string): Promise<void> {
    const { currentClarification } = this.state;
    if (!currentClarification) return;

    await this.sendAck(
      currentClarification.agentId,
      currentClarification.requestId,
      currentClarification.requestToken,
      'skipped',
      reason
    );

    // Remove from active list
    const activeClarifications = this.state.activeClarifications.filter(
      c => c.requestId !== currentClarification.requestId
    );

    this.setState({
      activeClarifications,
      currentClarification: null,
    });

    this.emit('clarification:skipped', {
      requestId: currentClarification.requestId,
      reason,
    });

    // Present next
    this.presentNext();
  }

  /**
   * Cancel a clarification
   */
  async cancel(requestId: string, reason?: string): Promise<void> {
    const clarification = this.state.activeClarifications.find(
      c => c.requestId === requestId
    );

    if (!clarification) return;

    await this.sendAck(
      clarification.agentId,
      clarification.requestId,
      clarification.requestToken,
      'cancelled',
      reason
    );

    // Remove from active list
    const activeClarifications = this.state.activeClarifications.filter(
      c => c.requestId !== requestId
    );

    // Clear current if it's the cancelled one
    const currentClarification = this.state.currentClarification?.requestId === requestId
      ? null
      : this.state.currentClarification;

    this.setState({
      activeClarifications,
      currentClarification,
    });

    this.emit('clarification:cancelled', {
      requestId,
      reason,
    });

    // Present next if current was cancelled
    if (!currentClarification) {
      this.presentNext();
    }
  }

  // -------------------------------------------------------------------------
  // ACK Management with Retry (V1.4 FIX #5)
  // -------------------------------------------------------------------------

  /**
   * Send ACK with retry support
   */
  private async sendAck(
    agentId: string,
    requestId: string,
    requestToken: string,
    ackType: AckType,
    reason?: string
  ): Promise<void> {
    try {
      await agentsAPI.acknowledge(agentId, requestId, {
        ackType,
        requestToken,
        reason,
      });

      // Update clarification state
      const activeClarifications = this.state.activeClarifications.map(c => {
        if (c.requestId === requestId) {
          return { ...c, currentAck: ackType };
        }
        return c;
      });

      this.setState({ activeClarifications });
    } catch (error) {
      // Queue for retry
      this.queueAckRetry(agentId, requestId, requestToken, ackType, reason);
    }
  }

  /**
   * Queue ACK for retry
   */
  private queueAckRetry(
    agentId: string,
    requestId: string,
    requestToken: string,
    ackType: AckType,
    reason?: string
  ): void {
    const now = Date.now();
    const pendingAck: PendingAck = {
      requestId,
      agentId,
      requestToken,
      ackType,
      attempts: 1,
      lastAttemptAt: now,
      nextRetryAt: now + this.retryConfig.initialDelayMs,
      reason,
    };

    this.setState({
      pendingAcks: [...this.state.pendingAcks, pendingAck],
    });

    this.emit('clarification:ack_retry', {
      requestId,
      ackType,
      attempt: 1,
    });
  }

  /**
   * Process pending ACK retries
   */
  private async processRetries(): Promise<void> {
    const now = Date.now();
    const pendingAcks: PendingAck[] = [];
    const toProcess: PendingAck[] = [];

    for (const ack of this.state.pendingAcks) {
      if (ack.nextRetryAt <= now) {
        toProcess.push(ack);
      } else {
        pendingAcks.push(ack);
      }
    }

    for (const ack of toProcess) {
      try {
        await agentsAPI.acknowledge(ack.agentId, ack.requestId, {
          ackType: ack.ackType,
          requestToken: ack.requestToken,
          reason: ack.reason,
        });

        // Success - don't re-queue
        this.emit('clarification:ack_retry', {
          requestId: ack.requestId,
          ackType: ack.ackType,
          attempt: ack.attempts,
          success: true,
        });
      } catch (error) {
        if (ack.attempts < this.retryConfig.maxRetries) {
          // Calculate next retry delay with exponential backoff
          const delay = Math.min(
            this.retryConfig.initialDelayMs * Math.pow(this.retryConfig.backoffMultiplier, ack.attempts),
            this.retryConfig.maxDelayMs
          );

          pendingAcks.push({
            ...ack,
            attempts: ack.attempts + 1,
            lastAttemptAt: now,
            nextRetryAt: now + delay,
          });

          this.emit('clarification:ack_retry', {
            requestId: ack.requestId,
            ackType: ack.ackType,
            attempt: ack.attempts + 1,
            nextRetryIn: delay,
          });
        } else {
          // Max retries reached
          this.emit('clarification:ack_failed', {
            requestId: ack.requestId,
            ackType: ack.ackType,
            attempts: ack.attempts,
          });
        }
      }
    }

    // Always update state after processing retries
    // (Previously only updated if length changed, which caused
    // stale attempts counts when ACKs were re-queued after failure)
    this.setState({ pendingAcks });
  }

  // -------------------------------------------------------------------------
  // Timeout Handling
  // -------------------------------------------------------------------------

  /**
   * Check for timed out clarifications
   */
  private checkTimeouts(): void {
    const now = Date.now();
    const timedOut: string[] = [];

    for (const clarification of this.state.activeClarifications) {
      const createdAt = new Date(clarification.createdAt).getTime();
      const elapsed = now - createdAt;

      if (elapsed > clarification.timeoutSeconds * 1000) {
        timedOut.push(clarification.requestId);
      }
    }

    for (const requestId of timedOut) {
      this.cancel(requestId, 'timeout');
      this.emit('clarification:timeout', { requestId });
    }
  }

  // -------------------------------------------------------------------------
  // Sync Operations
  // -------------------------------------------------------------------------

  /**
   * Sync with backend for pending clarifications
   */
  async sync(): Promise<void> {
    this.setState({ isLoading: true });

    try {
      const response = await agentsAPI.listPendingClarifications();
      const clarifications = response.data.clarifications.map(c => ({
        ...c,
        currentAck: c.currentAck as AckType,
        priority: c.priority as AgentPriority,
      }));

      this.setState({
        activeClarifications: sortByPriority(clarifications),
        isLoading: false,
      });

      // Present first if nothing shown
      if (!this.state.currentClarification && clarifications.length > 0) {
        this.presentNext();
      }
    } catch (error) {
      this.setState({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Sync failed',
      });
    }
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default clarification coordinator instance
 */
export const clarificationCoordinator = new ClarificationCoordinator();

/**
 * React hook for clarification coordinator
 */
export function useClarificationCoordinator() {
  return clarificationCoordinator;
}
