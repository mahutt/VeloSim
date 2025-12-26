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
import {
  loadMapImages,
  initializeMapSources,
  setMapLayers,
  setMapSource,
  updateRouteDisplay,
  clearRouteDisplay,
  MapSource,
} from '~/lib/map-helpers';
import { MockMap } from 'tests/mocks';

test('loadMapImages loads all necessary images', () => {
  MockMap.createRandomInstance();
  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);
  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
  expect(MockMap.instance?.loadImage).toHaveBeenCalledWith(
    '/station.png',
    expect.any(Function)
  );
  expect(MockMap.instance?.loadImage).toHaveBeenCalledWith(
    '/resource.png',
    expect.any(Function)
  );
});

test('initializeMapSources adds all required sources', () => {
  MockMap.createRandomInstance();
  initializeMapSources(MockMap.instance! as unknown as mapboxgl.Map);

  // Should add one source for each MapSource enum value
  expect(MockMap.instance?.addSource).toHaveBeenCalledTimes(
    Object.values(MapSource).length
  );

  // Should add the stations source with correct configuration
  expect(MockMap.instance?.addSource).toHaveBeenCalledWith('stations', {
    type: 'geojson',
    data: {
      type: 'FeatureCollection',
      features: [],
    },
  });

  // Should add the resources source with correct configuration
  expect(MockMap.instance?.addSource).toHaveBeenCalledWith('resources', {
    type: 'geojson',
    data: {
      type: 'FeatureCollection',
      features: [],
    },
  });
});

test('setMapLayers adds stations layer with correct configuration', () => {
  MockMap.createRandomInstance();
  setMapLayers(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.addLayer).toHaveBeenCalledTimes(5);
  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'stations',
    type: 'symbol',
    source: 'stations',
    layout: {
      'icon-image': [
        'case',
        ['boolean', ['get', 'selected'], false],
        'station-marker-selected',
        ['boolean', ['get', 'hover'], false],
        'station-marker-hover',
        'station-marker',
      ],
      'icon-allow-overlap': true,
    },
  });

  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'resources',
    type: 'symbol',
    source: 'resources',
    layout: {
      'icon-image': [
        'case',
        ['boolean', ['get', 'selected'], false],
        'resource-marker-selected',
        ['boolean', ['get', 'hover'], false],
        'resource-marker-hover',
        'resource-marker',
      ],
      'icon-allow-overlap': true,
    },
  });
});

test('loadMapImages handles image loading with async callbacks', async () => {
  MockMap.createRandomInstance();

  const mockImage = { width: 32, height: 32 };

  // Mock loadImage to simulate async callback
  MockMap.instance!.loadImage = vi.fn(
    (
      url: string,
      callback: (
        error: Error | null,
        image?: { width: number; height: number }
      ) => void
    ) => {
      // Simulate async image loading
      setTimeout(async () => {
        callback(null, mockImage);
      }, 0);
    }
  );

  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);

  // Wait for async callbacks
  await new Promise((resolve) => setTimeout(resolve, 10));

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
});

test('setMapSource updates source data correctly', () => {
  MockMap.createRandomInstance();

  // Mock the getSource method to return an object with setData method
  const mockGeoJSONSource = {
    setData: vi.fn(),
  };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const testData: GeoJSON.GeoJSON = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [-73.935242, 40.73061],
        },
        properties: {
          name: 'Test Station',
        },
      },
    ],
  };

  setMapSource(
    MapSource.Stations,
    testData,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  expect(MockMap.instance?.getSource).toHaveBeenCalledWith('stations');
  expect(mockGeoJSONSource.setData).toHaveBeenCalledWith(testData);
});

test('loadMapImages successfully adds images when loaded', () => {
  MockMap.createRandomInstance();

  const mockImage = { width: 32, height: 32 };

  // Mock loadImage to call the callback with success
  MockMap.instance!.loadImage = vi.fn(
    (
      url: string,
      callback: (
        error: Error | null,
        image?: { width: number; height: number }
      ) => void
    ) => {
      callback(null, mockImage);
    }
  );

  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
  expect(MockMap.instance?.addImage).toHaveBeenCalledTimes(6);
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'station-marker',
    mockImage
  );
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'station-marker-selected',
    mockImage
  );
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'resource-marker',
    mockImage
  );
  expect(MockMap.instance?.addImage).toHaveBeenCalledWith(
    'resource-marker-selected',
    mockImage
  );
});

test('loadMapImages handles image load failure gracefully', () => {
  MockMap.createRandomInstance();

  // Mock loadImage to call the callback with an error
  MockMap.instance!.loadImage = vi.fn(
    (
      url: string,
      callback: (
        error: Error | null,
        image?: { width: number; height: number }
      ) => void
    ) => {
      callback(new Error('Failed to load image'));
    }
  );

  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(6);
  // Should not call addImage if loadImage fails
  expect(MockMap.instance?.addImage).not.toHaveBeenCalled();
});

