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

import { SelectedItemType } from '~/components/map/selected-item-bar';
import type { NonZeroSpeed, Speed } from '~/providers/simulation-provider';
import type { ReactiveSimulationState } from './reactive-simulation-state';
import SimulationStateManager from './simulation-state-manager';
import {
  SimulationMode,
  TaskAction,
  TaskState,
  type BackendPayload,
  type BatchAssignTasksToDriverResponse,
  type BatchAssignTasksToDriverResponseItem,
  type BatchUnassignTasksFromDriverResponse,
  type Driver,
  type Station,
  type StationTask,
  type Vehicle,
} from '~/types';
import type { Map as MapboxGLMap } from 'mapbox-gl';
import MapManager from './map-manager';
import api from '~/api';
import LocalFrameSource from './frame-sources/local-frame-source';
import ServerFrameSource from './frame-sources/server-frame-source';
import {
  calculateDayFromSeconds,
  formatSecondsToHHMM,
} from '~/utils/clock-utils';
import { toast } from 'sonner';
import { formatTranslation } from '~/lib/i18n';
import { getRuntimeTranslationTable } from '~/lib/runtime-translations';
import { logMissingEntityError } from '~/utils/simulation-error-utils';

export default class SimulationEngine {
  private simulationId: string;
  private stateManager: SimulationStateManager;
  private mapManager: MapManager;

  private mode: SimulationMode;
  private serverFrameSource: ServerFrameSource;
  private localFrameSource: LocalFrameSource;
  private pendingScrub: number | null;

  constructor(
    simulationId: string,
    map: MapboxGLMap,
    state: ReactiveSimulationState,
    setStateCallback: React.Dispatch<
      React.SetStateAction<ReactiveSimulationState>
    >
  ) {
    this.simulationId = simulationId;
    this.stateManager = new SimulationStateManager(state, setStateCallback);
    this.mapManager = new MapManager(
      map,
      this.stateManager,
      (type, id) => this.selectItem(type, id),
      (resourceId, taskIds) => this.requestAssignment(resourceId, taskIds)
    );
    this.mode = SimulationMode.Server;

    this.serverFrameSource = new ServerFrameSource(
      this.simulationId,
      (frame) => {
        this.state.setStartTime(frame.clock.startTime);
        this.state.setSimulationSecondsPassed(frame.clock.simSecondsPassed);
        this.localFrameSource.saveFrame(frame);
        if (this.mode === SimulationMode.Server) this.handleFrame(frame);
      },
      toast.error
    );
    this.localFrameSource = new LocalFrameSource(this.simulationId, (frame) => {
      this.handleFrame(frame);
      if (
        frame.clock.simSecondsPassed === this.state.getSimulationSecondsPassed()
      ) {
        // Reached live simulation point, switch to server mode
        this.localFrameSource.setSpeed(0);
        this.serverFrameSource.setSpeed(this.state.getNonZeroSpeed());
        this.mode = SimulationMode.Server;
        this.state.setBlockAssignments(false);
      }
    });
    this.pendingScrub = null;

    this.serverFrameSource.start().then(() => {
      this.state.setLoading(false);
    });
  }

  get state() {
    return this.stateManager;
  }

  // Methods to be used by UI elements
  public selectItem(type: SelectedItemType, id: number): void {
    // Get the item and validate it exists
    let item: Station | Driver | undefined = undefined;
    if (type === SelectedItemType.Station) {
      item = this.state.getStation(id);
    } else {
      item = this.state.getDriver(id);
    }
    if (!item) {
      logMissingEntityError(type, id);
      const capitalizedType = type.charAt(0).toUpperCase() + type.slice(1);
      toast.error(
        `${capitalizedType} not found: Failed to load ${type} details. Please try again later.`
      );
      return;
    }
    this.state.setSelectedItem(item);
  }

  public clearSelection(): void {
    this.state.clearSelection();
  }

