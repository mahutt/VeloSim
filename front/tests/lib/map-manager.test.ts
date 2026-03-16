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

import {
  afterEach,
  beforeEach,
  describe,
  expect,
  test,
  vi,
  type Mock,
} from 'vitest';
import type { Map as MapboxGLMap } from 'mapbox-gl';
import MapManager from '~/lib/map-manager';
import { mockSimulationStateManager } from 'tests/mocks';
import type SimulationStateManager from '~/lib/simulation-state-manager';
import { makeDriver, makePayload, makeStation } from 'tests/test-helpers';
import type { Position, Route } from '~/types';
import { SelectedItemType } from '~/components/map/selected-item-bar';

const raf = vi.fn();
const caf = vi.fn();
vi.stubGlobal('requestAnimationFrame', raf);
vi.stubGlobal('cancelAnimationFrame', caf);

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
  mockSetupBoxSelectHandlers,
} = vi.hoisted(() => {
  return {
    mockSetupMapClickHandlers: vi.fn(),
    mockSetupMapDropHandlers: vi.fn(),
    mockSetupMapHoverHandlers: vi.fn(),
    mockSetupStationDragHandlers: vi.fn(),
    mockSetupBoxSelectHandlers: vi.fn(),
  };
});
vi.mock('~/lib/map-interactions', () => {
  return {
    setupMapClickHandlers: mockSetupMapClickHandlers,
    setupMapDropHandlers: mockSetupMapDropHandlers,
    setupMapHoverHandlers: mockSetupMapHoverHandlers,
    setupStationDragHandlers: mockSetupStationDragHandlers,
    setupBoxSelectHandlers: mockSetupBoxSelectHandlers,
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

const {
  mockSetMapSource,
  mockUpdateAllRoutesDisplay,
  mockClearAllRoutesDisplay,
  mockUpdateRouteDisplay,
  mockClearRouteDisplay,
  mockAdaptHeadquartersToGeoJSON,
  mockAdaptStationsToGeoJSON,
  mockAdaptResourcesToGeoJSON,
} = vi.hoisted(() => {
  return {
    mockSetMapSource: vi.fn(),
    mockUpdateAllRoutesDisplay: vi.fn(),
    mockClearAllRoutesDisplay: vi.fn(),
    mockUpdateRouteDisplay: vi.fn(),
    mockClearRouteDisplay: vi.fn(),
    mockAdaptHeadquartersToGeoJSON: vi.fn().mockReturnValue({}),
    mockAdaptStationsToGeoJSON: vi.fn().mockReturnValue({}),
    mockAdaptResourcesToGeoJSON: vi.fn().mockReturnValue({}),
  };
});
vi.mock('~/lib/map-helpers', () => {
  return {
    setMapSource: mockSetMapSource,
    MapSource: {
      Headquarters: 'headquarters',
      Stations: 'stations',
      Resources: 'resources',
    },
    MapLayer: {
      Stations: 'stations',
      StationCircle: 'station-circle',
      StationTaskCounts: 'station-task-counts',
    },
    updateAllRoutesDisplay: mockUpdateAllRoutesDisplay,
    clearAllRoutesDisplay: mockClearAllRoutesDisplay,
    updateRouteDisplay: mockUpdateRouteDisplay,
    clearRouteDisplay: mockClearRouteDisplay,
  };
});
vi.mock('~/lib/geojson-adapters', () => {
  return {
    adaptHeadquartersToGeoJSON: mockAdaptHeadquartersToGeoJSON,
    adaptStationsToGeoJSON: mockAdaptStationsToGeoJSON,
    adaptResourcesToGeoJSON: mockAdaptResourcesToGeoJSON,
  };
});

const mockToastError = vi.fn();
const mockToastInfo = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: unknown[]) => mockToastError(...args),
    info: (...args: unknown[]) => mockToastInfo(...args),
  },
}));

vi.mock('~/lib/logger', () => ({
  log: vi.fn(),
  LogLevel: { ERROR: 'error', INFO: 'info' },
}));

const mockMap = {
  isStyleLoaded: vi.fn(() => true),
  once: vi.fn(),
  getSource: () => ({
    setData: vi.fn(),
  }),
} as unknown as MapboxGLMap;

