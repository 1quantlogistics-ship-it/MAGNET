/**
 * MAGNET UI useChat Hook
 * Module 65.x: React hook for chat with backend integration
 */

import { useCallback, useRef } from 'react';
import { useChatStore } from '../stores/domain/chatStore';
import { useIntent } from './useIntent';
import type { ChatMessage } from '../types/chat';
import type { IntentPreviewResponse } from '../types/intent';

// ============================================================================
// Hook Return Type
// ============================================================================

export interface UseChatResult {
  /** All chat messages */
  messages: ChatMessage[];

  /** Whether AI is responding */
  isStreaming: boolean;

  /** Current input value */
  inputValue: string;

  /** Set input value */
  setInputValue: (value: string) => void;

  /** Send a message (triggers intent preview) */
  sendMessage: (designId: string, content: string) => Promise<void>;

  /** Apply pending preview */
  applyPending: (designId: string) => Promise<void>;

  /** Cancel pending preview */
  cancelPending: () => void;

  /** Whether there's a pending preview that can be applied */
  canApply: boolean;

  /** Pending preview (if any) */
  pendingPreview: IntentPreviewResponse | null;
}

// ============================================================================
// Helper: Format Preview as Chat Message
// ============================================================================

function formatPreviewResponse(preview: IntentPreviewResponse): string {
  const parts: string[] = [];

  // Status summary
  const approvedCount = preview.approved?.length ?? 0;
  const rejectedCount = preview.rejected?.length ?? 0;

  if (approvedCount > 0) {
    parts.push(`✓ ${approvedCount} action${approvedCount > 1 ? 's' : ''} approved`);
  }
  if (rejectedCount > 0) {
    parts.push(`✗ ${rejectedCount} action${rejectedCount > 1 ? 's' : ''} rejected`);
  }

  // Show approved actions
  if (preview.approved && preview.approved.length > 0) {
    parts.push('\n**Approved:**');
    for (const action of preview.approved) {
      const value = action.value !== undefined ? ` → ${action.value}` : '';
      parts.push(`• \`${action.path}\`${value}`);
    }
  }

  // Show rejected actions
  if (preview.rejected && preview.rejected.length > 0) {
    parts.push('\n**Rejected:**');
    for (const rejection of preview.rejected) {
      parts.push(`• \`${rejection.action.path}\`: ${rejection.reason}`);
    }
  }

  // Show warnings
  if (preview.warnings && preview.warnings.length > 0) {
    parts.push('\n**Warnings:**');
    for (const warning of preview.warnings) {
      parts.push(`⚠ ${warning}`);
    }
  }

  // Apply prompt
  if (approvedCount > 0) {
    parts.push('\n\nSay **"apply"** to execute, or **"cancel"** to discard.');
  } else if (preview.guidance) {
    parts.push(`\n\n${preview.guidance}`);
  }

  return parts.join('\n');
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook for chat with backend integration
 *
 * @returns Chat state and actions
 */
export function useChat(): UseChatResult {
  // Chat store state
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const inputValue = useChatStore((s) => s.inputValue);
  const setInputValue = useChatStore((s) => s.setInputValue);
  const addMessage = useChatStore((s) => s.addMessage);
  const startStreaming = useChatStore((s) => s.startStreaming);
  const appendStreamContent = useChatStore((s) => s.appendStreamContent);
  const finishStreaming = useChatStore((s) => s.finishStreaming);

  // Intent flow
  const { preview, apply, cancel, canApply, pendingPreview } = useIntent();

  /**
   * Send a message - routes to intent preview
   */
  const sendMessage = useCallback(
    async (designId: string, content: string) => {
      // Handle special commands
      const lowerContent = content.toLowerCase().trim();

      if (lowerContent === 'apply') {
        // Apply pending preview
        if (canApply) {
          await apply(designId);
          addMessage({
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: '✓ Changes applied successfully.',
            timestamp: Date.now(),
            status: 'sent',
          });
        } else {
          addMessage({
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: 'No pending changes to apply.',
            timestamp: Date.now(),
            status: 'sent',
          });
        }
        return;
      }

      if (lowerContent === 'cancel') {
        cancel();
        addMessage({
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: 'Pending changes cancelled.',
          timestamp: Date.now(),
          status: 'sent',
        });
        return;
      }

      // Add user message
      addMessage({
        id: `msg-${Date.now()}-user`,
        role: 'user',
        content,
        timestamp: Date.now(),
        status: 'sent',
      });

      // Start streaming indicator
      startStreaming();

      try {
        // Route to intent preview
        const previewResult = await preview(designId, content);

        if (previewResult) {
          const response = formatPreviewResponse(previewResult);

          // Simulate streaming for better UX
          for (const char of response) {
            await new Promise((r) => setTimeout(r, 5));
            appendStreamContent(char);
          }
        } else {
          appendStreamContent("I couldn't understand that command. Try something like:\n");
          appendStreamContent('• "set beam to 9 meters"\n');
          appendStreamContent('• "increase length by 10%"');
        }

        finishStreaming();
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Unknown error';
        appendStreamContent(`Error: ${errorMsg}`);
        finishStreaming();
      }
    },
    [
      preview,
      apply,
      cancel,
      canApply,
      addMessage,
      startStreaming,
      appendStreamContent,
      finishStreaming,
    ]
  );

  /**
   * Apply pending preview
   */
  const applyPending = useCallback(
    async (designId: string) => {
      if (canApply) {
        const result = await apply(designId);
        if (result) {
          addMessage({
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: `✓ Applied ${result.actions_executed} change${result.actions_executed > 1 ? 's' : ''}. Design version: ${result.design_version_before} → ${result.design_version_after}`,
            timestamp: Date.now(),
            status: 'sent',
          });
        }
      }
    },
    [apply, canApply, addMessage]
  );

  /**
   * Cancel pending preview
   */
  const cancelPending = useCallback(() => {
    cancel();
    addMessage({
      id: `msg-${Date.now()}`,
      role: 'assistant',
      content: 'Pending changes cancelled.',
      timestamp: Date.now(),
      status: 'sent',
    });
  }, [cancel, addMessage]);

  return {
    messages,
    isStreaming,
    inputValue,
    setInputValue,
    sendMessage,
    applyPending,
    cancelPending,
    canApply,
    pendingPreview,
  };
}
