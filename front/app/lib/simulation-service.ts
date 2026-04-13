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

import api from '~/api';
import type { BackendPayload, SeekResponse } from '~/types';

export default class SimulationService {
  /**
   * Seeks to a specific position in the simulation and retrieves the frames in the seek window around that position.
   * If the position does not point to a key frame, the result will include the nearest preceding key frame
   * and all subsequent frames up until the position.
   *
   * @param simulationId the ID of the target simulation
   * @param position the position to seek to, in seconds since the start of the simulation
   * @param window the number of seconds worth of frames to fetch following the target position
   * @returns an array of backend payloads for the frames in the seek window
   */
  static async seek(
    simulationId: string,
    position: number,
    window: number
  ): Promise<BackendPayload[]> {
    const { data: seekResponse } = await api.get<SeekResponse>(
      `/simulation/${simulationId}/seek`,
      {
        params: {
          position,
          frame_window_seconds: window,
        },
      }
    );
    const { frames } = seekResponse;
    const { initial_frames, future_frames } = frames;
    const allFrames = [...initial_frames, ...future_frames];
    return allFrames.map((sf) => sf.frame_data);
  }
}