function makeManager() {
  const selectItem = vi.fn();
  const requestAssignment = vi.fn();
  const manager = new MapManager(
    mockMap,
    mockSimulationStateManager as SimulationStateManager,
    selectItem,
    requestAssignment
  );
  return { manager, selectItem, requestAssignment };
}

function getClickHandler() {
  return mockSetupMapClickHandlers.mock.calls[
    mockSetupMapClickHandlers.mock.calls.length - 1
  ][1];
}

function getHoverHandler() {
  return mockSetupMapHoverHandlers.mock.calls[
    mockSetupMapHoverHandlers.mock.calls.length - 1
  ][1];
}

function getBoxSelectHandler() {
  return mockSetupBoxSelectHandlers.mock.calls[
    mockSetupBoxSelectHandlers.mock.calls.length - 1
  ][2];
}

function getStationDragHandler() {
  return mockSetupStationDragHandlers.mock.calls[
    mockSetupStationDragHandlers.mock.calls.length - 1
  ][1];
}

function getStationDragHoverHandler() {
  return mockSetupStationDragHandlers.mock.calls[
    mockSetupStationDragHandlers.mock.calls.length - 1
  ][2];
}

function getStationDragIdsGetter() {
  return mockSetupStationDragHandlers.mock.calls[
    mockSetupStationDragHandlers.mock.calls.length - 1
  ][3];
}

