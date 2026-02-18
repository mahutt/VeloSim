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
  HQEntitiesState,
  HQWidgetDriver,
  HQWidgetProps,
} from '~/components/simulation/hq-widget';
import { DriverState, type Driver, type Vehicle } from '~/types';

/**
 * Transforms a Driver instance into an HQWidgetDriver instance.
 * minutesTillShift is rounded up to the nearest whole minute.
 *
 * @param driver the driver instance to adapt for the HQ widget
 * @param simulationSeconds the number of seconds (ticks) elapsed in the simulation
 * @returns an HQWidgetDriver instance
 */
function adaptDriverForHQWidget(
  driver: Driver,
  simulationSeconds: number,
  startTime: number
): HQWidgetDriver {
  const secondsTillShift =
    driver.shift.startTime - (simulationSeconds + startTime);
  const minutesTillShift = Math.ceil(secondsTillShift / 60);
  return {
    id: driver.id,
    name: driver.name,
    minutesTillShift: minutesTillShift,
  };
}

/**
 * Creates an HQ widget state from the current simulation state.
 *
 * @param params
 * @param params.driversMap Map of driver IDs to current simulation drivers.
 * @param params.vehiclesMap Map of vehicle IDs to current simulation vehicles.
 * @param params.simulationSeconds Current simulation time in seconds.
 * @returns A valid HQ widget state.
 */
export function createHQWidgetState({
  drivers,
  vehicles,
  simulationSeconds,
  startTime,
}: {
  drivers: Driver[];
  vehicles: Vehicle[];
  simulationSeconds: number;
  startTime: number;
}): HQWidgetProps {
  const driversAtHQ: Driver[] = [];
  const driversPendingShift: Driver[] = [];

  for (const driver of drivers) {
    if (driver.state === DriverState.Idle && driver.vehicleId === null) {
      // necessarily at HQ if idle and no vehicle
      driversAtHQ.push(driver);
    } else if (driver.state === DriverState.PendingShift) {
      driversPendingShift.push(driver);
    }
  }

  let entities: HQEntitiesState | null = null;
  if (driversAtHQ.length > 0) {
    entities = {
      type: 'driver',
      count: driversAtHQ.length,
    };
  } else {
    const vehiclesAtHQ = vehicles.filter(
      (vehicle) => vehicle.driverId === null // A vehicle is known to be at HQ if it is not assigned a driver
    ).length;
    entities =
      vehiclesAtHQ > 0
        ? {
            type: 'vehicle',
            count: vehiclesAtHQ,
          }
        : null;
  }

  return {
    entities,
    driversAtHQ: driversAtHQ.map((driver) =>
      adaptDriverForHQWidget(driver, simulationSeconds, startTime)
    ),
    driversPendingShift: driversPendingShift.map((driver) =>
      adaptDriverForHQWidget(driver, simulationSeconds, startTime)
    ),
  };
}

/**
 * Compares two HQ widget state objects for deep equality.
 *
 * @param base First HQ widget state
 * @param other Second HQ widget state
 * @returns True if the two states are equal, false otherwise
 */
export function areHQWidgetStatesEqual(
  base: HQWidgetProps,
  other: HQWidgetProps
): boolean {
  const equalEntitiesState =
    base.entities?.type === other.entities?.type &&
    base.entities?.count === other.entities?.count;
  if (!equalEntitiesState) return false;

  const equalDriversAtHQ =
    base.driversAtHQ.length === other.driversAtHQ.length &&
    base.driversAtHQ.every((driver, index) => {
      const newDriver = other.driversAtHQ[index];
      return (
        driver.id === newDriver.id &&
        driver.name === newDriver.name &&
        driver.minutesTillShift === newDriver.minutesTillShift
      );
    });
  if (!equalDriversAtHQ) return false;

  const equalDriversPendingShift =
    base.driversPendingShift.length === other.driversPendingShift.length &&
    base.driversPendingShift.every((driver, index) => {
      const newDriver = other.driversPendingShift[index];
      return (
        driver.id === newDriver.id &&
        driver.name === newDriver.name &&
        driver.minutesTillShift === newDriver.minutesTillShift
      );
    });

  if (!equalDriversPendingShift) return false;
  return true;
}
