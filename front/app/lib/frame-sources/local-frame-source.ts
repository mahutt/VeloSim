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

import type { Speed } from '~/providers/simulation-provider';
import type { BackendPayload } from '~/types';
import type FrameSource from './frame-source';

export default class LocalFrameSource implements FrameSource {
  private simulationId: string;
  private onFrame: (frame: BackendPayload) => void;
  private onError: (error: string) => void;

  private frames: Map<number, BackendPayload>;
  private maxFramePosition: number;
  private position: number;
  private intervalTimer: number | null;
  private speed: Speed;

  constructor(
    simulationId: string,
    onFrame: (frame: BackendPayload) => void,
    onError: (error: string) => void
  ) {
    this.simulationId = simulationId;
    this.onFrame = onFrame;
    this.onError = onError;

    this.frames = new Map<number, BackendPayload>();
    this.maxFramePosition = 0;
    this.position = 0;
    this.intervalTimer = null;
    this.speed = 0;
  }

  public saveFrame(frame: BackendPayload) {
    const position = frame.clock.simSecondsPassed;
    this.frames.set(position, frame);
    if (position > this.maxFramePosition) {
      this.maxFramePosition = position;
    }
  }

  public getFrame(position: number): BackendPayload | undefined {
    return this.frames.get(position);
  }

  public getMaxFrame(): BackendPayload | undefined {
    return this.frames.get(this.maxFramePosition);
  }

  public setPosition(position: number) {
    this.position = position;
  }

  public async setSpeed(speed: Speed): Promise<void> {
    if (this.speed === speed) return;
    if (this.intervalTimer) clearInterval(this.intervalTimer);
    this.speed = speed;
    if (speed === 0) {
      this.intervalTimer = null;
      return;
    }
    this.intervalTimer = window.setInterval(
      this.emitFrame.bind(this),
      1000 / speed
    );
  }

  public emitFrame() {
    if (this.position > this.maxFramePosition) {
      this.setSpeed(0);
      return;
    }

    const frame = this.frames.get(this.position);

    if (!frame) {
      console.warn(
        `LocalFrameSource: No frame found at position ${this.position}`
      );
      this.setSpeed(0);
      return;
    }

    console.log(
      `LocalFrameSource: Emitting frame at position ${this.position}`
    );
    this.onFrame(frame);
    this.position += 1;
  }
}
