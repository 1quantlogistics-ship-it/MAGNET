/**
 * MAGNET UI Focus Arbiter
 *
 * Manages modal/focus state across the application.
 * Ensures only one modal surface has focus at a time and
 * handles focus transitions smoothly.
 */

import { UIEventBus } from './UIEventBus';
import { createUIEvent } from '../types/events';
import { UI_SCHEMA_VERSION } from '../types/schema-version';
import type { Unsubscribe } from '../types/contracts';

// ============================================================================
// Types
// ============================================================================

/**
 * Focus surfaces in the application
 */
export type FocusSurface =
  | 'workspace'           // Main 3D workspace
  | 'chat'                // Chat panel
  | 'prs-panel'           // PRS phase panel
  | 'context-menu'        // PRS context menu
  | 'clarification'       // Clarification modal
  | 'command-palette'     // Command palette
  | 'settings'            // Settings modal
  | 'error-modal'         // Error modal
  | 'milestone-toast'     // Milestone celebration
  | null;                 // No focus

/**
 * Focus priority levels
 */
export type FocusPriority = 'critical' | 'high' | 'normal' | 'low';

/**
 * Focus request
 */
export interface FocusRequest {
  surface: FocusSurface;
  priority: FocusPriority;
  source: string;
  timestamp: number;
}

/**
 * Focus state
 */
export interface FocusState {
  /** Currently focused surface */
  current: FocusSurface;
  /** Previously focused surface (for restoration) */
  previous: FocusSurface;
  /** Focus history stack */
  history: FocusSurface[];
  /** Whether focus is locked (prevents changes) */
  isLocked: boolean;
  /** Current lock holder (if locked) */
  lockHolder: string | null;
}

/**
 * Focus change listener
 */
export type FocusChangeListener = (
  current: FocusSurface,
  previous: FocusSurface
) => void;

/**
 * Focus arbiter configuration
 */
interface FocusArbiterConfig {
  /** Enable debug logging */
  debug?: boolean;
  /** Maximum history size */
  maxHistorySize?: number;
  /** Default surface when nothing focused */
  defaultSurface?: FocusSurface;
}

// ============================================================================
// Priority Map
// ============================================================================

const PRIORITY_ORDER: Record<FocusPriority, number> = {
  critical: 4,
  high: 3,
  normal: 2,
  low: 1,
};

const SURFACE_PRIORITY: Partial<Record<NonNullable<FocusSurface>, FocusPriority>> = {
  'error-modal': 'critical',
  'clarification': 'high',
  'command-palette': 'high',
  'context-menu': 'normal',
  'settings': 'normal',
  'milestone-toast': 'normal',
  'chat': 'low',
  'prs-panel': 'low',
  'workspace': 'low',
};

// ============================================================================
// UIFocusArbiter
// ============================================================================

class UIFocusArbiterImpl {
  private state: FocusState;
  private config: Required<FocusArbiterConfig>;
  private listeners: Set<FocusChangeListener> = new Set();

  constructor(config: FocusArbiterConfig = {}) {
    this.config = {
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      maxHistorySize: config.maxHistorySize ?? 10,
      defaultSurface: config.defaultSurface ?? 'workspace',
    };

    this.state = {
      current: this.config.defaultSurface,
      previous: null,
      history: [],
      isLocked: false,
      lockHolder: null,
    };
  }

  /**
   * Request focus for a surface
   * Returns true if focus was granted
   */
  requestFocus(surface: FocusSurface, source: string = 'unknown'): boolean {
    // Can't focus null directly, use releaseFocus instead
    if (surface === null) {
      return this.releaseFocus(source);
    }

    // Check if focus is locked by someone else
    const isLockHolder = this.state.isLocked && this.state.lockHolder === source;
    if (this.state.isLocked && !isLockHolder) {
      if (this.config.debug) {
        console.log(`[UIFocusArbiter] Focus request denied - locked by ${this.state.lockHolder}`);
      }
      return false;
    }

    // Skip priority check if requestor holds the lock
    if (!isLockHolder) {
      // Check priority (higher priority can preempt)
      const currentPriority = this.getSurfacePriority(this.state.current);
      const requestedPriority = this.getSurfacePriority(surface);

      if (PRIORITY_ORDER[requestedPriority] < PRIORITY_ORDER[currentPriority]) {
        if (this.config.debug) {
          console.log(`[UIFocusArbiter] Focus request denied - lower priority`);
        }
        return false;
      }
    }

    this.setFocus(surface, source);
    return true;
  }

