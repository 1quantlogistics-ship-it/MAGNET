/**
 * MAGNET UI Services
 *
 * Public exports for API and WebSocket clients.
 */

// Base API Client
export {
  BaseAPIClient,
  apiClient,
  type HttpMethod,
  type RequestConfig,
  type APIResponse,
  type APIError,
  type RequestInterceptor,
  type ResponseInterceptor,
  type ErrorInterceptor,
  type APIClientConfig,
} from './BaseAPIClient';

// WebSocket Client
export {
  WebSocketClient,
  createWebSocketClient,
  DEFAULT_ACK_RETRY_CONFIG,
  type WebSocketState,
  type WebSocketMessage,
  type AckMessage,
  type WebSocketEventHandlers,
  type AckRetryConfig,
  type WebSocketClientConfig,
} from './WebSocketClient';
