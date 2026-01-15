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

import { lineString, point } from '@turf/helpers';
import lineSlice from '@turf/line-slice';
import type { Driver, Station, Position, Headquarters } from '~/types';

export function adaptHeadquartersToGeoJSON(
  headquarters: Headquarters
): GeoJSON.FeatureCollection {
  return {
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
          coordinates: headquarters.position,
        },
      },
    ],
  };
}

export function adaptStationsToGeoJSON(
  stations: Station[],
  selectedStationId?: number,
  hoveredStationId?: number
): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: stations.map((station) => ({
      type: 'Feature',
      properties: {
        id: station.id,
        name: station.name,
        taskCount: station.taskIds.length,
        selected: station.id === selectedStationId,
        hover: station.id === hoveredStationId,
      },
      geometry: {
        type: 'Point',
        coordinates: station.position,
      },
    })),
  };
}

export function adaptResourcesToGeoJSON(
  resources: Driver[],
  selectedId?: number,
  hoveredId?: number
): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: resources.map((resource) => ({
      type: 'Feature',
      properties: {
        id: resource.id,
        route: resource.route?.coordinates || [],
        taskList: resource.taskIds,
        selected: resource.id === selectedId,
        hover: resource.id === hoveredId,
      },
      geometry: {
        type: 'Point',
        coordinates: resource.position,
      },
    })),
  };
}

export function adaptRouteToGeoJSON(
  routeGeometry: Position[] | null,
  position: Position | null,
  nextStopIndex: number
): {
  nextTask: GeoJSON.FeatureCollection;
  futureTasks: GeoJSON.FeatureCollection;
} {
  const emptyFeatureCollection: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: [],
  };

  if (!position || !routeGeometry || routeGeometry.length < 2) {
    return {
      nextTask: emptyFeatureCollection,
      futureTasks: emptyFeatureCollection,
    };
  }

  if (nextStopIndex < 0 || nextStopIndex > routeGeometry.length - 1) {
    return {
      nextTask: emptyFeatureCollection,
      futureTasks: emptyFeatureCollection,
    };
  }

  // 1. split the route at nextStopIndex to avoid snapping to the incorrect part of a line (due to double-backing)
  const preNextTaskSegment = routeGeometry.slice(0, nextStopIndex + 1);
  const postNextTaskSegment = routeGeometry.slice(nextStopIndex);

  // 2. remove points already travelled on preNextTaskSegment (using position)
  const nextTaskLine = lineSlice(
    point(position),
    point(routeGeometry[nextStopIndex]),
    lineString(preNextTaskSegment)
  );

  if (
    !nextTaskLine.geometry.coordinates ||
    nextTaskLine.geometry.coordinates.length < 2
  ) {
    return {
      nextTask: emptyFeatureCollection,
      futureTasks: emptyFeatureCollection,
    };
  }

  const result: {
    nextTask: GeoJSON.FeatureCollection;
    futureTasks: GeoJSON.FeatureCollection;
  } = {
    nextTask: {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { segment: 'next-task' },
          geometry: nextTaskLine.geometry,
        },
      ],
    },
    futureTasks: {
      type: 'FeatureCollection',
      features:
        postNextTaskSegment.length >= 2
          ? [
              {
                type: 'Feature',
                properties: { segment: 'future-tasks' },
                geometry: lineString(postNextTaskSegment).geometry,
              },
            ]
          : [],
    },
  };
  return result;
}
