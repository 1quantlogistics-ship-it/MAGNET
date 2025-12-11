/**
 * MAGNET UI Bootstrap Manager
 *
 * Manages initialization sequencing for stores and systems.
 * Ensures WebSocket messages are buffered until stores are ready.
 */

import type { Unsubscribe } from '../types/contracts';

// ============================================================================
// Types
// ============================================================================

/**
 * Bootstrap phases
 */
export type BootstrapPhase =
  | 'idle'           // Not started
  | 'initializing'   // Starting initialization
  | 'stores'         // Initializing stores
  | 'systems'        // Initializing systems
  | 'websocket'      // Connecting WebSocket
  | 'buffering'      // WebSocket connected, buffering until ready
  | 'ready'          // Fully initialized
  | 'error';         // Initialization failed

/**
 * Store initialization status
 */
export interface StoreStatus {
  name: string;
  initialized: boolean;
  error?: string;
}

/**
 * System initialization status
 */
export interface SystemStatus {
  name: string;
  initialized: boolean;
  error?: string;
}

/**
 * Bootstrap state
 */
export interface BootstrapState {
  phase: BootstrapPhase;
  stores: Map<string, StoreStatus>;
  systems: Map<string, SystemStatus>;
  startTime: number | null;
  readyTime: number | null;
  errors: string[];
}

/**
 * Bootstrap progress
 */
export interface BootstrapProgress {
  phase: BootstrapPhase;
  storesReady: number;
  storesTotal: number;
  systemsReady: number;
  systemsTotal: number;
  progress: number; // 0-100
}

/**
 * Phase change listener
 */
export type PhaseChangeListener = (phase: BootstrapPhase, progress: BootstrapProgress) => void;

/**
 * Store initializer function
 */
export type StoreInitializer = () => Promise<void>;

/**
 * System initializer function
 */
export type SystemInitializer = () => Promise<void>;

/**
 * Bootstrap configuration
 */
interface BootstrapConfig {
  /** Enable debug logging */
  debug?: boolean;
  /** Timeout for initialization (ms) */
  timeout?: number;
  /** Callback when ready */
  onReady?: () => void;
  /** Callback on error */
  onError?: (errors: string[]) => void;
}

// ============================================================================
// UIBootstrapManager
// ============================================================================

class UIBootstrapManagerImpl {
  private state: BootstrapState;
  private config: Required<BootstrapConfig>;
  private listeners: Set<PhaseChangeListener> = new Set();
  private storeInitializers: Map<string, StoreInitializer> = new Map();
  private systemInitializers: Map<string, SystemInitializer> = new Map();
  private websocketConnector: (() => Promise<void>) | null = null;
  private timeoutId: ReturnType<typeof setTimeout> | null = null;

  constructor(config: BootstrapConfig = {}) {
    this.config = {
      debug: config.debug ?? process.env.NODE_ENV === 'development',
      timeout: config.timeout ?? 30000,
      onReady: config.onReady ?? (() => {}),
      onError: config.onError ?? (() => {}),
    };

    this.state = {
      phase: 'idle',
      stores: new Map(),
      systems: new Map(),
      startTime: null,
      readyTime: null,
      errors: [],
    };
  }

  /**
   * Register a store initializer
   */
  registerStore(name: string, initializer: StoreInitializer): void {
    this.storeInitializers.set(name, initializer);
    this.state.stores.set(name, { name, initialized: false });

    if (this.config.debug) {
      console.log(`[UIBootstrapManager] Registered store: ${name}`);
    }
  }

  /**
   * Register a system initializer
   */
  registerSystem(name: string, initializer: SystemInitializer): void {
    this.systemInitializers.set(name, initializer);
    this.state.systems.set(name, { name, initialized: false });

    if (this.config.debug) {
      console.log(`[UIBootstrapManager] Registered system: ${name}`);
    }
  }

  /**
   * Register WebSocket connector
   */
  registerWebSocketConnector(connector: () => Promise<void>): void {
    this.websocketConnector = connector;
  }

  /**
   * Start bootstrap process
   */
  async bootstrap(): Promise<boolean> {
    if (this.state.phase !== 'idle') {
      console.warn('[UIBootstrapManager] Bootstrap already in progress or completed');
      return this.state.phase === 'ready';
    }

    this.state.startTime = Date.now();
    this.setPhase('initializing');

    // Set timeout
    this.timeoutId = setTimeout(() => {
      this.handleTimeout();
    }, this.config.timeout);

    try {
      // Initialize stores
      await this.initializeStores();

      // Initialize systems
      await this.initializeSystems();

      // Connect WebSocket
      await this.connectWebSocket();

      // Mark as ready
      this.setPhase('ready');
      this.state.readyTime = Date.now();

      if (this.timeoutId) {
        clearTimeout(this.timeoutId);
        this.timeoutId = null;
      }

      const duration = this.state.readyTime - this.state.startTime!;
      if (this.config.debug) {
        console.log(`[UIBootstrapManager] Bootstrap complete in ${duration}ms`);
      }

      this.config.onReady();
      return true;
    } catch (error) {
      this.handleError(error instanceof Error ? error.message : String(error));
      return false;
    }
  }

