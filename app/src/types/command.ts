/**
 * MAGNET UI Command Types
 *
 * Type definitions for the Command Palette (UI-04).
 * Includes CommandResult for action outcomes.
 */

import type { UISchemaVersion } from './schema-version';
import { UI_SCHEMA_VERSION } from './schema-version';

// ============================================================================
// Command Types
// ============================================================================

/**
 * Command categories for organization
 */
export type CommandCategory =
  | 'navigation'    // View/camera commands
  | 'edit'          // Design modification
  | 'analysis'      // Run analysis/validation
  | 'export'        // Export/save
  | 'view'          // Display settings
  | 'ai'            // AI assistant commands
  | 'system'        // System/settings
  | 'recent';       // Recently used

/**
 * Command execution status
 */
export type CommandStatus =
  | 'idle'
  | 'executing'
  | 'success'
  | 'error'
  | 'cancelled';

/**
 * Command parameter type
 */
export type CommandParamType =
  | 'string'
  | 'number'
  | 'boolean'
  | 'select'
  | 'component'   // Component selector
  | 'point3d';    // 3D position picker

/**
 * Command parameter definition
 */
export interface CommandParam {
  id: string;
  label: string;
  type: CommandParamType;
  required: boolean;
  default?: unknown;

  // For select type
  options?: Array<{ value: string; label: string }>;

  // For number type
  min?: number;
  max?: number;
  step?: number;

  // Validation
  validate?: (value: unknown) => string | null; // Returns error message or null
}

/**
 * Command definition
 */
export interface Command {
  id: string;
  schema_version: UISchemaVersion;

  // Display
  label: string;
  description?: string;
  icon?: string;  // Icon identifier

  // Classification
  category: CommandCategory;
  keywords: string[];  // For search

  // Keyboard shortcut
  shortcut?: {
    key: string;
    modifiers?: ('ctrl' | 'shift' | 'alt' | 'meta')[];
    displayText: string;  // e.g., "Ctrl+K"
  };

  // Parameters
  params?: CommandParam[];

  // Execution
  requiresConfirmation?: boolean;
  confirmationMessage?: string;
  isAsync: boolean;

  // Availability
  isAvailable: () => boolean;
  unavailableReason?: string;

  // Action
  execute: (params?: Record<string, unknown>) => Promise<CommandResult>;
}

// ============================================================================
// Command Result (FM6 Compliance - typed action outcomes)
// ============================================================================

/**
 * Result of command execution
 */
export interface CommandResult {
  commandId: string;
  status: 'success' | 'error' | 'cancelled' | 'partial';

  // Success data
  data?: unknown;
  message?: string;

  // Error data
  error?: {
    code: string;
    message: string;
    details?: string;
    recoverable: boolean;
  };

  // Execution metadata
  executionTime: number;  // ms
  timestamp: number;

  // For async operations
  progress?: number;  // 0-100 for partial

  // Undo support
  canUndo: boolean;
  undoAction?: () => Promise<void>;
}

// ============================================================================
// Command Palette State
// ============================================================================

/**
 * Command palette visibility mode
 */
export type PaletteMode =
  | 'closed'
  | 'search'      // Full search mode
  | 'quick'       // Quick action mode (limited results)
  | 'contextual'; // Showing contextual commands

/**
 * Command history entry
 */
export interface CommandHistoryEntry {
  commandId: string;
  timestamp: number;
  params?: Record<string, unknown>;
  result: CommandResult;
}

/**
 * Command store read-only state
 */
export interface CommandReadOnlyState {
  /** All registered commands */
  commands: Record<string, Command>;

  /** Commands by category */
  commandsByCategory: Record<CommandCategory, string[]>;

  /** Available commands (filtered by isAvailable) */
  availableCommandIds: string[];

  /** Matched commands for current search */
  searchResults: string[];
}

/**
 * Command store read-write state
 */
export interface CommandReadWriteState {
  /** Palette visibility mode */
  mode: PaletteMode;

  /** Current search query */
  searchQuery: string;

  /** Selected command index in results */
  selectedIndex: number;

  /** Currently executing command */
  executingCommandId: string | null;

  /** Last command result */
  lastResult: CommandResult | null;

  /** Command history */
  history: CommandHistoryEntry[];

  /** Favorite command IDs */
  favorites: string[];

  /** Recent command IDs */
  recentCommandIds: string[];

  /** Parameter input state (when command needs params) */
  paramInput: {
    commandId: string | null;
    currentParamIndex: number;
    values: Record<string, unknown>;
  };
}

/**
 * Combined command state
 */
export interface CommandState extends CommandReadOnlyState, CommandReadWriteState {}

// ============================================================================
// Default Values
// ============================================================================

export const INITIAL_COMMAND_STATE: CommandReadWriteState = {
  mode: 'closed',
  searchQuery: '',
  selectedIndex: 0,
  executingCommandId: null,
  lastResult: null,
  history: [],
  favorites: [],
  recentCommandIds: [],
  paramInput: {
    commandId: null,
    currentParamIndex: 0,
    values: {},
  },
};

// ============================================================================
// Factory Functions
// ============================================================================

/**
 * Create a command definition
 */
export function createCommand(
  partial: Omit<Command, 'schema_version' | 'isAvailable' | 'execute'> & {
    isAvailable?: () => boolean;
    execute: Command['execute'];
  }
): Command {
  return {
    schema_version: UI_SCHEMA_VERSION,
    isAvailable: () => true,
    ...partial,
  };
}

/**
 * Create a success command result
 */
export function createSuccessResult(
  commandId: string,
  data?: unknown,
  message?: string,
  executionTime: number = 0
): CommandResult {
  return {
    commandId,
    status: 'success',
    data,
    message,
    executionTime,
    timestamp: Date.now(),
    canUndo: false,
  };
}

/**
 * Create an error command result
 */
export function createErrorResult(
  commandId: string,
  errorCode: string,
  errorMessage: string,
  recoverable: boolean = true,
  executionTime: number = 0
): CommandResult {
  return {
    commandId,
    status: 'error',
    error: {
      code: errorCode,
      message: errorMessage,
      recoverable,
    },
    executionTime,
    timestamp: Date.now(),
    canUndo: false,
  };
}

// ============================================================================
// Search Utilities
// ============================================================================

/**
 * Score a command against a search query
 * Higher score = better match
 */
export function scoreCommand(command: Command, query: string): number {
  const lowerQuery = query.toLowerCase();
  let score = 0;

  // Exact label match
  if (command.label.toLowerCase() === lowerQuery) {
    score += 100;
  }
  // Label starts with query
  else if (command.label.toLowerCase().startsWith(lowerQuery)) {
    score += 80;
  }
  // Label contains query
  else if (command.label.toLowerCase().includes(lowerQuery)) {
    score += 50;
  }

  // Keyword matches
  for (const keyword of command.keywords) {
    if (keyword.toLowerCase() === lowerQuery) {
      score += 40;
    } else if (keyword.toLowerCase().startsWith(lowerQuery)) {
      score += 30;
    } else if (keyword.toLowerCase().includes(lowerQuery)) {
      score += 10;
    }
  }

  // Description match
  if (command.description?.toLowerCase().includes(lowerQuery)) {
    score += 5;
  }

  return score;
}

/**
 * Search and sort commands by relevance
 */
export function searchCommands(
  commands: Command[],
  query: string,
  maxResults: number = 10
): Command[] {
  if (!query.trim()) {
    return commands.slice(0, maxResults);
  }

  return commands
    .map(cmd => ({ cmd, score: scoreCommand(cmd, query) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, maxResults)
    .map(({ cmd }) => cmd);
}
