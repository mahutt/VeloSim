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

import { makePayload } from 'tests/test-helpers';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import LocalFrameSource from '~/lib/frame-sources/local-frame-source';
import type { BackendPayload } from '~/types';

describe('LocalFrameSource', () => {
  let frameSource: LocalFrameSource;
  let mockOnFrame: ReturnType<typeof vi.fn>;
  let mockOnError: ReturnType<typeof vi.fn>;

  const createMockFrame = (simSecondsPassed: number): BackendPayload =>
    makePayload({
      simId: 'test-sim',
      clock: {
        startTime: 0,
        simSecondsPassed,
        simMinutesPassed: simSecondsPassed / 60,
        realSecondsPassed: simSecondsPassed,
        realMinutesPassed: simSecondsPassed / 60,
      },
    });

  beforeEach(() => {
    mockOnFrame = vi.fn();
    mockOnError = vi.fn();
    frameSource = new LocalFrameSource('test-sim', mockOnFrame, mockOnError);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('saveFrame', () => {
    it('should NOT update maxFramePosition when saving a frame that is overriding an existing frame', () => {
      const frame5 = createMockFrame(5);
      const frame10 = createMockFrame(10);

      frameSource.saveFrame(frame10);
      frameSource.saveFrame(frame5);

      expect(frameSource.getMaxFrame()).toBe(frame10);
    });

    it('should update maxFramePosition when saving a frame that is the most recent', () => {
      const frame5 = createMockFrame(5);
      const frame10 = createMockFrame(10);

      frameSource.saveFrame(frame5);
      frameSource.saveFrame(frame10);

      expect(frameSource.getMaxFrame()).toBe(frame10);
    });
  });

  describe('setSpeed', () => {
    it('should NOT call setInterval when new speed equals the old speed', async () => {
      const setIntervalSpy = vi.spyOn(window, 'setInterval');

      await frameSource.setSpeed(1);
      expect(setIntervalSpy).toHaveBeenCalledTimes(1);

      await frameSource.setSpeed(1);
      expect(setIntervalSpy).toHaveBeenCalledTimes(1); // still only called once
    });

    it('should call clearInterval and set intervalTimer to null when new speed is 0', async () => {
      const clearIntervalSpy = vi.spyOn(window, 'clearInterval');
      const setIntervalSpy = vi.spyOn(window, 'setInterval');

      // Creates an interval
      await frameSource.setSpeed(1);
      expect(setIntervalSpy).toHaveBeenCalledTimes(1);

      // Clears the interval
      await frameSource.setSpeed(0);
      expect(clearIntervalSpy).toHaveBeenCalledTimes(1);
      expect(setIntervalSpy).toHaveBeenCalledTimes(1); // still only called once
    });
  });

  describe('emitFrame', () => {
    it('should not call onFrame if position is greater than maxFramePosition', async () => {
      frameSource.setPosition(1);
      frameSource.emitFrame();
      expect(mockOnFrame).not.toHaveBeenCalled();
    });
    it("should not call onFrame if frame isn't stored", async () => {
      const frame10 = createMockFrame(10);

      frameSource.saveFrame(frame10);
      frameSource.setPosition(5);
      frameSource.emitFrame();

      expect(mockOnFrame).not.toHaveBeenCalled();
    });
    it('should call onFrame and increment position if frame is found', async () => {
      const frame10 = createMockFrame(10);

      frameSource.saveFrame(frame10);
      frameSource.setPosition(10);
      frameSource.emitFrame();

      expect(mockOnFrame).toHaveBeenCalledWith(frame10);
    });
  });

  describe('getFrame', () => {
    it('should return the correct frame for a given position', () => {
      const frame5 = createMockFrame(5);
      const frame10 = createMockFrame(10);

      frameSource.saveFrame(frame5);
      frameSource.saveFrame(frame10);

      expect(frameSource.getFrame(5)).toBe(frame5);
      expect(frameSource.getFrame(10)).toBe(frame10);
    });
  });
});
