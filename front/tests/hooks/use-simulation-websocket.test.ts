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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useSimulationWebSocket } from '~/hooks/use-simulation-websocket';
import type { BackendPayload } from '~/types';

// Mock modules (must be before imports)
vi.mock('~/utils/simulation-error-utils', () => ({
  logFrameProcessingError: vi.fn(),
  logSimulationError: vi.fn(),
}));

vi.mock('~/api', () => ({
  default: {
    post: vi.fn().mockResolvedValue({}),
  },
}));

// Import the mocked api to access in tests
import api from '~/api';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  readyState: number = 0;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  close() {
    this.readyState = 3; // CLOSED
  }

  // Helper to simulate events
  simulateOpen() {
    this.readyState = 1; // OPEN
    if (this.onopen) this.onopen(new Event('open'));
  }

  simulateMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage(
        new MessageEvent('message', { data: JSON.stringify(data) })
      );
    }
  }

  simulateClose(code: number, reason: string) {
    if (this.onclose) {
      // Create a proper close event with accessible properties
      const event = Object.assign(new Event('close'), {
        code,
        reason,
        wasClean: code === 1000,
      }) as CloseEvent;
      this.onclose(event);
    }
  }

  simulateError() {
    if (this.onerror) this.onerror(new Event('error'));
  }
}

