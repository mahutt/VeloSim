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

import {
  SelectedItemType,
  type PopulatedDriver,
  type PopulatedStation,
  type SelectedItem,
} from '~/components/map/selected-item-bar';
import SimulationEngine from '~/lib/simulation-engine';
import {
  DEFAULT_REACTIVE_SIMULATION_STATE,
  type ReactiveSimulationState,
} from '~/lib/reactive-simulation-state';
import type { SimulationContextType } from '~/providers/simulation-provider';
import {
  DriverState,
  TaskAction,
  TaskState,
  type BackendPayload,
  type Driver,
  type Headquarters,
  type PayloadClock,
  type PendingAssignment,
  type Route,
  type SeekFrame,
  type SeekResponse,
  type Simulation,
  type Station,
  type StationTask,
  type Vehicle,
} from '~/types';
import type { ResourceItemElement } from '~/components/resource/resource-item';
import type { HQWidgetProps } from '~/components/simulation/hq-widget';

export function makePayloadClock(
  overrides: Partial<PayloadClock> = {}
): PayloadClock {
  return {
    simSecondsPassed: overrides.simSecondsPassed ?? 0,
    simMinutesPassed: overrides.simSecondsPassed ?? 0,
    realSecondsPassed: overrides.simSecondsPassed ?? 0,
    realMinutesPassed: overrides.simSecondsPassed ?? 0,
    startTime: overrides.simSecondsPassed ?? 0,
  };
}

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
    clock: overrides.clock ?? makePayloadClock(),
    reporting: overrides.reporting ?? {
      servicingToDrivingRatio: 0,
      vehicleUtilizationRatio: 0,
      averageTasksServicedPerShift: 0,
      averageTaskResponseTime: 0,
      vehicleDistanceTraveled: 0,
    },
  };
}

export function makeStation(overrides: Partial<Station> = {}): Station {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    name: overrides.name ?? `Station ${id}`,
    position: overrides.position ?? [0, 0],
    taskIds: overrides.taskIds ?? [],
  };
}

export function makePopulatedStation(
  overrides: Partial<PopulatedStation> = {}
): PopulatedStation {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    name: overrides.name ?? `Station ${id}`,
    position: overrides.position ?? [0, 0],
    tasks: overrides.tasks ?? [],
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

export function makePopulatedDriver(
  overrides: Partial<PopulatedDriver> = {}
): PopulatedDriver {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    name: overrides.name ?? `Driver ${id}`,
    position: overrides.position ?? [0, 0],
    tasks: overrides.tasks ?? [],
    route: overrides.route ?? null,
    state: overrides.state ?? DriverState.OffShift,
    inProgressTask: overrides.inProgressTask ?? null,
  };
}

export function makeVehicle(overrides: Partial<Vehicle> = {}): Vehicle {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    driverId: overrides.driverId ?? null,
    batteryCount: overrides.batteryCount ?? 0,
  } as Vehicle;
}

export function makeStationTask(
  overrides: Partial<StationTask> = {}
): StationTask {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    stationId: overrides.stationId ?? 1,
    state: overrides.state ?? TaskState.Open,
    assignedDriverId: overrides.assignedDriverId ?? null,
  };
}

export function makeSimulationContext(
  overrides: Partial<SimulationContextType> = {}
): SimulationContextType {
  return {
    state: overrides.state ?? DEFAULT_REACTIVE_SIMULATION_STATE,
    engine: overrides.engine ?? ({} as unknown as SimulationEngine),
  };
}

export function makeReactiveSimulationState(
  overrides: Partial<ReactiveSimulationState> = {}
): ReactiveSimulationState {
  return {
    ...DEFAULT_REACTIVE_SIMULATION_STATE,
    ...overrides,
  };
}

export function makeSelectedItem(
  overrides: Partial<SelectedItem> = {}
): SelectedItem {
  if (overrides.type === SelectedItemType.Driver) {
    return {
      type: SelectedItemType.Driver,
      value: (overrides.value as PopulatedDriver) ?? makePopulatedDriver(),
    };
  } else {
    return {
      type: SelectedItemType.Station,
      value: (overrides.value as PopulatedStation) ?? makePopulatedStation(),
    };
  }
}

