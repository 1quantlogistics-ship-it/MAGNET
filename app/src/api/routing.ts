/**
 * MAGNET UI Routing API Client
 * BRAVO OWNS THIS FILE.
 *
 * Module 60: Systems Routing API
 * Provides type-safe client for routing operations.
 *
 * Endpoints:
 * - POST /routing/route
 * - GET /routing/layout
 * - DELETE /routing/layout
 * - GET /routing/systems
 * - GET /routing/systems/{system_type}
 * - POST /routing/systems/{system_type}/reroute
 * - DELETE /routing/systems/{system_type}
 * - POST /routing/validate
 * - GET /routing/validation
 * - GET/POST /routing/zones
 * - GET/PUT /routing/config
 */

import { apiClient, type APIResponse, type RequestConfig } from '../services/BaseAPIClient';

// ============================================================================
// Types
// ============================================================================

/**
 * System type enumeration
 */
export type SystemType =
  | 'hvac'
  | 'electrical'
  | 'potable_water'
  | 'fire_main'
  | 'sewage'
  | 'fuel'
  | 'ballast'
  | 'bilge'
  | 'hydraulic'
  | 'pneumatic'
  | 'steam'
  | 'exhaust'
  | 'cargo'
  | 'inert_gas';

/**
 * Route request
 */
export interface RouteRequest {
  systems: string[];
  forceReroute?: boolean;
}

/**
 * Route response
 */
export interface RouteResponse {
  success: boolean;
  systemsRouted: string[];
  systemsFailed: string[];
  totalTrunks: number;
  totalLengthM: number;
  zoneViolations: number;
  log: string[];
  routingHash?: string;
  updateId?: string;
  prevUpdateId?: string;
  version: number;
}

/**
 * Topology node
 */
export interface TopologyNode {
  nodeId: string;
  position: [number, number, number];
  nodeType: 'source' | 'sink' | 'junction' | 'valve' | 'pump';
  spaceId?: string;
  deckId?: string;
}

/**
 * Trunk segment
 */
export interface TrunkSegment {
  trunkId: string;
  systemType: SystemType;
  startNode: string;
  endNode: string;
  path: [number, number, number][];
  lengthM: number;
  diameter?: number;
  material?: string;
  deckIds: string[];
  zoneIds: string[];
}

/**
 * System topology
 */
export interface SystemTopology {
  systemType: SystemType;
  nodes: Record<string, TopologyNode>;
  trunks: Record<string, TrunkSegment>;
  isComplete: boolean;
  totalLengthM: number;
}

/**
 * Routing layout
 */
export interface RoutingLayout {
  topologies: Record<string, SystemTopology>;
  routingHash?: string;
  updateId?: string;
  prevUpdateId?: string;
  version: number;
}

/**
 * Validation violation
 */
export interface RoutingViolation {
  violationId: string;
  systemType: string;
  trunkId?: string;
  rule: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  location?: [number, number, number];
  zoneId?: string;
  deckId?: string;
}

/**
 * Validation response
 */
export interface RoutingValidationResponse {
  isValid: boolean;
  systemsValidated: number;
  totalViolations: number;
  violations: RoutingViolation[];
  routingHash?: string;
  version: number;
}

/**
 * Fire zone definition
 */
export interface FireZone {
  zoneId: string;
  name: string;
  deckIds: string[];
  boundarySpaces: string[];
  rating: string;
}

/**
 * Watertight compartment
 */
export interface WTCompartment {
  compartmentId: string;
  name: string;
  boundaryFrames: [number, number];
  deckIds: string[];
}

/**
 * Zones response
 */
export interface ZonesResponse {
  fireZones: Record<string, FireZone>;
  wtCompartments: Record<string, WTCompartment>;
}

/**
 * Routing config
 */
export interface RoutingConfig {
  maxIterations: number;
  convergenceThreshold: number;
  allowCrossZone: boolean;
  preferVerticalFirst: boolean;
  minClearance: number;
  maxBendAngle: number;
}

// ============================================================================
// Routing API Client
// ============================================================================

/**
 * Routing API Client
 *
 * Provides methods for systems routing operations.
 * All responses include routing hashes and version tracking.
 */
export class RoutingAPIClient {
  private baseUrl: string;

  constructor(baseUrl: string = '/api/v1/designs') {
    this.baseUrl = baseUrl;
  }

  /**
   * Build path for routing endpoint
   */
  private path(designId: string, endpoint: string): string {
    return `${this.baseUrl}/${designId}/routing${endpoint}`;
  }

