/**
 * MAGNET UI Store Factory
 *
 * Factory for creating domain-bounded stores with consistent patterns.
 * Ensures all stores follow the UIStoreContract interface.
 *
 * V1.4.1: Fixed getter issue - readOnly now uses _internal.state directly
 * since JavaScript getters don't survive Zustand's state serialization.
 */

import { create, StoreApi } from 'zustand';
import { subscribeWithSelector, devtools } from 'zustand/middleware';
import type { UIStoreContract, StoreConfig } from '../../types/contracts';

/**
 * Store registry for debugging and orchestrator access
 */
const storeRegistry = new Map<string, StoreApi<unknown>>();

/**
 * Get all registered stores
 */
export function getRegisteredStores(): Map<string, StoreApi<unknown>> {
  return new Map(storeRegistry);
}

/**
 * Get a specific store by name
 */
export function getStore<T>(name: string): StoreApi<T> | undefined {
  return storeRegistry.get(name) as StoreApi<T> | undefined;
}

/**
 * Store state with internal tracking
 */
interface InternalStoreState<TState> {
  /** Current state */
  state: TState;
  /** Last synced state (for dirty checking) */
  lastSyncedState: TState;
  /** Whether store has unsaved changes */
  isDirty: boolean;
  /** Timestamp of last reconciliation */
  lastReconcileTimestamp: number;
}

/**
 * Full store interface including internals
 *
 * NOTE: readOnly is kept for backwards compatibility but consumers
 * should prefer using _internal.state directly for reliable access.
 */
type FullStoreState<TState> = UIStoreContract<TState, Partial<TState>> & {
  _internal: InternalStoreState<TState>;
  _update: (updater: (state: TState) => Partial<TState>) => void;
  /** Getter function for read-only state - use this instead of readOnly property */
  getReadOnly: () => TState;
  /** Getter function for read-write state */
  getReadWrite: () => Partial<TState>;
};

/**
 * Create a domain-bounded store
 */
export function createStore<TState extends object>(
  config: StoreConfig<TState>
): StoreApi<FullStoreState<TState>> {
  const {
    name,
    initialState,
    readOnlyFields,
    readWriteFields,
    reconcileTransform,
  } = config;

  const store = create<FullStoreState<TState>>()(
    devtools(
      subscribeWithSelector((set, get) => ({
        // UIStoreContract implementation
        // NOTE: readOnly as a getter doesn't work in Zustand - use getReadOnly() instead
        get readOnly(): TState {
          // This getter won't work after state updates due to Zustand's serialization
          // Kept for interface compatibility - consumers should use getReadOnly()
          return get()._internal.state;
        },

        get readWrite(): Partial<TState> {
          const state = get()._internal.state;
          const result: Partial<TState> = {};
          for (const field of readWriteFields) {
            result[field] = state[field];
          }
          return result;
        },

        // Function-based accessors that work correctly with Zustand
        getReadOnly: (): TState => {
          return get()._internal.state;
        },

        getReadWrite: (): Partial<TState> => {
          const state = get()._internal.state;
          const result: Partial<TState> = {};
          for (const field of readWriteFields) {
            result[field] = state[field];
          }
          return result;
        },

        reconcile: (source: Partial<TState>) => {
          set((prev) => {
            let newState: TState;

            if (reconcileTransform) {
              newState = reconcileTransform(source, prev._internal.state);
            } else {
              newState = { ...prev._internal.state };
              for (const key of Object.keys(source) as (keyof TState)[]) {
                if (source[key] !== undefined) {
                  newState[key] = source[key] as TState[keyof TState];
                }
              }
            }

            return {
              ...prev,
              _internal: {
                state: newState,
                lastSyncedState: { ...newState },
                isDirty: false,
                lastReconcileTimestamp: Date.now(),
              },
            };
          });
        },

        reset: () => {
          set((prev) => ({
            ...prev,
            _internal: {
              state: { ...initialState },
              lastSyncedState: { ...initialState },
              isDirty: false,
              lastReconcileTimestamp: Date.now(),
            },
          }));
        },

        getSnapshot: () => {
          return { ...get()._internal.state };
        },

        isDirty: () => {
          return get()._internal.isDirty;
        },

        // Internal state
        _internal: {
          state: { ...initialState },
          lastSyncedState: { ...initialState },
          isDirty: false,
          lastReconcileTimestamp: 0,
        },

        // Internal update function (used by orchestrator actions)
        _update: (updater: (state: TState) => Partial<TState>) => {
          set((prev) => {
            const changes = updater(prev._internal.state);
            return {
              ...prev,
              _internal: {
                ...prev._internal,
                state: { ...prev._internal.state, ...changes },
                isDirty: true,
              },
            };
          });
        },
      })),
      { name: `MAGNET:${name}` }
    )
  );

  // Register store
  storeRegistry.set(name, store as unknown as StoreApi<unknown>);

  return store;
}

/**
 * Create a selector hook for a store
 */
export function createStoreSelector<TState extends object, TSelected>(
  store: StoreApi<FullStoreState<TState>>,
  selector: (state: TState) => TSelected
): () => TSelected {
  return () => {
    const state = store.getState()._internal.state;
    return selector(state);
  };
}

/**
 * Create multiple selectors for a store
 */
export function createStoreSelectors<
  TState extends object,
  TSelectors extends Record<string, (state: TState) => unknown>
>(
  store: StoreApi<FullStoreState<TState>>,
  selectors: TSelectors
): { [K in keyof TSelectors]: () => ReturnType<TSelectors[K]> } {
  const result = {} as { [K in keyof TSelectors]: () => ReturnType<TSelectors[K]> };

  for (const key of Object.keys(selectors) as (keyof TSelectors)[]) {
    result[key] = createStoreSelector(store, selectors[key]) as () => ReturnType<TSelectors[typeof key]>;
  }

  return result;
}

/**
 * Subscribe to store changes with automatic cleanup
 */
export function subscribeToStore<TState extends object, TSelected>(
  store: StoreApi<FullStoreState<TState>>,
  selector: (state: TState) => TSelected,
  listener: (selected: TSelected, previousSelected: TSelected) => void
): () => void {
  return store.subscribe(
    (fullState) => selector(fullState._internal.state),
    listener
  );
}

/**
 * Batch multiple store updates
 */
export function batchStoreUpdates(updates: (() => void)[]): void {
  // In Zustand, updates are already batched in React 18
  // This function is for explicit batching outside React
  for (const update of updates) {
    update();
  }
}

/**
 * Reset all registered stores
 */
export function resetAllStores(): void {
  for (const store of storeRegistry.values()) {
    const typedStore = store as StoreApi<FullStoreState<unknown>>;
    if (typeof typedStore.getState().reset === 'function') {
      typedStore.getState().reset();
    }
  }
}

/**
 * Get dirty stores (stores with unsaved changes)
 */
export function getDirtyStores(): string[] {
  const dirty: string[] = [];

  for (const [name, store] of storeRegistry) {
    const typedStore = store as StoreApi<FullStoreState<unknown>>;
    if (typedStore.getState().isDirty()) {
      dirty.push(name);
    }
  }

  return dirty;
}
