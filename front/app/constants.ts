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

import type { ExpressionSpecification } from 'mapbox-gl';

const APP_NAME = 'VeloSim';
const GBFS_STATION_INFORMATION_URL = `https://gbfs.velobixi.com/gbfs/2-2/en/station_information.json`;
const GBFS_STATION_INFORMATION_STORAGE_KEY = 'gbfs_station_information';
const TOKEN_STORAGE_KEY = 'access_token';

/**
 * Greater Montreal Area geographical bounds for validation
 */
const MONTREAL_BOUNDS = {
  LAT_MIN: 45.24,
  LAT_MAX: 45.86,
  LON_MIN: -74.26,
  LON_MAX: -73.22,
} as const;

/**
 * Regex pattern for validating scheduled task format: dayN:HH:MM
 * Examples: day1:09:30, day2:14:00, day10:08:15
 */
const SCHEDULED_TASK_PATTERN = /^day\d+:\d{2}:\d{2}$/;

/**
 * Number of frames between key frames emitted by the backend.
 * This is used to determine how often to save frames to the LocalFrameSource
 */
const SIMULATION_FRAMES_PER_KEY_FRAME = 20;

// Traffic congestion display colors (green → amber → red)
const FREE_FLOW_COLOR = '#22c55e';
const MODERATE_COLOR = '#fbb83c';
const SEVERE_COLOR = '#f87171';

// Opacity per congestion level (higher severity = more opaque)
const FREE_FLOW_OPACITY = 0.9;
const MODERATE_OPACITY = 0.95;
const SEVERE_OPACITY = 1.0;

// Zoom-scaled line-offset to separate two-way route directions
// prettier-ignore
const ROUTE_LINE_OFFSET: ExpressionSpecification =
  ['interpolate', ['linear'], ['zoom'], 10, 0, 13, 1, 15, 2, 17, 4, 20, 6, 22, 8];

// Zoom-scaled line-width for route layers
// prettier-ignore
const ROUTE_LINE_WIDTH: ExpressionSpecification =
  ['interpolate', ['linear'], ['zoom'], 10, 1, 13, 2, 15, 3, 17, 4, 20, 6, 22, 8];

export {
  APP_NAME,
  GBFS_STATION_INFORMATION_URL,
  GBFS_STATION_INFORMATION_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
  MONTREAL_BOUNDS,
  SCHEDULED_TASK_PATTERN,
  SIMULATION_FRAMES_PER_KEY_FRAME,
  FREE_FLOW_COLOR,
  MODERATE_COLOR,
  SEVERE_COLOR,
  FREE_FLOW_OPACITY,
  MODERATE_OPACITY,
  SEVERE_OPACITY,
  ROUTE_LINE_OFFSET,
  ROUTE_LINE_WIDTH,
};