  private async assignTasks(
    driverId: number,
    taskIds: number[]
  ): Promise<void> {
    if (taskIds.length === 0) return;

    const driver = this.state.getDriver(driverId);
    const tasks = taskIds.map((id) => this.state.getTask(id));

    if (!driver) throw new Error(`Driver #${driverId} not found.`);
    if (tasks.includes(undefined))
      throw new Error(`One or more tasks not found. Failed to assign tasks.`);

    let items: BatchAssignTasksToDriverResponseItem[] = [];

    try {
      const payload = { driver_id: driverId, task_ids: taskIds };
      const response = await api.post<BatchAssignTasksToDriverResponse>(
        `/simulation/${this.simulationId}/drivers/assign/batch`,
        payload
      );
      items = response.data.items;
    } catch (error) {
      const t = getRuntimeTranslationTable();
      toast.error(
        formatTranslation(t.map.assignment.errors.batchAssignmentFailed, {
          count: taskIds.length,
        })
      );
      throw error;
    }

    const successfullyAssignedTaskIds = items
      .filter((i) => i.success)
      .map((i) => i.task_id);

    // update task and previous driver for every successfully assigned task
    for (const id of successfullyAssignedTaskIds) {
      const task = this.state.getTask(id)!;
      if (task.assignedDriverId) {
        const previousDriver = this.state.getDriver(task.assignedDriverId)!;
        this.state.setDriver({
          ...previousDriver,
          taskIds: previousDriver.taskIds.filter((t) => t !== id),
        });
      }
      this.state.setTask({
        ...task,
        state: TaskState.Assigned,
        assignedDriverId: driverId,
      });
    }

    // update new driver
    this.state.setDriver({
      ...driver,
      taskIds: [...driver.taskIds, ...successfullyAssignedTaskIds],
    });

    // show failed task assignment errors if applicable
    const totalItemsCount = items.length;
    const successfulItemsCount = successfullyAssignedTaskIds.length;
    const failedItemsCount = items.length - successfulItemsCount;

    if (failedItemsCount === totalItemsCount) {
      const t = getRuntimeTranslationTable();
      toast.error(
        formatTranslation(
          totalItemsCount === 1
            ? t.map.assignment.errors.failedToAssignAllSingular
            : t.map.assignment.errors.failedToAssignAllPlural,
          { count: totalItemsCount }
        )
      );
    } else if (failedItemsCount > 0) {
      const t = getRuntimeTranslationTable();
      toast.error(
        formatTranslation(t.map.assignment.errors.assignedPartial, {
          success: successfulItemsCount,
          total: totalItemsCount,
          failed: failedItemsCount,
        })
      );
    }
  }

  private async unassignTasks(
    driverId: number,
    taskIds: number[]
  ): Promise<void> {
    if (taskIds.length === 0) return;

    const driver = this.state.getDriver(driverId);

    if (!driver) throw new Error(`Driver #${driverId} not found.`);
    let items: BatchUnassignTasksFromDriverResponse['items'] = [];

    try {
      const response = await api.post<BatchUnassignTasksFromDriverResponse>(
        `/simulation/${this.simulationId}/drivers/unassign/batch`,
        { task_ids: taskIds }
      );
      items = response.data.items;
    } catch (error) {
      const t = getRuntimeTranslationTable();
      toast.error(
        formatTranslation(t.map.assignment.errors.batchUnassignmentFailed, {
          count: taskIds.length,
        })
      );
      throw error;
    }

    const successfullyUnassignedTaskIds = items
      .filter((i) => i.success)
      .map((i) => i.task_id);

    for (const id of successfullyUnassignedTaskIds) {
      const task = this.state.getTask(id)!;
      this.state.setTask({
        ...task,
        state: TaskState.Open,
        assignedDriverId: null,
      });
    }

    this.state.setDriver({
      ...driver,
      taskIds: driver.taskIds.filter(
        (id) => !successfullyUnassignedTaskIds.includes(id)
      ),
    });

    const totalItemsCount = items.length;
    const successfulItemsCount = successfullyUnassignedTaskIds.length;
    const failedItemsCount = totalItemsCount - successfulItemsCount;

    if (failedItemsCount === totalItemsCount) {
      const t = getRuntimeTranslationTable();
      if (totalItemsCount === 1) {
        toast.error(
          formatTranslation(t.map.assignment.errors.failedToUnassignSingle, {
            taskId: taskIds[0],
          })
        );
      } else {
        toast.error(
          formatTranslation(t.map.assignment.errors.failedToUnassignAll, {
            count: totalItemsCount,
          })
        );
      }
    } else if (failedItemsCount > 0) {
      const t = getRuntimeTranslationTable();
      toast.error(
        formatTranslation(t.map.assignment.errors.unassignedPartial, {
          success: successfulItemsCount,
          total: totalItemsCount,
          failed: failedItemsCount,
        })
      );
    }
  }