  /**
   * Route systems
   *
   * @param designId - Design identifier
   * @param systems - Systems to route
   * @param forceReroute - Force re-routing even if already routed
   * @returns Routing result
   */
  async route(
    designId: string,
    systems: string[],
    forceReroute?: boolean,
    config?: RequestConfig
  ): Promise<APIResponse<RouteResponse>> {
    return apiClient.post<RouteResponse>(
      this.path(designId, '/route'),
      { systems, force_reroute: forceReroute ?? false },
      config
    );
  }

  /**
   * Get routing layout
   *
   * @param designId - Design identifier
   * @returns Full routing layout
   */
  async getLayout(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<RoutingLayout>> {
    return apiClient.get<RoutingLayout>(
      this.path(designId, '/layout'),
      config
    );
  }

  /**
   * Clear all routing
   *
   * @param designId - Design identifier
   * @returns Operation result
   */
  async clearLayout(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<{ success: boolean; message: string }>> {
    return apiClient.delete<{ success: boolean; message: string }>(
      this.path(designId, '/layout'),
      config
    );
  }

  /**
   * List routed systems
   *
   * @param designId - Design identifier
   * @returns List of system types with routing
   */
  async listSystems(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<string[]>> {
    return apiClient.get<string[]>(
      this.path(designId, '/systems'),
      config
    );
  }

  /**
   * Get system topology
   *
   * @param designId - Design identifier
   * @param systemType - System type
   * @returns System topology
   */
  async getSystemTopology(
    designId: string,
    systemType: string,
    config?: RequestConfig
  ): Promise<APIResponse<SystemTopology>> {
    return apiClient.get<SystemTopology>(
      this.path(designId, `/systems/${systemType}`),
      config
    );
  }

  /**
   * Reroute a specific system
   *
   * @param designId - Design identifier
   * @param systemType - System type
   * @returns Rerouting result
   */
  async rerouteSystem(
    designId: string,
    systemType: string,
    config?: RequestConfig
  ): Promise<APIResponse<{ success: boolean; systemType: string; trunkCount: number; totalLengthM: number }>> {
    return apiClient.post<{ success: boolean; systemType: string; trunkCount: number; totalLengthM: number }>(
      this.path(designId, `/systems/${systemType}/reroute`),
      {},
      config
    );
  }

  /**
   * Clear system routing
   *
   * @param designId - Design identifier
   * @param systemType - System type
   * @returns Operation result
   */
  async clearSystemRouting(
    designId: string,
    systemType: string,
    config?: RequestConfig
  ): Promise<APIResponse<{ success: boolean; message: string }>> {
    return apiClient.delete<{ success: boolean; message: string }>(
      this.path(designId, `/systems/${systemType}`),
      config
    );
  }

  /**
   * Validate routing
   *
   * @param designId - Design identifier
   * @returns Validation result
   */
  async validate(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<RoutingValidationResponse>> {
    return apiClient.post<RoutingValidationResponse>(
      this.path(designId, '/validate'),
      {},
      config
    );
  }

  /**
   * Get validation result
   *
   * @param designId - Design identifier
   * @returns Last validation result
   */
  async getValidationResult(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<RoutingValidationResponse>> {
    return apiClient.get<RoutingValidationResponse>(
      this.path(designId, '/validation'),
      config
    );
  }

  /**
   * Get zones
   *
   * @param designId - Design identifier
   * @returns Zone definitions
   */
  async getZones(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<ZonesResponse>> {
    return apiClient.get<ZonesResponse>(
      this.path(designId, '/zones'),
      config
    );
  }

  /**
   * Update zones
   *
   * @param designId - Design identifier
   * @param zones - Zone definitions
   * @returns Operation result
   */
  async updateZones(
    designId: string,
    zones: Partial<ZonesResponse>,
    config?: RequestConfig
  ): Promise<APIResponse<{ success: boolean }>> {
    return apiClient.post<{ success: boolean }>(
      this.path(designId, '/zones'),
      {
        fire_zones: zones.fireZones,
        wt_compartments: zones.wtCompartments,
      },
      config
    );
  }

  /**
   * Get routing config
   *
   * @param designId - Design identifier
   * @returns Routing configuration
   */
  async getConfig(
    designId: string,
    config?: RequestConfig
  ): Promise<APIResponse<RoutingConfig>> {
    return apiClient.get<RoutingConfig>(
      this.path(designId, '/config'),
      config
    );
  }

  /**
   * Update routing config
   *
   * @param designId - Design identifier
   * @param routingConfig - Configuration updates
   * @returns Operation result
   */
  async updateConfig(
    designId: string,
    routingConfig: Partial<RoutingConfig>,
    config?: RequestConfig
  ): Promise<APIResponse<{ success: boolean }>> {
    return apiClient.put<{ success: boolean }>(
      this.path(designId, '/config'),
      routingConfig,
      config
    );
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default routing API client instance
 */
export const routingAPI = new RoutingAPIClient();
