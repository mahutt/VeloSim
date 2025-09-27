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

import { vi } from 'vitest';

type eventType = 'move';

export class MockMap {
  static instance: undefined | MockMap;
  private container: string | HTMLElement;
  private center: [number, number];
  private zoom: number;
  private style: string;
  private callBacks: Record<eventType, () => void> = { move: () => {} };
  constructor({
    container,
    center,
    zoom,
    style,
  }: {
    container: string | HTMLElement;
    center: [number, number];
    zoom: number;
    style: string;
  }) {
    MockMap.instance = this;
    this.center = center;
    this.zoom = zoom;
    this.style = style;
    this.container = container;
  }
  on = vi.fn((type: eventType, cb: () => void) => {
    this.callBacks[type] = cb;
  });
  remove = vi.fn();
  getCenter = vi.fn(() => this.center);
  getZoom = vi.fn(() => this.zoom);
  move = () => {
    this.callBacks['move']();
  };
  static clear() {
    MockMap.instance = undefined;
  }
}
