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

import type { Route, Resource } from '~/types';

// Backend sends position updates every 1 second
export const FRAME_INTERVAL_MS = 1000;

/**
 * Simulates backend sending position updates at regular intervals
 */
export function startMockBackend(
  routes: Route[],
  onFrame: (updates: Resource[]) => void
): () => void {
  // Track waypoint progression
  const waypointIndices = new Map<number, number>();
  routes.forEach((route) => waypointIndices.set(route.id, 0));

  const intervalId = window.setInterval(() => {
    const updates: Resource[] = [];

    routes.forEach((route) => {
      const currentIndex = waypointIndices.get(route.id)!;

      // Advance to next waypoint
      const nextIndex = (currentIndex + 1) % route.coordinates.length;
      const position = route.coordinates[nextIndex];

      // Send position update
      updates.push({
        id: route.id,
        position: position,
        taskList: [],
        routeId: route.id,
      });

      waypointIndices.set(route.id, nextIndex);
    });

    // Invoke callback with all position updates for this frame
    onFrame(updates);
  }, FRAME_INTERVAL_MS);

  return () => clearInterval(intervalId);
}
