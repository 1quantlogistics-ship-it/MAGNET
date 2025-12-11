/**
 * MAGNET UI Error Display
 *
 * Visual component for rendering error states.
 * VisionOS-styled glass card with error information.
 */

import React from 'react';

/**
 * Error display props
 */
interface ErrorDisplayProps {
  /** The error to display */
  error: Error;
  /** Component name where error occurred */
  componentName?: string;
  /** Retry handler (if recoverable) */
  onRetry?: () => void;
  /** Current retry count */
  retryCount?: number;
  /** Maximum retries allowed */
  maxRetries?: number;
  /** Custom className */
  className?: string;
  /** Compact mode (minimal info) */
  compact?: boolean;
}

/**
 * ErrorDisplay - VisionOS-styled error presentation
 */
export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  componentName,
  onRetry,
  retryCount = 0,
  maxRetries = 3,
  className = '',
  compact = false,
}) => {
  const canRetry = onRetry && retryCount < maxRetries;
  const isDevelopment = process.env.NODE_ENV === 'development';

  // Inline styles for glass effect (to be replaced with CSS modules in Phase 6)
  const containerStyle: React.CSSProperties = {
    background: 'rgba(255, 255, 255, 0.05)',
    backdropFilter: 'blur(24px)',
    WebkitBackdropFilter: 'blur(24px)',
    borderRadius: '20px',
    border: '1px solid rgba(255, 255, 255, 0.04)',
    padding: compact ? '16px' : '24px',
    maxWidth: '480px',
    margin: '0 auto',
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif',
    color: 'rgba(255, 255, 255, 0.9)',
  };

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: compact ? '12px' : '16px',
  };

  const iconStyle: React.CSSProperties = {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    background: 'rgba(255, 69, 58, 0.2)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '16px',
    flexShrink: 0,
  };

  const titleStyle: React.CSSProperties = {
    fontSize: '16px',
    fontWeight: 600,
    margin: 0,
    color: 'rgba(255, 255, 255, 0.95)',
  };

  const messageStyle: React.CSSProperties = {
    fontSize: '14px',
    lineHeight: 1.5,
    color: 'rgba(255, 255, 255, 0.7)',
    marginBottom: compact ? '12px' : '16px',
  };

  const detailsStyle: React.CSSProperties = {
    background: 'rgba(0, 0, 0, 0.2)',
    borderRadius: '12px',
    padding: '12px',
    marginBottom: '16px',
    fontSize: '12px',
    fontFamily: '"JetBrains Mono", "SF Mono", monospace',
    color: 'rgba(255, 255, 255, 0.6)',
    maxHeight: '120px',
    overflow: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  };

  const footerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: '12px',
    flexWrap: 'wrap',
  };

  const buttonStyle: React.CSSProperties = {
    background: canRetry ? 'rgba(0, 122, 255, 0.3)' : 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '12px',
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    color: canRetry ? 'rgba(10, 132, 255, 1)' : 'rgba(255, 255, 255, 0.5)',
    cursor: canRetry ? 'pointer' : 'not-allowed',
    transition: 'all 0.2s ease',
    fontFamily: 'inherit',
  };

  const retryInfoStyle: React.CSSProperties = {
    fontSize: '12px',
    color: 'rgba(255, 255, 255, 0.5)',
  };

  const componentTagStyle: React.CSSProperties = {
    fontSize: '11px',
    color: 'rgba(255, 255, 255, 0.4)',
    marginTop: '8px',
  };

  return (
    <div style={containerStyle} className={className} role="alert" aria-live="assertive">
      <div style={headerStyle}>
        <div style={iconStyle} aria-hidden="true">
          !
        </div>
        <h3 style={titleStyle}>
          {error.name === 'Error' ? 'Something went wrong' : error.name}
        </h3>
      </div>

      <p style={messageStyle}>{error.message || 'An unexpected error occurred.'}</p>

      {/* Show stack trace in development only */}
      {isDevelopment && error.stack && !compact && (
        <div style={detailsStyle}>
          <code>{error.stack}</code>
        </div>
      )}

      <div style={footerStyle}>
        {canRetry && (
          <button
            style={buttonStyle}
            onClick={onRetry}
            onMouseOver={(e) => {
              e.currentTarget.style.background = 'rgba(0, 122, 255, 0.4)';
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.background = 'rgba(0, 122, 255, 0.3)';
            }}
          >
            Try Again
          </button>
        )}

        {retryCount > 0 && (
          <span style={retryInfoStyle}>
            Attempt {retryCount} of {maxRetries}
          </span>
        )}

        {!canRetry && retryCount >= maxRetries && (
          <span style={retryInfoStyle}>
            Maximum retries reached. Please refresh the page.
          </span>
        )}
      </div>

      {componentName && (
        <p style={componentTagStyle}>Error in: {componentName}</p>
      )}
    </div>
  );
};

/**
 * Mini error indicator for inline errors
 */
export const ErrorIndicator: React.FC<{
  message?: string;
  onClick?: () => void;
}> = ({ message = 'Error', onClick }) => {
  const style: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    background: 'rgba(255, 69, 58, 0.15)',
    borderRadius: '8px',
    fontSize: '12px',
    color: 'rgba(255, 69, 58, 0.9)',
    cursor: onClick ? 'pointer' : 'default',
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif',
  };

  const dotStyle: React.CSSProperties = {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: 'rgba(255, 69, 58, 0.8)',
  };

  return (
    <span style={style} onClick={onClick} role={onClick ? 'button' : undefined}>
      <span style={dotStyle} />
      {message}
    </span>
  );
};

/**
 * Loading fallback for suspense boundaries
 */
export const LoadingFallback: React.FC<{
  message?: string;
}> = ({ message = 'Loading...' }) => {
  const style: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    color: 'rgba(255, 255, 255, 0.6)',
    fontSize: '14px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif',
  };

  return <div style={style}>{message}</div>;
};

export default ErrorDisplay;
