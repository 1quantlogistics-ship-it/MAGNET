/**
 * MAGNET UI Connection Banner
 *
 * Displays WebSocket connection status and reconnection progress.
 * Sticky banner that appears when connection is lost.
 */

import React, { useEffect, useState } from 'react';

// ============================================================================
// Types
// ============================================================================

type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'reconnecting';

interface ConnectionBannerProps {
  /** Current connection status */
  status: ConnectionStatus;
  /** Reconnection attempt number */
  reconnectAttempt?: number;
  /** Maximum reconnection attempts */
  maxReconnectAttempts?: number;
  /** Time until next reconnect (seconds) */
  reconnectIn?: number;
  /** Called when manual reconnect is clicked */
  onReconnect?: () => void;
  /** Called when banner is dismissed */
  onDismiss?: () => void;
  /** Position of the banner */
  position?: 'top' | 'bottom';
}

// ============================================================================
// Constants
// ============================================================================

const STATUS_CONFIG: Record<ConnectionStatus, { icon: string; message: string; className: string }> = {
  connected: {
    icon: '✓',
    message: 'Connected',
    className: 'connection-banner--connected',
  },
  connecting: {
    icon: '⟳',
    message: 'Connecting...',
    className: 'connection-banner--connecting',
  },
  disconnected: {
    icon: '✕',
    message: 'Connection lost',
    className: 'connection-banner--disconnected',
  },
  reconnecting: {
    icon: '⟳',
    message: 'Reconnecting...',
    className: 'connection-banner--reconnecting',
  },
};

// ============================================================================
// ConnectionBanner
// ============================================================================

export const ConnectionBanner: React.FC<ConnectionBannerProps> = ({
  status,
  reconnectAttempt,
  maxReconnectAttempts = 5,
  reconnectIn,
  onReconnect,
  onDismiss,
  position = 'top',
}) => {
  const [isVisible, setIsVisible] = useState(false);

  // Show/hide based on status
  useEffect(() => {
    if (status === 'connected') {
      // Show briefly on reconnection, then hide
      setIsVisible(true);
      const timer = setTimeout(() => setIsVisible(false), 2000);
      return () => clearTimeout(timer);
    } else {
      setIsVisible(true);
    }
  }, [status]);

  if (!isVisible) {
    return null;
  }

  const config = STATUS_CONFIG[status];
  const showReconnectButton = status === 'disconnected' && onReconnect;
  const showProgress = status === 'reconnecting' && reconnectAttempt !== undefined;

  return (
    <div
      className={`connection-banner connection-banner--${position} ${config.className}`}
      role="status"
      aria-live="polite"
    >
      <span className="connection-banner__icon">{config.icon}</span>
      <span className="connection-banner__message">
        {config.message}
        {showProgress && (
          <span className="connection-banner__progress">
            {' '}(Attempt {reconnectAttempt}/{maxReconnectAttempts})
          </span>
        )}
        {reconnectIn !== undefined && reconnectIn > 0 && (
          <span className="connection-banner__countdown">
            {' '}Retrying in {reconnectIn}s
          </span>
        )}
      </span>
      <div className="connection-banner__actions">
        {showReconnectButton && (
          <button
            className="connection-banner__reconnect"
            onClick={onReconnect}
          >
            Reconnect Now
          </button>
        )}
        {status === 'connected' && onDismiss && (
          <button
            className="connection-banner__dismiss"
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

export default ConnectionBanner;
