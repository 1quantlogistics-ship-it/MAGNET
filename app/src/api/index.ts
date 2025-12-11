/**
 * MAGNET UI API Clients
 * BRAVO OWNS THIS FILE.
 *
 * Domain-specific API clients for MAGNET backend.
 * All clients use BaseAPIClient for HTTP operations.
 */

// Interior API (Module 59)
export {
  InteriorAPIClient,
  interiorAPI,
  type SpaceType,
  type SpaceCategory,
  type SpaceBoundary,
  type SpaceDefinition,
  type GenerateRequest,
  type GenerateResponse,
  type DeckLayout,
  type LayoutResponse,
  type SpaceRequest,
  type SpaceResponse,
  type ValidationIssue as InteriorValidationIssue,
  type ValidationResponse as InteriorValidationResponse,
  type OptimizeRequest,
  type OptimizeResponse,
} from './interior';

// Routing API (Module 60)
export {
  RoutingAPIClient,
  routingAPI,
  type SystemType,
  type RouteRequest,
  type RouteResponse,
  type TopologyNode,
  type TrunkSegment,
  type SystemTopology,
  type RoutingLayout,
  type RoutingViolation,
  type RoutingValidationResponse,
  type FireZone,
  type WTCompartment,
  type ZonesResponse,
  type RoutingConfig,
} from './routing';

// Phase API (PRS)
export {
  PhaseAPIClient,
  phaseAPI,
  PHASE_ORDER,
  PHASE_DEPENDENCIES,
  getPhaseIndex,
  getNextPhase,
  getPreviousPhase,
  type PhaseStatus,
  type PhaseName,
  type PhaseInfo,
  type PhaseListResponse,
  type PhaseDetailResponse,
  type RunPhaseRequest,
  type RunPhaseResponse,
  type ValidatePhaseResponse,
  type ValidationIssue as PhaseValidationIssue,
  type ApprovePhaseRequest,
  type ApprovePhaseResponse,
} from './phase';

// Agents API (V1.4 Clarification)
export {
  AgentsAPIClient,
  agentsAPI,
  AGENT_PRIORITY_NAMES,
  isTerminalAck,
  getAgentPriority,
  sortByPriority,
  type AckType,
  type AgentPriority,
  type AgentType,
  type AckRequest,
  type AckResponse,
  type ClarificationRequest,
  type AckHistoryEntry,
  type CreateClarificationRequest,
  type ClarificationListResponse,
  type RespondRequest,
  type AgentStats,
} from './agents';
