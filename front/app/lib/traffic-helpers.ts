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

import type { CongestionLevel, Position, TrafficRange } from '~/types';

/**
 * Get color for traffic congestion level
 */
export function getTrafficColor(congestionLevel: CongestionLevel): string {
  switch (congestionLevel) {
    case 'moderate':
      return '#fbb83c'; // Bright Orange
    case 'severe':
      return '#f87171'; // Bright Red
    case 'free_flow':
    default:
      return '#22c55e';
  }
}

/**
 * Get opacity for traffic visualization
 */
export function getTrafficOpacity(congestionLevel: CongestionLevel): number {
  switch (congestionLevel) {
    case 'severe':
      return 1.0;
    case 'moderate':
      return 0.95;
    case 'free_flow':
    default:
      return 0.9;
  }
}

/**
 * Find nearest coordinate index to a position (simple squared-distance scan).
 */
export function findNearestCoordinateIndex(
  routeCoordinates: Position[],
  position: Position
): number {
  if (!routeCoordinates.length) return 0;

  let bestIdx = 0;
  let bestDist = Number.POSITIVE_INFINITY;
  const [lon, lat] = position;

  for (let i = 0; i < routeCoordinates.length; i += 1) {
    const [x, y] = routeCoordinates[i];
    const dx = x - lon;
    const dy = y - lat;
    const dist = dx * dx + dy * dy;
    if (dist < bestDist) {
      bestDist = dist;
      bestIdx = i;
    }
  }

  return bestIdx;
}

/**
 * Convert traffic ranges to GeoJSON LineString features for map rendering
 */
export function adaptTrafficRangesToGeoJSON(
  routeCoordinates: Position[],
  trafficRanges: TrafficRange[],
  minCoordinateIndex = 0
): GeoJSON.FeatureCollection {
  const clampedMin = Math.max(
    0,
    Math.min(minCoordinateIndex, routeCoordinates.length - 1)
  );
  const features = trafficRanges
    .filter((range) => range.congestionLevel !== 'free_flow')
    .map((range) => {
      if (range.endCoordinateIndex <= clampedMin) {
        return null;
      }

      const startIndex = Math.max(range.startCoordinateIndex, clampedMin);
      const segmentCoords = routeCoordinates.slice(
        startIndex,
        range.endCoordinateIndex + 1
      );

      // Skip if segment is too short
      if (segmentCoords.length < 2) {
        return null;
      }

      return {
        type: 'Feature' as const,
        properties: {
          congestionLevel: range.congestionLevel,
          color: getTrafficColor(range.congestionLevel),
          opacity: getTrafficOpacity(range.congestionLevel),
        },
        geometry: {
          type: 'LineString' as const,
          coordinates: segmentCoords,
        },
      };
    })
    .filter((f): f is NonNullable<typeof f> => f !== null);

  return {
    type: 'FeatureCollection',
    features,
  };
}
