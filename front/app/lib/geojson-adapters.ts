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
import {
  FREE_FLOW_COLOR,
  MODERATE_COLOR,
  SEVERE_COLOR,
  FREE_FLOW_OPACITY,
  MODERATE_OPACITY,
  SEVERE_OPACITY,
} from '~/constants';
import type {
  Driver,
  Station,
  Position,
  Headquarters,
  TrafficRange,
} from '~/types';

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
        name: resource.name,
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

/**
 * Split a coordinate array into colored sub-segments based on traffic ranges.
 * When ranges overlap, the worst congestion level wins.
 */
function splitByTraffic(
  coords: Position[],
  globalOffset: number,
  trafficRanges: TrafficRange[],
  segmentLabel: string
): GeoJSON.Feature[] {
  if (coords.length < 2) return [];

  const defaultColor = FREE_FLOW_COLOR;
  const defaultOpacity = FREE_FLOW_OPACITY;

  if (trafficRanges.length === 0) {
    return [
      {
        type: 'Feature',
        properties: {
          segmentLabel,
          color: defaultColor,
          opacity: defaultOpacity,
        },
        geometry: { type: 'LineString', coordinates: coords },
      },
    ];
  }

  const len = coords.length;

  // Severity config – add new levels here without changing the algorithm
  const severityConfig: Record<string, number> = {
    moderate: 1,
    severe: 2,
  };

  // One diff array per severity level – O(1) per range
  const diffs = new Map<number, number[]>();
  for (const range of trafficRanges) {
    const localStart = Math.max(range.startCoordinateIndex - globalOffset, 0);
    const localEnd = Math.min(range.endCoordinateIndex - globalOffset, len - 1);
    if (localStart >= len || localEnd < 0) continue;

    const s = severityConfig[range.congestionLevel] ?? 0;
    if (s === 0) continue;

    if (!diffs.has(s)) diffs.set(s, new Array(len + 1).fill(0));
    const diff = diffs.get(s)!;
    diff[localStart]++;
    diff[localEnd + 1]--;
  }

  // Single prefix-sum pass resolves worst severity at each coordinate – O(n)
  const severity: number[] = new Array(len).fill(0);
  for (const [level, diff] of diffs) {
    let count = 0;
    for (let i = 0; i < len; i++) {
      count += diff[i];
      if (count > 0 && level > severity[i]) severity[i] = level;
    }
  }

  const severityToColor = [FREE_FLOW_COLOR, MODERATE_COLOR, SEVERE_COLOR];
  const severityToOpacity = [
    FREE_FLOW_OPACITY,
    MODERATE_OPACITY,
    SEVERE_OPACITY,
  ];
  const colors = severity.map((s) => severityToColor[s]);
  const opacities = severity.map((s) => severityToOpacity[s]);

  const features: GeoJSON.Feature[] = [];
  let runStart = 0;

  for (let i = 1; i <= len; i++) {
    if (i === len || colors[i] !== colors[runStart]) {
      const slice = coords.slice(runStart, i + (i < len ? 1 : 0));
      if (slice.length >= 2) {
        features.push({
          type: 'Feature',
          properties: {
            segmentLabel,
            color: colors[runStart],
            opacity: opacities[runStart],
          },
          geometry: { type: 'LineString', coordinates: slice },
        });
      }
      runStart = i;
    }
  }

  return features;
}

export function adaptRouteToGeoJSON(
  routeGeometry: Position[] | null,
  position: Position | null,
  nextStopIndex: number,
  trafficRanges?: TrafficRange[]
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

  // Split at nextStopIndex to avoid snapping to incorrect segment on double-back
  const preNextTaskSegment = routeGeometry.slice(0, nextStopIndex + 1);
  const postNextTaskSegment = routeGeometry.slice(nextStopIndex);

  // Trim already-travelled portion
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

  // Find the global offset by matching trimmedCoords[1] (first original point
  // after the driver) to avoid oscillation at coordinate midpoints.
  const trimmedCoords = nextTaskLine.geometry.coordinates as Position[];
  let nextTaskGlobalOffset = 0;
  if (trimmedCoords.length >= 2) {
    const [tx, ty] = trimmedCoords[1];
    let bestDist = Number.POSITIVE_INFINITY;
    for (let i = 0; i < preNextTaskSegment.length; i++) {
      const dx = preNextTaskSegment[i][0] - tx;
      const dy = preNextTaskSegment[i][1] - ty;
      const dist = dx * dx + dy * dy;
      if (dist < bestDist) {
        bestDist = dist;
        nextTaskGlobalOffset = Math.max(i - 1, 0);
      }
    }
  }

  const nextTaskFeatures = splitByTraffic(
    trimmedCoords,
    nextTaskGlobalOffset,
    trafficRanges ?? [],
    'next-task'
  );

  const futureTaskFeatures =
    postNextTaskSegment.length >= 2
      ? splitByTraffic(
          postNextTaskSegment,
          nextStopIndex,
          trafficRanges ?? [],
          'future-tasks'
        )
      : [];

  return {
    nextTask: { type: 'FeatureCollection', features: nextTaskFeatures },
    futureTasks: { type: 'FeatureCollection', features: futureTaskFeatures },
  };
}
