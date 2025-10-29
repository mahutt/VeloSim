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

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import api from '../app/api';
import { TOKEN_STORAGE_KEY } from '../app/constants';

// Type workaround until this PR is merged: https://github.com/axios/axios/pull/5551
import type { AxiosRequestHeaders } from 'axios';
declare module 'axios' {
  export interface AxiosInterceptorManager<V> {
    handlers: Array<{
      fulfilled: (value: V) => V | Promise<V>;
      rejected: (error: unknown) => unknown;
    }>;
  }
}

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

    const config = await api.interceptors.request.handlers[0].fulfilled({
      headers: {} as AxiosRequestHeaders,
    });

    expect(config.headers.Authorization).toBe(`Bearer ${token}`);
  });

  it('should not add authorization header when token does not exist', async () => {
    const config = await api.interceptors.request.handlers[0].fulfilled({
      headers: {} as AxiosRequestHeaders,
    });

    expect(config.headers.Authorization).toBeUndefined();
  });

  it('should reject when interceptor encounters an error', async () => {
    const error = new Error('Test error');

    await expect(
      api.interceptors.request.handlers[0].rejected(error)
    ).rejects.toThrow('Test error');
  });
});
