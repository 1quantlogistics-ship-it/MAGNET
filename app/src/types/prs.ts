/**
 * MAGNET UI Module 02: PRS Type Definitions
 *
 * Complete TypeScript interfaces for the Prompt Recommendation System.
 * Provides contextual "Here's what you might want to do next" suggestions.
 */

import type { UISchemaVersion } from './schema-version';
import { UI_SCHEMA_VERSION } from './schema-version';

// ============================================================================
// Core Enums
// ============================================================================

/** Semantic categories for prompt grouping */
export type PRSCategory =
  | 'action'        // Do something
  | 'clarification' // Ask for details
  | 'navigation'    // Go somewhere
  | 'enhancement';  // Improve something

/** What triggered the prompt */
export type PRSTrigger =
  | 'hover'      // Mouse over component
  | 'selection'  // Component selected
  | 'phase'      // Phase-based suggestion
  | 'milestone'; // After milestone

/** Action types for prompts */
export type PRSActionType = 'chat' | 'command' | 'navigate' | 'modal';

/** Phase status in the workflow */
export type PRSPhaseStatus = 'completed' | 'active' | 'available' | 'locked';

/** Surface depth levels for 3D transforms */
export type PRSSurfaceDepth = 'near' | 'mid' | 'far';

/** Surface variants for visual styling */
export type PRSSurfaceVariant = 'default' | 'active' | 'success';

// ============================================================================
// Core Interfaces
// ============================================================================

/**
 * Action to execute when prompt is selected
 */
export interface PRSAction {
  type: PRSActionType;
  /** For 'chat' type - text to send */
  prompt?: string;
  /** For 'command' type - command identifier */
  commandId?: string;
  /** Additional parameters */
  params?: Record<string, unknown>;
  /** For 'navigate' type - target element ID */
  targetId?: string;
  /** For 'modal' type - modal identifier */
  modalId?: string;
}

/**
 * Single prompt recommendation
 */
export interface PRSPrompt {
  id: string;
  category: PRSCategory;
  trigger: PRSTrigger;

  /** Display text - STRICT: 5-8 words, max 25 chars */
  label: string;

  /** SVG icon component name */
  icon: string;

  /** Context references */
  targetId?: string;
  targetType?: string;
  phaseId?: string;

  /** Behavior */
  action: PRSAction;

  /** Ranking score 0-1 */
  relevance: number;

  /** When created */
  timestamp: number;
}

/**
 * Workflow phase definition
 */
export interface PRSPhase {
  id: string;
  name: string;
  status: PRSPhaseStatus;
  /** Progress percentage 0-100 */
  progress?: number;
  /** Associated prompts */
  prompts: PRSPrompt[];
  /** Phase order index */
  order: number;
  /** Description of the phase */
  description?: string;
}

/**
 * Milestone celebration definition
 */
export interface PRSMilestone {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  primaryAction: {
    label: string;
    action: PRSAction;
  };
  secondaryAction?: {
    label: string;
    action: PRSAction;
  };
  /** Auto-dismiss after N ms (0 = no auto-dismiss) */
  autoDismissMs?: number;
}

// ============================================================================
// Context Menu
// ============================================================================

/**
 * Context menu state
 */
export interface PRSContextMenuState {
  isOpen: boolean;
  targetId: string | null;
  position: { x: number; y: number };
  /** For 3D raycast positioning */
  worldPosition?: { x: number; y: number; z: number };
}

/**
 * Prompts grouped by category
 */
export interface PRSGroupedPrompts {
  action: PRSPrompt[];
  clarification: PRSPrompt[];
  navigation: PRSPrompt[];
  enhancement: PRSPrompt[];
}

// ============================================================================
// Component Props
// ============================================================================

/**
 * VisionSurface component props
 */
