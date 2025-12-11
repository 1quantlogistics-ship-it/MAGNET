/**
 * MAGNET UI Stale Content Notice
 *
 * Displays when domain hash or version mismatch indicates stale data.
 * Provides refresh action and auto-refresh countdown.
 */

import React, { useEffect, useState, useCallback } from 'react';
import type { Domain } from '../../types/domainHashes';

// ============================================================================
// Types
// ============================================================================

interface StaleContentNoticeProps {
  /** Which domain is stale */
  domain: Domain;
  /** Current hash in UI */
  currentHash?: string;
  /** Expected hash from backend */
  expectedHash?: string;
  /** Current version */
  currentVersion?: number;
  /** Expected version */
  expectedVersion?: number;
  /** Auto-refresh after seconds (0 = disabled) */
  autoRefreshSeconds?: number;
  /** Called when refresh is triggered */
  onRefresh: () => void;
  /** Called when notice is dismissed */
  onDismiss?: () => void;
  /** Custom message */
  message?: string;
}

// ============================================================================
// Constants
// ============================================================================

const DOMAIN_LABELS: Record<Domain, string> = {
  geometry: 'Hull & Structure',
  arrangement: 'Interior Layout',
  routing: 'Systems Routing',
  phase: 'Design Phase',
};

// ============================================================================
// StaleContentNotice
// ============================================================================

export const StaleContentNotice: React.FC<StaleContentNoticeProps> = ({
  domain,
  currentHash,
  expectedHash,
  currentVersion,
  expectedVersion,
  autoRefreshSeconds = 30,
  onRefresh,
  onDismiss,
  message,
}) => {
  const [countdown, setCountdown] = useState(autoRefreshSeconds);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    onRefresh();
  }, [onRefresh]);

  // Auto-refresh countdown
  useEffect(() => {
    if (autoRefreshSeconds <= 0 || isRefreshing) return;

    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          handleRefresh();
          return autoRefreshSeconds;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [autoRefreshSeconds, handleRefresh, isRefreshing]);

  const domainLabel = DOMAIN_LABELS[domain];
  const defaultMessage = `${domainLabel} data may be out of date. A newer version is available.`;

  return (
    <div className="stale-content-notice" role="alert">
      <div className="stale-content-notice__icon">⚠️</div>
      <div className="stale-content-notice__content">
        <p className="stale-content-notice__message">
          {message || defaultMessage}
        </p>
        {process.env.NODE_ENV === 'development' && (
          <div className="stale-content-notice__details">
            <span>Domain: {domain}</span>
            {currentVersion !== undefined && expectedVersion !== undefined && (
              <span>Version: {currentVersion} → {expectedVersion}</span>
            )}
          </div>
        )}
      </div>
      <div className="stale-content-notice__actions">
        <button
          className="stale-content-notice__refresh"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
        </button>
        {autoRefreshSeconds > 0 && !isRefreshing && (
          <span className="stale-content-notice__countdown">
            Auto-refresh in {countdown}s
          </span>
        )}
        {onDismiss && (
          <button
            className="stale-content-notice__dismiss"
            onClick={onDismiss}
            aria-label="Dismiss"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
};

export default StaleContentNotice;
