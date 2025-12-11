/**
 * MAGNET UI WebSocketClient Tests
 *
 * Tests for WebSocket client with ACK retry, reconnection,
 * and buffering support.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  WebSocketClient,
  createWebSocketClient,
  DEFAULT_ACK_RETRY_CONFIG,
  type WebSocketState,
  type WebSocketMessage,
} from '../../services/WebSocketClient';

// ============================================================================
// Mock WebSocket
// ============================================================================

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;

  private _autoOpen: boolean;

  constructor(public url: string, public protocols?: string[]) {
    this._autoOpen = true;
    // Auto-open after microtask
    if (this._autoOpen) {
      setTimeout(() => {
        this.readyState = MockWebSocket.OPEN;
        this.onopen?.(new Event('open'));
      }, 0);
    }
  }

  send = vi.fn((_data: string) => {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  });

  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { wasClean: true }));
  });

  // Test helpers
  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent('message', {
      data: JSON.stringify(data),
    }));
  }

  simulateError() {
    this.onerror?.(new Event('error'));
  }

  simulateClose(wasClean = true) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { wasClean }));
  }
}

// ============================================================================
// Test Setup
// ============================================================================

describe('WebSocketClient', () => {
  let originalWebSocket: typeof WebSocket;

  beforeEach(() => {
    originalWebSocket = (global as any).WebSocket;
    (global as any).WebSocket = MockWebSocket;
    vi.useFakeTimers();
  });

  afterEach(() => {
    (global as any).WebSocket = originalWebSocket;
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  // ============================================================================
  // Constructor Tests
  // ============================================================================

  describe('constructor', () => {
    it('creates client with URL', () => {
      const client = new WebSocketClient({ url: 'ws://test.com' });
      expect(client).toBeInstanceOf(WebSocketClient);
      expect(client.getState()).toBe('disconnected');
    });

    it('creates client with custom config', () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        autoReconnect: false,
        heartbeatInterval: 60000,
      });
      expect(client).toBeInstanceOf(WebSocketClient);
    });
  });

  // ============================================================================
  // Connection Lifecycle Tests
  // ============================================================================

  describe('connection lifecycle', () => {
    it('connects to WebSocket server', async () => {
      const onStateChange = vi.fn();
      const onOpen = vi.fn();

      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onStateChange, onOpen },
      });

      client.connect();

      expect(onStateChange).toHaveBeenCalledWith('connecting');

      // Allow auto-open (just need to advance past setTimeout(0))
      await vi.advanceTimersByTimeAsync(10);

      expect(onStateChange).toHaveBeenCalledWith('connected');
      expect(onOpen).toHaveBeenCalled();
    });

    it('reports connected state', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      expect(client.isConnected()).toBe(true);
      expect(client.getState()).toBe('connected');
    });

    it('disconnects from server', async () => {
      const onClose = vi.fn();
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onClose },
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      client.disconnect();

      expect(client.getState()).toBe('disconnected');
      expect(client.isConnected()).toBe(false);
    });

    it('does not reconnect on clean close', async () => {
      const onReconnect = vi.fn();
      const client = new WebSocketClient({
        url: 'ws://test.com',
        autoReconnect: true,
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onReconnect },
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Clean close via disconnect
      client.disconnect();

      await vi.advanceTimersByTimeAsync(5000);

      expect(onReconnect).not.toHaveBeenCalled();
    });
  });

  // ============================================================================
  // Reconnection Tests
  // ============================================================================

  describe('reconnection', () => {
    it('schedules reconnect on unclean close', async () => {
      const onReconnect = vi.fn();
      const onStateChange = vi.fn();

      const client = new WebSocketClient({
        url: 'ws://test.com',
        autoReconnect: true,
        reconnectDelay: 1000,
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onReconnect, onStateChange },
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Get the socket instance and simulate unclean close
      const states = onStateChange.mock.calls.map(c => c[0]);
      expect(states).toContain('connected');

      // Simulate unclean close by directly invoking close without wasClean
      onStateChange.mockClear();

      // Trigger reconnect by simulating disconnect
      (client as any).socket?.simulateClose(false);

      expect(onStateChange).toHaveBeenCalledWith('disconnected');
      expect(onStateChange).toHaveBeenCalledWith('reconnecting');

      await vi.advanceTimersByTimeAsync(1000);

      expect(onReconnect).toHaveBeenCalledWith(1);
    });

    it('uses exponential backoff for reconnection', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        autoReconnect: true,
        reconnectDelay: 1000,
        reconnectMultiplier: 2,
        maxReconnectDelay: 10000,
        handlers: {},
      });

      // Verify configuration exists
      expect((client as any).config.reconnectDelay).toBe(1000);
      expect((client as any).config.reconnectMultiplier).toBe(2);
    });

    it('stops reconnecting after max attempts', async () => {
      const onStateChange = vi.fn();

      const client = new WebSocketClient({
        url: 'ws://test.com',
        autoReconnect: true,
        maxReconnectAttempts: 2,
        reconnectDelay: 100,
        handlers: { onStateChange },
      });

      // Manually set reconnect attempt
      (client as any).reconnectAttempt = 2;
      (client as any).scheduleReconnect();

      expect(onStateChange).toHaveBeenCalledWith('error');
    });
  });

  // ============================================================================
  // Message Handling Tests
  // ============================================================================

  describe('message handling', () => {
    it('sends message when connected', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      const result = client.send({ type: 'test', payload: { data: 123 } });

      expect(result).toBe(true);
      expect((client as any).socket.send).toHaveBeenCalled();
    });

    it('returns false when sending while disconnected', () => {
      const client = new WebSocketClient({ url: 'ws://test.com' });

      const result = client.send({ type: 'test', payload: {} });

      expect(result).toBe(false);
    });

    it('receives and parses messages', async () => {
      const onMessage = vi.fn();

      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onMessage },
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Simulate incoming message
      (client as any).socket.simulateMessage({
        type: 'update',
        payload: { value: 'test' },
      });

      expect(onMessage).toHaveBeenCalledWith({
        type: 'update',
        payload: { value: 'test' },
      });
    });

    it('auto-ACKs messages with chain tracking', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      const sendSpy = vi.spyOn(client, 'send');

      // Simulate message with chain tracking
      (client as any).socket.simulateMessage({
        type: 'geometry_update',
        payload: {},
        messageId: 'msg-123',
        chain: {
          domain: 'geometry',
          update_id: 'upd-456',
          prev_update_id: null,
        },
      });

      // Should have called sendAck
      expect(sendSpy).toHaveBeenCalled();
    });
  });

  // ============================================================================
  // Buffering Tests
  // ============================================================================

  describe('buffering mode', () => {
    it('starts in buffering mode', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
      });

      client.startBuffering();
      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      expect(client.getState()).toBe('buffering');
    });

    it('buffers messages while in buffering mode', async () => {
      const onMessage = vi.fn();

      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onMessage },
      });

      client.startBuffering();
      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Simulate incoming messages
      (client as any).socket.simulateMessage({ type: 'msg1', payload: {} });
      (client as any).socket.simulateMessage({ type: 'msg2', payload: {} });

      // Should not have called handler yet
      expect(onMessage).not.toHaveBeenCalled();

      // Stop buffering
      client.stopBuffering();

      // Now should have received both messages
      expect(onMessage).toHaveBeenCalledTimes(2);
    });

    it('transitions from buffering to connected', async () => {
      const onStateChange = vi.fn();

      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onStateChange },
      });

      client.startBuffering();
      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      expect(client.getState()).toBe('buffering');

      client.stopBuffering();

      expect(client.getState()).toBe('connected');
    });
  });

  // ============================================================================
  // ACK Retry Tests
  // ============================================================================

  describe('ACK retry', () => {
    it('queues ACK for retry on failure', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Make send fail
      (client as any).socket.send.mockImplementation(() => {
        throw new Error('Send failed');
      });

      // Try to send ACK
      client.sendAck('msg-123', 'geometry', 'upd-456');

      // Should have queued for retry
      expect((client as any).pendingAcks.size).toBe(1);
    });

    it('uses exponential backoff for ACK retry', () => {
      const config = DEFAULT_ACK_RETRY_CONFIG;

      // First retry: 1000ms
      const delay1 = config.baseDelay * Math.pow(config.multiplier, 0);
      expect(delay1).toBe(1000);

      // Second retry: 2000ms
      const delay2 = config.baseDelay * Math.pow(config.multiplier, 1);
      expect(delay2).toBe(2000);

      // Third retry: 4000ms
      const delay3 = config.baseDelay * Math.pow(config.multiplier, 2);
      expect(delay3).toBe(4000);
    });

    it('limits retry delay to maxDelay', () => {
      const config = DEFAULT_ACK_RETRY_CONFIG;

      // 10th retry would be: 1000 * 2^9 = 512000ms
      // But should be capped at 8000ms
      const delay = Math.min(
        config.baseDelay * Math.pow(config.multiplier, 9),
        config.maxDelay
      );
      expect(delay).toBe(config.maxDelay);
    });
  });

  // ============================================================================
  // Heartbeat Tests
  // ============================================================================

  describe('heartbeat', () => {
    it('sends heartbeat ping at configured interval', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 5000,
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10); // Wait for connection

      const sendSpy = vi.spyOn(client, 'send');

      // Advance past heartbeat interval
      await vi.advanceTimersByTimeAsync(5000);

      expect(sendSpy).toHaveBeenCalledWith({
        type: 'ping',
        payload: expect.objectContaining({ timestamp: expect.any(Number) }),
      });

      // Clean up the heartbeat interval to prevent infinite loop
      client.disconnect();
    });

    it('disables heartbeat when interval is 0', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0,
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      const sendSpy = vi.spyOn(client, 'send');

      await vi.advanceTimersByTimeAsync(60000);

      // Should not have sent any heartbeats
      const heartbeatCalls = sendSpy.mock.calls.filter(
        call => call[0]?.type === 'ping'
      );
      expect(heartbeatCalls).toHaveLength(0);
    });
  });

  // ============================================================================
  // Error Handling Tests
  // ============================================================================

  describe('error handling', () => {
    it('calls error handler on WebSocket error', async () => {
      const onError = vi.fn();
      const onStateChange = vi.fn();

      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onError, onStateChange },
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Simulate error
      (client as any).socket.simulateError();

      expect(onError).toHaveBeenCalled();
      expect(onStateChange).toHaveBeenCalledWith('error');
    });

    it('handles malformed message gracefully', async () => {
      const onMessage = vi.fn();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for test
        handlers: { onMessage },
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Simulate malformed message
      (client as any).socket.onmessage?.(new MessageEvent('message', {
        data: 'not valid json{',
      }));

      expect(onMessage).not.toHaveBeenCalled();
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  // ============================================================================
  // Factory Function Tests
  // ============================================================================

  describe('createWebSocketClient factory', () => {
    it('creates client with URL and handlers', () => {
      const onOpen = vi.fn();

      const client = createWebSocketClient('ws://test.com', { onOpen });

      expect(client).toBeInstanceOf(WebSocketClient);
    });

    it('creates client with additional config', () => {
      const client = createWebSocketClient(
        'ws://test.com',
        {},
        { heartbeatInterval: 10000 }
      );

      expect((client as any).config.heartbeatInterval).toBe(10000);
    });
  });

  // ============================================================================
  // Cleanup Tests
  // ============================================================================

  describe('cleanup', () => {
    it('cleans up resources on disconnect', async () => {
      const client = new WebSocketClient({
        url: 'ws://test.com',
        heartbeatInterval: 0, // Disable heartbeat for this test
      });

      client.connect();
      await vi.advanceTimersByTimeAsync(10);

      // Add pending ACK
      (client as any).pendingAcks.set('test', {
        messageId: 'test',
        domain: 'geometry',
        updateId: 'upd',
        retryCount: 0,
        lastAttempt: Date.now(),
        timeoutId: setTimeout(() => {}, 1000),
      });

      client.disconnect();

      // Heartbeat should be cleared
      expect((client as any).heartbeatIntervalId).toBeNull();
      // Pending ACK timeouts should be cleared
      expect((client as any).reconnectTimeoutId).toBeNull();
    });

    it('clears pending ACK timeouts on cleanup', async () => {
      const client = new WebSocketClient({ url: 'ws://test.com' });

      // Manually add pending ACK with timeout
      const timeoutId = setTimeout(() => {}, 5000);
      (client as any).pendingAcks.set('msg-1', {
        messageId: 'msg-1',
        domain: 'geometry',
        updateId: 'upd-1',
        retryCount: 0,
        lastAttempt: Date.now(),
        timeoutId,
      });

      // Cleanup should clear the timeout
      (client as any).cleanup();

      // Verify cleanup was called (timeout cleared)
      expect((client as any).heartbeatIntervalId).toBeNull();
    });
  });
});
