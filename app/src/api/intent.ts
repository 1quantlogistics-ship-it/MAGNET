/**
 * MAGNET UI Intent API Client
 * Module 63.1: Intent preview/apply flow
 *
 * Endpoints:
 * - POST /intent/preview - Validate NL command without mutation
 * - POST /actions - Execute approved actions
 */

import { apiClient, type APIResponse, type RequestConfig } from '../services/BaseAPIClient';
import type {
  IntentPreviewRequest,
  IntentPreviewResponse,
  ApplyPayload,
  ApplyResult,
} from '../types/intent';

// ============================================================================
// Intent API Client
// ============================================================================

/**
 * Intent API Client
 *
 * Handles natural language intent preview and apply flow.
 * Preview validates without mutation, Apply executes via /actions.
 */
export class IntentAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1/designs') {
    this.baseUrl = baseUrl;
  }

  /**
   * Build path for intent endpoint
   */
  private path(designId: string, endpoint: string): string {
    return `${this.baseUrl}/${designId}${endpoint}`;
  }

  /**
   * Preview intent - validate without mutation
   *
   * Parses natural language and validates via ActionPlanValidator.
   * Returns approved/rejected actions without changing design state.
   *
   * @param designId - Design identifier
   * @param text - Natural language command
   * @param designVersionBefore - Optional version for stale check
   * @returns Preview result with approved/rejected actions
   */
  async preview(
    designId: string,
    text: string,
    designVersionBefore?: number,
    config?: RequestConfig
  ): Promise<APIResponse<IntentPreviewResponse>> {
    const request: IntentPreviewRequest = {
      text,
      design_version_before: designVersionBefore,
    };

    return apiClient.post<IntentPreviewResponse>(
      this.path(designId, '/intent/preview'),
      request,
      config
    );
  }

  /**
   * Apply approved actions
   *
   * Executes the apply_payload from a preview response.
   * This mutates design state and bumps version.
   *
   * @param designId - Design identifier
   * @param payload - Apply payload from preview response
   * @returns Apply result with version info
   */
  async apply(
    designId: string,
    payload: ApplyPayload,
    config?: RequestConfig
  ): Promise<APIResponse<ApplyResult>> {
    return apiClient.post<ApplyResult>(
      this.path(designId, '/actions'),
      payload,
      config
    );
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default intent API client instance
 */
export const intentAPI = new IntentAPIClient();
