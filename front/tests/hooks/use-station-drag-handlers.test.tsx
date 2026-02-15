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

import { beforeEach, describe, expect, test, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useStationDragHandlers } from '~/hooks/use-station-drag-handlers';
import { setupStationDragHandlers } from '~/lib/map-interactions';
import type { StationDragDropCallback } from '~/lib/map-interactions';

// ── Mocks ──────────────────────────────────────────────────────────────────

const mockMapRef = { current: { fake: 'map' } };
const mockStationsRef = {
  current: new Map<number, { name: string; taskIds: number[] }>(),
};
const mockDriversRef = { current: new Map<number, { id: number }>() };
const mockUpdateHoverState = vi.fn();
const mockSetHoverLocked = vi.fn();
const mockRequestAssignment = vi.fn();

vi.mock('~/providers/map-provider', () => ({
  useMap: () => ({
    mapRef: mockMapRef,
    mapLoaded: true,
  }),
}));

vi.mock('~/providers/simulation-provider', () => ({
  useSimulation: () => ({
    stationsRef: mockStationsRef,
    driversRef: mockDriversRef,
    updateHoverState: mockUpdateHoverState,
    setHoverLocked: mockSetHoverLocked,
  }),
}));

vi.mock('~/providers/task-assignment-provider', () => ({
  useTaskAssignment: () => ({
    requestAssignment: mockRequestAssignment,
  }),
}));

const mockCleanup = vi.fn();
vi.mock('~/lib/map-interactions', () => ({
  setupStationDragHandlers: vi.fn(() => mockCleanup),
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Re-import toast after mock so we can assert on it
import { toast } from 'sonner';

// ── Helpers ────────────────────────────────────────────────────────────────

/** Return the onDrop callback captured by the mock */
function capturedOnDrop(): StationDragDropCallback {
  const call = (setupStationDragHandlers as ReturnType<typeof vi.fn>).mock
    .calls[0];
  return call[1];
}

/** Return the onHighlight callback captured by the mock */
function capturedOnHighlight(): (stationId: number | null) => void {
  const call = (setupStationDragHandlers as ReturnType<typeof vi.fn>).mock
    .calls[0];
  return call[2];
}

// ── Tests ──────────────────────────────────────────────────────────────────

describe('useStationDragHandlers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStationsRef.current = new Map();
    mockDriversRef.current = new Map();
  });

  test('calls setupStationDragHandlers with the map and callbacks', () => {
    renderHook(() => useStationDragHandlers());

    expect(setupStationDragHandlers).toHaveBeenCalledWith(
      mockMapRef.current,
      expect.any(Function),
      expect.any(Function)
    );
  });

  test('cleanup is returned and called on unmount', () => {
    const { unmount } = renderHook(() => useStationDragHandlers());
    unmount();
    expect(mockCleanup).toHaveBeenCalled();
  });

  // ── onDrop callback (lines 47–67) ──────────────────────────────────────

  test('onDrop shows error toast when station is not found', () => {
    renderHook(() => useStationDragHandlers());
    const onDrop = capturedOnDrop();

    onDrop(999, 1);

    expect(toast.error).toHaveBeenCalledWith('Station #999 not found.');
    expect(mockRequestAssignment).not.toHaveBeenCalled();
  });

  test('onDrop shows error toast when driver is not found', () => {
    mockStationsRef.current.set(10, { name: 'Station A', taskIds: [1, 2] });

    renderHook(() => useStationDragHandlers());
    const onDrop = capturedOnDrop();

    onDrop(10, 888);

    expect(toast.error).toHaveBeenCalledWith('Driver #888 not found.');
    expect(mockRequestAssignment).not.toHaveBeenCalled();
  });

  test('onDrop shows info toast when station has no tasks', () => {
    mockStationsRef.current.set(10, { name: 'Station A', taskIds: [] });
    mockDriversRef.current.set(5, { id: 5 });

    renderHook(() => useStationDragHandlers());
    const onDrop = capturedOnDrop();

    onDrop(10, 5);

    expect(toast.info).toHaveBeenCalledWith('No tasks at Station A.');
    expect(mockRequestAssignment).not.toHaveBeenCalled();
  });

  test('onDrop calls requestAssignment with driverId and taskIds', () => {
    mockStationsRef.current.set(10, {
      name: 'Station A',
      taskIds: [101, 102, 103],
    });
    mockDriversRef.current.set(5, { id: 5 });

    renderHook(() => useStationDragHandlers());
    const onDrop = capturedOnDrop();

    onDrop(10, 5);

    expect(mockRequestAssignment).toHaveBeenCalledWith(5, [101, 102, 103]);
    expect(toast.error).not.toHaveBeenCalled();
    expect(toast.info).not.toHaveBeenCalled();
  });

  // ── onHighlight callback (lines 69–76) ─────────────────────────────────

  test('onHighlight with stationId sets hover then locks', () => {
    renderHook(() => useStationDragHandlers());
    const onHighlight = capturedOnHighlight();

    onHighlight(42);

    expect(mockUpdateHoverState).toHaveBeenCalledWith(42, null);
    expect(mockSetHoverLocked).toHaveBeenCalledWith(true);
    // hover is set before lock
    const hoverOrder = mockUpdateHoverState.mock.invocationCallOrder[0];
    const lockOrder = mockSetHoverLocked.mock.invocationCallOrder[0];
    expect(hoverOrder).toBeLessThan(lockOrder);
  });

  test('onHighlight with null unlocks then clears hover', () => {
    renderHook(() => useStationDragHandlers());
    const onHighlight = capturedOnHighlight();

    onHighlight(null);

    expect(mockSetHoverLocked).toHaveBeenCalledWith(false);
    expect(mockUpdateHoverState).toHaveBeenCalledWith(null, null);
    // unlock before clear
    const unlockOrder = mockSetHoverLocked.mock.invocationCallOrder[0];
    const clearOrder = mockUpdateHoverState.mock.invocationCallOrder[0];
    expect(unlockOrder).toBeLessThan(clearOrder);
  });
});
