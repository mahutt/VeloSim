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

/* Test here have been developed with the help of GitHub Copilot */

// Mock the mock-backend module before any imports that might use it
vi.mock('~/lib/mock-backend', async (importOriginal) => {
  const original = await importOriginal<typeof import('~/lib/mock-backend')>();
  return {
    ...original,
    startMockBackend: vi.fn(),
    FRAME_INTERVAL_MS: 16, // or whatever value is appropriate for your tests
  };
});

import { expect, test, vi, beforeEach, type Mock } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import {
  SimulationProvider,
  useSimulationContext,
} from '~/providers/simulation-provider';
import { MapProvider } from '~/providers/map-provider';
import { MockMap } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';
import { setMapSource, MapSource } from '~/lib/map-helpers';
import {
  setupMapClickHandlers,
  setupMapHoverHandlers,
} from '~/lib/map-interactions';
import {
  type Station,
  type Resource,
  type SelectedItem,
  SelectedItemType,
} from '~/types';
import api from '~/api';
import { adaptStationsToGeoJSON } from '~/lib/geojson-adapters';

// Mock the API module
vi.mock('~/api', () => {
  return {
    default: {
      get: vi.fn(),
    },
  };
});

// Mock the map-helpers module
vi.mock('~/lib/map-helpers.ts', async (importOriginal) => {
  return {
    ...(await importOriginal<typeof import('~/lib/map-helpers.ts')>()),
    loadMapImages: vi.fn(),
    initializeMapSources: vi.fn(),
    setMapLayers: vi.fn(),
    setMapSource: vi.fn(),
  };
});

// Mock the map-interactions module
vi.mock('~/lib/map-interactions.ts', () => {
  return {
    setupMapClickHandlers: vi.fn(),
    setupMapHoverHandlers: vi.fn(),
  };
});

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Test component to access the simulation context
const TestComponent = () => {
  const { stationsRef } = useSimulationContext();
  return (
    <div data-testid="test-component">
      {stationsRef.current.size > 0 ? 'data-loaded' : 'no-data'}
    </div>
  );
};

// Sample GeoJSON data for testing
const mockGetStationsResponse = {
  stations: [
    {
      id: 1,
      name: 'Metcalfe / de Maisonneuve',
      position: [-73.57314596652985, 45.501375027330134],
      tasks: [],
    },
    {
      id: 2,
      name: 'Sanguinet / de Maisonneuve',
      position: [-73.56261849403381, 45.51344071811516],
      tasks: [],
    },
    {
      id: 3,
      name: 'St-Denis / Ste-Catherine',
      position: [-73.5639146839003, 45.510079193884],
      tasks: [],
    },
    {
      id: 4,
      name: 'St-André / Ontario',
      position: [-73.56353, 45.521889],
      tasks: [],
    },
    {
      id: 5,
      name: 'St-André / de Maisonneuve',
      position: [-73.55974848376083, 45.517085960784755],
      tasks: [],
    },
    {
      id: 6,
      name: 'de la Commune / des Soeurs-Grises',
      position: [-73.55273187160492, 45.49798647260488],
      tasks: [],
    },
    {
      id: 7,
      name: 'Notre-Dame / St-Gabriel',
      position: [-73.55504930019379, 45.50711760282556],
      tasks: [],
    },
    {
      id: 8,
      name: 'de la Commune / Place Jacques-Cartier',
      position: [-73.55183601379395, 45.50761009451047],
      tasks: [],
    },
    {
      id: 9,
      name: 'de Maisonneuve / Mansfield (sud)',
      position: [-73.57346534729004, 45.502053864057466],
      tasks: [],
    },
    {
      id: 10,
      name: "Métro Place-d'Armes (St-Urbain / Viger)",
      position: [-73.5596989095211, 45.50632340391333],
      tasks: [],
    },
  ] as Station[],
  total: 10,
  page: 1,
  per_page: 20,
  total_pages: 1,
};

const mockResourcesData = {
  resources: [
    {
      id: 1,
      position: [-73.57776, 45.48944],
      taskList: [1, 2, 3],
      route: {
        coordinates: [
          [-73.57776, 45.48944],
          [-73.56776, 45.49944],
          [-73.55776, 45.50944],
        ],
      },
    },
    {
      id: 2,
      position: [-73.56776, 45.47944],
      taskList: [1, 2],
      route: {
        coordinates: [
          [-73.56776, 45.47944],
          [-73.568, 45.48],
          [-73.569, 45.482],
        ],
      },
    },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
});

test('simulation provider renders without crashing when wrapped in map provider', () => {
  render(
    <MapProvider>
      <SimulationProvider>
        <div data-testid="child">Test Child</div>
      </SimulationProvider>
    </MapProvider>
  );
});

