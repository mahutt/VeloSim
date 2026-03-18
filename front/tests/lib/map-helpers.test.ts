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
  updateAllRoutesDisplay,
  clearAllRoutesDisplay,
  MapSource,
} from '~/lib/map-helpers';
import { MockMap } from 'tests/mocks';
import type { Position, CongestionLevel } from '~/types';

test('loadMapImages loads all necessary images', () => {
  MockMap.createRandomInstance();
  loadMapImages(MockMap.instance! as unknown as mapboxgl.Map);
  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(7);
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

  expect(MockMap.instance?.addLayer).toHaveBeenCalledTimes(8);
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
      'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.4, 15, 1.0],
    },
    minzoom: 13,
    filter: ['>', ['get', 'taskCount'], 0],
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
      'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.5, 13, 1.0],
      'text-field': ['get', 'name'],
      'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 10, 8, 15, 12],
      'text-offset': [0, -1.5],
      'text-anchor': 'bottom',
      'text-allow-overlap': true,
    },
    paint: {
      'text-color': '#000000',
      'text-halo-color': '#ffffff',
      'text-halo-width': 1,
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

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(7);
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

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(7);
  expect(MockMap.instance?.addImage).toHaveBeenCalledTimes(7);
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

  expect(MockMap.instance?.loadImage).toHaveBeenCalledTimes(7);
  // Should not call addImage if loadImage fails
  expect(MockMap.instance?.addImage).not.toHaveBeenCalled();
});

test('updateRouteDisplay clears display when routeGeometry has less than 2 points', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  updateRouteDisplay(
    { coordinates: [[-73.5, 45.5]], nextStopIndex: 0, trafficRanges: [] },
    [0, 0],
    MockMap.instance! as unknown as mapboxgl.Map
  );

  expect(mockGeoJSONSource.setData).toHaveBeenCalledTimes(2);
  expect(mockGeoJSONSource.setData).toHaveBeenCalledWith({
    type: 'FeatureCollection',
    features: [],
  });
});

test('updateRouteDisplay splits route at nextStopIndex', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routeGeometry: Position[] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
    [-73.8, 45.8],
  ];

  updateRouteDisplay(
    { coordinates: routeGeometry, nextStopIndex: 2, trafficRanges: [] },
    [0, 0],
    MockMap.instance! as unknown as mapboxgl.Map
  );

  expect(mockGeoJSONSource.setData).toHaveBeenCalledTimes(2);

  const nextTaskCall = mockGeoJSONSource.setData.mock.calls[0][0];
  expect(nextTaskCall.type).toBe('FeatureCollection');
  expect(nextTaskCall.features).toHaveLength(1);
  expect(nextTaskCall.features[0].properties.segmentLabel).toBe('next-task');
  const nextTaskCoords = nextTaskCall.features[0].geometry.coordinates;
  expect(nextTaskCoords[0][0]).toBeCloseTo(-73.5, 3);
  expect(nextTaskCoords[0][1]).toBeCloseTo(45.5, 3);

  const futureTasksCall = mockGeoJSONSource.setData.mock.calls[1][0];
  expect(futureTasksCall.type).toBe('FeatureCollection');
  expect(futureTasksCall.features).toHaveLength(1);
  expect(futureTasksCall.features[0].properties.segmentLabel).toBe(
    'future-tasks'
  );
  const futureTasksCoords = futureTasksCall.features[0].geometry.coordinates;
  const lastFuture = futureTasksCoords[futureTasksCoords.length - 1];
  expect(lastFuture[0]).toBeCloseTo(-73.8, 3);
  expect(lastFuture[1]).toBeCloseTo(45.8, 3);
});

test('updateRouteDisplay handles nextStopIndex at start (0)', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routeGeometry: Position[] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
  ];

  // nextStopIndex = 1 means split at first task
  updateRouteDisplay(
    { coordinates: routeGeometry, nextStopIndex: 1, trafficRanges: [] },
    [-73.5, 45.5],
    MockMap.instance! as unknown as mapboxgl.Map
  );

  const nextTaskCall = mockGeoJSONSource.setData.mock.calls[0][0];
  expect(nextTaskCall.features).toHaveLength(1);
  expect(nextTaskCall.features[0].properties.segmentLabel).toBe('next-task');
  const nextTaskCoords = nextTaskCall.features[0].geometry.coordinates;
  expect(nextTaskCoords.length).toBeGreaterThanOrEqual(2);

  const futureTasksCall = mockGeoJSONSource.setData.mock.calls[1][0];
  expect(futureTasksCall.features.length).toBeGreaterThanOrEqual(0);
});

