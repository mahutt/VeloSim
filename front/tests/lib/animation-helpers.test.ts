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

import { makeDriver } from 'tests/test-helpers';
import { describe, expect, it, test } from 'vitest';
import {
  interpolateAlongRoute,
  updateDriverPositions,
} from '~/lib/animation-helpers';
import type { Driver, Position, Route } from '~/types';

// Helper to check if two positions are approximately equal
function expectPositionClose(actual: Position, expected: Position) {
  expect(actual[0]).toBeCloseTo(expected[0], 5);
  expect(actual[1]).toBeCloseTo(expected[1], 5);
}

test('interpolateAlongRoute returns old position when progress is 0', () => {
  const route: Position[] = [
    [0, 0],
    [5, 0],
    [10, 0],
  ];
  const oldPos: Position = [2, 0];
  const newPos: Position = [8, 0];

  const result = interpolateAlongRoute(route, oldPos, newPos, 0);

  expectPositionClose(result, [2, 0]);
});

test('interpolateAlongRoute returns new position when progress is 1', () => {
  const route: Position[] = [
    [0, 0],
    [5, 0],
    [10, 0],
  ];
  const oldPos: Position = [2, 0];
  const newPos: Position = [8, 0];

  const result = interpolateAlongRoute(route, oldPos, newPos, 1);

  expectPositionClose(result, [8, 0]);
});

test('interpolateAlongRoute returns midpoint when progress is 0.5', () => {
  const route: Position[] = [
    [0, 0],
    [10, 0],
  ];
  const oldPos: Position = [0, 0];
  const newPos: Position = [10, 0];

  const result = interpolateAlongRoute(route, oldPos, newPos, 0.5);

  expectPositionClose(result, [5, 0]);
});

test('interpolateAlongRoute works with negative coordinates', () => {
  const route: Position[] = [
    [-10, -10],
    [0, 0],
    [10, 10],
  ];
  const oldPos: Position = [-5, -5];
  const newPos: Position = [5, 5];

  const result = interpolateAlongRoute(route, oldPos, newPos, 0.5);

  expectPositionClose(result, [0, 0]);
});

test('interpolateAlongRoute follows route geometry (not straight line)', () => {
  // Route with a bend: goes right, then up
  const complexRoute: Position[] = [
    [0, 0],
    [5, 0],
    [5, 5],
  ];
  const oldPos: Position = [0, 0];
  const newPos: Position = [5, 5];

  // At progress 0.5, should be near the corner at [5, 0], not at [2.5, 2.5]
  const result = interpolateAlongRoute(complexRoute, oldPos, newPos, 0.5);

  // The midpoint along the L-shaped route should be near the corner
  expect(result[0]).toBeCloseTo(5, 1);
  expect(result[1]).toBeCloseTo(0, 1);
});

test('interpolateAlongRoute falls back to linear for single-point route', () => {
  const route: Position[] = [[5, 5]];
  const oldPos: Position = [0, 0];
  const newPos: Position = [10, 10];

  const result = interpolateAlongRoute(route, oldPos, newPos, 0.5);

  // Should fall back to linear interpolation
  expectPositionClose(result, [5, 5]);
});

describe('updateDriverPositions', () => {
  it("doesn't update a driver's position when no start / target positions are available", () => {
    const drivers = new Map<number, Driver>([[1, makeDriver({ id: 1 })]]);
    const currentPositions = new Map<number, Position>([[1, [0, 0]]]);
    const frameStartPositions = new Map<number, Position>();
    const frameTargetPositions = new Map<number, Position>();
    const routes = new Map<number, Route>();
    const lastDriverUpdates = new Map<number, number>();
    const speed = 1;

    const result = updateDriverPositions(
      drivers,
      currentPositions,
      frameStartPositions,
      frameTargetPositions,
      routes,
      lastDriverUpdates,
      speed
    );

    expect(result).toBe(false);
    expect(currentPositions.get(1)).toEqual([0, 0]);
  });

  it("updates a driver's position when start / target positions are available", () => {
    const drivers = new Map<number, Driver>([[1, makeDriver({ id: 1 })]]);
    const currentPositions = new Map<number, Position>([[1, [0.1, 0.1]]]);
    const frameStartPositions = new Map<number, Position>([[1, [0, 0]]]);
    const frameTargetPositions = new Map<number, Position>([[1, [1, 1]]]);
    const routes = new Map<number, Route>([
      [
        1,
        {
          coordinates: [
            [-1, -1],
            [0, 0],
            [0, 1],
            [1, 1],
          ],
          nextTaskEndIndex: 3,
        },
      ],
    ]);
    const lastDriverUpdates = new Map<number, number>([
      [1, performance.now() - 500],
    ]);
    const speed = 1;

    const result = updateDriverPositions(
      drivers,
      currentPositions,
      frameStartPositions,
      frameTargetPositions,
      routes,
      lastDriverUpdates,
      speed
    );

    expect(result).toBe(true);
    expect(currentPositions.get(1)![0]).toBeCloseTo(0);
    expect(currentPositions.get(1)![1]).toBeCloseTo(1);
  });

  it('uses linear interpolation when no route is available', () => {
    const drivers = new Map<number, Driver>([[1, makeDriver({ id: 1 })]]);
    const currentPositions = new Map<number, Position>([[1, [0.1, 0.1]]]);
    const frameStartPositions = new Map<number, Position>([[1, [0, 0]]]);
    const frameTargetPositions = new Map<number, Position>([[1, [1, 1]]]);
    const routes = new Map<number, Route>();
    const lastDriverUpdates = new Map<number, number>([
      [1, performance.now() - 500],
    ]);
    const speed = 0;

    const result = updateDriverPositions(
      drivers,
      currentPositions,
      frameStartPositions,
      frameTargetPositions,
      routes,
      lastDriverUpdates,
      speed
    );

    expect(result).toBe(true);
    expect(currentPositions.get(1)![0]).toBeCloseTo(0.5);
    expect(currentPositions.get(1)![1]).toBeCloseTo(0.5);
  });

  it('clears the start / target positions if the target is reached', () => {
    const drivers = new Map<number, Driver>([[1, makeDriver({ id: 1 })]]);
    const currentPositions = new Map<number, Position>([[1, [0.1, 0.1]]]);
    const frameStartPositions = new Map<number, Position>([[1, [0, 0]]]);
    const frameTargetPositions = new Map<number, Position>([[1, [1, 1]]]);
    const routes = new Map<number, Route>();
    const lastDriverUpdates = new Map<number, number>([
      [1, performance.now() - 1000],
    ]);
    const speed = 1;

    const result = updateDriverPositions(
      drivers,
      currentPositions,
      frameStartPositions,
      frameTargetPositions,
      routes,
      lastDriverUpdates,
      speed
    );

    expect(result).toBe(true);
    expect(frameStartPositions.has(1)).toBe(false);
    expect(frameTargetPositions.has(1)).toBe(false);
  });
});
