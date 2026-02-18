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
  type BackendPayload,
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
import { logMissingEntityError } from '~/utils/simulation-error-utils';

export default class SimulationEngine {
  private simulationId: string;
  private stateManager: SimulationStateManager;
  private mapManager: MapManager;

  private mode: SimulationMode;
  private serverFrameSource: ServerFrameSource;
  private localFrameSource: LocalFrameSource;

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
      () => this.clearSelection(),
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
    this.localFrameSource = new LocalFrameSource(
      this.simulationId,
      (frame) => {
        this.handleFrame(frame);
        if (
          frame.clock.simSecondsPassed ===
          this.state.getSimulationSecondsPassed()
        ) {
          // Reached live simulation point, switch to server mode
          this.localFrameSource.setSpeed(0);
          this.serverFrameSource.setSpeed(this.state.getNonZeroSpeed());
          this.mode = SimulationMode.Server;
        }
      },
      toast.error
    );

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
    this.state.setSelectedItem(null);
  }

  private async assignTask(driverId: number, taskId: number): Promise<void> {
    const resource = this.state.getDriver(driverId);

    if (!resource) {
      throw new Error(`Driver #${driverId} not found.`);
    }

    try {
      const payload = { task_id: taskId, driver_id: driverId };
      await api.post(
        `/simulation/${this.simulationId}/drivers/assign`,
        payload
      );

      const updatedResource = resource;
      if (!updatedResource.taskIds.includes(taskId)) {
        updatedResource.taskIds.push(taskId);
      }

      this.state.setDriver(updatedResource);
    } catch (error) {
      toast.error(`Failed to assign task ${taskId}.`);
      throw error;
    }
  }

  private async assignTasksBatch(
    driverId: number,
    taskIds: number[]
  ): Promise<void> {
    const resource = this.state.getDriver(driverId);

    if (!resource) {
      throw new Error(`Driver #${driverId} not found.`);
    }

    try {
      const payload = { driver_id: driverId, task_ids: taskIds };
      const response = await api.post<{
        items: { driver_id: number; task_id: number; success: boolean }[];
      }>(`/simulation/${this.simulationId}/drivers/assign/batch`, payload);

      const items = response.data.items;
      const successfulTaskIds = new Set(
        items.filter((item) => item.success).map((item) => item.task_id)
      );
      const failedTaskIds = items
        .filter((item) => !item.success)
        .map((item) => item.task_id);
      const totalTaskCount = items.length || taskIds.length;

      if (failedTaskIds.length > 0) {
        if (successfulTaskIds.size === 0) {
          toast.error(
            `Failed to assign ${totalTaskCount} task${totalTaskCount === 1 ? '' : 's'}.`
          );
        } else {
          toast.error(
            `Assigned ${successfulTaskIds.size} of ${totalTaskCount} tasks. ${failedTaskIds.length} failed.`
          );
        }
      }

      if (successfulTaskIds.size === 0) return;

      // add successfully assigned tasks to new driver
      const existingIds = new Set(resource.taskIds);
      const newTaskIds = [...successfulTaskIds].filter(
        (id) => !existingIds.has(id)
      );
      resource.taskIds.push(...newTaskIds);
      this.state.setDriver(resource);

      // remove successfully assigned tasks from previous driver
      for (const otherDriver of this.state.getAllDrivers()) {
        if (otherDriver.id === driverId) continue;

        const filteredTaskIds = otherDriver.taskIds.filter(
          (taskId) => !successfulTaskIds.has(taskId)
        );

        if (filteredTaskIds.length !== otherDriver.taskIds.length) {
          this.state.setDriver({
            ...otherDriver,
            taskIds: filteredTaskIds,
          });
        }
      }
    } catch (error) {
      toast.error(`Batch assignment failed. (${taskIds.length} tasks)`);
      throw error;
    }
  }

  private async unassignTask(driverId: number, taskId: number): Promise<void> {
    const resource = this.state.getDriver(driverId);
    if (!resource) {
      throw new Error(`Driver #${driverId} not found.`);
    }

    try {
      const payload = { task_id: taskId, driver_id: driverId };
      await api.post(
        `/simulation/${this.simulationId}/drivers/unassign`,
        payload
      );

      const updatedResource: Driver = {
        ...resource,
        taskIds: resource.taskIds.filter((t) => t !== taskId),
      };
      this.state.setDriver(updatedResource);
    } catch (error) {
      toast.error(`Failed to unassign task ${taskId}.`);
      throw error;
    }
  }

  private async reassignTask(
    prevDriverId: number,
    newDriverId: number,
    taskId: number
  ): Promise<void> {
    const prevResource = this.state.getDriver(prevDriverId);
    const newResource = this.state.getDriver(newDriverId);
    if (!prevResource) {
      throw new Error(`Previous driver #${prevDriverId} not found.`);
    }
    if (!newResource) {
      throw new Error(`New driver #${newDriverId} not found.`);
    }

    try {
      const payload = {
        task_id: taskId,
        old_driver_id: prevDriverId,
        new_driver_id: newDriverId,
      };

      await api.post(
        `/simulation/${this.simulationId}/drivers/reassign`,
        payload
      );

      const updatedPrevResource: Driver = {
        ...prevResource,
        taskIds: prevResource.taskIds.filter((t) => t !== taskId),
      };
      this.state.setDriver(updatedPrevResource);

      const updatedNewResource = newResource;
      if (!updatedNewResource.taskIds.includes(taskId)) {
        updatedNewResource.taskIds.push(taskId);
      }

      this.state.setDriver(updatedNewResource);
    } catch (error) {
      toast.error(`Failed to reassign task ${taskId}.`);
      throw error;
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

  public scrub(seconds: number): void {
    //   // stop sources until scrub is committed
    this.mode = SimulationMode.Scrubbing;
    this.localFrameSource.setSpeed(0);
    this.serverFrameSource.setSpeed(0);
    this.state.setScrubSimulationSecond(seconds);

    let targetFrame: BackendPayload | undefined;
    if (seconds === this.state.getSimulationSecondsPassed()) {
      targetFrame = this.localFrameSource.getMaxFrame();
    } else {
      targetFrame = this.localFrameSource.getFrame(seconds);
    }
    if (targetFrame) this.handleFrame(targetFrame, false);
  }

  public commitScrub(seconds: number): void {
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

    const scrubToPast = seconds !== this.state.getSimulationSecondsPassed();

    if (scrubToPast) {
      // Unpause local source to play from scrubbed position
      const frame = this.localFrameSource.getFrame(seconds);
      if (frame) this.handleFrame(frame, false);
      this.localFrameSource.setPosition(seconds);
      this.localFrameSource.setSpeed(this.getFrameSourceSpeed());
      this.mode = SimulationMode.Local;
    } else if (!scrubToPast) {
      // Unpause server source to play from live position
      const frame = this.localFrameSource.getMaxFrame();
      if (frame) this.handleFrame(frame, false);
      this.serverFrameSource.setSpeed(this.getFrameSourceSpeed());
      this.mode = SimulationMode.Server;
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
    const tasks = uniqueTaskIds
      .map((id) => this.state.getTask(id))
      .filter((t): t is StationTask => t !== undefined) // filter out non-existent tasks
      .filter((t) => t.assignedDriverId !== driverId); // filter out tasks already assigned to this resource
    if (tasks.length === 0) return;

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
          t.assignedDriverId !== undefined &&
          t.assignedDriverId !== targetDriver.id
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

  public requestUnassignment(driverId: number, taskId: number) {
    const targetDriver = this.state.getDriver(driverId)!; // assume the driver exists
    if (!targetDriver.vehicleId) return; // validate the driver is part of a resource
    const targetDriverVehicle = this.state.getVehicle(targetDriver.vehicleId)!; // assume the vehicle exists
    this.state.setPendingAssignment({
      action: TaskAction.Unassign,
      taskIds: [taskId],
      driverId: targetDriver.id,
      driverName: targetDriver.name,
      driverBatteryCount: targetDriverVehicle.batteryCount,
    });
  }

  public async confirmAssignment(): Promise<void> {
    const pendingAssignment = this.state.getPendingAssignment();
    if (!pendingAssignment || this.state.getPendingAssignmentLoading()) return;

    this.state.setPendingAssignmentLoading(true);

    try {
      if (pendingAssignment.action === TaskAction.Unassign) {
        await this.unassignTask(
          pendingAssignment.driverId,
          pendingAssignment.taskIds[0]
        );
      } else if (pendingAssignment.action === TaskAction.Reassign) {
        const taskIds = pendingAssignment.taskIds;
        if (taskIds.length > 1) {
          await this.assignTasksBatch(pendingAssignment.driverId, taskIds);
        } else {
          await this.reassignTask(
            pendingAssignment.prevDriverId,
            pendingAssignment.driverId,
            taskIds[0]
          );
        }
      } else {
        const taskIds = pendingAssignment.taskIds;
        if (taskIds.length > 1) {
          await this.assignTasksBatch(pendingAssignment.driverId, taskIds);
        } else {
          await this.assignTask(pendingAssignment.driverId, taskIds[0]);
        }
      }
    } catch (error) {
      console.error('Failed to complete task assignment action:', error);
    } finally {
      this.state.setPendingAssignment(null);
      this.state.setPendingAssignmentLoading(false);
    }
  }

  public async confirmUnassignedOnly() {
    const pendingAssignment = this.state.getPendingAssignment();
    if (!pendingAssignment || this.state.getPendingAssignmentLoading()) return;
    if (pendingAssignment.action !== TaskAction.Assign) return;

    const unassignedTaskIds = pendingAssignment.unassignedTaskIds;
    if (unassignedTaskIds.length === 0) {
      this.state.setPendingAssignment(null);
      return;
    }

    this.state.setPendingAssignmentLoading(true);

    try {
      if (unassignedTaskIds.length > 1) {
        await this.assignTasksBatch(
          pendingAssignment.driverId,
          unassignedTaskIds
        );
      } else {
        await this.assignTask(pendingAssignment.driverId, unassignedTaskIds[0]);
      }
    } catch (error) {
      console.error('Failed to assign unassigned tasks:', error);
    } finally {
      this.state.setPendingAssignment(null);
      this.state.setPendingAssignmentLoading(false);
    }
  }

  public cancelAssignment(): void {
    this.state.setPendingAssignment(null);
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
