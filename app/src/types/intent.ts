/**
 * MAGNET UI Intent Types
 * Module 63.1: Type definitions for intent preview/apply flow
 */

/**
 * Action in an intent
 */
export interface IntentAction {
  action_type: 'set' | 'increase' | 'decrease';
  path: string;
  value?: number | string | boolean;
  amount?: number;
  unit?: string | null;
}

/**
 * Rejected action with reason
 */
export interface RejectedAction {
  action: {
    path: string;
    value?: number | string | boolean;
  };
  reason: string;
}

/**
 * Apply payload - exact shape for POST /actions
 */
export interface ApplyPayload {
  plan_id: string;
  intent_id: string;
  design_version_before: number;
  actions: IntentAction[];
}

/**
 * Intent preview response from backend
 */
export interface IntentPreviewResponse {
  preview: true;
  plan_id: string | null;
  intent_id: string | null;
  design_version_before: number;
  actions: IntentAction[];
  approved: IntentAction[];
  rejected: RejectedAction[];
  warnings: string[];
  guidance?: string;
  apply_payload: ApplyPayload;
}

/**
 * Intent preview request
 */
export interface IntentPreviewRequest {
  text: string;
  design_version_before?: number;
}

/**
 * Apply result from /actions endpoint
 */
export interface ApplyResult {
  success: boolean;
  plan_id: string;
  actions_executed: number;
  design_version_before: number;
  design_version_after: number;
  warnings: string[];
  errors: string[];
}
