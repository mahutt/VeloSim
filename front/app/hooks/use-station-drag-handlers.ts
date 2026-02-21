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

import { useEffect } from 'react';
import { toast } from 'sonner';
import { useMap } from '~/providers/map-provider';
import { useSimulation } from '~/providers/simulation-provider';
import { useTaskAssignment } from '~/providers/task-assignment-provider';
import { setupStationDragHandlers } from '~/lib/map-interactions';
import { log, LogLevel } from '~/lib/logger';

/**
 * Hook that enables dragging a station icon on the map onto a driver icon
 * to batch-assign all open tasks from that station to the driver.
 */
export function useStationDragHandlers() {
  const { mapRef, mapLoaded } = useMap();
  const { stationsRef, driversRef, updateHoverState, setHoverLocked } =
    useSimulation();
  const { requestAssignment } = useTaskAssignment();

  useEffect(() => {
    if (!mapLoaded || !mapRef.current) return;

    const cleanup = setupStationDragHandlers(
      mapRef.current,
      (stationId, driverId) => {
        const station = stationsRef.current.get(stationId);
        if (!station) {
          toast.error(`Station #${stationId} not found.`);
          log({
            message: `Failed to drag station #${stationId} onto driver because station was not found`,
            level: LogLevel.ERROR,
            context: 'station_drag_drop',
          });
          return;
        }

        const driver = driversRef.current.get(driverId);
        if (!driver) {
          toast.error(`Driver #${driverId} not found.`);
          log({
            message: `Failed to drag station #${stationId} onto driver #${driverId} because driver was not found`,
            level: LogLevel.ERROR,
            context: 'station_drag_drop',
          });
          return;
        }

        const openTaskIds = station.taskIds;

        if (openTaskIds.length === 0) {
          toast.info(`No tasks at ${station.name}.`);
          return;
        }

        requestAssignment(driverId, openTaskIds);
        log({
          message: `Dragged station #${stationId} onto driver #${driverId} to assign ${openTaskIds.length} tasks`,
          level: LogLevel.INFO,
          context: 'station_drag_drop',
        });
      },
      (stationId) => {
        if (stationId !== null) {
          updateHoverState(stationId, null);
          setHoverLocked(true);
        } else {
          setHoverLocked(false);
          updateHoverState(null, null);
        }
      }
    );

    return cleanup;
  }, [mapLoaded, requestAssignment]);
}
