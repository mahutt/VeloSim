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

import type { Driver, Vehicle, Station, StationTask } from '~/types';

/**
 *
 * @param existingVehicle the current vehicle's state, if it exists in the simulation
 * @param updatedVehicle the new vehicle object received from the most recent frame
 * @returns boolean indicating whether the resource bar should be updated to reflect vehicle changes
 */
export function vehicleResourceHasUpdated(
  existingVehicle: Vehicle | undefined,
  updatedVehicle: Vehicle
): boolean {
  return (
    // If vehicle didn't exist before but is part of a resource
    (existingVehicle === undefined && updatedVehicle.driverId !== null) ||
    // If vehicle did exist but driver assignment changed
    (existingVehicle !== undefined &&
      existingVehicle.driverId !== updatedVehicle.driverId) ||
    // If vehicle did exist and is part of a resource, but battery count changed
    (existingVehicle !== undefined &&
      existingVehicle.driverId !== null &&
      existingVehicle.batteryCount !== updatedVehicle.batteryCount)
  );
}

/**
 *
 * @param existingDriver the current driver's state, if it exists in the simulation
 * @param updatedDriver the new driver object received from the most recent frame
 * @returns boolean indicating whether the resource bar should be updated to reflect driver changes
 */
export function driverResourceHasUpdated(
  existingDriver: Driver | undefined,
  updatedDriver: Driver
): boolean {
  // If driver didn't exist before, then we update based on whether it is part of a resource
  if (existingDriver === undefined) return updatedDriver.vehicleId !== null;
  // If vehicle assignment changed
  if (existingDriver.vehicleId !== updatedDriver.vehicleId) return true;
  // If task count or state changed
  if (
    existingDriver.vehicleId !== null &&
    (existingDriver.taskIds.length !== updatedDriver.taskIds.length ||
      existingDriver.state !== updatedDriver.state)
  )
    return true;
  return false;
}

/**
 *
 * @param station the station to check for partial assignment
 * @param tasks the current map of tasks in the simulation
 * @returns boolean indicating whether the station has a mix of assigned and unassigned tasks
 */
export function isStationPartiallyAssigned(
  station: Station,
  tasks: Map<number, StationTask>
): boolean {
  let hasAssigned = false;
  let hasUnassigned = false;

  for (const taskId of station.taskIds) {
    const task = tasks.get(taskId);
    if (!task) continue;
    if (task.assignedDriverId === null) hasUnassigned = true;
    else hasAssigned = true;
    if (hasAssigned && hasUnassigned) break;
  }

  return hasAssigned && hasUnassigned;
}
