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

import type { BBox, FeatureCollection } from 'geojson';
import type { ExpressionSpecification } from 'mapbox-gl';
import { UILanguage } from '~/types';

const APP_NAME = 'VeloSim';
const GBFS_STATION_INFORMATION_URL = `https://gbfs.velobixi.com/gbfs/2-2/en/station_information.json`;
const GBFS_STATION_INFORMATION_STORAGE_KEY = 'gbfs_station_information';
const TOKEN_STORAGE_KEY = 'access_token';
const USER_PREFERENCES_STORAGE_KEY = 'user_preferences';
const DEFAULT_UI_LANGUAGE = UILanguage.English;

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
 * Global geographical bounds for cluster querying
 */
const GLOBAL_BOUNDS: BBox = [-180, -90, 180, 90] as const;

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

/**
 * Empty feature collection, usually used for clearing Mapbox map sources
 */
export const EMPTY_FEATURE_COLLECTION: FeatureCollection = {
  type: 'FeatureCollection',
  features: [],
};

/**
 * Station task-count color thresholds
 */
const STATION_COLOR_LOW = '#0796dd';
const STATION_COLOR_MEDIUM = '#890eba';
const STATION_COLOR_HIGH = '#ed2b09';

/**
 * Station task-count hover state colors
 */
const STATION_COLOR_LOW_HOVERED = '#0886c5';
const STATION_COLOR_MEDIUM_HOVERED = '#6a0990';
const STATION_COLOR_HIGH_HOVERED = '#b32107';

/**
 * Partial-assignment ring colors
 */
const STATION_RING_COLOR_LOW = 'rgba(7, 150, 221, 0.55)';
const STATION_RING_COLOR_MEDIUM = 'rgba(137, 14, 186, 0.55)';
const STATION_RING_COLOR_HIGH = 'rgba(237, 43, 9, 0.55)';

/**
 * Task-count thresholds for station colors
 */
const STATION_TASK_COUNT_MEDIUM_THRESHOLD = 2;
const STATION_TASK_COUNT_HIGH_THRESHOLD = 3;

export {
  APP_NAME,
  GBFS_STATION_INFORMATION_URL,
  GBFS_STATION_INFORMATION_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
  USER_PREFERENCES_STORAGE_KEY,
  DEFAULT_UI_LANGUAGE,
  MONTREAL_BOUNDS,
  GLOBAL_BOUNDS,
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
  STATION_COLOR_LOW,
  STATION_COLOR_MEDIUM,
  STATION_COLOR_HIGH,
  STATION_COLOR_LOW_HOVERED,
  STATION_COLOR_MEDIUM_HOVERED,
  STATION_COLOR_HIGH_HOVERED,
  STATION_RING_COLOR_LOW,
  STATION_RING_COLOR_MEDIUM,
  STATION_RING_COLOR_HIGH,
  STATION_TASK_COUNT_MEDIUM_THRESHOLD,
  STATION_TASK_COUNT_HIGH_THRESHOLD,
};
