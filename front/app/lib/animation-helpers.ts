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
import type { Driver, Position, Route } from '~/types';
import { positionsEqual } from './utils';

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

// Expect to receive frames every 1 second
const BASE_FRAME_INTERVAL_MS = 1000;

/**
 * Updates driver positions for the current animation loop.
 *
 * @param drivers map of driver IDs to Driver objects
 * @param currentPositions map of driver IDs to their current positions
 * @param frameStartPositions map of driver IDs to their positions at the start of the frame
 * @param frameTargetPositions map of driver IDs to their target positions at the end of the frame
 * @param routes map of driver IDs to their current routes
 * @param lastDriverUpdates map of driver IDs to the timestamp of their last position update
 * @param speed simulation speed factor (1 = normal speed, 0 = paused)
 * @returns true if any driver positions were updated, false otherwise
 */
export function updateDriverPositions(
  drivers: Map<number, Driver>,
  currentPositions: Map<number, Position>,
  frameStartPositions: Map<number, Position>,
  frameTargetPositions: Map<number, Position>,
  routes: Map<number, Route>,
  lastDriverUpdates: Map<number, number>,
  speed: number
): boolean {
  let driverPositionsChanged = false;
  drivers.forEach((driver) => {
    const start = frameStartPositions.get(driver.id);
    const target = frameTargetPositions.get(driver.id);

    // If start / target positions aren't set, don't animate
    if (!start || !target) return;

    // Calculate interpolation progress (0 to 1)
    const now = performance.now();
    const frameElapsedMs = now - (lastDriverUpdates.get(driver.id) || 0);
    const speedAdjustedFrameInterval =
      speed === 0
        ? BASE_FRAME_INTERVAL_MS // If paused, use normal interval to avoid division by zero
        : BASE_FRAME_INTERVAL_MS / speed;
    const frameIntervalProgress = Math.min(
      frameElapsedMs / speedAdjustedFrameInterval,
      1
    );

    let currentPos: Position;
    const route = routes.get(driver.id);

    if (route) {
      // animate driver position along route geometry
      // constrain interpolation segment to next task segment only
      let constrainedRoute = route.coordinates;
      const nextStopIndex = route.nextStopIndex;
      if (nextStopIndex < constrainedRoute.length) {
        // animate only up to where the next task ends in the route
        constrainedRoute = constrainedRoute.slice(0, nextStopIndex + 1);
      }
      currentPos = interpolateAlongRoute(
        constrainedRoute,
        start,
        target,
        frameIntervalProgress
      );
    } else {
      // Fallback to linear interpolation if no route geometry
      currentPos = [
        start[0] + (target[0] - start[0]) * frameIntervalProgress,
        start[1] + (target[1] - start[1]) * frameIntervalProgress,
      ];
    }

    // Update current position if it has changed since last frame
    const prevPos = currentPositions.get(driver.id);
    if (!prevPos || !positionsEqual(prevPos, currentPos)) {
      currentPositions.set(driver.id, currentPos);
      driverPositionsChanged = true;
    }

    // If current and target are the same, clear start / target to prevent further animation
    if (positionsEqual(currentPos, target)) {
      frameStartPositions.delete(driver.id);
      frameTargetPositions.delete(driver.id);
    }

    // Update the resource object's position
    driver.position = currentPos;
  });
  return driverPositionsChanged;
}
