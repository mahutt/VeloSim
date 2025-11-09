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

import type { Resource, Station } from '~/types';

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
        taskCount: station.tasks.length,
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
  resources: Resource[],
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
        taskList: resource.taskList,
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