test('simulation provider throws error when used outside of map provider', () => {
  expect(() => {
    render(
      <SimulationProvider>
        <TestComponent />
      </SimulationProvider>
    );
  }).toThrow('useMap must be used within a MapProvider');
});

test('useSimulationContext hook throws error when used outside of simulation provider', () => {
  expect(() => {
    render(
      <MapProvider>
        <MapContainer />
        <TestComponent />
      </MapProvider>
    );
  }).toThrow('useSimulationContext must be used within a SimulationProvider');
});

test('simulation provider provides context with initial state', () => {
  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <TestComponent />
      </SimulationProvider>
    </MapProvider>
  );

  expect(getByTestId('test-component')).toHaveTextContent('no-data');
});

test('simulation provider fetches stations data when map is loaded', async () => {
  //Mock successful API response
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <TestComponent />
      </SimulationProvider>
    </MapProvider>
  );

  // Wait for the map to be created
  expect(MockMap.instance).toBeDefined();
  const map = MockMap.instance!;

  // Trigger the map load event to simulate map being ready
  act(() => {
    map.callBacks.load();
  });

  // Wait for the fetch to complete and state to update
  await waitFor(() => {
    expect(api.get).toHaveBeenCalledWith('/stations');
  });

  await waitFor(() => {
    expect(setMapSource).toHaveBeenCalledWith(
      MapSource.Stations,
      adaptStationsToGeoJSON(mockGetStationsResponse.stations),
      map
    );
  });
});

test('simulation provider updates stations ref when data is successfully fetched', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  let stationsRef: React.RefObject<Map<number, Station>> | undefined;

  const StateCapture = () => {
    const { stationsRef: stationsRefFromHook } = useSimulationContext();
    stationsRef = stationsRefFromHook;
    return null;
  };

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <StateCapture />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(api.get).toHaveBeenCalledWith('/stations');
  });

  await waitFor(() => {
    expect(stationsRef?.current.size).toBe(10);
  });
});

test('simulation provider handles fetch error for resource routes gracefully', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 404,
    json: () => Promise.resolve({}),
  });

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalledWith('/placeholder-data/resources.json');
  });

  // Should not throw, and setMapSource for resources should not be called
  await waitFor(
    () => {
      // Debug: Check all calls to setMapSource
      const calls = (setMapSource as Mock).mock.calls;
      const resourceCalls = calls.filter(
        (call) => call[0] === MapSource.Resources
      );

      expect(resourceCalls).toHaveLength(0);
    },
    { timeout: 100 }
  );
});

test('simulation provider sets up map click handlers and handles station selection', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  let clickHandler:
    | ((
        item: {
          type: SelectedItemType;
          id: number;
          coordinates: [number, number];
        } | null
      ) => void)
    | undefined;
  (setupMapClickHandlers as Mock).mockImplementation((map, handler) => {
    clickHandler = handler;
  });

  let selectedItem: SelectedItem | null = null;
  const TestComponent = () => {
    const { selectedItem: currentSelection } = useSimulationContext();
    selectedItem = currentSelection;
    return null;
  };

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <TestComponent />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(setupMapClickHandlers).toHaveBeenCalledWith(
      map,
      expect.any(Function)
    );
  });

  // Simulate clicking on a station
  act(() => {
    clickHandler!({
      type: SelectedItemType.Station,
      id: mockGetStationsResponse.stations[0].id,
      coordinates: mockGetStationsResponse.stations[0].position as [
        number,
        number,
      ],
    });
  });

  expect(selectedItem).toEqual({
    type: SelectedItemType.Station,
    value: mockGetStationsResponse.stations[0],
  });

  // Simulate clicking on empty area (deselect)
  act(() => {
    clickHandler!(null);
  });

  expect(selectedItem).toBeNull();
});

test('simulation provider sets up map click handlers and handles resource selection', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  let clickHandler:
    | ((
        item: {
          type: SelectedItemType;
          id: number;
          coordinates: [number, number];
        } | null
      ) => void)
    | undefined;
  (setupMapClickHandlers as Mock).mockImplementation((map, handler) => {
    clickHandler = handler;
  });

  let selectedItem: SelectedItem | null = null;
  const TestComponent = () => {
    const { selectedItem: currentSelection } = useSimulationContext();
    selectedItem = currentSelection;
    return null;
  };

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <TestComponent />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  // Wait for resources to be initialized
  await waitFor(() => {
    expect(setupMapClickHandlers).toHaveBeenCalledWith(
      map,
      expect.any(Function)
    );
  });

  // Simulate clicking on a resource (resource with id 1 should exist after fetch)
  act(() => {
    clickHandler!({
      type: SelectedItemType.Resource,
      id: 1,
      coordinates: [-73.57776, 45.48944],
    });
  });

  expect(selectedItem).toEqual({
    type: SelectedItemType.Resource,
    value: expect.objectContaining({
      id: 1,
      position: expect.any(Array),
      route: expect.objectContaining({
        coordinates: expect.any(Array),
      }),
    }),
  });
});