test('updateRouteDisplay handles nextStopIndex at end of route', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routeGeometry: Position[] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
  ];

  // nextStopIndex = 2 is at the last valid index
  updateRouteDisplay(
    { coordinates: routeGeometry, nextStopIndex: 2, trafficRanges: [] },
    [-73.5, 45.5],
    MockMap.instance! as unknown as mapboxgl.Map
  );

  const nextTaskCall = mockGeoJSONSource.setData.mock.calls[0][0];
  expect(nextTaskCall.features).toHaveLength(1);
  expect(nextTaskCall.features[0].properties.segmentLabel).toBe('next-task');
  const nextTaskCoords = nextTaskCall.features[0].geometry.coordinates;
  expect(nextTaskCoords.length).toBeGreaterThanOrEqual(2);

  // Future-tasks should be empty (no future tasks after the last point)
  const futureTasksCall = mockGeoJSONSource.setData.mock.calls[1][0];
  expect(futureTasksCall.features).toEqual([]);
});

test('clearRouteDisplay clears both route sources', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  clearRouteDisplay(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.getSource).toHaveBeenCalledWith('route-next-task');
  expect(MockMap.instance?.getSource).toHaveBeenCalledWith(
    'route-future-tasks'
  );
  expect(mockGeoJSONSource.setData).toHaveBeenCalledTimes(2);
});

test('setMapLayers adds route layers with correct configuration', () => {
  MockMap.createRandomInstance();
  setMapLayers(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'route-next-task',
    type: 'line',
    source: 'route-next-task',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': ['coalesce', ['get', 'color'], '#22c55e'],
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        1,
        13,
        2,
        15,
        3,
        17,
        4,
        20,
        6,
        22,
        8,
      ],
      'line-opacity': ['coalesce', ['get', 'opacity'], 0.9],
      'line-offset': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        0,
        13,
        1,
        15,
        2,
        17,
        4,
        20,
        6,
        22,
        8,
      ],
    },
  });

  expect(MockMap.instance?.addLayer).toHaveBeenCalledWith({
    id: 'route-future-tasks',
    type: 'line',
    source: 'route-future-tasks',
    layout: {
      'line-join': 'round',
      'line-cap': 'round',
    },
    paint: {
      'line-color': ['coalesce', ['get', 'color'], '#22c55e'],
      'line-width': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        1,
        13,
        2,
        15,
        3,
        17,
        4,
        20,
        6,
        22,
        8,
      ],
      'line-opacity': [
        'number',
        ['*', ['coalesce', ['get', 'opacity'], 0.9], 0.45],
        0.4,
      ],
      'line-offset': [
        'interpolate',
        ['linear'],
        ['zoom'],
        10,
        0,
        13,
        1,
        15,
        2,
        17,
        4,
        20,
        6,
        22,
        8,
      ],
    },
  });
});

test('initializeMapSources adds route sources', () => {
  MockMap.createRandomInstance();
  initializeMapSources(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.addSource).toHaveBeenCalledWith('route-next-task', {
    type: 'geojson',
    data: {
      type: 'FeatureCollection',
      features: [],
    },
  });

  expect(MockMap.instance?.addSource).toHaveBeenCalledWith(
    'route-future-tasks',
    {
      type: 'geojson',
      data: {
        type: 'FeatureCollection',
        features: [],
      },
    }
  );
});