test('updateRouteDisplay clears display when routeGeometry is null', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  updateRouteDisplay(null, 0, MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.getSource).toHaveBeenCalledWith('route-traversed');
  expect(MockMap.instance?.getSource).toHaveBeenCalledWith('route-remaining');
  expect(mockGeoJSONSource.setData).toHaveBeenCalledTimes(2);
  expect(mockGeoJSONSource.setData).toHaveBeenCalledWith({
    type: 'FeatureCollection',
    features: [],
  });
});

test('updateRouteDisplay clears display when routeGeometry has less than 2 points', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  updateRouteDisplay(
    [[-73.5, 45.5]],
    0,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  expect(mockGeoJSONSource.setData).toHaveBeenCalledTimes(2);
  expect(mockGeoJSONSource.setData).toHaveBeenCalledWith({
    type: 'FeatureCollection',
    features: [],
  });
});

test('updateRouteDisplay splits route at progress point', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routeGeometry: [number, number][] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
    [-73.8, 45.8],
  ];

  // Progress is now fractional (0-1): 0.5 = 50% along route
  updateRouteDisplay(
    routeGeometry,
    0.5,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  expect(mockGeoJSONSource.setData).toHaveBeenCalledTimes(2);

  // First call should be for traversed route (starts at route start)
  const traversedCall = mockGeoJSONSource.setData.mock.calls[0][0];
  expect(traversedCall.type).toBe('FeatureCollection');
  expect(traversedCall.features).toHaveLength(1);
  const traversedCoords = traversedCall.features[0].geometry.coordinates;
  expect(traversedCoords[0][0]).toBeCloseTo(-73.5, 3);
  expect(traversedCoords[0][1]).toBeCloseTo(45.5, 3);

  // Second call should be for remaining route (ends at route end)
  const remainingCall = mockGeoJSONSource.setData.mock.calls[1][0];
  expect(remainingCall.type).toBe('FeatureCollection');
  expect(remainingCall.features).toHaveLength(1);
  const remainingCoords = remainingCall.features[0].geometry.coordinates;
  const lastRemaining = remainingCoords[remainingCoords.length - 1];
  expect(lastRemaining[0]).toBeCloseTo(-73.8, 3);
  expect(lastRemaining[1]).toBeCloseTo(45.8, 3);
});

test('updateRouteDisplay handles progress at start of route', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routeGeometry: [number, number][] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
  ];

  // Progress 0 = at start of route
  updateRouteDisplay(
    routeGeometry,
    0,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  // Traversed should be empty (no distance covered)
  const traversedCall = mockGeoJSONSource.setData.mock.calls[0][0];
  expect(traversedCall.features).toEqual([]);

  // Remaining should cover entire route
  const remainingCall = mockGeoJSONSource.setData.mock.calls[1][0];
  expect(remainingCall.features).toHaveLength(1);
  const remainingCoords = remainingCall.features[0].geometry.coordinates;
  expect(remainingCoords[0][0]).toBeCloseTo(-73.5, 3);
  expect(remainingCoords[remainingCoords.length - 1][0]).toBeCloseTo(-73.7, 3);
});

test('updateRouteDisplay handles progress beyond route length', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routeGeometry: [number, number][] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
  ];

  // Progress 1 (or greater) = at end of route
  updateRouteDisplay(
    routeGeometry,
    1,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  // Traversed should cover entire route
  const traversedCall = mockGeoJSONSource.setData.mock.calls[0][0];
  expect(traversedCall.features).toHaveLength(1);
  const traversedCoords = traversedCall.features[0].geometry.coordinates;
  expect(traversedCoords[0][0]).toBeCloseTo(-73.5, 3);
  expect(traversedCoords[traversedCoords.length - 1][0]).toBeCloseTo(-73.7, 3);

  // Remaining should be empty (no distance left)
  const remainingCall = mockGeoJSONSource.setData.mock.calls[1][0];
  expect(remainingCall.features).toEqual([]);
});

test('clearRouteDisplay clears both route sources', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  clearRouteDisplay(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.getSource).toHaveBeenCalledWith('route-traversed');
  expect(MockMap.instance?.getSource).toHaveBeenCalledWith('route-remaining');
  expect(mockGeoJSONSource.setData).toHaveBeenCalledTimes(2);
});

test('setMapLayers adds route layers with correct configuration', () => {
  MockMap.createRandomInstance();
  setMapLayers(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'route-traversed',
    type: 'line',
    source: 'route-traversed',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#3b82f6',
      'line-width': 4,
      'line-opacity': 0.3,
    },
  });

  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'route-remaining',
    type: 'line',
    source: 'route-remaining',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': '#3b82f6',
      'line-width': 4,
      'line-opacity': 0.8,
    },
  });
});

test('initializeMapSources adds route sources', () => {
  MockMap.createRandomInstance();
  initializeMapSources(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.addSource).toHaveBeenCalledWith('route-traversed', {
    type: 'geojson',
    data: {
      type: 'FeatureCollection',
      features: [],
    },
  });

  expect(MockMap.instance?.addSource).toHaveBeenCalledWith('route-remaining', {
    type: 'geojson',
    data: {
      type: 'FeatureCollection',
      features: [],
    },
  });
});
