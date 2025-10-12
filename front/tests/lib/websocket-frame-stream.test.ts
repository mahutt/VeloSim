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

import { expect, test, vi, beforeEach, afterEach, describe } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  connectToFrameStream,
  startSimulation,
  stopSimulation,
  listSimulations,
} from '~/lib/websocket-frame-stream';
import { useSimulationFrames, useSimulationLifecycle } from '~/hooks';
import type { SimulationFrame } from '~/types';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  sentMessages: string[] = [];

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 0);
  }

  send(data: string): void {
    this.sentMessages.push(data);
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED;
    const event = { code: 1000, reason: 'Normal closure' } as CloseEvent;
    this.onclose?.(event);
  }

  // Helper method to simulate receiving a message
  simulateMessage(data: unknown): void {
    const event = new MessageEvent('message', {
      data: JSON.stringify(data),
    });
    this.onmessage?.(event);
  }

  // Helper method to simulate error
  simulateError(): void {
    this.onerror?.(new Event('error'));
  }

  static reset(): void {
    MockWebSocket.instances = [];
  }
}

// Mock fetch
const mockFetch = vi.fn();

beforeEach(() => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  global.WebSocket = MockWebSocket as any;
  global.fetch = mockFetch;
  MockWebSocket.reset();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('connectToFrameStream', () => {
  test('creates WebSocket connection with correct URL', () => {
    const simId = 'test-sim-123';
    const ws = connectToFrameStream(simId);

    expect(ws.url).toBe(
      `ws://localhost:8000/api/v1/simulation/stream/${simId}`
    );
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  test('logs on successful connection', async () => {
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    const simId = 'test-sim-456';

    connectToFrameStream(simId);

    await vi.runAllTimersAsync();

    expect(consoleLog).toHaveBeenCalledWith(
      `Connected to simulation ${simId} frame stream`
    );

    consoleLog.mockRestore();
  });

  test('logs on WebSocket close', () => {
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    const simId = 'test-sim-789';

    const ws = connectToFrameStream(simId);
    ws.close();

    expect(consoleLog).toHaveBeenCalledWith(
      `WebSocket closed for sim ${simId}:`,
      1000,
      'Normal closure'
    );

    consoleLog.mockRestore();
  });

  test('logs on WebSocket error', () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    const ws = connectToFrameStream('test-sim');

    if (ws.onerror) {
      ws.onerror(new Event('error'));
    }

    expect(consoleError).toHaveBeenCalledWith(
      'WebSocket error:',
      expect.any(Event)
    );

    consoleError.mockRestore();
  });
});

describe('startSimulation', () => {
  test('successfully starts simulation and returns sim_id', async () => {
    const mockSimId = 'sim-abc-123';
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sim_id: mockSimId }),
    });

    const simId = await startSimulation();

    expect(simId).toBe(mockSimId);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/simulation/start',
      { method: 'POST' }
    );
  });

  test('throws error when API call fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    await expect(startSimulation()).rejects.toThrow(
      'Failed to start simulation'
    );
  });
});

describe('stopSimulation', () => {
  test('successfully stops simulation', async () => {
    const simId = 'sim-to-stop';
    mockFetch.mockResolvedValueOnce({
      ok: true,
    });

    await stopSimulation(simId);

    expect(mockFetch).toHaveBeenCalledWith(
      `http://localhost:8000/api/v1/simulation/stop/${simId}`,
      { method: 'POST' }
    );
  });

  test('throws error when stop fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    await expect(stopSimulation('nonexistent')).rejects.toThrow(
      'Failed to stop simulation'
    );
  });
});

describe('listSimulations', () => {
  test('successfully retrieves list of active simulations', async () => {
    const mockSimulations = ['sim-1', 'sim-2', 'sim-3'];
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ active_simulations: mockSimulations }),
    });

    const simulations = await listSimulations();

    expect(simulations).toEqual(mockSimulations);
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/api/v1/simulation/list'
    );
  });

  test('throws error when list fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    await expect(listSimulations()).rejects.toThrow(
      'Failed to list simulations'
    );
  });
});

