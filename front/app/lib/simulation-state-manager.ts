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

import type {
  Driver,
  Vehicle,
  Station,
  StationTask,
  Headquarters,
  PendingAssignment,
  SimulationReport,
} from '~/types';
import {
  areReactiveSimulationStatesEqual,
  type ReactiveSimulationState,
} from './reactive-simulation-state';
import { SelectedItemType } from '~/components/map/selected-item-bar';
import type { SelectedItem } from '~/components/map/selected-item-bar';
import {
  driverResourceHasUpdated,
  isStationPartiallyAssigned,
  vehicleResourceHasUpdated,
} from './simulation-helpers';
import {
  areHQWidgetStatesEqual,
  createHQWidgetState,
} from './hq-widget-helpers';
import type { NonZeroSpeed } from '~/providers/simulation-provider';
import type { ResourceBarElement } from '~/components/resource/resource-bar';

export interface SimulationStateManagerInterface {
  getDriver: (driverId: number) => Driver | undefined;
  getAllDrivers: () => Driver[];
  setDriver: (driver: Driver) => void;

  getStation: (stationId: number) => Station | undefined;
  getAllStations: () => Station[];
  setStation: (station: Station) => void;
  getPartialAssignmentStationIds: () => ReadonlySet<number>;

  getVehicle: (vehicleId: number) => Vehicle | undefined;
  getAllVehicles: () => Vehicle[];
  setVehicle: (vehicle: Vehicle) => void;

  getTask: (taskId: number) => StationTask | undefined;
  setTask: (task: StationTask) => void;

  getSelectedItems: () => SelectedItem[];
  setSelectedItem: (item: Driver | Station | null) => void;
  addSelectedStation: (stationId: number) => void;
  removeSelectedStation: (stationId: number) => void;
  toggleSelectedStation: (stationId: number) => void;
  setSelectedStations: (stationIds: number[]) => void;
  clearSelection: () => void;

  getHeadquarters: () => Headquarters | null;
  setHeadquarters: (hq: Headquarters) => void;

  getMapShouldRefresh: () => boolean;
  setMapShouldRefresh: (shouldRefresh: boolean) => void;

  // Direct wrappers around reactive state:

  getLoading: () => boolean;
  setLoading: (isLoading: boolean) => void;

  getIsBuffering: () => boolean;
  setIsBuffering: (isBuffering: boolean) => void;

  getBlockAssignments: () => boolean;
  setBlockAssignments: (block: boolean) => void;

  getPendingAssignment: () => PendingAssignment | null;
  setPendingAssignment: (assignment: PendingAssignment | null) => void;

  getPendingAssignmentLoading: () => boolean;
  setPendingAssignmentLoading: (isLoading: boolean) => void;

  getFormattedSimTime: () => string;
  setFormattedSimTime: (formattedSimTime: string) => void;

  getCurrentDay: () => number;
  setCurrentDay: (day: number) => void;

  getNonZeroSpeed: () => NonZeroSpeed;
  setNonZeroSpeed: (speed: NonZeroSpeed) => void;

  getPaused: () => boolean;
  setPaused: (paused: boolean) => void;

  getShowAllRoutes: () => boolean;
  setShowAllRoutes: (show: boolean) => void;

  getClusterStations: () => boolean;
  setClusterStations: (cluster: boolean) => void;

  getStartTime: () => number;
  setStartTime: (startTime: number) => void;

  getSimulationSecondsPassed: () => number;
  setSimulationSecondsPassed: (seconds: number) => void;

  getScrubSimulationSecond: () => number;
  setScrubSimulationSecond: (second: number) => void;

  getReporting: () => SimulationReport;
  setReporting: (reporting: SimulationReport) => void;
}

export default class SimulationStateManager implements SimulationStateManagerInterface {
  private drivers: Map<number, Driver> = new Map();
  private vehicles: Map<number, Vehicle> = new Map();
  private stations: Map<number, Station> = new Map();
  private tasks: Map<number, StationTask> = new Map();
  private partialAssignmentStationIds: Set<number> = new Set();
  private headquarters: Headquarters | null = null;
  private mapShouldRefresh: boolean = false;