export interface VisionSurfaceProps {
  /** Visual variant */
  variant?: PRSSurfaceVariant;
  /** Depth level for 3D transform */
  depth?: PRSSurfaceDepth;
  /** Content */
  children: React.ReactNode;
  /** Additional className */
  className?: string;
  /** Additional styles */
  style?: React.CSSProperties;
  /** Click handler */
  onClick?: (event: React.MouseEvent) => void;
  /** Whether surface is focused */
  isFocused?: boolean;
}

/**
 * PRS PillButton component props (extends core PillButton)
 */
export interface PRSPillButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

/**
 * ContextMenu component props
 */
export interface ContextMenuProps {
  /** Whether menu is open */
  isOpen: boolean;
  /** Screen position */
  position: { x: number; y: number };
  /** World position for 3D transform */
  worldPosition?: { x: number; y: number; z: number };
  /** Grouped prompts to display */
  prompts: PRSGroupedPrompts;
  /** Called when prompt is selected */
  onSelectPrompt: (prompt: PRSPrompt) => void;
  /** Called when menu should close */
  onClose: () => void;
  /** Target element ID */
  targetId?: string;
}

/**
 * ContextMenuItem component props
 */
export interface ContextMenuItemProps {
  prompt: PRSPrompt;
  index: number;
  onSelect: () => void;
  isHighlighted?: boolean;
}

/**
 * PromptChip component props
 */
export interface PromptChipProps {
  prompt: PRSPrompt;
  onSelect: () => void;
  size?: 'sm' | 'md';
  className?: string;
}

/**
 * PhaseItem component props
 */
export interface PhaseItemProps {
  phase: PRSPhase;
  index: number;
  isActive: boolean;
  onSelect: () => void;
  isFocused?: boolean;
}

/**
 * PhasePanel component props
 */
export interface PhasePanelProps {
  phases: PRSPhase[];
  currentPhaseId: string | null;
  onSelectPhase: (phaseId: string) => void;
  onSelectPrompt: (prompt: PRSPrompt) => void;
  className?: string;
}

/**
 * MilestoneToast component props
 */
export interface MilestoneToastProps {
  milestone: PRSMilestone;
  onDismiss: () => void;
  onPrimaryAction: () => void;
  onSecondaryAction?: () => void;
}

/**
 * ChatSuggestions component props
 */
export interface ChatSuggestionsProps {
  suggestions: PRSPrompt[];
  onSelectSuggestion: (prompt: PRSPrompt) => void;
  maxVisible?: number;
  className?: string;
}

// ============================================================================
// Store Interface
// ============================================================================

/**
 * PRS Store state and actions
 */
export interface PRSStoreState {
  schema_version: UISchemaVersion;

  // Context menu state
  contextMenu: PRSContextMenuState;
  contextPrompts: PRSGroupedPrompts;

  // Phase state
  phases: PRSPhase[];
  currentPhaseId: string | null;

  // Milestone state
  milestoneQueue: PRSMilestone[];
  currentMilestone: PRSMilestone | null;

  // Chat suggestions
  chatSuggestions: PRSPrompt[];

  // Loading states
  isLoadingPhases: boolean;
  isLoadingSuggestions: boolean;
}

/**
 * PRS Store actions
 */
export interface PRSStoreActions {
  // Context menu
  setContextPrompts: (prompts: PRSGroupedPrompts) => void;
  showContextMenu: (
    targetId: string,
    position: { x: number; y: number },
    worldPosition?: { x: number; y: number; z: number }
  ) => void;
  hideContextMenu: () => void;

  // Phases
  setPhases: (phases: PRSPhase[]) => void;
  setCurrentPhase: (phaseId: string) => void;
  completePhase: (phaseId: string) => void;
  updatePhaseProgress: (phaseId: string, progress: number) => void;

  // Milestones
  showMilestone: (milestone: PRSMilestone) => void;
  dismissMilestone: () => void;
  queueMilestone: (milestone: PRSMilestone) => void;

  // Chat suggestions
  setChatSuggestions: (prompts: PRSPrompt[]) => void;
  clearChatSuggestions: () => void;

  // Actions
  executePrompt: (prompt: PRSPrompt) => void;

  // Reset
  reset: () => void;
}

