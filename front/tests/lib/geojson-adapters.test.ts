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

import { describe, it, expect } from 'vitest';
import { adaptStationsToGeoJSON } from '~/lib/geojson-adapters';
import type { Station } from '~/types';

describe('adaptStationsToGeoJSON', () => {
  it('should convert an array of stations to a GeoJSON FeatureCollection', () => {
    const stations: Station[] = [
      {
        id: 1,
        name: 'Central Station',
        position: [-74.006, 40.7128],
        tasks: [],
      },
      {
        id: 2,
        name: 'Park Station',
        position: [-73.9857, 40.7484],
        tasks: [],
      },
    ];

    const result = adaptStationsToGeoJSON(stations);

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: {
            id: 1,
            name: 'Central Station',
            taskCount: 0,
          },
          geometry: {
            type: 'Point',
            coordinates: [-74.006, 40.7128],
          },
        },
        {
          type: 'Feature',
          properties: {
            id: 2,
            name: 'Park Station',
            taskCount: 0,
          },
          geometry: {
            type: 'Point',
            coordinates: [-73.9857, 40.7484],
          },
        },
      ],
    });
  });

  it('should return an empty FeatureCollection when given an empty array', () => {
    const stations: Station[] = [];
    const result = adaptStationsToGeoJSON(stations);

    expect(result).toEqual({
      type: 'FeatureCollection',
      features: [],
    });
  });
});
