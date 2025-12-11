/**
 * MAGNET UI Error Overlay
 *
 * Full-screen error display for critical errors
 * that require user attention before continuing.
 */

import React, { useEffect, useState } from 'react';
import { errorHandler, UIError, ErrorSeverity } from '../../systems/UIErrorHandler';
import { focusArbiter } from '../../systems/UIFocusArbiter';

// ============================================================================
// Types
// ============================================================================

interface ErrorOverlayProps {
  /** Filter errors by minimum severity */
  minSeverity?: ErrorSeverity;
  /** Custom renderer for error content */
  renderError?: (error: UIError, onDismiss: () => void) => React.ReactNode;
  /** Called when overlay is dismissed */
  onDismiss?: () => void;
  /** Z-index for overlay */
  zIndex?: number;
}

// ============================================================================
// Constants
// ============================================================================

const SEVERITY_ORDER: Record<ErrorSeverity, number> = {
  info: 0,
  warning: 1,
  error: 2,
  critical: 3,
};

const SEVERITY_ICONS: Record<ErrorSeverity, string> = {
  info: 'info-circle',
  warning: 'exclamation-triangle',
  error: 'exclamation-circle',
  critical: 'times-circle',
};

// ============================================================================
// ErrorOverlay
// ============================================================================

export const ErrorOverlay: React.FC<ErrorOverlayProps> = ({
  minSeverity = 'error',
  renderError,
  onDismiss,
  zIndex = 9999,
}) => {
  const [errors, setErrors] = useState<UIError[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Subscribe to error handler
  useEffect(() => {
    const updateErrors = () => {
      const activeErrors = errorHandler.getActiveErrors()
        .filter(e => SEVERITY_ORDER[e.severity] >= SEVERITY_ORDER[minSeverity])
        .sort((a, b) => SEVERITY_ORDER[b.severity] - SEVERITY_ORDER[a.severity]);
      setErrors(activeErrors);
    };

    // Initial load
    updateErrors();

    // Subscribe to new errors
    const unsubscribe = errorHandler.subscribe(() => {
      updateErrors();
    });

    return () => {
      unsubscribe();
    };
  }, [minSeverity]);

  // Lock focus when overlay is visible
  useEffect(() => {
    if (errors.length > 0) {
      focusArbiter.requestFocus('error-modal', 'ErrorOverlay');
      focusArbiter.lockFocus('ErrorOverlay');
    } else {
      focusArbiter.unlockFocus('ErrorOverlay');
      focusArbiter.releaseFocus('ErrorOverlay');
    }

    return () => {
      focusArbiter.unlockFocus('ErrorOverlay');
    };
  }, [errors.length]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (errors.length === 0) return;

      if (e.key === 'Escape') {
        handleDismissCurrent();
      } else if (e.key === 'ArrowRight' && currentIndex < errors.length - 1) {
        setCurrentIndex(i => i + 1);
      } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
        setCurrentIndex(i => i - 1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [errors.length, currentIndex]);

  const handleDismissCurrent = () => {
    if (errors[currentIndex]) {
      errorHandler.dismiss(errors[currentIndex].id);
      if (currentIndex >= errors.length - 1) {
        setCurrentIndex(Math.max(0, currentIndex - 1));
      }
      onDismiss?.();
    }
  };

  const handleDismissAll = () => {
    errors.forEach(e => errorHandler.dismiss(e.id));
    setCurrentIndex(0);
    onDismiss?.();
  };

  // Don't render if no qualifying errors
  if (errors.length === 0) {
    return null;
  }

  const currentError = errors[currentIndex];

  return (
    <div
      className="error-overlay"
      style={{ zIndex }}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="error-overlay-title"
    >
      <div className="error-overlay__backdrop" onClick={handleDismissCurrent} />
      <div className={`error-overlay__content error-overlay__content--${currentError.severity}`}>
        {renderError ? (
          renderError(currentError, handleDismissCurrent)
        ) : (
          <>
            <div className="error-overlay__header">
              <span className={`error-overlay__icon error-overlay__icon--${currentError.severity}`}>
                {SEVERITY_ICONS[currentError.severity]}
              </span>
              <h2 id="error-overlay-title" className="error-overlay__title">
                {currentError.severity === 'critical' ? 'Critical Error' : 'Error'}
              </h2>
            </div>

            <div className="error-overlay__body">
              <p className="error-overlay__message">{currentError.userMessage}</p>
              {currentError.suggestedAction && (
                <p className="error-overlay__action">{currentError.suggestedAction}</p>
              )}
              {process.env.NODE_ENV === 'development' && (
                <details className="error-overlay__details">
                  <summary>Technical Details</summary>
                  <code>{currentError.code}</code>
                  <pre>{currentError.message}</pre>
                </details>
              )}
            </div>

            <div className="error-overlay__footer">
              {errors.length > 1 && (
                <div className="error-overlay__pagination">
                  <button
                    onClick={() => setCurrentIndex(i => i - 1)}
                    disabled={currentIndex === 0}
                  >
                    Previous
                  </button>
                  <span>{currentIndex + 1} of {errors.length}</span>
                  <button
                    onClick={() => setCurrentIndex(i => i + 1)}
                    disabled={currentIndex === errors.length - 1}
                  >
                    Next
                  </button>
                </div>
              )}
              <div className="error-overlay__actions">
                {errors.length > 1 && (
                  <button
                    className="error-overlay__dismiss-all"
                    onClick={handleDismissAll}
                  >
                    Dismiss All
                  </button>
                )}
                <button
                  className="error-overlay__dismiss"
                  onClick={handleDismissCurrent}
                >
                  {currentError.retryable ? 'Dismiss & Retry' : 'Dismiss'}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ErrorOverlay;