export function makePendingAssignment(
  overrides: Partial<PendingAssignment> = {}
): PendingAssignment {
  if (overrides.action === TaskAction.Assign) {
    return {
      action: TaskAction.Assign,
      taskIds: overrides.taskIds ?? [],
      driverId: overrides.driverId ?? 1,
      driverName: overrides.driverName ?? 'Driver 1',
      driverBatteryCount: overrides.driverBatteryCount ?? 0,
      unassignedTaskIds: overrides.unassignedTaskIds ?? [],
      reassignCount: overrides.reassignCount ?? 0,
    };
  } else if (overrides.action === TaskAction.Reassign) {
    return {
      action: TaskAction.Reassign,
      taskIds: overrides.taskIds ?? [],
      driverId: overrides.driverId ?? 1,
      driverName: overrides.driverName ?? 'Driver 1',
      driverBatteryCount: overrides.driverBatteryCount ?? 0,
      prevDriverId: overrides.prevDriverId ?? 2,
      prevDriverName: overrides.prevDriverName ?? 'Driver 2',
    };
  } else {
    return {
      action: TaskAction.Unassign,
      taskIds: overrides.taskIds ?? [],
      driverId: overrides.driverId ?? 1,
      driverName: overrides.driverName ?? 'Driver 1',
      driverBatteryCount: overrides.driverBatteryCount ?? 0,
    };
  }
}

export function makeResourceItemElement(
  overrides: Partial<ResourceItemElement> = {}
): ResourceItemElement {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id,
    name: overrides.name ?? `Resource ${id}`,
    taskCount: overrides.taskCount ?? 0,
    batteryCount: overrides.batteryCount ?? 0,
    batteryCapacity: overrides.batteryCapacity ?? 100,
    state: overrides.state ?? DriverState.OffShift,
  };
}

export function makeHQWidgetProps(
  overrides: Partial<HQWidgetProps> = {}
): HQWidgetProps {
  return {
    entities: overrides.entities ?? null,
    driversAtHQ: overrides.driversAtHQ ?? [],
    driversPendingShift: overrides.driversPendingShift ?? [],
  };
}

export function makeHeadquarters(
  overrides: Partial<Headquarters> = {}
): Headquarters {
  return {
    position: overrides.position ?? [0, 0],
  };
}

export function makeSimulation(
  overrides: Partial<Simulation> = {}
): Simulation {
  const id = overrides.id ?? Math.floor(Math.random() * 10000);
  return {
    id: id,
    uuid: overrides.uuid ?? 'uuid',
    name: overrides.name ?? 'Simulation',
    user_id: overrides.user_id ?? 3,
    completed: overrides.completed ?? false,
    date_created: overrides.date_created ?? '2024-02-02T12:00:00Z',
    date_updated: overrides.date_updated ?? '2024-02-02T12:00:00Z',
    resource_count: overrides.resource_count ?? 99,
    station_count: overrides.station_count ?? 99,
    task_count: overrides.task_count ?? 99,
    completion_percentage: overrides.completion_percentage ?? 0,
  };
}

export function makeRoute(overrides: Partial<Route> = {}): Route {
  return {
    coordinates: overrides.coordinates ?? [],
    nextStopIndex: overrides.nextStopIndex ?? 0,
    trafficRanges: overrides.trafficRanges ?? [],
  };
}

export function makeSeekResponse(
  overrides: Partial<SeekResponse> = {}
): SeekResponse {
  const sim_id =
    overrides.position?.sim_id ?? `${Math.floor(Math.random() * 10000)}`;
  return {
    position: {
      sim_id: overrides.position?.sim_id ?? sim_id,
      target_sim_seconds: overrides.position?.target_sim_seconds ?? 0,
    },
    frames: {
      initial_frames: overrides.frames?.initial_frames ?? [],
      future_frames: overrides.frames?.future_frames ?? [],
      has_more_frames: overrides.frames?.has_more_frames ?? false,
    },
    state: {
      current_sim_seconds: overrides.state?.current_sim_seconds ?? 0,
      is_at_live_edge: overrides.state?.is_at_live_edge ?? false,
      playback_speed: overrides.state?.playback_speed ?? 0,
    },
  };
}

export function makeSeekFrame(overrides: Partial<SeekFrame> = {}): SeekFrame {
  return {
    sim_instance_id: overrides.sim_instance_id ?? 0,
    seq_number: overrides.seq_number ?? 0,
    sim_seconds_elapsed: overrides.sim_seconds_elapsed ?? 0,
    frame_data: overrides.frame_data ?? makePayload(),
    is_key: overrides.is_key ?? false,
    id: overrides.id ?? 0,
    created_at: overrides.created_at ?? '2024-02-02T12:00:00Z',
  };
}
