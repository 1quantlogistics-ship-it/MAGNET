/**
 * MAGNET UI Base API Client
 *
 * Foundation HTTP client for all API interactions.
 * Provides auth handling, error formatting, and request/response interceptors.
 */

import type { DomainHashes } from '../types/domainHashes';

// ============================================================================
// Types
// ============================================================================

/**
 * HTTP methods supported
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/**
 * Request configuration
 */
export interface RequestConfig {
  /** Request headers */
  headers?: Record<string, string>;
  /** Query parameters */
  params?: Record<string, string | number | boolean>;
  /** Request timeout in ms */
  timeout?: number;
  /** Whether to include credentials */
  withCredentials?: boolean;
  /** Abort signal for cancellation */
  signal?: AbortSignal;
}

/**
 * API response wrapper
 */
export interface APIResponse<T> {
  /** Response data */
  data: T;
  /** HTTP status code */
  status: number;
  /** Response headers */
  headers: Record<string, string>;
  /** Domain hashes from response (if present) */
  domainHashes?: DomainHashes;
}

/**
 * API error
 */
export interface APIError {
  /** Error code */
  code: string;
  /** Human-readable message */
  message: string;
  /** HTTP status code */
  status: number;
  /** Additional error details */
  details?: Record<string, unknown>;
  /** Whether error is recoverable */
  recoverable: boolean;
}

/**
 * Request interceptor
 */
export type RequestInterceptor = (
  url: string,
  config: RequestConfig
) => RequestConfig | Promise<RequestConfig>;

/**
 * Response interceptor
 */
export type ResponseInterceptor = <T>(
  response: APIResponse<T>
) => APIResponse<T> | Promise<APIResponse<T>>;

/**
 * Error interceptor
 */
export type ErrorInterceptor = (
  error: APIError
) => APIError | Promise<APIError>;

// ============================================================================
// Configuration
// ============================================================================

/**
 * API client configuration
 */
export interface APIClientConfig {
  /** Base URL for all requests */
  baseUrl: string;
  /** Default timeout in ms */
  timeout: number;
  /** Default headers */
  defaultHeaders: Record<string, string>;
  /** Auth token getter */
  getAuthToken?: () => string | null;
  /** Request interceptors */
  requestInterceptors: RequestInterceptor[];
  /** Response interceptors */
  responseInterceptors: ResponseInterceptor[];
  /** Error interceptors */
  errorInterceptors: ErrorInterceptor[];
}

/**
 * Default configuration
 */
const DEFAULT_CONFIG: APIClientConfig = {
  baseUrl: '',
  timeout: 30000,
  defaultHeaders: {
    'Content-Type': 'application/json',
  },
  requestInterceptors: [],
  responseInterceptors: [],
  errorInterceptors: [],
};

// ============================================================================
// BaseAPIClient
// ============================================================================

/**
 * Base API client class
 *
 * Provides HTTP methods with automatic auth, error handling,
 * and domain hash extraction from responses.
 */
export class BaseAPIClient {
  private config: APIClientConfig;