test('simulation provider sets up map hover handlers and handles station hover', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: false,
    status: 404,
    json: () => Promise.resolve({}),
  });

  let hoverHandler:
    | ((
        item: {
          type: SelectedItemType;
          id: number;
          coordinates: [number, number];
        } | null
      ) => void)
    | undefined;
  (setupMapHoverHandlers as Mock).mockImplementation((map, handler) => {
    hoverHandler = handler;
  });

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(setupMapHoverHandlers).toHaveBeenCalledWith(
      map,
      expect.any(Function)
    );
  });

  // Simulate hovering on a station
  act(() => {
    hoverHandler!({
      type: SelectedItemType.Station,
      id: mockGetStationsResponse.stations[0].id,
      coordinates: mockGetStationsResponse.stations[0].position as [
        number,
        number,
      ],
    });
  });

  // Verify that setMapSource was called with the hovered station
  await waitFor(() => {
    const calls = (setMapSource as Mock).mock.calls;
    const stationCalls = calls.filter((call) => call[0] === MapSource.Stations);
    expect(stationCalls.length).toBeGreaterThan(0);
    // The last call should include hover state
    const lastStationCall = stationCalls[stationCalls.length - 1];
    expect(lastStationCall[1]).toEqual(
      adaptStationsToGeoJSON(
        mockGetStationsResponse.stations,
        undefined,
        mockGetStationsResponse.stations[0].id
      )
    );
  });

  // Simulate hovering off (null)
  act(() => {
    hoverHandler!(null);
  });

  // Verify that setMapSource was called without hover state
  await waitFor(() => {
    const calls = (setMapSource as Mock).mock.calls;
    const stationCalls = calls.filter((call) => call[0] === MapSource.Stations);
    const lastStationCall = stationCalls[stationCalls.length - 1];
    expect(lastStationCall[1]).toEqual(
      adaptStationsToGeoJSON(
        mockGetStationsResponse.stations,
        undefined,
        undefined
      )
    );
  });
});

test('simulation provider handles click on non-existent station gracefully', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  let clickHandler:
    | ((
        item: {
          type: SelectedItemType;
          id: number;
          coordinates: [number, number];
        } | null
      ) => void)
    | undefined;
  (setupMapClickHandlers as Mock).mockImplementation((map, handler) => {
    clickHandler = handler;
  });

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(setupMapClickHandlers).toHaveBeenCalledWith(
      map,
      expect.any(Function)
    );
  });

  // Simulate clicking on a non-existent station
  expect(() => {
    act(() => {
      clickHandler!({
        type: SelectedItemType.Station,
        id: 999, // Non-existent station ID
        coordinates: [0, 0], // Mock coordinates for non-existent station
      });
    });
  }).toThrow('Selected station not found: 999');
});

test('simulation provider handles click on non-existent resource gracefully', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  let clickHandler:
    | ((
        item: {
          type: SelectedItemType;
          id: number;
          coordinates: [number, number];
        } | null
      ) => void)
    | undefined;
  (setupMapClickHandlers as Mock).mockImplementation((map, handler) => {
    clickHandler = handler;
  });

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(setupMapClickHandlers).toHaveBeenCalledWith(
      map,
      expect.any(Function)
    );
  });

  // Simulate clicking on a non-existent resource
  expect(() => {
    act(() => {
      clickHandler!({
        type: SelectedItemType.Resource,
        id: 999, // Non-existent resource ID
        coordinates: [0, 0], // Mock coordinates for non-existent resource
      });
    });
  }).toThrow('Selected resource not found: 999');
});

test('simulation provider starts animation loop', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  const requestAnimationFrameSpy = vi.spyOn(window, 'requestAnimationFrame');

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(requestAnimationFrameSpy).toHaveBeenCalled();
  });

  requestAnimationFrameSpy.mockRestore();
});

test('simulation provider updates resource positions', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalledWith('/placeholder-data/resources.json');
  });

  await waitFor(
    () => {
      expect(setMapSource).toHaveBeenCalledWith(
        MapSource.Resources,
        expect.objectContaining({
          type: 'FeatureCollection',
          features: expect.arrayContaining([
            expect.objectContaining({
              type: 'Feature',
              geometry: expect.objectContaining({
                type: 'Point',
                coordinates: [-73.57776, 45.48944],
              }),
              properties: expect.objectContaining({
                id: 1,
                hover: false,
                selected: false,
              }),
            }),
          ]),
        }),
        map
      );
    },
    { timeout: 100 }
  );
});

