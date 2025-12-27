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
import along from '@turf/along';
import length from '@turf/length';
import type { Position } from '~/types';

/**
 * Project a position onto the route LineString and find its distance from start.
 * @param routeLine - The route as a Turf.js LineString feature
 * @param pos - The position to project
 * @returns The location (distance in km) along the route
 */
function getLocationOnRoute(
  routeLine: GeoJSON.Feature<GeoJSON.LineString>,
  pos: Position
): number {
  const pt = point(pos);
  const snapped = nearestPointOnLine(routeLine, pt, { units: 'kilometers' });
  return snapped.properties.location ?? 0;
}

/**
 * Interpolate a position along the route geometry between start and target positions.
 * Uses Turf.js to project positions onto the route and interpolate along the road.
 *
 * @param routeGeometry - Raw OSRM coordinates (sparse points defining the road)
 * @param startPosition - The position at the start of this animation frame
 * @param targetPosition - The position to reach by end of frame (from backend)
 * @param progress - Interpolation factor from 0 to 1
 * @returns The interpolated position snapped to the route
 */
export function interpolateAlongRoute(
  routeGeometry: Position[],
  startPosition: Position,
  targetPosition: Position,
  progress: number
): Position {
  // Need at least 2 points to form a line
  if (routeGeometry.length < 2) {
    // Fallback to linear interpolation
    return [
      startPosition[0] + (targetPosition[0] - startPosition[0]) * progress,
      startPosition[1] + (targetPosition[1] - startPosition[1]) * progress,
    ];
  }

  const routeLine = lineString(routeGeometry);

  // Project both positions onto the route to get their distances along it
  const startLocation = getLocationOnRoute(routeLine, startPosition);
  const targetLocation = getLocationOnRoute(routeLine, targetPosition);

  // Interpolate between the two locations
  const currentLocation =
    startLocation + (targetLocation - startLocation) * progress;

  // Get the point at this distance along the route
  const routeLength = length(routeLine, { units: 'kilometers' });
  const clampedLocation = Math.max(0, Math.min(currentLocation, routeLength));

  const interpolatedPoint = along(routeLine, clampedLocation, {
    units: 'kilometers',
  });

  return interpolatedPoint.geometry.coordinates as Position;
}

/**
 * Calculate progress as a fractional distance along the route.
 * Returns a value from 0 to 1 representing how far along the route the position is.
 *
 * @param routeGeometry - Raw OSRM coordinates defining the route
 * @param currentPosition - The current position to calculate progress for
 * @returns Progress from 0 (start) to 1 (end)
 */
export function calculateRouteProgress(
  routeGeometry: Position[],
  currentPosition: Position
): number {
  if (routeGeometry.length < 2) return 0;

  const routeLine = lineString(routeGeometry);
  const routeLength = length(routeLine, { units: 'kilometers' });

  if (routeLength === 0) return 0;

  const location = getLocationOnRoute(routeLine, currentPosition);
  return Math.max(0, Math.min(location / routeLength, 1));
}
