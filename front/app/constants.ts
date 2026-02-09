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

export {
  APP_NAME,
  GBFS_STATION_INFORMATION_URL,
  GBFS_STATION_INFORMATION_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
  MONTREAL_BOUNDS,
  SCHEDULED_TASK_PATTERN,
};