test('simulation provider cleans up on unmount', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  const cancelAnimationFrameSpy = vi.spyOn(window, 'cancelAnimationFrame');
  const clearIntervalSpy = vi.spyOn(window, 'clearInterval');

  const { unmount } = render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalled();
  });

  unmount();

  expect(cancelAnimationFrameSpy).toHaveBeenCalled();
  expect(clearIntervalSpy).toHaveBeenCalled();

  cancelAnimationFrameSpy.mockRestore();
  clearIntervalSpy.mockRestore();
});

test('simulation provider provides selection state', () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  let selectedItem: SelectedItem | null | undefined;
  let selectItem: ((type: SelectedItemType, id: number) => void) | undefined;

  const TestComponent = () => {
    const context = useSimulationContext();
    selectedItem = context.selectedItem;
    selectItem = context.selectItem;
    return null;
  };

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <TestComponent />
      </SimulationProvider>
    </MapProvider>
  );

  expect(selectedItem).toBeNull();
  expect(selectItem).toBeDefined();
});

test('simulation provider allows updating selection state', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  const TestComponent = () => {
    const { selectedItem, selectItem } = useSimulationContext();

    return (
      <div>
        <div data-testid="selected-item">
          {selectedItem ? JSON.stringify(selectedItem) : 'null'}
        </div>
        <button
          data-testid="select-station"
          onClick={() =>
            selectItem(
              SelectedItemType.Station,
              mockGetStationsResponse.stations[0].id
            )
          }
        >
          Select Station
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <TestComponent />
      </SimulationProvider>
    </MapProvider>
  );

  expect(getByTestId('selected-item')).toHaveTextContent('null');

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(api.get).toHaveBeenCalledWith('/stations');
  });

  act(() => {
    getByTestId('select-station').click();
  });

  await waitFor(() => {
    const content = getByTestId('selected-item').textContent;
    expect(content).not.toBe('null');
    const selectedItem = JSON.parse(content!);
    expect(selectedItem.type).toBe(SelectedItemType.Station);
    expect(selectedItem.value.id).toBe(mockGetStationsResponse.stations[0].id);
  });
});

test('simulation provider allows selecting a resource', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  const TestComponent = () => {
    const { selectedItem, selectItem } = useSimulationContext();

    return (
      <div>
        <div data-testid="selected-item">
          {selectedItem ? JSON.stringify(selectedItem) : 'null'}
        </div>
        <button
          data-testid="select-resource"
          onClick={() => selectItem(SelectedItemType.Resource, 1)}
        >
          Select Resource
        </button>
      </div>
    );
  };

  const { getByTestId } = render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
        <TestComponent />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalledWith('/placeholder-data/resources.json');
  });

  act(() => {
    getByTestId('select-resource').click();
  });

  await waitFor(() => {
    const content = getByTestId('selected-item').textContent;
    expect(content).not.toBe('null');
    const selectedItem = JSON.parse(content!);
    expect(selectedItem.type).toBe(SelectedItemType.Resource);
    expect(selectedItem.value.id).toBe(1);
  });
});
import * as mockBackend from '~/lib/mock-backend';

test('handleFrameUpdate updates resource positions and resets frame timer', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourcesData),
  });

  let handleFrameUpdateFn: ((updates: Resource[]) => void) | undefined;

  // Mock startMockBackend to capture handleFrameUpdate
  (mockBackend.startMockBackend as Mock).mockImplementation(
    (_resources, cb) => {
      handleFrameUpdateFn = cb;
      return () => {};
    }
  );

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  act(() => {
    map.callBacks.load();
  });

  // Wait for resources to be initialized and handleFrameUpdate to be set
  await waitFor(() => {
    expect(handleFrameUpdateFn).toBeTypeOf('function');
  });

  // Prepare spies and refs
  const nowSpy = vi.spyOn(performance, 'now').mockReturnValue(12345);
  // Simulate current animated position
  const newPosition: [number, number] = [-73.57776, 45.48944];

  // Simulate handleFrameUpdate call
  act(() => {
    const mockResource: Resource = {
      id: mockResourcesData.resources[0].id,
      position: newPosition,
      taskList: mockResourcesData.resources[0].taskList,
      route: {
        coordinates: mockResourcesData.resources[0].route.coordinates as [
          number,
          number,
        ][],
      },
    };
    handleFrameUpdateFn!([mockResource]);
  });

  // Check that the refs have been updated
  // We can't access refs directly, but we can check that setMapSource will eventually be called with the new position
  await waitFor(() => {
    const calls = (setMapSource as Mock).mock.calls;
    const resourceCalls = calls.filter(
      (call) => call[0] === MapSource.Resources
    );
    expect(resourceCalls.length).toBeGreaterThan(0);
    const lastCall = resourceCalls[resourceCalls.length - 1];
    expect(lastCall[1].features[0].geometry.coordinates).toEqual(newPosition);
  });

  nowSpy.mockRestore();
});