  private reactiveState: ReactiveSimulationState;
  private setReactiveState: React.Dispatch<
    React.SetStateAction<ReactiveSimulationState>
  >;

  constructor(
    initialState: ReactiveSimulationState,
    setStateCallback: React.Dispatch<
      React.SetStateAction<ReactiveSimulationState>
    >
  ) {
    this.reactiveState = initialState;
    this.setReactiveState = setStateCallback;
  }

  public getLoading() {
    return this.reactiveState.isLoading;
  }

  public setLoading(isLoading: boolean) {
    this.updateReactiveState({ isLoading });
  }

  public getIsBuffering() {
    return this.reactiveState.isBuffering;
  }

  public setIsBuffering(isBuffering: boolean) {
    if (this.reactiveState.isBuffering === isBuffering) return;
    this.updateReactiveState({ isBuffering });
  }

  public getBlockAssignments() {
    return this.reactiveState.blockAssignments;
  }

  public setBlockAssignments(blockAssignments: boolean) {
    if (this.reactiveState.blockAssignments === blockAssignments) return;
    this.updateReactiveState({ blockAssignments });
  }

  public setDriver(driver: Driver) {
    const previousDriver = this.drivers.get(driver.id);
    this.drivers.set(driver.id, driver);

    // If this driver is in the selection, refresh selected items
    if (this.isSelectedById(SelectedItemType.Driver, driver.id)) {
      this.refreshSelectedItems();
    }

    // Possibily update resource bar
    if (driverResourceHasUpdated(previousDriver, driver)) {
      this.updateResourceBarElement();
    }

    this.setMapShouldRefresh(true);
  }

  public getDriver(driverId: number) {
    return this.drivers.get(driverId);
  }

  public getAllDrivers() {
    return Array.from(this.drivers.values());
  }

  public setStation(station: Station) {
    this.stations.set(station.id, station);

    // If this station is in the selection, refresh selected items
    if (this.isSelectedById(SelectedItemType.Station, station.id)) {
      this.refreshSelectedItems();
    }

    this.recomputePartialAssignmentForStation(station.id);
    this.setMapShouldRefresh(true);
  }

  public getStation(stationId: number) {
    return this.stations.get(stationId);
  }

  public getAllStations() {
    return Array.from(this.stations.values());
  }

  public getPartialAssignmentStationIds() {
    return this.partialAssignmentStationIds;
  }

  public setVehicle(vehicle: Vehicle) {
    const previousVehicle = this.vehicles.get(vehicle.id);
    this.vehicles.set(vehicle.id, vehicle);
    if (vehicleResourceHasUpdated(previousVehicle, vehicle)) {
      this.updateResourceBarElement();
    }
  }

  public getVehicle(vehicleId: number) {
    return this.vehicles.get(vehicleId);
  }

  public getAllVehicles() {
    return Array.from(this.vehicles.values());
  }

  public setTask(task: StationTask) {
    const previousTask = this.tasks.get(task.id);
    this.tasks.set(task.id, task);

    if (previousTask && previousTask.stationId !== task.stationId) {
      this.recomputePartialAssignmentForStation(previousTask.stationId);
    }
    this.recomputePartialAssignmentForStation(task.stationId);

    if (
      this.reactiveState.selectedItems.some((item) =>
        item.value.tasks.some((selectedTask) => selectedTask.id === task.id)
      )
    ) {
      this.refreshSelectedItems();
    }

    this.setMapShouldRefresh(true);
  }

  public getTask(taskId: number) {
    return this.tasks.get(taskId);
  }

  public getSelectedItems(): SelectedItem[] {
    return this.reactiveState.selectedItems;
  }

  public setSelectedItem(item: Driver | Station | null) {
    this.setPendingAssignment(null);
    this.setMapShouldRefresh(true);

    if (!item) {
      this.setSelectedItems([]);
      return;
    }

    if ('shift' in item) {
      this.setSelectedItems([this.populateDriverItem(item as Driver)]);
    } else {
      this.setSelectedItems([this.populateStationItem(item as Station)]);
    }
  }

