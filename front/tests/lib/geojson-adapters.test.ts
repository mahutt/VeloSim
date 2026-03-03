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

import { describe, it, expect } from 'vitest';
import {
  adaptStationsToGeoJSON,
  adaptRouteToGeoJSON,
  adaptResourcesToGeoJSON,
  adaptHeadquartersToGeoJSON,
} from '~/lib/geojson-adapters';
import type { Station, Position, CongestionLevel } from '~/types';
import { makeDriver } from 'tests/test-helpers';

describe('adaptStationsToGeoJSON', () => {
  it('should convert an array of stations to a GeoJSON FeatureCollection', () => {
    const stations: Station[] = [
      {
        id: 1,
        name: 'Central Station',
        position: [-74.006, 40.7128],
        taskIds: [],
      },
      {
        id: 2,
        name: 'Park Station',
        position: [-73.9857, 40.7484],
        taskIds: [],
      },
    ];

    const result = adaptStationsToGeoJSON(stations);

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {
            id: 1,
            name: 'Central Station',
            taskCount: 0,
            hover: false,
            selected: false,
          },
          geometry: {
            type: 'Point',
            coordinates: [-74.006, 40.7128],
          },
        },
        {
          type: 'Feature',
          properties: {
            id: 2,
            name: 'Park Station',
            taskCount: 0,
            hover: false,
            selected: false,
          },
          geometry: {
            type: 'Point',
            coordinates: [-73.9857, 40.7484],
          },
        },
      ],
    });
  });

  it('should return an empty FeatureCollection when given an empty array', () => {
    const stations: Station[] = [];
    const result = adaptStationsToGeoJSON(stations);

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [],
    });
  });
});

