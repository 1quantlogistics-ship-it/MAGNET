/**
 * MAGNET UI Agents API Client
 * BRAVO OWNS THIS FILE.
 *
 * V1.4 Agent Clarification System
 * Handles clarification ACK protocol for agent arbitration.
 *
 * Endpoints:
 * - POST /agents/{agent_id}/clarification/{request_id}/ack
 * - GET /agents/{agent_id}/clarifications
 * - POST /agents/{agent_id}/clarifications
 * - GET /agents/{agent_id}/clarification/{request_id}
 * - POST /agents/{agent_id}/clarification/{request_id}/respond
 * - DELETE /agents/{agent_id}/clarification/{request_id}
 * - GET /agents/clarifications/pending
 * - GET /agents/stats
 */

import { apiClient, type APIResponse, type RequestConfig } from '../services/BaseAPIClient';

// ============================================================================
// Types
// ============================================================================

/**
 * ACK type for clarification lifecycle
 */
export type AckType =
  | 'queued'
  | 'presented'
  | 'responded'
  | 'skipped'
  | 'cancelled';

/**
 * Agent priority levels
 */
export type AgentPriority = 0 | 1 | 2 | 3 | 4;

/**
 * Agent priority names
 */
export const AGENT_PRIORITY_NAMES: Record<AgentPriority, string> = {
  4: 'compliance',
  3: 'routing',
  2: 'interior',
  1: 'production',
  0: 'default',
};

/**
 * Agent types
 */
export type AgentType =
  | 'compliance'
  | 'routing'
  | 'interior'
  | 'production'
  | 'hull'
  | 'systems'
  | 'weight';

/**
 * ACK request
 */
export interface AckRequest {
  ackType: AckType;
  requestToken: string;
  reason?: string;
}

/**
 * ACK response
 */
export interface AckResponse {
  success: boolean;
  requestId: string;
  agentId: string;
  ackType: AckType;
  timestamp: string;
  message: string;
}

/**
 * Clarification request
 */
export interface ClarificationRequest {
  requestId: string;
  agentId: string;
  requestToken: string;
  message: string;
  options: string[];
  defaultOption?: string;
  priority: AgentPriority;
  createdAt: string;
  timeoutSeconds: number;
  currentAck: AckType;
  ackHistory: AckHistoryEntry[];
  response?: string;
  responseData?: Record<string, unknown>;
  context?: Record<string, unknown>;
}

/**
 * ACK history entry
 */
export interface AckHistoryEntry {
  ackType: AckType;
  timestamp: string;
  reason?: string;
}

/**
 * Create clarification request
 */
export interface CreateClarificationRequest {
  message: string;
  options?: string[];
  defaultOption?: string;
  priority?: AgentPriority;
  context?: Record<string, unknown>;
  timeoutSeconds?: number;
}

/**
 * Clarification list response
 */
export interface ClarificationListResponse {
  clarifications: ClarificationRequest[];
  total: number;
  pending: number;
}

/**
 * Respond request
 */
export interface RespondRequest {
  response: string;
  responseData?: Record<string, unknown>;
}

/**
 * Agent stats
 */
export interface AgentStats {
  totalRequests: number;
  pendingRequests: number;
  agents: number;
  byAckType: Record<AckType, number>;
}

// ============================================================================
// Agents API Client
// ============================================================================

/**
 * Agents API Client
 *
 * Provides methods for agent clarification operations.
 * Implements V1.4 ACK protocol for clarification lifecycle.
 */
