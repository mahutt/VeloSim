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

import { describe, it, expect } from 'vitest';

import {
  createHQWidgetState,
  areHQWidgetStatesEqual,
} from '../../app/lib/hq-widget-helpers';
import { DriverState, type Vehicle } from '../../app/types';
import type { HQWidgetProps } from '~/components/simulation/hq-widget';
import { makeDriver, makeVehicle } from 'tests/test-helpers';

describe('createHQWidgetState', () => {
  it('returns null entities when no drivers at HQ and no vehicles at HQ (all quiet)', () => {
    const drivers = [
      makeDriver({ id: 1, state: DriverState.OnRoute, vehicleId: 11 }),
      makeDriver({ id: 2, state: DriverState.OnRoute, vehicleId: 12 }),
    ];
    const vehicles = [
      makeVehicle({ id: 11, driverId: 1 }),
      makeVehicle({ id: 12, driverId: 2 }),
    ];

    const state = createHQWidgetState({
      drivers,
      vehicles,
      simulationSeconds: 0,
      startTime: 0,
    });
    expect(state.entities).toBeNull();
    expect(state.driversAtHQ).toHaveLength(0);
    expect(state.driversPendingShift).toHaveLength(0);
  });

  it('detects drivers at HQ and adapts minutesTillShift correctly', () => {
    // simulationSeconds = 30, driver shift starts at 90 seconds => ceil((90-30)/60)=1 minute
    const drivers = [
      makeDriver({
        id: 1,
        state: DriverState.Idle,
        vehicleId: null,
        shift: { startTime: 90, endTime: 3600 },
        name: 'Alice',
      }),
      makeDriver({
        id: 2,
        state: DriverState.PendingShift,
        vehicleId: null,
        shift: { startTime: 300, endTime: 3600 },
        name: 'Bob',
      }),
    ];
    const vehicles: Vehicle[] = [];

    const state = createHQWidgetState({
      drivers,
      vehicles,
      simulationSeconds: 30,
      startTime: 0,
    });

    expect(state.entities).not.toBeNull();
    expect(state.entities?.type).toBe('driver');
    expect(state.entities?.count).toBe(1);
    expect(state.driversAtHQ).toHaveLength(1);
    expect(state.driversAtHQ[0].name).toBe('Alice');
    expect(state.driversAtHQ[0].minutesTillShift).toBe(1);

    // Pending shift mapping
    expect(state.driversPendingShift).toHaveLength(1);
    expect(state.driversPendingShift[0].name).toBe('Bob');
    // Bob: (300 - 30) / 60 = 4.5 => ceil => 5
    expect(state.driversPendingShift[0].minutesTillShift).toBe(5);
  });

  it('detects vehicles at HQ when no drivers at HQ', () => {
    const drivers = [
      makeDriver({ id: 1, state: DriverState.OnRoute, vehicleId: 11 }),
    ];
    const vehicles = [
      makeVehicle({ id: 11, driverId: null }),
      makeVehicle({ id: 12, driverId: null }),
    ];

    const state = createHQWidgetState({
      drivers,
      vehicles,
      simulationSeconds: 0,
      startTime: 0,
    });
    expect(state.entities).not.toBeNull();
    expect(state.entities?.type).toBe('vehicle');
    expect(state.entities?.count).toBe(2);
    expect(state.driversAtHQ).toHaveLength(0);
  });
});

describe('areHQWidgetStatesEqual', () => {
  it('returns false when entities state differs', () => {
    const base: HQWidgetProps = {
      entities: { type: 'driver', count: 1 },
      driversAtHQ: [{ id: 1, name: 'A', minutesTillShift: 5 }],
      driversPendingShift: [],
    } as const;

    const other: HQWidgetProps = {
      ...base,
      entities: { type: 'vehicle', count: 1 },
    } as const;

    expect(areHQWidgetStatesEqual(base, other)).toBe(false);
  });

  it('returns false when driversAtHQ differs', () => {
    const base: HQWidgetProps = {
      entities: { type: 'driver', count: 1 },
      driversAtHQ: [{ id: 1, name: 'A', minutesTillShift: 5 }],
      driversPendingShift: [],
    } as const;

    const other: HQWidgetProps = {
      ...base,
      driversAtHQ: [{ id: 2, name: 'B', minutesTillShift: 5 }],
    } as const;

    expect(areHQWidgetStatesEqual(base, other)).toBe(false);
  });

  it('returns false when driversPendingShift differs', () => {
    const base: HQWidgetProps = {
      entities: null,
      driversAtHQ: [],
      driversPendingShift: [{ id: 1, name: 'A', minutesTillShift: 3 }],
    } as const;

    const other: HQWidgetProps = {
      ...base,
      driversPendingShift: [{ id: 1, name: 'A', minutesTillShift: 4 }],
    } as const;

    expect(areHQWidgetStatesEqual(base, other)).toBe(false);
  });

  it('returns true for fully equal states', () => {
    const base: HQWidgetProps = {
      entities: { type: 'driver', count: 2 },
      driversAtHQ: [
        { id: 1, name: 'A', minutesTillShift: 1 },
        { id: 2, name: 'B', minutesTillShift: 2 },
      ],
      driversPendingShift: [],
    } as const;

    const other = JSON.parse(JSON.stringify(base));

    expect(areHQWidgetStatesEqual(base, other)).toBe(true);
  });
});