describe('adaptRouteToGeoJSON', () => {
  const emptyFeatureCollection = {
    type: 'FeatureCollection',
    features: [],
  };

  it('should return empty collection when routeGeometry is null', () => {
    const result = adaptRouteToGeoJSON(null, [0, 0], 0);

    expect(result.nextTask).toEqual(emptyFeatureCollection);
    expect(result.futureTasks).toEqual(emptyFeatureCollection);
  });

  it('should return empty collection when routeGeometry has fewer than 2 points', () => {
    const result = adaptRouteToGeoJSON([[0, 0]], [0, 0], 0);

    expect(result.nextTask).toEqual(emptyFeatureCollection);
    expect(result.futureTasks).toEqual(emptyFeatureCollection);
  });

  it('should split route into next-task and future-tasks segments based on nextStopIndex', () => {
    const routeGeometry: Position[] = [
      [-74.0, 40.7],
      [-74.1, 40.8],
      [-74.2, 40.9],
      [-74.3, 41.0],
    ];
    const nextStopIndex = 2;

    const result = adaptRouteToGeoJSON(
      routeGeometry,
      [-74.0, 40.7],
      nextStopIndex
    );

    const nextTaskFeatures = result.nextTask.features.filter(
      (f) => f.properties?.segmentLabel === 'next-task'
    );
    const futureTasksFeatures = result.futureTasks.features.filter(
      (f) => f.properties?.segmentLabel === 'future-tasks'
    );

    expect(nextTaskFeatures).toHaveLength(1);
    expect(futureTasksFeatures).toHaveLength(1);

    const nextTaskGeom = nextTaskFeatures[0].geometry as GeoJSON.LineString;
    expect(nextTaskGeom.coordinates[0][0]).toBeCloseTo(-74.0, 3);
    expect(nextTaskGeom.coordinates[0][1]).toBeCloseTo(40.7, 3);

    const futureTasksGeom = futureTasksFeatures[0]
      .geometry as GeoJSON.LineString;
    const lastFuture =
      futureTasksGeom.coordinates[futureTasksGeom.coordinates.length - 1];
    expect(lastFuture[0]).toBeCloseTo(-74.3, 3);
    expect(lastFuture[1]).toBeCloseTo(41.0, 3);
  });

  it('should handle nextStopIndex beyond route length', () => {
    const routeGeometry: Position[] = [
      [-74.0, 40.7],
      [-74.1, 40.8],
    ];
    const nextStopIndex = 100;

    const result = adaptRouteToGeoJSON(
      routeGeometry,
      [-74.0, 40.7],
      nextStopIndex
    );

    const nextTaskFeatures = result.nextTask.features.filter(
      (f) => f.properties?.segmentLabel === 'next-task'
    );
    const futureTasksFeatures = result.futureTasks.features.filter(
      (f) => f.properties?.segmentLabel === 'future-tasks'
    );

    expect(nextTaskFeatures).toHaveLength(0);
    expect(futureTasksFeatures).toHaveLength(0);
  });

  it('should return empty collection when position is null', () => {
    const result = adaptRouteToGeoJSON(
      [
        [-74.0, 40.7],
        [-74.1, 40.8],
      ],
      null,
      1
    );
    expect(result.nextTask).toEqual(emptyFeatureCollection);
    expect(result.futureTasks).toEqual(emptyFeatureCollection);
  });

  it('should return empty collection when nextStopIndex is negative', () => {
    const result = adaptRouteToGeoJSON(
      [
        [-74.0, 40.7],
        [-74.1, 40.8],
      ],
      [-74.0, 40.7],
      -1
    );
    expect(result.nextTask).toEqual(emptyFeatureCollection);
    expect(result.futureTasks).toEqual(emptyFeatureCollection);
  });

  it('should produce green default color when no trafficRanges are provided', () => {
    const routeGeometry: Position[] = [
      [-74.0, 40.7],
      [-74.1, 40.8],
      [-74.2, 40.9],
    ];
    const result = adaptRouteToGeoJSON(routeGeometry, [-74.0, 40.7], 2);

    const feature = result.nextTask.features[0];
    expect(feature.properties?.color).toBe('#22c55e');
    expect(feature.properties?.opacity).toBe(0.9);
  });

  it('should color route segments by congestion level', () => {
    const routeGeometry: Position[] = [
      [-74.0, 40.7],
      [-74.1, 40.8],
      [-74.2, 40.9],
      [-74.3, 41.0],
      [-74.4, 41.1],
    ];

    const trafficRanges = [
      {
        startCoordinateIndex: 1,
        endCoordinateIndex: 2,
        congestionLevel: 'moderate' as CongestionLevel,
      },
      {
        startCoordinateIndex: 3,
        endCoordinateIndex: 4,
        congestionLevel: 'severe' as CongestionLevel,
      },
    ];

    const result = adaptRouteToGeoJSON(
      routeGeometry,
      [-74.0, 40.7],
      4,
      trafficRanges
    );

    const colors = result.nextTask.features.map((f) => f.properties?.color);

    expect(colors).toContain('#fbb83c'); // moderate = orange
    expect(colors).toContain('#f87171'); // severe = red
  });

  it('should pick worst severity when traffic ranges overlap', () => {
    const routeGeometry: Position[] = [
      [-74.0, 40.7],
      [-74.1, 40.8],
      [-74.2, 40.9],
      [-74.3, 41.0],
    ];

    const trafficRanges = [
      {
        startCoordinateIndex: 0,
        endCoordinateIndex: 2,
        congestionLevel: 'moderate' as CongestionLevel,
      },
      {
        startCoordinateIndex: 1,
        endCoordinateIndex: 3,
        congestionLevel: 'severe' as CongestionLevel,
      },
    ];

    const result = adaptRouteToGeoJSON(
      routeGeometry,
      [-74.0, 40.7],
      3,
      trafficRanges
    );

    // The overlapping region (indices 1-2) should be severe (red), not moderate
    const colors = result.nextTask.features.map((f) => f.properties?.color);
    expect(colors).toContain('#f87171'); // severe wins
  });

  it('should ignore traffic ranges that fall entirely outside coordinate array', () => {
    const routeGeometry: Position[] = [
      [-74.0, 40.7],
      [-74.1, 40.8],
      [-74.2, 40.9],
    ];

    const trafficRanges = [
      {
        startCoordinateIndex: 100,
        endCoordinateIndex: 200,
        congestionLevel: 'severe' as CongestionLevel,
      },
    ];

    const result = adaptRouteToGeoJSON(
      routeGeometry,
      [-74.0, 40.7],
      2,
      trafficRanges
    );

    // Should be all default green since the range doesn't overlap
    const colors = result.nextTask.features.map((f) => f.properties?.color);
    expect(colors).toEqual(['#22c55e']);
  });

  it('should apply traffic to future-tasks segment', () => {
    const routeGeometry: Position[] = [
      [-74.0, 40.7],
      [-74.1, 40.8],
      [-74.2, 40.9],
      [-74.3, 41.0],
      [-74.4, 41.1],
    ];

    // Traffic on the future portion (after nextStopIndex = 2)
    const trafficRanges = [
      {
        startCoordinateIndex: 3,
        endCoordinateIndex: 4,
        congestionLevel: 'severe' as CongestionLevel,
      },
    ];

    const result = adaptRouteToGeoJSON(
      routeGeometry,
      [-74.0, 40.7],
      2,
      trafficRanges
    );

    expect(result.futureTasks.features.length).toBeGreaterThanOrEqual(1);
    const futureColors = result.futureTasks.features.map(
      (f) => f.properties?.color
    );
    expect(futureColors).toContain('#f87171');
  });
});

