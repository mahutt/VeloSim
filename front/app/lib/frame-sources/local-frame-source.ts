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
import type {
  BackendPayload,
  Driver,
  Station,
  StationTask,
  Vehicle,
} from '~/types';
import type FrameSource from './frame-source';
import SimulationService from '../simulation-service';
import { SIMULATION_FRAMES_PER_KEY_FRAME } from '~/constants';

export default class LocalFrameSource implements FrameSource {
  private simulationId: string;
  private onFrame: (frame: BackendPayload) => void;

  private frames: Map<number, BackendPayload>;
  private maxFramePosition: number;
  private position: number;
  private intervalTimer: number | null;
  private speed: Speed;
  private seekPromises: Map<number, Promise<void>>;

  constructor(simulationId: string, onFrame: (frame: BackendPayload) => void) {
    this.simulationId = simulationId;
    this.onFrame = onFrame;

    this.frames = new Map<number, BackendPayload>();
    this.maxFramePosition = 0;
    this.position = 0;
    this.intervalTimer = null;
    this.speed = 0;
    this.seekPromises = new Map<number, Promise<void>>();
  }

  public saveFrame(frame: BackendPayload) {
    const position = frame.clock.simSecondsPassed;
    this.frames.set(position, frame);
    if (position > this.maxFramePosition) {
      this.maxFramePosition = position;
    }
  }

  /**
   *
   * @param position the position (sim seconds passed) of the desired
   * @returns a keyframe at the desired position
   */
  public async getFrame(position: number): Promise<BackendPayload> {
    if (!this.frames.has(position)) {
      await this.load(position);
    }
    const keyPosition = this.getMaxKeyframePosition(position);
    const key = this.frames.get(keyPosition)!;
    const diffs = Array.from(
      { length: position - keyPosition },
      (_, i) => keyPosition + i + 1
    ).map((p) => this.frames.get(p)!);
    return this.mergeFrames(key, diffs);
  }

  public async load(position: number): Promise<void> {
    const keyPosition = this.getMaxKeyframePosition(position);
    if (!this.seekPromises.has(keyPosition)) {
      const seekPromise = SimulationService.seek(
        this.simulationId,
        keyPosition,
        SIMULATION_FRAMES_PER_KEY_FRAME - 1
      )
        .then((frames) => {
          frames.forEach((f) => this.saveFrame(f));
        })
        .finally(() => {
          this.seekPromises.delete(keyPosition);
        });
      this.seekPromises.set(keyPosition, seekPromise);
    }
    return this.seekPromises.get(keyPosition);
  }

  public hasFrame(position: number): boolean {
    return this.frames.has(position);
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

  public async emitFrame() {
    if (this.position > this.maxFramePosition) {
      this.setSpeed(0);
      return;
    }

    const nextKeyFramePosition =
      this.getMaxKeyframePosition(this.position) +
      SIMULATION_FRAMES_PER_KEY_FRAME;
    if (
      nextKeyFramePosition < this.maxFramePosition &&
      !this.frames.has(nextKeyFramePosition)
    ) {
      this.load(nextKeyFramePosition);
    }

    const frame = await this.getFrame(this.position);

    this.onFrame(frame);
    this.position += 1;
  }

  private getMaxKeyframePosition(limit?: number) {
    if (limit === undefined || limit > this.maxFramePosition)
      limit = this.maxFramePosition;
    return limit - (limit % SIMULATION_FRAMES_PER_KEY_FRAME);
  }

  private mergeFrames(
    key: BackendPayload,
    diffs: BackendPayload[]
  ): BackendPayload {
    if (diffs.length === 0) return key;

    const tasks = new Map<number, StationTask>();
    const stations = new Map<number, Station>();
    const drivers = new Map<number, Driver>();
    const vehicles = new Map<number, Vehicle>();

    for (const frame of [key, ...diffs]) {
      frame.tasks.forEach((t) => tasks.set(t.id, t));
      frame.stations.forEach((s) => stations.set(s.id, s));
      frame.drivers.forEach((d) => drivers.set(d.id, d));
      frame.vehicles.forEach((v) => vehicles.set(v.id, v));
    }

    const finalDiff = diffs[diffs.length - 1];
    return {
      ...finalDiff,
      tasks: Array.from(tasks.values()),
      stations: Array.from(stations.values()),
      drivers: Array.from(drivers.values()),
      vehicles: Array.from(vehicles.values()),
    };
  }
}
