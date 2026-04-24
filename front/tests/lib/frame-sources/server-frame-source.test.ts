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

// These unit tests were partially generated with the help of Claude Sonnet 4.5

/* eslint-disable @typescript-eslint/no-explicit-any */

import { makePayload, makePayloadClock } from 'tests/test-helpers';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import ServerFrameSource from '~/lib/frame-sources/server-frame-source';

// Mock the api module
const { mockApiPost } = vi.hoisted(() => {
  const mockApiPost = vi.fn().mockResolvedValue({});
  return { mockApiPost };
});

vi.mock('~/api', () => ({
  default: {
    post: mockApiPost,
  },
}));

// Mock the error utils
vi.mock('~/utils/simulation-error-utils', () => ({
  logFrameProcessingError: vi.fn(),
  logSimulationError: vi.fn(),
}));

describe('ServerFrameSource', () => {
  let frameSource: ServerFrameSource;
  let mockOnFrame: ReturnType<typeof vi.fn>;
  let mockOnError: ReturnType<typeof vi.fn>;
  let mockWebSocket: any;

  const createMockPayload = () =>
    makePayload({
      simId: 'test-sim',
      clock: makePayloadClock({
        startTime: 0,
        simSecondsPassed: 10,
        simMinutesPassed: 0.167,
        realSecondsPassed: 10,
        realMinutesPassed: 0.167,
      }),
    });

  beforeEach(() => {
    mockOnFrame = vi.fn();
    mockOnError = vi.fn();

    // Mock WebSocket with constants
    const MockWebSocket: any = vi.fn(function (this: any) {
      return mockWebSocket;
    });
    MockWebSocket.OPEN = 1;
    MockWebSocket.CLOSED = 3;
    MockWebSocket.CONNECTING = 0;
    MockWebSocket.CLOSING = 2;

    global.WebSocket = MockWebSocket;

    // Mock WebSocket instance
    mockWebSocket = {
      onopen: null,
      onmessage: null,
      onerror: null,
      onclose: null,
      readyState: MockWebSocket.OPEN,
      close: vi.fn(),
    };

    frameSource = new ServerFrameSource('test-sim', mockOnFrame, mockOnError);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('start', () => {
    it('should create WebSocket connection and handle initial frame', async () => {
      const startPromise = frameSource.start();

      expect(global.WebSocket).toHaveBeenCalled();

      // Simulate connection opened
      mockWebSocket.onopen();

      // Simulate initial frame
      const payload = createMockPayload();
      mockWebSocket.onmessage({
        data: JSON.stringify({ seq: 0, payload }),
      });

      const result = await startPromise;
      expect(result).toBe(true);
      expect(mockOnFrame).toHaveBeenCalledWith(payload);
    });

    it('should handle status messages', () => {
      frameSource.start();

      mockWebSocket.onmessage({
        data: JSON.stringify({ type: 'status', message: 'Running' }),
      });

      expect(mockOnFrame).not.toHaveBeenCalled();
    });

    it('should handle error messages', async () => {
      const startPromise = frameSource.start();

      mockWebSocket.onmessage({
        data: JSON.stringify({ type: 'error', message: 'Test error' }),
      });

      await expect(startPromise).rejects.toThrow('Test error');
      expect(mockOnError).toHaveBeenCalledWith('Test error');
    });

    it('should handle error messages without message field', async () => {
      const startPromise = frameSource.start();

      mockWebSocket.onmessage({
        data: JSON.stringify({ type: 'error' }),
      });

      await expect(startPromise).rejects.toThrow('Simulation error');
      expect(mockOnError).toHaveBeenCalledWith('An error occurred');
    });

    it('should handle regular frames', () => {
      frameSource.start();

      const payload = createMockPayload();
      mockWebSocket.onmessage({
        data: JSON.stringify({ seq: 5, payload }),
      });

      expect(mockOnFrame).toHaveBeenCalledWith(payload);
    });

    it('should handle parse errors', () => {
      frameSource.start();

      mockWebSocket.onmessage({
        data: 'invalid json',
      });

      expect(mockOnError).toHaveBeenCalledWith(
        'Simulation Frame Error: An error occurred while processing simulation data. The simulation may not display correctly.'
      );
    });

    it('should handle websocket errors', () => {
      frameSource.start();

      mockWebSocket.onerror(new Error('Connection failed'));

      expect(mockOnError).toHaveBeenCalledWith(
        'Connection Error: Failed to connect to simulation. Check authentication and try again.'
      );
    });

    it('should handle normal websocket close', () => {
      frameSource.start();

      mockWebSocket.onclose({ code: 1000, reason: 'Normal', wasClean: true });

      expect(mockApiPost).toHaveBeenCalledWith(
        '/simulation/test-sim/playbackSpeed',
        { playback_speed: 0 }
      );
    });

    it('should handle auth failure close (code 1008)', () => {
      frameSource.start();

      mockWebSocket.onclose({
        code: 1008,
        reason: 'Auth failed',
        wasClean: false,
      });

      expect(mockOnError).toHaveBeenCalledWith(
        'Authentication Failed: WebSocket authentication failed. Please try logging in again.'
      );
    });

    it('should handle unknown message types', () => {
      frameSource.start();

      mockWebSocket.onmessage({
        data: JSON.stringify({ type: 'unknown', data: 'test' }),
      });

      // Should not throw and not call onFrame
      expect(mockOnFrame).not.toHaveBeenCalled();
    });
  });

  describe('stop', () => {
    it('should close WebSocket if open', () => {
      frameSource.start();
      mockWebSocket.readyState = 1; // OPEN

      frameSource.stop();

      expect(mockWebSocket.close).toHaveBeenCalled();
    });

    it('should not close WebSocket if not open', () => {
      frameSource.start();
      mockWebSocket.readyState = 3; // CLOSED

      frameSource.stop();

      expect(mockWebSocket.close).not.toHaveBeenCalled();
    });
  });

  describe('setSpeed', () => {
    it('should call api with new speed', async () => {
      await frameSource.setSpeed(2);

      expect(mockApiPost).toHaveBeenCalledWith(
        '/simulation/test-sim/playbackSpeed',
        { playback_speed: 2 }
      );
    });

    it('should not call api if speed is the same', async () => {
      await frameSource.setSpeed(1);
      vi.clearAllMocks();

      await frameSource.setSpeed(1);

      expect(mockApiPost).not.toHaveBeenCalled();
    });
  });
});
