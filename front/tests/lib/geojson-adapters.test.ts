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
} from '~/lib/geojson-adapters';
import type { Station, Position } from '~/types';
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
      (f) => f.properties?.segment === 'next-task'
    );
    const futureTasksFeatures = result.futureTasks.features.filter(
      (f) => f.properties?.segment === 'future-tasks'
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
      (f) => f.properties?.segment === 'next-task'
    );
    const futureTasksFeatures = result.futureTasks.features.filter(
      (f) => f.properties?.segment === 'future-tasks'
    );

    expect(nextTaskFeatures).toHaveLength(0);
    expect(futureTasksFeatures).toHaveLength(0);
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
