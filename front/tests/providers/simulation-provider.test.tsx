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

import { expect, test, vi, beforeEach, type Mock } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import {
  SimulationProvider,
  useSimulation,
} from '~/providers/simulation-provider';
import { MapProvider } from '~/providers/map-provider';
import { MockMap } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';
import { setMapSource, MapSource } from '~/lib/map-helpers';
import { type Station, type SelectedItem, SelectedItemType } from '~/types';
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
    setupMapClickHandlers: vi.fn(),
  };
});

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Test component to access the simulation context
const TestComponent = () => {
  const { stationsRef } = useSimulation();
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

// Sample resource routes GeoJSON data
const mockResourceRoutesData = {
  type: 'FeatureCollection' as const,
  features: [
    {
      type: 'Feature' as const,
      properties: { id: 'resource-1' },
      geometry: {
        type: 'LineString' as const,
        coordinates: [
          [-73.57776, 45.48944],
          [-73.56776, 45.49944],
          [-73.55776, 45.50944],
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

test('useSimulation hook throws error when used outside of simulation provider', () => {
  expect(() => {
    render(
      <MapProvider>
        <MapContainer />
        <TestComponent />
      </MapProvider>
    );
  }).toThrow('useSimulation must be used within a SimulationProvider');
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
    json: () => Promise.resolve(mockResourceRoutesData),
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
    json: () => Promise.resolve(mockResourceRoutesData),
  });

  let stationsRef: React.RefObject<Map<number, Station>> | undefined;

  const StateCapture = () => {
    const { stationsRef: stationsRefFromHook } = useSimulation();
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

test('simulation provider loads resource routes', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourceRoutesData),
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
    expect(mockFetch).toHaveBeenCalledWith(
      '/placeholder-data/resource-routes.geojson'
    );
  });
});

test('simulation provider starts animation loop', async () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourceRoutesData),
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
    json: () => Promise.resolve(mockResourceRoutesData),
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
    expect(mockFetch).toHaveBeenCalledWith(
      '/placeholder-data/resource-routes.geojson'
    );
  });

  await waitFor(
    () => {
      expect(setMapSource).toHaveBeenCalledWith(
        MapSource.Resources,
        expect.any(Object),
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
    json: () => Promise.resolve(mockResourceRoutesData),
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
    json: () => Promise.resolve(mockResourceRoutesData),
  });

  let selectedItem: SelectedItem | null | undefined;
  let setSelectedItem: ((item: SelectedItem | null) => void) | undefined;

  const TestComponent = () => {
    const context = useSimulation();
    selectedItem = context.selectedItem;
    setSelectedItem = context.setSelectedItem;
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
  expect(setSelectedItem).toBeDefined();
});

test('simulation provider allows updating selection state', () => {
  (api.get as Mock).mockResolvedValueOnce({
    data: mockGetStationsResponse,
  });

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResourceRoutesData),
  });

  const TestComponent = () => {
    const { selectedItem, setSelectedItem } = useSimulation();

    return (
      <div>
        <div data-testid="selected-item">
          {selectedItem ? JSON.stringify(selectedItem) : 'null'}
        </div>
        <button
          data-testid="select-station"
          onClick={() =>
            setSelectedItem({
              type: SelectedItemType.Station,
              value: mockGetStationsResponse.stations[0],
            })
          }
        >
          Select Station
        </button>
        <button data-testid="deselect" onClick={() => setSelectedItem(null)}>
          Deselect
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

  act(() => {
    getByTestId('select-station').click();
  });

  expect(getByTestId('selected-item')).toHaveTextContent(
    JSON.stringify({
      type: 'station',
      value: mockGetStationsResponse.stations[0],
    })
  );

  act(() => {
    getByTestId('deselect').click();
  });

  expect(getByTestId('selected-item')).toHaveTextContent('null');
});