  public async reorderTasks(
    driverId: number,
    taskIds: number[],
    applyFromTop: boolean
  ): Promise<void> {
    const resource = this.state.getDriver(driverId);
    if (!resource) {
      throw new Error(`Driver #${driverId} not found.`);
    }

    try {
      const payload = {
        driver_id: driverId,
        task_ids: taskIds,
        apply_from_top: applyFromTop,
      };

      const response = await api.post<{
        driver_id: number;
        task_order: number[];
      }>(`/simulation/${this.simulationId}/drivers/reorder-tasks`, payload);

      const updatedResource: Driver = {
        ...resource,
        taskIds: response.data.task_order,
      };
      this.state.setDriver(updatedResource);
    } catch (error) {
      toast.error(`Failed to reorder tasks.`);
      throw error;
    }
  }

  public toggleShowAllRoutes(): void {
    this.state.setShowAllRoutes(!this.state.getShowAllRoutes());
  }

  public toggleClusterStations(): void {
    this.state.setClusterStations(!this.state.getClusterStations());
  }

  public async setSpeed(nonZeroSpeed: NonZeroSpeed): Promise<void> {
    const prevNonZeroSpeed = this.state.getNonZeroSpeed();
    try {
      this.state.setNonZeroSpeed(nonZeroSpeed);
      if (this.state.getPaused()) return;

      if (this.mode === SimulationMode.Local) {
        await this.localFrameSource.setSpeed(nonZeroSpeed);
      } else if (this.mode === SimulationMode.Server) {
        await this.serverFrameSource.setSpeed(nonZeroSpeed);
      }
    } catch {
      // Revert to previous speed
      this.state.setNonZeroSpeed(prevNonZeroSpeed);
    }
  }

  public async setPaused(paused: boolean): Promise<void> {
    const prevPaused = this.state.getPaused();
    try {
      this.state.setPaused(paused);
      if (this.mode === SimulationMode.Local) {
        await this.localFrameSource.setSpeed(this.getFrameSourceSpeed());
      } else if (this.mode === SimulationMode.Server) {
        await this.serverFrameSource.setSpeed(this.getFrameSourceSpeed());
      }
    } catch {
      // Revert to previous paused state
      this.state.setPaused(prevPaused);
    }
  }

  public async scrub(seconds: number): Promise<void> {
    // stop sources until scrub is committed
    this.mode = SimulationMode.Scrubbing;
    this.state.setBlockAssignments(true);
    this.localFrameSource.setSpeed(0);
    this.serverFrameSource.setSpeed(0);
    this.state.setScrubSimulationSecond(seconds);

    // If frame is stored locally, simply render it
    if (this.localFrameSource.hasFrame(seconds)) {
      // Despite the await, this is expected to resolve immediately
      const targetFrame = await this.localFrameSource.getFrame(seconds);
      this.handleFrame(targetFrame, false);
      return;
    }

    this.state.setIsBuffering(true);
    if (this.pendingScrub) clearTimeout(this.pendingScrub);
    this.pendingScrub = window.setTimeout(async () => {
      // If the user hasn't moved from the current scrub position in
      // some time, assume they want us to fetch and render the frame
      // at that position
      const targetFrame = await this.localFrameSource.getFrame(seconds);
      this.handleFrame(targetFrame, false);
      this.state.setIsBuffering(false);
    }, 1000);
  }

