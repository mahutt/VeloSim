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
import along from '@turf/along';
import length from '@turf/length';
import lineSlice from '@turf/line-slice';
import type { Driver, Station } from '~/types';

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
  routeGeometry: [number, number][] | null,
  progress: number
): {
  traversed: GeoJSON.FeatureCollection;
  remaining: GeoJSON.FeatureCollection;
} {
  const emptyFeatureCollection: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: [],
  };

  if (!routeGeometry || routeGeometry.length < 2) {
    return {
      traversed: emptyFeatureCollection,
      remaining: emptyFeatureCollection,
    };
  }

  // Progress is now fractional (0-1), use Turf.js for precise line slicing
  const routeLine = lineString(routeGeometry);
  const totalLength = length(routeLine, { units: 'kilometers' });
  const currentDistance = progress * totalLength;

  // Get the current position on the route
  const currentPoint = along(routeLine, currentDistance, {
    units: 'kilometers',
  });
  const startPoint = point(routeGeometry[0]);
  const endPoint = point(routeGeometry[routeGeometry.length - 1]);

  let traversed: GeoJSON.FeatureCollection = emptyFeatureCollection;
  let remaining: GeoJSON.FeatureCollection = emptyFeatureCollection;

  try {
    // Slice the route into traversed and remaining portions
    if (currentDistance > 0.001) {
      const traversedLine = lineSlice(startPoint, currentPoint, routeLine);
      if (traversedLine.geometry.coordinates.length >= 2) {
        traversed = {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              properties: {},
              geometry: traversedLine.geometry,
            },
          ],
        };
      }
    }

    if (currentDistance < totalLength - 0.001) {
      const remainingLine = lineSlice(currentPoint, endPoint, routeLine);
      if (remainingLine.geometry.coordinates.length >= 2) {
        remaining = {
          type: 'FeatureCollection',
          features: [
            {
              type: 'Feature',
              properties: {},
              geometry: remainingLine.geometry,
            },
          ],
        };
      }
    }
  } catch {
    // Fallback if slicing fails - show entire route as remaining
    remaining = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {},
          geometry: { type: 'LineString', coordinates: routeGeometry },
        },
      ],
    };
  }

  return { traversed, remaining };
}