  /**
   * Release focus from current surface
   */
  releaseFocus(source: string = 'unknown'): boolean {
    // Check if focus is locked by someone else
    if (this.state.isLocked && this.state.lockHolder !== source) {
      if (this.config.debug) {
        console.log(`[UIFocusArbiter] Release denied - locked by ${this.state.lockHolder}`);
      }
      return false;
    }

    // Restore previous focus or default
    const newFocus = this.state.previous || this.config.defaultSurface;
    this.setFocus(newFocus, source);
    return true;
  }

  /**
   * Pop focus from history (go back)
   */
  popFocus(source: string = 'unknown'): FocusSurface {
    if (this.state.isLocked && this.state.lockHolder !== source) {
      return this.state.current;
    }

    const previousFromHistory = this.state.history.pop() || this.config.defaultSurface;
    this.setFocus(previousFromHistory, source, false);
    return this.state.current;
  }

  /**
   * Lock focus to prevent changes
   */
  lockFocus(holder: string): boolean {
    if (this.state.isLocked) {
      return this.state.lockHolder === holder;
    }

    this.state.isLocked = true;
    this.state.lockHolder = holder;

    if (this.config.debug) {
      console.log(`[UIFocusArbiter] Focus locked by ${holder}`);
    }

    return true;
  }

  /**
   * Unlock focus
   */
  unlockFocus(holder: string): boolean {
    if (!this.state.isLocked || this.state.lockHolder !== holder) {
      return false;
    }

    this.state.isLocked = false;
    this.state.lockHolder = null;

    if (this.config.debug) {
      console.log(`[UIFocusArbiter] Focus unlocked by ${holder}`);
    }

    return true;
  }

  /**
   * Get current focus state
   */
  getState(): Readonly<FocusState> {
    return { ...this.state };
  }

  /**
   * Get current focused surface
   */
  getCurrentFocus(): FocusSurface {
    return this.state.current;
  }

  /**
   * Check if a surface is currently focused
   */
  isFocused(surface: FocusSurface): boolean {
    return this.state.current === surface;
  }

  /**
   * Check if focus is locked
   */
  isLocked(): boolean {
    return this.state.isLocked;
  }

  /**
   * Subscribe to focus changes
   */
  subscribe(listener: FocusChangeListener): Unsubscribe {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Reset focus to default
   */
  reset(): void {
    this.state = {
      current: this.config.defaultSurface,
      previous: null,
      history: [],
      isLocked: false,
      lockHolder: null,
    };

    if (this.config.debug) {
      console.log('[UIFocusArbiter] Reset to default state');
    }
  }

  /**
   * Set focus internally
   */
  private setFocus(surface: FocusSurface, source: string, addToHistory: boolean = true): void {
    const previous = this.state.current;

    if (previous === surface) {
      return; // No change
    }

    // Add to history
    if (addToHistory && previous !== null) {
      this.state.history.push(previous);

      // Trim history if needed
      if (this.state.history.length > this.config.maxHistorySize) {
        this.state.history = this.state.history.slice(-this.config.maxHistorySize);
      }
    }

    this.state.previous = previous;
    this.state.current = surface;

    if (this.config.debug) {
      console.log(`[UIFocusArbiter] Focus changed: ${previous} -> ${surface} (source: ${source})`);
    }

    // Notify listeners
    for (const listener of this.listeners) {
      try {
        listener(surface, previous);
      } catch (error) {
        console.error('[UIFocusArbiter] Listener error:', error);
      }
    }

    // Emit focus events
    if (previous) {
      UIEventBus.emit(createUIEvent('ui:panel_blur', { panelId: previous }, 'system'));
    }
    if (surface) {
      UIEventBus.emit(createUIEvent('ui:panel_focus', {
        panelId: surface,
        previousPanelId: previous ?? undefined,
      }, 'system'));
    }
  }

  /**
   * Get priority for a surface
   */
  private getSurfacePriority(surface: FocusSurface): FocusPriority {
    if (surface === null) return 'low';
    return SURFACE_PRIORITY[surface] || 'normal';
  }
}

// ============================================================================
// Exports
// ============================================================================

/**
 * Singleton focus arbiter instance
 */
export const focusArbiter = new UIFocusArbiterImpl({
  debug: process.env.NODE_ENV === 'development',
});

/**
 * Hook for using focus arbiter in React components
 */
export function useFocusArbiter() {
  return focusArbiter;
}

export { UIFocusArbiterImpl };
