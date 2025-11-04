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

// These test cases were written with the help of Claude Sonnet 4.5

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { log, LogLevel } from '~/lib/logger';
import api from '~/api';
import { TOKEN_STORAGE_KEY } from '~/constants';

vi.mock('~/api');

describe('log', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not send log when user is not authenticated', async () => {
    const consoleWarnSpy = vi
      .spyOn(console, 'warn')
      .mockImplementation(() => {});

    await log({
      message: 'Test message',
      level: LogLevel.INFO,
    });

    expect(api.post).not.toHaveBeenCalled();
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      'Attempted to log without authentication.'
    );

    consoleWarnSpy.mockRestore();
  });

  it('sends log with auto-generated timestamp, userAgent, and url when user is authenticated', async () => {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, 'mock-token');
    vi.mocked(api.post).mockResolvedValueOnce({});

    const mockDate = new Date('2025-01-15T08:30:00Z');
    vi.setSystemTime(mockDate);

    await log({
      message: 'Test message',
      level: LogLevel.INFO,
    });

    expect(api.post).toHaveBeenCalledWith('/logs/frontend', {
      message: 'Test message',
      level: 'info',
      timestamp: '2025-01-15T08:30:00.000Z',
      userAgent: navigator.userAgent,
      url: window.location.href,
    });

    vi.useRealTimers();
  });

  it('logs error to console when API call fails', async () => {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, 'mock-token');
    const consoleErrorSpy = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});

    const mockError = new Error('Network error');
    vi.mocked(api.post).mockRejectedValueOnce(mockError);

    await log({
      message: 'Test message',
      level: LogLevel.INFO,
    });

    expect(consoleErrorSpy).toHaveBeenCalledWith(
      'Failed to send log to backend:',
      mockError
    );

    consoleErrorSpy.mockRestore();
  });
});
