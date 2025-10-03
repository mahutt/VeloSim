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

import { expect, test, vi, beforeEach } from 'vitest';
import { render, waitFor, act } from '@testing-library/react';
import {
  SimulationProvider,
  useSimulation,
} from '~/providers/simulation-provider';
import { MapProvider } from '~/providers/map-provider';
import { MockMap } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';
import { setMapSource, MapSource } from '~/lib/map-helpers';

// Mock the map-helpers module
vi.mock('~/lib/map-helpers.ts', () => {
  return {
    loadMapImages: vi.fn(),
    initializeMapSources: vi.fn(),
    setMapLayers: vi.fn(),
    setMapSource: vi.fn(),
    MapSource: {
      Stations: 'stations',
      Resources: 'resources',
    },
  };
});

// Mock the fetch API
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Test component to access the simulation context
const TestComponent = () => {
  const { state } = useSimulation();
  return (
    <div data-testid="test-component">
      {state.current ? 'data-loaded' : 'no-data'}
    </div>
  );
};

// Sample GeoJSON data for testing
const mockStationsData = {
  type: 'FeatureCollection' as const,
  features: [
    {
      type: 'Feature' as const,
      geometry: {
        type: 'Point' as const,
        coordinates: [-73.57776, 45.48944],
      },
    },
  ],
};

// Sample GeoJSON data for resources
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
  // Mock successful fetch response
  mockFetch
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStationsData),
    })
    .mockResolvedValueOnce({
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
    expect(mockFetch).toHaveBeenCalledWith(
      '/placeholder-data/stations.geojson'
    );
  });

  await waitFor(() => {
    expect(setMapSource).toHaveBeenCalledWith(
      MapSource.Stations,
      mockStationsData,
      map
    );
  });
});

test('simulation provider updates state ref when data is successfully fetched', async () => {
  mockFetch
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStationsData),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResourceRoutesData),
    });

  let stateRef: React.RefObject<GeoJSON.GeoJSON | null> | null = null;

  const StateCapture = () => {
    const { state } = useSimulation();
    stateRef = state;
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
    expect(mockFetch).toHaveBeenCalledWith(
      '/placeholder-data/stations.geojson'
    );
  });

  await waitFor(() => {
    expect(stateRef?.current).toEqual(mockStationsData);
  });
});

test('simulation provider updates resource positions via animation loop', async () => {
  mockFetch
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStationsData),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResourceRoutesData),
    });

  const mockGeoJSONSource = {
    setData: vi.fn(),
  };

  render(
    <MapProvider>
      <SimulationProvider>
        <MapContainer />
      </SimulationProvider>
    </MapProvider>
  );

  const map = MockMap.instance!;
  map.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  act(() => {
    map.callBacks.load();
  });

  await waitFor(() => {
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  // Wait for animation loop to call setMapSource at least once
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
