/**
 * MAGNET UI Interior API Client
 * BRAVO OWNS THIS FILE.
 *
 * Module 59: Interior Layout API
 * Provides type-safe client for interior layout operations.
 *
 * Endpoints:
 * - POST /interior/generate
 * - GET /interior/layout
 * - POST /interior/spaces
 * - PUT /interior/spaces/{space_id}
 * - DELETE /interior/spaces/{space_id}
 * - POST /interior/validate
 * - POST /interior/optimize
 */

import { apiClient, type APIResponse, type RequestConfig } from '../services/BaseAPIClient';
import type { DomainHashes } from '../types/domainHashes';

// ============================================================================
// Types
// ============================================================================

/**
 * Space type enumeration
 */
export type SpaceType =
  | 'engine_room'
  | 'bridge'
  | 'cargo_hold'
  | 'ballast_tank'
  | 'fuel_tank'
  | 'cabin_crew'
  | 'cabin_officer'
  | 'cabin_passenger'
  | 'mess_crew'
  | 'galley'
  | 'laundry'
  | 'hospital'
  | 'stairway'
  | 'corridor'
  | 'void_space'
  | 'cofferdam';

/**
 * Space category
 */
export type SpaceCategory =
  | 'safety'
  | 'operational'
  | 'living'
  | 'cargo'
  | 'service'
  | 'circulation';

/**
 * Space boundary definition
 */
export interface SpaceBoundary {
  points: [number, number][];
  deckId: string;
  zMin: number;
  zMax: number;
}

/**
 * Space definition
 */
export interface SpaceDefinition {
  spaceId: string;
  name: string;
  spaceType: SpaceType;
  category: SpaceCategory;
  boundary: SpaceBoundary;
  deckId: string;
  zoneId?: string;
  maxOccupancy: number;
  isManned: boolean;
  notes?: string;
}

/**
 * Generation request parameters
 */
export interface GenerateRequest {
  loa: number;
  beam: number;
  depth: number;
  numDecks: number;
  crewCapacity: number;
  passengerCapacity: number;
  shipType: string;
}

/**
 * Generation response
 */
export interface GenerateResponse {
  success: boolean;
  layoutId?: string;
  designId: string;
  spaceCount: number;
  deckCount: number;
  totalAreaM2: number;
  arrangementHash?: string;
  updateId?: string;
  prevUpdateId?: string;
  version: number;
  errors: string[];
  warnings: string[];
}

/**
 * Deck layout data
 */
export interface DeckLayout {
  deckId: string;
  name: string;
  zLevel: number;
  height: number;
  spaces: SpaceDefinition[];
}

/**
 * Full layout response
 */
export interface LayoutResponse {
  layoutId: string;
  designId: string;
  version: number;
  updateId: string;
  prevUpdateId?: string;
  arrangementHash: string;
  spaceCount: number;
  deckCount: number;
  totalAreaM2: number;
  totalVolumeM3: number;
  decks: Record<string, DeckLayout>;
  metadata: Record<string, unknown>;
}

/**
 * Space request (create/update)
 */
export interface SpaceRequest {
  name: string;
  spaceType: SpaceType;
  category: SpaceCategory;
  boundary: {
    points: [number, number][];
    deckId: string;
    zMin: number;
    zMax: number;
  };
  deckId: string;
  zoneId?: string;
  maxOccupancy?: number;
  isManned?: boolean;
  notes?: string;
}

/**
 * Space operation response
 */
export interface SpaceResponse {
  success: boolean;
  spaceId: string;
  updateId: string;
  prevUpdateId?: string;
  arrangementHash: string;
  version: number;
  message: string;
}

/**
 * Validation issue
 */
export interface ValidationIssue {
  issueId: string;
  category: string;
  severity: 'error' | 'warning' | 'info' | 'critical';
  message: string;
  spaceId?: string;
  deckId?: string;
  regulation?: string;
  details: Record<string, unknown>;
}

/**
 * Validation response
 */
export interface ValidationResponse {
  isValid: boolean;
  designId: string;
  errorsCount: number;
  warningsCount: number;
  issues: ValidationIssue[];
  arrangementHash: string;
  version: number;
}

/**
 * Optimization request
 */
export interface OptimizeRequest {
  objectives?: Record<string, number>;
}

/**
 * Optimization response
 */
export interface OptimizeResponse {
  success: boolean;
  designId: string;
  improvements: Record<string, number>;
  updateId: string;
  prevUpdateId?: string;
  arrangementHash: string;
  version: number;
  message: string;
}

