/**
 * MAGNET UI Phase API Client
 * BRAVO OWNS THIS FILE.
 *
 * Phase management API for PRS (Phase Readiness System).
 * Tracks design workflow phases and milestones.
 *
 * Endpoints:
 * - GET /phases
 * - GET /phases/{phase}
 * - POST /phases/{phase}/run
 * - POST /phases/{phase}/validate
 * - POST /phases/{phase}/approve
 */

import { apiClient, type APIResponse, type RequestConfig } from '../services/BaseAPIClient';

// ============================================================================
// Types
// ============================================================================

/**
 * Phase status
 */
export type PhaseStatus =
  | 'pending'
  | 'active'
  | 'completed'
  | 'approved'
  | 'failed'
  | 'blocked';

/**
 * Phase name
 */
export type PhaseName =
  | 'mission'
  | 'hull_form'
  | 'structure'
  | 'propulsion'
  | 'systems'
  | 'weight_stability'
  | 'compliance'
  | 'production';

/**
 * Phase info
 */
export interface PhaseInfo {
  phase: PhaseName;
  status: PhaseStatus;
  description?: string;
  lastModified?: string;
  modifiedBy?: string;
}

/**
 * Phase list response
 */
export interface PhaseListResponse {
  phases: PhaseInfo[];
}

/**
 * Phase detail response
 */
export interface PhaseDetailResponse {
  phase: PhaseName;
  status: PhaseStatus;
  details: Record<string, unknown>;
  dependencies?: PhaseName[];
  blockers?: string[];
  phaseHash?: string;
  version?: number;
}

/**
 * Run phase request
 */
export interface RunPhaseRequest {
  phases?: PhaseName[];
  maxIterations?: number;
  asyncMode?: boolean;
}

/**
 * Run phase response
 */
export interface RunPhaseResponse {
  phase: PhaseName;
  status: 'completed' | 'submitted' | 'failed';
  jobId?: string;
  result?: Record<string, unknown>;
  phaseHash?: string;
  version?: number;
}

/**
 * Validate phase response
 */
export interface ValidatePhaseResponse {
  phase: PhaseName;
  passed: boolean;
  errors: number;
  warnings: number;
  issues?: ValidationIssue[];
  phaseHash?: string;
  version?: number;
}

/**
 * Validation issue
 */
export interface ValidationIssue {
  issueId: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  path?: string;
  rule?: string;
}

/**
 * Approve phase request
 */
export interface ApprovePhaseRequest {
  comment?: string;
}

/**
 * Approve phase response
 */
export interface ApprovePhaseResponse {
  phase: PhaseName;
  status: 'approved';
  approvedAt: string;
  approvedBy?: string;
  comment?: string;
  phaseHash?: string;
  version?: number;
}

// ============================================================================
// Phase API Client
// ============================================================================

/**
 * Phase API Client
 *
 * Provides methods for phase management operations.
 * Used by PRSOrchestrator for workflow state machine.
 */