  /**
   * Initialize stores
   */
  private async initializeStores(): Promise<void> {
    this.setPhase('stores');

    for (const [name, initializer] of this.storeInitializers) {
      try {
        await initializer();
        const status = this.state.stores.get(name)!;
        status.initialized = true;

        if (this.config.debug) {
          console.log(`[UIBootstrapManager] Store initialized: ${name}`);
        }

        this.notifyProgress();
      } catch (error) {
        const errorMsg = `Store "${name}" failed: ${error instanceof Error ? error.message : error}`;
        const status = this.state.stores.get(name)!;
        status.error = errorMsg;
        throw new Error(errorMsg);
      }
    }
  }

  /**
   * Initialize systems
   */
  private async initializeSystems(): Promise<void> {
    this.setPhase('systems');

    for (const [name, initializer] of this.systemInitializers) {
      try {
        await initializer();
        const status = this.state.systems.get(name)!;
        status.initialized = true;

        if (this.config.debug) {
          console.log(`[UIBootstrapManager] System initialized: ${name}`);
        }

        this.notifyProgress();
      } catch (error) {
        const errorMsg = `System "${name}" failed: ${error instanceof Error ? error.message : error}`;
        const status = this.state.systems.get(name)!;
        status.error = errorMsg;
        throw new Error(errorMsg);
      }
    }
  }

  /**
   * Connect WebSocket
   */
  private async connectWebSocket(): Promise<void> {
    if (!this.websocketConnector) {
      if (this.config.debug) {
        console.log('[UIBootstrapManager] No WebSocket connector registered, skipping');
      }
      return;
    }

    this.setPhase('websocket');
    await this.websocketConnector();
    this.setPhase('buffering');

    // Buffering phase is short - WebSocket is connected but
    // we wait a moment for any initial messages to queue
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  /**
   * Handle initialization timeout
   */
  private handleTimeout(): void {
    this.handleError(`Bootstrap timeout after ${this.config.timeout}ms`);
  }

  /**
   * Handle initialization error
   */
  private handleError(error: string): void {
    this.state.errors.push(error);
    this.setPhase('error');

    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    console.error('[UIBootstrapManager] Bootstrap failed:', error);
    // Pass the latest error directly, full list available via getErrors()
    this.config.onError(error);
  }

  /**
   * Set bootstrap phase
   */
  private setPhase(phase: BootstrapPhase): void {
    this.state.phase = phase;
    this.notifyProgress();
  }

  /**
   * Calculate current progress
   */
  getProgress(): BootstrapProgress {
    const storesReady = Array.from(this.state.stores.values())
      .filter(s => s.initialized).length;
    const storesTotal = this.state.stores.size;
    const systemsReady = Array.from(this.state.systems.values())
      .filter(s => s.initialized).length;
    const systemsTotal = this.state.systems.size;

    const total = storesTotal + systemsTotal + 1; // +1 for WebSocket
    const ready = storesReady + systemsReady + (this.state.phase === 'ready' ? 1 : 0);

    return {
      phase: this.state.phase,
      storesReady,
      storesTotal,
      systemsReady,
      systemsTotal,
      progress: total > 0 ? Math.round((ready / total) * 100) : 0,
    };
  }

  /**
   * Get current phase
   */
  getPhase(): BootstrapPhase {
    return this.state.phase;
  }

  /**
   * Check if ready
   */
  isReady(): boolean {
    return this.state.phase === 'ready';
  }

  /**
   * Subscribe to phase changes
   */
  subscribe(listener: PhaseChangeListener): Unsubscribe {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * Notify listeners of progress
   */
  private notifyProgress(): void {
    const progress = this.getProgress();

    for (const listener of this.listeners) {
      try {
        listener(this.state.phase, progress);
      } catch (error) {
        console.error('[UIBootstrapManager] Listener error:', error);
      }
    }
  }

  /**
   * Reset to initial state
   */
  reset(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    this.state = {
      phase: 'idle',
      stores: new Map(),
      systems: new Map(),
      startTime: null,
      readyTime: null,
      errors: [],
    };

    // Re-register stores/systems as uninitialized
    for (const name of this.storeInitializers.keys()) {
      this.state.stores.set(name, { name, initialized: false });
    }
    for (const name of this.systemInitializers.keys()) {
      this.state.systems.set(name, { name, initialized: false });
    }
  }
}

// ============================================================================
// Exports
// ============================================================================

/**
 * Singleton bootstrap manager instance
 */
export const bootstrapManager = new UIBootstrapManagerImpl({
  debug: process.env.NODE_ENV === 'development',
});

/**
 * Hook for using bootstrap manager in React components
 */
export function useBootstrapManager() {
  return bootstrapManager;
}

export { UIBootstrapManagerImpl };
