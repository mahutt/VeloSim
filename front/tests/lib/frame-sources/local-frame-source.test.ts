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
  makePayload,
  makePayloadClock,
  makeSeekFrame,
  makeSeekResponse,
} from 'tests/test-helpers';
import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  type Mock,
} from 'vitest';
import api from '~/api';
import LocalFrameSource from '~/lib/frame-sources/local-frame-source';
import type { BackendPayload } from '~/types';

vi.mock('~/api', () => {
  return {
    default: {
      get: vi.fn(),
    },
  };
});

describe('LocalFrameSource', () => {
  let frameSource: LocalFrameSource;
  let mockOnFrame: ReturnType<typeof vi.fn>;

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
    frameSource = new LocalFrameSource('test-sim', mockOnFrame);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe('saveFrame', () => {
    it('should make the frame available via getFrame', async () => {
      const frame0 = createMockFrame(0);
      frameSource.saveFrame(frame0);
      const fetchFrame0 = await frameSource.getFrame(0);
      expect(fetchFrame0).toBe(frame0);
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
    it('should call onFrame and increment position if frame is found', async () => {
      const frame0 = createMockFrame(0);
      const frame1 = createMockFrame(1);
      const frame2 = createMockFrame(2);
      const frame3 = createMockFrame(3);
      const frame4 = createMockFrame(4);
      const frame5 = createMockFrame(5);

      frameSource.saveFrame(frame0);
      frameSource.saveFrame(frame1);
      frameSource.saveFrame(frame2);
      frameSource.saveFrame(frame3);
      frameSource.saveFrame(frame4);
      frameSource.saveFrame(frame5);

      frameSource.setPosition(5);
      await frameSource.emitFrame();

      expect(mockOnFrame).toHaveBeenCalled();
    });
    it("should fetch the next batch of frames if they exist but aren't locally stored", async () => {
      (api.get as Mock).mockResolvedValueOnce({ data: makeSeekResponse() });
      const frame0 = createMockFrame(0);

      frameSource.saveFrame(frame0);

      frameSource.setPosition(0);
      frameSource['maxFramePosition'] = 30;
      await frameSource.emitFrame();

      expect(api.get).toHaveBeenCalled();
    });
  });

  describe('getFrame', () => {
    it('should return the correct frame for a given position', async () => {
      // Creating and saving frames 0-4 so that 5 can be fetched
      const frame0 = createMockFrame(0);
      const frame1 = createMockFrame(1);
      const frame2 = createMockFrame(2);
      const frame3 = createMockFrame(3);
      const frame4 = createMockFrame(4);
      const frame5 = createMockFrame(5);

      frameSource.saveFrame(frame0);
      frameSource.saveFrame(frame1);
      frameSource.saveFrame(frame2);
      frameSource.saveFrame(frame3);
      frameSource.saveFrame(frame4);
      frameSource.saveFrame(frame5);

      expect((await frameSource.getFrame(5)).clock.simSecondsPassed).toBe(5);
    });

    it("should seek and return the correct frame for a given position when it isn't stored", async () => {
      const frame0 = makePayload({
        clock: makePayloadClock({ simSecondsPassed: 0 }),
      });
      const frame1 = makePayload({
        clock: makePayloadClock({ simSecondsPassed: 1 }),
      });
      const seekResponse = makeSeekResponse({
        frames: {
          initial_frames: [
            makeSeekFrame({ frame_data: frame0 }),
            makeSeekFrame({ frame_data: frame1 }),
          ],
          future_frames: [],
          has_more_frames: false,
        },
      });
      (api.get as Mock).mockResolvedValueOnce({ data: seekResponse });
      expect((await frameSource.getFrame(1)).clock.simSecondsPassed).toBe(1);
    });
  });

  describe('hasFrame', () => {
    it('returns true when the frame has previously been saved', async () => {
      const frame5 = createMockFrame(5);
      frameSource.saveFrame(frame5);
      expect(frameSource.hasFrame(5)).toBe(true);
    });
    it('returns false when the frame has not previously been saved', async () => {
      expect(frameSource.hasFrame(5)).toBe(false);
    });
  });
});
