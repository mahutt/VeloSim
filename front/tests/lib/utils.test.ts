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

import { describe, expect, it } from 'vitest';
import { positionsEqual } from '~/lib/utils';
import type { Position } from '~/types';

describe('positionsEqual', () => {
  it('returns true when the coordinates match', () => {
    const basePosition: Position = [10, 20];
    const otherPosition: Position = [10, 20];
    const result = positionsEqual(basePosition, otherPosition);
    expect(result).toBe(true);
  });
  it('returns false when only longitude does not match', () => {
    const basePosition: Position = [10, 20];
    const otherPosition: Position = [11, 20];
    const result = positionsEqual(basePosition, otherPosition);
    expect(result).toBe(false);
  });
  it('returns false when only latitude does not match', () => {
    const basePosition: Position = [10, 20];
    const otherPosition: Position = [10, 21];
    const result = positionsEqual(basePosition, otherPosition);
    expect(result).toBe(false);
  });
  it('returns false when neither longitude and latitude match', () => {
    const basePosition: Position = [10, 20];
    const otherPosition: Position = [11, 21];
    const result = positionsEqual(basePosition, otherPosition);
    expect(result).toBe(false);
  });
});
