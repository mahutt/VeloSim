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

import { beforeEach, describe, expect, test, vi, type Mock } from 'vitest';
import type { Map as MapboxGLMap } from 'mapbox-gl';
import MapManager from '~/lib/map-manager';
import { mockSimulationStateManager } from 'tests/mocks';
import type SimulationStateManager from '~/lib/simulation-state-manager';
import { makeDriver, makePayload } from 'tests/test-helpers';
import type { Position, Route } from '~/types';

const raf = vi.fn();
vi.stubGlobal('requestAnimationFrame', raf);

const { MockSimulationStateManager } = await vi.hoisted(
  () => import('tests/mocks')
);
vi.mock('~/lib/simulation-state-manager', () => {
  return {
    default: MockSimulationStateManager,
  };
});

const {
  mockSetupMapClickHandlers,
  mockSetupMapDropHandlers,
  mockSetupMapHoverHandlers,
  mockSetupStationDragHandlers,
} = vi.hoisted(() => {
  return {
    mockSetupMapClickHandlers: vi.fn(),
    mockSetupMapDropHandlers: vi.fn(),
    mockSetupMapHoverHandlers: vi.fn(),
    mockSetupStationDragHandlers: vi.fn(),
  };
});
vi.mock('~/lib/map-interactions', () => {
  return {
    setupMapClickHandlers: mockSetupMapClickHandlers,
    setupMapDropHandlers: mockSetupMapDropHandlers,
    setupMapHoverHandlers: mockSetupMapHoverHandlers,
    setupStationDragHandlers: mockSetupStationDragHandlers,
  };
});

const { mockUpdateDriverPositions } = vi.hoisted(() => {
  return {
    mockUpdateDriverPositions: vi.fn(),
  };
});
vi.mock('~/lib/animation-helpers', () => {
  return {
    updateDriverPositions: mockUpdateDriverPositions,
  };
});

const mockMap = {
  isStyleLoaded: () => true,
  getSource: () => ({
    setData: vi.fn(),
  }),
} as unknown as MapboxGLMap;

function makeManager() {
  const selectItem = vi.fn();
  const clearSelection = vi.fn();
  const requestAssignment = vi.fn();
  const manager = new MapManager(
    mockMap,
    mockSimulationStateManager as SimulationStateManager,
    selectItem,
    clearSelection,
    requestAssignment
  );
  return { manager, selectItem, clearSelection, requestAssignment };
}

describe('MapManager', () => {
  let manager: MapManager;

  beforeEach(() => {
    ({ manager } = makeManager());
  });

  test('initializes map interactions on creation', () => {
    expect(mockSetupMapClickHandlers).toHaveBeenCalled();
    expect(mockSetupMapDropHandlers).toHaveBeenCalled();
    expect(mockSetupMapHoverHandlers).toHaveBeenCalled();
    expect(mockSetupStationDragHandlers).toHaveBeenCalled();
    expect(raf).toHaveBeenCalled();
  });

  test('processFrame sets current position on arrival of unknown driver', () => {
    const payload = makePayload({
      drivers: [makeDriver({ id: 1, position: [0, 0] })],
    });
    manager.processFrame(payload, true);
    const currentPositions = manager['currentPositions'] as Map<
      number,
      Position
    >;
    expect(currentPositions.get(1)).toEqual([0, 0]);
  });

  test('processFrame sets current position and clears start / target positions when animation is disabled', () => {
    manager.processFrame(
      makePayload({
        drivers: [makeDriver({ id: 1, position: [0, 0] })],
      }),
      true
    );
    manager.processFrame(
      makePayload({
        drivers: [makeDriver({ id: 1, position: [1, 1] })],
      }),
      true
    );
    manager.processFrame(
      makePayload({
        drivers: [makeDriver({ id: 1, position: [2, 2] })],
      }),
      false
    );
    const currentPositions = manager['currentPositions'] as Map<
      number,
      Position
    >;
    const frameStartPositions = manager['frameStartPositions'] as Map<
      number,
      Position
    >;
    const targetPositions = manager['targetPositions'] as Map<number, Position>;
    expect(currentPositions.get(1)).toEqual([2, 2]);
    expect(frameStartPositions.get(1)).toBeUndefined();
    expect(targetPositions.get(1)).toBeUndefined();
  });

  test('processFrame sets the route when provided', () => {
    manager.processFrame(
      makePayload({
        drivers: [
          makeDriver({
            id: 1,
            position: [0, 0],
            route: {
              coordinates: [
                [0, 0],
                [0.5, 0.5],
                [1, 1],
              ],
              nextStopIndex: 2,
              trafficRanges: [],
            },
          }),
        ],
      }),
      true
    );
    const routes = manager['routes'] as Map<number, Route>;
    expect(routes.get(1)).toBeDefined();
  });

  test('processFrame clears the route when omitted', () => {
    manager.processFrame(
      makePayload({
        drivers: [
          makeDriver({
            id: 1,
            position: [0, 0],
            route: {
              coordinates: [
                [0, 0],
                [0.5, 0.5],
                [1, 1],
              ],
              nextStopIndex: 2,
              trafficRanges: [],
            },
          }),
        ],
      }),
      true
    );
    manager.processFrame(
      makePayload({
        drivers: [
          makeDriver({
            id: 1,
            position: [0, 0],
            route: null,
          }),
        ],
      }),
      true
    );
    const routes = manager['routes'] as Map<number, Route>;
    expect(routes.get(1)).toBeUndefined();
  });

  test('animateResources schedules next frame', () => {
    raf.mockClear();
    mockUpdateDriverPositions.mockReturnValue(true);
    (mockSimulationStateManager.getMapShouldRefresh as Mock).mockReturnValue(
      true
    );
    manager['animateResources']();
    expect(raf).toHaveBeenCalled();
  });
});