describe('MapManager', () => {
  let manager: MapManager;
  let selectItem: ReturnType<typeof vi.fn>;
  let requestAssignment: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(null);
    (
      mockSimulationStateManager.getMultiSelectedStationIds as Mock
    ).mockReturnValue(new Set());
    (mockSimulationStateManager.getMapShouldRefresh as Mock).mockReturnValue(
      false
    );
    (mockSimulationStateManager.getShowAllRoutes as Mock).mockReturnValue(
      false
    );
    (mockSimulationStateManager.getAllDrivers as Mock).mockReturnValue([]);
    (mockSimulationStateManager.getAllStations as Mock).mockReturnValue([]);
    (mockSimulationStateManager.getHeadquarters as Mock).mockReturnValue(null);
    (mockSimulationStateManager.getNonZeroSpeed as Mock).mockReturnValue(1);
    (mockMap.isStyleLoaded as Mock).mockReturnValue(true);
    ({ manager, selectItem, requestAssignment } = makeManager());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('initializes map interactions on creation', () => {
    expect(mockSetupMapClickHandlers).toHaveBeenCalled();
    expect(mockSetupMapDropHandlers).toHaveBeenCalled();
    expect(mockSetupMapHoverHandlers).toHaveBeenCalled();
    expect(mockSetupStationDragHandlers).toHaveBeenCalled();
    expect(mockSetupBoxSelectHandlers).toHaveBeenCalled();
    expect(raf).toHaveBeenCalled();
  });

  // ── processFrame ──────────────────────────────────────────

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

  test('processFrame sets start/target when position changes', () => {
    manager.processFrame(
      makePayload({ drivers: [makeDriver({ id: 1, position: [0, 0] })] }),
      true
    );
    manager.processFrame(
      makePayload({ drivers: [makeDriver({ id: 1, position: [1, 1] })] }),
      true
    );
    const frameStartPositions = manager['frameStartPositions'] as Map<
      number,
      Position
    >;
    const targetPositions = manager['targetPositions'] as Map<number, Position>;
    expect(frameStartPositions.get(1)).toEqual([0, 0]);
    expect(targetPositions.get(1)).toEqual([1, 1]);
  });

  test('processFrame clears start/target when animation is disabled', () => {
    manager.processFrame(
      makePayload({ drivers: [makeDriver({ id: 1, position: [0, 0] })] }),
      true
    );
    manager.processFrame(
      makePayload({ drivers: [makeDriver({ id: 1, position: [1, 1] })] }),
      true
    );
    manager.processFrame(
      makePayload({ drivers: [makeDriver({ id: 1, position: [2, 2] })] }),
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

  test('processFrame stores route when provided', () => {
    manager.processFrame(
      makePayload({
        drivers: [
          makeDriver({
            id: 1,
            position: [0, 0],
            route: {
              coordinates: [
                [0, 0],
                [1, 1],
              ],
              nextStopIndex: 1,
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

  test('processFrame clears route when null', () => {
    manager.processFrame(
      makePayload({
        drivers: [
          makeDriver({
            id: 1,
            position: [0, 0],
            route: {
              coordinates: [
                [0, 0],
                [1, 1],
              ],
              nextStopIndex: 1,
              trafficRanges: [],
            },
          }),
        ],
      }),
      true
    );
    manager.processFrame(
      makePayload({
        drivers: [makeDriver({ id: 1, position: [0, 0], route: null })],
      }),
      true
    );
    const routes = manager['routes'] as Map<number, Route>;
    expect(routes.get(1)).toBeUndefined();
  });

  // ── click handler ─────────────────────────────────────────

  describe('click handler', () => {
    test('clicking empty space calls state.clearSelection', () => {
      const clickHandler = getClickHandler();
      clickHandler(null);

      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
    });

    test('regular click on station clears multi-selection and selects item', () => {
      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Station, id: 7 },
        { ctrlKey: false }
      );

      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
      expect(selectItem).toHaveBeenCalledWith(SelectedItemType.Station, 7);
    });

    test('regular click on driver clears multi-selection and selects item', () => {
      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Driver, id: 3 },
        { ctrlKey: false }
      );

      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
      expect(selectItem).toHaveBeenCalledWith(SelectedItemType.Driver, 3);
    });

    test('ctrl+click on driver does not trigger multi-selection (stations only)', () => {
      const clickHandler = getClickHandler();
      clickHandler({ type: SelectedItemType.Driver, id: 3 }, { ctrlKey: true });

      // Should fall through to regular click behavior
      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
      expect(selectItem).toHaveBeenCalledWith(SelectedItemType.Driver, 3);
    });

    test('ctrl+click promotes single-selected station into multi-selection', () => {
      const station = makeStation({ id: 5, name: 'Station 5' });
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        station
      );
      // First call: check if station 5 is already in set (no)
      // Second call: after toggle, check remaining size
      (mockSimulationStateManager.getMultiSelectedStationIds as Mock)
        .mockReturnValueOnce(new Set()) // promote check
        .mockReturnValue(new Set([5, 10])); // remaining check

      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Station, id: 10 },
        { ctrlKey: true }
      );

      expect(
        mockSimulationStateManager.addSelectedStation
      ).toHaveBeenCalledWith(5);
      expect(
        mockSimulationStateManager.toggleSelectedStation
      ).toHaveBeenCalledWith(10);
    });

    test('ctrl+click without existing single selection just toggles', () => {
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        null
      );
      (
        mockSimulationStateManager.getMultiSelectedStationIds as Mock
      ).mockReturnValue(new Set([10]));

      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Station, id: 10 },
        { ctrlKey: true }
      );

      expect(
        mockSimulationStateManager.addSelectedStation
      ).not.toHaveBeenCalled();
      expect(
        mockSimulationStateManager.toggleSelectedStation
      ).toHaveBeenCalledWith(10);
    });

    test('ctrl+click does not re-promote station already in multi-selection', () => {
      const station = makeStation({ id: 5, name: 'Station 5' });
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        station
      );
      (
        mockSimulationStateManager.getMultiSelectedStationIds as Mock
      ).mockReturnValue(new Set([5]));

      // After toggle, simulate 2 stations
      (mockSimulationStateManager.getMultiSelectedStationIds as Mock)
        .mockReturnValueOnce(new Set([5])) // first call in promote check
        .mockReturnValue(new Set([5, 10])); // after toggle

      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Station, id: 10 },
        { ctrlKey: true }
      );

      expect(
        mockSimulationStateManager.addSelectedStation
      ).not.toHaveBeenCalled();
      expect(
        mockSimulationStateManager.toggleSelectedStation
      ).toHaveBeenCalledWith(10);
    });

    test('ctrl+click demotes to single selection when only 1 station remains', () => {
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        null
      );
      // After toggle, only 1 station remains
      (
        mockSimulationStateManager.getMultiSelectedStationIds as Mock
      ).mockReturnValue(new Set([5]));

      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Station, id: 10 },
        { ctrlKey: true }
      );

      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
      expect(selectItem).toHaveBeenCalledWith(SelectedItemType.Station, 5);
    });

    test('ctrl+click demotes to empty selection when 0 stations remain', () => {
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        null
      );
      // After toggle, 0 stations remain
      (
        mockSimulationStateManager.getMultiSelectedStationIds as Mock
      ).mockReturnValue(new Set());

      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Station, id: 10 },
        { ctrlKey: true }
      );

      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
      expect(selectItem).not.toHaveBeenCalled();
    });

    test('ctrl+click with single-selected driver does not promote (driver has shift)', () => {
      const driver = makeDriver({ id: 3 });
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        driver
      );
      (
        mockSimulationStateManager.getMultiSelectedStationIds as Mock
      ).mockReturnValue(new Set([10]));

      const clickHandler = getClickHandler();
      clickHandler(
        { type: SelectedItemType.Station, id: 10 },
        { ctrlKey: true }
      );

      // Driver has 'shift' property so it should not be promoted as a station
      expect(
        mockSimulationStateManager.addSelectedStation
      ).not.toHaveBeenCalled();
    });
  });

  // ── hover handler ─────────────────────────────────────────

  describe('hover handler', () => {
    test('hovering over a station updates hover state', () => {
      vi.useFakeTimers();
      const hoverHandler = getHoverHandler();
      hoverHandler({ type: SelectedItemType.Station, id: 5 });

      expect(manager['hoveredStationId']).toBe(5);
      expect(manager['hoveredResourceId']).toBeNull();

      vi.advanceTimersByTime(20);
      expect(
        mockSimulationStateManager.setMapShouldRefresh
      ).toHaveBeenCalledWith(true);
      vi.useRealTimers();
    });

    test('hovering over a driver updates hover state', () => {
      vi.useFakeTimers();
      const hoverHandler = getHoverHandler();
      hoverHandler({ type: SelectedItemType.Driver, id: 3 });

      expect(manager['hoveredStationId']).toBeNull();
      expect(manager['hoveredResourceId']).toBe(3);

      vi.advanceTimersByTime(20);
      expect(
        mockSimulationStateManager.setMapShouldRefresh
      ).toHaveBeenCalledWith(true);
      vi.useRealTimers();
    });

    test('hovering over nothing clears hover state', () => {
      vi.useFakeTimers();
      const hoverHandler = getHoverHandler();
      // First hover over a station
      hoverHandler({ type: SelectedItemType.Station, id: 5 });
      vi.advanceTimersByTime(20);

      // Then move to nothing
      hoverHandler(null);

      expect(manager['hoveredStationId']).toBeNull();
      expect(manager['hoveredResourceId']).toBeNull();
      vi.useRealTimers();
    });

    test('hover is ignored when hoverLocked is true', () => {
      const hoverHandler = getHoverHandler();
      manager['hoverLocked'] = true;
      hoverHandler({ type: SelectedItemType.Station, id: 5 });

      expect(manager['hoveredStationId']).toBeNull();
    });
  });

  // ── box select handler ────────────────────────────────────

  describe('box select handler', () => {
    test('box select with multiple stations sets multi-selection', () => {
      const boxSelectHandler = getBoxSelectHandler();
      boxSelectHandler([1, 2, 3]);

      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
      expect(
        mockSimulationStateManager.setSelectedStations
      ).toHaveBeenCalledWith([1, 2, 3]);
    });

    test('box select with single station selects single item', () => {
      const boxSelectHandler = getBoxSelectHandler();
      boxSelectHandler([5]);

      expect(mockSimulationStateManager.clearSelection).toHaveBeenCalled();
      expect(selectItem).toHaveBeenCalledWith(SelectedItemType.Station, 5);
    });

    test('box select with empty array does nothing', () => {
      const boxSelectHandler = getBoxSelectHandler();
      boxSelectHandler([]);

      expect(mockSimulationStateManager.clearSelection).not.toHaveBeenCalled();
      expect(selectItem).not.toHaveBeenCalled();
    });
  });

  // ── station drag handler ──────────────────────────────────

  describe('station drag handler', () => {
    test('dragging stations onto a driver calls requestAssignment', () => {
      const station = makeStation({ id: 1, taskIds: [10, 11] });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(
        makeDriver({ id: 5 })
      );
      (mockSimulationStateManager.getStation as Mock).mockReturnValue(station);

      const dragHandler = getStationDragHandler();
      dragHandler([1], 5);

      expect(requestAssignment).toHaveBeenCalledWith(5, [10, 11]);
    });

    test('dragging stations onto a non-existent driver shows error', () => {
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(undefined);

      const dragHandler = getStationDragHandler();
      dragHandler([1], 99);

      expect(mockToastError).toHaveBeenCalledWith('Driver #99 not found.');
      expect(requestAssignment).not.toHaveBeenCalled();
    });

    test('dragging a non-existent station shows error and skips it', () => {
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(
        makeDriver({ id: 5 })
      );
      (mockSimulationStateManager.getStation as Mock).mockReturnValue(
        undefined
      );

      const dragHandler = getStationDragHandler();
      dragHandler([1], 5);

      expect(mockToastError).toHaveBeenCalledWith('Station #1 not found.');
    });

    test('dragging stations with no tasks shows info toast (single station)', () => {
      const station = makeStation({ id: 1, name: 'Central', taskIds: [] });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(
        makeDriver({ id: 5 })
      );
      (mockSimulationStateManager.getStation as Mock).mockReturnValue(station);

      const dragHandler = getStationDragHandler();
      dragHandler([1], 5);

      expect(mockToastInfo).toHaveBeenCalledWith('No tasks at Central.');
      expect(requestAssignment).not.toHaveBeenCalled();
    });

    test('dragging stations with no tasks shows info toast (multiple stations)', () => {
      const station = makeStation({ id: 1, taskIds: [] });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(
        makeDriver({ id: 5 })
      );
      (mockSimulationStateManager.getStation as Mock).mockReturnValue(station);

      const dragHandler = getStationDragHandler();
      dragHandler([1, 2], 5);

      expect(mockToastInfo).toHaveBeenCalledWith(
        'No tasks at the selected stations.'
      );
    });

    test('drag hover callback locks and unlocks hover', () => {
      const dragHoverHandler = getStationDragHoverHandler();

      dragHoverHandler(5);
      expect(manager['hoverLocked']).toBe(true);
      expect(manager['hoveredStationId']).toBe(5);

      dragHoverHandler(null);
      expect(manager['hoverLocked']).toBe(false);
    });

    test('getMultiSelectedStationIds getter returns current ids', () => {
      (
        mockSimulationStateManager.getMultiSelectedStationIds as Mock
      ).mockReturnValue(new Set([1, 2]));

      const getter = getStationDragIdsGetter();
      expect(getter()).toEqual([1, 2]);
    });
  });

  // ── updateMapSources ──────────────────────────────────────

  describe('updateMapSources', () => {
    test('updates headquarters when provided', () => {
      const hq = { position: [0, 0] as Position };
      const geojson = { type: 'FeatureCollection' };
      mockAdaptHeadquartersToGeoJSON.mockReturnValue(geojson);
      manager.updateMapSources(false, [], [], new Map(), new Map(), hq);

      expect(mockAdaptHeadquartersToGeoJSON).toHaveBeenCalledWith(hq);
      expect(mockSetMapSource).toHaveBeenCalledWith(
        'headquarters',
        geojson,
        mockMap
      );
    });

    test('updates stations when provided', () => {
      const stations = [makeStation({ id: 1 })];
      const geojson = { type: 'FeatureCollection' };
      mockAdaptStationsToGeoJSON.mockReturnValue(geojson);
      manager.updateMapSources(false, [], stations, new Map(), new Map(), null);

      expect(mockAdaptStationsToGeoJSON).toHaveBeenCalled();
      expect(mockSetMapSource).toHaveBeenCalledWith(
        'stations',
        geojson,
        mockMap
      );
    });

    test('updates resources for drivers with vehicles', () => {
      const drivers = [
        makeDriver({ id: 1, vehicleId: 10 }),
        makeDriver({ id: 2, vehicleId: null }),
      ];
      manager.updateMapSources(false, drivers, [], new Map(), new Map(), null);

      expect(mockAdaptResourcesToGeoJSON).toHaveBeenCalledWith(
        [expect.objectContaining({ id: 1 })],
        undefined,
        undefined
      );
    });

    test('shows all routes when toggle is on', () => {
      const routesMap = new Map<number, Route>();
      const positionsMap = new Map<number, Position>();
      manager.updateMapSources(true, [], [], routesMap, positionsMap, null);

      expect(mockUpdateAllRoutesDisplay).toHaveBeenCalledWith(
        routesMap,
        positionsMap,
        undefined,
        mockMap
      );
    });

    test('clears all routes when toggle is off', () => {
      manager.updateMapSources(false, [], [], new Map(), new Map(), null);

      expect(mockClearAllRoutesDisplay).toHaveBeenCalledWith(mockMap);
    });

    test('defers update when map style is not loaded', () => {
      (mockMap.isStyleLoaded as Mock).mockReturnValue(false);

      manager.updateMapSources(false, [], [], new Map(), new Map(), null);

      expect(mockMap.once as Mock).toHaveBeenCalledWith(
        'styledata',
        expect.any(Function)
      );
      expect(mockSetMapSource).not.toHaveBeenCalled();
    });

    test('shows selected route when a driver is selected', () => {
      const driver = makeDriver({ id: 1 });
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        driver
      );

      const route: Route = {
        coordinates: [
          [0, 0],
          [1, 1],
        ],
        nextStopIndex: 1,
        trafficRanges: [],
      };
      const routesMap = new Map<number, Route>([[1, route]]);
      const positionsMap = new Map<number, Position>([[1, [0, 0]]]);

      manager.updateMapSources(
        false,
        [driver],
        [],
        routesMap,
        positionsMap,
        null
      );

      expect(mockUpdateRouteDisplay).toHaveBeenCalledWith(
        route,
        [0, 0],
        mockMap
      );
    });

    test('clears route display when no driver is selected', () => {
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        null
      );

      manager.updateMapSources(false, [], [], new Map(), new Map(), null);

      expect(mockClearRouteDisplay).toHaveBeenCalledWith(mockMap);
    });

    test('clears route display when selected driver has no route', () => {
      const driver = makeDriver({ id: 1 });
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        driver
      );

      manager.updateMapSources(false, [driver], [], new Map(), new Map(), null);

      expect(mockClearRouteDisplay).toHaveBeenCalled();
    });

    test('returns selected station id when a station is selected', () => {
      const station = makeStation({ id: 7 });
      (mockSimulationStateManager.getSelectedItem as Mock).mockReturnValue(
        station
      );

      const stations = [station];
      manager.updateMapSources(false, [], stations, new Map(), new Map(), null);

      expect(mockAdaptStationsToGeoJSON).toHaveBeenCalledWith(
        stations,
        7,
        undefined,
        expect.anything()
      );
    });
  });

  // ── animateResources ──────────────────────────────────────

  describe('animateResources', () => {
    test('schedules next frame', () => {
      raf.mockClear();
      mockUpdateDriverPositions.mockReturnValue(false);
      manager['animateResources']();
      expect(raf).toHaveBeenCalled();
    });

    test('triggers map refresh when driver positions change', () => {
      mockUpdateDriverPositions.mockReturnValue(true);
      (mockSimulationStateManager.getMapShouldRefresh as Mock).mockReturnValue(
        false
      );

      manager['animateResources']();

      expect(
        mockSimulationStateManager.setMapShouldRefresh
      ).toHaveBeenCalledWith(true);
    });

    test('calls updateMapSources when map should refresh', () => {
      mockUpdateDriverPositions.mockReturnValue(false);
      (mockSimulationStateManager.getMapShouldRefresh as Mock).mockReturnValue(
        true
      );

      manager['animateResources']();

      expect(
        mockSimulationStateManager.setMapShouldRefresh
      ).toHaveBeenCalledWith(false);
    });
  });

  // ── cleanup ───────────────────────────────────────────────

  describe('cleanup', () => {
    test('cancels animation frame', () => {
      manager['animationFrame'] = 42;
      manager.cleanup();
      expect(caf).toHaveBeenCalledWith(42);
    });

    test('does not cancel if animationFrame is 0', () => {
      manager['animationFrame'] = 0;
      manager.cleanup();
      expect(caf).not.toHaveBeenCalled();
    });
  });
});