  public async commitScrub(seconds: number): Promise<void> {
    // Implementation to commit the scrubbed time change
    // Commit scrub is practically always called from scrubbing state.
    // Under particular circumstances, the simulation provider is not
    // in scrubbing state when commitScrub is called.
    // To account for that case, we force the mode to scrubbing first.
    if (this.mode !== SimulationMode.Scrubbing) {
      console.warn(
        '[Scrub] commitScrub called outside scrubbing mode, forcing scrubbing mode'
      );
      this.scrub(seconds);
    } else {
      // Have to set it here because if paused, it wont be emitted from frame source
      this.state.setScrubSimulationSecond(seconds);
    }

    if (this.pendingScrub) clearTimeout(this.pendingScrub);
    let frame: BackendPayload;
    try {
      frame = await this.localFrameSource.getFrame(seconds);
    } catch {
      const t = getRuntimeTranslationTable();
      toast.error(t.map.scrubbing.fail);
      this.state.setIsBuffering(false);
      return;
    }
    this.handleFrame(frame, false);
    this.state.setIsBuffering(false);

    const scrubToPast = seconds !== this.state.getSimulationSecondsPassed();
    if (scrubToPast) {
      // Unpause local source to play from scrubbed position
      this.localFrameSource.setPosition(seconds);
      this.localFrameSource.setSpeed(this.getFrameSourceSpeed());
      this.mode = SimulationMode.Local;
      this.state.setBlockAssignments(true);
    } else {
      // Unpause server source to play from live position
      this.serverFrameSource.setSpeed(this.getFrameSourceSpeed());
      this.mode = SimulationMode.Server;
      this.state.setBlockAssignments(false);
    }
  }

  private handleFrame(payload: BackendPayload, animate = true) {
    this.state.setScrubSimulationSecond(payload.clock.simSecondsPassed);
    this.state.setFormattedSimTime(
      formatSecondsToHHMM(
        payload.clock.simSecondsPassed,
        payload.clock.startTime
      )
    );
    this.state.setCurrentDay(
      calculateDayFromSeconds(
        payload.clock.simSecondsPassed,
        payload.clock.startTime
      )
    );
    this.state.setHeadquarters(payload.headquarters);
    this.state.setReporting(payload.reporting);

    payload.tasks.forEach((task) => {
      this.state.setTask(task);
    });

    payload.stations.forEach((updatedStation: Station) => {
      this.state.setStation(updatedStation);
    });

    payload.vehicles.forEach((updatedVehicle: Vehicle) => {
      this.state.setVehicle(updatedVehicle);
    });

    payload.drivers.forEach((updatedDriver: Driver) => {
      this.state.setDriver(updatedDriver);
    });

    // Currently, we call updateHQWidgetState to possibly a reactive state change that HQ widget relies on.
    // We want to avoid forcing state changes from SimulationEngine if possible, but for now
    // this is more efficient than calling updateHQWidgetState from multiple places in SimulationStateManager.
    this.state.updateHQWidgetState();
    this.mapManager.processFrame(payload, animate);
  }

