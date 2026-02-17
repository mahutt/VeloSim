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

import { describe, expect, test } from 'vitest';
import {
  getTrafficColor,
  getTrafficOpacity,
  findNearestCoordinateIndex,
  adaptTrafficRangesToGeoJSON,
} from '~/lib/traffic-helpers';
import { CongestionLevel } from '~/types';
import type { Position, TrafficRange } from '~/types';

describe('getTrafficColor', () => {
  test('returns green for free_flow', () => {
    expect(getTrafficColor(CongestionLevel.FreeFlow)).toBe('#22c55e');
  });

  test('returns orange for moderate', () => {
    expect(getTrafficColor(CongestionLevel.Moderate)).toBe('#fbb83c');
  });

  test('returns red for severe', () => {
    expect(getTrafficColor(CongestionLevel.Severe)).toBe('#f87171');
  });

  test('returns green for unknown congestion level (default)', () => {
    expect(getTrafficColor('unknown' as CongestionLevel)).toBe('#22c55e');
  });
});

describe('getTrafficOpacity', () => {
  test('returns 0.9 for free_flow', () => {
    expect(getTrafficOpacity(CongestionLevel.FreeFlow)).toBe(0.9);
  });

  test('returns 0.95 for moderate', () => {
    expect(getTrafficOpacity(CongestionLevel.Moderate)).toBe(0.95);
  });

  test('returns 1.0 for severe', () => {
    expect(getTrafficOpacity(CongestionLevel.Severe)).toBe(1.0);
  });

  test('returns 0.9 for unknown congestion level (default)', () => {
    expect(getTrafficOpacity('unknown' as CongestionLevel)).toBe(0.9);
  });
});

describe('findNearestCoordinateIndex', () => {
  const route: Position[] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
    [-73.8, 45.8],
  ];

  test('returns 0 for empty route', () => {
    expect(findNearestCoordinateIndex([], [-73.5, 45.5])).toBe(0);
  });

  test('returns exact match index', () => {
    expect(findNearestCoordinateIndex(route, [-73.7, 45.7])).toBe(2);
  });

  test('returns nearest index for position between coordinates', () => {
    // Closer to index 1 (-73.6, 45.6)
    expect(findNearestCoordinateIndex(route, [-73.61, 45.61])).toBe(1);
  });

  test('returns first index for position nearest to start', () => {
    expect(findNearestCoordinateIndex(route, [-73.49, 45.49])).toBe(0);
  });

  test('returns last index for position nearest to end', () => {
    expect(findNearestCoordinateIndex(route, [-73.81, 45.81])).toBe(3);
  });
});

describe('adaptTrafficRangesToGeoJSON', () => {
  const routeCoords: Position[] = [
    [-73.5, 45.5],
    [-73.6, 45.6],
    [-73.7, 45.7],
    [-73.8, 45.8],
    [-73.9, 45.9],
  ];

  test('filters out free_flow ranges', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 0,
        endCoordinateIndex: 2,
        congestionLevel: CongestionLevel.FreeFlow,
      },
    ];

    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges);
    expect(result.features).toHaveLength(0);
  });

  test('returns moderate range as feature with correct color', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 1,
        endCoordinateIndex: 3,
        congestionLevel: CongestionLevel.Moderate,
      },
    ];

    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges);
    expect(result.features).toHaveLength(1);
    expect(result.features[0].properties?.color).toBe('#fbb83c');
    expect(result.features[0].properties?.congestionLevel).toBe('moderate');
    expect(
      (result.features[0].geometry as GeoJSON.LineString).coordinates
    ).toEqual([
      [-73.6, 45.6],
      [-73.7, 45.7],
      [-73.8, 45.8],
    ]);
  });

  test('returns severe range with correct color and opacity', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 0,
        endCoordinateIndex: 1,
        congestionLevel: CongestionLevel.Severe,
      },
    ];

    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges);
    expect(result.features).toHaveLength(1);
    expect(result.features[0].properties?.color).toBe('#f87171');
    expect(result.features[0].properties?.opacity).toBe(1.0);
  });

  test('respects minCoordinateIndex — skips ranges fully before it', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 0,
        endCoordinateIndex: 1,
        congestionLevel: CongestionLevel.Severe,
      },
    ];

    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges, 2);
    expect(result.features).toHaveLength(0);
  });

  test('clamps range start to minCoordinateIndex', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 1,
        endCoordinateIndex: 3,
        congestionLevel: CongestionLevel.Moderate,
      },
    ];

    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges, 2);
    expect(result.features).toHaveLength(1);
    const coords = (result.features[0].geometry as GeoJSON.LineString)
      .coordinates;
    // Should start from index 2 (minCoordinateIndex), not 1
    expect(coords[0]).toEqual([-73.7, 45.7]);
  });

  test('returns empty features for too-short segment', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 2,
        endCoordinateIndex: 2,
        congestionLevel: CongestionLevel.Severe,
      },
    ];

    // Single point slice → length < 2 → filtered out
    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges);
    expect(result.features).toHaveLength(0);
  });

  test('handles multiple ranges', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 0,
        endCoordinateIndex: 1,
        congestionLevel: CongestionLevel.Moderate,
      },
      {
        startCoordinateIndex: 3,
        endCoordinateIndex: 4,
        congestionLevel: CongestionLevel.Severe,
      },
    ];

    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges);
    expect(result.features).toHaveLength(2);
    expect(result.features[0].properties?.congestionLevel).toBe('moderate');
    expect(result.features[1].properties?.congestionLevel).toBe('severe');
  });

  test('clamps minCoordinateIndex to valid range', () => {
    const ranges: TrafficRange[] = [
      {
        startCoordinateIndex: 0,
        endCoordinateIndex: 2,
        congestionLevel: CongestionLevel.Severe,
      },
    ];

    // minCoordinateIndex beyond route length → clamped to last valid index
    const result = adaptTrafficRangesToGeoJSON(routeCoords, ranges, 100);
    expect(result.features).toHaveLength(0);
  });
});