export class PhaseAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1/designs') {
    this.baseUrl = baseUrl;
  }

  /**
   * Build path for phase endpoint
   */
  private path(designId: string, endpoint: string): string {
    return `${this.baseUrl}/${designId}/phases${endpoint}`;
  }

  /**
   * List all phases
   *
   * @param designId - Design identifier
   * @returns Phase list with statuses
   */
  async listPhases(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<PhaseListResponse>> {
    return apiClient.get<PhaseListResponse>(
      this.path(designId, ''),
      config
    );
  }

  /**
   * Get phase details
   *
   * @param designId - Design identifier
   * @param phase - Phase name
   * @returns Phase details
   */
  async getPhase(
    designId: string,
    phase: PhaseName,
    config?: RequestConfig
  ): Promise<APIResponse<PhaseDetailResponse>> {
    return apiClient.get<PhaseDetailResponse>(
      this.path(designId, `/${phase}`),
      config
    );
  }

  /**
   * Run a phase
   *
   * @param designId - Design identifier
   * @param phase - Phase name
   * @param options - Run options
   * @returns Run result
   */
  async runPhase(
    designId: string,
    phase: PhaseName,
    options?: RunPhaseRequest,
    config?: RequestConfig
  ): Promise<APIResponse<RunPhaseResponse>> {
    return apiClient.post<RunPhaseResponse>(
      this.path(designId, `/${phase}/run`),
      {
        phases: options?.phases,
        max_iterations: options?.maxIterations ?? 5,
        async_mode: options?.asyncMode ?? false,
      },
      config
    );
  }

  /**
   * Validate a phase
   *
   * @param designId - Design identifier
   * @param phase - Phase name
   * @returns Validation result
   */
  async validatePhase(
    designId: string,
    phase: PhaseName,
    config?: RequestConfig
  ): Promise<APIResponse<ValidatePhaseResponse>> {
    return apiClient.post<ValidatePhaseResponse>(
      this.path(designId, `/${phase}/validate`),
      {},
      config
    );
  }

  /**
   * Approve a phase
   *
   * @param designId - Design identifier
   * @param phase - Phase name
   * @param comment - Approval comment
   * @returns Approval result
   */
  async approvePhase(
    designId: string,
    phase: PhaseName,
    comment?: string,
    config?: RequestConfig
  ): Promise<APIResponse<ApprovePhaseResponse>> {
    return apiClient.post<ApprovePhaseResponse>(
      this.path(designId, `/${phase}/approve`),
      { comment },
      config
    );
  }

  /**
   * Get all phase statuses as a map
   *
   * @param designId - Design identifier
   * @returns Map of phase name to status
   */
  async getPhaseStatuses(
    designId: string,
    config?: RequestConfig
  ): Promise<Record<PhaseName, PhaseStatus>> {
    const response = await this.listPhases(designId, config);
    const statuses: Record<string, PhaseStatus> = {};
    for (const phase of response.data.phases) {
      statuses[phase.phase] = phase.status;
    }
    return statuses as Record<PhaseName, PhaseStatus>;
  }

  /**
   * Check if phase can be started (dependencies met)
   *
   * @param designId - Design identifier
   * @param phase - Phase name
   * @returns Whether phase can start
   */
  async canStartPhase(
    designId: string,
    phase: PhaseName,
    config?: RequestConfig
  ): Promise<boolean> {
    const detail = await this.getPhase(designId, phase, config);
    const blockers = detail.data.blockers ?? [];
    return blockers.length === 0 && detail.data.status !== 'blocked';
  }
}

// ============================================================================
// Phase Order and Dependencies
// ============================================================================

/**
 * Default phase order
 */
export const PHASE_ORDER: readonly PhaseName[] = [
  'mission',
  'hull_form',
  'structure',
  'propulsion',
  'systems',
  'weight_stability',
  'compliance',
  'production',
] as const;

/**
 * Phase dependencies
 */
export const PHASE_DEPENDENCIES: Record<PhaseName, PhaseName[]> = {
  mission: [],
  hull_form: ['mission'],
  structure: ['hull_form'],
  propulsion: ['hull_form'],
  systems: ['structure', 'propulsion'],
  weight_stability: ['structure', 'systems'],
  compliance: ['weight_stability'],
  production: ['compliance'],
};

/**
 * Get index of phase in order
 */
export function getPhaseIndex(phase: PhaseName): number {
  return PHASE_ORDER.indexOf(phase);
}

/**
 * Get next phase in sequence
 */
export function getNextPhase(phase: PhaseName): PhaseName | null {
  const index = getPhaseIndex(phase);
  if (index < 0 || index >= PHASE_ORDER.length - 1) {
    return null;
  }
  return PHASE_ORDER[index + 1];
}

/**
 * Get previous phase in sequence
 */
export function getPreviousPhase(phase: PhaseName): PhaseName | null {
  const index = getPhaseIndex(phase);
  if (index <= 0) {
    return null;
  }
  return PHASE_ORDER[index - 1];
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default phase API client instance
 */
export const phaseAPI = new PhaseAPIClient();
