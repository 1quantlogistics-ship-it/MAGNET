/**
 * MAGNET UI BaseAPIClient Tests
 *
 * Tests for the HTTP client with auth, error handling,
 * and domain hash extraction.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  BaseAPIClient,
  type RequestConfig,
  type APIResponse,
  type APIError,
} from '../../services/BaseAPIClient';

// ============================================================================
// Test Setup
// ============================================================================

describe('BaseAPIClient', () => {
  let client: BaseAPIClient;
  let mockFetch: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockFetch = vi.fn();
    global.fetch = mockFetch;
    client = new BaseAPIClient({
      baseUrl: 'https://api.example.com',
      timeout: 5000,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ============================================================================
  // Constructor Tests
  // ============================================================================

  describe('constructor', () => {
    it('creates client with default config', () => {
      const defaultClient = new BaseAPIClient();
      expect(defaultClient).toBeInstanceOf(BaseAPIClient);
    });

    it('creates client with custom config', () => {
      const customClient = new BaseAPIClient({
        baseUrl: 'https://custom.api.com',
        timeout: 10000,
        defaultHeaders: { 'X-Custom': 'header' },
      });
      expect(customClient).toBeInstanceOf(BaseAPIClient);
    });
  });

  // ============================================================================
  // Request Building Tests
  // ============================================================================

  describe('request building', () => {
    it('builds URL with base URL', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ data: 'test' }),
        headers: new Headers(),
      });

      await client.get('/api/test');

      expect(mockFetch).toHaveBeenCalledWith(
        'https://api.example.com/api/test',
        expect.any(Object)
      );
    });

    it('builds URL with query parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      await client.get('/api/search', {
        params: { q: 'test', page: 1, active: true },
      });

      const calledUrl = mockFetch.mock.calls[0][0];
      expect(calledUrl).toContain('q=test');
      expect(calledUrl).toContain('page=1');
      expect(calledUrl).toContain('active=true');
    });

    it('includes default headers', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      await client.get('/api/test');

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.headers['Content-Type']).toBe('application/json');
    });

    it('merges custom headers with defaults', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      await client.get('/api/test', {
        headers: { 'X-Custom': 'value' },
      });

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.headers['Content-Type']).toBe('application/json');
      expect(calledOptions.headers['X-Custom']).toBe('value');
    });
  });

  // ============================================================================
  // Auth Token Tests
  // ============================================================================

  describe('auth token handling', () => {
    it('adds auth token when getter is set', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      client.setAuthTokenGetter(() => 'test-token-123');
      await client.get('/api/protected');

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.headers['Authorization']).toBe('Bearer test-token-123');
    });

    it('does not add auth header when token is null', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      client.setAuthTokenGetter(() => null);
      await client.get('/api/public');

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.headers['Authorization']).toBeUndefined();
    });
  });

  // ============================================================================
  // HTTP Method Tests
  // ============================================================================

  describe('HTTP methods', () => {
    beforeEach(() => {
      mockFetch.mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ success: true }),
        headers: new Headers(),
      });
    });

    it('executes GET request', async () => {
      await client.get('/api/resource');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: 'GET' })
      );
    });

    it('executes POST request with body', async () => {
      await client.post('/api/resource', { name: 'test' });

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.method).toBe('POST');
      expect(calledOptions.body).toBe(JSON.stringify({ name: 'test' }));
    });

    it('executes PUT request with body', async () => {
      await client.put('/api/resource/1', { name: 'updated' });

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.method).toBe('PUT');
      expect(calledOptions.body).toBe(JSON.stringify({ name: 'updated' }));
    });

    it('executes PATCH request with body', async () => {
      await client.patch('/api/resource/1', { status: 'active' });

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.method).toBe('PATCH');
      expect(calledOptions.body).toBe(JSON.stringify({ status: 'active' }));
    });

    it('executes DELETE request', async () => {
      await client.delete('/api/resource/1');
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: 'DELETE' })
      );
    });
  });

  // ============================================================================
  // Response Handling Tests
  // ============================================================================

  describe('response handling', () => {
    it('returns response data with status and headers', async () => {
      const responseHeaders = new Headers({
        'Content-Type': 'application/json',
        'X-Request-Id': 'req-123',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 1, name: 'test' }),
        headers: responseHeaders,
      });

      const response = await client.get<{ id: number; name: string }>('/api/item');

      expect(response.data).toEqual({ id: 1, name: 'test' });
      expect(response.status).toBe(200);
      expect(response.headers['content-type']).toBe('application/json');
    });
  });

  // ============================================================================
  // Domain Hash Extraction Tests
  // ============================================================================

  describe('domain hash extraction', () => {
    it('extracts domain hashes from response headers', async () => {
      const responseHeaders = new Headers({
        'X-Geometry-Hash': 'geo-abc123',
        'X-Arrangement-Hash': 'arr-def456',
        'X-Routing-Hash': 'rte-ghi789',
        'X-Phase-Hash': 'phs-jkl012',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: responseHeaders,
      });

      const response = await client.get('/api/design');

      expect(response.domainHashes).toBeDefined();
      expect(response.domainHashes?.geometryHash).toBe('geo-abc123');
      expect(response.domainHashes?.arrangementHash).toBe('arr-def456');
      expect(response.domainHashes?.routingHash).toBe('rte-ghi789');
      expect(response.domainHashes?.phaseHash).toBe('phs-jkl012');
    });

    it('extracts content hash when present', async () => {
      const responseHeaders = new Headers({
        'X-Geometry-Hash': 'geo-123',
        'X-Content-Hash': 'content-xyz',
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: responseHeaders,
      });

      const response = await client.get('/api/design');

      expect(response.domainHashes?.contentHash).toBe('content-xyz');
    });

    it('returns undefined when no domain hashes present', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      const response = await client.get('/api/simple');

      expect(response.domainHashes).toBeUndefined();
    });
  });

  // ============================================================================
  // Error Handling Tests
  // ============================================================================

  describe('error handling', () => {
    it('throws APIError on 4xx response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: async () => ({ code: 'NOT_FOUND', message: 'Resource not found' }),
      });

      await expect(client.get('/api/missing')).rejects.toMatchObject({
        code: 'NOT_FOUND',
        message: 'Resource not found',
        status: 404,
        recoverable: false,
      });
    });

    it('throws APIError on 5xx response (recoverable)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => ({ message: 'Server error' }),
      });

      await expect(client.get('/api/failing')).rejects.toMatchObject({
        status: 500,
        recoverable: true,
      });
    });

    it('marks 429 as recoverable', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        statusText: 'Too Many Requests',
        json: async () => ({ message: 'Rate limited' }),
      });

      await expect(client.get('/api/rate-limited')).rejects.toMatchObject({
        status: 429,
        recoverable: true,
      });
    });

    it('handles non-JSON error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: async () => { throw new Error('Not JSON'); },
      });

      await expect(client.get('/api/error')).rejects.toMatchObject({
        code: 'HTTP_500',
        status: 500,
      });
    });

    it('handles timeout errors', async () => {
      // Create client with very short timeout
      const shortTimeoutClient = new BaseAPIClient({
        baseUrl: 'https://api.example.com',
        timeout: 50, // 50ms timeout
      });

      // Make fetch reject with abort error (simulating timeout)
      mockFetch.mockRejectedValueOnce(new DOMException('Aborted', 'AbortError'));

      await expect(shortTimeoutClient.get('/api/slow')).rejects.toMatchObject({
        code: 'REQUEST_TIMEOUT',
        recoverable: true,
      });
    });
  });

  // ============================================================================
  // Interceptor Tests
  // ============================================================================

  describe('interceptors', () => {
    describe('request interceptors', () => {
      it('applies request interceptor', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({}),
          headers: new Headers(),
        });

        const interceptor = vi.fn((url, config) => ({
          ...config,
          headers: { ...config.headers, 'X-Intercepted': 'true' },
        }));

        const unsubscribe = client.addRequestInterceptor(interceptor);

        await client.get('/api/test');

        expect(interceptor).toHaveBeenCalled();
        const calledOptions = mockFetch.mock.calls[0][1];
        expect(calledOptions.headers['X-Intercepted']).toBe('true');

        unsubscribe();
      });

      it('removes request interceptor on unsubscribe', async () => {
        mockFetch.mockResolvedValue({
          ok: true,
          status: 200,
          json: async () => ({}),
          headers: new Headers(),
        });

        const interceptor = vi.fn((url, config) => config);
        const unsubscribe = client.addRequestInterceptor(interceptor);

        await client.get('/api/test');
        expect(interceptor).toHaveBeenCalledTimes(1);

        unsubscribe();

        await client.get('/api/test');
        expect(interceptor).toHaveBeenCalledTimes(1); // Not called again
      });
    });

    describe('response interceptors', () => {
      it('applies response interceptor', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: async () => ({ value: 1 }),
          headers: new Headers(),
        });

        const interceptor = vi.fn((response) => ({
          ...response,
          data: { ...response.data, intercepted: true },
        }));

        client.addResponseInterceptor(interceptor);

        const response = await client.get('/api/test');

        expect(interceptor).toHaveBeenCalled();
        expect(response.data).toHaveProperty('intercepted', true);
      });
    });

    describe('error interceptors', () => {
      it('applies error interceptor', async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          status: 400,
          statusText: 'Bad Request',
          json: async () => ({ message: 'Original error' }),
        });

        const interceptor = vi.fn((error) => ({
          ...error,
          message: 'Transformed error',
        }));

        client.addErrorInterceptor(interceptor);

        await expect(client.get('/api/error')).rejects.toMatchObject({
          message: 'Transformed error',
        });
      });
    });
  });

  // ============================================================================
  // Credentials Tests
  // ============================================================================

  describe('credentials handling', () => {
    it('uses same-origin credentials by default', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      await client.get('/api/test');

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.credentials).toBe('same-origin');
    });

    it('includes credentials when withCredentials is true', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      await client.get('/api/test', { withCredentials: true });

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.credentials).toBe('include');
    });
  });

  // ============================================================================
  // Abort Signal Tests
  // ============================================================================

  describe('abort signal', () => {
    it('uses provided abort signal', async () => {
      const controller = new AbortController();

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({}),
        headers: new Headers(),
      });

      await client.get('/api/test', { signal: controller.signal });

      const calledOptions = mockFetch.mock.calls[0][1];
      expect(calledOptions.signal).toBe(controller.signal);
    });
  });
});
