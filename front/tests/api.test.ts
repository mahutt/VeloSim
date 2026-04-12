/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import api from '../app/api';
import { TOKEN_STORAGE_KEY } from '../app/constants';
import type { AxiosRequestHeaders, InternalAxiosRequestConfig } from 'axios';

// Type for accessing internal interceptor handlers
type InterceptorHandler<V> = {
  fulfilled: (value: V) => V | Promise<V>;
  rejected: (error: unknown) => unknown;
};

type AxiosInterceptorManagerWithHandlers<V> = {
  handlers: InterceptorHandler<V>[];
};

describe('API Configuration', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('should create axios instance with correct base configuration', () => {
    expect(api.defaults.headers['Content-Type']).toBe('application/json');
  });

  it('should add authorization header when token exists', async () => {
    const token = 'test-token';
    sessionStorage.setItem(TOKEN_STORAGE_KEY, token);

    const interceptors = api.interceptors
      .request as unknown as AxiosInterceptorManagerWithHandlers<InternalAxiosRequestConfig>;
    const config = await interceptors.handlers[0]?.fulfilled({
      headers: {} as AxiosRequestHeaders,
    } as InternalAxiosRequestConfig);

    expect(config?.headers.Authorization).toBe(`Bearer ${token}`);
  });

  it('should not add authorization header when token does not exist', async () => {
    const interceptors = api.interceptors
      .request as unknown as AxiosInterceptorManagerWithHandlers<InternalAxiosRequestConfig>;
    const config = await interceptors.handlers[0]?.fulfilled({
      headers: {} as AxiosRequestHeaders,
    } as InternalAxiosRequestConfig);

    expect(config?.headers.Authorization).toBeUndefined();
  });

  it('should reject when interceptor encounters an error', async () => {
    const error = new Error('Test error');

    const interceptors = api.interceptors
      .request as unknown as AxiosInterceptorManagerWithHandlers<InternalAxiosRequestConfig>;
    await expect(interceptors.handlers[0]?.rejected(error)).rejects.toThrow(
      'Test error'
    );
  });

  it('should use backend URL from environment when provided', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_BACKEND_URL', 'http://localhost:8000');

    const { default: apiWithBackendUrl } = await import('../app/api');

    expect(apiWithBackendUrl.defaults.baseURL).toBe(
      'http://localhost:8000/api/v1'
    );

    vi.unstubAllEnvs();
  });
});
