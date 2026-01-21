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

import { makeDriver, makeVehicle } from 'tests/test-helpers';
import { describe, expect, it } from 'vitest';
import {
  driverResourceHasUpdated,
  vehicleResourceHasUpdated,
} from '~/lib/simulation-helpers';

describe('vehicleResourceHasUpdated', () => {
  it('should return true if the vehicle did not exist before but is part of a resource', () => {
    const existingVehicle = undefined;
    const updatedVehicle = makeVehicle({ driverId: 1 });
    const result = vehicleResourceHasUpdated(existingVehicle, updatedVehicle);
    expect(result).toBe(true);
  });
  it('should return true if the vehicle existed but driver assignment changed', () => {
    const existingVehicle = makeVehicle({ driverId: 1 });
    const updatedVehicle = makeVehicle({ driverId: 2 });
    const result = vehicleResourceHasUpdated(existingVehicle, updatedVehicle);
    expect(result).toBe(true);
  });
  it('should return true if the vehicle existed, is part of a resource, and battery count changed', () => {
    const existingVehicle = makeVehicle({ driverId: 1, batteryCount: 5 });
    const updatedVehicle = makeVehicle({ driverId: 1, batteryCount: 4 });
    const result = vehicleResourceHasUpdated(existingVehicle, updatedVehicle);
    expect(result).toBe(true);
  });
  it("should return false if it is part of the same resource and battery count hasn't changed", () => {
    const existingVehicle = makeVehicle({ driverId: 1, batteryCount: 5 });
    const updatedVehicle = makeVehicle({ driverId: 1, batteryCount: 5 });
    const result = vehicleResourceHasUpdated(existingVehicle, updatedVehicle);
    expect(result).toBe(false);
  });
  it("should return false if the vehicle's battery count changed, but it is not part of a resource", () => {
    const existingVehicle = makeVehicle({ driverId: null, batteryCount: 5 });
    const updatedVehicle = makeVehicle({ driverId: null, batteryCount: 4 });
    const result = vehicleResourceHasUpdated(existingVehicle, updatedVehicle);
    expect(result).toBe(false);
  });
});

describe('driverResourceHasUpdated', () => {
  it('should return true if the driver is part of a resource and task count changed', () => {
    const existingDriver = makeDriver({ id: 1, vehicleId: 1, taskIds: [1, 2] });
    const updatedDriver = makeDriver({
      id: 1,
      vehicleId: 1,
      taskIds: [1, 2, 3],
    });
    const result = driverResourceHasUpdated(existingDriver, updatedDriver);
    expect(result).toBe(true);
  });
  it('should return false if the driver is not part of a resource', () => {
    const existingDriver = makeDriver({
      id: 1,
      vehicleId: null,
      taskIds: [1, 2],
    });
    const updatedDriver = makeDriver({
      id: 1,
      vehicleId: null,
      taskIds: [1, 2, 3],
    });
    const result = driverResourceHasUpdated(existingDriver, updatedDriver);
    expect(result).toBe(false);
  });
  it('should return false if the driver is part of a resource but its task count has not changed', () => {
    const existingDriver = makeDriver({ id: 1, vehicleId: 1, taskIds: [1, 2] });
    const updatedDriver = makeDriver({ id: 1, vehicleId: 1, taskIds: [1, 2] });
    const result = driverResourceHasUpdated(existingDriver, updatedDriver);
    expect(result).toBe(false);
  });
});
