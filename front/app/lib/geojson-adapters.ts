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
import nearestPointOnLine from '@turf/nearest-point-on-line';
import {
  FREE_FLOW_COLOR,
  MODERATE_COLOR,
  SEVERE_COLOR,
  FREE_FLOW_OPACITY,
  MODERATE_OPACITY,
  SEVERE_OPACITY,
  EMPTY_FEATURE_COLLECTION,
} from '~/constants';
import type {
  Driver,
  Station,
  Position,
  Headquarters,
  TrafficRange,
  Route,
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
  selectedStationIds: Set<number>,
  hoveredStationId: number | null,
  partiallyAssignedStationIds: ReadonlySet<number> = new Set<number>()
): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: stations.map((station) => ({
      type: 'Feature',
      properties: {
        id: station.id,
        name: station.name,
        taskCount: station.taskIds.length,
        selected: selectedStationIds.has(station.id),
        hasPartialAssignment: partiallyAssignedStationIds.has(station.id),
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
  selectedId: number | null,
  hoveredId: number | null
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
 * Ranges are assumed non-overlapping (resolved server-side). O(m log m + n).
 */
function splitByTraffic(
  coords: Position[],
  globalOffset: number,
  trafficRanges: TrafficRange[],
  segmentLabel: string
): GeoJSON.Feature[] {
  if (coords.length < 2) return [];

  if (trafficRanges.length === 0) {
    return [
      {
        type: 'Feature',
        properties: {
          segmentLabel,
          color: FREE_FLOW_COLOR,
          opacity: FREE_FLOW_OPACITY,
        },
        geometry: { type: 'LineString', coordinates: coords },
      },
    ];
  }

  const len = coords.length;

  const congestionStyle: Record<string, { color: string; opacity: number }> = {
    moderate: { color: MODERATE_COLOR, opacity: MODERATE_OPACITY },
    severe: { color: SEVERE_COLOR, opacity: SEVERE_OPACITY },
  };

  // Convert to local indices, filter out-of-bounds / free-flow, sort by start
  const localRanges = trafficRanges
    .map((r) => ({
      start: Math.max(r.startCoordinateIndex - globalOffset, 0),
      end: Math.min(r.endCoordinateIndex - globalOffset, len - 1),
      ...(congestionStyle[r.congestionLevel] ?? {
        color: FREE_FLOW_COLOR,
        opacity: FREE_FLOW_OPACITY,
      }),
    }))
    .filter((r) => r.start < len && r.end >= 0 && r.end > r.start)
    .sort((a, b) => a.start - b.start);

  const features: GeoJSON.Feature[] = [];
  let cursor = 0;

  for (const range of localRanges) {
    // Free-flow gap before this range
    if (range.start > cursor) {
      addSegment(features, coords, cursor, range.start, segmentLabel);
    }
    // Colored traffic segment
    addSegment(
      features,
      coords,
      range.start,
      range.end,
      segmentLabel,
      range.color,
      range.opacity
    );
    cursor = range.end;
  }

  // Trailing free-flow after last range
  if (cursor < len - 1) {
    addSegment(features, coords, cursor, len - 1, segmentLabel);
  }

  return features;
}

/** Push a LineString feature from coords[startIdx..endIdx]. Defaults to free-flow style. */
function addSegment(
  features: GeoJSON.Feature[],
  coords: Position[],
  startIdx: number,
  endIdx: number,
  segmentLabel: string,
  color: string = FREE_FLOW_COLOR,
  opacity: number = FREE_FLOW_OPACITY
) {
  const slice = coords.slice(startIdx, endIdx + 1);
  if (slice.length < 2) return;
  features.push({
    type: 'Feature',
    properties: { segmentLabel, color, opacity },
    geometry: { type: 'LineString', coordinates: slice },
  });
}

export function adaptRouteToGeoJSON(
  route: Route,
  position: Position
): {
  nextTask: GeoJSON.FeatureCollection;
  futureTasks: GeoJSON.FeatureCollection;
} {
  const { coordinates, nextStopIndex, trafficRanges } = route;
  if (
    coordinates.length < 2 ||
    nextStopIndex < 0 ||
    nextStopIndex > coordinates.length - 1
  ) {
    return {
      nextTask: EMPTY_FEATURE_COLLECTION,
      futureTasks: EMPTY_FEATURE_COLLECTION,
    };
  }

  // Split at nextStopIndex to avoid snapping to incorrect segment on double-back
  const preNextTaskSegment = coordinates.slice(0, nextStopIndex + 1);
  const postNextTaskSegment = coordinates.slice(nextStopIndex);

  // Trim already-travelled portion: snap driver position onto the route
  // and slice from that point forward. nearestPointOnLine gives us the
  // segment index for free, replacing the previous brute-force offset search.
  const preNextTaskLine = lineString(preNextTaskSegment);
  const snapped = nearestPointOnLine(preNextTaskLine, point(position));
  const snapIndex = snapped.properties.index;
  const snapCoord = snapped.geometry.coordinates as Position;

  const trimmedCoords: Position[] = [
    snapCoord,
    ...preNextTaskSegment.slice(snapIndex + 1),
  ];

  const nextTaskGlobalOffset = snapIndex;

  const nextTaskFeatures =
    trimmedCoords.length >= 2
      ? splitByTraffic(
          trimmedCoords,
          nextTaskGlobalOffset,
          trafficRanges,
          'next-task'
        )
      : [];

  const futureTaskFeatures =
    postNextTaskSegment.length >= 2
      ? splitByTraffic(
          postNextTaskSegment,
          nextStopIndex,
          trafficRanges,
          'future-tasks'
        )
      : [];

  return {
    nextTask: { type: 'FeatureCollection', features: nextTaskFeatures },
    futureTasks: { type: 'FeatureCollection', features: futureTaskFeatures },
  };
}
