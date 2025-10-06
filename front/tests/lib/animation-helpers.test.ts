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

import { expect, test } from 'vitest';
import { interpolateAlongRoute } from '~/lib/animation-helpers';

test('interpolateAlongRoute returns old position when progress is 0', () => {
  const route: [number, number][] = [
    [0, 0],
    [5, 0],
    [10, 0],
  ];
  const oldPos: [number, number] = [2, 0];
  const newPos: [number, number] = [8, 0];

  const result = interpolateAlongRoute(route, oldPos, newPos, 0);

  expect(result).toEqual([2, 0]);
});

test('interpolateAlongRoute returns new position when progress is 1', () => {
  const route: [number, number][] = [
    [0, 0],
    [5, 0],
    [10, 0],
  ];
  const oldPos: [number, number] = [2, 0];
  const newPos: [number, number] = [8, 0];

  const result = interpolateAlongRoute(route, oldPos, newPos, 1);

  expect(result).toEqual([8, 0]);
});

test('interpolateAlongRoute returns midpoint when progress is 0.5', () => {
  const route: [number, number][] = [
    [0, 0],
    [10, 0],
  ];
  const oldPos: [number, number] = [0, 0];
  const newPos: [number, number] = [10, 0];

  const result = interpolateAlongRoute(route, oldPos, newPos, 0.5);

  expect(result).toEqual([5, 0]);
});

test('interpolateAlongRoute works with negative coordinates', () => {
  const route: [number, number][] = [
    [-10, -10],
    [0, 0],
    [10, 10],
  ];
  const oldPos: [number, number] = [-5, -5];
  const newPos: [number, number] = [5, 5];

  const result = interpolateAlongRoute(route, oldPos, newPos, 0.5);

  expect(result).toEqual([0, 0]);
});

test('interpolateAlongRoute handles complex route geometry', () => {
  // Route geometry is currently ignored in placeholder implementation
  // This test verifies current behavior (straight line)
  const complexRoute: [number, number][] = [
    [0, 0],
    [2, 2],
    [5, 2],
    [8, 5],
    [10, 10],
  ];
  const oldPos: [number, number] = [0, 0];
  const newPos: [number, number] = [10, 10];

  const result = interpolateAlongRoute(complexRoute, oldPos, newPos, 0.5);

  // Current implementation does straight line, ignoring route
  expect(result).toEqual([5, 5]);
});
