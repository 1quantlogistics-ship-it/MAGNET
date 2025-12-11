/**
 * MAGNET UI Clarification Engine
 *
 * Singleton orchestrator for AI-initiated clarification requests.
 * Provides Promise-based API for backend agents to request clarifications.
 */

import type {
  ClarificationType,
  ClarificationPriority,
  ClarificationOption,
  ClarificationField,
  ClarificationResolvedEventDetail,
  ScreenPosition,
  WorldPosition,
} from '../types/clarification';
import {
  requestClarification,
  subscribeToClarification,
} from '../stores/domain/clarificationStore';
import { DEFAULT_AUTO_DISMISS_MS } from '../types/clarification';

/**
 * Options for quick clarification
 */
interface QuickOption {
  label: string;
  value: unknown;
  isDefault?: boolean;
}

/**
 * Options for standard clarification
 */
interface StandardOption {
  label: string;
  description?: string;
  value: unknown;
  isDefault?: boolean;
}

/**
 * Pending request with promise resolvers
 */
interface PendingRequest {
  resolve: (value: unknown) => void;
  reject: (error: Error) => void;
}

/**
 * ClarificationEngine singleton
 *
 * Usage:
 * ```typescript
 * const tankType = await clarify.askQuick(
 *   'Which tank type?',
 *   [
 *     { label: 'Ballast', value: 'ballast' },
 *     { label: 'Fuel', value: 'fuel', isDefault: true }
 *   ]
 * );
 * ```
 */
class ClarificationEngineClass {
  private static instance: ClarificationEngineClass | null = null;
  private pendingRequests = new Map<string, PendingRequest>();
  private unsubscribe: (() => void) | null = null;

  private constructor() {
    this.setupEventListener();
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): ClarificationEngineClass {
    if (!ClarificationEngineClass.instance) {
      ClarificationEngineClass.instance = new ClarificationEngineClass();
    }
    return ClarificationEngineClass.instance;
  }

  /**
   * Setup event listener for resolved clarifications
   */
  private setupEventListener(): void {
    const handler = (event: Event) => {
      const { requestId, status, response } = (event as CustomEvent<ClarificationResolvedEventDetail>).detail;

      const pending = this.pendingRequests.get(requestId);
      if (!pending) return;

      this.pendingRequests.delete(requestId);

      if (status === 'answered') {
        pending.resolve(response);
      } else if (status === 'skipped') {
        pending.resolve(response); // Default value
      } else if (status === 'expired') {
        pending.resolve(response); // Default value
      }
    };

    window.addEventListener('clarification:resolved', handler);
    this.unsubscribe = () => window.removeEventListener('clarification:resolved', handler);
  }

  /**
   * Ask a quick clarification (inline spatial chips)
   *
   * @param question The question to ask
   * @param options Array of options with label, value, and optional isDefault
   * @param assumptionPhrase Optional phrase to show when auto-proceeding (e.g., "I'll proceed with metric units")
   */
  public async askQuick(
    question: string,
    options: QuickOption[],
    assumptionPhrase?: string
  ): Promise<unknown> {
    return this.createRequest('quick', {
      question,
      options: options.map((opt, i) => ({
        id: `opt-${i}`,
        label: opt.label,
        value: opt.value,
        isDefault: opt.isDefault,
      })),
      assumptionPhrase,
      defaultValue: options.find((o) => o.isDefault)?.value ?? options[0]?.value,
      priority: 'recommended',
    });
  }

  /**
   * Ask for option selection (floating spatial card)
   *
   * @param question The question to ask
   * @param context Additional context for the question
   * @param options Array of options with label, description, and value
   * @param allowMultiple Whether to allow selecting multiple options
   */
  public async askOptions(
    question: string,
    context: string,
    options: StandardOption[],
    allowMultiple = false
  ): Promise<unknown> {
    return this.createRequest('standard', {
      question,
      context,
      options: options.map((opt, i) => ({
        id: `opt-${i}`,
        label: opt.label,
        description: opt.description,
        value: opt.value,
        isDefault: opt.isDefault,
      })),
      allowMultiple,
      defaultValue: options.find((o) => o.isDefault)?.value ?? options[0]?.value,
      priority: 'recommended',
    });
  }

  /**
   * Ask for form input (spatial modal form)
   *
   * @param question The question to ask
   * @param context Additional context
   * @param fields Array of field definitions
   */
  public async askForm(
    question: string,
    context: string,
    fields: ClarificationField[]
  ): Promise<Record<string, unknown>> {
    // Build default values
    const defaultValue: Record<string, unknown> = {};
    for (const field of fields) {
      if (field.defaultValue !== undefined) {
        defaultValue[field.id] = field.defaultValue;
      }
    }

    const result = await this.createRequest('complex', {
      question,
      context,
      fields,
      defaultValue,
      priority: 'required',
    });

    return result as Record<string, unknown>;
  }

  /**
   * Ask for 3D component selection (contextual prompt + highlight)
   *
   * @param question The question to ask
   * @param context Optional additional context
   * @param targetPosition Optional screen position to anchor near
   */
  public async askSelectComponent(
    question: string,
    context?: string,
    targetPosition?: ScreenPosition
  ): Promise<string | null> {
    const result = await this.createRequest('contextual', {
      question,
      context,
      targetPosition,
      defaultValue: null,
      priority: 'required',
    });

    return result as string | null;
  }

  /**
   * Internal: create request and return promise
   */
  private createRequest(
    type: ClarificationType,
    params: {
      question: string;
      context?: string;
      options?: ClarificationOption[];
      fields?: ClarificationField[];
      allowMultiple?: boolean;
      targetPosition?: ScreenPosition;
      worldPosition?: WorldPosition;
      assumptionPhrase?: string;
      defaultValue?: unknown;
      priority: ClarificationPriority;
    }
  ): Promise<unknown> {
    return new Promise((resolve, reject) => {
      const id = requestClarification({
        type,
        priority: params.priority,
        question: params.question,
        context: params.context,
        options: params.options,
        fields: params.fields,
        allowMultiple: params.allowMultiple,
        targetPosition: params.targetPosition,
        worldPosition: params.worldPosition,
        assumptionPhrase: params.assumptionPhrase,
        defaultValue: params.defaultValue,
        autoDismissMs: DEFAULT_AUTO_DISMISS_MS,
      });

      this.pendingRequests.set(id, { resolve, reject });
    });
  }

  /**
   * Cleanup (for testing)
   */
  public cleanup(): void {
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
    this.pendingRequests.clear();
    ClarificationEngineClass.instance = null;
  }
}

/**
 * Export singleton instance
 */
export const clarify = ClarificationEngineClass.getInstance();

/**
 * Export class for testing
 */
export { ClarificationEngineClass };

export default clarify;
