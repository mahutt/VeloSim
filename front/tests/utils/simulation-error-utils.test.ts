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

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  logSimulationError,
  logMissingEntityError,
} from '~/utils/simulation-error-utils';

describe('simulation-error-utils', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  describe('logSimulationError', () => {
    it('should log error with all details to console', () => {
      const error = new Error('Test error');
      const context = 'Test context';
      const additionalData = { entityId: 123, entityType: 'station' };

      logSimulationError(error, context, additionalData);

      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('Test error')
      );
      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('Test context')
      );
      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('"entityId": 123')
      );
    });

    it('should handle string errors', () => {
      logSimulationError('String error', 'Context');

      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('String error')
      );
      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('Context')
      );
    });
  });

  describe('logMissingEntityError', () => {
    it('should log structured data for missing station', () => {
      logMissingEntityError('station', 123);

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.message).toBe('station with ID 123 not found in state');
      expect(loggedData.context).toBe('Missing station data');
      expect(loggedData.entityType).toBe('station');
      expect(loggedData.entityId).toBe(123);
      expect(loggedData.errorType).toBe('MISSING_ENTITY_DATA');
    });

    it('should log structured data for missing resource', () => {
      logMissingEntityError('resource', 456);

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.message).toBe(
        'resource with ID 456 not found in state'
      );
      expect(loggedData.context).toBe('Missing resource data');
      expect(loggedData.entityType).toBe('resource');
      expect(loggedData.entityId).toBe(456);
      expect(loggedData.errorType).toBe('MISSING_ENTITY_DATA');
    });

    it('should log valid JSON for monitoring systems', () => {
      logMissingEntityError('station', 123);

      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.any(String)
      );

      // Verify the logged data is valid JSON
      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      expect(() => JSON.parse(call)).not.toThrow();
    });
  });
});
