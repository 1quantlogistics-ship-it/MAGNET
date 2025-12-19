/**
 * MAGNET UI useIntent Hook
 * Module 63.1: React hook for intent preview/apply flow
 *
 * Combines IntentAPIClient with intentStore for reactive state.
 */

import { useCallback, useMemo } from 'react';
import { useStore } from 'zustand';
import { intentAPI } from '../api/intent';
import {
  intentStore,
  startPreview,
  setPreviewResult,
  setPreviewError,
  startApply,
  setApplyResult,
  setApplyError,
  cancelIntent,
  type IntentStatus,
} from '../stores/domain/intentStore';
import type { IntentPreviewResponse, ApplyResult } from '../types/intent';

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseIntentResult {
  /** Current intent status */
  status: IntentStatus;

  /** Pending preview (if any) */
  pendingPreview: IntentPreviewResponse | null;

  /** Last apply result */
  lastApplyResult: ApplyResult | null;

  /** Error message (if any) */
  error: string | null;

  /** Original input text */
  inputText: string;

  /** Preview a natural language command */
  preview: (designId: string, text: string) => Promise<IntentPreviewResponse | null>;

  /** Apply pending preview */
  apply: (designId: string) => Promise<ApplyResult | null>;

  /** Cancel pending preview */
  cancel: () => void;

  /** Whether there are approved actions to apply */
  canApply: boolean;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for intent preview/apply flow
 *
 * @returns Intent state and actions
 */
export function useIntent(): UseIntentResult {
  // Subscribe to store state
  const state = useStore(intentStore, (s) => s._internal.state);

  /**
   * Preview a natural language command
   */
  const preview = useCallback(
    async (designId: string, text: string): Promise<IntentPreviewResponse | null> => {
      startPreview(text);

      try {
        const response = await intentAPI.preview(designId, text);
        setPreviewResult(response.data);
        return response.data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Preview failed';
        setPreviewError(message);
        return null;
      }
    },
    []
  );

  /**
   * Apply pending preview
   */
  const apply = useCallback(
    async (designId: string): Promise<ApplyResult | null> => {
      const pending = intentStore.getState()._internal.state.pendingPreview;
      if (!pending?.apply_payload) {
        setApplyError('No pending preview to apply');
        return null;
      }

      startApply();

      try {
        const response = await intentAPI.apply(designId, pending.apply_payload);
        setApplyResult(response.data);
        return response.data;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Apply failed';
        setApplyError(message);
        return null;
      }
    },
    []
  );

  /**
   * Cancel pending preview
   */
  const cancel = useCallback(() => {
    cancelIntent();
  }, []);

  // Derived state
  const canApply = useMemo(() => {
    return (
      state.status === 'preview_ready' &&
      state.pendingPreview !== null &&
      state.pendingPreview.approved.length > 0
    );
  }, [state.status, state.pendingPreview]);

  return {
    status: state.status,
    pendingPreview: state.pendingPreview,
    lastApplyResult: state.lastApplyResult,
    error: state.errorMessage,
    inputText: state.inputText,
    preview,
    apply,
    cancel,
    canApply,
  };
}