// ============================================================================
// Interior API Client
// ============================================================================

/**
 * Interior API Client
 *
 * Provides methods for interior layout management.
 * All responses include arrangement hashes and version tracking.
 */
export class InteriorAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1/designs') {
    this.baseUrl = baseUrl;
  }

  /**
   * Build path for interior endpoint
   */
  private path(designId: string, endpoint: string): string {
    return `${this.baseUrl}/${designId}/interior${endpoint}`;
  }

  /**
   * Generate interior layout
   *
   * @param designId - Design identifier
   * @param params - Generation parameters
   * @returns Generated layout summary
   */
  async generate(
    designId: string,
    params: GenerateRequest,
    config?: RequestConfig
  ): Promise<APIResponse<GenerateResponse>> {
    return apiClient.post<GenerateResponse>(
      this.path(designId, '/generate'),
      {
        loa: params.loa,
        beam: params.beam,
        depth: params.depth,
        num_decks: params.numDecks,
        crew_capacity: params.crewCapacity,
        passenger_capacity: params.passengerCapacity,
        ship_type: params.shipType,
      },
      config
    );
  }

  /**
   * Get current layout
   *
   * @param designId - Design identifier
   * @returns Full layout data
   */
  async getLayout(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<LayoutResponse>> {
    return apiClient.get<LayoutResponse>(
      this.path(designId, '/layout'),
      config
    );
  }

  /**
   * Create a new space
   *
   * @param designId - Design identifier
   * @param space - Space definition
   * @returns Created space info
   */
  async createSpace(
    designId: string,
    space: SpaceRequest,
    config?: RequestConfig
  ): Promise<APIResponse<SpaceResponse>> {
    return apiClient.post<SpaceResponse>(
      this.path(designId, '/spaces'),
      {
        name: space.name,
        space_type: space.spaceType,
        category: space.category,
        boundary: {
          points: space.boundary.points,
          deck_id: space.boundary.deckId,
          z_min: space.boundary.zMin,
          z_max: space.boundary.zMax,
        },
        deck_id: space.deckId,
        zone_id: space.zoneId,
        max_occupancy: space.maxOccupancy ?? 0,
        is_manned: space.isManned ?? false,
        notes: space.notes ?? '',
      },
      config
    );
  }

  /**
   * Update an existing space
   *
   * @param designId - Design identifier
   * @param spaceId - Space identifier
   * @param space - Updated space definition
   * @returns Update result
   */
  async updateSpace(
    designId: string,
    spaceId: string,
    space: SpaceRequest,
    config?: RequestConfig
  ): Promise<APIResponse<SpaceResponse>> {
    return apiClient.put<SpaceResponse>(
      this.path(designId, `/spaces/${spaceId}`),
      {
        name: space.name,
        space_type: space.spaceType,
        category: space.category,
        boundary: {
          points: space.boundary.points,
          deck_id: space.boundary.deckId,
          z_min: space.boundary.zMin,
          z_max: space.boundary.zMax,
        },
        deck_id: space.deckId,
        zone_id: space.zoneId,
        max_occupancy: space.maxOccupancy ?? 0,
        is_manned: space.isManned ?? false,
        notes: space.notes ?? '',
      },
      config
    );
  }

  /**
   * Delete a space
   *
   * @param designId - Design identifier
   * @param spaceId - Space identifier
   * @returns Deletion result
   */
  async deleteSpace(
    designId: string,
    spaceId: string,
    config?: RequestConfig
  ): Promise<APIResponse<SpaceResponse>> {
    return apiClient.delete<SpaceResponse>(
      this.path(designId, `/spaces/${spaceId}`),
      config
    );
  }

  /**
   * Validate layout
   *
   * @param designId - Design identifier
   * @returns Validation result
   */
  async validate(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<ValidationResponse>> {
    return apiClient.post<ValidationResponse>(
      this.path(designId, '/validate'),
      {},
      config
    );
  }

  /**
   * Optimize layout
   *
   * @param designId - Design identifier
   * @param objectives - Optimization objectives and weights
   * @returns Optimization result
   */
  async optimize(
    designId: string,
    objectives?: Record<string, number>,
    config?: RequestConfig
  ): Promise<APIResponse<OptimizeResponse>> {
    return apiClient.post<OptimizeResponse>(
      this.path(designId, '/optimize'),
      { objectives: objectives ?? {} },
      config
    );
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default interior API client instance
 */
export const interiorAPI = new InteriorAPIClient();