  public getMultiSelectedStationIds(): Set<number> {
    const ids = new Set<number>();
    for (const item of this.reactiveState.selectedItems) {
      if (item.type === SelectedItemType.Station) ids.add(item.value.id);
    }
    return ids;
  }

  public addSelectedStation(stationId: number): void {
    const ids = this.getMultiSelectedStationIds();
    ids.add(stationId);
    this.updateSelectedStations(ids);
  }

  public removeSelectedStation(stationId: number): void {
    const ids = this.getMultiSelectedStationIds();
    ids.delete(stationId);
    this.updateSelectedStations(ids);
  }

  public toggleSelectedStation(stationId: number): void {
    const ids = this.getMultiSelectedStationIds();
    if (ids.has(stationId)) {
      ids.delete(stationId);
    } else {
      ids.add(stationId);
    }
    this.updateSelectedStations(ids);
  }

  public setSelectedStations(stationIds: number[]): void {
    this.updateSelectedStations(new Set(stationIds));
  }

  public clearSelection(): void {
    if (this.reactiveState.selectedItems.length === 0) return;
    this.setSelectedItems([]);
    this.setPendingAssignment(null);
    this.setMapShouldRefresh(true);
  }

  private updateSelectedStations(ids: Set<number>): void {
    this.setPendingAssignment(null);
    const items: SelectedItem[] = [];
    for (const id of ids) {
      const station = this.stations.get(id);
      if (station) items.push(this.populateStationItem(station));
    }
    this.setSelectedItems(items);
    this.setMapShouldRefresh(true);
  }

  private setSelectedItems(items: SelectedItem[]): void {
    this.updateReactiveState({ selectedItems: items });
  }

  private isSelectedById(type: SelectedItemType, id: number): boolean {
    return this.reactiveState.selectedItems.some(
      (item) => item.type === type && item.value.id === id
    );
  }

  private refreshSelectedItems(): void {
    if (this.reactiveState.selectedItems.length === 0) return;
    const refreshed: SelectedItem[] = [];
    for (const item of this.reactiveState.selectedItems) {
      if (item.type === SelectedItemType.Driver) {
        const driver = this.drivers.get(item.value.id);
        if (driver) refreshed.push(this.populateDriverItem(driver));
      } else {
        const station = this.stations.get(item.value.id);
        if (station) refreshed.push(this.populateStationItem(station));
      }
    }
    this.setSelectedItems(refreshed);
  }

  private populateDriverItem(driver: Driver): SelectedItem {
    return {
      type: SelectedItemType.Driver,
      value: {
        ...driver,
        tasks: driver.taskIds.map((id) => this.tasks.get(id)!),
        inProgressTask: driver.inProgressTaskId
          ? this.tasks.get(driver.inProgressTaskId)!
          : null,
      },
    };
  }

  private populateStationItem(station: Station): SelectedItem {
    return {
      type: SelectedItemType.Station,
      value: {
        id: station.id,
        name: station.name,
        position: station.position,
        tasks: station.taskIds.map((id) => this.tasks.get(id)!),
      },
    };
  }

  public getStartTime() {
    return this.reactiveState.startTime;
  }

  public setStartTime(startTime: number) {
    this.updateReactiveState({ startTime });
  }

  public getSimulationSecondsPassed() {
    return this.reactiveState.simulationSecondsPassed;
  }

  public setSimulationSecondsPassed(seconds: number) {
    this.updateReactiveState({ simulationSecondsPassed: seconds });
  }

  public getFormattedSimTime() {
    return this.reactiveState.formattedSimTime;
  }

  public setFormattedSimTime(formattedSimTime: string) {
    this.updateReactiveState({ formattedSimTime });
  }

  public getCurrentDay() {
    return this.reactiveState.currentDay;
  }

  public setCurrentDay(day: number) {
    this.updateReactiveState({ currentDay: day });
  }

  public getScrubSimulationSecond() {
    return this.reactiveState.scrubSimulationSecond;
  }

  public setScrubSimulationSecond(second: number) {
    this.updateReactiveState({ scrubSimulationSecond: second });
  }

