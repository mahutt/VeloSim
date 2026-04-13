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
  makePopulatedDriver,
  makeSelectedItem,
  makeReactiveSimulationState,
  makePendingAssignment,
  makeResourceItemElement,
  makeHQWidgetProps,
} from 'tests/test-helpers';
import { describe, it, expect } from 'vitest';
import { SelectedItemType } from '~/components/map/selected-item-bar';
import {
  areReactiveSimulationStatesEqual,
  type ReactiveSimulationState,
} from '~/lib/reactive-simulation-state';
import { DriverState, TaskAction } from '~/types';

describe('areReactiveSimulationStatesEqual', () => {
  it('returns true for two default states', () => {
    const a = makeReactiveSimulationState();
    const b = makeReactiveSimulationState();
    expect(areReactiveSimulationStatesEqual(a, b)).toBe(true);
  });

  it('returns true for a deep clone of a non-trivial state', () => {
    const a: ReactiveSimulationState = {
      isLoading: false,
      isBuffering: false,
      formattedSimTime: '08:30',
      currentDay: 2,
      paused: true,
      nonZeroSpeed: 2,
      showAllRoutes: true,
      simulationSecondsPassed: 900,
      scrubSimulationSecond: 450,
      startTime: 100,
      pendingAssignment: {
        action: TaskAction.Assign,
        taskIds: [10, 20],
        driverId: 1,
        driverName: 'Alice',
        driverBatteryCount: 4,
        reassignCount: 1,
        unassignedTaskIds: [10],
      },
      pendingAssignmentLoading: false,
      selectedItems: [
        {
          type: SelectedItemType.Driver,
          value: {
            id: 5,
            name: 'Bob',
            state: DriverState.Idle,
            position: [0, 0],
            tasks: [],
            route: null,
            inProgressTask: null,
          },
        },
      ],
      blockAssignments: false,
      HQWidgetState: {
        entities: { type: SelectedItemType.Driver, count: 2 },
        driversAtHQ: [{ id: 1, name: 'Alice', minutesTillShift: 3 }],
        driversPendingShift: [{ id: 2, name: 'Bob', minutesTillShift: 7 }],
      },
      resourceBarElement: [
        {
          id: 1,
          name: 'Van A',
          taskCount: 3,
          batteryCount: 5,
          batteryCapacity: 10,
          state: DriverState.Idle,
        },
      ],
      reporting: {
        servicingToDrivingRatio: 1.5,
        vehicleUtilizationRatio: 0.75,
        averageTasksServicedPerShift: 4.2,
        averageTaskResponseTime: 120,
        vehicleDistanceTraveled: 2500,
      },
    };

    const b = JSON.parse(JSON.stringify(a));
    expect(areReactiveSimulationStatesEqual(a, b)).toBe(true);
  });

  describe('primitive fields', () => {
    it('returns false when isLoading differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ isLoading: false }),
          makeReactiveSimulationState({ isLoading: true })
        )
      ).toBe(false);
    });

    it('returns false when formattedSimTime differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ formattedSimTime: '08:00' }),
          makeReactiveSimulationState({ formattedSimTime: '09:00' })
        )
      ).toBe(false);
    });

    it('returns false when currentDay differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ currentDay: 1 }),
          makeReactiveSimulationState({ currentDay: 2 })
        )
      ).toBe(false);
    });

    it('returns false when nonZeroSpeed differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ nonZeroSpeed: 1 }),
          makeReactiveSimulationState({ nonZeroSpeed: 2 })
        )
      ).toBe(false);
    });

    it('returns false when paused differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ paused: false }),
          makeReactiveSimulationState({ paused: true })
        )
      ).toBe(false);
    });

    it('returns false when showAllRoutes differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ showAllRoutes: false }),
          makeReactiveSimulationState({ showAllRoutes: true })
        )
      ).toBe(false);
    });

    it('returns false when startTime differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ startTime: 0 }),
          makeReactiveSimulationState({ startTime: 100 })
        )
      ).toBe(false);
    });

    it('returns false when simulationSecondsPassed differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ simulationSecondsPassed: 0 }),
          makeReactiveSimulationState({ simulationSecondsPassed: 60 })
        )
      ).toBe(false);
    });

    it('returns false when scrubSimulationSecond differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ scrubSimulationSecond: 0 }),
          makeReactiveSimulationState({ scrubSimulationSecond: 30 })
        )
      ).toBe(false);
    });

    it('returns false when pendingAssignmentLoading differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ pendingAssignmentLoading: false }),
          makeReactiveSimulationState({ pendingAssignmentLoading: true })
        )
      ).toBe(false);
    });
  });

  describe('selectedItems', () => {
    it('returns true when both are empty', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ selectedItems: [] }),
          makeReactiveSimulationState({ selectedItems: [] })
        )
      ).toBe(true);
    });

    it('returns false when one is empty and the other is not', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ selectedItems: [] }),
          makeReactiveSimulationState({
            selectedItems: [makeSelectedItem()],
          })
        )
      ).toBe(false);
    });

    it('returns false when types differ', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
              }),
            ],
          }),
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
              }),
            ],
          })
        )
      ).toBe(false);
    });

    it('returns false when ids differ', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({ id: 1 }),
              }),
            ],
          }),
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({ id: 2 }),
              }),
            ],
          })
        )
      ).toBe(false);
    });

    it('returns true when type and id match', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({ id: 42 }),
              }),
            ],
          }),
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Driver,
                value: makePopulatedDriver({ id: 42 }),
              }),
            ],
          })
        )
      ).toBe(true);
    });

    it('returns false for multi-selection with different lengths', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: { id: 1, name: 'A', position: [0, 0], tasks: [] },
              }),
            ],
          }),
          makeReactiveSimulationState({
            selectedItems: [
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: { id: 1, name: 'A', position: [0, 0], tasks: [] },
              }),
              makeSelectedItem({
                type: SelectedItemType.Station,
                value: { id: 2, name: 'B', position: [0, 0], tasks: [] },
              }),
            ],
          })
        )
      ).toBe(false);
    });
  });

  describe('pendingAssignment', () => {
    it('returns true when both are null', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ pendingAssignment: null }),
          makeReactiveSimulationState({ pendingAssignment: null })
        )
      ).toBe(true);
    });

    it('returns false when one is null and the other is not', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ pendingAssignment: null }),
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment(),
          })
        )
      ).toBe(false);
    });

    it('returns false when actions differ', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              action: TaskAction.Assign,
            }),
          }),
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              action: TaskAction.Unassign,
            }),
          })
        )
      ).toBe(false);
    });

    it('returns false when driverIds differ', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({ driverId: 1 }),
          }),
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({ driverId: 2 }),
          })
        )
      ).toBe(false);
    });

    it('returns false when taskIds have different lengths', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              taskIds: [1, 2],
            }),
          }),
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              taskIds: [1, 2, 3],
            }),
          })
        )
      ).toBe(false);
    });

    it('returns false when taskIds have the same length but different values', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              taskIds: [1, 2],
            }),
          }),
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              taskIds: [1, 3],
            }),
          })
        )
      ).toBe(false);
    });

    it('returns true when taskIds are equal but in different order', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              taskIds: [1, 2],
            }),
          }),
          makeReactiveSimulationState({
            pendingAssignment: makePendingAssignment({
              taskIds: [2, 1],
            }),
          })
        )
      ).toBe(true);
    });
  });

  describe('HQWidgetState', () => {
    it('returns false when HQ widget entities type differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            HQWidgetState: makeHQWidgetProps({
              entities: { type: 'driver', count: 1 },
            }),
          }),
          makeReactiveSimulationState({
            HQWidgetState: makeHQWidgetProps({
              entities: { type: 'vehicle', count: 1 },
            }),
          })
        )
      ).toBe(false);
    });

    it('returns false when driversAtHQ differ', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            HQWidgetState: makeHQWidgetProps({
              entities: { type: 'driver', count: 1 },
              driversAtHQ: [{ id: 1, name: 'Alice', minutesTillShift: 5 }],
            }),
          }),
          makeReactiveSimulationState({
            HQWidgetState: makeHQWidgetProps({
              entities: { type: 'driver', count: 1 },
              driversAtHQ: [{ id: 2, name: 'Bob', minutesTillShift: 5 }],
            }),
          })
        )
      ).toBe(false);
    });
  });

  describe('resourceBarElement', () => {
    it('returns false when resource bar lengths differ', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            resourceBarElement: [makeResourceItemElement()],
          }),
          makeReactiveSimulationState({ resourceBarElement: [] })
        )
      ).toBe(false);
    });

    it('returns false when a resource item field differs', () => {
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({
            resourceBarElement: [makeResourceItemElement({ taskCount: 1 })],
          }),
          makeReactiveSimulationState({
            resourceBarElement: [makeResourceItemElement({ taskCount: 2 })],
          })
        )
      ).toBe(false);
    });

    it('returns true for matching resource bar elements', () => {
      const item = makeResourceItemElement();
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ resourceBarElement: [item] }),
          makeReactiveSimulationState({ resourceBarElement: [{ ...item }] })
        )
      ).toBe(true);
    });

    it('returns false when resource bar element order differs', () => {
      const itemA = makeResourceItemElement({ id: 1 });
      const itemB = makeResourceItemElement({ id: 2 });
      expect(
        areReactiveSimulationStatesEqual(
          makeReactiveSimulationState({ resourceBarElement: [itemA, itemB] }),
          makeReactiveSimulationState({ resourceBarElement: [itemB, itemA] })
        )
      ).toBe(false);
    });
  });
});
