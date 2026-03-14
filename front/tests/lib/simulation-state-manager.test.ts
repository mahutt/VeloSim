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
  makeHeadquarters,
  makePendingAssignment,
  makeReactiveSimulationState,
  makeStation,
  makeStationTask,
  makeVehicle,
} from 'tests/test-helpers';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { SelectedItemType } from '~/components/map/selected-item-bar';
import type { ReactiveSimulationState } from '~/lib/reactive-simulation-state';
import SimulationStateManager from '~/lib/simulation-state-manager';
import { DriverState, type Driver, type Vehicle } from '~/types';

vi.mock('./reactive-simulation-state', () => ({
  areReactiveSimulationStatesEqual: (
    a: ReactiveSimulationState,
    b: ReactiveSimulationState
  ) => JSON.stringify(a) === JSON.stringify(b),
}));

vi.mock('./simulation-helpers', () => ({
  driverResourceHasUpdated: (prev: Driver | undefined, next: Driver) =>
    prev?.state !== next?.state,
  vehicleResourceHasUpdated: (prev: Vehicle | undefined, next: Vehicle) =>
    prev?.batteryCount !== next?.batteryCount,
}));

function makeManager() {
  const setState = vi.fn();
  const manager = new SimulationStateManager(
    makeReactiveSimulationState({ isLoading: false }),
    setState
  );
  return { manager, setState };
}

