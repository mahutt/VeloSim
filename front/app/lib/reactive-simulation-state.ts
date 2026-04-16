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

import type { SelectedItem } from '~/components/map/selected-item-bar';
import type { ResourceBarElement } from '~/components/resource/resource-bar';
import type { ResourceItemElement } from '~/components/resource/resource-item';
import type { HQWidgetProps } from '~/components/simulation/hq-widget';
import type { NonZeroSpeed } from '~/providers/simulation-provider';
import type { PendingAssignment, SimulationReport } from '~/types';
import { areHQWidgetStatesEqual } from './hq-widget-helpers';

export interface ReactiveSimulationState {
  // loader
  isLoading: boolean;

  // buffer overlay
  isBuffering: boolean;

  // selected item bar
  selectedItems: SelectedItem[];
  blockAssignments: boolean;

  // task assignment banner
  pendingAssignment: PendingAssignment | null;
  pendingAssignmentLoading: boolean;

  // clock
  formattedSimTime: string;
  currentDay: number;

  // playback controls
  nonZeroSpeed: NonZeroSpeed;
  paused: boolean;

  // options
  showAllRoutes: boolean;
  clusterStations: boolean;

  // resource bar
  resourceBarElement: ResourceBarElement;

  // HQ widget
  HQWidgetState: HQWidgetProps;

  // scrubber
  startTime: number;
  simulationSecondsPassed: number;
  scrubSimulationSecond: number;

  // reporting widget
  reporting: SimulationReport;
}

export const DEFAULT_REACTIVE_SIMULATION_STATE: ReactiveSimulationState = {
  isLoading: true,
  selectedItems: [],
  isBuffering: false,
  blockAssignments: false,
  pendingAssignment: null,
  pendingAssignmentLoading: false,
  formattedSimTime: '--:--',
  currentDay: 0,
  nonZeroSpeed: 1,
  paused: false,
  showAllRoutes: false,
  clusterStations: false,
  resourceBarElement: [],
  HQWidgetState: {
    entities: null,
    driversAtHQ: [],
    driversPendingShift: [],
  },
  startTime: 0,
  simulationSecondsPassed: 0,
  scrubSimulationSecond: 0,
  reporting: {
    servicingToDrivingRatio: 0,
    vehicleUtilizationRatio: 0,
    averageTasksServicedPerShift: 0,
    averageTaskResponseTime: 0,
    vehicleDistanceTraveled: 0,
  },
};

export function areReactiveSimulationStatesEqual(
  a: ReactiveSimulationState,
  b: ReactiveSimulationState
): boolean {
  return (
    a.isLoading === b.isLoading &&
    areSelectedItemsEqual(a.selectedItems, b.selectedItems) &&
    a.isBuffering === b.isBuffering &&
    a.blockAssignments === b.blockAssignments &&
    arePendingAssignmentsEqual(a.pendingAssignment, b.pendingAssignment) &&
    a.pendingAssignmentLoading === b.pendingAssignmentLoading &&
    a.formattedSimTime === b.formattedSimTime &&
    a.currentDay === b.currentDay &&
    a.nonZeroSpeed === b.nonZeroSpeed &&
    a.paused === b.paused &&
    a.showAllRoutes === b.showAllRoutes &&
    a.clusterStations === b.clusterStations &&
    areResourceBarElementsEqual(a.resourceBarElement, b.resourceBarElement) &&
    areHQWidgetStatesEqual(a.HQWidgetState, b.HQWidgetState) &&
    a.startTime === b.startTime &&
    a.simulationSecondsPassed === b.simulationSecondsPassed &&
    a.scrubSimulationSecond === b.scrubSimulationSecond &&
    areSimulationReportsEqual(a.reporting, b.reporting)
  );
}

function areSelectedItemsEqual(a: SelectedItem[], b: SelectedItem[]): boolean {
  if (a === b) return true;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) {
    if (a[i].type !== b[i].type || a[i].value.id !== b[i].value.id)
      return false;
  }
  return true;
}

function arePendingAssignmentsEqual(
  a: PendingAssignment | null,
  b: PendingAssignment | null
): boolean {
  if (a === b) return true; // covers case where both are null or same reference
  if (!a || !b) return false; // one is null and the other isn't
  if (a.action !== b.action) return false; // different actions
  if (a.driverId !== b.driverId) return false; // different drivers
  if (a.taskIds.length !== b.taskIds.length) return false; // different number of tasks
  const sortedA = [...a.taskIds].sort();
  const sortedB = [...b.taskIds].sort();
  for (let i = 0; i < sortedA.length; i++) {
    if (sortedA[i] !== sortedB[i]) return false; // different task IDs
  }
  // We don't compare driver names since they never change
  // We don't compare battery count as we don't expect battery counts to change
  // in the time that it takes to confirm / cancel an assignment.
  // We don't compare the previous driver IDs since this is a function of the taskIds list
  return true;
}

function areResourceBarElementsEqual(
  a: ResourceBarElement,
  b: ResourceBarElement
): boolean {
  if (a.length !== b.length) return false;
  // order matters for resource bar elements since they are displayed in the order of the list
  for (let i = 0; i < a.length; i++) {
    if (!areResourceItemElementsEqual(a[i], b[i])) return false;
  }
  return true;
}

function areResourceItemElementsEqual(
  a: ResourceItemElement,
  b: ResourceItemElement
): boolean {
  return (
    a.id === b.id &&
    a.name === b.name &&
    a.taskCount === b.taskCount &&
    a.batteryCount === b.batteryCount &&
    a.batteryCapacity === b.batteryCapacity &&
    a.state === b.state
  );
}

function areSimulationReportsEqual(
  a: SimulationReport,
  b: SimulationReport
): boolean {
  return (
    a.servicingToDrivingRatio === b.servicingToDrivingRatio &&
    a.vehicleUtilizationRatio === b.vehicleUtilizationRatio &&
    a.averageTasksServicedPerShift === b.averageTasksServicedPerShift &&
    a.averageTaskResponseTime === b.averageTaskResponseTime &&
    a.vehicleDistanceTraveled === b.vehicleDistanceTraveled
  );
}
