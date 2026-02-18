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
  makeDriver,
  makePayload,
  makePendingAssignment,
  makeReactiveSimulationState,
  makeStation,
  makeStationTask,
  makeVehicle,
} from 'tests/test-helpers';
import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import api from '~/api';

import { SelectedItemType } from '~/components/map/selected-item-bar';
import SimulationEngine from '~/lib/simulation-engine';
import { SimulationMode, TaskAction } from '~/types';
import { logMissingEntityError } from '~/utils/simulation-error-utils';

const {
  MockMapManager,
  mockSimulationStateManager,
  MockSimulationStateManager,
  mockLocalFrameSource,
  MockLocalFrameSource,
  mockServerFrameSource,
  MockServerFrameSource,
} = await vi.hoisted(async () => await import('tests/mocks'));
vi.mock('~/lib/map-manager', () => ({
  default: MockMapManager,
}));
vi.mock('~/lib/simulation-state-manager', () => ({
  default: MockSimulationStateManager,
}));
vi.mock('~/lib/frame-sources/local-frame-source', () => ({
  default: MockLocalFrameSource,
}));
vi.mock('~/lib/frame-sources/server-frame-source', () => ({
  default: MockServerFrameSource,
}));
vi.mock('~/utils/simulation-error-utils', () => ({
  logMissingEntityError: vi.fn(),
}));
vi.mock('~/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockMap = {} as unknown as mapboxgl.Map;

describe('SimulationEngine', () => {
  let engine: SimulationEngine;

  beforeEach(() => {
    vi.clearAllMocks();
    engine = new SimulationEngine(
      'test_simulation',
      mockMap,
      makeReactiveSimulationState(),
      () => {}
    );
  });

  it('instantiates map manager, simulation state manager, and server frame source on creation', async () => {
    expect(MockMapManager).toHaveBeenCalledTimes(1);
    expect(MockSimulationStateManager).toHaveBeenCalledTimes(1);
    expect(MockServerFrameSource).toHaveBeenCalledTimes(1);
  });

  describe('selectItem', () => {
    it("calls state manager's setSelectedItem for the right station", () => {
      const station = makeStation({ id: 1 });
      (mockSimulationStateManager.getStation as Mock).mockReturnValue(station);

      engine.selectItem(SelectedItemType.Station, 1);

      expect(mockSimulationStateManager.setSelectedItem).toHaveBeenCalledWith(
        station
      );
    });
    it("calls state manager's setSelectedItem for the right driver", () => {
      const driver = makeDriver({ id: 1 });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(driver);

      engine.selectItem(SelectedItemType.Driver, 1);

      expect(mockSimulationStateManager.setSelectedItem).toHaveBeenCalledWith(
        driver
      );
    });
    it("calls logMissingEntityError if the entity doesn't exist", () => {
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(undefined);
      engine.selectItem(SelectedItemType.Driver, 1);
      expect(mockSimulationStateManager.setSelectedItem).not.toHaveBeenCalled();
      expect(logMissingEntityError).toHaveBeenCalled();
    });
  });

  describe('clearSelection', () => {
    it("calls state manager's setSelectedItem with null", () => {
      engine.clearSelection();
      expect(mockSimulationStateManager.setSelectedItem).toHaveBeenCalledWith(
        null
      );
    });
  });

  describe('reorderTasks', () => {
    it('throws error if driver id is invalid', async () => {
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(undefined);
      await expect(engine.reorderTasks(1, [1], false)).rejects.toThrow();
    });
    it('updates the task order of the driver in the state manager', async () => {
      const driver = makeDriver({ id: 1, taskIds: [1, 2, 3] });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(driver);
      (api.post as Mock).mockResolvedValue({ data: { task_order: [3, 2, 1] } });
      await engine.reorderTasks(1, [3, 2, 1], false);
      expect(mockSimulationStateManager.setDriver).toHaveBeenCalledWith({
        ...driver,
        taskIds: [3, 2, 1],
      });
    });
    it('rethrows error if API call fails', async () => {
      const driver = makeDriver({ id: 1, taskIds: [1, 2, 3] });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(driver);
      (api.post as Mock).mockRejectedValue(new Error('API error'));
      await expect(engine.reorderTasks(1, [3, 2, 1], false)).rejects.toThrow(
        'API error'
      );
    });
  });

  describe('toggleShowAllRoutes', () => {
    it('toggles the showAllRoutes property in the state manager', () => {
      const initialShowAllRoutes = false;
      (mockSimulationStateManager.getShowAllRoutes as Mock).mockReturnValue(
        initialShowAllRoutes
      );
      engine.toggleShowAllRoutes();
      expect(mockSimulationStateManager.setShowAllRoutes).toHaveBeenCalledWith(
        !initialShowAllRoutes
      );
    });
  });

  describe('setSpeed', () => {
    beforeEach(() => {
      (mockSimulationStateManager.getNonZeroSpeed as Mock).mockReturnValue(1);
    });
    it('sets the speed in the state manager', () => {
      engine.setSpeed(2);
      expect(mockSimulationStateManager.setNonZeroSpeed).toHaveBeenCalledWith(
        2
      );
    });
    it('reverts the speed change in the state manager if serverFrameSource.setSpeed throws an error', async () => {
      (mockServerFrameSource.setSpeed as Mock).mockRejectedValue(
        new Error('API error')
      );
      engine['mode'] = SimulationMode.Server;
      await engine.setSpeed(2);
      expect(mockSimulationStateManager.setNonZeroSpeed).toHaveBeenCalledWith(
        2
      );
      expect(mockSimulationStateManager.setNonZeroSpeed).toHaveBeenCalledWith(
        1
      );
    });
  });

  describe('setPaused', () => {
    beforeEach(() => {
      (mockSimulationStateManager.getPaused as Mock).mockReturnValue(false);
    });
    it('sets the paused state in the state manager', () => {
      engine.setPaused(true);
      expect(mockSimulationStateManager.setPaused).toHaveBeenCalledWith(true);
    });
    it('reverts the paused state in the state manager if serverFrameSource.setSpeed throws an error', async () => {
      (mockServerFrameSource.setSpeed as Mock).mockRejectedValue(
        new Error('API error')
      );
      engine['mode'] = SimulationMode.Server;
      await engine.setPaused(true);
      expect(mockSimulationStateManager.setPaused).toHaveBeenCalledWith(true);
      expect(mockSimulationStateManager.setPaused).toHaveBeenCalledWith(false);
    });
  });

  describe('scrub', () => {
    it('calls localFrameSource.getMaxFrame when scrubbing to end', () => {
      (
        mockSimulationStateManager.getSimulationSecondsPassed as Mock
      ).mockReturnValue(1000);
      engine.scrub(1000);
      expect(mockLocalFrameSource.getMaxFrame).toHaveBeenCalled();
    });
    it('calls localFrameSource.getFrame when scrubbing to a past time', () => {
      (
        mockSimulationStateManager.getSimulationSecondsPassed as Mock
      ).mockReturnValue(1000);
      engine.scrub(500);
      expect(mockLocalFrameSource.getFrame).toHaveBeenCalledWith(500);
    });
  });

  describe('commitScrub', () => {
    it('switches to local mode when scrubbing to past', () => {
      (
        mockSimulationStateManager.getSimulationSecondsPassed as Mock
      ).mockReturnValue(1000);
      engine.commitScrub(500);
      expect(engine['mode']).toBe(SimulationMode.Local);
    });
    it('switches to server mode when scrubbing to end', () => {
      (
        mockSimulationStateManager.getSimulationSecondsPassed as Mock
      ).mockReturnValue(1000);
      engine.commitScrub(1000);
      expect(engine['mode']).toBe(SimulationMode.Server);
    });
  });

  describe('handleFrame', () => {
    it("calls state manager's updateHQWidgetState", () => {
      const frame = makePayload({
        tasks: [makeStationTask()],
        stations: [makeStation()],
        drivers: [makeDriver()],
        vehicles: [makeVehicle()],
      });
      engine['handleFrame'](frame);
      expect(mockSimulationStateManager.updateHQWidgetState).toHaveBeenCalled();
    });
  });

  describe('requestAssignment', () => {
    it('sets a pending assignment if tasks are currently unassigned', () => {
      const driver = makeDriver({ id: 1, vehicleId: 1 });
      const vehicle = makeVehicle({ id: 1 });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(driver);
      (mockSimulationStateManager.getVehicle as Mock).mockReturnValue(vehicle);
      (mockSimulationStateManager.getTask as Mock)
        .mockReturnValueOnce(
          makeStationTask({ id: 1, assignedDriverId: undefined })
        )
        .mockReturnValueOnce(
          makeStationTask({ id: 2, assignedDriverId: undefined })
        );
      engine.requestAssignment(1, [1, 2]);
      expect(
        mockSimulationStateManager.setPendingAssignment
      ).toHaveBeenCalledWith(
        makePendingAssignment({
          action: TaskAction.Assign,
          taskIds: [1, 2],
          driverId: driver.id,
          driverName: driver.name,
          driverBatteryCount: vehicle.batteryCount,
          reassignCount: 2,
          unassignedTaskIds: [1, 2],
        })
      );
    });
    it('sets a pending assignment if tasks are currently assigned to different drivers', () => {
      const driver = makeDriver({ id: 1, vehicleId: 1 });
      const vehicle = makeVehicle({ id: 1 });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(driver);
      (mockSimulationStateManager.getVehicle as Mock).mockReturnValue(vehicle);
      (mockSimulationStateManager.getTask as Mock)
        .mockReturnValueOnce(makeStationTask({ id: 1, assignedDriverId: 100 }))
        .mockReturnValueOnce(makeStationTask({ id: 2, assignedDriverId: 101 }));
      engine.requestAssignment(1, [1, 2]);
      expect(
        mockSimulationStateManager.setPendingAssignment
      ).toHaveBeenCalledWith(
        makePendingAssignment({
          action: TaskAction.Assign,
          taskIds: [1, 2],
          driverId: driver.id,
          driverName: driver.name,
          driverBatteryCount: vehicle.batteryCount,
          reassignCount: 2,
        })
      );
    });
    it('sets a pending re-assignment if tasks are currently assigned to the same driver', () => {
      const driver = makeDriver({ id: 1, vehicleId: 1 });
      const vehicle = makeVehicle({ id: 1 });
      const prevDriver = makeDriver({ id: 100 });
      (mockSimulationStateManager.getDriver as Mock)
        .mockReturnValueOnce(driver)
        .mockReturnValueOnce(prevDriver);
      (mockSimulationStateManager.getVehicle as Mock).mockReturnValue(vehicle);
      (mockSimulationStateManager.getTask as Mock)
        .mockReturnValueOnce(makeStationTask({ id: 1, assignedDriverId: 100 }))
        .mockReturnValueOnce(makeStationTask({ id: 2, assignedDriverId: 100 }));
      engine.requestAssignment(1, [1, 2]);
      expect(
        mockSimulationStateManager.setPendingAssignment
      ).toHaveBeenCalledWith(
        makePendingAssignment({
          action: TaskAction.Reassign,
          taskIds: [1, 2],
          driverId: driver.id,
          driverName: driver.name,
          driverBatteryCount: vehicle.batteryCount,
          prevDriverId: prevDriver.id,
          prevDriverName: prevDriver.name,
        })
      );
    });
  });
  describe('requestUnassignment', () => {
    it('sets a pending unassignment', () => {
      const driver = makeDriver({ id: 1, vehicleId: 1 });
      const vehicle = makeVehicle({ id: 1 });
      (mockSimulationStateManager.getDriver as Mock).mockReturnValue(driver);
      (mockSimulationStateManager.getVehicle as Mock).mockReturnValue(vehicle);
      engine.requestUnassignment(1, 1);
      expect(
        mockSimulationStateManager.setPendingAssignment
      ).toHaveBeenCalledWith(
        makePendingAssignment({
          action: TaskAction.Unassign,
          taskIds: [1],
          driverId: driver.id,
          driverName: driver.name,
          driverBatteryCount: vehicle.batteryCount,
        })
      );
    });
  });
});
