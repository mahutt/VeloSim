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

import { featureCollection, lineString, point } from '@turf/helpers';
import nearestPointOnLine from '@turf/nearest-point-on-line';
import { distance } from '@turf/distance';
import { circle } from '@turf/circle';
import type {
  Feature,
  FeatureCollection,
  LineString,
  Point,
  Polygon,
} from 'geojson';
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
import type { AnyProps } from 'supercluster';

export function adaptHeadquartersToGeoJSON(
  headquarters: Headquarters
): FeatureCollection<Point> {
  return featureCollection([
    point(headquarters.position, {
      id: 'headquarters',
      name: 'Headquarters',
    }),
  ]);
}

export function adaptStationsToGeoJSON(
  stations: Station[],
  selectedStationIds: Set<number>,
  hoveredStationId: number | null,
  taskHoveredStationId: number | null,
  partiallyAssignedStationIds: ReadonlySet<number> = new Set<number>()
): FeatureCollection<Point, AnyProps> {
  return featureCollection(
    stations.map((station) =>
      point(station.position, {
        id: station.id,
        name: station.name,
        taskCount: station.taskIds.length,
        selected: selectedStationIds.has(station.id),
        hasPartialAssignment: partiallyAssignedStationIds.has(station.id),
        hover: station.id === hoveredStationId,
        taskHover: station.id === taskHoveredStationId,
      })
    )
  );
}

export function adaptClustersToGeoJSON(
  clusters: Feature<Point>[],
  hoveredId: number | null
): FeatureCollection<Polygon> {
  const features: Feature<Polygon>[] = [];
  for (const cluster of clusters) {
    const center = point(cluster.geometry.coordinates);
    const stationPoints = cluster.properties!.stationPoints as Position[];
    const radius = Math.max(
      ...stationPoints.map((p) =>
        distance(center, point(p), { units: 'kilometers' })
      )
    );
    const feature = circle(center, radius, {
      steps: 64,
      units: 'kilometers',
      properties: {
        ...cluster.properties,
        hover: cluster.properties!.cluster_id === hoveredId,
      },
    });
    features.push(feature);
  }
  return featureCollection(features);
}

export function adaptClusterCentroidsToGeoJSON(
  centroids: Feature<Point>[],
  hoveredId: number | null
): FeatureCollection<Point> {
  return featureCollection(
    centroids.map((c) => {
      const clusterId = c.properties!.cluster_id;
      c.properties!.hover = clusterId === hoveredId;
      return c;
    })
  );
}

export function adaptResourcesToGeoJSON(
  resources: Driver[],
  selectedId: number | null,
  hoveredId: number | null,
  bearings: Map<number, number>
): FeatureCollection<Point> {
  return featureCollection(
    resources.map((resource) =>
      point(resource.position, {
        id: resource.id,
        name: resource.name,
        state: resource.state,
        selected: resource.id === selectedId,
        hover: resource.id === hoveredId,
        bearing: bearings.get(resource.id) ?? 0,
      })
    )
  );
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
): Feature<LineString>[] {
  if (coords.length < 2) return [];

  if (trafficRanges.length === 0) {
    return [
      lineString(coords, {
        segmentLabel,
        color: FREE_FLOW_COLOR,
        opacity: FREE_FLOW_OPACITY,
      }),
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

  const features: Feature<LineString>[] = [];
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
  features: Feature<LineString>[],
  coords: Position[],
  startIdx: number,
  endIdx: number,
  segmentLabel: string,
  color: string = FREE_FLOW_COLOR,
  opacity: number = FREE_FLOW_OPACITY
) {
  const slice = coords.slice(startIdx, endIdx + 1);
  if (slice.length < 2) return;
  features.push(lineString(slice, { segmentLabel, color, opacity }));
}

export function adaptRouteToGeoJSON(
  route: Route,
  position: Position
): {
  nextTask: FeatureCollection<LineString>;
  futureTasks: FeatureCollection<LineString>;
} {
  const { coordinates, nextStopIndex, trafficRanges } = route;
  if (
    coordinates.length < 2 ||
    nextStopIndex < 0 ||
    nextStopIndex > coordinates.length - 1
  ) {
    return {
      nextTask: EMPTY_FEATURE_COLLECTION as FeatureCollection<LineString>,
      futureTasks: EMPTY_FEATURE_COLLECTION as FeatureCollection<LineString>,
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
    nextTask: featureCollection(nextTaskFeatures),
    futureTasks: featureCollection(futureTaskFeatures),
  };
}
