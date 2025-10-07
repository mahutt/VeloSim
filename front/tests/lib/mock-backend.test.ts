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

import { expect, test, vi, beforeEach, afterEach } from 'vitest';
import { startMockBackend, FRAME_INTERVAL_MS } from '~/lib/mock-backend';
import type { Route } from '~/types';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

test('startMockBackend sends position updates at regular intervals', () => {
  const routes: Route[] = [
    {
      id: 1,
      coordinates: [
        [0, 0],
        [1, 1],
        [2, 2],
      ],
    },
  ];

  const onFrame = vi.fn();
  startMockBackend(routes, onFrame);

  expect(onFrame).not.toHaveBeenCalled();

  vi.advanceTimersByTime(FRAME_INTERVAL_MS);
  expect(onFrame).toHaveBeenCalledTimes(1);

  vi.advanceTimersByTime(FRAME_INTERVAL_MS);
  expect(onFrame).toHaveBeenCalledTimes(2);
});

test('startMockBackend cleanup stops sending updates', () => {
  const routes: Route[] = [
    {
      id: 1,
      coordinates: [
        [0, 0],
        [1, 1],
      ],
    },
  ];

  const onFrame = vi.fn();
  const cleanup = startMockBackend(routes, onFrame);

  vi.advanceTimersByTime(FRAME_INTERVAL_MS);
  expect(onFrame).toHaveBeenCalledTimes(1);

  cleanup();

  vi.advanceTimersByTime(FRAME_INTERVAL_MS * 3);
  expect(onFrame).toHaveBeenCalledTimes(1);
});
