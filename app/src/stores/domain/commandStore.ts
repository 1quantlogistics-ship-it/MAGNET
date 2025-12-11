/**
 * MAGNET UI Command Store
 *
 * Command palette state management.
 * Uses StoreFactory for domain-bounded store with read-only/read-write separation.
 */

import { createStore } from '../contracts/StoreFactory';
import { UI_SCHEMA_VERSION } from '../../types/schema-version';
import type { UISchemaVersion } from '../../types/schema-version';
import type {
  Command,
  CommandCategory,
  CommandParam,
  CommandResult,
  CommandHistoryEntry,
} from '../../types/command';

/**
 * Command read-only state (from backend/registry)
 */
export interface CommandReadOnlyState {
  schema_version: UISchemaVersion;

  /** All available commands */
  commands: Command[];

  /** Command categories */
  categories: CommandCategory[];

  /** Recently used command IDs */
  recentCommandIds: string[];

  /** Pinned command IDs */
  pinnedCommandIds: string[];

  /** Command execution history */
  history: CommandHistoryEntry[];

  /** Maximum history entries */
  maxHistorySize: number;
}

/**
 * Command read-write state (UI-only)
 */
export interface CommandReadWriteState {
  /** Palette open state */
  isOpen: boolean;

  /** Current search query */
  searchQuery: string;

  /** Selected command index */
  selectedIndex: number;

  /** Active category filter */
  activeCategory: CommandCategory | null;

  /** Command being executed */
  executingCommandId: string | null;

  /** Param input mode */
  isParamInputMode: boolean;

  /** Current param values */
  paramValues: Record<string, unknown>;

  /** Current param index (for multi-param commands) */
  currentParamIndex: number;

  /** Last result */
  lastResult: CommandResult | null;

  /** Show result overlay */
  showResult: boolean;
}

/**
 * Combined command store state
 */
export interface CommandStoreState extends CommandReadOnlyState, CommandReadWriteState {}

/**
 * Initial command state
 */
const initialCommandState: CommandStoreState = {
  schema_version: UI_SCHEMA_VERSION,
  commands: [],
  categories: [],
  recentCommandIds: [],
  pinnedCommandIds: [],
  history: [],
  maxHistorySize: 50,
  isOpen: false,
  searchQuery: '',
  selectedIndex: 0,
  activeCategory: null,
  executingCommandId: null,
  isParamInputMode: false,
  paramValues: {},
  currentParamIndex: 0,
  lastResult: null,
  showResult: false,
};

/**
 * Create the command store
 */
export const commandStore = createStore<CommandStoreState>({
  name: 'command',
  initialState: initialCommandState,
  readOnlyFields: [
    'schema_version',
    'commands',
    'categories',
    'recentCommandIds',
    'pinnedCommandIds',
    'history',
    'maxHistorySize',
  ],
  readWriteFields: [
    'isOpen',
    'searchQuery',
    'selectedIndex',
    'activeCategory',
    'executingCommandId',
    'isParamInputMode',
    'paramValues',
    'currentParamIndex',
    'lastResult',
    'showResult',
  ],
});

// ============================================================================
// Actions
// ============================================================================

/**
 * Open command palette
 */
export function openCommandPalette(): void {
  commandStore.getState()._update(() => ({
    isOpen: true,
    searchQuery: '',
    selectedIndex: 0,
    activeCategory: null,
    isParamInputMode: false,
    paramValues: {},
    currentParamIndex: 0,
    showResult: false,
  }));
}

/**
 * Close command palette
 */
export function closeCommandPalette(): void {
  commandStore.getState()._update(() => ({
    isOpen: false,
    executingCommandId: null,
    isParamInputMode: false,
    paramValues: {},
  }));
}

/**
 * Toggle command palette
 */
export function toggleCommandPalette(): void {
  const isOpen = commandStore.getState().readOnly.isOpen;
  if (isOpen) {
    closeCommandPalette();
  } else {
    openCommandPalette();
  }
}

/**
 * Set search query
 */
export function setSearchQuery(query: string): void {
  commandStore.getState()._update(() => ({
    searchQuery: query,
    selectedIndex: 0,
  }));
}

/**
 * Set selected index
 */
export function setSelectedIndex(index: number): void {
  commandStore.getState()._update(() => ({
    selectedIndex: Math.max(0, index),
  }));
}

/**
 * Move selection up
 */
export function selectPrevious(): void {
  commandStore.getState()._update((state) => ({
    selectedIndex: Math.max(0, state.selectedIndex - 1),
  }));
}

/**
 * Move selection down
 */
export function selectNext(maxIndex: number): void {
  commandStore.getState()._update((state) => ({
    selectedIndex: Math.min(maxIndex, state.selectedIndex + 1),
  }));
}

/**
 * Set active category
 */
export function setActiveCategory(category: CommandCategory | null): void {
  commandStore.getState()._update(() => ({
    activeCategory: category,
    selectedIndex: 0,
  }));
}

/**
 * Enter param input mode
 */
export function enterParamInputMode(commandId: string): void {
  commandStore.getState()._update(() => ({
    executingCommandId: commandId,
    isParamInputMode: true,
    paramValues: {},
    currentParamIndex: 0,
  }));
}

/**
 * Set param value
 */
export function setParamValue(paramId: string, value: unknown): void {
  commandStore.getState()._update((state) => ({
    paramValues: {
      ...state.paramValues,
      [paramId]: value,
    },
  }));
}

/**
 * Move to next param
 */
export function nextParam(): void {
  commandStore.getState()._update((state) => ({
    currentParamIndex: state.currentParamIndex + 1,
  }));
}

/**
 * Move to previous param
 */
