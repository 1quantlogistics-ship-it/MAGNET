/**
 * useGeometryEvents.ts - WebSocket event subscription hook v1.1
 * BRAVO OWNS THIS FILE.
 *
 * Module 58: WebGL 3D Visualization
 * Subscribes to real-time geometry updates via WebSocket.
 * Addresses: FM7 (Streaming protocol)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  WebSocketMessage,
  GeometryUpdateMessage,
  GeometryFailedMessage,
  GeometryInvalidatedMessage,
} from '../types/schema';
import {
  isGeometryUpdateMessage,
  isGeometryFailedMessage,
  isGeometryInvalidatedMessage,
} from '../types/schema';

// =============================================================================
// TYPES
// =============================================================================

export interface UseGeometryEventsOptions {
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onGeometryUpdate?: (message: GeometryUpdateMessage) => void;
  onGeometryFailed?: (message: GeometryFailedMessage) => void;
  onGeometryInvalidated?: () => void;
  onConnected?: () => void;
  onDisconnected?: () => void;
  wsUrl?: string;
}

export interface UseGeometryEventsResult {
  isConnected: boolean;
  lastEvent: WebSocketMessage | null;
  lastUpdateId: string | null;
  error: Error | null;
  connect: () => void;
  disconnect: () => void;
}

// =============================================================================
// HOOK
// =============================================================================

export function useGeometryEvents(
  designId: string,
  options: UseGeometryEventsOptions = {},
): UseGeometryEventsResult {
  const {
    autoReconnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 5,
    onGeometryUpdate,
    onGeometryFailed,
    onGeometryInvalidated,
    onConnected,
    onDisconnected,
    wsUrl,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WebSocketMessage | null>(null);
  const [lastUpdateId, setLastUpdateId] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const designIdRef = useRef(designId);

  // Update ref when designId changes
  designIdRef.current = designId;

  // Get WebSocket URL
  const getWsUrl = useCallback((): string => {
    if (wsUrl) return wsUrl;

    // Construct URL from current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/v1/designs/${designIdRef.current}/3d/stream`;
  }, [wsUrl]);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message = JSON.parse(event.data) as WebSocketMessage;
      setLastEvent(message);

      if (isGeometryUpdateMessage(message)) {
        setLastUpdateId(message.update_id);
        onGeometryUpdate?.(message);
      } else if (isGeometryFailedMessage(message)) {
        onGeometryFailed?.(message);
      } else if (isGeometryInvalidatedMessage(message)) {
        onGeometryInvalidated?.();
      }
    } catch (err) {
      console.error('Failed to parse WebSocket message:', err);
    }
  }, [onGeometryUpdate, onGeometryFailed, onGeometryInvalidated]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    const url = getWsUrl();
    console.log(`Connecting to geometry stream: ${url}`);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Geometry stream connected');
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        onConnected?.();

        // Subscribe to design
        ws.send(JSON.stringify({
          message_type: 'subscribe',
          design_id: designIdRef.current,
        }));
      };

      ws.onmessage = handleMessage;

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError(new Error('WebSocket connection error'));
      };

      ws.onclose = (event) => {
        console.log('Geometry stream disconnected:', event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        onDisconnected?.();

        // Auto-reconnect if enabled
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++;
          console.log(`Reconnecting in ${reconnectInterval}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      setError(err instanceof Error ? err : new Error('Failed to connect'));
    }
  }, [getWsUrl, handleMessage, autoReconnect, reconnectInterval, maxReconnectAttempts, onConnected, onDisconnected]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    // Clear reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      // Unsubscribe first
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          message_type: 'unsubscribe',
          design_id: designIdRef.current,
        }));
      }

      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    reconnectAttemptsRef.current = 0;
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  // Reconnect when design ID changes
  useEffect(() => {
    if (isConnected && wsRef.current) {
      // Unsubscribe from old design
      wsRef.current.send(JSON.stringify({
        message_type: 'unsubscribe',
        design_id: designIdRef.current,
      }));

      // Subscribe to new design
      wsRef.current.send(JSON.stringify({
        message_type: 'subscribe',
        design_id: designId,
      }));
    }

    designIdRef.current = designId;
    setLastUpdateId(null);
  }, [designId, isConnected]);

  return {
    isConnected,
    lastEvent,
    lastUpdateId,
    error,
    connect,
    disconnect,
  };
}

// =============================================================================
// SIMPLE EVENT HOOK
// =============================================================================

/**
 * Simplified hook that just triggers refresh on invalidation.
 */
export function useGeometryRefresh(
  designId: string,
  onRefreshNeeded: () => void,
): boolean {
  const { isConnected } = useGeometryEvents(designId, {
    onGeometryInvalidated: onRefreshNeeded,
  });

  return isConnected;
}

export default useGeometryEvents;
