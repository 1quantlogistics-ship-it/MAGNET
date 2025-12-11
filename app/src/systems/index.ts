/**
 * MAGNET UI Systems
 *
 * Central exports for all UI system modules.
 */

// Event Bus
export {
  eventBus,
  useEventBus,
  UIEventBus,
  createEventBus,
  type DomainEventHandler,
} from './UIEventBus';

// Orchestrator
export { orchestrator, useOrchestrator, UIOrchestrator } from './UIOrchestrator';

// State Reconciler
export { reconciler, useReconciler, UIStateReconciler } from './UIStateReconciler';

// Agent Event Router
export {
  agentRouter,
  useAgentRouter,
  UIAgentEventRouter,
  type AgentType,
  type AgentStreamState,
} from './UIAgentEventRouter';

// Animation Scheduler
export {
  animationScheduler,
  AnimationScheduler,
  EASING,
  scheduleSpring,
  scheduleFade,
  scheduleTransform,
  type AnimationPriority,
  type AnimationState,
  type AnimationEntry,
} from './AnimationScheduler';

// Transaction Manager (V1.4)
export {
  transactionManager,
  useTransactionManager,
  type UITransactionManagerImpl,
} from './UITransactionManager';

// Focus Arbiter (V1.4)
export {
  focusArbiter,
  useFocusArbiter,
  type FocusSurface,
  type FocusPriority,
  type FocusRequest,
  type FocusState,
  type FocusChangeListener,
} from './UIFocusArbiter';

// Bootstrap Manager (V1.4)
export {
  bootstrapManager,
  useBootstrapManager,
  type BootstrapPhase,
  type StoreStatus,
  type SystemStatus,
  type BootstrapState,
  type BootstrapProgress,
  type PhaseChangeListener,
} from './UIBootstrapManager';

// Error Handler (V1.4)
export {
  errorHandler,
  useErrorHandler,
  UIErrorHandlerImpl,
  type UIError,
  type ErrorSeverity,
  type ErrorCategory,
  type ErrorHandler,
  type RetryConfig,
} from './UIErrorHandler';

// PRS Orchestrator (V1.4 - BRAVO)
export {
  prsOrchestrator,
  usePRSOrchestrator,
  PRSOrchestrator,
  type PRSState,
  type MilestoneNotification,
  type TransitionResult,
  type PRSEventType,
  type PRSEventPayload,
} from './PRSOrchestrator';

// Clarification Coordinator (V1.4 - BRAVO)
export {
  clarificationCoordinator,
  useClarificationCoordinator,
  ClarificationCoordinator,
  DEFAULT_ACK_RETRY_CONFIG,
  type AckRetryConfig,
  type CoordinatorState,
  type ClarificationEventType,
} from './ClarificationCoordinator';
