/**
 * MAGNET UI Error Toast
 *
 * Non-blocking toast notifications for warnings and info messages.
 * Auto-dismisses after a configurable duration.
 */

import React, { useEffect, useState } from 'react';
import { errorHandler, UIError, ErrorSeverity } from '../../systems/UIErrorHandler';

// ============================================================================
// Types
// ============================================================================

interface ErrorToastProps {
  /** Maximum toasts to display */
  maxToasts?: number;
  /** Position on screen */
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  /** Maximum severity to show as toast (higher goes to overlay) */
  maxSeverity?: ErrorSeverity;
  /** Custom toast renderer */
  renderToast?: (error: UIError, onDismiss: () => void) => React.ReactNode;
}

interface ToastItemProps {
  error: UIError;
  onDismiss: () => void;
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

// ============================================================================
// ToastItem
// ============================================================================

const ToastItem: React.FC<ToastItemProps> = ({ error, onDismiss }) => {
  const [isExiting, setIsExiting] = useState(false);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(onDismiss, 200); // Match CSS animation
  };

  return (
    <div
      className={`error-toast__item error-toast__item--${error.severity} ${isExiting ? 'error-toast__item--exiting' : ''}`}
      role="alert"
    >
      <div className="error-toast__content">
        <span className={`error-toast__icon error-toast__icon--${error.severity}`} />
        <div className="error-toast__text">
          <p className="error-toast__message">{error.userMessage}</p>
          {error.suggestedAction && (
            <p className="error-toast__action">{error.suggestedAction}</p>
          )}
        </div>
        <button
          className="error-toast__close"
          onClick={handleDismiss}
          aria-label="Dismiss"
        >
          &times;
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// ErrorToast
// ============================================================================

export const ErrorToast: React.FC<ErrorToastProps> = ({
  maxToasts = 5,
  position = 'top-right',
  maxSeverity = 'warning',
  renderToast,
}) => {
  const [toasts, setToasts] = useState<UIError[]>([]);

  useEffect(() => {
    const updateToasts = () => {
      const activeErrors = errorHandler.getActiveErrors()
        .filter(e => SEVERITY_ORDER[e.severity] <= SEVERITY_ORDER[maxSeverity])
        .slice(0, maxToasts);
      setToasts(activeErrors);
    };

    updateToasts();

    const unsubscribe = errorHandler.subscribe(() => {
      updateToasts();
    });

    return () => {
      unsubscribe();
    };
  }, [maxToasts, maxSeverity]);

  const handleDismiss = (errorId: string) => {
    errorHandler.dismiss(errorId);
  };

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className={`error-toast error-toast--${position}`} aria-live="polite">
      {toasts.map(error => (
        renderToast ? (
          <React.Fragment key={error.id}>
            {renderToast(error, () => handleDismiss(error.id))}
          </React.Fragment>
        ) : (
          <ToastItem
            key={error.id}
            error={error}
            onDismiss={() => handleDismiss(error.id)}
          />
        )
      ))}
    </div>
  );
};

export default ErrorToast;