describe('SimulationStateManager', () => {
  let manager: SimulationStateManager;
  let setState: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    ({ manager, setState } = makeManager());
  });

  // Loading
  it('gets initial loading state and sets it', () => {
    expect(manager.getLoading()).toBe(false);
    manager.setLoading(true);
    expect(setState).toHaveBeenCalled();
  });

  it('does not call setState when reactive state is unchanged', () => {
    expect(manager.getLoading()).toBe(false);
    manager.setLoading(false);
    expect(setState).not.toHaveBeenCalled();
  });

  // block assignments
  it('gets initial block assignments state and sets it', () => {
    expect(manager.getBlockAssignments()).toBe(false);
    manager.setBlockAssignments(true);
    expect(setState).toHaveBeenCalled();
  });

  it('does not call setState when block assignments is unchanged', () => {
    expect(manager.getBlockAssignments()).toBe(false);
    manager.setBlockAssignments(false);
    expect(setState).not.toHaveBeenCalled();
  });

  // Drivers
  it('gets undefined for unknown driver', () => {
    expect(manager.getDriver(999)).toBeUndefined();
  });

  it('sets, gets and lists drivers', () => {
    const driver = makeDriver({ id: 1 });
    manager.setDriver(driver);
    expect(manager.getDriver(1)).toBe(driver);
    expect(manager.getAllDrivers()).toContain(driver);
  });

  it('setDriver updates selectedItem when it was the previous driver', () => {
    const driver = makeDriver({ id: 1, name: 'Alice' });
    manager.setDriver(driver);
    manager.setSelectedItem(driver);
    const updated = makeDriver({ id: 1, name: 'Alice Updated' });
    manager.setDriver(updated);
    expect(manager.getSelectedItem()).toBe(updated);
  });

  it('setDriver triggers resource bar update when driver state changes', () => {
    manager.setVehicle(makeVehicle({ id: 10 }));
    manager.setDriver(
      makeDriver({
        id: 1,
        state: DriverState.OnBreak,
        vehicleId: 10,
      })
    );
    const callsBefore = setState.mock.calls.length;
    manager.setDriver(
      makeDriver({ id: 1, state: DriverState.Idle, vehicleId: 10 })
    );
    expect(setState.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  // Vehicles
  it('sets, gets and lists vehicles', () => {
    const vehicle = makeVehicle({ id: 1 });
    manager.setVehicle(vehicle);
    expect(manager.getVehicle(1)).toBe(vehicle);
    expect(manager.getAllVehicles()).toContain(vehicle);
  });

  it('setVehicle triggers resource bar update when batteryCount changes', () => {
    manager.setDriver(makeDriver({ id: 2, vehicleId: 1 }));
    manager.setVehicle(makeVehicle({ id: 1, batteryCount: 5, driverId: 2 }));
    const callsBefore = setState.mock.calls.length;
    manager.setVehicle(makeVehicle({ id: 1, batteryCount: 3, driverId: 2 }));
    expect(setState.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  // Stations
  it('sets, gets and lists stations', () => {
    const station = makeStation({ id: 1 });
    manager.setStation(station);
    expect(manager.getStation(1)).toBe(station);
    expect(manager.getAllStations()).toContain(station);
  });

  it('setStation updates selectedItem when it was the previous station', () => {
    const station = makeStation({ id: 1, name: 'Station A' });
    manager.setStation(station);
    manager.setSelectedItem(station);
    const updated = makeStation({ id: 1, name: 'Station B' });
    manager.setStation(updated);
    expect(manager.getSelectedItem()).toBe(updated);
  });

  // Tasks
  it('sets and gets a task', () => {
    const task = makeStationTask({ id: 1 });
    manager.setTask(task);
    expect(manager.getTask(1)).toBe(task);
  });

  // Selected item — null
  it('setSelectedItem(null) clears selectedItems', () => {
    manager.setSelectedItem(null);
    expect(manager.getSelectedItem()).toBeNull();
    expect(setState).not.toHaveBeenCalled();
  });

  // Selected item — driver with tasks and inProgressTask
  it('setSelectedItem with driver builds Driver selectedItems entry', () => {
    manager.setTask(makeStationTask({ id: 1000 }));
    manager.setTask(makeStationTask({ id: 2000 }));
    const driver = makeDriver({
      taskIds: [1000, 2000],
      inProgressTaskId: 2000,
    });
    manager.setDriver(driver);
    manager.setSelectedItem(driver);
    expect(setState).toHaveBeenCalledWith(
      expect.objectContaining({
        selectedItems: [
          expect.objectContaining({
            type: SelectedItemType.Driver,
            value: expect.objectContaining({
              inProgressTask: expect.objectContaining({ id: 2000 }),
            }),
          }),
        ],
      })
    );
  });

  // HQ
  it('sets and gets headquarters', () => {
    const hq = makeHeadquarters({ position: [1, 2] });
    manager.setHeadquarters(hq);
    expect(manager.getHeadquarters()).toBe(hq);
  });

  // Map refresh
  it('gets and sets mapShouldRefresh', () => {
    expect(manager.getMapShouldRefresh()).toBe(false);
    manager.setMapShouldRefresh(true);
    expect(manager.getMapShouldRefresh()).toBe(true);
  });

  // showAllRoutes no-op when unchanged
  it('setShowAllRoutes is a no-op when value is unchanged', () => {
    manager.setShowAllRoutes(true);
    const callsBefore = setState.mock.calls.length;
    manager.setShowAllRoutes(true);
    expect(setState.mock.calls.length).toBe(callsBefore);
  });

  // Reactive state pass-throughs
  it.each([
    [
      'formattedSimTime',
      (m: SimulationStateManager) => m.setFormattedSimTime('12:00'),
      (m: SimulationStateManager) => m.getFormattedSimTime(),
      '12:00',
    ],
    [
      'currentDay',
      (m: SimulationStateManager) => m.setCurrentDay(3),
      (m: SimulationStateManager) => m.getCurrentDay(),
      3,
    ],
    [
      'nonZeroSpeed',
      (m: SimulationStateManager) => m.setNonZeroSpeed(2),
      (m: SimulationStateManager) => m.getNonZeroSpeed(),
      2,
    ],
    [
      'paused',
      (m: SimulationStateManager) => m.setPaused(true),
      (m: SimulationStateManager) => m.getPaused(),
      true,
    ],
    [
      'showAllRoutes',
      (m: SimulationStateManager) => m.setShowAllRoutes(true),
      (m: SimulationStateManager) => m.getShowAllRoutes(),
      true,
    ],
    [
      'startTime',
      (m: SimulationStateManager) => m.setStartTime(9999),
      (m: SimulationStateManager) => m.getStartTime(),
      9999,
    ],
    [
      'simSecondsPassed',
      (m: SimulationStateManager) => m.setSimulationSecondsPassed(42),
      (m: SimulationStateManager) => m.getSimulationSecondsPassed(),
      42,
    ],
    [
      'scrubSecond',
      (m: SimulationStateManager) => m.setScrubSimulationSecond(10),
      (m: SimulationStateManager) => m.getScrubSimulationSecond(),
      10,
    ],
    [
      'pendingAssignment',
      (m: SimulationStateManager) =>
        m.setPendingAssignment(makePendingAssignment({ driverId: 1 })),
      (m: SimulationStateManager) => m.getPendingAssignment(),
      makePendingAssignment({ driverId: 1 }),
    ],
    [
      'pendingLoading',
      (m: SimulationStateManager) => m.setPendingAssignmentLoading(true),
      (m: SimulationStateManager) => m.getPendingAssignmentLoading(),
      true,
    ],
  ])(
    'sets and triggers re-render for %s',
    (_, setter, getter, expectedValue) => {
      setter(manager);
      expect(setState).toHaveBeenCalled();
      expect(getter(manager)).toEqual(expectedValue);
    }
  );

  // updateHQWidgetState
  it('updateHQWidgetState triggers setState when state changes', () => {
    manager.setStartTime(0);
    manager.setDriver(makeDriver({ shift: { startTime: 60, endTime: 3600 } }));
    manager.setVehicle(makeVehicle());
    const callsBefore = setState.mock.calls.length;
    manager.updateHQWidgetState();
    expect(setState.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  // getReactiveState
  it('getReactiveState returns current reactive state', () => {
    expect(manager.getReactiveState()).toMatchObject({ isLoading: false });
  });

  // ── Multi-selection ────────────────────────────────────────────────

  describe('multi-station selection', () => {
    it('getMultiSelectedStationIds returns empty set initially', () => {
      expect(manager.getMultiSelectedStationIds().size).toBe(0);
    });

    it('toggleMultiSelectedStation adds a station', () => {
      const station = makeStation({ id: 1, taskIds: [100] });
      const task = makeStationTask({ id: 100, stationId: 1 });
      manager.setStation(station);
      manager.setTask(task);

      setState.mockClear();
      manager.toggleMultiSelectedStation(1);

      expect(manager.getMultiSelectedStationIds()).toEqual(new Set([1]));
      expect(setState).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedItems: [
            expect.objectContaining({
              type: SelectedItemType.Station,
              value: expect.objectContaining({
                id: 1,
                tasks: [expect.objectContaining({ id: 100 })],
              }),
            }),
          ],
        })
      );
    });

    it('toggleMultiSelectedStation removes a station that is already selected', () => {
      const station = makeStation({ id: 1 });
      manager.setStation(station);
      manager.toggleMultiSelectedStation(1);

      setState.mockClear();
      manager.toggleMultiSelectedStation(1);

      expect(manager.getMultiSelectedStationIds().size).toBe(0);
      expect(setState).toHaveBeenCalledWith(
        expect.objectContaining({ selectedItems: [] })
      );
    });

    it('toggleMultiSelectedStation sets mapShouldRefresh', () => {
      manager.setStation(makeStation({ id: 1 }));
      manager.setMapShouldRefresh(false);
      manager.toggleMultiSelectedStation(1);
      expect(manager.getMapShouldRefresh()).toBe(true);
    });

    it('setMultiSelectedStations replaces the selection', () => {
      const s1 = makeStation({ id: 1, taskIds: [10] });
      const s2 = makeStation({ id: 2, taskIds: [20] });
      manager.setStation(s1);
      manager.setStation(s2);
      manager.setTask(makeStationTask({ id: 10, stationId: 1 }));
      manager.setTask(makeStationTask({ id: 20, stationId: 2 }));

      setState.mockClear();
      manager.setMultiSelectedStations([1, 2]);

      expect(manager.getMultiSelectedStationIds()).toEqual(new Set([1, 2]));
      expect(setState).toHaveBeenCalledWith(
        expect.objectContaining({
          selectedItems: expect.arrayContaining([
            expect.objectContaining({
              type: SelectedItemType.Station,
              value: expect.objectContaining({ id: 1 }),
            }),
            expect.objectContaining({
              type: SelectedItemType.Station,
              value: expect.objectContaining({ id: 2 }),
            }),
          ]),
        })
      );
    });

    it('setMultiSelectedStations skips unknown station ids', () => {
      manager.setStation(makeStation({ id: 1 }));

      manager.setMultiSelectedStations([1, 999]);

      const state = manager.getReactiveState();
      expect(state.selectedItems).toHaveLength(1);
      expect(state.selectedItems[0].value.id).toBe(1);
    });

    it('clearMultiSelectedStations resets selection to empty', () => {
      manager.setStation(makeStation({ id: 1 }));
      manager.setMultiSelectedStations([1]);

      setState.mockClear();
      manager.clearMultiSelectedStations();

      expect(manager.getMultiSelectedStationIds().size).toBe(0);
      expect(setState).toHaveBeenCalledWith(
        expect.objectContaining({ selectedItems: [] })
      );
    });

    it('clearMultiSelectedStations is a no-op when already empty', () => {
      setState.mockClear();
      manager.clearMultiSelectedStations();
      expect(setState).not.toHaveBeenCalled();
    });

    it('setStation updates reactive multi-selection when station is in the set', () => {
      const station = makeStation({ id: 1, name: 'Old', taskIds: [10] });
      manager.setStation(station);
      manager.setTask(makeStationTask({ id: 10, stationId: 1 }));
      manager.setMultiSelectedStations([1]);

      // Verify initial multi-selection has the old name
      expect(manager.getReactiveState().selectedItems).toEqual([
        expect.objectContaining({
          value: expect.objectContaining({ id: 1, name: 'Old' }),
        }),
      ]);

      const updated = makeStation({ id: 1, name: 'New', taskIds: [10] });
      manager.setStation(updated);

      // After updating the station, the reactive multi-selection should reflect the new name
      expect(manager.getReactiveState().selectedItems).toEqual([
        expect.objectContaining({
          value: expect.objectContaining({ id: 1, name: 'New' }),
        }),
      ]);
    });

    it('setMultiSelectedStations sets mapShouldRefresh', () => {
      manager.setMapShouldRefresh(false);
      manager.setMultiSelectedStations([]);
      expect(manager.getMapShouldRefresh()).toBe(true);
    });

    it('clearMultiSelectedStations sets mapShouldRefresh when clearing non-empty set', () => {
      manager.setStation(makeStation({ id: 1 }));
      manager.setMultiSelectedStations([1]);
      manager.setMapShouldRefresh(false);
      manager.clearMultiSelectedStations();
      expect(manager.getMapShouldRefresh()).toBe(true);
    });
  });
});
