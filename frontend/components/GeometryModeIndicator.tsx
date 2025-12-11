/**
 * GeometryModeIndicator.tsx - Geometry mode indicator v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Shows authoritative vs visual-only mode (FM1)
 */

import React from 'react';
import type { GeometryMode } from '../types/schema';

// =============================================================================
// TYPES
// =============================================================================

export interface GeometryModeIndicatorProps {
  mode: GeometryMode;
  style?: React.CSSProperties;
  className?: string;
}

// =============================================================================
// COMPONENT
// =============================================================================

export default function GeometryModeIndicator({
  mode,
  style,
  className = '',
}: GeometryModeIndicatorProps) {
  const isAuthoritative = mode === 'authoritative';

  const containerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 10px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 500,
    background: isAuthoritative
      ? 'rgba(34, 197, 94, 0.2)'
      : 'rgba(251, 191, 36, 0.2)',
    color: isAuthoritative ? '#22c55e' : '#fbbf24',
    border: `1px solid ${isAuthoritative ? '#22c55e' : '#fbbf24'}`,
    ...style,
  };

  const dotStyle: React.CSSProperties = {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: isAuthoritative ? '#22c55e' : '#fbbf24',
  };

  return (
    <div className={`geometry-mode-indicator ${className}`} style={containerStyle}>
      <span style={dotStyle} />
      {isAuthoritative ? 'Authoritative Geometry' : 'Visual Approximation'}
      {!isAuthoritative && (
        <span
          title="This visualization may not match engineering calculations. Run hull_form phase for accurate geometry."
          style={{ cursor: 'help' }}
        >
          ⚠️
        </span>
      )}
    </div>
  );
}
