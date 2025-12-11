/**
 * MAGNET UI Fallback Modal
 *
 * Full-screen fallback UI when critical errors occur
 * or when the application needs user intervention to recover.
 */

import React, { useEffect, useCallback } from 'react';
import { focusArbiter } from '../../systems/UIFocusArbiter';

// ============================================================================
// Types
// ============================================================================

interface FallbackModalProps {
  /** Title for the fallback */
  title: string;
  /** Description of what went wrong */
  description: string;
  /** Error details (for developers) */
  errorDetails?: string;
  /** Stack trace (for developers) */
  stackTrace?: string;
  /** Show retry button */
  showRetry?: boolean;
  /** Show refresh page button */
  showRefresh?: boolean;
  /** Show contact support link */
  showSupport?: boolean;
  /** Support URL */
  supportUrl?: string;
  /** Called when retry is clicked */
  onRetry?: () => void;
  /** Called when user dismisses (if dismissable) */
  onDismiss?: () => void;
  /** Whether modal can be dismissed */
  dismissable?: boolean;
  /** Illustration type */
  illustration?: 'error' | 'maintenance' | 'offline' | 'timeout';
}

// ============================================================================
// Constants
// ============================================================================

const ILLUSTRATIONS: Record<string, string> = {
  error: '❌',
  maintenance: '🔧',
  offline: '📡',
  timeout: '⏱️',
};

// ============================================================================
// FallbackModal
// ============================================================================

export const FallbackModal: React.FC<FallbackModalProps> = ({
  title,
  description,
  errorDetails,
  stackTrace,
  showRetry = true,
  showRefresh = true,
  showSupport = false,
  supportUrl = 'mailto:support@magnet.ai',
  onRetry,
  onDismiss,
  dismissable = false,
  illustration = 'error',
}) => {
  // Lock focus when modal is open
  useEffect(() => {
    focusArbiter.requestFocus('error-modal', 'FallbackModal');
    focusArbiter.lockFocus('FallbackModal');

    return () => {
      focusArbiter.unlockFocus('FallbackModal');
      focusArbiter.releaseFocus('FallbackModal');
    };
  }, []);

  // Handle escape key
  useEffect(() => {
    if (!dismissable) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onDismiss?.();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dismissable, onDismiss]);

  const handleRefresh = useCallback(() => {
    window.location.reload();
  }, []);

  return (
    <div
      className="fallback-modal"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="fallback-modal-title"
      aria-describedby="fallback-modal-description"
    >
      <div className="fallback-modal__backdrop" />
      <div className="fallback-modal__content">
        <div className="fallback-modal__illustration">
          {ILLUSTRATIONS[illustration]}
        </div>

        <h1 id="fallback-modal-title" className="fallback-modal__title">
          {title}
        </h1>

        <p id="fallback-modal-description" className="fallback-modal__description">
          {description}
        </p>

        {process.env.NODE_ENV === 'development' && errorDetails && (
          <details className="fallback-modal__details">
            <summary>Error Details</summary>
            <pre className="fallback-modal__error-details">{errorDetails}</pre>
            {stackTrace && (
              <pre className="fallback-modal__stack-trace">{stackTrace}</pre>
            )}
          </details>
        )}

        <div className="fallback-modal__actions">
          {showRetry && onRetry && (
            <button
              className="fallback-modal__button fallback-modal__button--primary"
              onClick={onRetry}
            >
              Try Again
            </button>
          )}
          {showRefresh && (
            <button
              className="fallback-modal__button fallback-modal__button--secondary"
              onClick={handleRefresh}
            >
              Refresh Page
            </button>
          )}
          {showSupport && (
            <a
              href={supportUrl}
              className="fallback-modal__link"
              target="_blank"
              rel="noopener noreferrer"
            >
              Contact Support
            </a>
          )}
          {dismissable && onDismiss && (
            <button
              className="fallback-modal__button fallback-modal__button--text"
              onClick={onDismiss}
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FallbackModal;