export function previousParam(): void {
  commandStore.getState()._update((state) => ({
    currentParamIndex: Math.max(0, state.currentParamIndex - 1),
  }));
}

/**
 * Cancel param input
 */
export function cancelParamInput(): void {
  commandStore.getState()._update(() => ({
    isParamInputMode: false,
    executingCommandId: null,
    paramValues: {},
    currentParamIndex: 0,
  }));
}

/**
 * Set command result
 */
export function setCommandResult(result: CommandResult): void {
  commandStore.getState()._update(() => ({
    lastResult: result,
    showResult: true,
    executingCommandId: null,
    isParamInputMode: false,
  }));
}

/**
 * Dismiss result
 */
export function dismissResult(): void {
  commandStore.getState()._update(() => ({
    showResult: false,
  }));
}

/**
 * Set executing command
 */
export function setExecutingCommand(commandId: string | null): void {
  commandStore.getState()._update(() => ({
    executingCommandId: commandId,
  }));
}

// ============================================================================
// Selectors
// ============================================================================

/**
 * Get all commands
 */
export function getAllCommands(): Command[] {
  return commandStore.getState().readOnly.commands;
}

/**
 * Get filtered commands
 */
export function getFilteredCommands(): Command[] {
  const state = commandStore.getState().readOnly;
  let filtered = [...state.commands];

  // Filter by category
  if (state.activeCategory) {
    filtered = filtered.filter((c) => c.category === state.activeCategory);
  }

  // Filter by search query
  if (state.searchQuery) {
    const query = state.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (c) =>
        c.name.toLowerCase().includes(query) ||
        c.description?.toLowerCase().includes(query) ||
        c.keywords?.some((k) => k.toLowerCase().includes(query))
    );
  }

  // Sort: pinned first, then recent, then alphabetical
  filtered.sort((a, b) => {
    const aPinned = state.pinnedCommandIds.includes(a.id);
    const bPinned = state.pinnedCommandIds.includes(b.id);
    if (aPinned !== bPinned) return aPinned ? -1 : 1;

    const aRecent = state.recentCommandIds.indexOf(a.id);
    const bRecent = state.recentCommandIds.indexOf(b.id);
    if (aRecent !== -1 && bRecent !== -1) return aRecent - bRecent;
    if (aRecent !== -1) return -1;
    if (bRecent !== -1) return 1;

    return a.name.localeCompare(b.name);
  });

  return filtered;
}

/**
 * Get command by ID
 */
export function getCommandById(commandId: string): Command | null {
  return (
    commandStore.getState().readOnly.commands.find((c) => c.id === commandId) ?? null
  );
}

/**
 * Get selected command
 */
export function getSelectedCommand(): Command | null {
  const state = commandStore.getState().readOnly;
  const filtered = getFilteredCommands();
  return filtered[state.selectedIndex] ?? null;
}

/**
 * Get commands by category
 */
export function getCommandsByCategory(): Map<CommandCategory, Command[]> {
  const commands = commandStore.getState().readOnly.commands;
  const grouped = new Map<CommandCategory, Command[]>();

  for (const cmd of commands) {
    const existing = grouped.get(cmd.category) ?? [];
    grouped.set(cmd.category, [...existing, cmd]);
  }

  return grouped;
}

/**
 * Get recent commands
 */
export function getRecentCommands(limit: number = 5): Command[] {
  const state = commandStore.getState().readOnly;
  return state.recentCommandIds
    .slice(0, limit)
    .map((id) => state.commands.find((c) => c.id === id))
    .filter((c): c is Command => c !== undefined);
}

/**
 * Get pinned commands
 */
export function getPinnedCommands(): Command[] {
  const state = commandStore.getState().readOnly;
  return state.pinnedCommandIds
    .map((id) => state.commands.find((c) => c.id === id))
    .filter((c): c is Command => c !== undefined);
}

/**
 * Check if command is pinned
 */
export function isCommandPinned(commandId: string): boolean {
  return commandStore.getState().readOnly.pinnedCommandIds.includes(commandId);
}

/**
 * Get current param being edited
 */
export function getCurrentParam(): CommandParam | null {
  const state = commandStore.getState().readOnly;
  if (!state.executingCommandId || !state.isParamInputMode) return null;

  const command = getCommandById(state.executingCommandId);
  if (!command?.params) return null;

  return command.params[state.currentParamIndex] ?? null;
}

/**
 * Get all param values
 */
export function getParamValues(): Record<string, unknown> {
  return commandStore.getState().readOnly.paramValues;
}

/**
 * Check if all required params are filled
 */
export function areRequiredParamsFilled(): boolean {
  const state = commandStore.getState().readOnly;
  if (!state.executingCommandId) return true;

  const command = getCommandById(state.executingCommandId);
  if (!command?.params) return true;

  const requiredParams = command.params.filter((p) => p.required);
  return requiredParams.every((p) => state.paramValues[p.id] !== undefined);
}

/**
 * Get command history
 */
export function getCommandHistory(limit?: number): CommandHistoryEntry[] {
  const history = commandStore.getState().readOnly.history;
  return limit ? history.slice(0, limit) : history;
}

/**
 * Check if palette is in param input mode
 */
export function isInParamInputMode(): boolean {
  return commandStore.getState().readOnly.isParamInputMode;
}

/**
 * Check if a command is currently executing
 */
export function isExecuting(): boolean {
  return commandStore.getState().readOnly.executingCommandId !== null;
}

/**
 * Get last result
 */
export function getLastResult(): CommandResult | null {
  return commandStore.getState().readOnly.lastResult;
}

/**
 * Check if palette is open
 */
export function isPaletteOpen(): boolean {
  return commandStore.getState().readOnly.isOpen;
}