  public getReporting() {
    return this.reactiveState.reporting;
  }

  public setReporting(reporting: SimulationReport) {
    this.updateReactiveState({ reporting });
  }

  public getPaused() {
    return this.reactiveState.paused;
  }

  public setPaused(paused: boolean) {
    if (this.reactiveState.paused === paused) return;
    this.updateReactiveState({ paused });
  }

  public getNonZeroSpeed() {
    return this.reactiveState.nonZeroSpeed;
  }

  public setNonZeroSpeed(nonZeroSpeed: NonZeroSpeed) {
    this.updateReactiveState({ nonZeroSpeed });
  }

  public getShowAllRoutes() {
    return this.reactiveState.showAllRoutes;
  }

  public setShowAllRoutes(showAllRoutes: boolean) {
    if (this.reactiveState.showAllRoutes !== showAllRoutes) {
      this.updateReactiveState({ showAllRoutes });
      this.setMapShouldRefresh(true);
    }
  }

  public getClusterStations() {
    return this.reactiveState.clusterStations;
  }

  public setClusterStations(clusterStations: boolean) {
    if (this.reactiveState.clusterStations !== clusterStations) {
      this.updateReactiveState({ clusterStations });
      this.setMapShouldRefresh(true);
    }
  }

  public getHeadquarters() {
    return this.headquarters;
  }

  public setHeadquarters(hq: Headquarters) {
    this.headquarters = hq;
  }

  public getMapShouldRefresh() {
    return this.mapShouldRefresh;
  }

  public setMapShouldRefresh(shouldRefresh: boolean) {
    this.mapShouldRefresh = shouldRefresh;
  }

  public getPendingAssignment() {
    return this.reactiveState.pendingAssignment;
  }

  public setPendingAssignment(pendingAssignment: PendingAssignment | null) {
    this.updateReactiveState({ pendingAssignment });
  }

  public getPendingAssignmentLoading() {
    return this.reactiveState.pendingAssignmentLoading;
  }

  public setPendingAssignmentLoading(pendingAssignmentLoading: boolean) {
    this.updateReactiveState({ pendingAssignmentLoading });
  }

  private recomputePartialAssignmentForStation(stationId: number) {
    const station = this.stations.get(stationId);
    if (station && isStationPartiallyAssigned(station, this.tasks)) {
      this.partialAssignmentStationIds.add(stationId);
    } else {
      this.partialAssignmentStationIds.delete(stationId);
    }
  }

  private updateResourceBarElement() {
    const newResourceBarElement: ResourceBarElement = [];

    for (const driver of this.getAllDrivers()) {
      if (!driver.vehicleId) continue;
      const vehicle = this.getVehicle(driver.vehicleId!);
      if (!vehicle) continue;
      newResourceBarElement.push({
        id: driver.id,
        name: driver.name,
        taskCount: driver.taskIds.length,
        batteryCount: vehicle.batteryCount,
        batteryCapacity: vehicle.batteryCapacity,
        state: driver.state,
      });
    }

    this.updateReactiveState({
      resourceBarElement: newResourceBarElement,
    });
  }

  public updateHQWidgetState() {
    const newHQState = createHQWidgetState({
      drivers: this.getAllDrivers(),
      vehicles: this.getAllVehicles(),
      simulationSeconds: this.reactiveState.scrubSimulationSecond,
      startTime: this.reactiveState.startTime,
    });

    if (!areHQWidgetStatesEqual(this.reactiveState.HQWidgetState, newHQState)) {
      this.updateReactiveState({ HQWidgetState: newHQState });
    }
  }

  public getReactiveState() {
    return this.reactiveState;
  }

  private updateReactiveState(partialState: Partial<ReactiveSimulationState>) {
    const newReactiveState = { ...this.reactiveState, ...partialState };
    if (
      !areReactiveSimulationStatesEqual(this.reactiveState, newReactiveState)
    ) {
      this.setReactiveState(newReactiveState);
    }
    this.reactiveState = { ...this.reactiveState, ...partialState };
  }
}