  constructor(config: Partial<APIClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Set auth token getter
   */
  setAuthTokenGetter(getter: () => string | null): void {
    this.config.getAuthToken = getter;
  }

  /**
   * Add request interceptor
   */
  addRequestInterceptor(interceptor: RequestInterceptor): () => void {
    this.config.requestInterceptors.push(interceptor);
    return () => {
      const index = this.config.requestInterceptors.indexOf(interceptor);
      if (index > -1) this.config.requestInterceptors.splice(index, 1);
    };
  }

  /**
   * Add response interceptor
   */
  addResponseInterceptor(interceptor: ResponseInterceptor): () => void {
    this.config.responseInterceptors.push(interceptor);
    return () => {
      const index = this.config.responseInterceptors.indexOf(interceptor);
      if (index > -1) this.config.responseInterceptors.splice(index, 1);
    };
  }

  /**
   * Add error interceptor
   */
  addErrorInterceptor(interceptor: ErrorInterceptor): () => void {
    this.config.errorInterceptors.push(interceptor);
    return () => {
      const index = this.config.errorInterceptors.indexOf(interceptor);
      if (index > -1) this.config.errorInterceptors.splice(index, 1);
    };
  }

  /**
   * Build full URL with query params
   */
  private buildUrl(path: string, params?: Record<string, string | number | boolean>): string {
    const url = new URL(path, this.config.baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, String(value));
      });
    }
    return url.toString();
  }

  /**
   * Build request headers
   */
  private buildHeaders(config: RequestConfig): Record<string, string> {
    const headers: Record<string, string> = {
      ...this.config.defaultHeaders,
      ...config.headers,
    };

    // Add auth token if available
    const token = this.config.getAuthToken?.();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  /**
   * Extract domain hashes from response headers
   */
  private extractDomainHashes(headers: Headers): DomainHashes | undefined {
    const geometryHash = headers.get('X-Geometry-Hash');
    const arrangementHash = headers.get('X-Arrangement-Hash');
    const routingHash = headers.get('X-Routing-Hash');
    const phaseHash = headers.get('X-Phase-Hash');
    const contentHash = headers.get('X-Content-Hash');

    if (geometryHash || arrangementHash || routingHash || phaseHash) {
      return {
        geometryHash: geometryHash || '',
        arrangementHash: arrangementHash || '',
        routingHash: routingHash || '',
        phaseHash: phaseHash || '',
        contentHash: contentHash || undefined,
      };
    }

    return undefined;
  }

  /**
   * Parse API error from response
   */
  private async parseError(response: Response): Promise<APIError> {
    let errorData: Record<string, unknown> = {};

    try {
      errorData = await response.json();
    } catch {
      // Response body is not JSON
    }

    return {
      code: (errorData.code as string) || `HTTP_${response.status}`,
      message: (errorData.message as string) || response.statusText,
      status: response.status,
      details: errorData.details as Record<string, unknown>,
      recoverable: response.status >= 500 || response.status === 429,
    };
  }

  /**
   * Execute HTTP request
   */
  async request<T>(
    method: HttpMethod,
    path: string,
    body?: unknown,
    config: RequestConfig = {}
  ): Promise<APIResponse<T>> {
    // Apply request interceptors
    let finalConfig = config;
    for (const interceptor of this.config.requestInterceptors) {
      finalConfig = await interceptor(path, finalConfig);
    }

    const url = this.buildUrl(path, finalConfig.params);
    const headers = this.buildHeaders(finalConfig);
    const timeout = finalConfig.timeout ?? this.config.timeout;

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        credentials: finalConfig.withCredentials ? 'include' : 'same-origin',
        signal: finalConfig.signal ?? controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        let error = await this.parseError(response);

        // Apply error interceptors
        for (const interceptor of this.config.errorInterceptors) {
          error = await interceptor(error);
        }

        throw error;
      }

      const data = await response.json() as T;
      const responseHeaders: Record<string, string> = {};
      response.headers.forEach((value, key) => {
        responseHeaders[key] = value;
      });

      let apiResponse: APIResponse<T> = {
        data,
        status: response.status,
        headers: responseHeaders,
        domainHashes: this.extractDomainHashes(response.headers),
      };

      // Apply response interceptors
      for (const interceptor of this.config.responseInterceptors) {
        apiResponse = await interceptor(apiResponse);
      }

      return apiResponse;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof DOMException && error.name === 'AbortError') {
        throw {
          code: 'REQUEST_TIMEOUT',
          message: `Request timed out after ${timeout}ms`,
          status: 0,
          recoverable: true,
        } as APIError;
      }

      throw error;
    }
  }

  // Convenience methods

  async get<T>(path: string, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>('GET', path, undefined, config);
  }

  async post<T>(path: string, body?: unknown, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>('POST', path, body, config);
  }

  async put<T>(path: string, body?: unknown, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>('PUT', path, body, config);
  }

  async patch<T>(path: string, body?: unknown, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>('PATCH', path, body, config);
  }

  async delete<T>(path: string, config?: RequestConfig): Promise<APIResponse<T>> {
    return this.request<T>('DELETE', path, undefined, config);
  }
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Default API client instance
 */
export const apiClient = new BaseAPIClient();
