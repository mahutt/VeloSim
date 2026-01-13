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

import { vi } from 'vitest';
import type { SimulationContextType } from '~/providers/simulation-provider';
import {
  DriverState,
  type BackendPayload,
  type Driver,
  type Vehicle,
} from '~/types';

export function makePayload(
  overrides: Partial<BackendPayload> = {}
): BackendPayload {
  return {
    simId: overrides.simId ?? 'test-sim-id',
    headquarters: overrides.headquarters ?? {
      position: [0, 0],
    },
    tasks: overrides.tasks ?? [],
    stations: overrides.stations ?? [],
    drivers: overrides.drivers ?? [],
    vehicles: overrides.vehicles ?? [],
    clock: overrides.clock ?? {
      simSecondsPassed: 0,
      simMinutesPassed: 0,
      realSecondsPassed: 0,
      realMinutesPassed: 0,
      startTime: Date.now(),
    },
  };
}

export function makeDriver(overrides: Partial<Driver> = {}): Driver {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    name: overrides.name ?? `Driver ${id}`,
    position: overrides.position ?? [0, 0],
    taskIds: overrides.taskIds ?? [],
    state: overrides.state ?? DriverState.OffShift,
    shift: overrides.shift ?? { startTime: 3600, endTime: 7200 },
    inProgressTaskId: overrides.inProgressTaskId ?? null,
    vehicleId: overrides.vehicleId ?? null,
    route: overrides.route,
  } as Driver;
}

export function makeVehicle(overrides: Partial<Vehicle> = {}): Vehicle {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    driverId: overrides.driverId ?? null,
    batteryCount: overrides.batteryCount ?? 0,
  } as Vehicle;
}

export function makeSimulationContext(
  overrides: Partial<SimulationContextType> = {}
): SimulationContextType {
  return {
    speedRef: overrides.speedRef ?? { current: 1 },
    stationsRef: overrides.stationsRef ?? { current: new Map() },
    driversRef: overrides.driversRef ?? { current: new Map() },
    resourceBarElement: overrides.resourceBarElement ?? [],
    selectedItem: overrides.selectedItem ?? null,
    selectItem: overrides.selectItem ?? vi.fn(),
    clearSelection: overrides.clearSelection ?? vi.fn(),
    assignTask: overrides.assignTask ?? vi.fn(),
    unassignTask: overrides.unassignTask ?? vi.fn(),
    reassignTask: overrides.reassignTask ?? vi.fn(),
    reorderTasks: overrides.reorderTasks ?? vi.fn(),
    simId: overrides.simId ?? null,
    isConnected: overrides.isConnected ?? false,
    simulationStatus: overrides.simulationStatus ?? 'idle',
    isLoading: overrides.isLoading ?? false,
    formattedSimTime: overrides.formattedSimTime ?? null,
    currentDay: overrides.currentDay ?? 1,
    HQWidgetState: overrides.HQWidgetState ?? {
      entities: null,
      driversAtHQ: [],
      driversPendingShift: [],
    },
  };
}
