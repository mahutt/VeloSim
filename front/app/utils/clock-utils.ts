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

const SECONDS_PER_DAY = 86400;
const SECONDS_PER_HOUR = 3600;

export function formatSecondsToHHMM(
  seconds: number,
  startTime: number = 0
): string {
  const totalSeconds = seconds + startTime;

  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return '00:00';

  const hours = Math.floor(totalSeconds / SECONDS_PER_HOUR);
  const minutes = Math.floor((totalSeconds % SECONDS_PER_HOUR) / 60);
  const pad = (n: number) => n.toString().padStart(2, '0');
  const hoursDisplayed = hours % 24;

  return `${pad(hoursDisplayed)}:${pad(minutes)}`;
}

export function calculateDayFromSeconds(
  seconds: number,
  startTime: number = 0
): number {
  const totalSeconds = seconds + startTime;

  if (!Number.isFinite(totalSeconds) || totalSeconds < 0) return 1;
  return Math.floor(totalSeconds / SECONDS_PER_DAY) + 1;
}