describe('adaptHeadquartersToGeoJSON', () => {
  it('should convert headquarters to a GeoJSON FeatureCollection', () => {
    const hq = { position: [-73.5, 45.5] as Position };
    const result = adaptHeadquartersToGeoJSON(hq);

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {
            id: 'headquarters',
            name: 'Headquarters',
          },
          geometry: {
            type: 'Point',
            coordinates: [-73.5, 45.5],
          },
        },
      ],
    });
  });
});

describe('adaptStationsToGeoJSON — selection and hover', () => {
  const stations: Station[] = [
    { id: 1, name: 'A', position: [-73.5, 45.5], taskIds: [1, 2] },
    { id: 2, name: 'B', position: [-73.6, 45.6], taskIds: [3] },
  ];

  it('should set selected flag for the matching station', () => {
    const result = adaptStationsToGeoJSON(stations, 2);
    expect(result.features[0].properties?.selected).toBe(false);
    expect(result.features[1].properties?.selected).toBe(true);
  });

  it('should set hover flag for the matching station', () => {
    const result = adaptStationsToGeoJSON(stations, undefined, 1);
    expect(result.features[0].properties?.hover).toBe(true);
    expect(result.features[1].properties?.hover).toBe(false);
  });

  it('should include the correct taskCount', () => {
    const result = adaptStationsToGeoJSON(stations);
    expect(result.features[0].properties?.taskCount).toBe(2);
    expect(result.features[1].properties?.taskCount).toBe(1);
  });
});

describe('adaptResourcesToGeoJSON', () => {
  const baseDriver = makeDriver({
    id: 1,
    name: 'Vini',
    position: [-73.935, 40.73],
    taskIds: [10, 20],
    vehicleId: 5,
  });

  it('should include driver name in GeoJSON properties', () => {
    const result = adaptResourcesToGeoJSON([baseDriver]);

    expect(result.features).toHaveLength(1);
    expect(result.features[0].properties).toEqual(
      expect.objectContaining({ name: baseDriver.name })
    );
  });

  it('should convert drivers to a GeoJSON FeatureCollection with all properties', () => {
    const result = adaptResourcesToGeoJSON([baseDriver]);

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {
            id: baseDriver.id,
            name: baseDriver.name,
            route: [],
            taskList: baseDriver.taskIds,
            selected: false,
            hover: false,
          },
          geometry: {
            type: 'Point',
            coordinates: baseDriver.position,
          },
        },
      ],
    });
  });

  it('should mark the selected resource', () => {
    const result = adaptResourcesToGeoJSON([baseDriver], baseDriver.id);

    expect(result.features[0].properties).toEqual(
      expect.objectContaining({ selected: true, hover: false })
    );
  });

  it('should mark the hovered resource', () => {
    const result = adaptResourcesToGeoJSON(
      [baseDriver],
      undefined,
      baseDriver.id
    );

    expect(result.features[0].properties).toEqual(
      expect.objectContaining({ selected: false, hover: true })
    );
  });

  it('should return an empty FeatureCollection when given an empty array', () => {
    const result = adaptResourcesToGeoJSON([]);

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [],
    });
  });

  it('should include route coordinates when driver has a route', () => {
    const routeCoordinates: Position[] = [
      [-73.935, 40.73],
      [-73.94, 40.74],
    ];
    const driverWithRoute = makeDriver({
      ...baseDriver,
      route: { coordinates: routeCoordinates, nextStopIndex: 1 },
    });

    const result = adaptResourcesToGeoJSON([driverWithRoute]);

    expect(result.features[0].properties).toEqual(
      expect.objectContaining({ route: routeCoordinates })
    );
  });
});