export class AgentsAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1/agents') {
    this.baseUrl = baseUrl;
  }

  // -------------------------------------------------------------------------
  // ACK Protocol (V1.4 Core)
  // -------------------------------------------------------------------------

  /**
   * Acknowledge a clarification request
   *
   * V1.4 spec endpoint:
   * POST /api/v1/agents/{agent_id}/clarification/{request_id}/ack
   *
   * @param agentId - Agent identifier
   * @param requestId - Clarification request ID
   * @param ack - ACK request body
   * @returns ACK response with timestamp
   */
  async acknowledge(
    agentId: string,
    requestId: string,
    ack: AckRequest,
    config?: RequestConfig
  ): Promise<APIResponse<AckResponse>> {
    return apiClient.post<AckResponse>(
      `${this.baseUrl}/${agentId}/clarification/${requestId}/ack`,
      {
        ack_type: ack.ackType,
        request_token: ack.requestToken,
        reason: ack.reason,
      },
      config
    );
  }

  /**
   * Mark clarification as queued
   */
  async markQueued(
    agentId: string,
    requestId: string,
    requestToken: string,
    config?: RequestConfig
  ): Promise<APIResponse<AckResponse>> {
    return this.acknowledge(agentId, requestId, {
      ackType: 'queued',
      requestToken,
    }, config);
  }

  /**
   * Mark clarification as presented to user
   */
  async markPresented(
    agentId: string,
    requestId: string,
    requestToken: string,
    config?: RequestConfig
  ): Promise<APIResponse<AckResponse>> {
    return this.acknowledge(agentId, requestId, {
      ackType: 'presented',
      requestToken,
    }, config);
  }

  /**
   * Mark clarification as skipped
   */
  async markSkipped(
    agentId: string,
    requestId: string,
    requestToken: string,
    reason?: string,
    config?: RequestConfig
  ): Promise<APIResponse<AckResponse>> {
    return this.acknowledge(agentId, requestId, {
      ackType: 'skipped',
      requestToken,
      reason,
    }, config);
  }

  /**
   * Mark clarification as cancelled
   */
  async markCancelled(
    agentId: string,
    requestId: string,
    requestToken: string,
    reason?: string,
    config?: RequestConfig
  ): Promise<APIResponse<AckResponse>> {
    return this.acknowledge(agentId, requestId, {
      ackType: 'cancelled',
      requestToken,
      reason,
    }, config);
  }

  // -------------------------------------------------------------------------
  // Clarification Management
  // -------------------------------------------------------------------------

  /**
   * List clarifications for an agent
   *
   * @param agentId - Agent identifier
   * @param pendingOnly - Only return pending requests
   * @returns Clarification list
   */
  async listClarifications(
    agentId: string,
    pendingOnly?: boolean,
    config?: RequestConfig
  ): Promise<APIResponse<ClarificationListResponse>> {
    return apiClient.get<ClarificationListResponse>(
      `${this.baseUrl}/${agentId}/clarifications`,
      {
        ...config,
        params: {
          ...config?.params,
          pending_only: pendingOnly ? 'true' : 'false',
        },
      }
    );
  }

  /**
   * Create a clarification request
   *
   * @param agentId - Agent identifier
   * @param request - Clarification details
   * @returns Created clarification
   */
  async createClarification(
    agentId: string,
    request: CreateClarificationRequest,
    config?: RequestConfig
  ): Promise<APIResponse<ClarificationRequest>> {
    return apiClient.post<ClarificationRequest>(
      `${this.baseUrl}/${agentId}/clarifications`,
      {
        message: request.message,
        options: request.options ?? [],
        default_option: request.defaultOption,
        priority: request.priority ?? 0,
        context: request.context ?? {},
        timeout_seconds: request.timeoutSeconds ?? 300,
      },
      config
    );
  }

  /**
   * Get a specific clarification
   *
   * @param agentId - Agent identifier
   * @param requestId - Request identifier
   * @returns Clarification details
   */
  async getClarification(
    agentId: string,
    requestId: string,
    config?: RequestConfig
  ): Promise<APIResponse<ClarificationRequest>> {
    return apiClient.get<ClarificationRequest>(
      `${this.baseUrl}/${agentId}/clarification/${requestId}`,
      config
    );
  }

  /**
   * Submit response to a clarification
   *
   * @param agentId - Agent identifier
   * @param requestId - Request identifier
   * @param response - User response
   * @returns ACK response
   */
  async respond(
    agentId: string,
    requestId: string,
    response: RespondRequest,
    config?: RequestConfig
  ): Promise<APIResponse<AckResponse>> {
    return apiClient.post<AckResponse>(
      `${this.baseUrl}/${agentId}/clarification/${requestId}/respond`,
      {
        response: response.response,
        response_data: response.responseData ?? {},
      },
      config
    );
  }

  /**
   * Cancel a clarification request
   *
   * @param agentId - Agent identifier
   * @param requestId - Request identifier
   * @param reason - Cancellation reason
   * @returns ACK response
   */
  async cancel(
    agentId: string,
    requestId: string,
    reason?: string,
    config?: RequestConfig
  ): Promise<APIResponse<AckResponse>> {
    return apiClient.delete<AckResponse>(
      `${this.baseUrl}/${agentId}/clarification/${requestId}`,
      {
        ...config,
        params: {
          ...config?.params,
          reason: reason ?? 'user_cancelled',
        },
      }
    );
  }

  // -------------------------------------------------------------------------
  // Global Operations
  // -------------------------------------------------------------------------

  /**
   * List all pending clarifications (priority-sorted)
   *
   * @returns Pending clarifications
   */
  async listPendingClarifications(
    config?: RequestConfig
  ): Promise<APIResponse<ClarificationListResponse>> {
    return apiClient.get<ClarificationListResponse>(
      `${this.baseUrl}/clarifications/pending`,
      config
    );
  }

  /**
   * Get agent statistics
   *
   * @returns Agent stats
   */
  async getStats(
    config?: RequestConfig
  ): Promise<APIResponse<AgentStats>> {
    return apiClient.get<AgentStats>(
      `${this.baseUrl}/stats`,
      config
    );
  }

  /**
   * Clean up expired clarifications
   *
   * @returns Cleanup result
   */
  async cleanup(
    config?: RequestConfig
  ): Promise<APIResponse<{ success: boolean; cleanedUp: number }>> {
    return apiClient.post<{ success: boolean; cleanedUp: number }>(
      `${this.baseUrl}/clarifications/cleanup`,
      {},
      config
    );
  }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Check if a clarification is in a terminal state
 */
export function isTerminalAck(ack: AckType): boolean {
  return ack === 'responded' || ack === 'skipped' || ack === 'cancelled';
}

/**
 * Get priority value for agent type
 */
export function getAgentPriority(agentType: AgentType): AgentPriority {
  const priorities: Record<AgentType, AgentPriority> = {
    compliance: 4,
    routing: 3,
    interior: 2,
    production: 1,
    hull: 2,
    systems: 2,
    weight: 2,
  };
  return priorities[agentType] ?? 0;
}

/**
 * Sort clarifications by priority (highest first)
 */
export function sortByPriority(
  clarifications: ClarificationRequest[]
): ClarificationRequest[] {
  return [...clarifications].sort((a, b) => b.priority - a.priority);
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default agents API client instance
 */
export const agentsAPI = new AgentsAPIClient();