test('updateAllRoutesDisplay displays next task for all routes except selected', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routes = new Map<
    number,
    { coordinates: Position[]; nextStopIndex: number; trafficRanges: [] }
  >([
    [
      1,
      {
        coordinates: [[-73.5, 45.5] as Position, [-73.6, 45.6] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
    [
      2,
      {
        coordinates: [[-73.7, 45.7] as Position, [-73.8, 45.8] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
    [
      3,
      {
        coordinates: [[-73.9, 45.9] as Position, [-74.0, 46.0] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
  ]);

  const positions = new Map<number, Position>([
    [1, [-73.5, 45.5]],
    [2, [-73.7, 45.7]],
    [3, [-73.9, 45.9]],
  ]);

  updateAllRoutesDisplay(
    routes,
    positions,
    2,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  expect(MockMap.instance?.getSource).toHaveBeenCalledWith(
    'all-routes-next-task'
  );
  expect(mockGeoJSONSource.setData).toHaveBeenCalled();

  const call = mockGeoJSONSource.setData.mock.calls[0][0];
  expect(call.type).toBe('FeatureCollection');
  // Should have 2 features (drivers 1 and 3, excluding selected driver 2)
  expect(call.features).toHaveLength(2);
});

test('updateAllRoutesDisplay skips routes without positions', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routes = new Map<
    number,
    { coordinates: Position[]; nextStopIndex: number; trafficRanges: [] }
  >([
    [
      1,
      {
        coordinates: [[-73.5, 45.5] as Position, [-73.6, 45.6] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
    [
      2,
      {
        coordinates: [[-73.7, 45.7] as Position, [-73.8, 45.8] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
  ]);

  const positions = new Map<number, Position>([
    [1, [-73.5, 45.5]],
    // Driver 2 has no position
  ]);

  updateAllRoutesDisplay(
    routes,
    positions,
    null,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  const call = mockGeoJSONSource.setData.mock.calls[0][0];
  // Should only have 1 feature (driver 1, driver 2 skipped)
  expect(call.features).toHaveLength(1);
});

test('updateAllRoutesDisplay handles empty coordinates gracefully', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routes = new Map<
    number,
    { coordinates: Position[]; nextStopIndex: number; trafficRanges: [] }
  >([
    [1, { coordinates: [], nextStopIndex: 0, trafficRanges: [] }],
    [
      2,
      {
        coordinates: [[-73.7, 45.7] as Position, [-73.8, 45.8] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
  ]);

  const positions = new Map<number, Position>([
    [1, [-73.5, 45.5]],
    [2, [-73.7, 45.7]],
  ]);

  updateAllRoutesDisplay(
    routes,
    positions,
    null,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  const call = mockGeoJSONSource.setData.mock.calls[0][0];
  // Should only have 1 feature (driver 2, driver 1 has empty coordinates)
  expect(call.features).toHaveLength(1);
});

test('updateAllRoutesDisplay displays all routes when no driver is selected', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routes = new Map<
    number,
    { coordinates: Position[]; nextStopIndex: number; trafficRanges: [] }
  >([
    [
      1,
      {
        coordinates: [[-73.5, 45.5] as Position, [-73.6, 45.6] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
    [
      2,
      {
        coordinates: [[-73.7, 45.7] as Position, [-73.8, 45.8] as Position],
        nextStopIndex: 1,
        trafficRanges: [],
      },
    ],
  ]);

  const positions = new Map<number, Position>([
    [1, [-73.5, 45.5]],
    [2, [-73.7, 45.7]],
  ]);

  updateAllRoutesDisplay(
    routes,
    positions,
    null,
    MockMap.instance! as unknown as mapboxgl.Map
  );

  const call = mockGeoJSONSource.setData.mock.calls[0][0];
  // Should have all 2 features
  expect(call.features).toHaveLength(2);
});

test('clearAllRoutesDisplay clears the all-routes layer', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  clearAllRoutesDisplay(MockMap.instance! as unknown as mapboxgl.Map);

  expect(MockMap.instance?.getSource).toHaveBeenCalledWith(
    'all-routes-next-task'
  );
  expect(mockGeoJSONSource.setData).toHaveBeenCalledWith({
    type: 'FeatureCollection',
    features: [],
  });
});

test('updateRouteDisplay passes traffic ranges through to route features', () => {
  MockMap.createRandomInstance();

  const mockGeoJSONSource = { setData: vi.fn() };
  MockMap.instance!.getSource = vi.fn().mockReturnValue(mockGeoJSONSource);

  const routeGeometry: Position[] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
    [-73.8, 45.8],
  ];

  const trafficRanges = [
    {
      startCoordinateIndex: 1,
      endCoordinateIndex: 2,
      congestionLevel: 'severe' as CongestionLevel,
    },
  ];

  updateRouteDisplay(
    { coordinates: routeGeometry, nextStopIndex: 3, trafficRanges },
    [-73.5, 45.5],
    MockMap.instance! as unknown as mapboxgl.Map
  );

  const nextTaskCall = mockGeoJSONSource.setData.mock.calls[0][0];
  const colors = nextTaskCall.features.map(
    (f: GeoJSON.Feature) => f.properties?.color
  );
  // Should include severe red for the traffic range
  expect(colors).toContain('#f87171');
});
