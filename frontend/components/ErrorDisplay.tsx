/**
 * ErrorDisplay.tsx - Structured error display v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Displays geometry errors with recovery hints (FM5)
 */

import React from 'react';
import type { GeometryError } from '../types/schema';

// =============================================================================
// TYPES
// =============================================================================

export interface ErrorDisplayProps {
  error: GeometryError;
  onRetry?: () => void;
  onDismiss?: () => void;
  style?: React.CSSProperties;
  className?: string;
}

// =============================================================================
// SEVERITY COLORS
// =============================================================================

const SEVERITY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  error: {
    bg: 'rgba(239, 68, 68, 0.15)',
    border: '#ef4444',
    text: '#fca5a5',
  },
  warning: {
    bg: 'rgba(251, 191, 36, 0.15)',
    border: '#fbbf24',
    text: '#fde68a',
  },
  info: {
    bg: 'rgba(59, 130, 246, 0.15)',
    border: '#3b82f6',
    text: '#93c5fd',
  },
};

// =============================================================================
// COMPONENT
// =============================================================================

export default function ErrorDisplay({
  error,
  onRetry,
  onDismiss,
  style,
  className = '',
}: ErrorDisplayProps) {
  const colors = SEVERITY_COLORS[error.severity] || SEVERITY_COLORS.error;

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    padding: '16px',
    borderRadius: '8px',
    background: colors.bg,
    border: `1px solid ${colors.border}`,
    color: colors.text,
    fontFamily: 'system-ui, -apple-system, sans-serif',
    ...style,
  };

  const headerStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  };

  const titleStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontWeight: 600,
    fontSize: '14px',
  };

  const codeStyle: React.CSSProperties = {
    fontSize: '11px',
    padding: '2px 6px',
    borderRadius: '4px',
    background: 'rgba(0, 0, 0, 0.2)',
    fontFamily: 'monospace',
  };

  const messageStyle: React.CSSProperties = {
    fontSize: '13px',
    lineHeight: '1.5',
    color: '#e0e0e0',
  };

  const hintStyle: React.CSSProperties = {
    fontSize: '12px',
    padding: '8px 12px',
    borderRadius: '4px',
    background: 'rgba(0, 0, 0, 0.2)',
    borderLeft: `3px solid ${colors.border}`,
    color: '#a0a0a0',
  };

  const buttonContainerStyle: React.CSSProperties = {
    display: 'flex',
    gap: '8px',
    marginTop: '4px',
  };

  const buttonStyle: React.CSSProperties = {
    padding: '6px 12px',
    borderRadius: '4px',
    border: 'none',
    fontSize: '12px',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'background 0.2s',
  };

  const retryButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    background: colors.border,
    color: '#000',
  };

  const dismissButtonStyle: React.CSSProperties = {
    ...buttonStyle,
    background: 'transparent',
    color: colors.text,
    border: `1px solid ${colors.border}`,
  };

  const getIcon = () => {
    switch (error.severity) {
      case 'warning':
        return '⚠️';
      case 'info':
        return 'ℹ️';
      default:
        return '❌';
    }
  };

  return (
    <div className={`error-display ${className}`} style={containerStyle}>
      <div style={headerStyle}>
        <div style={titleStyle}>
          <span>{getIcon()}</span>
          <span>Geometry {error.severity === 'error' ? 'Error' : error.severity}</span>
          <span style={codeStyle}>{error.code}</span>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            style={{
              background: 'none',
              border: 'none',
              color: colors.text,
              cursor: 'pointer',
              fontSize: '18px',
              padding: '0',
              lineHeight: '1',
            }}
          >
            ×
          </button>
        )}
      </div>

      <div style={messageStyle}>{error.message}</div>

      {error.recovery_hint && (
        <div style={hintStyle}>
          <strong>Suggestion:</strong> {error.recovery_hint}
        </div>
      )}

      {Object.keys(error.details).length > 0 && (
        <details style={{ fontSize: '11px' }}>
          <summary style={{ cursor: 'pointer', color: '#808080' }}>
            Technical Details
          </summary>
          <pre
            style={{
              marginTop: '8px',
              padding: '8px',
              background: 'rgba(0, 0, 0, 0.3)',
              borderRadius: '4px',
              overflow: 'auto',
              fontSize: '10px',
            }}
          >
            {JSON.stringify(error.details, null, 2)}
          </pre>
        </details>
      )}

      {(onRetry || onDismiss) && (
        <div style={buttonContainerStyle}>
          {onRetry && (
            <button style={retryButtonStyle} onClick={onRetry}>
              Retry
            </button>
          )}
          {onDismiss && (
            <button style={dismissButtonStyle} onClick={onDismiss}>
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}