/**
 * Complete PRS Store interface
 */
export interface PRSStore extends PRSStoreState, PRSStoreActions {}

// ============================================================================
// Focus Orchestrator
// ============================================================================

/** Surfaces that can receive focus */
export type PRSFocusSurface =
  | 'context-menu'
  | 'phase-panel'
  | 'milestone-toast'
  | 'chat-suggestions'
  | 'workspace'
  | null;

/**
 * Focus state for soft-focus orchestration
 */
export interface PRSFocusState {
  focusedSurface: PRSFocusSurface;
  previousSurface: PRSFocusSurface;
  transitionTimestamp: number;
}

// ============================================================================
// Icon Types
// ============================================================================

/** Available PRS icon names */
export type PRSIconName =
  | 'phase-complete'
  | 'phase-active'
  | 'phase-available'
  | 'phase-locked'
  | 'action'
  | 'clarification'
  | 'navigation'
  | 'enhancement'
  | 'chat'
  | 'command'
  | 'chevron-right'
  | 'chevron-down'
  | 'check'
  | 'close'
  | 'sparkle'
  | 'lightbulb'
  | 'target'
  | 'arrow-right'
  | 'info'
  | 'warning'
  | 'success'
  | 'milestone';

/**
 * PRSIcon component props
 */
export interface PRSIconProps {
  name: PRSIconName;
  size?: number;
  className?: string;
  color?: string;
}

// ============================================================================
// Initial States
// ============================================================================

export const INITIAL_CONTEXT_MENU_STATE: PRSContextMenuState = {
  isOpen: false,
  targetId: null,
  position: { x: 0, y: 0 },
};

export const INITIAL_GROUPED_PROMPTS: PRSGroupedPrompts = {
  action: [],
  clarification: [],
  navigation: [],
  enhancement: [],
};

export const INITIAL_PRS_STATE: PRSStoreState = {
  schema_version: UI_SCHEMA_VERSION,
  contextMenu: INITIAL_CONTEXT_MENU_STATE,
  contextPrompts: INITIAL_GROUPED_PROMPTS,
  phases: [],
  currentPhaseId: null,
  milestoneQueue: [],
  currentMilestone: null,
  chatSuggestions: [],
  isLoadingPhases: false,
  isLoadingSuggestions: false,
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Group prompts by category
 */
export function groupPromptsByCategory(prompts: PRSPrompt[]): PRSGroupedPrompts {
  const grouped: PRSGroupedPrompts = {
    action: [],
    clarification: [],
    navigation: [],
    enhancement: [],
  };

  for (const prompt of prompts) {
    grouped[prompt.category].push(prompt);
  }

  // Sort by relevance within each category
  for (const category of Object.keys(grouped) as PRSCategory[]) {
    grouped[category].sort((a, b) => b.relevance - a.relevance);
  }

  return grouped;
}

/**
 * Get total prompt count from grouped prompts
 */
export function getTotalPromptCount(grouped: PRSGroupedPrompts): number {
  return (
    grouped.action.length +
    grouped.clarification.length +
    grouped.navigation.length +
    grouped.enhancement.length
  );
}

/**
 * Check if grouped prompts has any prompts
 */
export function hasPrompts(grouped: PRSGroupedPrompts): boolean {
  return getTotalPromptCount(grouped) > 0;
}

/**
 * Get category display label
 */
export function getCategoryLabel(category: PRSCategory): string {
  const labels: Record<PRSCategory, string> = {
    action: 'Actions',
    clarification: 'Clarify',
    navigation: 'Navigate',
    enhancement: 'Enhance',
  };
  return labels[category];
}

/**
 * Get phase status icon name
 */
export function getPhaseStatusIcon(status: PRSPhaseStatus): PRSIconName {
  const icons: Record<PRSPhaseStatus, PRSIconName> = {
    completed: 'phase-complete',
    active: 'phase-active',
    available: 'phase-available',
    locked: 'phase-locked',
  };
  return icons[status];
}