describe('useSimulationWebSocket', () => {
  let mockWebSocket: typeof MockWebSocket;

  beforeEach(() => {
    MockWebSocket.instances = [];
    mockWebSocket = MockWebSocket as unknown as typeof MockWebSocket;
    global.WebSocket = mockWebSocket as unknown as typeof WebSocket;
    vi.clearAllMocks();
    vi.mocked(api.post).mockResolvedValue({});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should not connect when disabled', () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: false,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it('should not connect when simId is null', () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    renderHook(() =>
      useSimulationWebSocket({
        simId: null,
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    expect(MockWebSocket.instances).toHaveLength(0);
  });

  it('should connect when enabled and simId is provided', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    expect(ws.url).toContain('test-sim');
  });

  it('should set status to connecting and then loading on connection', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    // Wait for connecting status (happens quickly after hook mounts)
    await waitFor(() => {
      expect(result.current.simulationStatus).toBe('connecting');
    });

    // Simulate WebSocket open
    MockWebSocket.instances[0].simulateOpen();

    await waitFor(() => {
      expect(result.current.simulationStatus).toBe('loading');
      expect(result.current.isConnected).toBe(true);
    });
  });

  it('should handle initial frame (seq === 0)', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    const initialPayload: BackendPayload = {
      simId: 'test-sim',
      resources: [],
      stations: [],
      tasks: [],
      clock: {
        simSecondsPassed: 0,
        simMinutesPassed: 0,
        realSecondsPassed: 0,
        realMinutesPassed: 0,
        startTime: 0,
      },
    };

    ws.simulateMessage({
      seq: 0,
      payload: initialPayload,
    });

    await waitFor(() => {
      expect(onInitialFrame).toHaveBeenCalledWith(initialPayload);
      expect(result.current.simulationStatus).toBe('ready');
    });
  });

  it('should handle frame updates (seq > 0)', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    // Send initial frame first
    ws.simulateMessage({
      seq: 0,
      payload: {
        resources: [],
        stations: [],
        tasks: [],
        clock: {
          simSecondsPassed: 0,
          simMinutesPassed: 0,
          realSecondsPassed: 0,
          realMinutesPassed: 0,
          startTime: 0,
        },
      },
    });

    await waitFor(() => {
      expect(result.current.simulationStatus).toBe('ready');
    });

    // Send frame update
    const updatePayload: BackendPayload = {
      simId: 'test-sim',
      tasks: [],
      stations: [],
      resources: [
        {
          id: 1,
          position: [0, 0],
          taskIds: [],
          inProgressTaskId: null,
        },
      ],
      clock: {
        simSecondsPassed: 1,
        simMinutesPassed: 0,
        realSecondsPassed: 1,
        realMinutesPassed: 0,
        startTime: 0,
      },
    };

    ws.simulateMessage({
      seq: 1,
      payload: updatePayload,
    });

    await waitFor(() => {
      expect(onFrameUpdate).toHaveBeenCalledWith(updatePayload);
      expect(result.current.simulationStatus).toBe('running');
    });
  });

  it('should handle status messages', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    ws.simulateMessage({
      type: 'status',
      message: 'Simulation started',
    });

    // Status messages should not trigger callbacks
    expect(onInitialFrame).not.toHaveBeenCalled();
    expect(onFrameUpdate).not.toHaveBeenCalled();
  });

  it('should handle error messages from server', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    ws.simulateMessage({
      type: 'error',
      message: 'Server error occurred',
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        'Simulation Error',
        'Server error occurred'
      );
      expect(result.current.simulationStatus).toBe('error');
    });
  });

  it('should handle authentication failure (code 1008)', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();
    ws.simulateClose(1008, 'Authentication failed');

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        'Authentication Failed',
        'WebSocket authentication failed. Please try logging in again.'
      );
      expect(result.current.simulationStatus).toBe('error');
      expect(result.current.isConnected).toBe(false);
    });
  });

  it('should handle WebSocket errors', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    ws.simulateError();

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        'Connection Error',
        'Failed to connect to simulation. Check authentication and try again.'
      );
      expect(result.current.simulationStatus).toBe('error');
    });
  });

  it('should cleanup WebSocket on unmount', async () => {
    const onInitialFrame = vi.fn();
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { unmount } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    const closeSpy = vi.spyOn(ws, 'close');

    unmount();

    expect(closeSpy).toHaveBeenCalled();
  });

  it('should handle initial frame processing errors', async () => {
    const onInitialFrame = vi.fn().mockImplementation(() => {
      throw new Error('Processing failed');
    });
    const onFrameUpdate = vi.fn();
    const onError = vi.fn();

    const { result } = renderHook(() =>
      useSimulationWebSocket({
        simId: 'test-sim',
        enabled: true,
        onInitialFrame,
        onFrameUpdate,
        onError,
      })
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    ws.simulateMessage({
      seq: 0,
      payload: { resources: [], stations: [], tasks: [] },
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(
        'Initialization Error',
        'Failed to initialize simulation. Please refresh and try again.'
      );
      expect(result.current.simulationStatus).toBe('error');
    });
  });

  it('should update callback refs without reconnecting', async () => {
    const onInitialFrame1 = vi.fn();
    const onFrameUpdate1 = vi.fn();
    const onError = vi.fn();

    const { rerender } = renderHook(
      ({ onInitialFrame, onFrameUpdate }) =>
        useSimulationWebSocket({
          simId: 'test-sim',
          enabled: true,
          onInitialFrame,
          onFrameUpdate,
          onError,
        }),
      {
        initialProps: {
          onInitialFrame: onInitialFrame1,
          onFrameUpdate: onFrameUpdate1,
        },
      }
    );

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const initialWsCount = MockWebSocket.instances.length;

    // Update callbacks
    const onInitialFrame2 = vi.fn();
    const onFrameUpdate2 = vi.fn();

    rerender({
      onInitialFrame: onInitialFrame2,
      onFrameUpdate: onFrameUpdate2,
    });

    // Should not create new WebSocket
    expect(MockWebSocket.instances).toHaveLength(initialWsCount);

    const ws = MockWebSocket.instances[0];
    ws.simulateOpen();

    // New callback should be used
    ws.simulateMessage({
      seq: 0,
      payload: { resources: [], stations: [], tasks: [] },
    });

    await waitFor(() => {
      expect(onInitialFrame2).toHaveBeenCalled();
      expect(onInitialFrame1).not.toHaveBeenCalled();
    });
  });
});