  public requestAssignment(driverId: number, taskIds: number[]): void {
    const targetDriver = this.state.getDriver(driverId)!; // assume the driver exists
    if (!targetDriver.vehicleId) return; // validate the driver is part of a resource
    const targetDriverVehicle = this.state.getVehicle(targetDriver.vehicleId)!; // assume the vehicle exists

    // obtain valid task objects from taskIds param
    const uniqueTaskIds = Array.from(new Set(taskIds));
    const allTasks = uniqueTaskIds
      .map((id) => this.state.getTask(id))
      .filter((t): t is StationTask => t !== undefined); // filter out non-existent tasks
    const tasks = allTasks.filter((t) => t.assignedDriverId !== driverId); // filter out tasks already assigned to this resource
    if (tasks.length === 0) {
      if (allTasks.length > 0) {
        toast.info(
          `All ${allTasks.length === 1 ? 'task is' : `${allTasks.length} tasks are`} already assigned to ${targetDriver.name}.`
        );
      }
      return;
    }

    // determine if all tasks are assigned to the same resource
    const assignedIds = tasks.map((t) => t.assignedDriverId);
    const firstAssignedId = assignedIds[0]!;
    const singleAssignedDriver = assignedIds.every(
      (id) => id !== null && id === firstAssignedId
    );

    if (singleAssignedDriver) {
      const prevDriver = this.state.getDriver(firstAssignedId)!;
      this.state.setPendingAssignment({
        action: TaskAction.Reassign,
        taskIds: tasks.map((t) => t.id),
        driverId: targetDriver.id,
        driverName: targetDriver.name,
        driverBatteryCount: targetDriverVehicle.batteryCount,
        prevDriverId: prevDriver.id,
        prevDriverName: prevDriver.name,
      });
    } else {
      const reassignCount = tasks.filter(
        (t) =>
          t.assignedDriverId !== null && t.assignedDriverId !== targetDriver.id
      ).length;
      const unassignedTaskIds = tasks
        .filter((task) => !task.assignedDriverId)
        .map((t) => t.id);
      this.state.setPendingAssignment({
        action: TaskAction.Assign,
        taskIds: tasks.map((t) => t.id),
        driverId: targetDriver.id,
        driverName: targetDriver.name,
        driverBatteryCount: targetDriverVehicle.batteryCount,
        reassignCount,
        unassignedTaskIds,
      });
    }
  }

  public requestUnassignment(
    driverId: number,
    taskIds: number[],
    stationName?: string
  ) {
    const targetDriver = this.state.getDriver(driverId)!; // assume the driver exists
    if (!targetDriver.vehicleId) return; // validate the driver is part of a resource
    const targetDriverVehicle = this.state.getVehicle(targetDriver.vehicleId)!; // assume the vehicle exists
    this.state.setPendingAssignment({
      action: TaskAction.Unassign,
      taskIds,
      driverId: targetDriver.id,
      driverName: targetDriver.name,
      driverBatteryCount: targetDriverVehicle.batteryCount,
      stationName,
    });
  }

  public async confirmAssignment(unassignedOnly = false): Promise<void> {
    const pendingAssignment = this.state.getPendingAssignment();
    if (!pendingAssignment || this.state.getPendingAssignmentLoading()) return;

    let unassignedTaskIds: number[] = [];

    if (unassignedOnly) {
      if (pendingAssignment.action !== TaskAction.Assign) return;

      unassignedTaskIds = pendingAssignment.unassignedTaskIds;
      if (unassignedTaskIds.length === 0) {
        this.state.setPendingAssignment(null);
        return;
      }
    }

    this.state.setPendingAssignmentLoading(true);

    try {
      if (pendingAssignment.action === TaskAction.Unassign) {
        await this.unassignTasks(
          pendingAssignment.driverId,
          pendingAssignment.taskIds
        );
      } else {
        await this.assignTasks(
          pendingAssignment.driverId,
          unassignedOnly ? unassignedTaskIds : pendingAssignment.taskIds
        );
      }
      this.selectItem(SelectedItemType.Driver, pendingAssignment.driverId);
    } catch (error) {
      console.error('Failed to complete task assignment action:', error);
    } finally {
      this.state.setPendingAssignment(null);
      this.state.setPendingAssignmentLoading(false);
    }
  }

  public cancelAssignment(): void {
    this.state.setPendingAssignment(null);
  }

  public setTaskHoveredStationId(stationId: number | null): void {
    this.mapManager.setTaskHoveredStationId(stationId);
  }

  public destroy(): void {
    this.mapManager.cleanup();
    this.serverFrameSource.stop();
    this.localFrameSource.setSpeed(0);
  }

  public hasStarted(): boolean {
    return !this.state.getLoading();
  }

  private getFrameSourceSpeed(): Speed {
    return this.state.getPaused() ? 0 : this.state.getNonZeroSpeed();
  }
}