describe('useSimulationFrames', () => {
  test('does not connect when simId is null', () => {
    const { result } = renderHook(() => useSimulationFrames(null));

    expect(result.current.connected).toBe(false);
    expect(result.current.frames).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(MockWebSocket.instances).toHaveLength(0);
  });

  test('connects to WebSocket when simId is provided', async () => {
    const simId = 'test-sim-connect';
    const { result } = renderHook(() => useSimulationFrames(simId));

    // Only advance timers enough for WebSocket connection, not the ping interval
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain(simId);
    expect(result.current.connected).toBe(true);
  });

  test('receives and stores frame updates', async () => {
    const simId = 'test-sim-frames';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    const frame1: SimulationFrame = {
      sim_id: simId,
      seq_numb: 0,
      payload: 'frame 0 data',
      timestamp: 1000,
    };

    const frame2: SimulationFrame = {
      sim_id: simId,
      seq_numb: 1,
      payload: 'frame 1 data',
      timestamp: 2000,
    };

    act(() => {
      MockWebSocket.instances[0].simulateMessage(frame1);
    });

    expect(result.current.frames).toHaveLength(1);
    expect(result.current.frames[0]).toEqual(frame1);

    act(() => {
      MockWebSocket.instances[0].simulateMessage(frame2);
    });

    expect(result.current.frames).toHaveLength(2);
    expect(result.current.frames[1]).toEqual(frame2);
  });

  test('handles connection_established message', async () => {
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    const simId = 'test-sim-established';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'connection_established',
        sim_id: simId,
        message: 'Connected to simulation frame stream',
      });
    });

    // Should not add to frames array
    expect(result.current.frames).toHaveLength(0);
    expect(consoleLog).toHaveBeenCalledWith(
      'Connection established:',
      'Connected to simulation frame stream'
    );

    consoleLog.mockRestore();
  });

  test('handles pong message', async () => {
    const simId = 'test-sim-pong';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    act(() => {
      MockWebSocket.instances[0].simulateMessage({ type: 'pong' });
    });

    // Should not add to frames array
    expect(result.current.frames).toHaveLength(0);
  });

  test('handles error messages from server', async () => {
    const simId = 'test-sim-error';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    const errorMessage = 'Simulation not found';

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        error: errorMessage,
        sim_id: simId,
      });
    });

    expect(result.current.error).toBe(errorMessage);
    expect(result.current.frames).toHaveLength(0);
  });

  test('handles WebSocket connection error', async () => {
    const simId = 'test-sim-ws-error';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    act(() => {
      MockWebSocket.instances[0].simulateError();
    });

    expect(result.current.error).toBe('WebSocket connection error');
    expect(result.current.connected).toBe(false);
  });

  test('handles invalid JSON in message', async () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    const simId = 'test-sim-invalid-json';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    act(() => {
      const event = new MessageEvent('message', { data: 'invalid json' });
      MockWebSocket.instances[0].onmessage?.(event);
    });

    expect(result.current.error).toBe('Failed to parse frame data');
    expect(consoleError).toHaveBeenCalled();

    consoleError.mockRestore();
  });

  test('clearFrames function empties frames array', async () => {
    const simId = 'test-sim-clear';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    const frame: SimulationFrame = {
      sim_id: simId,
      seq_numb: 0,
      payload: 'test data',
      timestamp: 1000,
    };

    act(() => {
      MockWebSocket.instances[0].simulateMessage(frame);
    });

    expect(result.current.frames).toHaveLength(1);

    act(() => {
      result.current.clearFrames();
    });

    expect(result.current.frames).toHaveLength(0);
  });

  test('disconnect function closes WebSocket', async () => {
    const simId = 'test-sim-disconnect';
    const { result } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(result.current.connected).toBe(true);

    act(() => {
      result.current.disconnect();
    });

    expect(MockWebSocket.instances[0].readyState).toBe(MockWebSocket.CLOSED);
  });

  test('sends ping messages at regular intervals', async () => {
    const simId = 'test-sim-ping';
    renderHook(() => useSimulationFrames(simId));

    // Wait for initial connection
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    const ws = MockWebSocket.instances[0];

    // Fast-forward 30 seconds
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(ws.sentMessages).toContain('ping');

    // Fast-forward another 30 seconds
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000);
    });

    expect(
      ws.sentMessages.filter((msg) => msg === 'ping').length
    ).toBeGreaterThanOrEqual(2);
  });

  test('cleans up WebSocket on unmount', async () => {
    const simId = 'test-sim-cleanup';
    const { unmount } = renderHook(() => useSimulationFrames(simId));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    const ws = MockWebSocket.instances[0];
    expect(ws.readyState).toBe(MockWebSocket.OPEN);

    unmount();

    expect(ws.readyState).toBe(MockWebSocket.CLOSED);
  });

  test('updates connection when simId changes', async () => {
    const simId1 = 'test-sim-1';
    const simId2 = 'test-sim-2';
    const { rerender } = renderHook(({ simId }) => useSimulationFrames(simId), {
      initialProps: { simId: simId1 },
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain(simId1);

    const firstWs = MockWebSocket.instances[0];

    await act(async () => {
      rerender({ simId: simId2 });
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(MockWebSocket.instances).toHaveLength(2);
    expect(firstWs.readyState).toBe(MockWebSocket.CLOSED);
    expect(MockWebSocket.instances[1].url).toContain(simId2);
  });
});

describe('useSimulationLifecycle', () => {
  test('initial state is not running', () => {
    const { result } = renderHook(() => useSimulationLifecycle());

    expect(result.current.isRunning).toBe(false);
    expect(result.current.simId).toBeNull();
    expect(result.current.error).toBeNull();
  });

  test('start creates new simulation', async () => {
    const mockSimId = 'new-sim-123';
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sim_id: mockSimId }),
    });

    const { result } = renderHook(() => useSimulationLifecycle());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.isRunning).toBe(true);
    expect(result.current.simId).toBe(mockSimId);
    expect(result.current.error).toBeNull();
  });

  test('start handles API error', async () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useSimulationLifecycle());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.simId).toBeNull();
    expect(result.current.error).toBe('Failed to start simulation');
    expect(consoleError).toHaveBeenCalled();

    consoleError.mockRestore();
  });

  test('stop ends running simulation', async () => {
    const mockSimId = 'sim-to-stop-123';
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ sim_id: mockSimId }),
      })
      .mockResolvedValueOnce({
        ok: true,
      });

    const { result } = renderHook(() => useSimulationLifecycle());

    // Start simulation
    await act(async () => {
      await result.current.start();
    });

    expect(result.current.isRunning).toBe(true);
    expect(result.current.simId).toBe(mockSimId);

    // Stop simulation
    await act(async () => {
      await result.current.stop();
    });

    expect(result.current.isRunning).toBe(false);
    expect(result.current.simId).toBeNull();
    expect(result.current.error).toBeNull();
  });

  test('stop does nothing when no simulation is running', async () => {
    const { result } = renderHook(() => useSimulationLifecycle());

    await act(async () => {
      await result.current.stop();
    });

    expect(mockFetch).not.toHaveBeenCalled();
    expect(result.current.isRunning).toBe(false);
  });

  test('stop handles API error', async () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    const mockSimId = 'sim-error-123';
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ sim_id: mockSimId }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

    const { result } = renderHook(() => useSimulationLifecycle());

    // Start simulation
    await act(async () => {
      await result.current.start();
    });

    // Stop simulation (should fail)
    await act(async () => {
      await result.current.stop();
    });

    expect(result.current.error).toBe('Failed to stop simulation');
    expect(consoleError).toHaveBeenCalled();

    consoleError.mockRestore();
  });

  test('clears error on successful start after failed start', async () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => {});
    const mockSimId = 'sim-success-123';

    // First call fails
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useSimulationLifecycle());

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.error).toBe('Failed to start simulation');

    // Second call succeeds
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ sim_id: mockSimId }),
    });

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.error).toBeNull();
    expect(result.current.isRunning).toBe(true);
    expect(result.current.simId).toBe(mockSimId);

    consoleError.mockRestore();
  });
});
