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
  logSimulationErrorWithContext,
  logFrameProcessingError,
  logStateSyncError,
  SimulationStateLayer,
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

    it('should not produce [object Event] when passed a DOM Event', () => {
      const event = new Event('error');
      logSimulationError(event, 'WebSocket error');

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.message).not.toBe('[object Event]');
      expect(loggedData.message).toBe('An unknown error occurred');
      expect(loggedData.rawErrorType).toBe('Event');
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

      expect(loggedData.message).toBe(
        'station with ID 123 not found in frontend state'
      );
      expect(loggedData.context).toBe(
        'State sync issue: station exists in mapbox but not in frontend'
      );
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
        'resource with ID 456 not found in frontend state'
      );
      expect(loggedData.context).toBe(
        'State sync issue: resource exists in mapbox but not in frontend'
      );
      expect(loggedData.entityType).toBe('resource');
      expect(loggedData.entityId).toBe(456);
      expect(loggedData.errorType).toBe('MISSING_ENTITY_DATA');
    });

    it('should log valid JSON for monitoring systems', () => {
      logMissingEntityError('station', 123);

      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringMatching(/.+/)
      );

      // Verify the logged data is valid JSON
      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      expect(() => JSON.parse(call)).not.toThrow();
    });
  });

  describe('logSimulationErrorWithContext', () => {
    it('should log error with context', () => {
      const error = new Error('Context test error');
      const context = 'WebSocket connection';
      const additionalData = { attempt: 1 };

      logSimulationErrorWithContext(error, context, additionalData);

      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('Context test error')
      );
      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('WebSocket connection')
      );
    });

    it('should handle errors without additional data', () => {
      const error = new Error('Simple error');
      logSimulationErrorWithContext(error, 'Simple context');

      expect(console.error).toHaveBeenCalledWith(
        '[SIMULATION_ERROR]',
        expect.stringContaining('Simple error')
      );
    });
  });

  describe('logFrameProcessingError', () => {
    it('should log frame processing error with frame number', () => {
      const error = new Error('Frame parse error');
      const frameNumber = 42;

      logFrameProcessingError(error, frameNumber);

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.message).toBe('Frame parse error');
      expect(loggedData.context).toBe('WebSocket frame processing');
      expect(loggedData.frameNumber).toBe(42);
      expect(loggedData.errorType).toBe('FRAME_PROCESSING_ERROR');
      expect(loggedData.stateLayer).toBe(SimulationStateLayer.Frontend);
    });

    it('should handle frame number -1 for unknown frames', () => {
      const error = new Error('Unknown frame error');
      logFrameProcessingError(error, -1);

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.frameNumber).toBe(-1);
    });

    it('should include error stack trace', () => {
      const error = new Error('Stack trace test');
      logFrameProcessingError(error, 10);

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.stack).toBeDefined();
    });
  });

  describe('logStateSyncError', () => {
    it('should log state sync error between server and frontend', () => {
      const error = new Error('State mismatch');
      logStateSyncError(
        error,
        SimulationStateLayer.Server,
        SimulationStateLayer.Frontend
      );

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.message).toBe('State mismatch');
      expect(loggedData.context).toBe('State sync between server and frontend');
      expect(loggedData.errorType).toBe('STATE_SYNC_ERROR');
      expect(loggedData.sourceLayer).toBe(SimulationStateLayer.Server);
      expect(loggedData.targetLayer).toBe(SimulationStateLayer.Frontend);
    });

    it('should log state sync error between frontend and mapbox', () => {
      const error = new Error('Mapbox sync failed');
      logStateSyncError(
        error,
        SimulationStateLayer.Frontend,
        SimulationStateLayer.Mapbox
      );

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.context).toBe('State sync between frontend and mapbox');
      expect(loggedData.sourceLayer).toBe(SimulationStateLayer.Frontend);
      expect(loggedData.targetLayer).toBe(SimulationStateLayer.Mapbox);
    });

    it('should handle string errors', () => {
      logStateSyncError(
        'String sync error',
        SimulationStateLayer.Server,
        SimulationStateLayer.Mapbox
      );

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.message).toBe('String sync error');
    });
  });

  describe('SimulationStateLayer enum', () => {
    it('should have correct layer values', () => {
      expect(SimulationStateLayer.Server).toBe('server');
      expect(SimulationStateLayer.Frontend).toBe('frontend');
      expect(SimulationStateLayer.Mapbox).toBe('mapbox');
    });
  });

  describe('Error logging integration', () => {
    it('should log errors in correct format for Grafana/Loki scraping', () => {
      const error = new Error('Integration test');
      logSimulationError(error, 'Integration context', {
        userId: 'user123',
        sessionId: 'session456',
      });

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      // Verify structure matches logging system expectations
      expect(loggedData).toHaveProperty('message');
      expect(loggedData).toHaveProperty('level');
      expect(loggedData).toHaveProperty('context');
      expect(loggedData).toHaveProperty('userId');
      expect(loggedData).toHaveProperty('sessionId');
    });

    it('should maintain error context through multiple layers', () => {
      // Simulate error flowing through layers
      const originalError = new Error('Original error');

      // Server layer
      logStateSyncError(
        originalError,
        SimulationStateLayer.Server,
        SimulationStateLayer.Frontend
      );

      expect(console.error).toHaveBeenCalled();

      vi.clearAllMocks();

      // Frontend layer
      logFrameProcessingError(originalError, 100);

      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('Edge cases', () => {
    it('should handle null/undefined errors gracefully', () => {
      logSimulationError(null as unknown as Error, 'Null error');
      expect(console.error).toHaveBeenCalled();

      vi.clearAllMocks();

      logSimulationError(undefined as unknown as Error, 'Undefined error');
      expect(console.error).toHaveBeenCalled();
    });

    it('should handle errors without stack traces', () => {
      const customError = { message: 'Custom error' };
      logSimulationError(customError as Error, 'Custom context');

      const mockConsoleError = console.error as unknown as ReturnType<
        typeof vi.fn
      >;
      const call = mockConsoleError.mock.calls[0][1] as string;
      const loggedData = JSON.parse(call);

      expect(loggedData.message).toBeDefined();
      expect(loggedData.stack).toBeUndefined();
    });

    it('should handle very large additional data objects', () => {
      const largeData = {
        payload: Array(100).fill({ id: 1, data: 'test' }),
        metadata: { timestamp: Date.now(), version: '1.0.0' },
      };

      expect(() => {
        logSimulationError(new Error('Large data'), 'Context', largeData);
      }).not.toThrow();
    });

    it('should handle circular references in additional data', () => {
      const circularData: Record<string, unknown> = { key: 'value' };
      circularData.self = circularData;

      // JSON.stringify will throw on circular references - this is expected behavior
      // The error will be caught by the logging system but not propagated
      const consoleSpy = vi.spyOn(console, 'error');

      logSimulationError(new Error('Circular'), 'Context', circularData);

      // Console.error should still be called even if JSON.stringify fails
      expect(consoleSpy).toHaveBeenCalled();
    });
  });
});
