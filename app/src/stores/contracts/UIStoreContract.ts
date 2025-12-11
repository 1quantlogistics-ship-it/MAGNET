/**
 * MAGNET UI Store Contract Implementation
 *
 * Enforces domain-bounded stores with explicit read/write separation.
 * All mutations flow through the UIOrchestrator - no direct store writes.
 */

import { create, StateCreator, StoreApi } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { UIStoreContract, StoreConfig } from '../../types/contracts';

/**
 * Create a domain-bounded store that conforms to UIStoreContract
 *
 * @param config - Store configuration
 * @returns Zustand store with contract-compliant interface
 */
export function createDomainStore<TState extends object>(
  config: StoreConfig<TState>
): StoreApi<UIStoreContract<TState, Partial<TState>>> & {
  use: () => UIStoreContract<TState, Partial<TState>>;
} {
  const { name, initialState, readOnlyFields, readWriteFields, reconcileTransform } = config;

  // Validate that all fields are accounted for
  const allConfiguredFields = new Set([...readOnlyFields, ...readWriteFields]);
  const stateFields = Object.keys(initialState) as (keyof TState)[];

  for (const field of stateFields) {
    if (!allConfiguredFields.has(field)) {
      console.warn(
        `[${name}] Field "${String(field)}" not configured as readOnly or readWrite`
      );
    }
  }

  // Track dirty state
  let isDirtyFlag = false;
  let lastSyncedState: TState = { ...initialState };

  // Create the store
  type StoreState = UIStoreContract<TState, Partial<TState>> & {
    _internal: {
      state: TState;
      setDirty: (dirty: boolean) => void;
    };
  };

  const storeCreator: StateCreator<
    StoreState,
    [['zustand/subscribeWithSelector', never]],
    []
  > = (set, get) => ({
    // Read-only computed state
    get readOnly(): TState {
      return get()._internal.state;
    },

    // Read-write subset
    get readWrite(): Partial<TState> {
      const state = get()._internal.state;
      const result: Partial<TState> = {};

      for (const field of readWriteFields) {
        result[field] = state[field];
      }

      return result;
    },

    // Reconcile from authoritative source (backend)
    reconcile: (source: Partial<TState>) => {
      set((prev) => {
        let newState = { ...prev._internal.state };

        // Apply source values, respecting transforms
        if (reconcileTransform) {
          newState = reconcileTransform(source, newState);
        } else {
          // Default: merge source into state
          for (const key of Object.keys(source) as (keyof TState)[]) {
            if (source[key] !== undefined) {
              newState[key] = source[key] as TState[keyof TState];
            }
          }
        }

        // Update synced state
        lastSyncedState = { ...newState };
        isDirtyFlag = false;

        return {
          ...prev,
          _internal: {
            ...prev._internal,
            state: newState,
          },
        };
      });
    },

    // Reset to initial state
    reset: () => {
      set((prev) => ({
        ...prev,
        _internal: {
          ...prev._internal,
          state: { ...initialState },
        },
      }));
      lastSyncedState = { ...initialState };
      isDirtyFlag = false;
    },

    // Get snapshot for debugging/persistence
    getSnapshot: () => {
      return { ...get()._internal.state };
    },

    // Check if store has local changes
    isDirty: () => isDirtyFlag,

    // Internal state management
    _internal: {
      state: { ...initialState },
      setDirty: (dirty: boolean) => {
        isDirtyFlag = dirty;
      },
    },
  });

  const store = create<StoreState>()(
    subscribeWithSelector(storeCreator)
  );

  // Add convenience hook
  const useStore = () => store.getState();

  return Object.assign(store, { use: useStore });
}

/**
 * Create a read-write action that marks store as dirty
 * Use this to create actions that can be dispatched through the orchestrator
 */
export function createStoreAction<TState extends object, TPayload>(
  store: StoreApi<UIStoreContract<TState, Partial<TState>> & { _internal: { state: TState; setDirty: (dirty: boolean) => void } }>,
  action: (state: TState, payload: TPayload) => Partial<TState>
): (payload: TPayload) => void {
  return (payload: TPayload) => {
    const currentState = store.getState()._internal.state;
    const changes = action(currentState, payload);

    store.setState((prev) => ({
      ...prev,
      _internal: {
        ...prev._internal,
        state: {
          ...prev._internal.state,
          ...changes,
        },
      },
    }));

    // Mark as dirty
    store.getState()._internal.setDirty(true);
  };
}

/**
 * Type helper for extracting store state type
 */
export type ExtractStoreState<T> = T extends StoreApi<UIStoreContract<infer S, unknown>>
  ? S
  : never;
