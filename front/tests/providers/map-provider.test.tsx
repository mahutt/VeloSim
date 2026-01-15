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

import { expect, test, vi } from 'vitest';
import { render, act } from '@testing-library/react';
import {
  INITIAL_CENTER,
  INITIAL_ZOOM,
  MapProvider,
  useMap,
} from '~/providers/map-provider';
import { MockMap } from 'tests/mocks';
import MapContainer from '~/components/map/map-container';
import {
  initializeMapSources,
  loadMapImages,
  setMapLayers,
} from '~/lib/map-helpers';
import { logSimulationError } from '~/utils/simulation-error-utils';
import { SimulationProvider } from '~/providers/simulation-provider';
import { TaskAssignmentProvider } from '~/providers/task-assignment-provider';

// Mock useAuth hook
vi.mock('~/hooks/use-auth', () => ({
  default: () => ({
    user: { id: 1, username: 'test_user', is_admin: false },
    setUser: vi.fn(),
    loading: false,
    setLoading: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
    setToken: vi.fn(),
  }),
}));

// Mocking setup map helpers that are called by MapProvider
vi.mock('~/lib/map-helpers.ts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('~/lib/map-helpers.ts')>();
  return {
    ...actual,
    loadMapImages: vi.fn(),
    initializeMapSources: vi.fn(),
    setMapLayers: vi.fn(),
    setMapSource: vi.fn(),
  };
});

// Mock simulation error utils
vi.mock('~/utils/simulation-error-utils', () => ({
  logSimulationError: vi.fn(),
}));

// Mock useError hook
const mockDisplayError = vi.fn();
vi.mock('~/hooks/use-error', () => ({
  default: () => ({ displayError: mockDisplayError }),
}));

test('map provider instantiates mapboxgl Map instance in presence of map container', async () => {
  render(
    <MapProvider>
      <SimulationProvider>
        <TaskAssignmentProvider>
          <MapContainer />
        </TaskAssignmentProvider>
      </SimulationProvider>
    </MapProvider>
  );
  const map = MockMap.instance;
  expect(map).toBeDefined();
  expect(map!.getCenter()).toBe(INITIAL_CENTER);
  expect(map!.getZoom()).toBe(INITIAL_ZOOM);
});

test("map provider doesn't instantiate mapboxgl Map instance without map container", async () => {
  render(
    <MapProvider>
      <div />
    </MapProvider>
  );
  const map = MockMap.instance;
  expect(map).toBeUndefined();
});

test('on-load callback sets mapLoaded to true', async () => {
  // Create a simple test component that only uses the map container ref
  const TestMapContainer = () => {
    const { mapContainerRef } = useMap();
    return (
      <div
        id="map-container"
        data-testid="map-container"
        className="h-screen w-full"
        ref={mapContainerRef}
      />
    );
  };

  render(
    <MapProvider>
      <TestMapContainer />
    </MapProvider>
  );

  expect(MockMap.instance).toBeDefined();
  const map = MockMap.instance!;
  expect(map.callBacks.load).toBeDefined();

  // Wrap the state update in act()
  act(() => {
    map.callBacks.load();
  });

  expect(loadMapImages).toHaveBeenCalledWith(map);
  expect(initializeMapSources).toHaveBeenCalledWith(map);
  expect(setMapLayers).toHaveBeenCalledWith(map);
});

test('on-error callback logs error, calls logSimulationError and displayError, and reloads on retry', async () => {
  // Mock dependencies
  const mockReload = vi.fn();
  const errorEvent = {
    error: { message: 'Map failed to load tiles' },
    sourceId: 'mapbox-streets',
  };

  // Mock window.location.reload
  const originalReload = window.location.reload;
  window.location.reload = mockReload;

  // Setup mockDisplayError to call retry callback
  mockDisplayError.mockImplementation((_title, _desc, retry) => {
    if (retry) retry();
  });

  // Minimal test component to trigger map error
  const TestMapContainer = () => {
    const { mapContainerRef } = useMap();
    return <div ref={mapContainerRef} />;
  };

  render(
    <MapProvider>
      <TestMapContainer />
    </MapProvider>
  );

  const map = MockMap.instance!;
  expect(map.callBacks.error).toBeDefined();

  // Spy on console.error
  const consoleErrorSpy = vi
    .spyOn(console, 'error')
    .mockImplementation(() => {});

  // Trigger error callback
  act(() => {
    map.callBacks.error(errorEvent);
  });

  expect(logSimulationError).toHaveBeenCalledWith(
    'Map failed to load tiles',
    'Map loading',
    {
      errorType: 'MAP_LOAD_FAILED',
      sourceId: 'mapbox-streets',
      originalError: errorEvent.error,
    }
  );
  expect(mockDisplayError).toHaveBeenCalledWith(
    'Failed to load map',
    'An error occurred while loading the map. Please try again later.',
    expect.any(Function)
  );
  expect(mockReload).toHaveBeenCalled();

  // Restore mocks
  consoleErrorSpy.mockRestore();
  window.location.reload = originalReload;
  mockDisplayError.mockClear();
});
